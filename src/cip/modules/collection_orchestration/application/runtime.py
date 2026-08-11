from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from os import getpid
from socket import gethostname
from time import sleep

from sqlalchemy.orm import Session, sessionmaker

from cip.adapters.sources.ashby.registry import load_ashby_boards
from cip.adapters.sources.crossref_publications.registry import (
    load_crossref_publication_targets,
)
from cip.adapters.sources.developer_ecosystem.registry import load_developer_ecosystem_targets
from cip.adapters.sources.github_code_search.registry import (
    load_github_code_search_templates,
)
from cip.adapters.sources.greenhouse.registry import load_greenhouse_boards
from cip.adapters.sources.incident_catalogs.sec_registry import load_sec_incident_targets
from cip.adapters.sources.lever.registry import load_lever_sites
from cip.adapters.sources.organization_identity.registry import load_organization_identity_targets
from cip.adapters.sources.passive_infrastructure.rdap_registry import load_rdap_targets
from cip.adapters.sources.passive_infrastructure.registry import load_passive_infrastructure_targets
from cip.adapters.sources.patentsview_patents.registry import load_patentsview_patent_targets
from cip.adapters.sources.public_web.registry import load_public_web_targets
from cip.adapters.sources.recruitee.registry import load_recruitee_sites
from cip.adapters.sources.smartrecruiters.registry import load_smartrecruiters_companies
from cip.adapters.sources.teamtailor.registry import load_teamtailor_accounts
from cip.adapters.sources.vulnerability_catalogs.registry import load_vulnerability_query_targets
from cip.modules.collection_orchestration.application.adapter_composition import (
    AdapterCompositionInputs,
    build_runtime_adapters,
)
from cip.modules.collection_orchestration.application.ports import CollectionAdapter
from cip.modules.collection_orchestration.application.provider_secret_supplier import (
    connected_secret_supplier,
)
from cip.modules.collection_orchestration.application.scheduler import schedule_due_jobs
from cip.modules.collection_orchestration.application.worker import (
    WorkerOutcome,
    WorkerStatus,
    run_worker_once,
)
from cip.modules.collection_orchestration.domain.models import SourceSchedule
from cip.modules.collection_orchestration.infrastructure.schedule_bundle import (
    load_collection_schedule_bundle,
)
from cip.modules.data_governance.domain.retention import RetentionPolicy
from cip.modules.data_governance.infrastructure.retention_loader import load_retention_policy
from cip.modules.provider_onboarding.application.service import sync_provider_profiles
from cip.modules.provider_onboarding.infrastructure.registry import load_provider_profiles
from cip.modules.public_footprint.infrastructure.search_registry import load_search_query_templates
from cip.modules.source_governance.infrastructure.persistence import sync_source_registry
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.modules.source_governance.infrastructure.registry_bundle import load_source_registry_bundle
from cip.modules.source_portfolio.application.backfill_worker import (
    BackfillWorkerOutcome,
    BackfillWorkerStatus,
    run_backfill_once,
)
from cip.modules.source_portfolio.application.execution import source_execution_allowed
from cip.modules.source_portfolio.application.service import (
    reconcile_runtime_adapters,
    sync_source_portfolio,
)
from cip.modules.source_portfolio.domain.models import CatalogStatus, SourceCatalogEntry
from cip.modules.source_portfolio.infrastructure.registry_bundle import load_source_portfolio_bundle
from cip.shared.config.settings import Settings
from cip.shared.kernel.time import utc_now
from cip.shared.persistence.session import (
    create_database_engine,
    create_session_factory,
    session_scope,
)

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CollectionRuntime:
    factory: sessionmaker[Session]
    schedules: tuple[SourceSchedule, ...]
    adapters: dict[tuple[str, str], CollectionAdapter]
    retention_policy: RetentionPolicy
    portfolio: tuple[SourceCatalogEntry, ...]


