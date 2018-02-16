from acumos_proto_viewer.utils import register_proto, load_proto, _protobuf_to_js
from types import ModuleType
import os

register_proto(os.path.abspath(os.path.dirname(__file__)), "test_paul", "fakemodelid")

def test_register_load():
    test_pb2 = load_proto("fakemodelid")
    test_pb2 = load_proto("fakemodelid") #cache hit
    assert isinstance(test_pb2, ModuleType)

def test_protobuf_to_js():
    js = _protobuf_to_js("fakemodelid")
    assert js == {
       "definitions":{
          "testpaul.Data1":{
             "title":"Data1",
             "type":"object",
             "properties":{
                "a":{
                   "type":"number"
                },
                "b":{
                   "type":"number"
                },
                "c":{
                   "type":"integer",
                   "minimum":-2147483648,
                   "maximum":2147483647
                },
                "d":{
                   "type":"integer",
                   "minimum":-9007199254740991,
                   "maximum":9007199254740991
                },
                "e":{
                   "type":"boolean"
                },
                "f":{
                   "type":"string"
                },
                "g":{
                   "type":"string"
                }
             }
          },
          "testpaul.Data2":{
             "title":"Data2",
             "type":"object",
             "properties":{
                "a":{
                   "$ref":"#/definitions/testpaul.Data1"
                },
                "b":{
                   "type":"object",
                   "additionalProperties":{
                      "$ref":"#/definitions/testpaul.Data1"
                   }
                },
                "c":{
                   "type":"object",
                   "additionalProperties":{
                      "type":"integer",
                      "minimum":-2147483648,
                      "maximum":2147483647
                   }
                },
                "d":{
                   "type":"array",
                   "items":{
                      "$ref":"#/definitions/testpaul.Data1"
                   }
                },
                "e":{
                   "type":"array",
                   "items":{
                      "type":"integer",
                      "minimum":-2147483648,
                      "maximum":2147483647
                   }
                }
             }
          }
       }
    }


