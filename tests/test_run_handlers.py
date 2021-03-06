# Acumos - Apache 2.0


import hashlib
import fakeredis
from acumos_proto_viewer.run_handlers import MODEL_SELECTION, MESSAGE_SELECTION
from acumos_proto_viewer.run_handlers import get_source_index, handle_data_post, handle_onap_mr_put, handle_onap_mr_delete, get_model_properties, get_modelid_messagename_type
from acumos_proto_viewer import data


def test_get_source_index():
    """
    Test utils.get_source_index
    """
    sid = "foo"
    mid = "bar"
    mess_name = "shazam"
    ind = "{0}{1}{2}".format(sid, mid, mess_name)
    expected_index = hashlib.sha224(ind.encode('utf-8')).hexdigest()
    assert get_source_index(sid, mid, mess_name) == expected_index

    field_name = "amazingfield"
    ind = "{0}{1}{2}{3}".format(sid, mid, mess_name, field_name)
    expected_index = hashlib.sha224(ind.encode('utf-8')).hexdigest()
    assert get_source_index(sid, mid, mess_name, field_name) == expected_index


def test_handle_data_post(monkeypatch, monkeyed_requests_get, fake_msg, cleanuptmp,
                          test_proto_url, test_proto_mid, test_proto_with_arrays_url, test_proto_with_arrays_mid):
    """
    Test run_handlers.handle_data_post
    """
    monkeypatch.setattr('requests.get', monkeyed_requests_get)
    assert(test_proto_mid not in data.list_known_protobufs())
    assert(test_proto_with_arrays_mid not in data.list_known_protobufs())
    headers = {"PROTO-URL": test_proto_url, "Message-Name": "Data1"}
    code, status = handle_data_post(headers, fake_msg())
    headers = {"PROTO-URL": test_proto_with_arrays_url, "Message-Name": "ImageTagSet"}
    code, status = handle_data_post(headers, fake_msg())
    assert(test_proto_mid in data.list_known_protobufs())
    assert(test_proto_with_arrays_mid in data.list_known_protobufs())

    assert get_model_properties(test_proto_mid, "Data1", "protobuf") == {
        'a': {'type': 'number'},
        'b': {'type': 'number'},
        'c': {
            'type': 'integer',
            'minimum': -2147483648,
            'maximum': 2147483647
        },
        'd': {
            'type': 'integer',
            'minimum': -9007199254740991,
            'maximum': 9007199254740991
        },
        'e': {'type': 'boolean'},
        'f': {'type': 'string'},
        'g': {'type': 'string'},
        'apv_received_at': {'type': 'integer'},
        'apv_model_as_string': {'type': 'string'},
        'apv_sequence_number': {'type': 'integer'}}

    assert get_model_properties(test_proto_with_arrays_mid, "ImageTagSet", "protobuf") == {
        "image": {
            "type": "array",
            "items": {
                "type": "integer",
                "minimum": -9007199254740991,
                "maximum": 9007199254740991
            }
        },
        "tag": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "score": {
            "type": "array",
            "items": {
                "type": "number"
            }
        },
        "apv_received_at": {
            "type": "integer"
        },
        "apv_model_as_string": {
            "type": "string"
        },
        "apv_sequence_number": {
            "type": "integer"
        }
    }

    # test failures
    headers = {"PROTO-URXXX": test_proto_mid, "Message-Name": "Data1"}
    code, status = handle_data_post(headers, fake_msg())
    assert code == 400
    assert status == "Error: PROTO-URL or Message-Name header missing."

    headers = {"PROTO-URL": "emptyinside", "Message-Name": "Data1"}
    code, status = handle_data_post(headers, fake_msg())
    assert code == 400
    assert status == "Error: emptyinside was not downloadable!"

    cleanuptmp()


def test_handle_onap_mr_put_delete(monkeypatch, monkeyed_requests_get, test_probe_fake_schema_url):
    """
    Test run_handlers put and delete of onap_mr
    """
    def noop(*args, **kwargs):
        """monkeypatch staring a thread"""
        pass

    data.myredis = fakeredis.FakeStrictRedis()
    monkeypatch.setattr('threading.Thread.start', noop)
    monkeypatch.setattr('requests.get', monkeyed_requests_get)

    headers = {"schema-url": test_probe_fake_schema_url,
               "server-hostname": "foo",
               "server-port": 666}

    topic_name = "amazing_topic"

    # pre checks
    assert data.myredis.get("amazing_topic") is None
    code, status = handle_onap_mr_delete(topic_name)
    assert code == 404

    code, status = handle_onap_mr_put(headers, topic_name)
    assert data.myredis.get("amazing_topic") is not None
    assert code == 200
    assert status == ""
    assert "amazing_topic" in data.list_known_jsonschemas()

    assert get_model_properties("amazing_topic", "unused", "jsonschema") == {
        "value": {"type": "number", "description": ""},
        "apv_received_at": {'type': 'integer'},
        "apv_model_as_string": {'type': 'string'},
        "apv_sequence_number": {'type': 'integer'}}

    code, status = handle_onap_mr_delete(topic_name)
    assert code == 200
    assert data.myredis.get("amazing_topic") is None

    code, status = handle_onap_mr_delete(topic_name)
    assert code == 404


def test_get_modelid_messagename_type():
    class FakeVal():
        def __init__(self, v):
            self.value = v

    class FakeDoc():
        def __init__():
            pass

        def get_model_by_name(arg):
            if arg == MODEL_SELECTION:
                return FakeVal("protobuf_amazing_model")
            if arg == MESSAGE_SELECTION:
                return FakeVal("amazing_message")

    assert ("amazing_model", "amazing_message",
            "protobuf") == get_modelid_messagename_type(FakeDoc)

    class FakeDoc2():
        def __init__():
            pass

        def get_model_by_name(arg):
            if arg == MODEL_SELECTION:
                return FakeVal("topic_amazing_model")

    assert ("amazing_model", "amazing_model_messages",
            "jsonschema") == get_modelid_messagename_type(FakeDoc2)
