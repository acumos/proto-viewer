import hashlib
from acumos_proto_viewer import data
from acumos_proto_viewer.exceptions import ProtoNotReachable


def get_source_index(session_id, model_id, message_name, field_name=None):
    """
    Gets a ColumnDataSource index given session id, modelid, messagename, and optionally field
    """
    if field_name is None:
        hind = "{0}{1}{2}".format(session_id, model_id, message_name)
    else:
        hind = "{0}{1}{2}{3}".format(session_id, model_id, message_name, field_name)
    return hashlib.sha224(hind.encode('utf-8')).hexdigest()


def handle_data_post(headers, req_body):
    """
    Handle the  POST to /data
    """
    proto_url = headers.get("PROTO-URL", None)#the weird casing on these were told to me by the model connector team
    message_name = headers.get("Message-Name", None)
    if (proto_url is None or message_name is None):
        return 400, "Error: PROTO-URL or Message-Name header missing."
    try:
        data.inject_data(req_body, proto_url, message_name)
        return 200, req_body #Kazi has asked that due to the way the Acmos "model conector" aka "blueprint orchestrator" works, that I should return the request body that I recieved. OK..
    except ProtoNotReachable:
        return 400, "Error: {0} was not downloadable!".format(proto_url)
