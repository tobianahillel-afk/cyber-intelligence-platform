from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from cip.adapters.sources.incident_catalogs.sec_registry import load_sec_incident_targets

ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000000406")


def test_checked_in_sec_target_registry_is_empty_by_default() -> None:
    targets = load_sec_incident_targets(Path("policies/sec_incident_targets.yml"))

    assert targets == ()


def test_sec_target_registry_accepts_exact_ten_digit_cik(tmp_path: Path) -> None:
    path = tmp_path / "targets.yml"
    path.write_text(
        f"""version: 1
targets:
  - target_id: issuer
    organization_id: {ORGANIZATION_ID}
    cik: "0000320193"
    enabled: true
""",
        encoding="utf-8",
    )

    targets = load_sec_incident_targets(path)

    assert targets[0].cik == "0000320193"
    assert targets[0].enabled is True


@pytest.mark.parametrize("cik", ["320193", "000032019A", "00000320193", ""])
def test_sec_target_registry_rejects_noncanonical_ciks(
    tmp_path: Path,
    cik: str,
) -> None:
    path = tmp_path / "targets.yml"
    path.write_text(
        f"""version: 1
targets:
  - target_id: invalid
    organization_id: {ORGANIZATION_ID}
    cik: "{cik}"
    enabled: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_sec_incident_targets(path)


def test_sec_target_registry_rejects_duplicate_cik(tmp_path: Path) -> None:
    path = tmp_path / "targets.yml"
    path.write_text(
        f"""version: 1
targets:
  - target_id: issuer-one
    organization_id: {ORGANIZATION_ID}
    cik: "0000320193"
  - target_id: issuer-two
    organization_id: 00000000-0000-0000-0000-000000000407
    cik: "0000320193"
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate SEC CIK target"):
        load_sec_incident_targets(path)
