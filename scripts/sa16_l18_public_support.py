from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from cip.adapters.sources.public_web.artifact_context import BrowserArtifactExecutionContext
from cip.adapters.sources.public_web.browser_action_executor import (
    execute_public_browser_action_plan,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.automatic_public_web_runtime import (
    AutomaticPublicWebRuntimeConfig,
)
from cip.modules.collection_orchestration.infrastructure.models import (
    CollectionCheckpointRecord,
    CollectionJobRecord,
)
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.public_footprint.domain import (
    PublicResourceKind,
    PublicStructuredStateKind,
    PublicSurfaceKind,
)
from cip.modules.public_footprint.domain.artifacts import BrowserScreenshotMode
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionKind,
    BrowserActionPlan,
    BrowserActionStep,
    BrowserHttpMethod,
    BrowserTransitionRule,
)
from cip.modules.public_footprint.infrastructure.artifact_persistence import (
    load_browser_artifacts_for_plan,
    persist_browser_artifact,
)
from cip.modules.public_footprint.infrastructure.browser_action_persistence import (
    persist_browser_action_plan,
    save_browser_action_checkpoint,
)
from cip.modules.public_footprint.infrastructure.models import (
    PublicResourceRecord,
    PublicResourceVersionRecord,
    PublicStructuredStateRecord,
    PublicSurfaceReferenceRecord,
)
from cip.modules.public_footprint.infrastructure.projections import (
    persist_public_footprint_projections,
)
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    HttpMethod,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.modules.source_portfolio.application.service import (
    get_source_health,
    sync_source_portfolio,
)
from cip.modules.source_portfolio.domain.models import (
    AdapterCapabilityManifest,
    CatalogStatus,
    CollectionMode,
    SourceCatalogEntry,
)
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import (
    create_database_engine,
    create_session_factory,
    session_scope,
)

_REQUIRED_SURFACES = frozenset(
    {
        PublicSurfaceKind.RESPONSE_HEADER.value,
        PublicSurfaceKind.CANONICAL_LINK.value,
        PublicSurfaceKind.ALTERNATE_LINK.value,
        PublicSurfaceKind.STYLESHEET.value,
        PublicSurfaceKind.SCRIPT.value,
        PublicSurfaceKind.RESOURCE_REFERENCE.value,
        PublicSurfaceKind.FORM_ENDPOINT.value,
        PublicSurfaceKind.DOCUMENT_LINK.value,
        PublicSurfaceKind.MEDIA_LINK.value,
    }
)
_SECRET_MARKERS = ("must-drop", "accesstoken", "sessionid", "password")


def build_factory(
    root: Path,
    organization_id: UUID,
    origin: str,
    now: datetime,
) -> sessionmaker[Session]:
    engine = create_database_engine(f"sqlite+pysqlite:///{root / 'l18-public.sqlite'}")
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)
    with session_scope(factory) as session:
        session.add(
            OrganizationRecord(
                id=organization_id,
                canonical_name="SA16 L18 public composite fixture",
                legal_name=None,
                country_code=None,
                website_url=origin,
                registration_ids=[],
                created_at=now,
                updated_at=now,
            )
        )
    return factory


def runtime_config(
    organization_id: UUID,
    now: datetime,
) -> AutomaticPublicWebRuntimeConfig:
    return AutomaticPublicWebRuntimeConfig(
        enabled=True,
        organization_ids=(organization_id,),
        authorization_reference="sa16-l18-public-static-approval",
        reviewed_at=now,
        refresh_interval_seconds=300,
        max_link_depth=2,
        max_pages=12,
        max_total_bytes=4_000_000,
        max_resource_bytes=1_000_000,
        max_redirects=2,
        crawl_deadline_seconds=20,
        max_crawl_concurrency=3,
        browser_fallback_enabled=True,
        browser_authorization_reference="sa16-l18-public-browser-approval",
        browser_reviewed_at=now,
        browser_min_static_text_chars=200,
        browser_max_pages=2,
    )


def prepare_worker_source(
    factory: sessionmaker[Session],
    source_id: str,
    adapter_id: str,
    fixture_host: str,
    now: datetime,
) -> None:
    with session_scope(factory) as session:
        sync_source_portfolio(
            session,
            (
                SourceCatalogEntry(
                    source_id=source_id,
                    display_name="SA16 L18 controlled automatic public target",
                    canonical_url=f"https://{fixture_host}/",
                    category="public_web",
                    status=CatalogStatus.EXECUTABLE,
                    freshness_max_age_seconds=300,
                    commercial_use_cases=("corporate_public_footprint",),
                    adapter=AdapterCapabilityManifest(
                        source_id=source_id,
                        adapter_id=adapter_id,
                        adapter_version="1",
                        provider_schema_version="sa16-l18-public-v1",
                        modes=frozenset({CollectionMode.INCREMENTAL_CURSOR}),
                        canonical_output_types=(
                            "raw_observation",
                            "public_footprint_projection",
                        ),
                        supports_corrections=True,
                        supports_tombstones=True,
                        cost_per_request=0,
                    ),
                    authorization_expires_at=now + timedelta(days=1),
                    monthly_cost_limit=0,
                ),
            ),
            now=now,
        )


def health_values(
    factory: sessionmaker[Session],
    source_id: str,
) -> dict[str, object]:
    with factory() as session:
        health = get_source_health(session, source_id)
        payload = health.operational_metrics
        if payload.get("namespace") != "public_web.crawl.v1":
            raise RuntimeError("L18 public worker persisted no crawl health namespace")
        values = payload.get("values")
        if not isinstance(values, dict):
            raise RuntimeError("L18 public crawl health values are malformed")
        return dict(values)


