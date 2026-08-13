from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid4, uuid5

from cip.adapters.sources.public_web.provisioning import AUTOMATIC_PUBLIC_WEB_SOURCE_ID
from cip.modules.collection_orchestration.application.automatic_public_web_runtime import (
    AutomaticPublicWebRuntimeConfig,
    build_automatic_public_web_runtime,
)
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import (
    create_database_engine,
    create_session_factory,
    session_scope,
)

_TARGETS = (
    ("Example COM", "https://example.com/"),
    ("Example ORG", "https://example.org/"),
    ("Example NET", "https://example.net/"),
    ("Python", "https://www.python.org/"),
    ("Python Docs", "https://docs.python.org/"),
    ("PyPI", "https://pypi.org/"),
    ("Django", "https://www.djangoproject.com/"),
    ("Rust", "https://www.rust-lang.org/"),
    ("Go", "https://go.dev/"),
    ("Node.js", "https://nodejs.org/"),
    ("Kubernetes", "https://kubernetes.io/"),
    ("PostgreSQL", "https://www.postgresql.org/"),
    ("SQLite", "https://sqlite.org/"),
    ("GNU", "https://www.gnu.org/"),
    ("W3C", "https://www.w3.org/"),
    ("IETF", "https://www.ietf.org/"),
    ("RFC Editor", "https://www.rfc-editor.org/"),
    ("curl", "https://curl.se/"),
    ("OpenSSL", "https://www.openssl.org/"),
    ("Apache HTTP Server", "https://httpd.apache.org/"),
)


def main() -> None:
    now = datetime.now(UTC)
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)
    organization_ids = tuple(uuid5(NAMESPACE_URL, url) for _, url in _TARGETS)
    with session_scope(factory) as session:
        session.add_all(_organization_record(name, url, now) for name, url in _TARGETS)
    config = AutomaticPublicWebRuntimeConfig(
        enabled=True,
        organization_ids=organization_ids,
        authorization_reference="sa16-l08-controlled-neutral-public-targets",
        reviewed_at=now,
        refresh_interval_seconds=86_400,
        max_link_depth=0,
        max_pages=2,
        max_total_bytes=2_000_000,
        max_resource_bytes=1_000_000,
        max_redirects=3,
    )
    with session_scope(factory) as session:
        bundle = build_automatic_public_web_runtime(
            session,
            config,
            now=now,
            timeout_seconds=30.0,
        )
    if len(bundle.targets) != len(_TARGETS):
        raise RuntimeError("SA16-L08 runtime did not build every approved target")
    targets_by_id = {target.id: target for target in bundle.targets}
    successes = 0
    for schedule in bundle.schedules:
        identity = (schedule.source_id, schedule.adapter_id)
        adapter = bundle.adapters.get(identity)
        target = targets_by_id.get(schedule.source_id)
        if adapter is None or target is None:
            raise RuntimeError(f"SA16-L08 missing runtime binding: {identity}")
        if target.source_id != AUTOMATIC_PUBLIC_WEB_SOURCE_ID:
            raise RuntimeError("SA16-L08 target lost governed source provenance")
        if target.id == target.source_id:
            raise RuntimeError("SA16-L08 collapsed target and governed source identities")
        batch = adapter.collect(
            collection_job_id=uuid4(),
            checkpoint_payload=None,
            collected_at=now,
            retention_until=now + timedelta(days=30),
        )
        pages = batch.checkpoint_payload.get("pages")
        if not isinstance(pages, dict) or target.base_url not in pages:
            raise RuntimeError(f"SA16-L08 homepage was not checkpointed: {target.base_url}")
        if not batch.observations or not batch.public_footprint_projections:
            raise RuntimeError(f"SA16-L08 produced no data: {target.base_url}")
        if any(
            observation.source_id != AUTOMATIC_PUBLIC_WEB_SOURCE_ID
            for observation in batch.observations
        ):
            raise RuntimeError(f"SA16-L08 lost observation provenance: {target.base_url}")
        if any(
            not projection.resource.canonical_url.startswith(target.base_url)
            for projection in batch.public_footprint_projections
        ):
            raise RuntimeError(f"SA16-L08 escaped approved origin: {target.base_url}")
        successes += 1
        print(
            "SA16-L08 target passed: "
            f"target={target.id} source={target.source_id} url={target.base_url} "
            f"observations={len(batch.observations)} "
            f"projections={len(batch.public_footprint_projections)}"
        )
    if successes != len(_TARGETS):
        raise RuntimeError("SA16-L08 did not validate every controlled target")
    print(f"SA-16 L08 multi-target live validation passed: targets={successes}")


def _organization_record(
    name: str,
    url: str,
    now: datetime,
) -> OrganizationRecord:
    return OrganizationRecord(
        id=uuid5(NAMESPACE_URL, url),
        canonical_name=name,
        legal_name=None,
        country_code=None,
        website_url=url,
        registration_ids=[],
        created_at=now,
        updated_at=now,
    )


if __name__ == "__main__":
    main()
