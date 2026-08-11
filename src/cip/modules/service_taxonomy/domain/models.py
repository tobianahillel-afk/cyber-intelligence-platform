from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

SERVICE_TAXONOMY_VERSION = "2026.08"


class CyberServiceFamily(StrEnum):
    STRATEGY_VCISO = "security_strategy_vciso"
    SECURITY_STRATEGY_VCISO = "security_strategy_vciso"
    AUDIT_RISK_ASSESSMENT = "risk_assessment_audit"
    RISK_ASSESSMENT_AUDIT = "risk_assessment_audit"
    GRC_COMPLIANCE = "grc_compliance"
    PENETRATION_TESTING = "penetration_testing"
    RED_PURPLE_TEAMING = "red_team_purple_team"
    RED_TEAM_PURPLE_TEAM = "red_team_purple_team"
    VULNERABILITY_ATTACK_SURFACE = "vulnerability_management_asm"
    VULNERABILITY_MANAGEMENT_ASM = "vulnerability_management_asm"
    SOC_SIEM_MDR_XDR_SOAR = "soc_siem_mdr_detection"
    SOC_SIEM_MDR_DETECTION = "soc_siem_mdr_detection"
    INCIDENT_RESPONSE_DFIR = "incident_response_dfir"
    RESILIENCE_CRISIS_READINESS = "resilience_bcp_drp"
    RESILIENCE_BCP_DRP = "resilience_bcp_drp"
    IAM_IGA_PAM_ZERO_TRUST = "iam_pam_zero_trust"
    IAM_PAM_ZERO_TRUST = "iam_pam_zero_trust"
    CLOUD_CONTAINER_SECURITY = "cloud_security"
    CLOUD_SECURITY = "cloud_security"
    APPSEC_DEVSECOPS = "application_security_devsecops"
    APPLICATION_SECURITY_DEVSECOPS = "application_security_devsecops"
    NETWORK_SASE_SECURITY = "network_security_sase"
    NETWORK_SECURITY_SASE = "network_security_sase"
    DATA_PROTECTION = "data_security_privacy"
    DATA_SECURITY_PRIVACY = "data_security_privacy"
    THIRD_PARTY_SUPPLY_CHAIN = "third_party_supply_chain"
    OT_ICS_IOT_SECURITY = "ot_ics_iot_security"
    AWARENESS_TRAINING = "security_awareness_training"
    SECURITY_AWARENESS_TRAINING = "security_awareness_training"
    PRODUCT_INTEGRATION_MIGRATION = "product_integration_migration"
    CYBER_INSURANCE_READINESS = "cyber_insurance_readiness"


_LEGACY_FAMILY_IDS: dict[str, CyberServiceFamily] = {
    "strategy_vciso": CyberServiceFamily.STRATEGY_VCISO,
    "audit_risk_assessment": CyberServiceFamily.AUDIT_RISK_ASSESSMENT,
    "grc_compliance": CyberServiceFamily.GRC_COMPLIANCE,
    "penetration_testing": CyberServiceFamily.PENETRATION_TESTING,
    "red_purple_teaming": CyberServiceFamily.RED_PURPLE_TEAMING,
    "vulnerability_attack_surface": CyberServiceFamily.VULNERABILITY_ATTACK_SURFACE,
    "soc_siem_mdr_xdr_soar": CyberServiceFamily.SOC_SIEM_MDR_XDR_SOAR,
    "incident_response_dfir": CyberServiceFamily.INCIDENT_RESPONSE_DFIR,
    "resilience_crisis_readiness": CyberServiceFamily.RESILIENCE_CRISIS_READINESS,
    "iam_iga_pam_zero_trust": CyberServiceFamily.IAM_IGA_PAM_ZERO_TRUST,
    "cloud_container_security": CyberServiceFamily.CLOUD_CONTAINER_SECURITY,
    "appsec_devsecops": CyberServiceFamily.APPSEC_DEVSECOPS,
    "network_sase_security": CyberServiceFamily.NETWORK_SASE_SECURITY,
    "data_protection": CyberServiceFamily.DATA_PROTECTION,
    "third_party_supply_chain": CyberServiceFamily.THIRD_PARTY_SUPPLY_CHAIN,
    "ot_ics_iot_security": CyberServiceFamily.OT_ICS_IOT_SECURITY,
    "awareness_training": CyberServiceFamily.AWARENESS_TRAINING,
    "product_integration_migration": CyberServiceFamily.PRODUCT_INTEGRATION_MIGRATION,
    "cyber_insurance_readiness": CyberServiceFamily.CYBER_INSURANCE_READINESS,
}


def parse_service_family(value: str | CyberServiceFamily) -> CyberServiceFamily:
    if isinstance(value, CyberServiceFamily):
        return value
    normalized = value.strip().casefold()
    if not normalized:
        raise ValueError("service family identifier is required")
    try:
        return CyberServiceFamily(normalized)
    except ValueError:
        legacy = _LEGACY_FAMILY_IDS.get(normalized)
        if legacy is None:
            raise ValueError(f"unknown service family identifier: {value}") from None
        return legacy


def legacy_service_family_ids() -> dict[str, str]:
    return {legacy: family.value for legacy, family in _LEGACY_FAMILY_IDS.items()}


def service_family_identifiers(
    value: str | CyberServiceFamily,
) -> tuple[str, ...]:
    family = parse_service_family(value)
    aliases = tuple(
        legacy for legacy, mapped in _LEGACY_FAMILY_IDS.items() if mapped is family
    )
    return tuple(dict.fromkeys((family.value, *aliases)))


@dataclass(frozen=True, slots=True)
class ServiceFamilyMatch:
    family: CyberServiceFamily
    matched_terms: tuple[str, ...]
    confidence: float

    def __post_init__(self) -> None:
        terms = tuple(
            dict.fromkeys(
                term.strip().casefold() for term in self.matched_terms if term.strip()
            )
        )
        if not terms:
            raise ValueError("service family match requires at least one term")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(self, "matched_terms", terms)
