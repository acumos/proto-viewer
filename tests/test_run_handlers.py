import hashlib
from acumos_proto_viewer.run_handlers import get_source_index, handle_data_post
from acumos_proto_viewer.utils import list_compiled_proto_names


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


def test_handle_data_post(monkeypatch, monkeyed_requests_get, fake_msg, cleanuptmp):
    """
    Test run_handlers.handle_data_post
    """
    monkeypatch.setattr('requests.get', monkeyed_requests_get)
    assert('fakemodelid_100_proto' not in list_compiled_proto_names())
    headers = {"PROTO-URL": "fakemodelid/1.0.0/fakemodelid-1.0.0-proto",
               "Message-Name": "Data1"}

    code, status = handle_data_post(headers, fake_msg())
    assert('fakemodelid_100_proto' in list_compiled_proto_names())

    headers = {"PROTO-UR": "fakemodelid/1.0.0/fakemodelid-1.0.0-proto",
               "Message-Name": "Data1"}

    code, status = handle_data_post(headers, fake_msg())
    assert code == 400
    assert status == "Error: PROTO-URL or Message-Name header missing."

    headers = {"PROTO-URL": "emptyinside",
               "Message-Name": "Data1"}

    code, status = handle_data_post(headers, fake_msg())
    assert code == 400
    assert status == "Error: emptyinside was not downloadable!"

    cleanuptmp()
