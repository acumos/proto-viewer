# Acumos - Apache 2.0


from requests.exceptions import HTTPError
import pytest
from acumos_proto_viewer.utils import load_proto
from acumos_proto_viewer import data
import test_constants


class FakeResponse():
    def __init__(self, status_code, text):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPError(response=FakeResponse(404, ""))


@pytest.fixture
def monkeyed_requests_get():
    def mrg(url):
        if url == test_constants.test_proto_url:
            return FakeResponse(status_code=200,
                                text=test_constants.test_proto_txt)
        if url == test_constants.test_proto_with_arrays_url:
            return FakeResponse(status_code=200,
                                text=test_constants.test_proto_with_arrays_txt)
        if url == "http://myserver.com/emptyinside":
            return FakeResponse(status_code=404,
                                text="")
        if url == test_constants.test_probe_fake_schema_url:
            return FakeResponse(status_code=200,
                                text=test_constants.test_probe_fake_schema_txt)

    return mrg


@pytest.fixture
def cleanuptmp():
    def _dt():
        for mid in [test_constants.test_proto_mid, test_constants.test_proto_with_arrays_mid]:
            del data.proto_data_structure[mid]
            assert(mid not in data.list_known_protobufs())
    return _dt


@pytest.fixture
def fake_msg():
    def _fake_msg():
        test = load_proto(test_constants.test_proto_mid)
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
def fake_msg_with_arrays():
    def _fake_msg_with_arrays():
        test = load_proto(test_constants.test_proto_with_arrays_mid)
        m = test.ImageTagSet(image=[1, 2, 3], tag=["fish", "cat", "dog"], score=[0.8, 0.9, 1.0])
        msgb = m.SerializeToString()
        return msgb
    return _fake_msg_with_arrays


@pytest.fixture
def fake_msg_with_arrays_jsonwb():
    def _fake_msg_with_arrays_jsonwb():
        return {"image": ['1', '2', '3'],  # TODO! This is messed up because data._msg_to_json_preserve_bytes does not currently handle nested itens, you get whatever google gives you!
                "tag": ["fish", "cat", "dog"],
                "score": [0.8, 0.9, 1.0],
                'apv_received_at': 55555555555,
                'apv_sequence_number': 1,
                'apv_model_as_string': '{\n    "image": [\n        "1",\n        "2",\n        "3"\n    ],\n    "score": [\n        0.8,\n        0.9,\n        1.0\n    ],\n    "tag": [\n        "fish",\n        "cat",\n        "dog"\n    ]\n}'}
    return _fake_msg_with_arrays_jsonwb


@pytest.fixture
def fake_msg_as_jsonwb():
    def _fake_msg_as_jsonwb():
        return {'a': 1.1111111111111111e+24,
                'b': 666.666015625,  # rekt
                'c': 777,
                'd': 77777777777777,
                'e': True,
                'f': 'helives',
                'g': b'U+1F615',
                'apv_received_at': 55555555555,
                'apv_model_as_string': '{\n    "a": 1.1111111111111111e+24,\n    "b": 666.666015625,\n    "c": 777,\n    "d": 77777777777777,\n    "e": true,\n    "f": "helives",\n    "g": "<RAW BYTES>"\n}',
                'apv_sequence_number': 1}
    return _fake_msg_as_jsonwb
