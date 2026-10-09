"""Request-scoped dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, Request

from app.config import Settings
from app.core.errors import RateLimitedError
from app.core.rate_limit import SlidingWindowLimiter
from app.safety.gate import SafetyGate
from app.schemas.meta import ComponentStatus
from app.sessions.store import SessionStore


@dataclass
class AppContext:
    settings: Settings
    gate: SafetyGate
    store: SessionStore
    turn_limiter: SlidingWindowLimiter
    session_limiter: SlidingWindowLimiter
    started_at: float
    components: dict[str, ComponentStatus]


def get_context(request: Request) -> AppContext:
    return cast(AppContext, request.app.state.ctx)


Ctx = Annotated[AppContext, Depends(get_context)]


def client_key(request: Request, settings: Settings) -> str:
    """Address used for rate limiting only. Never logged or stored beyond the window.

    Behind a trusted proxy the right-most X-Forwarded-For entry is used: it is the
    address the proxy itself saw, while left-most entries can be set by the client.
    """
    if settings.trust_forwarded_for:
        forwarded = request.headers.get("x-forwarded-for", "")
        hops = [h.strip() for h in forwarded.split(",") if h.strip()]
        if hops:
            return hops[-1]
    return request.client.host if request.client else "unknown"


def _enforce(limiter: SlidingWindowLimiter, request: Request, settings: Settings) -> None:
    allowed, retry_after = limiter.hit(client_key(request, settings))
    if not allowed:
        raise RateLimitedError(
            "Too many requests. Please wait a moment and try again.",
            headers={"Retry-After": str(retry_after)},
            extra={"retry_after": retry_after},
        )


def limit_turns(request: Request, ctx: Ctx) -> None:
    _enforce(ctx.turn_limiter, request, ctx.settings)


def limit_session_creation(request: Request, ctx: Ctx) -> None:
    _enforce(ctx.session_limiter, request, ctx.settings)
