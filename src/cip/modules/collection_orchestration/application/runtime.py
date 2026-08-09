from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from os import getpid
from socket import gethostname
from time import sleep

from sqlalchemy.orm import Session, sessionmaker

from cip.adapters.sources.greenhouse.registry import GreenhouseBoard, load_greenhouse_boards
from cip.adapters.sources.lever.registry import LeverSite, load_lever_sites
from cip.adapters.sources.organization_identity.registry import (
    OrganizationIdentityTarget,
    load_organization_identity_targets,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget, load_public_web_targets
from cip.adapters.sources.smartrecruiters.registry import (
    SmartRecruitersCompany,
    load_smartrecruiters_companies,
)
from cip.adapters.sources.vulnerability_catalogs.registry import (
    VulnerabilityQueryTarget,
    load_vulnerability_query_targets,
)
from cip.modules.collection_orchestration.application.adapters import CisaKevAdapter
from cip.modules.collection_orchestration.application.boamp_adapter import BoampAdapter
from cip.modules.collection_orchestration.application.decp_adapter import DecpAdapter
from cip.modules.collection_orchestration.application.greenhouse_adapter import GreenhouseAdapter
from cip.modules.collection_orchestration.application.identity_adapters import (
    register_identity_adapters,
)
from cip.modules.collection_orchestration.application.lever_adapter import LeverAdapter
from cip.modules.collection_orchestration.application.ports import CollectionAdapter
from cip.modules.collection_orchestration.application.public_web_adapter import PublicWebAdapter
from cip.modules.collection_orchestration.application.reference_adapter import (
    ReferencePortfolioAdapter,
)
from cip.modules.collection_orchestration.application.scheduler import schedule_due_jobs
from cip.modules.collection_orchestration.application.smartrecruiters_adapter import (
    SmartRecruitersAdapter,
)
from cip.modules.collection_orchestration.application.ted_adapter import TedSearchAdapter
from cip.modules.collection_orchestration.application.vulnerability_registration import (
    register_vulnerability_adapters,
)
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
    entries = load_source_registry_bundle(
        settings.source_registry_path,
        settings.identity_source_registry_path,
        settings.decp_source_registry_path,
        settings.public_web_source_registry_path,
        settings.vulnerability_source_registry_path,
        settings.incident_source_registry_path,
        settings.threat_telemetry_source_registry_path,
        settings.passive_exposure_source_registry_path,
        settings.advisory_source_registry_path,
        settings.corporate_change_source_registry_path,
        settings.relationship_source_registry_path,
        settings.conditional_integration_source_registry_path,
    )
    portfolio = load_source_portfolio_bundle(
        settings.source_portfolio_path,
        settings.decp_source_portfolio_path,
        settings.public_web_source_portfolio_path,
        settings.vulnerability_source_portfolio_path,
        settings.incident_source_portfolio_path,
        settings.threat_telemetry_source_portfolio_path,
        settings.passive_exposure_source_portfolio_path,
        settings.advisory_source_portfolio_path,
        settings.corporate_change_source_portfolio_path,
        settings.relationship_source_portfolio_path,
        settings.conditional_integration_source_portfolio_path,
    )
    greenhouse_boards = load_greenhouse_boards(settings.greenhouse_board_registry_path)
    lever_sites = load_lever_sites(settings.lever_site_registry_path)
    smartrecruiters_companies = load_smartrecruiters_companies(
        settings.smartrecruiters_company_registry_path
    )
    identity_targets = load_organization_identity_targets(
        settings.organization_identity_target_registry_path
    )
    public_web_targets = load_public_web_targets(settings.public_web_target_registry_path)
    vulnerability_targets = load_vulnerability_query_targets(
        settings.vulnerability_query_target_registry_path
    )
    with session_scope(factory) as session:
        sync_source_registry(session, entries)
        sync_source_portfolio(session, portfolio, now=utc_now())
    adapters = _build_adapters(
        entries,
        greenhouse_boards=greenhouse_boards,
        lever_sites=lever_sites,
        smartrecruiters_companies=smartrecruiters_companies,
        identity_targets=identity_targets,
        public_web_targets=public_web_targets,
        vulnerability_targets=vulnerability_targets,
        timeout_seconds=settings.source_http_timeout_seconds,
    )
    with session_scope(factory) as session:
        reconcile_runtime_adapters(session, adapters.keys(), now=utc_now())
    _validate_portfolio_adapters(portfolio, adapters)
    schedules = load_collection_schedule_bundle(
        settings.collection_schedule_path,
        settings.decp_collection_schedule_path,
        settings.public_web_collection_schedule_path,
        settings.vulnerability_collection_schedule_path,
    )
    _validate_registered_schedules(schedules, adapters, portfolio)
    return CollectionRuntime(
        factory=factory,
        schedules=schedules,
        adapters=adapters,
        retention_policy=load_retention_policy(settings.retention_policy_path),
        portfolio=portfolio,
    )


def _build_adapters(
    entries: tuple[SourceRegistryEntry, ...],
    *,
    greenhouse_boards: tuple[GreenhouseBoard, ...],
    lever_sites: tuple[LeverSite, ...],
    smartrecruiters_companies: tuple[SmartRecruitersCompany, ...],
    identity_targets: tuple[OrganizationIdentityTarget, ...],
    public_web_targets: tuple[PublicWebTarget, ...],
    vulnerability_targets: tuple[VulnerabilityQueryTarget, ...],
    timeout_seconds: float,
) -> dict[tuple[str, str], CollectionAdapter]:
    by_id = {entry.policy.id: entry for entry in entries}
    cisa_entry = by_id.get(CisaKevAdapter.source_id)
    ted_entry = by_id.get(TedSearchAdapter.source_id)
    boamp_entry = by_id.get(BoampAdapter.source_id)
    decp_entry = by_id.get(DecpAdapter.source_id)
    greenhouse_entry = by_id.get(GreenhouseAdapter.source_id)
    lever_entry = by_id.get(LeverAdapter.source_id)
    smartrecruiters_entry = by_id.get(SmartRecruitersAdapter.source_id)
    public_web_entry = by_id.get(PublicWebAdapter.source_id)
    adapters: dict[tuple[str, str], CollectionAdapter] = {}
    if cisa_entry is not None:
        cisa = CisaKevAdapter(cisa_entry, timeout_seconds=timeout_seconds)
        adapters[(cisa.source_id, cisa.adapter_id)] = cisa
    if ted_entry is not None:
        ted = TedSearchAdapter(ted_entry, timeout_seconds=timeout_seconds)
        adapters[(ted.source_id, ted.adapter_id)] = ted
    if boamp_entry is not None:
        boamp = BoampAdapter(boamp_entry, timeout_seconds=timeout_seconds)
        adapters[(boamp.source_id, boamp.adapter_id)] = boamp
    if decp_entry is not None:
        decp = DecpAdapter(decp_entry, timeout_seconds=timeout_seconds)
        adapters[(decp.source_id, decp.adapter_id)] = decp
    if greenhouse_entry is not None:
        greenhouse = GreenhouseAdapter(
            greenhouse_entry,
            greenhouse_boards,
            timeout_seconds=timeout_seconds,
        )
        adapters[(greenhouse.source_id, greenhouse.adapter_id)] = greenhouse
    if lever_entry is not None:
        lever = LeverAdapter(
            lever_entry,
            lever_sites,
            timeout_seconds=timeout_seconds,
        )
        adapters[(lever.source_id, lever.adapter_id)] = lever
    if smartrecruiters_entry is not None:
        smartrecruiters = SmartRecruitersAdapter(
            smartrecruiters_entry,
            smartrecruiters_companies,
            timeout_seconds=timeout_seconds,
        )
        adapters[(smartrecruiters.source_id, smartrecruiters.adapter_id)] = smartrecruiters
    if public_web_entry is not None:
        public_web = PublicWebAdapter(
            public_web_entry,
            public_web_targets,
            timeout_seconds=timeout_seconds,
        )
        adapters[(public_web.source_id, public_web.adapter_id)] = public_web
    register_identity_adapters(
        adapters,
        by_id,
        identity_targets,
        timeout_seconds=timeout_seconds,
    )
    register_vulnerability_adapters(
        adapters,
        by_id,
        vulnerability_targets,
        timeout_seconds=timeout_seconds,
    )
    reference = ReferencePortfolioAdapter()
    adapters[(reference.source_id, reference.adapter_id)] = reference
    return adapters


def run_scheduler_once(runtime: CollectionRuntime, *, now: datetime | None = None) -> int:
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
        raise ValueError(f"enabled schedules have no registered adapter: {', '.join(missing)}")


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
