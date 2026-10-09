"""Health and metadata responses."""

from __future__ import annotations

from datetime import date
from typing import Literal

from app.schemas.common import RegionChoice, ResponseModel
from app.schemas.safety import RegionOption

ComponentState = Literal["ok", "unavailable", "not_configured"]


class ComponentStatus(ResponseModel):
    status: ComponentState
    required: bool
    detail: str | None = None


class HealthOut(ResponseModel):
    status: Literal["ok", "degraded"]
    version: str
    uptime_seconds: int
    components: dict[str, ComponentStatus]
    model_version: str | None
    index_version: str | None
    llm: Literal["disabled", "available", "degraded"]


class MetaOut(ResponseModel):
    version: str
    disclaimer: str
    disclaimer_version: str
    regions: list[RegionOption]
    default_region: RegionChoice
    emergency_resources_last_verified: date
    scope_note: str
