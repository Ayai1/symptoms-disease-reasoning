"""Deterministic red-flag detection.

Runs on raw message text before any model or extractor and has no dependency
on them (see DECISIONS.md D-005). Rules are defined in
``safety/data/red_flags.yaml``; patterns map text to named signals and rules
combine signals accumulated over the session (D-014).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.safety.text import NegationDetector, Normalizer

RuleLevel = Literal["self_harm", "emergency", "urgent"]
ResourceKind = Literal[
    "emergency", "ambulance", "crisis_line", "crisis_text", "poison", "urgent_advice"
]

# Higher wins when several rules fire in one turn.
LEVEL_PRIORITY: dict[RuleLevel, int] = {"self_harm": 3, "emergency": 2, "urgent": 1}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class NormalizationConfig(_Strict):
    contractions: dict[str, str] = Field(default_factory=dict)
    spelling: dict[str, str] = Field(default_factory=dict)


class NegationConfig(_Strict):
    triggers: list[str]
    pseudo_triggers: list[str] = Field(default_factory=list)
    terminators: list[str] = Field(default_factory=list)
    window_tokens: int = Field(default=6, ge=1, le=20)


class SignalConfig(_Strict):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    patterns: list[str] = Field(min_length=1)
    negatable: bool = True


class Condition(_Strict):
    all: list[str] = Field(default_factory=list)
    any: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _non_empty(self) -> Condition:
        if not self.all and not self.any:
            raise ValueError("a rule condition needs 'all' or 'any'")
        return self


class RuleConfig(_Strict):
    id: str = Field(pattern=r"^RF-[A-Z0-9-]+$")
    level: RuleLevel
    title: str
    rationale: str
    advice: str | None = None
    when: Condition
    extra_resources: list[ResourceKind] = Field(default_factory=list)


class RedFlagConfig(_Strict):
    schema_version: Literal[1]
    normalization: NormalizationConfig
    negation: NegationConfig
    signals: list[SignalConfig]
    rules: list[RuleConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def _references(self) -> RedFlagConfig:
        signal_ids = [s.id for s in self.signals]
        if len(signal_ids) != len(set(signal_ids)):
            raise ValueError("duplicate signal ids")
        rule_ids = [r.id for r in self.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("duplicate rule ids")
        known = set(signal_ids)
        for rule in self.rules:
            unknown = (set(rule.when.all) | set(rule.when.any)) - known
            if unknown:
                raise ValueError(f"rule {rule.id} references unknown signals {sorted(unknown)}")
        return self


@dataclass(frozen=True)
class Signal:
    id: str
    patterns: tuple[re.Pattern[str], ...]
    negatable: bool


@dataclass(frozen=True)
class Rule:
    id: str
    level: RuleLevel
    title: str
    rationale: str
    advice: str | None
    all_signals: frozenset[str]
    any_signals: frozenset[str]
    extra_resources: tuple[ResourceKind, ...]

    def matches(self, signals: frozenset[str] | set[str]) -> bool:
        if not self.all_signals <= signals:
            return False
        return not self.any_signals or bool(self.any_signals & signals)


class RedFlagEngine:
    def __init__(self, config: RedFlagConfig) -> None:
        self.normalizer = Normalizer(
            config.normalization.contractions, config.normalization.spelling
        )
        self.negation = NegationDetector(
            config.negation.triggers,
            config.negation.pseudo_triggers,
            config.negation.terminators,
            config.negation.window_tokens,
        )
        self.signals: tuple[Signal, ...] = tuple(
            Signal(
                id=s.id,
                patterns=tuple(re.compile(p) for p in s.patterns),
                negatable=s.negatable,
            )
            for s in config.signals
        )
        self.rules: tuple[Rule, ...] = tuple(
            Rule(
                id=r.id,
                level=r.level,
                title=r.title,
                rationale=r.rationale,
                advice=r.advice,
                all_signals=frozenset(r.when.all),
                any_signals=frozenset(r.when.any),
                extra_resources=tuple(r.extra_resources),
            )
            for r in config.rules
        )

    @classmethod
    def from_yaml(cls, path: Path) -> RedFlagEngine:
        with path.open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        return cls(RedFlagConfig.model_validate(raw))

    def detect_signals(self, text: str) -> frozenset[str]:
        """Signals present (and not explicitly negated) in one message."""
        normalized = self.normalizer.normalize(text)
        found: set[str] = set()
        for signal in self.signals:
            for pattern in signal.patterns:
                if self._has_affirmed_match(pattern, normalized, signal.negatable):
                    found.add(signal.id)
                    break
        return frozenset(found)

    def _has_affirmed_match(self, pattern: re.Pattern[str], text: str, negatable: bool) -> bool:
        for match in pattern.finditer(text):
            if not negatable or not self.negation.is_negated(text, match.start()):
                return True
        return False

    def evaluate(self, signals: frozenset[str] | set[str]) -> list[Rule]:
        """All rules satisfied by the signal set, highest priority first."""
        fired = [rule for rule in self.rules if rule.matches(signals)]
        return sorted(fired, key=lambda r: LEVEL_PRIORITY[r.level], reverse=True)
