"""Which contacts the safety gate returns, per region and outcome."""

from __future__ import annotations

from app.safety.gate import SafetyDecision, SafetyGate


def _ids(decision: SafetyDecision) -> list[str]:
    return [r.id for r in decision.resources]


def test_self_harm_shows_crisis_support_first_india(gate: SafetyGate) -> None:
    decision = gate.check("I want to kill myself", region_code="IN")
    assert decision.outcome == "self_harm"
    assert _ids(decision)[0] == "in_tele_manas"
    assert "in_emergency" in _ids(decision)
    assert "You do not have to face this alone" in decision.message
    assert "call 112" in decision.message


def test_self_harm_us_and_uk(gate: SafetyGate) -> None:
    us = gate.check("I want to kill myself", region_code="US")
    assert _ids(us)[:1] == ["us_988"]
    assert "us_emergency" in _ids(us)
    uk = gate.check("I want to kill myself", region_code="GB")
    assert _ids(uk)[:2] == ["gb_samaritans", "gb_shout"]
    assert "gb_emergency" in _ids(uk)


def test_self_harm_unknown_region_is_generic(gate: SafetyGate) -> None:
    decision = gate.check("I want to kill myself", region_code="OTHER")
    assert decision.resources == ()
    assert decision.message == gate.resources.generic.support_message


def test_emergency_contacts_per_region(gate: SafetyGate) -> None:
    assert _ids(gate.check("I'm choking", region_code="IN")) == ["in_emergency", "in_ambulance"]
    assert _ids(gate.check("I'm choking", region_code="US")) == ["us_emergency"]
    assert _ids(gate.check("I'm choking", region_code="GB")) == ["gb_emergency"]


def test_emergency_unknown_region_is_generic(gate: SafetyGate) -> None:
    decision = gate.check("I'm choking", region_code="OTHER")
    assert decision.resources == ()
    assert "local emergency number" in decision.message


def test_poisoning_adds_poison_help_where_available(gate: SafetyGate) -> None:
    decision = gate.check("my child swallowed bleach", region_code="US")
    assert _ids(decision) == ["us_emergency", "us_poison"]


def test_rule_advice_is_included(gate: SafetyGate) -> None:
    decision = gate.check("her face is drooping", region_code="GB")
    assert "Note the time the symptoms started." in decision.message
    assert decision.message.startswith("Call 999 now")


def test_urgent_notice_points_to_same_day_care(gate: SafetyGate) -> None:
    decision = gate.check("I fainted yesterday", region_code="GB")
    assert decision.outcome == "urgent"
    assert _ids(decision) == ["gb_111", "gb_emergency"]
    assert "call 999" in decision.message
