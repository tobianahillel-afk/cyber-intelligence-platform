from cip.modules.service_taxonomy.domain.models import (
    CANONICAL_TAXONOMY_VERSION,
    CyberServiceFamily,
)

CANONICAL_IDS = {
    "security_strategy_vciso",
    "risk_assessment_audit",
    "grc_compliance",
    "penetration_testing",
    "red_team_purple_team",
    "vulnerability_management_asm",
    "soc_siem_mdr_detection",
    "incident_response_dfir",
    "resilience_bcp_drp",
    "iam_pam_zero_trust",
    "cloud_security",
    "application_security_devsecops",
    "network_security_sase",
    "data_security_privacy",
    "third_party_supply_chain",
    "ot_ics_iot_security",
    "security_awareness_training",
    "product_integration_migration",
    "cyber_insurance_readiness",
}

LEGACY_IDS = {
    "strategy_vciso": CyberServiceFamily.STRATEGY_VCISO,
    "audit_risk_assessment": CyberServiceFamily.AUDIT_RISK_ASSESSMENT,
    "red_purple_teaming": CyberServiceFamily.RED_PURPLE_TEAMING,
    "vulnerability_attack_surface": CyberServiceFamily.VULNERABILITY_ATTACK_SURFACE,
    "soc_siem_mdr_xdr_soar": CyberServiceFamily.SOC_SIEM_MDR_XDR_SOAR,
    "resilience_crisis_readiness": CyberServiceFamily.RESILIENCE_CRISIS_READINESS,
    "iam_iga_pam_zero_trust": CyberServiceFamily.IAM_IGA_PAM_ZERO_TRUST,
    "cloud_container_security": CyberServiceFamily.CLOUD_CONTAINER_SECURITY,
    "appsec_devsecops": CyberServiceFamily.APPSEC_DEVSECOPS,
    "network_sase_security": CyberServiceFamily.NETWORK_SASE_SECURITY,
    "data_protection": CyberServiceFamily.DATA_PROTECTION,
    "awareness_training": CyberServiceFamily.AWARENESS_TRAINING,
}


def test_taxonomy_exposes_all_documented_canonical_ids() -> None:
    assert {family.value for family in CyberServiceFamily} == CANONICAL_IDS
    assert CANONICAL_TAXONOMY_VERSION == "1.0.0"


def test_historical_service_family_values_remain_read_compatible() -> None:
    for historical_value, expected_family in LEGACY_IDS.items():
        parsed = CyberServiceFamily(historical_value)
        assert parsed is expected_family
        assert parsed.value in CANONICAL_IDS
