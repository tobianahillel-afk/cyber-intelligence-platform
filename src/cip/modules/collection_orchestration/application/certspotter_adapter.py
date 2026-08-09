from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from hashlib import sha256
from uuid import UUID

import httpx
from pydantic import TypeAdapter, ValidationError

from cip.adapters.sources.passive_infrastructure.registry import PassiveInfrastructureTarget
from cip.adapters.sources.passive_infrastructure.schemas import CertSpotterCertificate
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
from cip.shared.kernel.time import require_aware_utc


class CertSpotterAdapter:
    source_id = "certspotter-ct"
    adapter_id = "certspotter-issuances-api"
    adapter_version = "1"
    data_category = DataCategory.TECHNOLOGY_OBSERVATION

    def __init__(
        self,
        entry: SourceRegistryEntry,
        targets: tuple[PassiveInfrastructureTarget, ...],
        *,
        token_provider: Callable[[], str | None],
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("Cert Spotter adapter requires certspotter-ct policy")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._entry = entry
        self._targets = tuple(target for target in targets if target.enabled)
        self._token_provider = token_provider
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
        token = self._token_provider()
        if token is None or not token.strip():
            raise AdapterExecutionError(
                "Cert Spotter production API secret is unavailable",
                error_code="provider_not_connected",
                retryable=False,
            )
        with httpx.Client(
            timeout=self._timeout_seconds,
            follow_redirects=False,
            transport=self._transport,
        ) as client:
            body = get_json(
                client,
                target_url,
                params={
                    "domain": target.domain,
                    "include_subdomains": "true",
                    "expand": "dns_names",
                },
                headers={"Authorization": f"Bearer {token.strip()}"},
            )
        try:
            certificates = TypeAdapter(list[CertSpotterCertificate]).validate_json(body)
        except ValidationError as exc:
            raise AdapterExecutionError(
                "Cert Spotter response schema changed",
                error_code="source_schema_drift",
                retryable=False,
            ) from exc
        context = PassiveObservationContext(
            source_id=self.source_id,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
        )
        observations = tuple(
            raw_passive_observation(
                certificate,
                context=context,
                source_url=target_url,
                source_record_key=certificate.id,
                source_record_type="certspotter-issuance",
                observed_at=_certificate_time(certificate, collected_at),
                published_at=_certificate_time(certificate, collected_at),
            )
            for certificate in certificates
        )
        projections = tuple(
            _map_certificate(certificate, target=target, collected_at=collected_at)
            for certificate in certificates
        )
        return AdapterCollectionBatch(
            observations=observations,
            passive_exposure_projections=projections,
            checkpoint_payload={"target_index": next_index},
            not_modified=not certificates,
        )


def _map_certificate(
    certificate: CertSpotterCertificate,
    *,
    target: PassiveInfrastructureTarget,
    collected_at: datetime,
) -> PassiveObservationSnapshot:
    fingerprint = certificate.tbs_sha256.casefold()
    asset_ref = AssetRef.from_value(AssetType.CERTIFICATE, fingerprint)
    observed_at = _certificate_time(certificate, collected_at)
    revision_key = sha256(certificate.model_dump_json().encode("utf-8")).hexdigest()
    asset = PassiveAsset(
        ref=asset_ref,
        first_seen_at=observed_at,
        last_seen_at=collected_at,
        expires_at=certificate.not_after,
        state=AssetState.OBSERVED,
    )
    link = OrganizationAssetLink(
        id=_stable_uuid(f"certspotter-link:{target.target_id}:{fingerprint}"),
        organization_id=target.organization_id,
        asset=asset_ref,
        status=OrganizationLinkStatus.REVIEW_REQUIRED,
        confidence=0.7,
        risks=(AttributionRisk.UNVERIFIED_OWNERSHIP,),
        valid_from=observed_at,
        valid_to=certificate.not_after,
        reason="certificate issuance can cover shared or third-party managed infrastructure",
        provenance_refs=(f"target:{target.target_id}", f"certificate:{certificate.id}"),
    )
    observation = PassiveObservation(
        id=_stable_uuid(f"certspotter-observation:{certificate.id}:{revision_key}"),
        provider=CertSpotterAdapter.source_id,
        source_record_key=certificate.id,
        source_revision_key=revision_key,
        observation_type=PassiveObservationType.CERTIFICATE_TRANSPARENCY,
        subject_asset=asset_ref,
        observed_at=observed_at,
        valid_from=observed_at,
        valid_to=certificate.not_after,
        confidence=0.8,
        collection_method="certificate_transparency_search_api",
        hostname_value=target.domain,
        service_name=None,
        port=None,
        certificate_fingerprint=fingerprint,
        technology_observation_id=None,
        active_validation=False,
        credential_use=False,
        authenticated_access=False,
        direct_connection_to_asset=False,
        exploitation_attempted=False,
    )
    return PassiveObservationSnapshot(
        provider=CertSpotterAdapter.source_id,
        source_record_key=certificate.id,
        source_revision_key=revision_key,
        asset=asset,
        organization_link=link,
        observation=observation,
    )


def _certificate_time(
    certificate: CertSpotterCertificate,
    fallback: datetime,
) -> datetime:
    if certificate.not_before is None:
        return fallback
    return require_aware_utc(certificate.not_before, field_name="not_before")


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
