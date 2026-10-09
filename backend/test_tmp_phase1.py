"""TEMPORARY Phase 1 acceptance checks. Delete this file after review.

Covers every Phase 1 item in one place:
  A. Repository restructure and documentation
  B. Safety gate behaviour (red flags, self-harm support, medication guard)
  C. Startup validation and the emergency-resources CI gate
  D. API contract, session lock, limits, CORS
  E. Privacy (logs, validation errors) and isolation (no LLM/model in safety, no pickle)

Run:  cd backend && uv run pytest test_tmp_phase1.py -v
"""

from __future__ import annotations

import copy
import json
import re
import tomllib
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import SAFETY_DATA_DIR, Settings
from app.main import create_app
from app.safety.gate import SafetyGate
from app.safety.resources import EmergencyResources
from scripts.check_emergency_resources import main as check_resources_main
from tests.conftest import load_cases, make_settings, new_session, send

BACKEND = Path(__file__).resolve().parent
REPO = BACKEND.parent


@pytest.fixture(scope="module")
def gate() -> SafetyGate:
    s = make_settings()
    return SafetyGate.from_paths(
        s.red_flag_rules_path, s.medication_rules_path, s.emergency_resources_path
    )


@pytest.fixture
def client() -> Any:
    with TestClient(create_app(make_settings())) as c:
        yield c


# ===================================================================== A. repo
LEGACY_ITEMS = [
    "src",
    "data",
    "rag_explainer.py",
    "rag_probability_explainer.py",
    "rag_pubmed_index.py",
    "rag_pubmed_loader.py",
    "rag_pubmed_retriever.py",
    "rag_rxnorm_loader.py",
    "rag_signal_extractor.py",
    "run_diagnosis.py",
    "run_training.py",
    "test_tot.py",
    "tester.py",
    "requirements.txt",
]


@pytest.mark.parametrize("name", LEGACY_ITEMS)
def test_a1_prototype_moved_to_legacy(name: str) -> None:
    assert not (REPO / name).exists(), f"{name} still at repository root"
    assert (REPO / "legacy" / name).exists(), f"{name} missing from legacy/"


def test_a2_readme_is_factual_and_states_data_scope() -> None:
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "api_server.py" not in readme
    assert "FINAL DIAGNOSIS" not in readme
    assert "% confidence" not in readme
    for phrase in ("synthetic", "respiratory", "cardiac", "ENT", "not a medical device"):
        assert phrase in readme, phrase
    prose = re.sub(r"```.*?```", "", readme, flags=re.S)
    assert not re.search(r"\b(I|I'm|I've|my|we|our|us)\b", prose), "first-person wording"


def test_a3_no_employer_or_internship_mentions() -> None:
    skip = {".git", ".venv", "node_modules", "legacy", ".mypy_cache", ".ruff_cache"}
    for path in REPO.rglob("*"):
        if (
            path.is_dir()
            or skip & set(path.parts)
            or path.suffix not in {".md", ".py", ".yml", ".yaml", ".toml", ""}
        ):
            continue
        if path.name == Path(__file__).name:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        assert "internship" not in text, path
        assert "employer" not in text, path


