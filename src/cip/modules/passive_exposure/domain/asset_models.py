from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from cip.modules.passive_exposure.domain.enums import (
    EXACT_LINK_METHODS,
    AttributionRisk,
    OrganizationLinkMethod,
    OrganizationLinkStatus,
    PassiveAssetKind,
    TechnologyEvidenceLevel,
)
from cip.modules.passive_exposure.domain.normalization import (
    normalize_asn,
    normalize_certificate_fingerprint,
    normalize_cloud_resource,
    normalize_domain,
    normalize_hostname,
    normalize_ip,
    normalize_optional_text,
)


@dataclass(frozen=True, slots=True)
class PassiveAsset:
    kind: PassiveAssetKind
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", normalize_asset(self.kind, self.value))

    @property
    def key(self) -> str:
        return f"{self.kind.value}:{self.value}"


@dataclass(frozen=True, slots=True)
class OrganizationLink:
    status: OrganizationLinkStatus
    method: OrganizationLinkMethod
    confidence: float
    organization_id: UUID | None = None
    reasons: tuple[str, ...] = ()
    attribution_risks: tuple[AttributionRisk, ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("organization-link confidence must be between 0 and 1")
        reasons = _unique_text(self.reasons, maximum=500)
        risks = tuple(sorted(set(self.attribution_risks), key=lambda risk: risk.value))
        object.__setattr__(self, "reasons", reasons)
        object.__setattr__(self, "attribution_risks", risks)
        if self.status in {
            OrganizationLinkStatus.UNRESOLVED,
            OrganizationLinkStatus.REJECTED,
        } and self.organization_id is not None:
            raise ValueError("unresolved or rejected links cannot retain organization_id")
        if self.status in {
            OrganizationLinkStatus.EXACT,
            OrganizationLinkStatus.CANDIDATE,
            OrganizationLinkStatus.REVIEW_REQUIRED,
        } and self.organization_id is None:
            raise ValueError("resolved or reviewable links require organization_id")
        if self.status is OrganizationLinkStatus.EXACT:
            if self.method not in EXACT_LINK_METHODS:
                raise ValueError("exact links require exact official evidence")
            if risks:
                raise ValueError("attribution risks prevent an exact organization link")
        if self.method is OrganizationLinkMethod.NAME_ONLY and self.status not in {
            OrganizationLinkStatus.REVIEW_REQUIRED,
            OrganizationLinkStatus.REJECTED,
        }:
            raise ValueError("name-only links must remain reviewable or rejected")
        if self.status is not OrganizationLinkStatus.UNRESOLVED and not reasons:
            raise ValueError("linked records require at least one explicit reason")
        if self.status is OrganizationLinkStatus.UNRESOLVED:
            if self.method is not OrganizationLinkMethod.NONE:
                raise ValueError("unresolved links must use method none")
            if reasons:
                raise ValueError("unresolved links cannot retain link reasons")

    @property
    def requires_review(self) -> bool:
        return self.status in {
            OrganizationLinkStatus.CANDIDATE,
            OrganizationLinkStatus.REVIEW_REQUIRED,
        }


@dataclass(frozen=True, slots=True)
class TechnologyObservation:
    evidence_level: TechnologyEvidenceLevel
    product_name: str | None = None
    product_version: str | None = None
    component_name: str | None = None

    def __post_init__(self) -> None:
        product_name = normalize_optional_text(self.product_name, maximum=300)
        product_version = normalize_optional_text(self.product_version, maximum=200)
        component_name = normalize_optional_text(self.component_name, maximum=300)
        object.__setattr__(self, "product_name", product_name)
        object.__setattr__(self, "product_version", product_version)
        object.__setattr__(self, "component_name", component_name)
        if self.evidence_level is TechnologyEvidenceLevel.TECHNOLOGY_MENTION:
            if product_name is None:
                raise ValueError("technology mentions require a product name")
        if self.evidence_level is TechnologyEvidenceLevel.PASSIVE_OBSERVATION:
            if product_name is None:
                raise ValueError("passive technology observations require a product name")
        if self.evidence_level is TechnologyEvidenceLevel.OBSERVED_VERSION:
            if product_name is None or product_version is None:
                raise ValueError("observed versions require product and version")


def normalize_asset(kind: PassiveAssetKind, value: str) -> str:
    if kind is PassiveAssetKind.DOMAIN:
        return normalize_domain(value)
    if kind is PassiveAssetKind.HOSTNAME:
        return normalize_hostname(value)
    if kind is PassiveAssetKind.IPV4:
        return normalize_ip(value, version=4)
    if kind is PassiveAssetKind.IPV6:
        return normalize_ip(value, version=6)
    if kind is PassiveAssetKind.CERTIFICATE:
        return normalize_certificate_fingerprint(value)
    if kind is PassiveAssetKind.ASN:
        return normalize_asn(value)
    if kind is PassiveAssetKind.CLOUD_RESOURCE:
        return normalize_cloud_resource(value)
    raise ValueError(f"unsupported passive asset kind: {kind}")


def _unique_text(values: tuple[str, ...], *, maximum: int) -> tuple[str, ...]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        if len(normalized) > maximum:
            raise ValueError(f"text value cannot exceed {maximum} characters")
        key = normalized.casefold()
        if key not in seen:
            seen.add(key)
            unique.append(normalized)
    return tuple(unique)
