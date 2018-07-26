import hashlib
from acumos_proto_viewer import data, get_module_logger
from acumos_proto_viewer.exceptions import SchemaNotReachable

_logger = get_module_logger(__name__)

# Constants used in the GUI to name bokeh models
DEFAULT_UNSELECTED = "Please Select"
MODEL_SELECTION = "modelselec"
AFTER_MODEL_SELECTION = "aftermodelselec"
MESSAGE_SELECTION = "messageselec"
GRAPH_SELECTION = "graphselec"
GRAPH_OPTIONS = ["Please Select", "line", "scatter", "step", "image", "table", "raw"]
FIGURE_MODEL = "thefig"
FIELD_SELECTION = "fieldsselection"
IMAGE_MIME_SELECTION = "imagemimeselection"
IMAGE_SELECTION = "imageselect"
MIME_SELECTION = "mimeselection"
X_AXIS_SELECTION = "xaxisselect"
Y_AXIS_SELECTION = "yaxisselect"
COLUMN_MULTISELECT = "colmultiselect"
COLUMN_SELECTION = "colselect"


def get_modelid_messagename_type(curdoc):
    """
    Given the current document, returns the model_id selected and messagename/type
    """
    model_id = curdoc.get_model_by_name(MODEL_SELECTION).value
    if model_id.startswith("protobuf_"):
        model_id = model_id.replace("protobuf_", "")
        message_name = curdoc.get_model_by_name(MESSAGE_SELECTION).value if curdoc.get_model_by_name(MESSAGE_SELECTION) else None
        model_type = "protobuf"
    else:
        model_id = model_id.replace("topic_", "")
        message_name = "{0}_messages".format(model_id)
        model_type = "jsonschema"
    return model_id, message_name, model_type


def get_model_properties(model_id, message_name, model_type):
    """
    Gets model properties
    """
    return data.proto_data_structure[model_id]["messages"][message_name]["properties"] if model_type == "protobuf" else data.jsonschema_data_structure[model_id]["json_schema"]["properties"]


def get_source_index(session_id, model_id, message_name, field_name=None):
    """
    Gets a ColumnDataSource index given session id, modelid, messagename, and optionally field
    """
    if field_name is None:
        hind = "{0}{1}{2}".format(session_id, model_id, message_name)
    else:
        hind = "{0}{1}{2}{3}".format(
            session_id, model_id, message_name, field_name)
    return hashlib.sha224(hind.encode('utf-8')).hexdigest()


def handle_data_post(headers, req_body):
    """
    Handles the POST to /data. Uses metadata to discover the supporting protocol buffer definition.
    """
    proto_url = headers.get("PROTO-URL", None)  # the weird casing on these were told to me by the model connector team
    message_name = headers.get("Message-Name", None)
    # this level of chattiness is not desirable for typical use
    # _logger.debug("handle_data_post: proto_url %s message_name %s", proto_url, message_name)
    if (proto_url is None or message_name is None):
        return 400, "Error: PROTO-URL or Message-Name header missing."
    try:
        res = data.inject_data(req_body, proto_url, message_name)
        # Kazi has asked that due to the way the Acmos "model conector" aka "blueprint orchestrator" works,
        # that I should return the request body that I received
        if res:
            return 200, req_body
        else:
            return 400, req_body
    except SchemaNotReachable:
        _logger.error("handle_data_post: failed to download def for url %s", proto_url)
        return 400, "Error: {0} was not downloadable!".format(proto_url)


def handle_onap_mr_put(headers, topic_name):
    """
    Handles the PUT to /onap_topic_subscription
    """
    server_hostname = headers.get("server-hostname")
    server_port = headers.get("server-port")
    schema_url = headers.get("schema-url")
    # this level of chattiness is not desirable for typical use
    # _logger.debug("handle_onap_mr_put: server_hostname %s port %s schema url %s", server_hostname, server_port, schema_url)
    if (server_hostname is None or server_port is None or schema_url is None):
        return 400, "Error: Required header missing."
    try:
        url = "http://{0}:{1}/events/{2}".format(server_hostname, server_port, topic_name)
        _logger.debug("handle_onap_mr_put: constructed URL %s", url)
        data.setup_mr_subscription(url, schema_url, topic_name)
    except SchemaNotReachable:
        return 400, "Error: {0} was not downloadable!".format(schema_url)

    return 200, ""


def handle_onap_mr_delete(topic_name):
    """
    Remove a message-router subscription
    """
    existed = data.delete_mr_subscription(topic_name)
    if existed:
        return 200, ""
    return 404, "{0} was not registered".format(topic_name)
