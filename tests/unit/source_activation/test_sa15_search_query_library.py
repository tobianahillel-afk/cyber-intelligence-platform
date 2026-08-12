from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from cip.modules.public_footprint.infrastructure.manual_search import (
    build_google_analyst_search_url,
)
from cip.modules.public_footprint.infrastructure.search_registry import (
    load_search_query_templates,
)

ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = ROOT / "policies" / "search_query_templates.yml"

EXPECTED_TEMPLATE_IDS = {
    "q-site-company-research",
    "q-filetype-documents",
    "q-intitle-inurl-research",
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
    "q-code-package-developer-evidence",
}


def test_sa15_dork_library_covers_every_required_family() -> None:
    templates = load_search_query_templates(REGISTRY_PATH)

    assert {template.id for template in templates} == EXPECTED_TEMPLATE_IDS
    assert len(templates) == len(EXPECTED_TEMPLATE_IDS)
    assert len({template.query_pattern for template in templates}) == len(templates)

    combined = " ".join(template.query_pattern for template in templates).casefold()
    for operator in ("site:", "filetype:", "intitle:", "inurl:"):
        assert operator in combined
    for term in ("procurement", "siem", "zero trust", "kubernetes", "sbom"):
        assert term in combined


def test_sa15_dork_library_is_versioned_disabled_and_uses_correct_placeholders() -> None:
    templates = load_search_query_templates(REGISTRY_PATH)

    for template in templates:
        assert template.version == 2
        assert template.purpose.startswith("corporate-public-footprint")
        assert template.enabled is False
        if template.id == "q-site-company-research":
            assert template.query_pattern.count("{domain}") == 1
            assert "{organization}" not in template.query_pattern
            with pytest.raises(ValueError, match="organization_domain"):
                template.render("Example Corp")
            rendered = template.render(
                "Example Corp",
                organization_domain="example.com",
            )
            assert rendered.startswith("site:example.com ")
        else:
            assert template.query_pattern.count("{organization}") == 1
            assert "{domain}" not in template.query_pattern
            rendered = template.render("Example Corp")
            assert "{organization}" not in rendered
            assert "Example Corp" in rendered


def test_sa15_google_route_builds_manual_link_without_network_io() -> None:
    templates = load_search_query_templates(REGISTRY_PATH)
    template = next(item for item in templates if item.id == "q-filetype-documents")

    url = build_google_analyst_search_url(template, "Example Corp")
    parsed = urlparse(url)

    assert parsed.scheme == "https"
    assert parsed.netloc == "www.google.com"
    assert parsed.path == "/search"
    query = parse_qs(parsed.query)["q"][0]
    assert "Example Corp" in query
    assert "filetype:pdf" in query


def test_sa15_google_site_route_uses_domain_not_display_name() -> None:
    templates = load_search_query_templates(REGISTRY_PATH)
    template = next(item for item in templates if item.id == "q-site-company-research")

    url = build_google_analyst_search_url(
        template,
        "Example Corp",
        organization_domain="example.com",
    )
    query = parse_qs(urlparse(url).query)["q"][0]

    assert query.startswith("site:example.com ")
    assert "site:Example Corp" not in query
