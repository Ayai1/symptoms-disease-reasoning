"""Behaviour of the red-flag rules against the curated case suite."""

from __future__ import annotations

from typing import Any

import pytest

from app.safety.gate import SafetyGate
from tests.conftest import load_cases

CASES = load_cases("red_flags.yaml")


def _id(case: dict[str, Any]) -> str:
    return str(case["text"])[:60]


@pytest.mark.parametrize("case", CASES["single"], ids=_id)
def test_single_message(gate: SafetyGate, case: dict[str, Any]) -> None:
    decision = gate.check(case["text"], region_code=case.get("region", "IN"))
    assert decision.outcome == case["outcome"], (decision.outcome, decision.rule_ids)
    for rule_id in case.get("rules", []):
        assert rule_id in decision.rule_ids


@pytest.mark.parametrize("case", CASES["multi_turn"], ids=lambda c: " | ".join(c["turns"]))
def test_multi_turn(gate: SafetyGate, case: dict[str, Any]) -> None:
    signals: set[str] = set()
    fired: set[str] = set()
    for text, outcome, rules in zip(case["turns"], case["outcomes"], case["rules"], strict=True):
        decision = gate.check(text, region_code="IN", prior_signals=signals, fired_rule_ids=fired)
        assert decision.outcome == outcome, (text, decision.outcome, decision.rule_ids)
        for rule_id in rules:
            assert rule_id in decision.rule_ids
        signals |= decision.new_signals
        fired |= set(decision.rule_ids)


@pytest.mark.parametrize("case", CASES["context"], ids=lambda c: f"{c['age_band']}: {c['text']}")
def test_session_context(gate: SafetyGate, case: dict[str, Any]) -> None:
    decision = gate.check(case["text"], region_code="IN", age_band=case["age_band"])
    assert decision.outcome == case["outcome"]
    for rule_id in case["rules"]:
        assert rule_id in decision.rule_ids


def test_every_rule_has_a_case() -> None:
    """Each rule in the configuration is exercised by at least one case."""
    from app.config import SAFETY_DATA_DIR
    from app.safety.red_flags import RedFlagEngine

    engine = RedFlagEngine.from_yaml(SAFETY_DATA_DIR / "red_flags.yaml")
    covered: set[str] = set()
    for case in CASES["single"] + CASES["context"]:
        covered.update(case.get("rules", []))
    for case in CASES["multi_turn"]:
        for rules in case["rules"]:
            covered.update(rules)
    uncovered = {rule.id for rule in engine.rules} - covered
    assert not uncovered, sorted(uncovered)


def test_emergency_locks_and_urgent_does_not(gate: SafetyGate) -> None:
    assert gate.check("I'm choking", region_code="IN").locks_session
    assert gate.check("I want to kill myself", region_code="IN").locks_session
    assert not gate.check("I fainted yesterday", region_code="IN").locks_session
