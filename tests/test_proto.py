# Acumos - Apache 2.0


from types import ModuleType
from acumos_proto_viewer.utils import register_proto_from_url, load_proto, _protobuf_to_js, get_message_data
from acumos_proto_viewer import data
import test_constants


def test_register_load(monkeypatch, monkeyed_requests_get, cleanuptmp):
    monkeypatch.setattr('requests.get', monkeyed_requests_get)
    register_proto_from_url(test_constants.test_proto_url)
    register_proto_from_url(test_constants.test_proto_with_arrays_url)
    assert(test_constants.test_proto_mid in data.list_known_protobufs())
    assert(test_constants.test_proto_with_arrays_mid in data.list_known_protobufs())
    test_pb2 = load_proto(test_constants.test_proto_mid)
    test_pb2 = load_proto(test_constants.test_proto_mid)  # cache hit

    assert isinstance(test_pb2, ModuleType)

    test2_pb2 = load_proto(test_constants.test_proto_with_arrays_mid)
    test2_pb2 = load_proto(test_constants.test_proto_with_arrays_mid)  # cache hit

    assert isinstance(test2_pb2, ModuleType)

    cleanuptmp()


def test_protobuf_to_js(monkeypatch, monkeyed_requests_get, cleanuptmp):
    monkeypatch.setattr('requests.get', monkeyed_requests_get)
    register_proto_from_url(test_constants.test_proto_url)
    register_proto_from_url(test_constants.test_proto_with_arrays_url)
    assert(test_constants.test_proto_mid in data.list_known_protobufs())
    assert(test_constants.test_proto_with_arrays_mid in data.list_known_protobufs())

    js = _protobuf_to_js(test_constants.test_proto_mid)
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

    js = _protobuf_to_js(test_constants.test_proto_with_arrays_mid)
    print(js)
    assert(js == {
        "definitions": {
            "YKhGXjKWHYsPwKJFfEPnmoHOkDkPKBxX.ImageTagSet": {
                "title": "ImageTagSet",
                "type": "object",
                "properties": {
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
                    }
                }
            }
        }
    })
    cleanuptmp()


def test_get_message_data():
    # Protobuf converted to JSON looks like this
    pbmsg = {
        "i": 1,
        "j": 2,
        "k": {
            "x": 3,
            "y": 4
        }
    }
    assert 1 == get_message_data(pbmsg, "i")
    assert 3 == get_message_data(pbmsg, "k.x")
