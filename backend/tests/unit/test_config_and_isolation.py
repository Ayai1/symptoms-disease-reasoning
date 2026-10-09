from __future__ import annotations

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import PACKAGE_DIR, Settings


def test_cors_origins_from_comma_separated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_CORS_ORIGINS", "https://a.example/, http://localhost:3000")
    assert Settings().cors_origins == ["https://a.example", "http://localhost:3000"]


def test_wildcard_cors_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(cors_origins=["*"])


FORBIDDEN_IN_SAFETY = (
    "app.llm",
    "app.reasoning",
    "app.nlu",
    "app.retrieval",
    "anthropic",
    "openai",
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_safety_package_has_no_model_or_llm_dependency() -> None:
    """DECISIONS.md D-005: the safety path never depends on models or LLMs."""
    for path in (PACKAGE_DIR / "safety").glob("*.py"):
        for name in _imports(path):
            assert not name.startswith(FORBIDDEN_IN_SAFETY), f"{path.name} imports {name}"


def test_no_pickle_in_application_code() -> None:
    for path in PACKAGE_DIR.rglob("*.py"):
        assert "pickle" not in _imports(path), path.name
