from __future__ import annotations

from pathlib import Path

import pytest

from cip.modules.public_footprint.infrastructure.search_registry import (
    load_search_query_templates,
)


def test_repository_search_query_templates_are_versioned_and_disabled() -> None:
    templates = load_search_query_templates(Path("policies/search_query_templates.yml"))

    assert templates
    assert all(template.version >= 1 for template in templates)
    assert all(not template.enabled for template in templates)
    assert len({(template.id, template.version) for template in templates}) == len(templates)
    for template in templates:
        rendered = template.render("Example Corp")
        assert "{organization}" not in rendered
        assert "Example Corp" in rendered


def test_search_query_registry_rejects_duplicate_versions(tmp_path: Path) -> None:
    registry = tmp_path / "search-queries.yml"
    registry.write_text(
        """version: 1
templates:
  - id: duplicate
    version: 1
    enabled: false
    purpose: corporate-public-footprint
    query_pattern: '"{organization}" security'
  - id: duplicate
    version: 1
    enabled: false
    purpose: corporate-public-footprint
    query_pattern: '"{organization}" technology'
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate"):
        load_search_query_templates(registry)
