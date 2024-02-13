import logging
import os


def setup_logging():
    CONSOLE_LOG_LVL = os.getenv("CONSOLE_LOG_LVL", "DEBUG")
    logging.basicConfig(level=CONSOLE_LOG_LVL)

    # Remove all handlers associated with the root logger
    logger = logging.getLogger()
    for handler in logger.handlers[:]:  # Iterate over a copy of the list
        logger.removeHandler(handler)

    # Create a new handler with the desired settings
    new_handler = logging.StreamHandler()
    new_format = logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s")
    new_handler.setFormatter(new_format)

    # Add the new handler to the logger
    logger.addHandler(new_handler)

    _mute_httpx_logging()
    _mute_telegram_logging()
    _mute_sqlalchemy_logging()


def _mute_httpx_logging():
    logging.getLogger("httpx").setLevel(logging.WARNING)


def _mute_telegram_logging():
    logging.getLogger("telegram.ext.Application").setLevel(logging.WARNING)


def _mute_sqlalchemy_logging():
    logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
