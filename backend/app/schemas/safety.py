"""Public shapes for safety resources and turn results."""

from __future__ import annotations

from datetime import date
from typing import Literal

from app.safety.resources import Resource
from app.schemas.common import RegionChoice, ResponseModel

TurnKind = Literal[
    "emergency", "self_harm_support", "urgent_notice", "medication_refusal", "notice"
]
TurnAction = Literal["start_new_session", "continue"]


class ResourceOut(ResponseModel):
    id: str
    kind: str
    label: str
    contact: str
    alt_contact: str | None
    contact_type: Literal["call", "text", "call_or_text"]
    availability: str | None
    note: str | None

    @classmethod
    def of(cls, resource: Resource) -> ResourceOut:
        return cls(
            id=resource.id,
            kind=resource.kind,
            label=resource.label,
            contact=resource.contact,
            alt_contact=resource.alt_contact,
            contact_type=resource.contact_type,
            availability=resource.availability,
            note=resource.note,
        )


class RegionResourcesOut(ResponseModel):
    region: RegionChoice
    label: str
    emergency_message: str
    support_message: str | None
    resources: list[ResourceOut]
    last_verified: date


class RegionOption(ResponseModel):
    code: RegionChoice
    label: str


class TurnResult(ResponseModel):
    turn_id: str
    kind: TurnKind
    title: str
    message: str
    resources: list[ResourceOut]
    rule_ids: list[str]
    session_status: Literal["active", "locked"]
    actions: list[TurnAction]
    disclaimer: str
