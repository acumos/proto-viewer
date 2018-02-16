from tempfile import TemporaryDirectory
import base64
from os.path import dirname, isfile, join as path_join
from os import makedirs, listdir
from subprocess import PIPE, Popen
import shutil
import sys
import importlib.util
import configparser
import json
from shutil import copyfile
from acumos_proto_viewer import get_module_logger

_logger = get_module_logger(__name__)

def _get_out_dir(config_cache = {}):
    """"
    Read config file to see where compiled protos should go
    """
    #try to memoize so we don't have to instantiate a new config_parser every time
    k = "out_dir"
    if k not in config_cache:
        config = configparser.ConfigParser()
        config.read(".config")
        config_cache[k] = config["general"]["compiled_proto_output"]
    return config_cache[k]

def _compile_proto(proto_dir, proto_name, model_id):
    """
    The .proto file is expected to be at (proto_dir)/(proto_name).proto
    The generated module will be at (out_dir)/(model_id)_pb2.py
        NOTE: if this already exists, this function returns immediately. THis is a kind of cache I suppose.
        TODO: add a flag to force a recompile
    """
    out_dir = _get_out_dir()
    pf = "{0}/{1}.proto".format(out_dir, model_id)
    shutil.copy("{0}/{1}.proto".format(proto_dir, proto_name), pf)
    gen_module = "{0}/{1}_pb2.py".format(out_dir, model_id)

    if isfile(gen_module):
        _logger.debug("pb2 module already existed, returning immediately")
        return gen_module

    if not isfile(pf):
        raise Exception("The file {0} is not a file or does not exist".format(pf))

    cmd = ["protoc", "--python_out", out_dir, "--proto_path", out_dir, pf]
    p = Popen(cmd, stderr=PIPE)
    _, err = p.communicate()
    if p.returncode != 0:
        raise Exception("A failure occurred while generating source code from protobuf: {}".format(err))
    if not isfile(gen_module):
        raise Exception("An unknown failure occurred while generating Python module {}".format(gen_module_path))

def _load_module(module_name, path):
    """
    Imports and returns a module from path for Python 3.5+
    """
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _protobuf_to_js(module_name):
    """
    Converts a protobuf to jsonschema
    """
    out_dir = _get_out_dir()
    pf = "{0}/{1}.proto".format(out_dir, module_name)
    cmd = ["protobuf-jsonschema", pf]
    p = Popen(cmd, stderr=PIPE, stdout=PIPE)
    out = p.stdout.read()
    return json.loads(out)

"""
PUBLIC
"""

def register_proto(proto_dir, proto_name, model_id):
   """
   Makes a proto file "known" to this viz
   Later this would get done on demand when an unknown message type comes in by quering the catalog with the modelid
   """
   from acumos_proto_viewer import data
   _logger.info("Registering proto {0}/{1}".format(proto_dir, proto_name))
   _compile_proto(proto_dir, proto_name, model_id)
   data.proto_data_structure[model_id] = {}
   js = _protobuf_to_js(model_id)
   data.proto_data_structure[model_id]["json_schema"] = js
   data.proto_data_structure[model_id]["proto_file_name"] = proto_name
   data.proto_data_structure[model_id]["messages"] = {}

   for k in list(js["definitions"].keys()):
       #Inject a field for the timestamp to live. Not sure how I feel about this, but I don't see a better way to timestamp every recieved record right now.
       js["definitions"][k]["properties"]["apv_recieved_at"] = {'type' : 'timestamp'}
       js["definitions"][k]["properties"]["apv_model_as_string"] = {'type' : 'string'}
       js["definitions"][k]["properties"]["apv_sequence_number"] = {'type' : 'int'}
       data.proto_data_structure[model_id]["messages"][k.split(".")[1]] = {"properties" : js["definitions"][k]["properties"]}

def list_compiled_proto_names():
    """
    Return the list of module names that have been compiled in this instance
    """
    return [f[0:-7] for f in listdir(_get_out_dir()) if f.endswith("_pb2.py")]

def load_proto(model_id, cache={}):
    """
    Load a protobuf module and return it
    Memoizes
    """
    if model_id in cache:
        return cache[model_id]
    else:
        out_dir = _get_out_dir()
        expected_path = "{0}/{1}_pb2.py".format(out_dir, model_id)
        m = _load_module(model_id, expected_path)
        cache[model_id] = m
        return m

#def base_64_to_datauri(b64s):
#    return 'data:image/png;base64,'+ b64s

#def image_bytes_to_datauri(imagebytes, mime):
#    """
#    Takes raw image bytestream and returns a browser-renderable-datauri string
#    """
#    uri = b'data:image/'
#    uri += mime.encode() #bokeh sends the dropdown selection
#    uri += b';base64,'
#    uri += base64.b64encode(imagebytes)
#    return uri.decode()
