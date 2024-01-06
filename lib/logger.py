import logging
import os

from dotenv import load_dotenv


def get_logger(name):
    load_dotenv()
    LOG_LVL = os.getenv("LOG_LVL", "INFO")
    CONSOLE_LOG_LVL = os.getenv("CONSOLE_LOG_LVL", "ERROR")
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LVL)

    handler = logging.StreamHandler()
    handler.setLevel(CONSOLE_LOG_LVL)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s:\n %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    sqlalchemy_logger = logging.getLogger("sqlalchemy")  # Not in usage
    sqlalchemy_logger.setLevel(logging.ERROR)
    sqlalchemy_logger.addHandler(handler)

    return logger
