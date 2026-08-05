from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CyberServiceFamily(StrEnum):
    STRATEGY_VCISO = "strategy_vciso"
    AUDIT_RISK_ASSESSMENT = "audit_risk_assessment"
    GRC_COMPLIANCE = "grc_compliance"
    PENETRATION_TESTING = "penetration_testing"
    RED_PURPLE_TEAMING = "red_purple_teaming"
    VULNERABILITY_ATTACK_SURFACE = "vulnerability_attack_surface"
    SOC_SIEM_MDR_XDR_SOAR = "soc_siem_mdr_xdr_soar"
    INCIDENT_RESPONSE_DFIR = "incident_response_dfir"
    RESILIENCE_CRISIS_READINESS = "resilience_crisis_readiness"
    IAM_IGA_PAM_ZERO_TRUST = "iam_iga_pam_zero_trust"
    CLOUD_CONTAINER_SECURITY = "cloud_container_security"
    APPSEC_DEVSECOPS = "appsec_devsecops"
    NETWORK_SASE_SECURITY = "network_sase_security"
    DATA_PROTECTION = "data_protection"
    THIRD_PARTY_SUPPLY_CHAIN = "third_party_supply_chain"
    OT_ICS_IOT_SECURITY = "ot_ics_iot_security"
    AWARENESS_TRAINING = "awareness_training"
    PRODUCT_INTEGRATION_MIGRATION = "product_integration_migration"
    CYBER_INSURANCE_READINESS = "cyber_insurance_readiness"


@dataclass(frozen=True, slots=True)
class ServiceFamilyMatch:
    family: CyberServiceFamily
    matched_terms: tuple[str, ...]
    confidence: float

    def __post_init__(self) -> None:
        terms = tuple(dict.fromkeys(term.strip().casefold() for term in self.matched_terms if term.strip()))
        if not terms:
            raise ValueError("service family match requires at least one term")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(self, "matched_terms", terms)
