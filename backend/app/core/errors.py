"""Application errors and exception handlers.

Every error response has the shape
``{"error": {"code": str, "message": str, "request_id": str, ...}}``.
Handlers never echo request input back to the client or into logs.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(
        self,
        message: str,
        *,
        headers: dict[str, str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.headers = headers or {}
        self.extra = extra or {}


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class SessionLockedError(AppError):
    status_code = 409
    code = "session_locked"


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "payload_too_large"


def request_id_of(request: Request) -> str:
    return str(getattr(request.state, "request_id", ""))


def error_body(code: str, message: str, request_id: str, **extra: Any) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "request_id": request_id, **extra}}


async def _app_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)  # noqa: S101 - narrowed for the type checker
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.code, exc.message, request_id_of(request), **exc.extra),
        headers=exc.headers,
    )


async def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    # Report location and error type only. Pydantic's default payload includes
    # the submitted value, which may be the user's symptom text.
    fields = [
        {"loc": [str(part) for part in err.get("loc", ())], "type": str(err.get("type", ""))}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_body(
            "validation_error",
            "The request did not pass validation.",
            request_id_of(request),
            fields=fields,
        ),
    )


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101
    code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
    message = {404: "Not found.", 405: "Method not allowed."}.get(
        exc.status_code, "Request failed."
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(code, message, request_id_of(request)),
        headers=getattr(exc, "headers", None),
    )


async def _unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled_exception",
        extra={"fields": {"request_id": request_id_of(request), "exc_type": type(exc).__name__}},
    )
    return JSONResponse(
        status_code=500,
        content=error_body(
            "internal_error", "Something went wrong on our side.", request_id_of(request)
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(Exception, _unhandled_error)
