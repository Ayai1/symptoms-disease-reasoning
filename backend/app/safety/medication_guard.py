"""Detects requests for medication, dosing or treatment advice.

The assistant never answers these. A message is a request when it matches a
strong pattern, or a request pattern together with a medication term.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.safety.text import Normalizer


class MedicationGuardConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    strong_patterns: list[str] = Field(min_length=1)
    request_patterns: list[str] = Field(min_length=1)
    medication_terms: list[str] = Field(min_length=1)


def _compile(patterns: list[str]) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p) for p in patterns)


class MedicationGuard:
    def __init__(self, config: MedicationGuardConfig, normalizer: Normalizer) -> None:
        self._normalizer = normalizer
        self._strong = _compile(config.strong_patterns)
        self._request = _compile(config.request_patterns)
        self._terms = _compile(config.medication_terms)

    @classmethod
    def from_yaml(cls, path: Path, normalizer: Normalizer) -> MedicationGuard:
        with path.open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        return cls(MedicationGuardConfig.model_validate(raw), normalizer)

    def is_request(self, text: str) -> bool:
        normalized = self._normalizer.normalize(text)
        if any(p.search(normalized) for p in self._strong):
            return True
        return any(p.search(normalized) for p in self._request) and any(
            t.search(normalized) for t in self._terms
        )
