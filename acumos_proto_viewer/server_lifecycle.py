from acumos_proto_viewer import get_module_logger

_logger = get_module_logger(__name__)


def on_server_loaded(server_context):
    ''' If present, this function is called when the server first starts. '''
    _logger.debug("on_server_loaded called")


def on_server_unloaded(server_context):
    ''' If present, this function is called when the server shuts down. '''
    _logger.debug("on_server_unloaded called")


def on_session_created(session_context):
    ''' If present, this function is called when a session is created. '''
    _logger.debug("on_server_created called")


def on_session_destroyed(session_context):
    ''' If present, this function is called when a session is closed. '''
    sid = session_context.id
    _logger.debug("on_session_destroyed called for session_id {0}".format(sid))
