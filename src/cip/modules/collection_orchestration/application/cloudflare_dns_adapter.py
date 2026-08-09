from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from uuid import UUID

import httpx
from pydantic import ValidationError

from cip.adapters.sources.passive_infrastructure.registry import PassiveInfrastructureTarget
from cip.adapters.sources.passive_infrastructure.schemas import (
    CloudflareDnsAnswer,
    CloudflareDnsResponse,
)
from cip.modules.collection_orchestration.application.passive_adapter_support import (
    PassiveObservationContext,
    authorize_passive_request,
    get_json,
    raw_passive_observation,
)
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.passive_exposure.domain.models import (
    AttributionRisk,
    OrganizationLink,
    OrganizationLinkMethod,
    OrganizationLinkStatus,
    PassiveAsset,
    PassiveAssetKind,
    PassiveObservationKind,
    PassiveObservationSnapshot,
    PassiveObservationState,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_DNS_TYPES = ("A", "AAAA")
_DNS_ASSET_KINDS = {
    1: PassiveAssetKind.IPV4,
    28: PassiveAssetKind.IPV6,
}


class CloudflareDnsAdapter:
    source_id = "cloudflare-doh"
    adapter_id = "cloudflare-dns-json"
    adapter_version = "1"
    data_category = DataCategory.TECHNOLOGY_OBSERVATION

    def __init__(
        self,
        entry: SourceRegistryEntry,
        targets: tuple[PassiveInfrastructureTarget, ...],
        *,
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("Cloudflare DNS adapter requires cloudflare-doh policy")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._entry = entry
        self._targets = tuple(target for target in targets if target.enabled)
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch:
        target, next_index = _next_target(self._targets, checkpoint_payload)
        if target is None:
            return _empty_batch()
        target_url = self._entry.policy.base_url
        authorize_passive_request(
            self._entry,
            target_url=target_url,
            collected_at=collected_at,
        )
        context = PassiveObservationContext(
            source_id=self.source_id,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
        )
        observations = []
        projections = []
        with httpx.Client(
            timeout=self._timeout_seconds,
            follow_redirects=False,
            transport=self._transport,
        ) as client:
            for record_type in _DNS_TYPES:
                response = _query(client, target_url, target.domain, record_type)
                for answer in response.answers:
                    snapshot = _map_answer(
                        answer,
                        target=target,
                        source_url=target_url,
                        observed_at=collected_at,
                    )
                    if snapshot is None:
                        continue
                    observations.append(
                        raw_passive_observation(
                            answer,
                            context=context,
                            source_url=target_url,
                            source_record_key=snapshot.source_record_key,
                            source_record_type="cloudflare-dns-answer",
                            observed_at=collected_at,
                        )
                    )
                    projections.append(snapshot)
        return AdapterCollectionBatch(
            observations=tuple(observations),
            passive_exposure_projections=tuple(projections),
            checkpoint_payload={"target_index": next_index},
            not_modified=not projections,
        )


def _query(
    client: httpx.Client,
    target_url: str,
    domain: str,
    record_type: str,
) -> CloudflareDnsResponse:
    body = get_json(
        client,
        target_url,
        params={"name": domain, "type": record_type},
        headers={"accept": "application/dns-json"},
    )
    try:
        result = CloudflareDnsResponse.model_validate_json(body)
    except ValidationError as exc:
        raise AdapterExecutionError(
            "Cloudflare DNS response schema changed",
            error_code="source_schema_drift",
            retryable=False,
        ) from exc
    if result.status != 0:
        raise AdapterExecutionError(
            f"Cloudflare DNS returned DNS status {result.status}",
            error_code="provider_dns_error",
            retryable=False,
        )
    return result


def _map_answer(
    answer: CloudflareDnsAnswer,
    *,
    target: PassiveInfrastructureTarget,
    source_url: str,
    observed_at: datetime,
) -> PassiveObservationSnapshot | None:
    asset_kind = _DNS_ASSET_KINDS.get(answer.record_type)
    if asset_kind is None:
        return None
    try:
        asset = PassiveAsset(kind=asset_kind, value=answer.data)
    except ValueError:
        return None
    record_key = f"{target.domain}:{answer.record_type}:{asset.value}"
    return PassiveObservationSnapshot(
        source_id=CloudflareDnsAdapter.source_id,
        source_record_key=record_key,
        source_url=source_url,
        asset=asset,
        observation_kind=PassiveObservationKind.PASSIVE_DNS,
        state=PassiveObservationState.CURRENT,
        observed_at=observed_at,
        published_at=observed_at,
        modified_at=observed_at,
        expires_at=observed_at + timedelta(seconds=answer.ttl),
        confidence=0.75,
        independence_key=f"cloudflare-doh:{target.domain}",
        organization_link=OrganizationLink(
            status=OrganizationLinkStatus.REVIEW_REQUIRED,
            method=OrganizationLinkMethod.PASSIVE_CORRELATION,
            confidence=0.65,
            organization_id=target.organization_id,
            reasons=("DNS resolution can point to shared or CDN infrastructure",),
            attribution_risks=(AttributionRisk.SHARED_HOSTING,),
        ),
    )


def _next_target(
    targets: tuple[PassiveInfrastructureTarget, ...],
    payload: Mapping[str, object] | None,
) -> tuple[PassiveInfrastructureTarget | None, int]:
    if not targets:
        return None, 0
    value = 0 if payload is None else payload.get("target_index", 0)
    if not isinstance(value, int) or value < 0:
        raise AdapterExecutionError(
            "invalid passive target checkpoint",
            error_code="invalid_checkpoint",
            retryable=False,
        )
    index = value % len(targets)
    return targets[index], 0 if index + 1 >= len(targets) else index + 1


def _empty_batch() -> AdapterCollectionBatch:
    return AdapterCollectionBatch(
        observations=(),
        passive_exposure_projections=(),
        checkpoint_payload={"target_index": 0},
        not_modified=True,
    )
