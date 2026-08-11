from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Self

CANONICAL_TAXONOMY_VERSION = "1.0.0"


class CyberServiceFamily(StrEnum):
    STRATEGY_VCISO = "security_strategy_vciso"
    AUDIT_RISK_ASSESSMENT = "risk_assessment_audit"
    GRC_COMPLIANCE = "grc_compliance"
    PENETRATION_TESTING = "penetration_testing"
    RED_PURPLE_TEAMING = "red_team_purple_team"
    VULNERABILITY_ATTACK_SURFACE = "vulnerability_management_asm"
    SOC_SIEM_MDR_XDR_SOAR = "soc_siem_mdr_detection"
    INCIDENT_RESPONSE_DFIR = "incident_response_dfir"
    RESILIENCE_CRISIS_READINESS = "resilience_bcp_drp"
    IAM_IGA_PAM_ZERO_TRUST = "iam_pam_zero_trust"
    CLOUD_CONTAINER_SECURITY = "cloud_security"
    APPSEC_DEVSECOPS = "application_security_devsecops"
    NETWORK_SASE_SECURITY = "network_security_sase"
    DATA_PROTECTION = "data_security_privacy"
    THIRD_PARTY_SUPPLY_CHAIN = "third_party_supply_chain"
    OT_ICS_IOT_SECURITY = "ot_ics_iot_security"
    AWARENESS_TRAINING = "security_awareness_training"
    PRODUCT_INTEGRATION_MIGRATION = "product_integration_migration"
    CYBER_INSURANCE_READINESS = "cyber_insurance_readiness"

    @classmethod
    def _missing_(cls, value: object) -> Self | None:
        if not isinstance(value, str):
            return None
        canonical = _LEGACY_SERVICE_FAMILY_VALUES.get(value)
        return None if canonical is None else cls(canonical)


_LEGACY_SERVICE_FAMILY_VALUES = {
    "strategy_vciso": CyberServiceFamily.STRATEGY_VCISO.value,
    "audit_risk_assessment": CyberServiceFamily.AUDIT_RISK_ASSESSMENT.value,
    "red_purple_teaming": CyberServiceFamily.RED_PURPLE_TEAMING.value,
    "vulnerability_attack_surface": CyberServiceFamily.VULNERABILITY_ATTACK_SURFACE.value,
    "soc_siem_mdr_xdr_soar": CyberServiceFamily.SOC_SIEM_MDR_XDR_SOAR.value,
    "resilience_crisis_readiness": CyberServiceFamily.RESILIENCE_CRISIS_READINESS.value,
    "iam_iga_pam_zero_trust": CyberServiceFamily.IAM_IGA_PAM_ZERO_TRUST.value,
    "cloud_container_security": CyberServiceFamily.CLOUD_CONTAINER_SECURITY.value,
    "appsec_devsecops": CyberServiceFamily.APPSEC_DEVSECOPS.value,
    "network_sase_security": CyberServiceFamily.NETWORK_SASE_SECURITY.value,
    "data_protection": CyberServiceFamily.DATA_PROTECTION.value,
    "awareness_training": CyberServiceFamily.AWARENESS_TRAINING.value,
}


@dataclass(frozen=True, slots=True)
class ServiceFamilyMatch:
    family: CyberServiceFamily
    matched_terms: tuple[str, ...]
    confidence: float
    taxonomy_version: str = CANONICAL_TAXONOMY_VERSION

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
        if not self.taxonomy_version.strip():
            raise ValueError("taxonomy_version is required")
        object.__setattr__(self, "matched_terms", terms)
        object.__setattr__(self, "taxonomy_version", self.taxonomy_version.strip())
