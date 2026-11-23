import logging
import os

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging() -> None:
    """Set up the root logger once, for the whole application."""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=getattr(logging, level_name, logging.INFO), format=LOG_FORMAT)
