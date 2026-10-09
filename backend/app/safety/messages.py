"""User-facing safety wording. Kept in one place so it can be reviewed as a whole."""

from __future__ import annotations

from collections.abc import Iterable

DISCLAIMER_VERSION = "2026-10-09"
DISCLAIMER = (
    "This is an educational tool, not a medical device. It does not diagnose conditions "
    "or give treatment advice. It lists possible matches using a synthetic dataset that "
    "mainly covers respiratory, heart, and ear, nose and throat conditions. If you are "
    "worried about your health, talk to a doctor. In an emergency, call your local "
    "emergency number."
)

LOCKED_SESSION_MESSAGE = (
    "Symptom analysis has stopped for this session because of a possible emergency. "
    "If you need to describe something different, start a new session."
)

PENDING_ENGINE_TITLE = "Message received"
PENDING_ENGINE_MESSAGE = (
    "Symptom analysis is not available in this version yet. No warning signs were "
    "found in your message, but this check is limited. If your symptoms get worse or "
    "you are worried, contact a doctor or your local emergency number."
)

SELF_HARM_TITLE = "You deserve support right now"
MEDICATION_TITLE = "I can't advise on medicines or treatment"


def _emergency_call(emergency_contact: str | None) -> str:
    return f"call {emergency_contact}" if emergency_contact else "call your local emergency number"


def emergency_message(region_message: str, advice: Iterable[str]) -> str:
    parts = [
        region_message,
        "What you described could be a medical emergency. Do not wait to see if it gets better.",
        *advice,
    ]
    return " ".join(p for p in parts if p)


def self_harm_message(emergency_contact: str | None, has_resources: bool) -> str:
    reach_out = (
        "Please reach out now to one of the services below. They are free, confidential "
        "and ready to listen."
        if has_resources
        else "Please reach out now to a crisis line or someone you trust."
    )
    return (
        "It sounds like you may be going through something really painful. "
        "You do not have to face this alone. "
        f"{reach_out} "
        "If you are in immediate danger or have already hurt yourself, "
        f"{_emergency_call(emergency_contact)} now."
    )


def urgent_message(emergency_contact: str | None) -> str:
    return (
        "Please get medical advice today, for example from a doctor or an urgent care "
        "service. If it gets worse or you notice new warning signs, "
        f"{_emergency_call(emergency_contact)} straight away."
    )


def medication_message(poison_contact: str | None, emergency_contact: str | None) -> str:
    overdose = (
        f"call Poison Help on {poison_contact}, or {_emergency_call(emergency_contact)} "
        "if they are unwell"
        if poison_contact
        else _emergency_call(emergency_contact)
    )
    return (
        "This assistant does not give advice about medicines, doses or treatments. "
        "A pharmacist or doctor can advise you safely, and the medicine's label or "
        "leaflet lists how to take it. "
        f"If someone may have taken too much of a medicine, {overdose} now."
    )
