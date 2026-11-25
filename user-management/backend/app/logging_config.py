"""Logging setup for the whole application, done once at startup.

Every log line includes the ID of the request it belongs to:

    2026-11-25 10:15:02 WARNING [app.services.auth_service] request_id=3f2c... Login failed: wrong password account_id=4
    2026-11-25 10:15:02 INFO [app.requests] request_id=3f2c... POST /auth/login 401 98ms

The middleware stores the ID in a context variable (request_id_var) when a
request starts. A context variable is like a global, but each request (each
asyncio task / worker thread) sees its own value, so concurrent requests never
mix up their IDs. Log lines written outside a request show request_id=-.
"""

import logging
import os
from contextvars import ContextVar

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] request_id=%(request_id)s %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_default_record_factory = logging.getLogRecordFactory()


def _record_factory(*args: object, **kwargs: object) -> logging.LogRecord:
    """Create every log record with a request_id attribute, from any logger."""
    record = _default_record_factory(*args, **kwargs)
    record.request_id = request_id_var.get()
    return record


def _read_bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes"}


def configure_logging() -> None:
    """Set up the root logger once, for the whole application."""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()

    logging.setLogRecordFactory(_record_factory)
    logging.basicConfig(
        level=getattr(logging, level_name, logging.INFO),
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
    )

    # LOG_SQL=true prints every SQL statement SQLAlchemy sends. Only for
    # debugging: it is noisy, and query parameters can contain user data.
    if _read_bool("LOG_SQL"):
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
