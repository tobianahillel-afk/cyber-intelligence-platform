from __future__ import annotations

import tomllib
from pathlib import Path

from cip import __version__
from cip.main import create_app

PROJECT_FILE = Path("pyproject.toml")


def test_application_version_has_one_authoritative_value() -> None:
    project = tomllib.loads(PROJECT_FILE.read_text(encoding="utf-8"))
    project_version = project["project"]["version"]
    api_version = create_app().version

    assert project_version == __version__ == api_version


def test_runtime_version_uses_semantic_versioning() -> None:
    parts = __version__.split(".")

    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
