"""Shared API types."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

RegionChoice = Literal["IN", "US", "GB", "OTHER"]
AgeBand = Literal["<1", "1-4", "5-14", "15-24", "25-44", "45-64", "65+"]
Sex = Literal["female", "male", "unspecified"]
SESSION_ID_PATTERN = r"^[A-Za-z0-9_-]{20,64}$"
MAX_MESSAGE_CHARS = 2000


class ApiModel(BaseModel):
    """Base for request bodies: unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")


class ResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