def build_collection_runtime(settings: Settings) -> CollectionRuntime:
    engine = create_database_engine(settings.database_url)
    factory = create_session_factory(engine)
    entries = _load_source_entries(settings)
    portfolio = _load_portfolio(settings)
    adapter_inputs = _load_adapter_inputs(settings, entries)
    profiles = load_provider_profiles(settings.provider_onboarding_registry_path)
    synchronized_at = utc_now()
    with session_scope(factory) as session:
        sync_source_registry(session, entries)
        sync_provider_profiles(session, profiles, now=synchronized_at)
        sync_source_portfolio(session, portfolio, now=synchronized_at)
    adapters = build_runtime_adapters(
        adapter_inputs,
        brave_token_provider=connected_secret_supplier(
            factory,
            source_id="brave-search-api",
            secret_name="api_token",
        ),
        github_code_search_token_provider=connected_secret_supplier(
            factory,
            source_id="github-code-search-metadata",
            secret_name="api_token",
        ),
        patentsview_api_key_provider=connected_secret_supplier(
            factory,
            source_id="patentsview-patent-metadata",
            secret_name="api_key",
        ),
        certspotter_token_provider=connected_secret_supplier(
            factory,
            source_id="certspotter-ct",
            secret_name="api_token",
        ),
        phishtank_token_provider=connected_secret_supplier(
            factory,
            source_id="phishtank-verified-online",
            secret_name="api_token",
        ),
        teamtailor_token_provider=connected_secret_supplier(
            factory,
            source_id="teamtailor-public-jobs",
            secret_name="api_token",
        ),
        sec_user_agent=settings.sec_edgar_user_agent,
        phishtank_user_agent=settings.phishtank_user_agent,
        timeout_seconds=settings.source_http_timeout_seconds,
    )
    with session_scope(factory) as session:
        reconcile_runtime_adapters(session, adapters.keys(), now=utc_now())
    _validate_portfolio_adapters(portfolio, adapters)
    schedules = _load_schedules(settings)
    _validate_registered_schedules(schedules, adapters, portfolio)
    return CollectionRuntime(
        factory=factory,
        schedules=schedules,
        adapters=adapters,
        retention_policy=load_retention_policy(settings.retention_policy_path),
        portfolio=portfolio,
    )


def _load_source_entries(settings: Settings) -> tuple[SourceRegistryEntry, ...]:
    return load_source_registry_bundle(
        settings.source_registry_path,
        settings.identity_source_registry_path,
        settings.company_identity_expansion_source_registry_path,
        settings.decp_source_registry_path,
        settings.procurement_funding_source_registry_path,
        settings.public_web_source_registry_path,
        settings.vulnerability_source_registry_path,
        settings.search_archive_source_registry_path,
        settings.incident_source_registry_path,
        settings.threat_telemetry_source_registry_path,
        settings.passive_exposure_source_registry_path,
        settings.passive_infrastructure_source_registry_path,
        settings.advisory_source_registry_path,
        settings.corporate_change_source_registry_path,
        settings.relationship_source_registry_path,
        settings.conditional_integration_source_registry_path,
        settings.ats_source_registry_path,
    )


def _load_portfolio(settings: Settings) -> tuple[SourceCatalogEntry, ...]:
    return load_source_portfolio_bundle(
        settings.source_portfolio_path,
        settings.company_identity_expansion_source_portfolio_path,
        settings.decp_source_portfolio_path,
        settings.procurement_funding_source_portfolio_path,
        settings.public_web_source_portfolio_path,
        settings.vulnerability_source_portfolio_path,
        settings.search_archive_source_portfolio_path,
        settings.incident_source_portfolio_path,
        settings.threat_telemetry_source_portfolio_path,
        settings.passive_exposure_source_portfolio_path,
        settings.passive_infrastructure_source_portfolio_path,
        settings.advisory_source_portfolio_path,
        settings.corporate_change_source_portfolio_path,
        settings.relationship_source_portfolio_path,
        settings.conditional_integration_source_portfolio_path,
        settings.ats_source_portfolio_path,
    )


def _load_adapter_inputs(
    settings: Settings,
    entries: tuple[SourceRegistryEntry, ...],
) -> AdapterCompositionInputs:
    return AdapterCompositionInputs(
        entries=entries,
        greenhouse_boards=load_greenhouse_boards(settings.greenhouse_board_registry_path),
        lever_sites=load_lever_sites(settings.lever_site_registry_path),
        smartrecruiters_companies=load_smartrecruiters_companies(
            settings.smartrecruiters_company_registry_path
        ),
        ashby_boards=load_ashby_boards(settings.ashby_board_registry_path),
        recruitee_sites=load_recruitee_sites(settings.recruitee_site_registry_path),
        teamtailor_accounts=load_teamtailor_accounts(
            settings.teamtailor_account_registry_path
        ),
        identity_targets=load_organization_identity_targets(
            settings.organization_identity_target_registry_path
        ),
        public_web_targets=load_public_web_targets(settings.public_web_target_registry_path),
        developer_ecosystem_targets=load_developer_ecosystem_targets(
            settings.developer_ecosystem_target_registry_path
        ),
        search_templates=load_search_query_templates(
            settings.search_query_template_registry_path
        ),
        github_code_search_templates=load_github_code_search_templates(
            settings.github_code_search_template_registry_path
        ),
        crossref_publication_targets=load_crossref_publication_targets(
            settings.crossref_publication_target_registry_path
        ),
        patentsview_patent_targets=load_patentsview_patent_targets(
            settings.patentsview_patent_target_registry_path
        ),
        vulnerability_targets=load_vulnerability_query_targets(
            settings.vulnerability_query_target_registry_path
        ),
        passive_infrastructure_targets=load_passive_infrastructure_targets(
            settings.passive_infrastructure_target_registry_path
        ),
        rdap_targets=load_rdap_targets(settings.rdap_target_registry_path),
        sec_incident_targets=load_sec_incident_targets(
            settings.sec_incident_target_registry_path
        ),
    )


