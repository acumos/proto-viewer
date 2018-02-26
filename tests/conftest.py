from requests.exceptions import HTTPError
import pytest
import os

class FakeResponse():
    def __init__(self, status_code, text):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPError(response=FakeResponse(404, ""))


test_proto = """
syntax = "proto3";

package testpaul;

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
    return mrg

@pytest.fixture
def cleanuptmp():
    def _dt():
        os.remove("/tmp/protofiles/fakemodelid_100_proto.proto")
        os.remove("/tmp/protofiles/fakemodelid_100_proto_pb2.py")
    return _dt
