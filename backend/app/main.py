"""Application factory.

Run with: ``uv run uvicorn app.main:create_app --factory --no-access-log``

Startup check: safety rules and emergency resources are loaded and validated
while the app is created. Invalid safety configuration stops the process
instead of serving requests without a working safety gate (DECISIONS.md D-008).
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import date

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api import routes_meta, routes_sessions
from app.api.deps import AppContext
from app.config import Settings
from app.core.errors import error_body, register_exception_handlers
from app.core.logging import configure_logging
from app.core.rate_limit import SlidingWindowLimiter
from app.safety.gate import SafetyGate
from app.schemas.meta import ComponentStatus
from app.sessions.store import InMemorySessionStore

API_PREFIX = "/api/v1"
_REQUEST_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")

logger = logging.getLogger("app")


def _build_context(settings: Settings) -> AppContext:
    gate = SafetyGate.from_paths(
        settings.red_flag_rules_path,
        settings.medication_rules_path,
        settings.emergency_resources_path,
    )
    resources = gate.resources
    stale = resources.is_stale(date.today())
    components = {
        "safety_rules": ComponentStatus(
            status="ok",
            required=True,
            detail=f"{len(gate.red_flags.rules)} rules, {len(gate.red_flags.signals)} signals",
        ),
        "emergency_resources": ComponentStatus(
            status="ok",
            required=True,
            detail=(
                f"last verified {resources.last_verified.isoformat()}"
                + ("; re-verification overdue" if stale else "")
            ),
        ),
        "session_store": ComponentStatus(status="ok", required=True, detail="in-memory"),
        "model": ComponentStatus(status="not_configured", required=False),
        "retrieval_index": ComponentStatus(status="not_configured", required=False),
        "llm": ComponentStatus(status="not_configured", required=False, detail="disabled"),
    }
    if stale:
        logger.warning(
            "emergency_resources_stale",
            extra={"fields": {"component": "emergency_resources"}},
        )
    return AppContext(
        settings=settings,
        gate=gate,
        store=InMemorySessionStore(
            idle_ttl_seconds=settings.session_idle_ttl_seconds,
            absolute_ttl_seconds=settings.session_absolute_ttl_seconds,
            max_sessions=settings.max_sessions,
        ),
        turn_limiter=SlidingWindowLimiter(settings.rate_limit_turns_per_minute),
        session_limiter=SlidingWindowLimiter(settings.rate_limit_sessions_per_minute),
        started_at=time.time(),
        components=components,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level)

    show_docs = settings.environment != "production"
    app = FastAPI(
        title="Symptom Assistant API",
        version=__version__,
        docs_url=f"{API_PREFIX}/docs" if show_docs else None,
        redoc_url=None,
        openapi_url=f"{API_PREFIX}/openapi.json" if show_docs else None,
    )
    app.state.ctx = _build_context(settings)

    register_exception_handlers(app)
    app.include_router(routes_meta.router, prefix=API_PREFIX)
    app.include_router(routes_sessions.router, prefix=API_PREFIX)

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        supplied = request.headers.get("x-request-id", "")
        request_id = supplied if _REQUEST_ID.fullmatch(supplied) else uuid.uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()

        length = request.headers.get("content-length", "")
        if length.isdigit() and int(length) > settings.max_body_bytes:
            response: Response = JSONResponse(
                status_code=413,
                content=error_body(
                    "payload_too_large", "The request body is too large.", request_id
                ),
            )
        else:
            response = await call_next(request)

        response.headers["X-Request-ID"] = request_id
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"

        route = request.scope.get("route")
        logger.info(
            "request",
            extra={
                "fields": {
                    "request_id": request_id,
                    "method": request.method,
                    # Route template, never the concrete path (it contains session IDs).
                    "route": getattr(route, "path", "unmatched"),
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                }
            },
        )
        return response

    # Added last so it is the outermost middleware: error, 413 and 429
    # responses also carry CORS headers.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Retry-After"],
        max_age=600,
    )

    logger.info(
        "startup",
        extra={
            "fields": {
                "version": __version__,
                "count": len(app.state.ctx.gate.red_flags.rules),
            }
        },
    )
    return app
