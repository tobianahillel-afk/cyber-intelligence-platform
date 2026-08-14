from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from cip.adapters.sources.public_web.browser_fallback_governance import (
    build_browser_fallback_entry,
)
from cip.adapters.sources.public_web.provisioning import provision_public_web_target
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.automatic_public_web_config import (
    AutomaticPublicWebRuntimeConfig,
)
from cip.modules.collection_orchestration.application.ports import CollectionAdapter
from cip.modules.collection_orchestration.application.public_web_adapter import (
    PublicWebAdapter,
)
from cip.modules.collection_orchestration.application.public_web_fallback_adapter import (
    PublicWebFallbackAdapter,
)
from cip.modules.collection_orchestration.domain.models import SourceSchedule
from cip.modules.organizations.domain.entities import Organization
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.shared.kernel.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class AutomaticPublicWebRuntimeBundle:
    adapters: dict[tuple[str, str], CollectionAdapter]
    schedules: tuple[SourceSchedule, ...]
    targets: tuple[PublicWebTarget, ...]


def build_automatic_public_web_runtime(
    session: Session,
    config: AutomaticPublicWebRuntimeConfig,
    *,
    now: datetime,
    timeout_seconds: float,
) -> AutomaticPublicWebRuntimeBundle:
    current = require_aware_utc(now, field_name="now")
    policy = config.policy()
    if policy is None:
        return AutomaticPublicWebRuntimeBundle({}, (), ())
    browser_policy = config.browser_policy()
    adapters: dict[tuple[str, str], CollectionAdapter] = {}
    schedules: list[SourceSchedule] = []
    targets: list[PublicWebTarget] = []
    for organization_id in sorted(set(config.organization_ids), key=str):
        organization = _load_organization(session, organization_id, current)
        provisioned = provision_public_web_target(
            organization,
            policy,
            first_crawl_at=current,
        )
        if browser_policy is None:
            adapter: CollectionAdapter = PublicWebAdapter(
                provisioned.source_entry,
                provisioned.target,
                timeout_seconds=timeout_seconds,
            )
        else:
            browser_entry = build_browser_fallback_entry(
                provisioned.source_entry,
                provisioned.target,
                browser_policy,
            )
            adapter = PublicWebFallbackAdapter(
                provisioned.source_entry,
                browser_entry,
                provisioned.target,
                fallback_policy=browser_policy.fallback_policy(),
                timeout_seconds=timeout_seconds,
            )
        identity = (adapter.source_id, adapter.adapter_id)
        if identity in adapters:
            raise ValueError(f"duplicate automatic public web adapter: {identity}")
        adapters[identity] = adapter
        schedules.append(
            SourceSchedule(
                source_id=adapter.source_id,
                adapter_id=adapter.adapter_id,
                interval_seconds=provisioned.refresh_interval_seconds,
            )
        )
        targets.append(provisioned.target)
    return AutomaticPublicWebRuntimeBundle(
        adapters=adapters,
        schedules=tuple(schedules),
        targets=tuple(targets),
    )


def _load_organization(
    session: Session,
    organization_id: UUID,
    now: datetime,
) -> Organization:
    record = session.get(OrganizationRecord, organization_id)
    if record is None:
        raise ValueError(
            f"approved automatic public web organization not found: {organization_id}"
        )
    if record.website_url is None:
        raise ValueError(
            f"approved automatic public web organization has no website: {organization_id}"
        )
    return Organization(
        id=record.id,
        canonical_name=record.canonical_name,
        legal_name=record.legal_name,
        country_code=record.country_code,
        website_url=record.website_url,
        registration_ids=tuple(record.registration_ids),
        created_at=now,
        updated_at=now,
    )
