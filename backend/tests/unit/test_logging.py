from __future__ import annotations

import json
import logging

from app.core.logging import JsonFormatter, hash_session_id, scrub


def _format(
    msg: str, fields: dict[str, object] | None = None, exc: bool = False
) -> dict[str, object]:
    record = logging.LogRecord("t", logging.INFO, __file__, 1, msg, None, None)
    if fields is not None:
        record.fields = fields
    if exc:
        try:
            raise ValueError("user text: I have chest pain")
        except ValueError:
            import sys

            record.exc_info = sys.exc_info()
    result: dict[str, object] = json.loads(JsonFormatter().format(record))
    return result


def test_scrub_removes_emails_and_phone_numbers() -> None:
    text = "mail me at jane.doe@example.com or call +91 98765 43210"
    assert scrub(text) == "mail me at [email] or call [number]"


def test_only_allowlisted_fields_are_emitted() -> None:
    out = _format("turn", {"outcome": "pass", "text": "I have chest pain", "ip": "1.2.3.4"})
    assert out["outcome"] == "pass"
    assert "text" not in out
    assert "ip" not in out


def test_exceptions_log_type_only() -> None:
    out = _format("boom", exc=True)
    assert out["exc_type"] == "ValueError"
    assert "chest pain" not in json.dumps(out)


def test_session_hash_is_stable_and_salted() -> None:
    assert hash_session_id("abc", "s1") == hash_session_id("abc", "s1")
    assert hash_session_id("abc", "s1") != hash_session_id("abc", "s2")
    assert "abc" not in hash_session_id("abc", "s1")
