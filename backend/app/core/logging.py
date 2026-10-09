"""Structured JSON logging with a privacy allowlist.

Privacy rules (see docs/PLAN.md §8):
- Log records carry structured fields only through ``extra={"fields": {...}}``.
- Only keys in ``ALLOWED_FIELDS`` are emitted; everything else is dropped.
- User message text, extracted spans, client IPs and raw session IDs are never
  passed to the logger. As a second line of defence every string is scrubbed
  for e-mail addresses and long digit sequences.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

ALLOWED_FIELDS = frozenset(
    {
        "request_id",
        "method",
        "route",
        "status",
        "duration_ms",
        "session",
        "outcome",
        "rule_ids",
        "error_code",
        "exc_type",
        "component",
        "version",
        "count",
    }
)

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
_PHONE_OR_ID = re.compile(r"\+?\d[\d\s().-]{6,}\d")


def scrub(text: str) -> str:
    """Remove e-mail addresses and long digit sequences (phone numbers, IDs)."""
    text = _EMAIL.sub("[email]", text)
    return _PHONE_OR_ID.sub("[number]", text)


def hash_session_id(session_id: str, salt: str) -> str:
    """Short, salted, one-way identifier for correlating log lines of a session."""
    digest = hashlib.sha256(f"{salt}:{session_id}".encode()).hexdigest()
    return digest[:12]


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return scrub(value)
    if isinstance(value, list | tuple | set | frozenset):
        return [_clean(v) for v in value]
    if isinstance(value, int | float | bool) or value is None:
        return value
    return scrub(str(value))


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "event": scrub(record.getMessage()),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            for key, value in fields.items():
                if key in ALLOWED_FIELDS:
                    payload[key] = _clean(value)
        if record.exc_info and record.exc_info[0] is not None:
            # Exception type only: messages and tracebacks can contain user input.
            payload["exc_type"] = record.exc_info[0].__name__
        return json.dumps(payload, separators=(",", ":"))


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    for name in ("uvicorn", "uvicorn.error"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers = []
        uv_logger.propagate = True
    # uvicorn's access log prints full paths (with session IDs) and client IPs.
    access = logging.getLogger("uvicorn.access")
    access.handlers = []
    access.propagate = False
    access.disabled = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
