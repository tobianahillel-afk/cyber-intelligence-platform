from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from cip.adapters.sources.passive_infrastructure.rdap_registry import (
    RdapTarget,
    RdapTargetFile,
    RdapTargetKind,
    load_rdap_targets,
)
from cip.adapters.sources.passive_infrastructure.rdap_schemas import PublicRdapObject

ORG_ID = UUID("00000000-0000-0000-0000-000000000811")


def test_rdap_target_normalizes_supported_resource_kinds() -> None:
    domain = _target(RdapTargetKind.DOMAIN, "Example.COM.")
    ipv4 = _target(RdapTargetKind.IPV4, "8.8.8.8")
    ipv6 = _target(RdapTargetKind.IPV6, "2606:4700:4700::1111")
    asn = _target(RdapTargetKind.ASN, "64497")

    assert domain.value == "example.com"
    assert ipv4.value == "8.8.8.8"
    assert ipv6.value == "2606:4700:4700::1111"
    assert asn.value == "AS64497"


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        (RdapTargetKind.DOMAIN, "8.8.8.8"),
        (RdapTargetKind.IPV4, "10.0.0.1"),
        (RdapTargetKind.IPV6, "2001:db8::1"),
        (RdapTargetKind.ASN, "AS0"),
        (RdapTargetKind.ASN, "not-an-asn"),
    ],
)
def test_rdap_target_rejects_wrong_or_non_global_resources(
    kind: RdapTargetKind,
    value: str,
) -> None:
    with pytest.raises(ValueError):
        _target(kind, value)


def test_rdap_target_file_rejects_duplicate_resource(tmp_path: Path) -> None:
    path = tmp_path / "rdap.yml"
    path.write_text(
        """version: 1
targets:
  - target_id: one
    organization_id: 00000000-0000-0000-0000-000000000811
    kind: domain
    value: example.com
    enabled: false
  - target_id: two
    organization_id: 00000000-0000-0000-0000-000000000811
    kind: domain
    value: EXAMPLE.COM.
    enabled: false
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate RDAP target resource"):
        load_rdap_targets(path)


def test_public_rdap_schema_drops_entities_and_vcards() -> None:
    record = PublicRdapObject.model_validate(
        {
            "objectClassName": "domain",
            "handle": "EXAMPLE",
            "ldhName": "example.com",
            "entities": [
                {
                    "handle": "private-person",
                    "vcardArray": [
                        "vcard",
                        [["email", {}, "text", "private@example.com"]],
                    ],
                }
            ],
        }
    )

    serialized = record.model_dump_json()
    assert "entities" not in serialized
    assert "private-person" not in serialized
    assert "private@example.com" not in serialized


def test_checked_in_rdap_registry_is_empty_by_default() -> None:
    parsed = RdapTargetFile.model_validate(
        {"version": 1, "targets": list(load_rdap_targets(Path("policies/rdap_targets.yml")))}
    )
    assert parsed.targets == []


def _target(kind: RdapTargetKind, value: str) -> RdapTarget:
    return RdapTarget(
        target_id=f"target-{kind.value}",
        organization_id=ORG_ID,
        kind=kind,
        value=value,
        enabled=False,
    )
