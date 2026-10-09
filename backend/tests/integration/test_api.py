from __future__ import annotations

import json
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.meta import ComponentStatus
from tests.conftest import make_settings, new_session, send

ORIGIN = "https://allowed.example"


# ---------------------------------------------------------------- health / meta
def test_health_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["llm"] == "disabled"
    assert body["components"]["safety_rules"]["status"] == "ok"
    assert body["components"]["emergency_resources"]["status"] == "ok"
    assert response.headers["X-Request-ID"]
    assert response.headers["Cache-Control"] == "no-store"


def test_health_503_when_required_component_unavailable(client: TestClient) -> None:
    ctx = client.app.state.ctx  # type: ignore[attr-defined]
    ctx.components["safety_rules"] = ComponentStatus(status="unavailable", required=True)
    response = client.get("/api/v1/health")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"


def test_meta(client: TestClient) -> None:
    body = client.get("/api/v1/meta").json()
    assert [r["code"] for r in body["regions"]] == ["IN", "US", "GB", "OTHER"]
    assert body["default_region"] == "IN"
    assert "not a medical device" in body["disclaimer"]
    assert "synthetic" in body["scope_note"]


def test_emergency_resources_endpoint(client: TestClient) -> None:
    india = client.get("/api/v1/emergency-resources/IN").json()
    assert [r["contact"] for r in india["resources"]] == ["112", "108", "14416"]
    other = client.get("/api/v1/emergency-resources/OTHER").json()
    assert other["resources"] == []
    assert "local emergency number" in other["emergency_message"]
    assert client.get("/api/v1/emergency-resources/FR").status_code == 422


