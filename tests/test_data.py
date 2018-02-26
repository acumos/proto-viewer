from acumos_proto_viewer.utils import load_proto, register_proto_from_url
from acumos_proto_viewer import data
import fakeredis
import hashlib

def _return_fake_msg():
    register_proto_from_url("http://myserver.com/fakemodelid/1.0.0/fakemodelid-1.0.0-proto")
    test = load_proto("fakemodelid_100_proto")
    """
    message Data1 {
    double a = 1;
    float b = 2;
    int32 c = 3;
    int64 d = 4;
    bool e = 5;
    string f = 6;
    bytes g = 7;}
    """
    m = test.Data1()
    m.a = 1111111111111111111111111
    m.b = 666.666
    m.c = 777
    m.d = 77777777777777
    m.e = True
    m.f = "helives"
    m.g = bytes("U+1F615", encoding="UTF-8")
    msgb = m.SerializeToString()
    return msgb

def _fake_msg_as_jsonwb():
    return {'a': 1.1111111111111111e+24,
            'b': 666.666015625, #rekt
            'c': 777,
            'd': 77777777777777,
            'e': True,
            'f': 'helives',
            'g': b'U+1F615',
            'apv_recieved_at': 55555555555,
            'apv_model_as_string': 'a: 1.1111111111111111e+24\nb: 666.666015625\nc: 777\nd: 77777777777777\ne: true\nf: "helives"\ng: "U+1F615"\n',
            'apv_sequence_number': 1}

def test_msg_to_json_preserve_bytes(monkeypatch, monkeyed_requests_get, cleanuptmp):
    monkeypatch.setattr('requests.get', monkeyed_requests_get)
    msgb = _return_fake_msg()
    #the method under test here generates a timestamp so we have to fake that
    monkeypatch.setattr('time.time', lambda: 55555555555)
    jpb = data._msg_to_json_preserve_bytes(msgb, "fakemodelid_100_proto", "Data1", 1)
    assert (jpb == _fake_msg_as_jsonwb())
    cleanuptmp()

def test_inject_data(monkeypatch, monkeyed_requests_get, cleanuptmp):
    monkeypatch.setattr('requests.get', monkeyed_requests_get)
    msgb = _return_fake_msg()

    #patching
    data.myredis = fakeredis.FakeStrictRedis()
    monkeypatch.setattr('acumos_proto_viewer.data.get_raw_data_source_size', lambda x, y: 0)
    monkeypatch.setattr('acumos_proto_viewer.data._get_bucket', lambda: 'asdf0')
    monkeypatch.setattr('time.time', lambda: 55555555555)

    data.inject_data(msgb, "fakemodelid_100_proto", "Data1")

    expected_h = "{0}{1}{2}".format("fakemodelid_100_proto", "Data1", 'asdf0')
    expected_index = hashlib.sha224(expected_h.encode('utf-8')).hexdigest().encode()

    assert(data.myredis.keys() == [expected_index])

    data.myredis.get(expected_index)

    assert(data.get_raw_data("fakemodelid_100_proto", "Data1", 0, 1) == [_fake_msg_as_jsonwb()])

    data.myredis.flushall()

    cleanuptmp()
