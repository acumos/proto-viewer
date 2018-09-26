# Acumos - Apache 2.0


test_proto_url = "http://myserver.com/fakemodelid/1.0.0/fakemodelid-1.0.0-proto"
test_proto_mid = "http___myserver_com_fakemodelid_1_0_0_fakemodelid_1_0_0_proto"
test_proto_txt = """
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


test_proto_with_arrays_url = "http://myserver.com/fakemodelidwitharrays/1.0.0/fakemodelidwitharrays-1.0.0-proto"
test_proto_with_arrays_mid = "http___myserver_com_fakemodelidwitharrays_1_0_0_fakemodelidwitharrays_1_0_0_proto"
test_proto_with_arrays_txt = """
syntax = "proto3";
package YKhGXjKWHYsPwKJFfEPnmoHOkDkPKBxX;

service Model {
  rpc classify (ImageTagSet) returns (ImageTagSet);
}

message ImageTagSet {
  repeated int64 image = 1;
  repeated string tag = 2;
  repeated double score = 3;
}
"""

test_probe_fake_schema_url = "http://myserver.com/probe_testschema/1.0.0/probe_testschema-1.0.0"
test_probe_fake_schema_txt = """
{
    "$schema": "http://json-schema.org/draft-04/schema#",
    "properties": {
      "value": {
        "type": "number",
        "description": ""
      }
    },
    "required": ["value"],
    "type": "object"
  }
"""
