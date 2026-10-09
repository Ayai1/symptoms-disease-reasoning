"""CI gate for the emergency resources file (DECISIONS.md D-002).

Fails when the file is invalid, a source URL is not HTTPS, or ``last_verified``
is older than ``max_age_days``. Fix by re-verifying every number against its
listed sources and updating ``last_verified`` in the same commit.

Usage: uv run python scripts/check_emergency_resources.py [--today YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from app.config import SAFETY_DATA_DIR
from app.safety.resources import EmergencyResources

DEFAULT_PATH = SAFETY_DATA_DIR / "emergency_resources.yaml"


def check(path: Path, today: date) -> list[str]:
    """Return a list of problems; empty when the file passes."""
    try:
        data = EmergencyResources.from_yaml(path)
    except Exception as exc:  # report any load or validation failure
        return [f"invalid file: {exc}"]

    problems: list[str] = []
    for code, region in data.regions.items():
        for resource in region.resources:
            for url in resource.source_urls:
                if url.scheme != "https":
                    problems.append(f"{code}/{resource.id}: source is not https: {url}")
    if data.last_verified > today:
        problems.append(f"last_verified {data.last_verified} is in the future")
    if data.is_stale(today):
        problems.append(
            f"last_verified {data.last_verified} is {data.age_days(today)} days old "
            f"(limit {data.max_age_days}). Re-verify every number against its source_urls "
            "and update last_verified."
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = parser.parse_args(argv)

    problems = check(args.path, args.today)
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return 1
    print(f"OK: {args.path.name} verified {EmergencyResources.from_yaml(args.path).last_verified}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
