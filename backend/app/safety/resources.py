"""Emergency and crisis-support contacts per region (DECISIONS.md D-002)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.safety.red_flags import ResourceKind

RegionCode = Literal["IN", "US", "GB"]
REGION_CODES: tuple[RegionCode, ...] = ("IN", "US", "GB")
OTHER_REGION = "OTHER"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Resource(_Strict):
    id: str = Field(pattern=r"^[a-z]{2}_[a-z0-9_]+$")
    kind: ResourceKind
    label: str
    contact: str = Field(pattern=r"^[0-9][0-9 \-]*[0-9]$")
    alt_contact: str | None = Field(default=None, pattern=r"^[0-9][0-9 \-]*[0-9]$")
    contact_type: Literal["call", "text", "call_or_text"]
    availability: str | None = None
    note: str | None = None
    source_urls: list[HttpUrl] = Field(min_length=1)


class Region(_Strict):
    label: str
    emergency_message: str
    resources: list[Resource] = Field(min_length=1)

    @model_validator(mode="after")
    def _has_emergency_number(self) -> Region:
        kinds = [r.kind for r in self.resources]
        if kinds.count("emergency") != 1:
            raise ValueError(f"{self.label}: exactly one 'emergency' resource is required")
        if "crisis_line" not in kinds:
            raise ValueError(f"{self.label}: a 'crisis_line' resource is required")
        return self

    def of_kind(self, *kinds: ResourceKind) -> list[Resource]:
        """Resources of the given kinds, in the order the kinds are listed."""
        return [r for kind in kinds for r in self.resources if r.kind == kind]


class GenericRegion(_Strict):
    label: str
    emergency_message: str
    support_message: str


class EmergencyResources(_Strict):
    schema_version: Literal[1]
    last_verified: date
    max_age_days: int = Field(gt=0, le=365)
    verified_by: str
    verification_method: str
    default_region: RegionCode
    generic: GenericRegion
    regions: dict[RegionCode, Region]

    @model_validator(mode="after")
    def _all_regions_present(self) -> EmergencyResources:
        missing = set(REGION_CODES) - set(self.regions)
        if missing:
            raise ValueError(f"missing regions: {sorted(missing)}")
        return self

    @classmethod
    def from_yaml(cls, path: Path) -> EmergencyResources:
        with path.open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        return cls.model_validate(raw)

    def region(self, code: str) -> Region | None:
        """The region for a supported code, or None for OTHER/unknown codes."""
        if code in REGION_CODES:
            return self.regions[code]
        return None

    def age_days(self, today: date) -> int:
        return (today - self.last_verified).days

    def is_stale(self, today: date) -> bool:
        return self.age_days(today) > self.max_age_days
