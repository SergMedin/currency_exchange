import logging


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setLevel(logging.ERROR)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s:\n %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    sqlalchemy_logger = logging.getLogger('sqlalchemy')
    sqlalchemy_logger.setLevel(logging.DEBUG)
    sqlalchemy_logger.addHandler(handler)

    return logger
