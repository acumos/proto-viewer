from os.path import isfile
from os import makedirs, listdir, environ
from subprocess import PIPE, Popen
import importlib.util
import json
import requests
from acumos_proto_viewer import get_module_logger
from acumos_proto_viewer.exceptions import ProtoNotReachable

_logger = get_module_logger(__name__)

OUTPUT_DIR = "/tmp/protofiles"
makedirs(OUTPUT_DIR, exist_ok=True)


def _gen_compiled_proto_path(model_id):
    """
    Generate the expected compiled proto path from a model_id
    """
    return "{0}/{1}_pb2.py".format(OUTPUT_DIR, model_id)


def _check_modelid_already_registered(model_id):
    """
    Checks whether a model_id already exists so we can exit immediately before doing work
    """
    if isfile(_gen_compiled_proto_path(model_id)):
        _logger.debug("pb2 module already existed, returning immediately")
        return True
    return False


def _compile_proto(model_id):
    """
    The generated module will be at (OUTPUT_DIR)/(model_id)_pb2.py
        NOTE: if this already exists, this function returns immediately. THis is a kind of cache I suppose.
        TODO: add a flag to force a recompile
    """
    gen_module = _gen_compiled_proto_path(model_id)
    if _check_modelid_already_registered(model_id):
        return gen_module

    expected_proto = "{0}/{1}.proto".format(OUTPUT_DIR, model_id)
    if not isfile(expected_proto):
        _logger.error("Proto file {0} does not exist! {1} listing: {2}".format(expected_proto, OUTPUT_DIR, listdir(OUTPUT_DIR)))
        raise Exception("Proto file {0} does not exist".format(expected_proto))

    cmd = ["protoc", "--python_out", OUTPUT_DIR, model_id + ".proto"]
    _logger.debug("Running CMD: {0}".format(" ".join(cmd)))

    p = Popen(cmd, stderr=PIPE, cwd=OUTPUT_DIR) #cwd works even in Docker, I was having issues with protoc and proto_path inside docker (permissioning??)
    _, err = p.communicate()
    if p.returncode != 0:
        raise Exception("A failure occurred while generating source code from protobuf: {}".format(err))

    if not isfile(gen_module):
        _logger.error("pb2.py file did not get created! {0} listing: {1}".format(OUTPUT_DIR, listdir(OUTPUT_DIR)))
        raise Exception("An unknown failure occurred while generating Python module {}".format(gen_module))


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
    pf = "{0}/{1}.proto".format(OUTPUT_DIR, module_name)
    cmd = ["protobuf-jsonschema", pf]
    p = Popen(cmd, stderr=PIPE, stdout=PIPE)
    out = p.stdout.read()
    return json.loads(out)


def _register_proto(proto_name, model_id):
    """
    Makes a proto file "known" to this viz
    Later this would get done on demand when an unknown message type comes in by quering the catalog with the modelid
    """
    from acumos_proto_viewer import data
    _logger.info("Registering proto %s", model_id)
    _compile_proto(model_id)
    data.proto_data_structure[model_id] = {}
    j_schema = _protobuf_to_js(model_id)
    data.proto_data_structure[model_id]["json_schema"] = j_schema
    data.proto_data_structure[model_id]["proto_file_name"] = proto_name
    data.proto_data_structure[model_id]["messages"] = {}

    for key in list(j_schema["definitions"].keys()):
        #Inject a field for the timestamp to live. Not sure how I feel about this, but I don't see a better way to timestamp every recieved record right now.
        j_schema["definitions"][key]["properties"]["apv_recieved_at"] = {'type': 'timestamp'}
        j_schema["definitions"][key]["properties"]["apv_model_as_string"] = {'type': 'string'}
        j_schema["definitions"][key]["properties"]["apv_sequence_number"] = {'type': 'int'}
        data.proto_data_structure[model_id]["messages"][key.split(".")[1]] = {"properties": j_schema["definitions"][key]["properties"]}


def _proto_url_to_modelid(url):
    return url.split("/")[-1].replace(".", "").replace("-", "_") #protoc cannot handle filenames with . in it!. It also renames "-" to "_"


def _wget_proto(url):
    """
    Used to download the proto files
    """
    model_id = _proto_url_to_modelid(url)
    fname = model_id + ".proto"
    if _check_modelid_already_registered(model_id):
        return model_id, fname
    else:
        _logger.debug("Attempting to download {0}".format(url))
        r = requests.get(url)
        if r.status_code == 200:
            wpath = "{0}/{1}".format(OUTPUT_DIR, fname)
            with open(wpath, "w") as f:
                f.write(r.text)
            _logger.debug("{0} succesfully downloaded to {1}, modeil_id = {2}".format(url, wpath, model_id))
            return model_id, fname
        else:
            _logger.error("Error: unable to reach {0}".format(url))
            raise ProtoNotReachable()


#######
# PUBLIC
def register_proto_from_url(url):
    """
    Makes a proto file known to this probe by a URL.
    The term URL here is overloaded. When the probe runs in certain scenarios, for example when it talks to the Acumos model connector, it is not given a full URl in the POST.
    Instead, in that scenario, it is given a partial URL, and the prefix is given when the probe is deployed as an ENV variable under "NEXUSENDPOINTURL".
    This function handles both cases: when it recieves a full URL, and when it recieves a partial.
    If it is not given a full URL, AND that NEXUSENDPOINTURL does not exist, this function throws a ProtoNotReachable
    """
    if url.startswith("http"):
        targeturl = url
    else:
        if "NEXUSENDPOINTURL" in environ:
            nexus_endpoint = environ["NEXUSENDPOINTURL"]
            if not nexus_endpoint.endswith("/"):
                nexus_endpoint = nexus_endpoint + "/" #I have been giving conflicting examples about whether this contains a trailing /, being safe here.
            targeturl = "{0}{1}".format(nexus_endpoint, url)
        else:
            raise ProtoNotReachable()
    modelid, fname = _wget_proto(targeturl)
    _register_proto(fname, modelid)
    return modelid


def list_compiled_proto_names():
    """
    Return the list of module names that have been compiled in this instance
    """
    return [f[0:-7] for f in listdir(OUTPUT_DIR) if f.endswith("_pb2.py")]


def load_proto(model_id, cache={}):
    """
    Load a protobuf module and return it
    Memoizes
    """
    if model_id in cache:
        return cache[model_id]
    else:
        expected_path = "{0}/{1}_pb2.py".format(OUTPUT_DIR, model_id)
        m = _load_module(model_id, expected_path)
        cache[model_id] = m
        return m
