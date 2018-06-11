from os.path import isfile
from os import makedirs, listdir, environ
from subprocess import PIPE, Popen
import importlib.util
import json
import requests
from acumos_proto_viewer import get_module_logger
from acumos_proto_viewer.exceptions import SchemaNotReachable

_logger = get_module_logger(__name__)

OUTPUT_DIR = "/tmp/protofiles"
makedirs(OUTPUT_DIR, exist_ok=True)


def _gen_compiled_proto_path(model_id):
    """
    Generates the expected compiled proto path from a model_id
    """
    return "{0}/{1}_pb2.py".format(OUTPUT_DIR, model_id)


def _check_model_id_already_registered(model_id):
    """
    Checks whether a model_id already exists so we can exit immediately before doing work
    """
    from acumos_proto_viewer import data
    if isfile(_gen_compiled_proto_path(model_id)) and model_id in data.proto_data_structure:
        return True
    return False


def _compile_proto(model_id):
    """
    Invokes the protoc utility to compile a .proto file and produce a Python module.
    The generated module will be at (OUTPUT_DIR)/(model_id)_pb2.py
        NOTE: if this already exists, this function returns immediately. This is a kind of cache I suppose.
        TODO: add a flag to force a recompile
    """
    gen_module = _gen_compiled_proto_path(model_id)

    expected_proto = "{0}/{1}.proto".format(OUTPUT_DIR, model_id)
    if not isfile(expected_proto):
        _logger.error("Proto file {0} does not exist! {1} listing: {2}".format(
            expected_proto, OUTPUT_DIR, listdir(OUTPUT_DIR)))
        raise Exception("Proto file {0} does not exist".format(expected_proto))

    cmd = ["protoc", "--python_out", OUTPUT_DIR, model_id + ".proto"]
    _logger.debug("Running CMD: {0}".format(" ".join(cmd)))

    # cwd works even in Docker, I was having issues with protoc and proto_path inside docker (permissioning??)
    p = Popen(cmd, stderr=PIPE, cwd=OUTPUT_DIR)
    _, err = p.communicate()
    if p.returncode != 0:
        raise Exception(
            "A failure occurred while generating source code from protobuf: {}".format(err))

    if not isfile(gen_module):
        _logger.error("pb2.py file did not get created! {0} listing: {1}".format(
            OUTPUT_DIR, listdir(OUTPUT_DIR)))
        raise Exception(
            "An unknown failure occurred while generating Python module {}".format(gen_module))


def _load_module(module_name, path):
    """
    Imports and returns a module from path for Python 3.5+
    """
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _inject_apv_keys_into_schema(schema_entrypoint):
    """
    Injects well-known proto-viewer keys into a jsonschema.
    """
    schema_entrypoint["apv_received_at"] = {'type': 'integer'}
    schema_entrypoint["apv_model_as_string"] = {'type': 'string'}
    schema_entrypoint["apv_sequence_number"] = {'type': 'integer'}


def _protobuf_to_js(module_name):
    """
    Converts a protobuf to jsonschema and returns the generated schema as a JSON object.
    """
    pf = "{0}/{1}.proto".format(OUTPUT_DIR, module_name)
    cmd = ["protobuf-jsonschema", pf]
    p = Popen(cmd, stderr=PIPE, stdout=PIPE)
    out = p.stdout.read()
    return json.loads(out)


def _register_jsonschema(js_schema, model_id):
    """
    Makes a jsonschema known to this viz
    """
    from acumos_proto_viewer import data
    _logger.info("Registering jsonschema %s", model_id)
    data.jsonschema_data_structure[model_id] = {}
    _inject_apv_keys_into_schema(js_schema["properties"])
    data.jsonschema_data_structure[model_id]["json_schema"] = js_schema


