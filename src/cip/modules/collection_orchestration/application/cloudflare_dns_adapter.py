from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from hashlib import sha256
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
from cip.modules.passive_exposure.domain.asset_models import AssetRef, PassiveAsset
from cip.modules.passive_exposure.domain.enums import (
    AssetState,
    AssetType,
    AttributionRisk,
    OrganizationLinkStatus,
    PassiveObservationType,
)
from cip.modules.passive_exposure.domain.models import PassiveObservationSnapshot
from cip.modules.passive_exposure.domain.observation_models import (
    OrganizationAssetLink,
    PassiveObservation,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_DNS_TYPES = ("A", "AAAA")


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
                for answer in response.Answer:
                    snapshot = _map_answer(answer, target=target, observed_at=collected_at)
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
    if result.Status != 0:
        raise AdapterExecutionError(
            f"Cloudflare DNS returned DNS status {result.Status}",
            error_code="provider_dns_error",
            retryable=False,
        )
    return result


def _map_answer(
    answer: CloudflareDnsAnswer,
    *,
    target: PassiveInfrastructureTarget,
    observed_at: datetime,
) -> PassiveObservationSnapshot | None:
    if answer.type not in {1, 28}:
        return None
    try:
        asset_ref = AssetRef.from_value(AssetType.IP, answer.data)
    except ValueError:
        return None
    record_key = f"{target.domain}:{answer.type}:{asset_ref.value}"
    revision_key = sha256(answer.model_dump_json().encode("utf-8")).hexdigest()
    asset = PassiveAsset(
        ref=asset_ref,
        first_seen_at=observed_at,
        last_seen_at=observed_at,
        state=AssetState.OBSERVED,
    )
    link = OrganizationAssetLink(
        id=_stable_uuid(f"cloudflare-link:{target.target_id}:{asset_ref.value}"),
        organization_id=target.organization_id,
        asset=asset_ref,
        status=OrganizationLinkStatus.REVIEW_REQUIRED,
        confidence=0.65,
        risks=(AttributionRisk.SHARED_HOSTING,),
        valid_from=observed_at,
        valid_to=None,
        reason="DNS resolution can point to shared or CDN infrastructure",
        provenance_refs=(f"target:{target.target_id}", f"dns:{target.domain}"),
    )
    observation = PassiveObservation(
        id=_stable_uuid(f"cloudflare-observation:{record_key}:{revision_key}"),
        provider=CloudflareDnsAdapter.source_id,
        source_record_key=record_key,
        source_revision_key=revision_key,
        observation_type=PassiveObservationType.PASSIVE_DNS,
        subject_asset=asset_ref,
        observed_at=observed_at,
        valid_from=observed_at,
        valid_to=None,
        confidence=0.75,
        collection_method="official_dns_over_https",
        hostname_value=target.domain,
        service_name=None,
        port=None,
        certificate_fingerprint=None,
        technology_observation_id=None,
        active_validation=False,
        credential_use=False,
        authenticated_access=False,
        direct_connection_to_asset=False,
        exploitation_attempted=False,
    )
    return PassiveObservationSnapshot(
        provider=CloudflareDnsAdapter.source_id,
        source_record_key=record_key,
        source_revision_key=revision_key,
        asset=asset,
        organization_link=link,
        observation=observation,
    )


def _stable_uuid(value: str) -> UUID:
    digest = sha256(value.encode("utf-8")).hexdigest()
    return UUID(digest[:32])


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
