import logging


def get_module_logger(mod_name):
    """
    Gets a logger for the named module.
    Configures a stream handler and formatter; uses level DEBUG.
    To use this, do logger = get_module_logger(__name__)
    """
    logger = logging.getLogger(mod_name)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(name)-12s] %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    # avoid double output, do not propagate to the default stdout handler
    logger.propagate = False
    return logger
