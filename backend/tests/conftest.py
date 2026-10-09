from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.safety.gate import SafetyGate

TESTS_DIR = Path(__file__).resolve().parent
CASES_DIR = TESTS_DIR / "safety" / "cases"


def load_cases(name: str) -> Any:
    with (CASES_DIR / name).open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def make_settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "environment": "test",
        "cors_origins": ["https://allowed.example"],
        "log_salt": "test-salt",
    }
    base.update(overrides)
    return Settings(**base)


@pytest.fixture(scope="session")
def gate() -> SafetyGate:
    settings = make_settings()
    return SafetyGate.from_paths(
        settings.red_flag_rules_path,
        settings.medication_rules_path,
        settings.emergency_resources_path,
    )


@pytest.fixture
def client_factory() -> Iterator[Callable[..., TestClient]]:
    clients: list[TestClient] = []

    def factory(**overrides: Any) -> TestClient:
        client = TestClient(create_app(make_settings(**overrides)))
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client.close()


@pytest.fixture
def client(client_factory: Callable[..., TestClient]) -> TestClient:
    return client_factory()


def new_session(client: TestClient, **body: Any) -> str:
    payload: dict[str, Any] = {"acknowledged_disclaimer": True, **body}
    response = client.post("/api/v1/sessions", json=payload)
    assert response.status_code == 201, response.text
    return str(response.json()["session_id"])


def send(client: TestClient, session_id: str, text: str) -> Any:
    return client.post(f"/api/v1/sessions/{session_id}/messages", json={"text": text})
