"""Safety gate: the first step for every user message.

Order of checks:
1. Red-flag rules on accumulated signals (self-harm > emergency > urgent).
2. Medication/treatment request guard.
3. Otherwise pass to the rest of the pipeline.

The gate is deterministic and has no dependency on models, extractors or LLMs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.safety import messages
from app.safety.medication_guard import MedicationGuard
from app.safety.red_flags import RedFlagEngine, ResourceKind, Rule
from app.safety.resources import EmergencyResources, Region, Resource

Outcome = Literal["self_harm", "emergency", "urgent", "medication_refusal", "pass"]

# Session context (not text) that maps to red-flag signals.
AGE_BAND_SIGNALS: dict[str, frozenset[str]] = {"<1": frozenset({"infant"})}


@dataclass(frozen=True)
class SafetyDecision:
    outcome: Outcome
    new_signals: frozenset[str]
    rules: tuple[Rule, ...] = ()
    title: str = ""
    message: str = ""
    resources: tuple[Resource, ...] = ()
    locks_session: bool = False

    @property
    def rule_ids(self) -> tuple[str, ...]:
        return tuple(r.id for r in self.rules)


class SafetyGate:
    def __init__(
        self,
        red_flags: RedFlagEngine,
        medication_guard: MedicationGuard,
        resources: EmergencyResources,
    ) -> None:
        self.red_flags = red_flags
        self.medication_guard = medication_guard
        self.resources = resources

    @classmethod
    def from_paths(
        cls, red_flags_path: Path, medication_path: Path, resources_path: Path
    ) -> SafetyGate:
        engine = RedFlagEngine.from_yaml(red_flags_path)
        guard = MedicationGuard.from_yaml(medication_path, engine.normalizer)
        return cls(engine, guard, EmergencyResources.from_yaml(resources_path))

    def check(
        self,
        text: str,
        *,
        region_code: str,
        prior_signals: frozenset[str] | set[str] = frozenset(),
        fired_rule_ids: frozenset[str] | set[str] = frozenset(),
        age_band: str | None = None,
    ) -> SafetyDecision:
        new_signals = self.red_flags.detect_signals(text)
        context = AGE_BAND_SIGNALS.get(age_band or "", frozenset())
        all_signals = frozenset(prior_signals) | new_signals | context
        region = self.resources.region(region_code)

        fired = [
            rule
            for rule in self.red_flags.evaluate(all_signals)
            if rule.level != "urgent" or rule.id not in fired_rule_ids
        ]
        if fired:
            top_level = fired[0].level
            decisive = tuple(r for r in fired if r.level == top_level)
            if top_level == "self_harm":
                return self._self_harm(new_signals, decisive, region)
            if top_level == "emergency":
                return self._emergency(new_signals, decisive, region)
            return self._urgent(new_signals, decisive, region)

        if self.medication_guard.is_request(text):
            return self._medication(new_signals, region)

        return SafetyDecision(outcome="pass", new_signals=new_signals)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _extra_kinds(rules: tuple[Rule, ...]) -> list[ResourceKind]:
        kinds: list[ResourceKind] = []
        for rule in rules:
            kinds.extend(k for k in rule.extra_resources if k not in kinds)
        return kinds

    @staticmethod
    def _dedupe(resources: list[Resource]) -> tuple[Resource, ...]:
        seen: set[str] = set()
        out: list[Resource] = []
        for r in resources:
            if r.id not in seen:
                seen.add(r.id)
                out.append(r)
        return tuple(out)

    @staticmethod
    def _emergency_contact(region: Region | None) -> str | None:
        if region is None:
            return None
        return region.of_kind("emergency")[0].contact

    def _self_harm(
        self, new_signals: frozenset[str], rules: tuple[Rule, ...], region: Region | None
    ) -> SafetyDecision:
        resources: tuple[Resource, ...] = ()
        if region is not None:
            resources = self._dedupe(
                region.of_kind("crisis_line", "crisis_text", "emergency", "urgent_advice")
                + region.of_kind(*self._extra_kinds(rules))
            )
        message = (
            messages.self_harm_message(self._emergency_contact(region), bool(resources))
            if region is not None
            else self.resources.generic.support_message
        )
        return SafetyDecision(
            outcome="self_harm",
            new_signals=new_signals,
            rules=rules,
            title=messages.SELF_HARM_TITLE,
            message=message,
            resources=resources,
            locks_session=True,
        )

    def _emergency(
        self, new_signals: frozenset[str], rules: tuple[Rule, ...], region: Region | None
    ) -> SafetyDecision:
        advice = list(dict.fromkeys(r.advice for r in rules if r.advice))
        region_message = (
            region.emergency_message
            if region is not None
            else self.resources.generic.emergency_message
        )
        resources: tuple[Resource, ...] = ()
        if region is not None:
            resources = self._dedupe(
                region.of_kind("emergency", "ambulance") + region.of_kind(*self._extra_kinds(rules))
            )
        return SafetyDecision(
            outcome="emergency",
            new_signals=new_signals,
            rules=rules,
            title=rules[0].title,
            message=messages.emergency_message(region_message, advice),
            resources=resources,
            locks_session=True,
        )

    def _urgent(
        self, new_signals: frozenset[str], rules: tuple[Rule, ...], region: Region | None
    ) -> SafetyDecision:
        resources = self._dedupe(region.of_kind("urgent_advice", "emergency")) if region else ()
        return SafetyDecision(
            outcome="urgent",
            new_signals=new_signals,
            rules=rules,
            title=rules[0].title,
            message=messages.urgent_message(self._emergency_contact(region)),
            resources=resources,
            locks_session=False,
        )

    def _medication(self, new_signals: frozenset[str], region: Region | None) -> SafetyDecision:
        poison = region.of_kind("poison") if region else []
        resources = self._dedupe(poison + (region.of_kind("urgent_advice") if region else []))
        return SafetyDecision(
            outcome="medication_refusal",
            new_signals=new_signals,
            title=messages.MEDICATION_TITLE,
            message=messages.medication_message(
                poison[0].contact if poison else None, self._emergency_contact(region)
            ),
            resources=resources,
        )
