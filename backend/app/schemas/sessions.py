"""Session request and response bodies."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import (
    MAX_MESSAGE_CHARS,
    AgeBand,
    ApiModel,
    RegionChoice,
    ResponseModel,
    Sex,
)


class SessionCreate(ApiModel):
    region: RegionChoice = "IN"
    age_band: AgeBand | None = None
    sex: Sex = "unspecified"
    acknowledged_disclaimer: Literal[True]


class SessionOut(ResponseModel):
    session_id: str
    status: Literal["active", "locked"]
    lock_reason: Literal["emergency", "self_harm"] | None
    region: RegionChoice
    age_band: AgeBand | None
    sex: Sex
    created_at: datetime
    expires_at: datetime
    turn_count: int
    disclaimer: str


class MessageIn(ApiModel):
    text: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)

    @field_validator("text")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value
