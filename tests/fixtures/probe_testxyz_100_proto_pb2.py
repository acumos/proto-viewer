# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: probe_testxyz_100_proto.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='probe_testxyz_100_proto.proto',
  package='whatisthisfor',
  syntax='proto3',
  serialized_pb=_b('\n\x1dprobe_testxyz_100_proto.proto\x12\rwhatisthisfor\"*\n\x07XYZData\x12\t\n\x01x\x18\x01 \x01(\x02\x12\t\n\x01y\x18\x02 \x01(\x02\x12\t\n\x01z\x18\x03 \x01(\x02\x62\x06proto3')
)




_XYZDATA = _descriptor.Descriptor(
  name='XYZData',
  full_name='whatisthisfor.XYZData',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='x', full_name='whatisthisfor.XYZData.x', index=0,
      number=1, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='y', full_name='whatisthisfor.XYZData.y', index=1,
      number=2, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='z', full_name='whatisthisfor.XYZData.z', index=2,
      number=3, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=48,
  serialized_end=90,
)

DESCRIPTOR.message_types_by_name['XYZData'] = _XYZDATA
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

XYZData = _reflection.GeneratedProtocolMessageType('XYZData', (_message.Message,), dict(
  DESCRIPTOR = _XYZDATA,
  __module__ = 'probe_testxyz_100_proto_pb2'
  # @@protoc_insertion_point(class_scope:whatisthisfor.XYZData)
  ))
_sym_db.RegisterMessage(XYZData)


# @@protoc_insertion_point(module_scope)