def _load_schedules(settings: Settings) -> tuple[SourceSchedule, ...]:
    return load_collection_schedule_bundle(
        settings.collection_schedule_path,
        settings.decp_collection_schedule_path,
        settings.procurement_funding_collection_schedule_path,
        settings.public_web_collection_schedule_path,
        settings.vulnerability_collection_schedule_path,
        settings.search_archive_collection_schedule_path,
        settings.passive_infrastructure_collection_schedule_path,
        settings.incident_collection_schedule_path,
        settings.threat_telemetry_collection_schedule_path,
        settings.ats_collection_schedule_path,
    )


def run_scheduler_once(
    runtime: CollectionRuntime,
    *,
    now: datetime | None = None,
) -> int:
    current = now or utc_now()
    with session_scope(runtime.factory) as session:
        eligible = tuple(
            schedule
            for schedule in runtime.schedules
            if source_execution_allowed(session, schedule.source_id, now=current)
        )
        return schedule_due_jobs(session, eligible, now=current)


def run_scheduler_forever(
    settings: Settings,
    *,
    sleep_fn: Callable[[float], None] = sleep,
    max_iterations: int | None = None,
) -> None:
    runtime = build_collection_runtime(settings)
    iterations = 0
    while max_iterations is None or iterations < max_iterations:
        created = run_scheduler_once(runtime)
        LOGGER.info("collection scheduler created %s job(s)", created)
        iterations += 1
        if max_iterations is None or iterations < max_iterations:
            sleep_fn(settings.scheduler_poll_seconds)


def run_worker_forever(
    settings: Settings,
    *,
    worker_id: str | None = None,
    sleep_fn: Callable[[float], None] = sleep,
    max_iterations: int | None = None,
) -> None:
    runtime = build_collection_runtime(settings)
    identity = worker_id or f"{gethostname()}:{getpid()}"
    iterations = 0
    while max_iterations is None or iterations < max_iterations:
        outcome = run_worker_once(
            runtime.factory,
            worker_id=identity,
            adapters=runtime.adapters,
            retention_policy=runtime.retention_policy,
        )
        _log_worker_outcome(outcome)
        backfill_outcome = BackfillWorkerOutcome(BackfillWorkerStatus.IDLE)
        if outcome.status is WorkerStatus.IDLE:
            backfill_outcome = run_backfill_once(
                runtime.factory,
                worker_id=identity,
                adapters=runtime.adapters,
                retention_policy=runtime.retention_policy,
            )
            _log_backfill_outcome(backfill_outcome)
        iterations += 1
        if (
            outcome.status is WorkerStatus.IDLE
            and backfill_outcome.status is BackfillWorkerStatus.IDLE
            and (max_iterations is None or iterations < max_iterations)
        ):
            sleep_fn(settings.worker_poll_seconds)


def _validate_registered_schedules(
    schedules: tuple[SourceSchedule, ...],
    adapters: dict[tuple[str, str], CollectionAdapter],
    portfolio: tuple[SourceCatalogEntry, ...],
) -> None:
    portfolio_by_id = {entry.source_id: entry for entry in portfolio}
    missing: list[str] = []
    for schedule in schedules:
        identity = (schedule.source_id, schedule.adapter_id)
        if not schedule.enabled or identity in adapters:
            continue
        entry = portfolio_by_id.get(schedule.source_id)
        conditional = (
            entry is not None
            and entry.status is CatalogStatus.PAUSED
            and "activation_requires" in entry.metadata
        )
        if not conditional:
            missing.append(f"{schedule.source_id}/{schedule.adapter_id}")
    if missing:
        raise ValueError(
            "enabled schedules have no registered adapter: " + ", ".join(missing)
        )


def _validate_portfolio_adapters(
    portfolio: tuple[SourceCatalogEntry, ...],
    adapters: dict[tuple[str, str], CollectionAdapter],
) -> None:
    missing = [
        f"{entry.source_id}/{entry.adapter.adapter_id}"
        for entry in portfolio
        if entry.executable
        and entry.adapter is not None
        and (entry.source_id, entry.adapter.adapter_id) not in adapters
    ]
    if missing:
        raise ValueError(
            "executable source portfolio entries have no registered adapter: "
            + ", ".join(missing)
        )


def _log_worker_outcome(outcome: WorkerOutcome) -> None:
    LOGGER.info(
        "collection worker status=%s job_id=%s observations=%s error=%s",
        outcome.status.value,
        outcome.job_id,
        outcome.observations_written,
        outcome.error_code,
    )


def _log_backfill_outcome(outcome: BackfillWorkerOutcome) -> None:
    LOGGER.info(
        "backfill worker status=%s partition_id=%s observations=%s error=%s",
        outcome.status.value,
        outcome.partition_id,
        outcome.observations_written,
        outcome.error_code,
    )