# -------------------------------------------------------------------- sessions
@pytest.mark.parametrize(
    "body",
    [{}, {"acknowledged_disclaimer": False}, {"acknowledged_disclaimer": True, "extra": 1}],
)
def test_session_requires_acknowledged_disclaimer(
    client: TestClient, body: dict[str, object]
) -> None:
    response = client.post("/api/v1/sessions", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_session_lifecycle(client: TestClient) -> None:
    session_id = new_session(client, region="US", age_band="25-44", sex="female")
    body = client.get(f"/api/v1/sessions/{session_id}").json()
    assert body["status"] == "active"
    assert body["region"] == "US"
    assert client.delete(f"/api/v1/sessions/{session_id}").status_code == 204
    missing = client.get(f"/api/v1/sessions/{session_id}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


def test_unknown_and_malformed_session_ids(client: TestClient) -> None:
    assert send(client, "a" * 30, "hello").status_code == 404
    assert send(client, "bad", "hello").status_code == 422


# ----------------------------------------------------------------------- turns
def test_benign_message_returns_notice(client: TestClient) -> None:
    session_id = new_session(client)
    body = send(client, session_id, "I have a runny nose and a mild cough").json()
    assert body["kind"] == "notice"
    assert body["session_status"] == "active"
    assert body["actions"] == ["continue"]
    assert "not a medical device" in body["disclaimer"]


def test_red_flag_locks_session_and_offers_new_session(client: TestClient) -> None:
    session_id = new_session(client, region="IN")
    body = send(client, session_id, "I have chest pain and I can't breathe").json()
    assert body["kind"] == "emergency"
    assert body["session_status"] == "locked"
    assert body["actions"] == ["start_new_session"]
    assert "RF-CARDIAC-COMBO" in body["rule_ids"]
    assert [r["contact"] for r in body["resources"]] == ["112", "108"]

    locked = send(client, session_id, "hello again")
    assert locked.status_code == 409
    error = locked.json()["error"]
    assert error["code"] == "session_locked"
    assert error["actions"] == ["start_new_session"]
    assert error["resources"][0]["contact"] == "112"

    snapshot = client.get(f"/api/v1/sessions/{session_id}").json()
    assert snapshot["lock_reason"] == "emergency"
    assert new_session(client)  # a new session is always available


def test_self_harm_shows_support_resources_first(client: TestClient) -> None:
    session_id = new_session(client, region="GB")
    body = send(client, session_id, "I don't want to live anymore").json()
    assert body["kind"] == "self_harm_support"
    assert [r["id"] for r in body["resources"]][:2] == ["gb_samaritans", "gb_shout"]
    assert body["actions"] == ["start_new_session"]

    locked = send(client, session_id, "ok").json()["error"]
    assert locked["lock_reason"] == "self_harm"
    assert locked["resources"][0]["id"] == "gb_samaritans"


def test_medication_request_is_refused_without_lock(client: TestClient) -> None:
    session_id = new_session(client, region="US")
    body = send(client, session_id, "how much ibuprofen can I take?").json()
    assert body["kind"] == "medication_refusal"
    assert body["session_status"] == "active"
    assert body["resources"][0]["id"] == "us_poison"


def test_signals_combine_across_turns(client: TestClient) -> None:
    session_id = new_session(client)
    first = send(client, session_id, "I have chest pain").json()
    assert first["kind"] == "urgent_notice"
    assert first["session_status"] == "active"
    second = send(client, session_id, "and now I'm sweating").json()
    assert second["kind"] == "emergency"


def test_infant_age_band_is_used(client: TestClient) -> None:
    session_id = new_session(client, age_band="<1")
    assert send(client, session_id, "she has a fever").json()["kind"] == "emergency"


# ----------------------------------------------------------- validation/limits
def test_validation_error_does_not_echo_input(client: TestClient) -> None:
    session_id = new_session(client)
    response = send(client, session_id, "x" * 2001 + " secret-symptom-marker")
    assert response.status_code == 422
    assert "secret-symptom-marker" not in response.text
    assert send(client, session_id, "   ").status_code == 422


def test_payload_too_large(client_factory: Callable[..., TestClient]) -> None:
    client = client_factory(max_body_bytes=100)
    response = client.post(
        "/api/v1/sessions", json={"acknowledged_disclaimer": True, "x": "y" * 200}
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_turn_rate_limit(client_factory: Callable[..., TestClient]) -> None:
    client = client_factory(rate_limit_turns_per_minute=2)
    session_id = new_session(client)
    assert send(client, session_id, "cough").status_code == 200
    assert send(client, session_id, "cough").status_code == 200
    limited = send(client, session_id, "cough")
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) >= 1
    assert limited.json()["error"]["code"] == "rate_limited"


def test_session_creation_rate_limit(client_factory: Callable[..., TestClient]) -> None:
    client = client_factory(rate_limit_sessions_per_minute=1)
    new_session(client)
    response = client.post("/api/v1/sessions", json={"acknowledged_disclaimer": True})
    assert response.status_code == 429


# ------------------------------------------------------------------------ CORS
def test_cors_allows_configured_origin(client: TestClient) -> None:
    response = client.options(
        "/api/v1/sessions",
        headers={"Origin": ORIGIN, "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    simple = client.get("/api/v1/health", headers={"Origin": ORIGIN})
    assert simple.headers["access-control-allow-origin"] == ORIGIN


def test_cors_rejects_other_origins(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers


# --------------------------------------------------------------------- privacy
def test_logs_contain_no_message_text_or_session_ids(capsys: pytest.CaptureFixture[str]) -> None:
    client = TestClient(create_app(make_settings()))
    session_id = new_session(client)
    send(client, session_id, "my chest hurts, write to jane@example.com")
    send(client, session_id, "zebra-unicorn-marker headache")
    client.close()

    out = capsys.readouterr().out
    for forbidden in ("zebra-unicorn-marker", "chest hurts", "jane@example.com", session_id):
        assert forbidden not in out

    lines = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    turns = [line for line in lines if line.get("event") == "turn"]
    assert len(turns) == 2
    assert turns[0]["outcome"] == "urgent"
    assert turns[0]["rule_ids"] == ["RF-URGENT-CHEST-PAIN"]
    routes = {line.get("route") for line in lines if line.get("event") == "request"}
    assert "/api/v1/sessions/{session_id}/messages" in routes