def _register_proto(proto_name, model_id):
    """
    Makes a proto file "known" to this viz
    Later this would get done on demand when an unknown message type comes in
    by querying the catalog with the model_id.
    """
    from acumos_proto_viewer import data

    _logger.info("Registering previously unregistered proto %s", model_id)
    _compile_proto(model_id)
    data.proto_data_structure[model_id] = {}
    j_schema = _protobuf_to_js(model_id)
    data.proto_data_structure[model_id]["json_schema"] = j_schema
    data.proto_data_structure[model_id]["proto_file_name"] = proto_name
    data.proto_data_structure[model_id]["messages"] = {}

    for key in list(j_schema["definitions"].keys()):
        _inject_apv_keys_into_schema(j_schema["definitions"][key]["properties"])
        data.proto_data_structure[model_id]["messages"][key.split(
            ".")[1]] = {"properties": j_schema["definitions"][key]["properties"]}

    _logger.debug("Corresponding JSON schema is: ")
    _logger.debug(json.dumps(j_schema))


def _proto_url_to_model_id(url):
    # protoc cannot handle filenames with . in it!. It also renames "-" to "_"
    return url.split("/")[-1].replace(".", "").replace("-", "_")


def _wget_proto(url, model_id):
    """
    Downloads proto files from the specified URL for the specified message (model).
    """
    fname = model_id + ".proto"
    _logger.debug("Attempting to download {0}".format(url))
    r = requests.get(url)
    if r.status_code == 200:
        wpath = "{0}/{1}".format(OUTPUT_DIR, fname)
        with open(wpath, "w") as f:
            f.write(r.text)
        _logger.debug("{0} succesfully downloaded to {1}, modeil_id = {2}".format(
            url, wpath, model_id))
        return model_id, fname
    else:
        _logger.error("Error: unable to reach {0}".format(url))
        raise SchemaNotReachable()


def _wget_jsonschema(url, model_id):
    """
    Used to download a JSON Schema file
    """
    _logger.debug("Attempting to download {0}".format(url))
    r = requests.get(url)
    if r.status_code == 200:
        _logger.debug("{0} succesfully downloaded as {1}".format(url, model_id))
        return json.loads(r.text)
    _logger.error("Error: unable to reach {0}".format(url))
    raise SchemaNotReachable()


def _register_schema_from_url(url, schema_type, model_id):
    """
    Makes a proto file or jsonschema file known to this probe by a URL.
    The term URL here is overloaded. When the probe runs in certain scenarios,
    for example when it talks to the Acumos model connector, it is not given a
    full URl in the POST. Instead, in that scenario, it is given a partial URL,
    and the prefix is given (deployment configuration) as an ENV variable named
    "NEXUSENDPOINTURL". This function handles both cases: when it receives a full
    URL, and when it receives a partial. If it is not given a full URL, AND that
    NEXUSENDPOINTURL does not exist, this function throws a SchemaNotReachable.
    """
    # short circut if already registered
    if _check_model_id_already_registered(model_id):
        return model_id

    if url.startswith("http"):
        targeturl = url
    else:
        if "NEXUSENDPOINTURL" in environ:
            nexus_endpoint = environ["NEXUSENDPOINTURL"]
            if not nexus_endpoint.endswith("/"):
                # I have been giving conflicting examples about whether this contains a trailing /, being safe here.
                nexus_endpoint = nexus_endpoint + "/"
            targeturl = "{0}{1}".format(nexus_endpoint, url)
        else:
            raise SchemaNotReachable()

    if schema_type == "proto":
        fname = _wget_proto(targeturl, model_id)
        _register_proto(fname, model_id)
    else:
        js_schema = _wget_jsonschema(targeturl, model_id)
        _register_jsonschema(js_schema, model_id)
    return model_id


#######
# PUBLIC


def register_proto_from_url(url):
    """
    Register a proto file from a URL
    """
    model_id = _proto_url_to_model_id(url)
    return _register_schema_from_url(url, "proto", model_id)


def register_jsonschema_from_url(url, topic_name):
    """
    Register a jsonschema from a URL
    Use topic_name as model_id
    """
    return _register_schema_from_url(url, "jsonschema", topic_name)


def load_proto(model_id, cache={}):
    """
    Load a protobuf module and return it
    Memoizes
    """
    if model_id in cache:
        return cache[model_id]
    expected_path = "{0}/{1}_pb2.py".format(OUTPUT_DIR, model_id)
    module = _load_module(model_id, expected_path)
    cache[model_id] = module
    return module
