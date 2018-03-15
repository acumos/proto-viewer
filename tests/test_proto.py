from types import ModuleType
from acumos_proto_viewer.utils import register_proto_from_url, load_proto, _protobuf_to_js
from acumos_proto_viewer import data


def test_register_load(monkeypatch, monkeyed_requests_get, cleanuptmp):
    monkeypatch.setattr('requests.get', monkeyed_requests_get)
    register_proto_from_url("http://myserver.com/fakemodelid/1.0.0/fakemodelid-1.0.0-proto")
    assert('fakemodelid_100_proto' in data.list_known_protobufs())
    test_pb2 = load_proto("fakemodelid_100_proto")
    test_pb2 = load_proto("fakemodelid_100_proto")  # cache hit

    assert isinstance(test_pb2, ModuleType)
    cleanuptmp()


def test_protobuf_to_js(monkeypatch, monkeyed_requests_get, cleanuptmp):
    monkeypatch.setattr('requests.get', monkeyed_requests_get)
    register_proto_from_url("fakemodelid/1.0.0/fakemodelid-1.0.0-proto")
    assert('fakemodelid_100_proto' in data.list_known_protobufs())

    js = _protobuf_to_js("fakemodelid_100_proto")
    cleanuptmp()
    assert js == {
        "definitions": {
            "mygreatpackage.Data1": {
                "title": "Data1",
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number"
                    },
                    "b": {
                        "type": "number"
                    },
                    "c": {
                        "type": "integer",
                        "minimum": -2147483648,
                        "maximum": 2147483647
                    },
                    "d": {
                        "type": "integer",
                        "minimum": -9007199254740991,
                        "maximum": 9007199254740991
                    },
                    "e": {
                        "type": "boolean"
                    },
                    "f": {
                        "type": "string"
                    },
                    "g": {
                        "type": "string"
                    }
                }
            },
            "mygreatpackage.Data2": {
                "title": "Data2",
                "type": "object",
                "properties": {
                    "a": {
                        "$ref": "#/definitions/mygreatpackage.Data1"
                    },
                    "b": {
                        "type": "object",
                        "additionalProperties": {
                            "$ref": "#/definitions/mygreatpackage.Data1"
                        }
                    },
                    "c": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "integer",
                            "minimum": -2147483648,
                            "maximum": 2147483647
                        }
                    },
                    "d": {
                        "type": "array",
                        "items": {
                            "$ref": "#/definitions/mygreatpackage.Data1"
                        }
                    },
                    "e": {
                        "type": "array",
                        "items": {
                            "type": "integer",
                            "minimum": -2147483648,
                            "maximum": 2147483647
                        }
                    }
                }
            }
        }
    }
