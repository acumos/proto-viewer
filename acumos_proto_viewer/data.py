from acumos_proto_viewer.utils import load_proto, register_jsonschema_from_url, register_proto_from_url

import jsonschema
import hashlib
import uuid
from threading import Thread

from datetime import date, datetime
from datetime import time as dttime
import time
import json
import pickle
import copy

import requests

from google.protobuf.json_format import MessageToJson
from acumos_proto_viewer import get_module_logger
import redis

_logger = get_module_logger(__name__)

proto_data_structure = {}
jsonschema_data_structure = {}

myredis = redis.StrictRedis(host='localhost', port=6379, db=0)


def _msg_to_json_preserve_bytes(binarydata, model_id, message_name, sequence_no):
    """
    Converts an inbound protobuf message to JSON, preserving byte fields.
    Google's builtin method MessageToJson *silently reencodes* byte fields as base64.
    But we don't want that because that breaks images that arrive as raw bytes. So
    this preserves byte fields. Also it injects values for well-known probe fields.
    """
    # this level of chattiness is not desirable for typical use
    # _logger.debug("_msg_to_json_preserve_bytes: model_id %s, message %s", model_id, message_name)
    mod = load_proto(model_id)
    msg = getattr(mod, message_name)()
    msg.ParseFromString(binarydata)

    json_equiv = json.loads(MessageToJson(msg))
    fields = proto_data_structure[model_id]["messages"][message_name]["properties"].keys()
    for f in fields:
        if f == "apv_received_at":
            json_equiv[f] = int(time.time())
        elif f == "apv_sequence_number":
            json_equiv[f] = sequence_no
        elif f == "apv_model_as_string":
            pass  # handled later below
        else:
            # check if the item type was bytes, and preserve it if so, no encoding!
            # TODO! Check for nested things like arrays of bytes!
            item = getattr(msg, f)
            # print((f, item, type(item), json_equiv[f]))
            if isinstance(item, bytes) or isinstance(item, int):
                json_equiv[f] = item

    # in order to do the json serialization for the RAW format, create a copy
    # of this where we take the bytes and b64 them
    json_copy = copy.deepcopy(json_equiv)
    del json_copy["apv_sequence_number"]
    del json_copy["apv_received_at"]
    for k in json_copy:
        v = json_copy[k]
        if isinstance(v, bytes):
            json_copy[k] = "<RAW BYTES>"
    json_equiv["apv_model_as_string"] = json.dumps(json_copy, indent=4, sort_keys=True)
    return json_equiv


def _get_bucket():
    """
    Note: we use the Unix timestamp bucketed methodology described below
    because myredis list members can't have TTLs:
        https://quickleft.com/blog/how-to-create-and-expire-list-items-in-myredis/
    The result of this is that a current session logging into the probe will see
    the data since the last midnight. If this isn't good enough, and memory is
    plentiful, we can go to the last week or something.
    """
    return str(int(datetime.combine(date.today(), dttime.min).timestamp()))


def _get_raw_data_source_index(model_id, message_name):
    """
    Gets the myredis index given model_id and message_name
    """
    bucket = _get_bucket()
    h = "{0}{1}{2}".format(model_id, message_name, bucket)
    index = hashlib.sha224(h.encode('utf-8')).hexdigest()
    return index

###########
# PUBLIC


def get_raw_data_source_size(model_id, message_name):
    index = _get_raw_data_source_index(model_id, message_name)
    return myredis.llen(index) if myredis.exists(index) else 0


def get_raw_data(model_id, message_name, index_start, index_end):
    """
    Gets the raw data (list of records) for a (model_id, message_name) pair.
    These data sources are populated from the /senddata endpoint.
    We always go from the last midnight.
    """
    index = _get_raw_data_source_index(model_id, message_name)
    # you cannot have lists of dicts in myredis, the solution is to serialize them,
    # see https://stackoverflow.com/questions/8664664/list-of-dicts-in-myredis
    return [pickle.loads(x) for x in myredis.lrange(index, index_start, index_end)] if myredis.exists(index) else []


