from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
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
from cip.shared.kernel.time import require_aware_utc

_MAX_PAGE_SIZE = 100
_MAX_CURSOR_TARGETS = 500


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
        cursors = _cursor_map(checkpoint_payload, self._targets)
        page = self._request_page(
            target_url,
            target,
            token=token.strip(),
            after=cursors.get(target.target_id),
        )
        if page:
            cursors[target.target_id] = page[-1].id
        scoped = tuple(
            certificate
            for certificate in page
            if _matches_target(certificate, target.domain)
        )
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
                observed_at=_observed_at(certificate, collected_at),
                published_at=collected_at,
            )
            for certificate in scoped
        )
        projections = tuple(
            _map_certificate(
                certificate,
                target=target,
                source_url=target_url,
                collected_at=collected_at,
            )
            for certificate in scoped
        )
        return AdapterCollectionBatch(
            observations=observations,
            passive_exposure_projections=projections,
            checkpoint_payload={
                "target_index": next_index,
                "after_by_target": cursors,
            },
            not_modified=not projections,
        )

    def _request_page(
        self,
        target_url: str,
        target: PassiveInfrastructureTarget,
        *,
        token: str,
        after: str | None,
    ) -> tuple[CertSpotterCertificate, ...]:
        params = {
            "domain": target.domain,
            "include_subdomains": "true",
            "expand": "dns_names",
        }
        if after is not None:
            params["after"] = after
        with httpx.Client(
            timeout=self._timeout_seconds,
            follow_redirects=False,
            transport=self._transport,
        ) as client:
            body = get_json(
                client,
                target_url,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
        try:
            page = tuple(TypeAdapter(list[CertSpotterCertificate]).validate_json(body))
        except ValidationError as exc:
            raise AdapterExecutionError(
                "Cert Spotter response schema changed",
                error_code="source_schema_drift",
                retryable=False,
            ) from exc
        if len(page) > _MAX_PAGE_SIZE:
            raise AdapterExecutionError(
                "Cert Spotter page exceeds configured bound",
                error_code="source_page_too_large",
                retryable=False,
            )
        return page


def _map_certificate(
    certificate: CertSpotterCertificate,
    *,
    target: PassiveInfrastructureTarget,
    source_url: str,
    collected_at: datetime,
) -> PassiveObservationSnapshot:
    observed_at = _observed_at(certificate, collected_at)
    expires_at = _optional_utc(certificate.not_after, "not_after")
    active = expires_at is None or expires_at >= collected_at
    state = (
        PassiveObservationState.CURRENT
        if active
        else PassiveObservationState.EXPIRED
    )
    return PassiveObservationSnapshot(
        source_id=CertSpotterAdapter.source_id,
        source_record_key=certificate.id,
        source_url=source_url,
        asset=PassiveAsset(
            kind=PassiveAssetKind.CERTIFICATE,
            value=certificate.tbs_sha256,
        ),
        observation_kind=PassiveObservationKind.CERTIFICATE,
        state=state,
        observed_at=observed_at,
        published_at=collected_at,
        modified_at=collected_at,
        expires_at=expires_at,
        confidence=0.8,
        independence_key=f"certspotter-ct:{target.domain}",
        organization_link=OrganizationLink(
            status=OrganizationLinkStatus.REVIEW_REQUIRED,
            method=OrganizationLinkMethod.PASSIVE_CORRELATION,
            confidence=0.7,
            organization_id=target.organization_id,
            reasons=(
                "certificate issuance can cover shared or third-party managed infrastructure",
            ),
            attribution_risks=(AttributionRisk.SHARED_HOSTING,),
        ),
        active=active,
    )


def _matches_target(certificate: CertSpotterCertificate, target_domain: str) -> bool:
    target = target_domain.rstrip(".").casefold()
    suffix = f".{target}"
    for raw_name in certificate.dns_names:
        name = raw_name.strip().rstrip(".").casefold()
        if name.startswith("*."):
            name = name[2:]
        if name == target or name.endswith(suffix):
            return True
    return False


def _cursor_map(
    payload: Mapping[str, object] | None,
    targets: tuple[PassiveInfrastructureTarget, ...],
) -> dict[str, str]:
    if payload is None:
        return {}
    raw = payload.get("after_by_target", {})
    if not isinstance(raw, dict) or len(raw) > _MAX_CURSOR_TARGETS:
        raise _invalid_checkpoint()
    known_ids = {target.target_id for target in targets}
    cursors: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, str) or not value.strip():
            raise _invalid_checkpoint()
        if key in known_ids:
            cursors[key] = value.strip()
    return cursors


def _observed_at(
    certificate: CertSpotterCertificate,
    collected_at: datetime,
) -> datetime:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    if certificate.not_before is None:
        return collected
    not_before = require_aware_utc(certificate.not_before, field_name="not_before")
    return min(not_before, collected)


def _optional_utc(value: datetime | None, field_name: str) -> datetime | None:
    if value is None:
        return None
    return require_aware_utc(value, field_name=field_name)


def _next_target(
    targets: tuple[PassiveInfrastructureTarget, ...],
    payload: Mapping[str, object] | None,
) -> tuple[PassiveInfrastructureTarget | None, int]:
    if not targets:
        return None, 0
    value = 0 if payload is None else payload.get("target_index", 0)
    if not isinstance(value, int) or value < 0:
        raise _invalid_checkpoint()
    index = value % len(targets)
    return targets[index], 0 if index + 1 >= len(targets) else index + 1


def _invalid_checkpoint() -> AdapterExecutionError:
    return AdapterExecutionError(
        "invalid passive target checkpoint",
        error_code="invalid_checkpoint",
        retryable=False,
    )


def _empty_batch() -> AdapterCollectionBatch:
    return AdapterCollectionBatch(
        observations=(),
        passive_exposure_projections=(),
        checkpoint_payload={"target_index": 0, "after_by_target": {}},
        not_modified=True,
    )
