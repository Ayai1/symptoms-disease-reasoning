"""Session lifecycle and message turns.

Phase 1: the message endpoint runs the safety gate only (DECISIONS.md D-015).
Message text is used for the safety check and then discarded; it is never
stored in the session or written to logs.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Path, Response, status

from app.api.deps import Ctx, limit_session_creation, limit_turns
from app.core.errors import AppError, NotFoundError, SessionLockedError
from app.core.logging import hash_session_id
from app.safety import messages
from app.safety.gate import Outcome
from app.safety.red_flags import ResourceKind
from app.schemas.common import SESSION_ID_PATTERN, AgeBand, RegionChoice, Sex
from app.schemas.safety import ResourceOut, TurnKind, TurnResult
from app.schemas.sessions import MessageIn, SessionCreate, SessionOut
from app.sessions.store import Session, SessionCapacityError

router = APIRouter(prefix="/sessions")
logger = logging.getLogger("app.sessions")

SessionId = Annotated[str, Path(pattern=SESSION_ID_PATTERN)]

TURN_KIND: dict[Outcome, TurnKind] = {
    "self_harm": "self_harm_support",
    "emergency": "emergency",
    "urgent": "urgent_notice",
    "medication_refusal": "medication_refusal",
    "pass": "notice",
}

LOCK_RESOURCE_KINDS: dict[str, tuple[ResourceKind, ...]] = {
    "self_harm": ("crisis_line", "crisis_text", "emergency", "urgent_advice"),
    "emergency": ("emergency", "ambulance"),
}


class ServiceBusyError(AppError):
    status_code = 503
    code = "service_busy"


def _ts(value: float) -> datetime:
    return datetime.fromtimestamp(value, UTC)


def _session_out(ctx: Ctx, session: Session) -> SessionOut:
    return SessionOut(
        session_id=session.id,
        status=session.status,
        lock_reason=session.lock_reason,
        region=cast(RegionChoice, session.region),
        age_band=cast(AgeBand | None, session.age_band),
        sex=cast(Sex, session.sex),
        created_at=_ts(session.created_at),
        expires_at=_ts(ctx.store.expires_at(session)),
        turn_count=session.turn_count,
        disclaimer=messages.DISCLAIMER,
    )


def _get_live(ctx: Ctx, session_id: str) -> Session:
    session = ctx.store.get(session_id)
    if session is None:
        raise NotFoundError("Session not found or expired. Start a new session.")
    return session


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=SessionOut,
    dependencies=[Depends(limit_session_creation)],
)
def create_session(body: SessionCreate, ctx: Ctx) -> SessionOut:
    try:
        session = ctx.store.create(region=body.region, age_band=body.age_band, sex=body.sex)
    except SessionCapacityError as exc:
        raise ServiceBusyError("The service is busy. Please try again shortly.") from exc
    logger.info(
        "session_created",
        extra={"fields": {"session": hash_session_id(session.id, ctx.settings.log_salt)}},
    )
    return _session_out(ctx, session)


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: SessionId, ctx: Ctx) -> SessionOut:
    return _session_out(ctx, _get_live(ctx, session_id))


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: SessionId, ctx: Ctx) -> Response:
    """Erase a session immediately. Idempotent."""
    ctx.store.delete(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{session_id}/messages",
    response_model=TurnResult,
    dependencies=[Depends(limit_turns)],
)
def post_message(session_id: SessionId, body: MessageIn, ctx: Ctx) -> TurnResult:
    session = _get_live(ctx, session_id)
    session_hash = hash_session_id(session.id, ctx.settings.log_salt)

    if session.status == "locked":
        region = ctx.gate.resources.region(session.region)
        kinds = LOCK_RESOURCE_KINDS.get(session.lock_reason or "emergency", ())
        resources = region.of_kind(*kinds) if region else []
        raise SessionLockedError(
            messages.LOCKED_SESSION_MESSAGE,
            extra={
                "lock_reason": session.lock_reason,
                "actions": ["start_new_session"],
                "resources": [ResourceOut.of(r).model_dump() for r in resources],
            },
        )

    decision = ctx.gate.check(
        body.text,
        region_code=session.region,
        prior_signals=session.signals,
        fired_rule_ids=session.fired_rule_ids,
        age_band=session.age_band,
    )

    session.signals |= decision.new_signals
    session.fired_rule_ids |= set(decision.rule_ids)
    session.turn_count += 1
    if decision.locks_session:
        session.status = "locked"
        session.lock_reason = "self_harm" if decision.outcome == "self_harm" else "emergency"
    ctx.store.save(session)

    logger.info(
        "turn",
        extra={
            "fields": {
                "session": session_hash,
                "outcome": decision.outcome,
                "rule_ids": list(decision.rule_ids),
            }
        },
    )

    if decision.outcome == "pass":
        title, message = messages.PENDING_ENGINE_TITLE, messages.PENDING_ENGINE_MESSAGE
    else:
        title, message = decision.title, decision.message

    return TurnResult(
        turn_id=uuid.uuid4().hex,
        kind=TURN_KIND[decision.outcome],
        title=title,
        message=message,
        resources=[ResourceOut.of(r) for r in decision.resources],
        rule_ids=list(decision.rule_ids),
        session_status=session.status,
        actions=["start_new_session"] if decision.locks_session else ["continue"],
        disclaimer=messages.DISCLAIMER,
    )
