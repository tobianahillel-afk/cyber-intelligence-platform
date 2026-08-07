from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from cip.adapters.sources.vendor_advisory_catalogs.mappers import map_vendor_advisory
from cip.adapters.sources.vendor_advisory_catalogs.schemas import ProviderAdvisoryRecord
from cip.modules.vulnerability_applicability.domain.enums import AdvisoryRevisionState

NOW = datetime(2026, 8, 7, 0, 0, tzinfo=UTC)


def payload() -> dict[str, object]:
    return {
        "record_id": "ADV-2026-1:r1",
        "advisory_id": "ADV-2026-1",
        "source_url": "https://security.example.test/ADV-2026-1",
        "state": "current",
        "published_at": NOW.isoformat(),
        "modified_at": NOW.isoformat(),
        "vulnerabilities": ["CVE-2026-0001"],
        "affected_ranges": [
            {
                "product": {
                    "vendor": "Example",
                    "product": "Gateway",
                    "component": "Core",
                    "ecosystem": "vendor",
                    "identifiers": ["cpe:2.3:a:example:gateway:*:*:*:*:*:*:*:*"],
                },
                "scheme": "semver",
                "boundaries": [
                    {"kind": "introduced", "version": "1.0.0", "inclusive": True},
                    {"kind": "fixed", "version": "2.0.0", "inclusive": False},
                ],
                "precision": "version",
            }
        ],
        "fixed_versions": ["2.0.0"],
        "workarounds": ["Disable the optional remote service"],
        "metadata_only": True,
    }


def test_strict_schema_maps_to_domain_revision() -> None:
    record = ProviderAdvisoryRecord.model_validate(payload())
    revision = map_vendor_advisory(record, source_id="official-vendor-psirt")

    assert revision.state is AdvisoryRevisionState.CURRENT
    assert revision.vulnerabilities == ("cve-2026-0001",)
    assert revision.affected_ranges[0].product.vendor == "example"
    assert revision.fixed_versions == ("2.0.0",)
    assert revision.active_validation_performed is False


def test_schema_rejects_unknown_fields() -> None:
    value = payload()
    value["unexpected"] = True

    with pytest.raises(ValidationError, match="extra_forbidden"):
        ProviderAdvisoryRecord.model_validate(value)


def test_schema_rejects_embedded_credentials() -> None:
    value = payload()
    value["source_url"] = "https://user:secret@security.example.test/advisory"

    with pytest.raises(ValidationError, match="embedded credentials"):
        ProviderAdvisoryRecord.model_validate(value)


def test_schema_rejects_active_or_binary_collection() -> None:
    for field_name in ("active_probe", "direct_connection", "exploit_attempt"):
        value = payload()
        value[field_name] = True
        with pytest.raises(ValidationError, match="active validation"):
            ProviderAdvisoryRecord.model_validate(value)

    value = payload()
    value["binary_payload"] = "not-allowed"
    with pytest.raises(ValidationError, match="binary payloads"):
        ProviderAdvisoryRecord.model_validate(value)


def test_schema_preserves_correction_reference() -> None:
    value = payload()
    value["state"] = "corrected"
    value["record_id"] = "ADV-2026-1:r2"
    value["supersedes_record_key"] = "ADV-2026-1:r1"

    revision = map_vendor_advisory(
        ProviderAdvisoryRecord.model_validate(value),
        source_id="official-vendor-psirt",
    )

    assert revision.state is AdvisoryRevisionState.CORRECTED
    assert revision.supersedes_record_key == "adv-2026-1:r1"
