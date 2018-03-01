import fakeredis
import hashlib
from acumos_proto_viewer.utils import register_proto_from_url, list_compiled_proto_names
from acumos_proto_viewer import data


def test_msg_to_json_preserve_bytes(monkeypatch, monkeyed_requests_get, cleanuptmp, fake_msg_as_jsonwb, fake_msg):
    monkeypatch.setattr('requests.get', monkeyed_requests_get)
    register_proto_from_url(
        "http://myserver.com/fakemodelid/1.0.0/fakemodelid-1.0.0-proto")
    msgb = fake_msg()
    # the method under test here generates a timestamp so we have to fake that
    monkeypatch.setattr('time.time', lambda: 55555555555)
    jpb = data._msg_to_json_preserve_bytes(
        msgb, "fakemodelid_100_proto", "Data1", 1)
    assert (jpb == fake_msg_as_jsonwb())
    cleanuptmp()


def _verify_inject_test(cleanuptmp, fake_msg_as_jsonwb):
    expected_h = "{0}{1}{2}".format("fakemodelid_100_proto", "Data1", 'asdf0')
    expected_index = hashlib.sha224(
        expected_h.encode('utf-8')).hexdigest().encode()

    assert(data.myredis.keys() == [expected_index])

    data.myredis.get(expected_index)

    assert(data.get_raw_data("fakemodelid_100_proto",
                             "Data1", 0, 1) == [fake_msg_as_jsonwb()])

    data.myredis.flushall()

    cleanuptmp()


def test_inject_data_env(monkeypatch, monkeyed_requests_get, cleanuptmp, fake_msg, fake_msg_as_jsonwb):
    monkeypatch.setattr('requests.get', monkeyed_requests_get)
    assert('fakemodelid_100_proto' not in list_compiled_proto_names())
    register_proto_from_url("fakemodelid/1.0.0/fakemodelid-1.0.0-proto")
    assert('fakemodelid_100_proto' in list_compiled_proto_names())
    msgb = fake_msg()

    # patching
    data.myredis = fakeredis.FakeStrictRedis()
    monkeypatch.setattr(
        'acumos_proto_viewer.data.get_raw_data_source_size', lambda x, y: 0)
    monkeypatch.setattr(
        'acumos_proto_viewer.data._get_bucket', lambda: 'asdf0')
    monkeypatch.setattr('time.time', lambda: 55555555555)

    data.inject_data(
        msgb, "fakemodelid/1.0.0/fakemodelid-1.0.0-proto", "Data1")
    _verify_inject_test(cleanuptmp, fake_msg_as_jsonwb)


def test_inject_data(monkeypatch, monkeyed_requests_get, cleanuptmp, fake_msg, fake_msg_as_jsonwb):
    monkeypatch.setattr('requests.get', monkeyed_requests_get)
    msgb = fake_msg()

    # patching
    data.myredis = fakeredis.FakeStrictRedis()
    monkeypatch.setattr(
        'acumos_proto_viewer.data.get_raw_data_source_size', lambda x, y: 0)
    monkeypatch.setattr(
        'acumos_proto_viewer.data._get_bucket', lambda: 'asdf0')
    monkeypatch.setattr('time.time', lambda: 55555555555)

    assert('fakemodelid_100_proto' not in list_compiled_proto_names())
    data.inject_data(
        msgb, "http://myserver.com/fakemodelid/1.0.0/fakemodelid-1.0.0-proto", "Data1")
    assert('fakemodelid_100_proto' in list_compiled_proto_names())
    _verify_inject_test(cleanuptmp, fake_msg_as_jsonwb)
