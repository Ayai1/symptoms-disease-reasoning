from __future__ import annotations

import copy
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from app.config import SAFETY_DATA_DIR
from app.safety.resources import EmergencyResources
from scripts.check_emergency_resources import check

PATH = SAFETY_DATA_DIR / "emergency_resources.yaml"


def _raw() -> dict[str, Any]:
    with PATH.open(encoding="utf-8") as fh:
        data: dict[str, Any] = yaml.safe_load(fh)
    return data


def test_file_loads_with_three_regions() -> None:
    data = EmergencyResources.from_yaml(PATH)
    assert set(data.regions) == {"IN", "US", "GB"}
    assert data.default_region == "IN"


@pytest.mark.parametrize(
    ("region", "emergency", "crisis"),
    [("IN", "112", "14416"), ("US", "911", "988"), ("GB", "999", "116 123")],
)
def test_expected_numbers(region: str, emergency: str, crisis: str) -> None:
    data = EmergencyResources.from_yaml(PATH)
    entry = data.region(region)
    assert entry is not None
    assert entry.of_kind("emergency")[0].contact == emergency
    assert entry.of_kind("crisis_line")[0].contact == crisis


def test_unknown_region_returns_none() -> None:
    data = EmergencyResources.from_yaml(PATH)
    assert data.region("OTHER") is None
    assert data.region("FR") is None


def test_every_resource_has_a_source() -> None:
    data = EmergencyResources.from_yaml(PATH)
    for region in data.regions.values():
        for resource in region.resources:
            assert resource.source_urls


def test_region_without_emergency_number_is_rejected() -> None:
    raw = copy.deepcopy(_raw())
    raw["regions"]["IN"]["resources"] = [
        r for r in raw["regions"]["IN"]["resources"] if r["kind"] != "emergency"
    ]
    with pytest.raises(ValidationError):
        EmergencyResources.model_validate(raw)


def test_missing_region_is_rejected() -> None:
    raw = copy.deepcopy(_raw())
    del raw["regions"]["GB"]
    with pytest.raises(ValidationError):
        EmergencyResources.model_validate(raw)


def test_staleness() -> None:
    data = EmergencyResources.from_yaml(PATH)
    assert not data.is_stale(data.last_verified)
    assert not data.is_stale(data.last_verified + timedelta(days=data.max_age_days))
    assert data.is_stale(data.last_verified + timedelta(days=data.max_age_days + 1))


def test_check_script_passes_on_verification_date() -> None:
    data = EmergencyResources.from_yaml(PATH)
    assert check(PATH, data.last_verified) == []


def test_check_script_fails_when_stale() -> None:
    data = EmergencyResources.from_yaml(PATH)
    problems = check(PATH, data.last_verified + timedelta(days=data.max_age_days + 1))
    assert any("days old" in p for p in problems)


def test_check_script_rejects_http_sources(tmp_path: Path) -> None:
    raw = copy.deepcopy(_raw())
    raw["regions"]["US"]["resources"][0]["source_urls"] = ["http://example.org/"]
    bad = tmp_path / "resources.yaml"
    bad.write_text(yaml.safe_dump(raw), encoding="utf-8")
    problems = check(bad, date.fromisoformat(str(raw["last_verified"])))
    assert any("not https" in p for p in problems)
