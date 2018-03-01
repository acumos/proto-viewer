from requests.exceptions import HTTPError
import pytest
import os
from acumos_proto_viewer.utils import list_compiled_proto_names, load_proto


class FakeResponse():
    def __init__(self, status_code, text):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPError(response=FakeResponse(404, ""))


test_proto = """
syntax = "proto3";

package mygreatpackage;

message Data1 {
    double a = 1;
    float b = 2;
    int32 c = 3;
    int64 d = 4;
    bool e = 5;
    string f = 6;
    bytes g = 7;
}

message Data2 {
    Data1 a = 1;
    map<string, Data1> b = 2;
    map<string, int32> c = 3;
    repeated Data1 d = 4;
    repeated int32 e = 5;
}
"""


@pytest.fixture
def monkeyed_requests_get():
    def mrg(url):
        if url == "http://myserver.com/fakemodelid/1.0.0/fakemodelid-1.0.0-proto":
            return FakeResponse(status_code=200,
                                text=test_proto)
        if url == "http://myserver.com/emptyinside":
            return FakeResponse(status_code=404,
                                text="")

    return mrg


@pytest.fixture
def cleanuptmp():
    def _dt():
        os.remove("/tmp/protofiles/fakemodelid_100_proto.proto")
        os.remove("/tmp/protofiles/fakemodelid_100_proto_pb2.py")
        assert('fakemodelid_100_proto' not in list_compiled_proto_names())
    return _dt


@pytest.fixture
def fake_msg():
    def _fake_msg():
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
    return _fake_msg


@pytest.fixture
def fake_msg_as_jsonwb():
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
    return _fake_msg_as_jsonwb
