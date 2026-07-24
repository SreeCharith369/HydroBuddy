import logging
from pathlib import Path

from utils.resources import resource_path

LOG_DIR = resource_path("logs")
LOG_FILE = LOG_DIR / "hydrobuddy.log"
LOGGER_NAME = "hydrobuddy"

logger = logging.getLogger(LOGGER_NAME)


def configure_logging() -> logging.Logger:
    """Configure and return the shared HydroBuddy logger."""

    LOG_DIR.mkdir(exist_ok=True)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not any(isinstance(handler, logging.FileHandler) for handler in logger.handlers):
        handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        logger.addHandler(handler)

    return logger
