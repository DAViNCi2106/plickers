"""
app/core/logging.py
===================
Structured JSON logging setup.
IMPORTANT: passwords, hashes, tokens, and full auth headers
           must NEVER appear in log output.
"""
from __future__ import annotations

import logging
import sys

try:
    from pythonjsonlogger.json import JsonFormatter  # python-json-logger >= 3
except ImportError:
    from pythonjsonlogger.jsonlogger import JsonFormatter  # type: ignore  # < 3

from app.core.config import settings

_SENSITIVE_KEYS = frozenset(
    {"password", "password_hash", "token", "authorization", "secret", "hash"}
)


class SanitisedFilter(logging.Filter):
    """Strip any log record that accidentally contains a sensitive key."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(getattr(record, "msg", "")).lower()
        for key in _SENSITIVE_KEYS:
            if key in msg:
                record.msg = "[REDACTED — sensitive field]"
                record.args = ()
                break
        return True


def setup_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    handler.addFilter(SanitisedFilter())

    root = logging.getLogger()
    root.handlers = []
    root.addHandler(handler)
    root.setLevel(level)

    # Quieten noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )
