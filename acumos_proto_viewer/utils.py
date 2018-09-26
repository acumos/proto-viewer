# Acumos - Apache 2.0


from os.path import isfile
from os import makedirs, listdir, environ
from subprocess import PIPE, Popen
import importlib.util
import json
import requests
from acumos_proto_viewer import get_module_logger
from acumos_proto_viewer.exceptions import SchemaNotReachable

_logger = get_module_logger(__name__)

# well-known probe field names
APV_RECVD = "apv_received_at"
APV_SEQNO = "apv_sequence_number"
APV_MODEL = "apv_model_as_string"

OUTPUT_DIR = "/tmp/protofiles"
makedirs(OUTPUT_DIR, exist_ok=True)


def _gen_compiled_proto_path(model_id):
    """
    Generates the expected compiled proto path from a model_id
    """
    path = "{0}/{1}_pb2.py".format(OUTPUT_DIR, model_id)
    # _logger.debug("_gen_compiled_proto_path: result is %s", path)
    return path


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
    # _logger.debug("_compile_proto: expected_proto is %s", expected_proto)
    if not isfile(expected_proto):
        _logger.error("_compile_proto: Proto file {0} does not exist! {1} listing: {2}".format(
            expected_proto, OUTPUT_DIR, listdir(OUTPUT_DIR)))
        raise Exception("Proto file {0} does not exist".format(expected_proto))

    cmd = ["protoc", "--python_out", OUTPUT_DIR, model_id + ".proto"]
    _logger.debug("_compile_proto: running CMD: %s", " ".join(cmd))

    # cwd works even in Docker, I was having issues with protoc and proto_path inside docker (permissioning??)
    p = Popen(cmd, stderr=PIPE, cwd=OUTPUT_DIR)
    _, err = p.communicate()
    if p.returncode != 0:
        raise Exception(
            "A failure occurred while generating source code from protobuf: {}".format(err))

    if not isfile(gen_module):
        _logger.error("_compile_proto: expected file {0} did not get created! {1} listing: {12}".format(gen_module, OUTPUT_DIR, listdir(OUTPUT_DIR)))
        raise Exception(
            "An unknown failure occurred while generating Python module {}".format(gen_module))


def _inject_apv_keys_into_schema(schema_entrypoint):
    """
    Injects well-known proto-viewer keys into a jsonschema.
    """
    schema_entrypoint[APV_MODEL] = {'type': 'string'}
    schema_entrypoint[APV_RECVD] = {'type': 'integer'}
    schema_entrypoint[APV_SEQNO] = {'type': 'integer'}


def _protobuf_to_js(module_name):
    """
    Converts a protobuf to jsonschema and returns the generated schema as a JSON object.
    """
    pf = "{0}/{1}.proto".format(OUTPUT_DIR, module_name)
    cmd = ["protobuf-jsonschema", pf]
    _logger.debug("_protobuf_to_js: running CMD: %s", " ".join(cmd))
    p = Popen(cmd, stderr=PIPE, stdout=PIPE)
    out = p.stdout.read()
    return json.loads(out)


def _register_jsonschema(js_schema, model_id):
    """
    Makes a jsonschema known to this viz
    This was added to benefit ONAP/DCAE and is lightly tested at best.
    TODO: Does not inject APV keys into messages.
    """
    # import here to avoid circular dependency
    from acumos_proto_viewer import data

    _logger.info("_register_jsonschema: registering for model_id {0}".format(model_id))
    data.jsonschema_data_structure[model_id] = {}
    _inject_apv_keys_into_schema(js_schema["properties"])
    data.jsonschema_data_structure[model_id]["json_schema"] = js_schema


def _flatten_message_fields(json_schema, msg_name, prefix=None):
    """
    Builds and returns a dict of field names -> props in the message;
    e.g., keys "i, j, k.a, k.b".  Recurses on nested messages.
    The prefix should be null/empty on first invocation; i.e., root.
    """
    flat_field_props = {}
    for field_name in json_schema["definitions"][msg_name]["properties"]:
        qual_field_name = field_name if prefix is None or prefix == "" else prefix + "." + field_name
        field_attr = json_schema["definitions"][msg_name]["properties"][field_name]
        if '$ref' in field_attr:
            # it's a nested message
            nested_msg_name = field_attr["$ref"].split("/")[2]
            nested_dict = _flatten_message_fields(json_schema, nested_msg_name, prefix=qual_field_name)
            flat_field_props = {**flat_field_props, **nested_dict}
        else:
            # it's a scalar, only property is type
            flat_field_props[qual_field_name] = field_attr

    _logger.debug("_flatten_message_fields: msg {0} yields {1}".format(msg_name, flat_field_props))
    return flat_field_props


