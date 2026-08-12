from __future__ import annotations

from pathlib import Path

from cip.modules.public_footprint.infrastructure.search_registry import (
    load_search_query_templates,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "policies" / "search_query_templates.yml"

EXPECTED_TEMPLATE_IDS = {
    "q-procurement-contracts",
    "q-products-providers",
    "q-soc-siem-mdr-xdr-soar",
    "q-iam-pam-iga-zero-trust",
    "q-cloud-kubernetes",
    "q-appsec-devsecops-sast-dast-sca-sbom",
    "q-pentest-red-purple",
    "q-grc-compliance",
    "q-incidents-ransomware-regulator",
    "q-hiring-team-growth",
    "q-architecture-migration-transformation",
    "q-partners-customers-case-studies",
    "q-reports-presentations-standards-publications",
}


def test_sa15_dork_library_covers_every_required_family() -> None:
    registry = load_search_query_templates(REGISTRY_PATH)
    templates = registry.all()

    assert {template.query_id for template in templates} == EXPECTED_TEMPLATE_IDS
    assert len(templates) == len(EXPECTED_TEMPLATE_IDS)
    assert len({template.query for template in templates}) == len(templates)


def test_sa15_dork_library_is_versioned_and_manual_only() -> None:
    registry = load_search_query_templates(REGISTRY_PATH)

    for template in registry.all():
        assert template.version == 2
        assert template.source == "google"
        assert template.endpoint == "https://www.google.com/search"
        assert template.license_tag == "manual-link"
        assert template.robots_status == "not-automated"
        assert template.enabled is False
        assert "{organization}" in template.query
        assert template.allowed_stored_fields == (
            "url",
            "title",
            "snippet",
            "fetched_at",
            "query_id",
            "metadata",
        )