def test_a4_license_notice_decisions() -> None:
    assert (REPO / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")
    notice = (REPO / "NOTICE").read_text(encoding="utf-8")
    for name in ("DDXPlus", "MedlinePlus", "CC-BY"):
        assert name in notice, name
    decisions = (REPO / "DECISIONS.md").read_text(encoding="utf-8")
    for n in range(1, 16):
        assert f"D-{n:03d}" in decisions, f"D-{n:03d} missing"
    assert "Node.js 24" in decisions


def test_a5_ci_and_toolchain() -> None:
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for step in (
        "uv sync --frozen",
        "ruff check",
        "ruff format --check",
        "mypy",
        "pytest",
        "check_emergency_resources.py",
    ):
        assert step in ci, step
    assert (BACKEND / "uv.lock").exists()
    assert (BACKEND / ".python-version").read_text().strip() == "3.12"
    project = tomllib.loads((BACKEND / "pyproject.toml").read_text())["project"]
    assert project["requires-python"] == ">=3.12,<3.13"
    assert project["license"] == "MIT"


# ================================================================ B. safety
def test_b1_red_flag_recall_and_specificity(gate: SafetyGate) -> None:
    cases = load_cases("red_flags.yaml")["single"]
    positives = [c for c in cases if c["outcome"] in {"emergency", "self_harm"}]
    negatives = [c for c in cases if c["outcome"] == "pass"]
    missed = [
        c["text"]
        for c in positives
        if gate.check(c["text"], region_code="IN").outcome != c["outcome"]
    ]
    false_alarms = [
        c["text"] for c in negatives if gate.check(c["text"], region_code="IN").outcome != "pass"
    ]
    print(
        f"\nred-flag positives: {len(positives) - len(missed)}/{len(positives)} detected; "
        f"benign/negated: {len(negatives) - len(false_alarms)}/{len(negatives)} passed"
    )
    assert not missed, missed
    assert not false_alarms, false_alarms


def test_b2_every_case_outcome(gate: SafetyGate) -> None:
    for case in load_cases("red_flags.yaml")["single"]:
        decision = gate.check(case["text"], region_code="IN")
        assert decision.outcome == case["outcome"], (case["text"], decision.rule_ids)
        assert set(case.get("rules", [])) <= set(decision.rule_ids), case["text"]


def test_b3_medication_guard(gate: SafetyGate) -> None:
    for case in load_cases("medication_guard.yaml")["cases"]:
        assert gate.medication_guard.is_request(case["text"]) is case["refuse"], case["text"]


@pytest.mark.parametrize(
    ("region", "first_two"),
    [
        ("IN", ["in_tele_manas", "in_emergency"]),
        ("US", ["us_988", "us_emergency"]),
        ("GB", ["gb_samaritans", "gb_shout"]),
    ],
)
def test_b4_self_harm_support_first(gate: SafetyGate, region: str, first_two: list[str]) -> None:
    decision = gate.check("I don't want to live anymore", region_code=region)
    assert decision.outcome == "self_harm"
    assert [r.id for r in decision.resources][:2] == first_two
    assert decision.locks_session


def test_b5_unknown_region_gets_generic_message(gate: SafetyGate) -> None:
    emergency = gate.check("I'm choking", region_code="OTHER")
    assert emergency.resources == ()
    assert "local emergency number" in emergency.message


def test_b6_default_region_is_india() -> None:
    data = EmergencyResources.from_yaml(SAFETY_DATA_DIR / "emergency_resources.yaml")
    assert data.default_region == "IN"
    assert data.last_verified.isoformat() == "2026-10-09"


# ============================================================ C. startup gate
def _write(tmp: Path, name: str, data: Any) -> Path:
    path = tmp / name
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_c1_invalid_emergency_resources_stop_startup(tmp_path: Path) -> None:
    raw = yaml.safe_load((SAFETY_DATA_DIR / "emergency_resources.yaml").read_text())
    broken = copy.deepcopy(raw)
    broken["regions"]["US"]["resources"] = [
        r for r in broken["regions"]["US"]["resources"] if r["kind"] != "emergency"
    ]
    path = _write(tmp_path, "resources.yaml", broken)
    with pytest.raises(ValidationError):
        create_app(make_settings(emergency_resources_path=path))


def test_c2_invalid_red_flag_rules_stop_startup(tmp_path: Path) -> None:
    raw = yaml.safe_load((SAFETY_DATA_DIR / "red_flags.yaml").read_text())
    raw["rules"][0]["when"] = {"any": ["no_such_signal"]}
    path = _write(tmp_path, "red_flags.yaml", raw)
    with pytest.raises(ValidationError):
        create_app(make_settings(red_flag_rules_path=path))


def test_c3_resources_gate_fails_when_stale() -> None:
    data = EmergencyResources.from_yaml(SAFETY_DATA_DIR / "emergency_resources.yaml")
    fresh = data.last_verified.isoformat()
    stale = (data.last_verified + timedelta(days=data.max_age_days + 1)).isoformat()
    assert check_resources_main(["--today", fresh]) == 0
    assert check_resources_main(["--today", stale]) == 1


# ================================================================== D. API
def test_d1_health_and_meta(client: TestClient) -> None:
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["components"]["safety_rules"]["status"] == "ok"
    meta = client.get("/api/v1/meta").json()
    assert meta["default_region"] == "IN"
    assert [r["code"] for r in meta["regions"]] == ["IN", "US", "GB", "OTHER"]


def test_d2_emergency_locks_and_offers_new_session(client: TestClient) -> None:
    sid = new_session(client)
    body = send(client, sid, "her speech is slurred").json()
    assert body["kind"] == "emergency"
    assert body["actions"] == ["start_new_session"]
    again = send(client, sid, "anything")
    assert again.status_code == 409
    assert again.json()["error"]["actions"] == ["start_new_session"]
    assert new_session(client)


def test_d3_limits_and_cors() -> None:
    with TestClient(
        create_app(make_settings(rate_limit_turns_per_minute=1, max_body_bytes=200))
    ) as c:
        sid = new_session(c)
        assert send(c, sid, "cough").status_code == 200
        assert send(c, sid, "cough").status_code == 429
        assert send(c, sid, "x" * 500).status_code == 413
        ok = c.get("/api/v1/health", headers={"Origin": "https://allowed.example"})
        assert ok.headers.get("access-control-allow-origin") == "https://allowed.example"
        bad = c.get("/api/v1/health", headers={"Origin": "https://other.example"})
        assert "access-control-allow-origin" not in bad.headers


def test_d4_settings_reject_wildcard_cors() -> None:
    with pytest.raises(ValidationError):
        Settings(cors_origins=["*"])


# =========================================================== E. privacy etc.
def test_e1_logs_have_no_user_text(capsys: pytest.CaptureFixture[str]) -> None:
    with TestClient(create_app(make_settings())) as c:
        sid = new_session(c)
        send(c, sid, "unique-marker-123 I have a cough")
        bad = send(c, sid, "y" * 2100 + " other-marker-456")
        assert bad.status_code == 422
        assert "other-marker-456" not in bad.text
    out = capsys.readouterr().out
    assert "unique-marker" not in out
    assert "other-marker" not in out
    assert sid not in out
    events = [json.loads(line)["event"] for line in out.splitlines() if line.startswith("{")]
    assert "turn" in events


def test_e2_safety_isolation_and_no_pickle() -> None:
    app_dir = BACKEND / "app"
    for path in (app_dir / "safety").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        for forbidden in ("app.llm", "app.reasoning", "app.nlu", "anthropic", "openai"):
            assert forbidden not in source, f"{path.name} references {forbidden}"
    for path in app_dir.rglob("*.py"):
        assert "import pickle" not in path.read_text(encoding="utf-8"), path.name
