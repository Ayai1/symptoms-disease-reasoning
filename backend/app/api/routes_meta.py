"""Health, metadata and emergency-resource endpoints."""

from __future__ import annotations

import time

from fastapi import APIRouter, Response

from app import __version__
from app.api.deps import Ctx
from app.safety import messages
from app.schemas.common import RegionChoice
from app.schemas.meta import HealthOut, MetaOut
from app.schemas.safety import RegionOption, RegionResourcesOut, ResourceOut

router = APIRouter()

SCOPE_NOTE = (
    "Possible matches will come from a model trained on DDXPlus, a synthetic dataset of "
    "49 conditions that are mostly respiratory, heart, and ear, nose and throat conditions. "
    "Results do not measure clinical accuracy."
)


@router.get("/health", response_model=HealthOut)
def health(ctx: Ctx, response: Response) -> HealthOut:
    """Liveness and readiness. Returns 503 if a required component is unavailable."""
    ready = all(c.status == "ok" for c in ctx.components.values() if c.required)
    if not ready:
        response.status_code = 503
    response.headers["Cache-Control"] = "no-store"
    return HealthOut(
        status="ok" if ready else "degraded",
        version=__version__,
        uptime_seconds=int(time.time() - ctx.started_at),
        components=ctx.components,
        model_version=None,
        index_version=None,
        llm="disabled",
    )


@router.get("/meta", response_model=MetaOut)
def meta(ctx: Ctx) -> MetaOut:
    resources = ctx.gate.resources
    regions = [RegionOption(code=code, label=r.label) for code, r in resources.regions.items()]
    regions.append(RegionOption(code="OTHER", label=resources.generic.label))
    return MetaOut(
        version=__version__,
        disclaimer=messages.DISCLAIMER,
        disclaimer_version=messages.DISCLAIMER_VERSION,
        regions=regions,
        default_region=resources.default_region,
        emergency_resources_last_verified=resources.last_verified,
        scope_note=SCOPE_NOTE,
    )


@router.get("/emergency-resources/{region}", response_model=RegionResourcesOut)
def emergency_resources(region: RegionChoice, ctx: Ctx) -> RegionResourcesOut:
    data = ctx.gate.resources
    entry = data.region(region)
    if entry is None:
        return RegionResourcesOut(
            region="OTHER",
            label=data.generic.label,
            emergency_message=data.generic.emergency_message,
            support_message=data.generic.support_message,
            resources=[],
            last_verified=data.last_verified,
        )
    return RegionResourcesOut(
        region=region,
        label=entry.label,
        emergency_message=entry.emergency_message,
        support_message=None,
        resources=[ResourceOut.of(r) for r in entry.resources],
        last_verified=data.last_verified,
    )