def inject_data(binarydata, proto_url, message_name):
    """
    Injects data into the appropriate queue.
    Raises SchemaNotReachable if the proto_url is invalid.
    In the future if the data moves to a database this would go away
    """
    # register the proto file. Will return immediately if already exists
    model_id = register_proto_from_url(proto_url)

    size = get_raw_data_source_size(model_id, message_name)
    index = _get_raw_data_source_index(model_id, message_name)
    _logger.debug("inject_data: message_name %s sequence %d", message_name, size + 1)
    m = _msg_to_json_preserve_bytes(binarydata, model_id, message_name, size + 1)
    # safeguard against malformed data
    act_keys = sorted(m.keys())
    exp_keys = sorted(proto_data_structure[model_id]["messages"][message_name]["properties"].keys())
    if act_keys == exp_keys:
        # this auto creates the key if it does not exist yet #https://myredis.io/commands/lpush
        try:
            pickled_message = pickle.dumps(m)
            myredis.rpush(index, pickled_message)
        except Exception as exc:
            _logger.error("inject_data: failed to pickle data or upload it to redis")
            _logger.exception(exc)
        if size == 0:
            _logger.debug("inject_data: created new data source with TTL of one day")
            myredis.expire(index, 60 * 60 * 24)
    else:
        _logger.warn("inject_data: dropped message due to unexpected keys: received {0} expected {1}".format(act_keys, exp_keys))


def delete_mr_subscription(topic_name):
    """
    Teardown a message-router subscription
    """
    # all we need to do is delete the active flag and the thread will kill itself
    if myredis.get(topic_name) is None:
        return False
    myredis.delete(topic_name)
    return True


def setup_mr_subscription(fully_qualified_topic_url, schema_url, topic_name):
    """
    Creates a new message-router subscription (if it doesn't already exist)
    """
    register_jsonschema_from_url(schema_url, topic_name)
    if myredis.get(topic_name) is not None:
        return True
    myredis.set(topic_name, 1)
    tp = Thread(target=mr_reader_thread, args=[fully_qualified_topic_url, topic_name])
    tp.start()  # thread will kill itself when DELETE is called or an exception is raised


def mr_reader_thread(fully_qualified_topic_url, topic_name):
    """
    Enters a message-router polling loop.
    topic name == model_id!
    """
    _logger.info("Starting MR thread on topic %s", topic_name)
    groupid = uuid.uuid4().hex
    clientid = uuid.uuid4().hex
    while myredis.get(topic_name) is not None:  # check if we should die
        time.sleep(.5)
        _logger.debug("Getting from {0}".format(topic_name))
        resp = requests.get('{0}/{1}/{2}?timeout=1000&limit=100'.format(fully_qualified_topic_url, groupid, clientid))
        try:
            resp.raise_for_status()
        except Exception as exc:
            myredis.delete(topic_name)
            raise exc

        data = json.loads(resp.text)

        message_name = "{0}_messages".format(topic_name)

        size = get_raw_data_source_size(topic_name, message_name)
        index = _get_raw_data_source_index(topic_name, message_name)

        item_sequence_no = size + 1
        for data_item in data:
            data_item = json.loads(data_item)

            # set the apv fields
            data_item["apv_model_as_string"] = json.dumps(data_item)
            data_item["apv_received_at"] = int(time.time())
            data_item["apv_sequence_number"] = item_sequence_no

            # safegaurd against malformed data
            try:
                jsonschema.validate(data_item, jsonschema_data_structure[topic_name]["json_schema"])
            except jsonschema.exceptions.ValidationError:
                _logger.error("data item does not match the schema!")

            # this auto creates the key if it does not exist yet #https://myredis.io/commands/lpush
            myredis.rpush(index, pickle.dumps(data_item))
            _logger.debug("MR reader for {0} recieved valid data".format(topic_name))
            if size == 0:
                _logger.debug(
                    "Created new data source and setting a TTL of one day")
                myredis.expire(index, 60 * 60 * 24)

            item_sequence_no += 1

    _logger.debug("mr_reader_thread for %s is now exiting", topic_name)


def list_known_jsonschemas():
    """
    Returns the list of known jsonschemas
    """
    return [k for k in jsonschema_data_structure]


def list_known_protobufs():
    """
    Returns the list of known protobufs
    """
    return [k for k in proto_data_structure]
