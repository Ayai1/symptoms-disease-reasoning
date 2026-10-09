"""Medication guard behaviour against the curated case suite."""

from __future__ import annotations

from typing import Any

import pytest

from app.safety.gate import SafetyGate
from tests.conftest import load_cases

CASES = load_cases("medication_guard.yaml")["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: str(c["text"])[:60])
def test_medication_guard(gate: SafetyGate, case: dict[str, Any]) -> None:
    assert gate.medication_guard.is_request(case["text"]) is case["refuse"]


@pytest.mark.parametrize("case", [c for c in CASES if c["refuse"]], ids=lambda c: c["text"][:60])
def test_refusal_through_gate(gate: SafetyGate, case: dict[str, Any]) -> None:
    decision = gate.check(case["text"], region_code="US")
    assert decision.outcome == "medication_refusal"
    assert not decision.locks_session
    assert "does not give advice about medicines" in decision.message
    assert [r.id for r in decision.resources] == ["us_poison"]


def test_red_flag_wins_over_medication_request(gate: SafetyGate) -> None:
    decision = gate.check("how many pills to take to end my life", region_code="IN")
    assert decision.outcome == "self_harm"