def verify_public_persistence(
    factory: sessionmaker[Session],
    organization_id: UUID,
    target_id: str,
    adapter_id: str,
) -> None:
    with factory() as session:
        surfaces = set(session.scalars(select(PublicSurfaceReferenceRecord.kind)))
        missing = _REQUIRED_SURFACES - surfaces
        if missing:
            raise RuntimeError(f"L18 public surface inventory missing: {sorted(missing)}")
        states = tuple(session.scalars(select(PublicStructuredStateRecord)))
        state_kinds = {state.kind for state in states}
        required_states = {
            PublicStructuredStateKind.NETWORK_JSON.value,
            PublicStructuredStateKind.SCRIPT_STATE.value,
        }
        if not required_states.issubset(state_kinds):
            raise RuntimeError("L18 rendered structured state is incomplete")
        for state in states:
            payload = state.payload_json.casefold()
            if any(marker in payload for marker in _SECRET_MARKERS):
                raise RuntimeError("L18 persisted sensitive rendered structured state")
        resources = tuple(session.scalars(select(PublicResourceRecord)))
        if not any(item.kind == PublicResourceKind.DOCUMENT.value for item in resources):
            raise RuntimeError("L18 crawler persisted no document resource")
        versions = tuple(session.scalars(select(PublicResourceVersionRecord)))
        if not any(
            item.mime_type == "application/x-public-resource-tombstone" for item in versions
        ):
            raise RuntimeError("L18 crawler persisted no tombstone version")
        checkpoint = session.get(CollectionCheckpointRecord, (target_id, adapter_id))
        if checkpoint is None or not checkpoint.payload.get("pages"):
            raise RuntimeError("L18 public crawl checkpoint was not persisted")
        jobs = tuple(session.scalars(select(CollectionJobRecord)))
        if not jobs or any(job.source_id != target_id for job in jobs):
            raise RuntimeError("L18 target-specific public job lineage is inconsistent")
        if any(resource.organization_id != organization_id for resource in resources):
            raise RuntimeError("L18 public evidence lost organization provenance")


def artifact_plan(source_id: str, origin: str, fixture_host: str) -> BrowserActionPlan:
    return BrowserActionPlan(
        plan_id=uuid4(),
        version=1,
        source_id=source_id,
        provider_id="sa16-l18-controlled-public",
        target_id=source_id,
        purpose="corporate-public-footprint",
        steps=(
            BrowserActionStep(
                step_id="navigate",
                kind=BrowserActionKind.NAVIGATE,
                target_url=f"{origin}artifact",
            ),
            BrowserActionStep(
                step_id="screenshot",
                kind=BrowserActionKind.SCREENSHOT,
                selector="main#evidence",
                screenshot_mode=BrowserScreenshotMode.ELEMENT,
            ),
            BrowserActionStep(
                step_id="download",
                kind=BrowserActionKind.DOWNLOAD,
                selector="a#download",
                expected_download_url=f"{origin}artifact-download.txt",
            ),
        ),
        allowed_transitions=(
            BrowserTransitionRule(
                host=fixture_host,
                path_prefix="/",
                methods=frozenset({BrowserHttpMethod.GET}),
            ),
        ),
        max_actions=3,
        max_total_value_chars=0,
    )


def run_artifact_plan(
    factory: sessionmaker[Session],
    target: PublicWebTarget,
    plan: BrowserActionPlan,
    now: datetime,
) -> None:
    with session_scope(factory) as session:
        checkpoint = persist_browser_action_plan(session, plan, now=now)
    with httpx.Client(follow_redirects=False, trust_env=False) as client:
        context = BrowserArtifactExecutionContext(
            job_id=uuid4(),
            captured_at=now,
            retention_until=now + timedelta(days=1),
            download_client=client,
        )
        with session_scope(factory) as session:
            result = execute_public_browser_action_plan(
                target,
                _artifact_entry(target, now),
                plan,
                checkpoint,
                collected_at=now,
                checkpoint_writer=lambda value: save_browser_action_checkpoint(
                    session,
                    value,
                    now=now,
                ),
                artifact_context=context,
            )
            for artifact in result.artifacts:
                persist_browser_artifact(session, artifact, now=now)
            persist_public_footprint_projections(
                session,
                result.public_footprint_projections,
                now=now,
            )


def verify_artifacts(
    factory: sessionmaker[Session],
    plan: BrowserActionPlan,
) -> None:
    with factory() as session:
        artifacts = load_browser_artifacts_for_plan(session, plan.plan_id, plan.version)
    if len(artifacts) != 2:
        raise RuntimeError("L18 public artifact plan did not persist screenshot and download")
    if any(item.raw_retained or item.storage_uri is not None for item in artifacts):
        raise RuntimeError("L18 public artifact plan retained raw bytes against policy")
    if not any(item.excerpt and "browser download" in item.excerpt for item in artifacts):
        raise RuntimeError("L18 browser download produced no parsed evidence excerpt")


def _artifact_entry(target: PublicWebTarget, now: datetime) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        policy=SourcePolicy(
            id=target.id,
            name="SA16 L18 controlled public artifacts",
            base_url=target.base_url,
            status=SourceStatus.ENABLED,
            source_type=SourceType.BROWSER,
            owner="CIP controlled L18 validation",
            licence="Repository-owned first-party fixture",
            allowed_data_categories=frozenset({DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}),
            retention_days=1,
            raw_content_storage=False,
            human_review_required=False,
        ),
        authorization=SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="sa16-l18-public-artifact-approval",
            reviewed_at=now,
            approved_hosts=frozenset({target.host}),
            approved_path_prefixes=("/",),
            approved_purposes=frozenset({"corporate-public-footprint"}),
            approved_http_methods=frozenset({HttpMethod.GET}),
            automated_collection_allowed=True,
            raw_storage_allowed=False,
        ),
        economics={"monthly_cost": 0},
    )
