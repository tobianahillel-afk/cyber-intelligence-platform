from __future__ import annotations

from enum import StrEnum


class PassiveAssetKind(StrEnum):
    DOMAIN = "domain"
    HOSTNAME = "hostname"
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    CERTIFICATE = "certificate"
    ASN = "asn"
    CLOUD_RESOURCE = "cloud_resource"


class PassiveObservationKind(StrEnum):
    PASSIVE_DNS = "passive_dns"
    CERTIFICATE = "certificate"
    ASN = "asn"
    CLOUD = "cloud"
    SERVICE = "service"
    PORT = "port"
    PRODUCT = "product"
    VERSION = "version"
    TECHNOLOGY_MENTION = "technology_mention"


class PassiveObservationState(StrEnum):
    CURRENT = "current"
    HISTORICAL = "historical"
    EXPIRED = "expired"
    CORRECTED = "corrected"
    RETRACTED = "retracted"
    DELETED = "deleted"
    UNKNOWN = "unknown"


class OrganizationLinkStatus(StrEnum):
    UNRESOLVED = "unresolved"
    EXACT = "exact"
    CANDIDATE = "candidate"
    REVIEW_REQUIRED = "review_required"
    REJECTED = "rejected"


class OrganizationLinkMethod(StrEnum):
    EXACT_OFFICIAL_DOMAIN = "exact_official_domain"
    EXACT_OFFICIAL_IDENTIFIER = "exact_official_identifier"
    PROVIDER_ASSERTION = "provider_assertion"
    PASSIVE_CORRELATION = "passive_correlation"
    NAME_ONLY = "name_only"
    NONE = "none"


class AttributionRisk(StrEnum):
    SHARED_HOSTING = "shared_hosting"
    CDN = "cdn"
    RESELLER = "reseller"
    SUBSIDIARY = "subsidiary"
    ABANDONED_DOMAIN = "abandoned_domain"
    REASSIGNED_ADDRESS = "reassigned_address"


class TechnologyEvidenceLevel(StrEnum):
    TECHNOLOGY_MENTION = "technology_mention"
    PASSIVE_OBSERVATION = "passive_observation"
    OBSERVED_VERSION = "observed_version"


EXACT_LINK_METHODS = {
    OrganizationLinkMethod.EXACT_OFFICIAL_DOMAIN,
    OrganizationLinkMethod.EXACT_OFFICIAL_IDENTIFIER,
}
TERMINAL_STATES = {
    PassiveObservationState.EXPIRED,
    PassiveObservationState.RETRACTED,
    PassiveObservationState.DELETED,
}
