import fakeredis
import hashlib
from acumos_proto_viewer.utils import register_proto_from_url
from acumos_proto_viewer import data


def test_msg_to_json_preserve_bytes(monkeypatch, monkeyed_requests_get, cleanuptmp, fake_msg_as_jsonwb, fake_msg, fake_msg_with_arrays_jsonwb, fake_msg_with_arrays):
    monkeypatch.setattr('requests.get', monkeyed_requests_get)
    register_proto_from_url("http://myserver.com/fakemodelid/1.0.0/fakemodelid-1.0.0-proto")
    register_proto_from_url("http://myserver.com/fakemodelidwitharrays/1.0.0/fakemodelidwitharrays-1.0.0-proto")
    msgb = fake_msg()
    # the method under test here generates a timestamp so we have to fake that
    monkeypatch.setattr('time.time', lambda: 55555555555)
    jpb = data._msg_to_json_preserve_bytes(
        msgb, "fakemodelid_100_proto", "Data1", 1)
    assert (jpb == fake_msg_as_jsonwb())

    msgba = fake_msg_with_arrays()
    jpb2 = data._msg_to_json_preserve_bytes(
        msgba, "fakemodelidwitharrays_100_proto", "ImageTagSet", 1)
    assert(jpb2 == fake_msg_with_arrays_jsonwb())

    cleanuptmp()


def _verify_inject_test(fake_msg_as_jsonwb, fake_msg_with_arrays_jsonwb):
    expected_h_1 = "{0}{1}{2}".format("fakemodelid_100_proto", "Data1", 'asdf0')
    expected_index_1 = hashlib.sha224(
        expected_h_1.encode('utf-8')).hexdigest().encode()

    expected_h_2 = "{0}{1}{2}".format("fakemodelidwitharrays_100_proto", "ImageTagSet", 'asdf0')
    expected_index_2 = hashlib.sha224(
        expected_h_2.encode('utf-8')).hexdigest().encode()

    assert(data.myredis.keys() == [expected_index_1, expected_index_2])

    assert(data.get_raw_data("fakemodelid_100_proto",
                             "Data1", 0, 1) == [fake_msg_as_jsonwb()])

    assert(data.get_raw_data("fakemodelidwitharrays_100_proto", "ImageTagSet", 0, 1) == [fake_msg_with_arrays_jsonwb()])

    data.myredis.flushall()


def test_inject_data_env(monkeypatch, monkeyed_requests_get, cleanuptmp, fake_msg, fake_msg_with_arrays, fake_msg_as_jsonwb, fake_msg_with_arrays_jsonwb):
    monkeypatch.setattr('requests.get', monkeyed_requests_get)
    assert('fakemodelid_100_proto' not in data.list_known_protobufs())
    assert('fakemodelidwitharrays_100_proto' not in data.list_known_protobufs())
    register_proto_from_url("http://myserver.com/fakemodelidwitharrays/1.0.0/fakemodelidwitharrays-1.0.0-proto")
    register_proto_from_url("fakemodelid/1.0.0/fakemodelid-1.0.0-proto")
    assert('fakemodelid_100_proto' in data.list_known_protobufs())
    assert('fakemodelidwitharrays_100_proto' in data.list_known_protobufs())

    # patching
    data.myredis = fakeredis.FakeStrictRedis()
    monkeypatch.setattr(
        'acumos_proto_viewer.data.get_raw_data_source_size', lambda x, y: 0)
    monkeypatch.setattr(
        'acumos_proto_viewer.data._get_bucket', lambda: 'asdf0')
    monkeypatch.setattr('time.time', lambda: 55555555555)

    msgb = fake_msg()
    data.inject_data(
        msgb, "fakemodelid/1.0.0/fakemodelid-1.0.0-proto", "Data1")

    msgbwa = fake_msg_with_arrays()
    data.inject_data(
        msgbwa, "fakemodelidwitharrays/1.0.0/fakemodelidwitharrays-1.0.0-proto", "ImageTagSet")
    _verify_inject_test(fake_msg_as_jsonwb, fake_msg_with_arrays_jsonwb)

    cleanuptmp()


def test_inject_data(monkeypatch, monkeyed_requests_get, cleanuptmp, fake_msg, fake_msg_with_arrays, fake_msg_as_jsonwb, fake_msg_with_arrays_jsonwb):
    # patching
    monkeypatch.setattr('requests.get', monkeyed_requests_get)
    data.myredis = fakeredis.FakeStrictRedis()
    monkeypatch.setattr(
        'acumos_proto_viewer.data.get_raw_data_source_size', lambda x, y: 0)
    monkeypatch.setattr(
        'acumos_proto_viewer.data._get_bucket', lambda: 'asdf0')
    monkeypatch.setattr('time.time', lambda: 55555555555)

    assert('fakemodelid_100_proto' not in data.list_known_protobufs())
    assert('fakemodelidwitharrays_100_proto' not in data.list_known_protobufs())
    msgb = fake_msg()
    data.inject_data(
        msgb, "http://myserver.com/fakemodelid/1.0.0/fakemodelid-1.0.0-proto", "Data1")
    msgbwa = fake_msg_with_arrays()
    data.inject_data(
        msgbwa, "fakemodelidwitharrays/1.0.0/fakemodelidwitharrays-1.0.0-proto", "ImageTagSet")

    assert('fakemodelid_100_proto' in data.list_known_protobufs())
    assert('fakemodelidwitharrays_100_proto' in data.list_known_protobufs())
    _verify_inject_test(fake_msg_as_jsonwb, fake_msg_with_arrays_jsonwb)

    cleanuptmp()