def _register_proto(proto_name, model_id):
    """
    Makes a proto file known to this viz.
    Later this would get done on demand when an unknown message type
    arrives by querying the catalog with the model_id.
    """
    # import here to avoid circular dependency
    from acumos_proto_viewer import data

    _logger.info("_register_proto: registering for model_id {0}".format(model_id))
    _compile_proto(model_id)
    data.proto_data_structure[model_id] = {}
    j_schema = _protobuf_to_js(model_id)
    _logger.debug("_register_proto: corresponding JSON schema: {0}".format(json.dumps(j_schema)))
    data.proto_data_structure[model_id]["json_schema"] = j_schema
    data.proto_data_structure[model_id]["proto_file_name"] = proto_name
    data.proto_data_structure[model_id]["messages"] = {}

    for msg_name in list(j_schema["definitions"].keys()):
        # json schema definition key is package.message
        msg_name_no_pkg = msg_name.split(".")[1]
        # this is unnecessary for nested messages, but we don't know that here
        _inject_apv_keys_into_schema(j_schema["definitions"][msg_name]["properties"])
        # field names from protobuf definition
        json_props = j_schema["definitions"][msg_name]["properties"]
        flat_json_props = _flatten_message_fields(j_schema, msg_name)
        data.proto_data_structure[model_id]["messages"][msg_name_no_pkg] = {
            "properties": json_props,
            "properties_flat": flat_json_props
        }


def _proto_url_to_model_id(url):
    """
    Removes special characters from the URL (/.-:) to return a unique ID.
    protoc cannot handle filenames with . in them!
    """
    model_id = url.replace(":", "_").replace("/", "_").replace("-", "_").replace(".", "_")
    # _logger.debug("_proto_url_to_model_id: result is %s", model_id)
    return model_id


def _wget_proto(url, model_id):
    """
    Fetches a proto file from the specified URL for the specified message (model ID).
    Writes the content to a file.  Returns tuple of model ID and file name.
    """
    fname = model_id + ".proto"
    _logger.debug("_wget_proto: GET of %s", url)
    r = requests.get(url)
    if r.status_code == 200:
        wpath = "{0}/{1}".format(OUTPUT_DIR, fname)
        with open(wpath, "w") as f:
            f.write(r.text)
        _logger.debug("_wget_proto: model_id {0}, url {1} downloaded to {2}".format(model_id, url, wpath))
        return model_id, fname
    else:
        _logger.error("_wget_proto failed: unable to reach %s", url)
        raise SchemaNotReachable()


def _wget_jsonschema(url, model_id):
    """
    Fetches a JSON Schema file from the specified URL for the specified message (model ID).
    Loads the resulting text as JSON and returns the object.
    """
    _logger.debug("_wget_jsonschema: attempting to download %s", url)
    r = requests.get(url)
    if r.status_code == 200:
        _logger.debug("_wget_jsonschema: model_id {0}, url {1} downloaded".format(model_id, url))
        return json.loads(r.text)
    _logger.error("_wget_jsonschema failed: unable to reach %s", url)
    raise SchemaNotReachable()


def _register_schema_from_url(url, schema_type, model_id):
    """
    Makes a proto file or jsonschema file known to this probe by a URL.
    The term URL here is overloaded. When the probe runs in certain scenarios,
    for example when it talks to the Acumos model connector, it is not given a
    full URL in the POST. Instead, in that scenario, it is given a partial URL,
    and the prefix is given (deployment configuration) as an ENV variable named
    "NEXUSENDPOINTURL". This function handles both cases: when it receives a full
    URL, and when it receives a partial. If it is not given a full URL, AND that
    NEXUSENDPOINTURL does not exist, this function throws a SchemaNotReachable.
    Returns the model ID.
    """
    # _logger.debug("_register_schema_from_url: checking model_id %s", model_id)
    # short circut if already registered
    if _check_model_id_already_registered(model_id):
        return model_id

    if url.startswith("http"):
        _logger.debug("_register_schema_from_url: complete URL, using %s", url)
        targeturl = url
    else:
        if "NEXUSENDPOINTURL" in environ:
            nexus_endpoint = environ["NEXUSENDPOINTURL"]
            _logger.debug("_register_schema_from_url: partial URL, extending with %s", nexus_endpoint)
            if not nexus_endpoint.endswith("/"):
                # conflicting examples about whether this contains a trailing /, be safe here
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
    Registers a proto file from a URL.
    Raises SchemaNotReachable if the URL is invalid.
    """
    model_id = _proto_url_to_model_id(url)
    return _register_schema_from_url(url, "proto", model_id)


def register_jsonschema_from_url(url, topic_name):
    """
    Registers a jsonschema from a URL
    Uses topic_name as model_id
    """
    return _register_schema_from_url(url, "jsonschema", topic_name)


def load_module(module_name, path):
    """
    Imports and returns a module from path for Python 3.5+.
    """
    _logger.debug("load_module: importing module name %s", module_name)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_proto(model_id, cache={}):
    """
    Loads a protobuf module and returns it
    Memoizes
    """
    if model_id in cache:
        return cache[model_id]
    expected_path = "{0}/{1}_pb2.py".format(OUTPUT_DIR, model_id)
    # _logger.debug("load_proto: checking cache path %s", expected_path)
    module = load_module(model_id, expected_path)
    cache[model_id] = module
    return module


def get_message_data(msg_dict, field_name):
    """
    Extracts data from a JSON dict using a field name,
    which may refer to a field in a nested message ("i.x").
    Calls self on nested field names.
    Returns none if field is not found.
    """
    if field_name in msg_dict:
        return msg_dict[field_name]
    index = field_name.find(".")
    if index > 0:
        prefix = field_name[:index]
        suffix = field_name[index + 1:]
        if prefix in msg_dict:
            return get_message_data(msg_dict[prefix], suffix)
        else:
            _logger.warning("get_message_data: first component not found {0}".format(prefix))
    # _logger.warning("_get_message_data: unknown field {0}".format(field_name))
    return None
