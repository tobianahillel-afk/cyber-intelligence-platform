from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from ipaddress import ip_address, ip_network
from urllib.parse import quote, urljoin, urlsplit
from uuid import UUID

import httpx
from pydantic import ValidationError

from cip.adapters.sources.passive_infrastructure.rdap_registry import (
    RdapTarget,
    RdapTargetKind,
)
from cip.adapters.sources.passive_infrastructure.rdap_schemas import (
    IanaRdapBootstrap,
    PublicRdapObject,
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
from cip.modules.passive_exposure.domain.normalization import normalize_domain
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_BOOTSTRAP_FILES = {
    RdapTargetKind.DOMAIN: "dns.json",
    RdapTargetKind.IPV4: "ipv4.json",
    RdapTargetKind.IPV6: "ipv6.json",
    RdapTargetKind.ASN: "asn.json",
}
_ASSET_KINDS = {
    RdapTargetKind.DOMAIN: PassiveAssetKind.DOMAIN,
    RdapTargetKind.IPV4: PassiveAssetKind.IPV4,
    RdapTargetKind.IPV6: PassiveAssetKind.IPV6,
    RdapTargetKind.ASN: PassiveAssetKind.ASN,
}
_EXPECTED_OBJECT_CLASSES = {
    RdapTargetKind.DOMAIN: "domain",
    RdapTargetKind.IPV4: "ip network",
    RdapTargetKind.IPV6: "ip network",
    RdapTargetKind.ASN: "autnum",
}
_ASN_SPACE = 4_294_967_296


class IanaRdapAdapter:
    source_id = "iana-rdap-public"
    adapter_id = "iana-bootstrap-rdap"
    adapter_version = "1"
    data_category = DataCategory.TECHNOLOGY_OBSERVATION

    def __init__(
        self,
        entry: SourceRegistryEntry,
        targets: tuple[RdapTarget, ...],
        *,
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("RDAP adapter requires iana-rdap-public policy")
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
        bootstrap_url = urljoin(
            self._entry.policy.base_url,
            _BOOTSTRAP_FILES[target.kind],
        )
        authorize_passive_request(
            self._entry,
            target_url=bootstrap_url,
            collected_at=collected_at,
        )
        with httpx.Client(
            timeout=self._timeout_seconds,
            follow_redirects=False,
            transport=self._transport,
        ) as client:
            bootstrap = _fetch_bootstrap(client, bootstrap_url)
            base_url = _authoritative_base_url(bootstrap, target)
            rdap_url = _rdap_url(base_url, target)
            record = _fetch_public_object(client, rdap_url)
        _validate_record_identity(record, target)
        context = PassiveObservationContext(
            source_id=self.source_id,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
        )
        snapshot = _map_record(record, target=target, source_url=rdap_url, now=collected_at)
        observation = raw_passive_observation(
            record,
            context=context,
            source_url=rdap_url,
            source_record_key=snapshot.source_record_key,
            source_record_type="public-rdap-registration",
            observed_at=collected_at,
        )
        return AdapterCollectionBatch(
            observations=(observation,),
            passive_exposure_projections=(snapshot,),
            checkpoint_payload={"target_index": next_index},
            not_modified=False,
        )


def _fetch_bootstrap(client: httpx.Client, url: str) -> IanaRdapBootstrap:
    body = get_json(client, url, params={})
    try:
        return IanaRdapBootstrap.model_validate_json(body)
    except ValidationError as exc:
        raise AdapterExecutionError(
            "IANA RDAP bootstrap schema changed",
            error_code="source_schema_drift",
            retryable=False,
        ) from exc


def _fetch_public_object(client: httpx.Client, url: str) -> PublicRdapObject:
    body = get_json(
        client,
        url,
        params={},
        headers={"accept": "application/rdap+json, application/json"},
    )
    try:
        return PublicRdapObject.model_validate_json(body)
    except ValidationError as exc:
        raise AdapterExecutionError(
            "authoritative RDAP response schema changed",
            error_code="source_schema_drift",
            retryable=False,
        ) from exc


def _authoritative_base_url(bootstrap: IanaRdapBootstrap, target: RdapTarget) -> str:
    candidates = _matching_services(bootstrap, target)
    if not candidates:
        raise _bootstrap_error("no authoritative RDAP service for target")
    for _specificity, urls in sorted(candidates, reverse=True):
        for url in urls:
            parsed = urlsplit(url)
            if parsed.scheme == "https" and parsed.hostname and not parsed.username:
                return url if url.endswith("/") else f"{url}/"
    raise _bootstrap_error("authoritative RDAP service has no HTTPS endpoint")


def _matching_services(
    bootstrap: IanaRdapBootstrap,
    target: RdapTarget,
) -> list[tuple[int, tuple[str, ...]]]:
    matches: list[tuple[int, tuple[str, ...]]] = []
    for keys, urls in bootstrap.services:
        specificity = _service_specificity(keys, target)
        if specificity >= 0:
            matches.append((specificity, tuple(urls)))
    return matches


def _service_specificity(keys: list[str], target: RdapTarget) -> int:
    if target.kind is RdapTargetKind.DOMAIN:
        return _domain_specificity(keys, target.value)
    if target.kind in {RdapTargetKind.IPV4, RdapTargetKind.IPV6}:
        return _ip_specificity(keys, target.value)
    return _asn_specificity(keys, target.value)


def _domain_specificity(keys: list[str], domain: str) -> int:
    best = -1
    for key in keys:
        suffix = key.casefold().strip(".")
        if suffix == "":
            best = max(best, 0)
        elif domain == suffix or domain.endswith(f".{suffix}"):
            best = max(best, suffix.count(".") + 1)
    return best


def _ip_specificity(keys: list[str], value: str) -> int:
    address = ip_address(value)
    best = -1
    for key in keys:
        try:
            network = ip_network(key, strict=False)
        except ValueError:
            continue
        if network.version == address.version and address in network:
            best = max(best, network.prefixlen)
    return best


def _asn_specificity(keys: list[str], value: str) -> int:
    number = int(value.removeprefix("AS"))
    best = -1
    for key in keys:
        start_text, separator, end_text = key.partition("-")
        if not separator or not start_text.isdigit() or not end_text.isdigit():
            continue
        start, end = int(start_text), int(end_text)
        if start <= number <= end:
            best = max(best, _ASN_SPACE - (end - start))
    return best


def _rdap_url(base_url: str, target: RdapTarget) -> str:
    resource = target.value
    if target.kind is RdapTargetKind.DOMAIN:
        path = f"domain/{quote(resource, safe='.-')}"
    elif target.kind in {RdapTargetKind.IPV4, RdapTargetKind.IPV6}:
        path = f"ip/{quote(resource, safe=':.')}"
    else:
        path = f"autnum/{resource.removeprefix('AS')}"
    url = urljoin(base_url, path)
    parsed = urlsplit(url)
    base = urlsplit(base_url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != base.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise _bootstrap_error("derived RDAP URL escaped authoritative HTTPS endpoint")
    return url


def _validate_record_identity(record: PublicRdapObject, target: RdapTarget) -> None:
    if record.objectClassName.casefold() != _EXPECTED_OBJECT_CLASSES[target.kind]:
        raise _identity_error()
    if target.kind is RdapTargetKind.DOMAIN:
        if record.ldhName is None or normalize_domain(record.ldhName) != target.value:
            raise _identity_error()
    elif target.kind in {RdapTargetKind.IPV4, RdapTargetKind.IPV6}:
        _validate_ip_record(record, target.value)
    else:
        _validate_asn_record(record, target.value)


def _validate_ip_record(record: PublicRdapObject, value: str) -> None:
    if record.startAddress is None or record.endAddress is None:
        raise _identity_error()
    address = ip_address(value)
    start, end = ip_address(record.startAddress), ip_address(record.endAddress)
    if start.version != address.version or end.version != address.version:
        raise _identity_error()
    if not int(start) <= int(address) <= int(end):
        raise _identity_error()


def _validate_asn_record(record: PublicRdapObject, value: str) -> None:
    if record.startAutnum is None or record.endAutnum is None:
        raise _identity_error()
    number = int(value.removeprefix("AS"))
    if not record.startAutnum <= number <= record.endAutnum:
        raise _identity_error()


def _map_record(
    record: PublicRdapObject,
    *,
    target: RdapTarget,
    source_url: str,
    now: datetime,
) -> PassiveObservationSnapshot:
    risks = _attribution_risks(target.kind)
    asset = PassiveAsset(kind=_ASSET_KINDS[target.kind], value=target.value)
    key_part = record.handle or record.ldhName or record.name or target.value
    return PassiveObservationSnapshot(
        source_id=IanaRdapAdapter.source_id,
        source_record_key=f"{target.kind.value}:{target.value}:{key_part}"[:500],
        source_url=source_url,
        asset=asset,
        observation_kind=PassiveObservationKind.REGISTRATION,
        state=PassiveObservationState.CURRENT,
        observed_at=now,
        published_at=now,
        modified_at=now,
        confidence=0.75,
        independence_key=f"rdap:{target.kind.value}:{target.value}",
        organization_link=OrganizationLink(
            status=OrganizationLinkStatus.REVIEW_REQUIRED,
            method=OrganizationLinkMethod.PASSIVE_CORRELATION,
            confidence=0.65,
            organization_id=target.organization_id,
            reasons=(
                "RDAP registration or allocation metadata does not prove current "
                "operational ownership",
            ),
            attribution_risks=risks,
        ),
    )


def _attribution_risks(kind: RdapTargetKind) -> tuple[AttributionRisk, ...]:
    if kind is RdapTargetKind.DOMAIN:
        return (AttributionRisk.ABANDONED_DOMAIN,)
    if kind in {RdapTargetKind.IPV4, RdapTargetKind.IPV6}:
        return (AttributionRisk.REASSIGNED_ADDRESS,)
    return (AttributionRisk.RESELLER,)


def _next_target(
    targets: tuple[RdapTarget, ...],
    payload: Mapping[str, object] | None,
) -> tuple[RdapTarget | None, int]:
    if not targets:
        return None, 0
    value = 0 if payload is None else payload.get("target_index", 0)
    if not isinstance(value, int) or value < 0:
        raise AdapterExecutionError(
            "invalid RDAP target checkpoint",
            error_code="invalid_checkpoint",
            retryable=False,
        )
    index = value % len(targets)
    return targets[index], 0 if index + 1 >= len(targets) else index + 1


def _bootstrap_error(message: str) -> AdapterExecutionError:
    return AdapterExecutionError(
        message,
        error_code="rdap_bootstrap_error",
        retryable=False,
    )


def _identity_error() -> AdapterExecutionError:
    return AdapterExecutionError(
        "RDAP response identity does not cover requested target",
        error_code="source_identity_mismatch",
        retryable=False,
    )


def _empty_batch() -> AdapterCollectionBatch:
    return AdapterCollectionBatch(
        observations=(),
        passive_exposure_projections=(),
        checkpoint_payload={"target_index": 0},
        not_modified=True,
    )
