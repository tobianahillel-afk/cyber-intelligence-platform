from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy import func, select

from cip.adapters.sources.public_web.provisioning import (
    AutomaticPublicWebPolicy,
    provision_public_web_target,
)
from cip.modules.collection_orchestration.application.public_web_adapter import PublicWebAdapter
from cip.modules.organizations.domain.entities import Organization
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.public_footprint.domain import PublicSurfaceKind
from cip.modules.public_footprint.infrastructure.models import PublicSurfaceReferenceRecord
from cip.modules.public_footprint.infrastructure.projections import (
    persist_public_footprint_projections,
)
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import (
    create_database_engine,
    create_session_factory,
    session_scope,
)

_TARGETS = (
    ("Example", "https://example.com/"),
    ("Python", "https://www.python.org/"),
    ("Python Docs", "https://docs.python.org/"),
    ("PyPI", "https://pypi.org/"),
    ("Django", "https://www.djangoproject.com/"),
    ("FreeBSD", "https://www.freebsd.org/"),
    ("Go", "https://go.dev/"),
    ("Node.js", "https://nodejs.org/"),
    ("Kubernetes", "https://kubernetes.io/"),
    ("PostgreSQL", "https://www.postgresql.org/"),
    ("SQLite", "https://sqlite.org/"),
    ("Linux Kernel", "https://www.kernel.org/"),
    ("IETF", "https://www.ietf.org/"),
    ("RFC Editor", "https://www.rfc-editor.org/"),
    ("curl", "https://curl.se/"),
    ("Debian", "https://www.debian.org/"),
    ("Selenium Web Form", "https://www.selenium.dev/selenium/web/web-form.html"),
    ("Selenium Downloads", "https://www.selenium.dev/downloads/"),
    ("W3C PDF Technique", "https://www.w3.org/WAI/WCAG21/Techniques/pdf/PDF11"),
    ("W3C Easy Checks", "https://www.w3.org/WAI/test-evaluate/preliminary/"),
)
_REQUIRED_KINDS = frozenset(
    {
        PublicSurfaceKind.RESPONSE_HEADER,
        PublicSurfaceKind.CANONICAL_LINK,
        PublicSurfaceKind.ALTERNATE_LINK,
        PublicSurfaceKind.STYLESHEET,
        PublicSurfaceKind.SCRIPT,
        PublicSurfaceKind.RESOURCE_REFERENCE,
        PublicSurfaceKind.FORM_ENDPOINT,
        PublicSurfaceKind.DOCUMENT_LINK,
        PublicSurfaceKind.MEDIA_LINK,
    }
)


def main() -> None:
    now = datetime.now(UTC)
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)
    with session_scope(factory) as session:
        session.add_all(_organization_record(name, url, now) for name, url in _TARGETS)

    seen_kinds: set[PublicSurfaceKind] = set()
    successful = 0
    for name, url in _TARGETS:
        batch = _collect_target(name, url, now)
        projections = batch.public_footprint_projections
        if not projections:
            raise RuntimeError(f"SA16-L10 produced no projections: {url}")
        target_kinds = {
            surface.kind
            for projection in projections
            for surface in projection.surfaces
        }
        if PublicSurfaceKind.RESPONSE_HEADER not in target_kinds:
            raise RuntimeError(f"SA16-L10 captured no approved headers: {url}")
        if name == "Selenium Web Form" and PublicSurfaceKind.FORM_ENDPOINT not in target_kinds:
            raise RuntimeError("SA16-L10 did not inventory the Selenium form endpoint")
        seen_kinds.update(target_kinds)
        with session_scope(factory) as session:
            persist_public_footprint_projections(session, projections, now=now)
        successful += 1
        print(
            f"SA16-L10 target={url} surfaces={len(target_kinds)} "
            f"kinds={','.join(sorted(kind.value for kind in target_kinds))}",
            flush=True,
        )

    missing = _REQUIRED_KINDS - seen_kinds
    if missing:
        names = ",".join(sorted(kind.value for kind in missing))
        raise RuntimeError(f"SA16-L10 live inventory missing surface kinds: {names}")
    with session_scope(factory) as session:
        persisted = int(
            session.scalar(select(func.count()).select_from(PublicSurfaceReferenceRecord)) or 0
        )
        if persisted <= 0:
            raise RuntimeError("SA16-L10 persisted no surface records")
        form_count = int(
            session.scalar(
                select(func.count())
                .select_from(PublicSurfaceReferenceRecord)
                .where(PublicSurfaceReferenceRecord.kind == PublicSurfaceKind.FORM_ENDPOINT.value)
            )
            or 0
        )
        if form_count <= 0:
            raise RuntimeError("SA16-L10 persisted no form endpoint metadata")
    if successful != len(_TARGETS):
        raise RuntimeError("SA16-L10 did not validate every configured target")
    print(
        "SA-16 L10 live validation passed: "
        f"targets={successful} persisted_surfaces={persisted} "
        f"surface_kinds={len(seen_kinds)} form_submissions=0",
        flush=True,
    )


def _collect_target(name: str, url: str, now: datetime):
    origin = _origin(url)
    organization = Organization(
        id=uuid5(NAMESPACE_URL, url),
        canonical_name=name,
        legal_name=None,
        country_code=None,
        website_url=origin,
        registration_ids=(),
        created_at=now,
        updated_at=now,
    )
    policy = AutomaticPublicWebPolicy(
        authorization_reference="sa16-l10-live-approval",
        reviewed_at=now,
        discover_sitemaps=False,
        discover_feeds=False,
        max_link_depth=0,
        max_pages=1,
        max_total_bytes=2_000_000,
        max_resource_bytes=1_000_000,
        max_redirects=3,
    )
    provisioned = provision_public_web_target(organization, policy, first_crawl_at=now)
    target = replace(
        provisioned.target,
        seed_urls=(url,),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
        max_pages=1,
    )
    adapter = PublicWebAdapter(
        provisioned.source_entry,
        target,
        timeout_seconds=30.0,
    )
    return adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=now,
        retention_until=now + timedelta(days=30),
    )


def _origin(url: str) -> str:
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.netloc}/"


def _organization_record(name: str, url: str, now: datetime) -> OrganizationRecord:
    return OrganizationRecord(
        id=uuid5(NAMESPACE_URL, url),
        canonical_name=name,
        legal_name=None,
        country_code=None,
        website_url=_origin(url),
        registration_ids=[],
        created_at=now,
        updated_at=now,
    )


if __name__ == "__main__":
    main()
