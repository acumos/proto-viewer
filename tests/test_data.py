# Acumos - Apache 2.0


import fakeredis
import hashlib
from acumos_proto_viewer.utils import register_proto_from_url
from acumos_proto_viewer import data


def test_msg_to_json_preserve_bytes(monkeypatch, monkeyed_requests_get, cleanuptmp,
                                    fake_msg_as_jsonwb, fake_msg, fake_msg_with_arrays_jsonwb, fake_msg_with_arrays,
                                    test_proto_url, test_proto_mid, test_proto_msg,
                                    test_proto_with_arrays_url, test_proto_with_arrays_mid, test_proto_with_arrays_msg):
    monkeypatch.setattr('requests.get', monkeyed_requests_get)
    register_proto_from_url(test_proto_url)
    register_proto_from_url(test_proto_with_arrays_url)
    msgb = fake_msg()
    # the method under test here generates a timestamp so we have to fake that
    monkeypatch.setattr('time.time', lambda: 55555555555)
    jpb = data._msg_to_json_preserve_bytes(msgb, test_proto_mid, test_proto_msg, 1)
    assert (jpb == fake_msg_as_jsonwb())

    msgba = fake_msg_with_arrays()
    jpb2 = data._msg_to_json_preserve_bytes(msgba, test_proto_with_arrays_mid, test_proto_with_arrays_msg, 1)
    assert(jpb2 == fake_msg_with_arrays_jsonwb())

    cleanuptmp()


def _verify_inject_test(fake_msg_as_jsonwb, fake_msg_with_arrays_jsonwb,
                        test_proto_mid, test_proto_msg,
                        test_proto_with_arrays_mid, test_proto_with_arrays_msg):
    expected_h_1 = "{0}{1}{2}".format(test_proto_mid, test_proto_msg, 'asdf0')
    expected_index_1 = hashlib.sha224(expected_h_1.encode('utf-8')).hexdigest().encode()
    expected_h_2 = "{0}{1}{2}".format(test_proto_with_arrays_mid, test_proto_with_arrays_msg, 'asdf0')
    expected_index_2 = hashlib.sha224(expected_h_2.encode('utf-8')).hexdigest().encode()
    assert(data.myredis.keys() == [expected_index_1, expected_index_2])
    assert(data.get_raw_data(test_proto_mid, test_proto_msg, 0, 1) == [fake_msg_as_jsonwb()])
    assert(data.get_raw_data(test_proto_with_arrays_mid, test_proto_with_arrays_msg, 0, 1) == [fake_msg_with_arrays_jsonwb()])

    data.myredis.flushall()


def test_inject_data_env(monkeypatch, monkeyed_requests_get, cleanuptmp,
                         fake_msg, fake_msg_with_arrays, fake_msg_as_jsonwb, fake_msg_with_arrays_jsonwb,
                         test_proto_url, test_proto_mid, test_proto_msg,
                         test_proto_with_arrays_url, test_proto_with_arrays_mid, test_proto_with_arrays_msg):
    monkeypatch.setattr('requests.get', monkeyed_requests_get)
    assert(test_proto_mid not in data.list_known_protobufs())
    assert(test_proto_with_arrays_mid not in data.list_known_protobufs())
    register_proto_from_url(test_proto_url)
    register_proto_from_url(test_proto_with_arrays_url)
    assert(test_proto_mid in data.list_known_protobufs())
    assert(test_proto_with_arrays_mid in data.list_known_protobufs())

    # patching
    data.myredis = fakeredis.FakeStrictRedis()
    monkeypatch.setattr('acumos_proto_viewer.data.get_raw_data_source_count', lambda x, y: 0)
    monkeypatch.setattr('acumos_proto_viewer.data._get_bucket', lambda: 'asdf0')
    monkeypatch.setattr('time.time', lambda: 55555555555)

    msgb = fake_msg()
    data.inject_data(msgb, test_proto_url, test_proto_msg)
    msgbwa = fake_msg_with_arrays()
    data.inject_data(msgbwa, test_proto_with_arrays_url, test_proto_with_arrays_msg)
    _verify_inject_test(fake_msg_as_jsonwb, fake_msg_with_arrays_jsonwb,
                        test_proto_mid, test_proto_msg,
                        test_proto_with_arrays_mid, test_proto_with_arrays_msg)

    cleanuptmp()


def test_inject_data(monkeypatch, monkeyed_requests_get, cleanuptmp,
                     fake_msg, fake_msg_with_arrays, fake_msg_as_jsonwb, fake_msg_with_arrays_jsonwb,
                     test_proto_url, test_proto_mid, test_proto_msg,
                     test_proto_with_arrays_url, test_proto_with_arrays_mid, test_proto_with_arrays_msg):
    # patching
    monkeypatch.setattr('requests.get', monkeyed_requests_get)
    data.myredis = fakeredis.FakeStrictRedis()
    monkeypatch.setattr('acumos_proto_viewer.data.get_raw_data_source_count', lambda x, y: 0)
    monkeypatch.setattr('acumos_proto_viewer.data._get_bucket', lambda: 'asdf0')
    monkeypatch.setattr('time.time', lambda: 55555555555)

    assert(test_proto_mid not in data.list_known_protobufs())
    assert(test_proto_with_arrays_mid not in data.list_known_protobufs())
    msgb = fake_msg()
    data.inject_data(msgb, test_proto_url, test_proto_msg)
    msgbwa = fake_msg_with_arrays()
    data.inject_data(msgbwa, test_proto_with_arrays_url, test_proto_with_arrays_msg)
    assert(test_proto_mid in data.list_known_protobufs())
    assert(test_proto_with_arrays_mid in data.list_known_protobufs())
    _verify_inject_test(fake_msg_as_jsonwb, fake_msg_with_arrays_jsonwb,
                        test_proto_mid, test_proto_msg,
                        test_proto_with_arrays_mid, test_proto_with_arrays_msg)

    cleanuptmp()
