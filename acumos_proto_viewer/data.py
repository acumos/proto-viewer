from acumos_proto_viewer.utils import load_proto, register_proto_from_url

import hashlib

from datetime import date, datetime
from datetime import time as dttime
import time
import marshal

from google.protobuf import text_format
from acumos_proto_viewer import get_module_logger
import redis

_logger = get_module_logger(__name__)

proto_data_structure = {} #WARNING, HACKY FOR NOW, LATER SHOULD BE SQLITE OR SOMETHING

myredis = redis.StrictRedis(host='localhost', port=6379, db=0)


def _msg_to_json_preserve_bytes(binarydata, model_id, message_name, sequence_no):
    """
    Google's builtin method MessageToJson *silently reencodes* byte fields as base64
    But we don't want that here, becuase we have messages with raw image bytes
    So this custom function preserves byte fields
    Also it injects a timestamp
    """
    mod = load_proto(model_id)
    msg = getattr(mod, message_name)()
    msg.ParseFromString(binarydata)
    r = {}
    fields = proto_data_structure[model_id]["messages"][message_name]["properties"].keys()
    for f in fields:
        if f == "apv_recieved_at":
            r[f] = int(time.time())
        elif f == "apv_model_as_string":
            r[f] = text_format.MessageToString(msg)
        elif f == "apv_sequence_number":
            r[f] = sequence_no
        else:
            r[f] = getattr(msg, f)
    return r


def _get_bucket():
    """
    Note: we use this Unix timestamp bucketed methodlogy described here because myredis list members can't have TTLs:
        https://quickleft.com/blog/how-to-create-and-expire-list-items-in-myredis/
    The result of this is that a current session logging into the probe will see the data since the last midnight. If this isn't good enough, and memory is plentiful, we can go to the last week or something.
    """
    return str(int(datetime.combine(date.today(), dttime.min).timestamp()))


def _get_raw_data_source_index(model_id, message_name):
    """
    Get the myredis index given model_id and message_name
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
    Get the raw data (list of records) for a (model_id, message_name) pair.
    These data sources are populated from the /senddata endpoint.

        We always go from the last midngight
    """
    index = _get_raw_data_source_index(model_id, message_name)
    #you cannot have lists of dicts in myredis, the solution is to serialize them, see https://stackoverflow.com/questions/8664664/list-of-dicts-in-myredis
    return [marshal.loads(x) for x in myredis.lrange(index, index_start, index_end)] if myredis.exists(index) else []


def inject_data(binarydata, proto_url, message_name):
    """
    Inject data into the appropriate queue
    In the future if the data moves to a database this would go away
    """
    #register the proto file. Will return immediately if already exists
    model_id = register_proto_from_url(proto_url)

    size = get_raw_data_source_size(model_id, message_name)
    index = _get_raw_data_source_index(model_id, message_name)
    m = _msg_to_json_preserve_bytes(binarydata, model_id, message_name,
                                    size + 1)
    if sorted(m.keys()) == sorted(proto_data_structure[model_id]["messages"][message_name]["properties"].keys()): #safegaurd against malformed data
        myredis.rpush(index, marshal.dumps(m)) #this auto creates the key if it does not exist yet #https://myredis.io/commands/lpush
        if size == 0:
            _logger.debug("Created new data source and setting a TTL of one day")
            myredis.expire(index, 60*60*24)
    else:
        _logger.debug("Data dropped! {0} compared to {1}".format(m.keys(), sorted(proto_data_structure[model_id]["messages"][message_name]["properties"].keys())))
