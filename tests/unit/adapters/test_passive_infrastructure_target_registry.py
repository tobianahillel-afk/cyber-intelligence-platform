from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from cip.adapters.sources.passive_infrastructure.registry import (
    load_passive_infrastructure_targets,
)

ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000000305")


def test_checked_in_passive_target_registry_is_empty_by_default() -> None:
    targets = load_passive_infrastructure_targets(
        Path("policies/passive_infrastructure_targets.yml")
    )

    assert targets == ()


def test_target_registry_normalizes_public_domain(tmp_path: Path) -> None:
    path = tmp_path / "targets.yml"
    path.write_text(
        f"""version: 1
targets:
  - target_id: example
    organization_id: {ORGANIZATION_ID}
    domain: EXAMPLE.COM.
    enabled: true
""",
        encoding="utf-8",
    )

    targets = load_passive_infrastructure_targets(path)

    assert targets[0].domain == "example.com"
    assert targets[0].enabled is True


@pytest.mark.parametrize("domain", ["localhost", "corp.local", "example.invalid", "10.0.0.1"])
def test_target_registry_rejects_non_public_domains(tmp_path: Path, domain: str) -> None:
    path = tmp_path / "targets.yml"
    path.write_text(
        f"""version: 1
targets:
  - target_id: invalid
    organization_id: {ORGANIZATION_ID}
    domain: {domain}
    enabled: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_passive_infrastructure_targets(path)


def test_target_registry_rejects_duplicate_target_ids(tmp_path: Path) -> None:
    path = tmp_path / "targets.yml"
    path.write_text(
        f"""version: 1
targets:
  - target_id: duplicate
    organization_id: {ORGANIZATION_ID}
    domain: example.com
  - target_id: duplicate
    organization_id: {ORGANIZATION_ID}
    domain: example.org
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate passive infrastructure target_id"):
        load_passive_infrastructure_targets(path)
