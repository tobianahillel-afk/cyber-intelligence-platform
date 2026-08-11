from cip.modules.service_taxonomy.domain.classifier import classify_service_families
from cip.modules.service_taxonomy.domain.models import (
    CyberServiceFamily,
    parse_service_family,
    service_family_identifiers,
)

EXPECTED_IDS = {
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

PHRASES = {
    CyberServiceFamily.STRATEGY_VCISO: "virtual CISO cyber strategy",
    CyberServiceFamily.AUDIT_RISK_ASSESSMENT: "EBIOS risk assessment",
    CyberServiceFamily.GRC_COMPLIANCE: "ISO 27001 DORA compliance",
    CyberServiceFamily.PENETRATION_TESTING: "penetration testing",
    CyberServiceFamily.RED_PURPLE_TEAMING: "purple team exercise",
    CyberServiceFamily.VULNERABILITY_ATTACK_SURFACE: "attack surface management",
    CyberServiceFamily.SOC_SIEM_MDR_XDR_SOAR: "SIEM MDR security monitoring",
    CyberServiceFamily.INCIDENT_RESPONSE_DFIR: "incident response DFIR",
    CyberServiceFamily.RESILIENCE_CRISIS_READINESS: "business continuity disaster recovery",
    CyberServiceFamily.IAM_IGA_PAM_ZERO_TRUST: "IAM PAM zero trust",
    CyberServiceFamily.CLOUD_CONTAINER_SECURITY: "cloud security CSPM",
    CyberServiceFamily.APPSEC_DEVSECOPS: "application security DevSecOps",
    CyberServiceFamily.NETWORK_SASE_SECURITY: "network security SASE",
    CyberServiceFamily.DATA_PROTECTION: "data loss prevention encryption",
    CyberServiceFamily.THIRD_PARTY_SUPPLY_CHAIN: "third-party risk supply chain security",
    CyberServiceFamily.OT_ICS_IOT_SECURITY: "OT security industrial control system",
    CyberServiceFamily.AWARENESS_TRAINING: "security awareness phishing simulation",
    CyberServiceFamily.PRODUCT_INTEGRATION_MIGRATION: "security integration migration SIEM",
    CyberServiceFamily.CYBER_INSURANCE_READINESS: "cyber insurance readiness",
}

LEGACY_IDS = {
    "strategy_vciso": "security_strategy_vciso",
    "audit_risk_assessment": "risk_assessment_audit",
    "red_purple_teaming": "red_team_purple_team",
    "vulnerability_attack_surface": "vulnerability_management_asm",
    "soc_siem_mdr_xdr_soar": "soc_siem_mdr_detection",
    "resilience_crisis_readiness": "resilience_bcp_drp",
    "iam_iga_pam_zero_trust": "iam_pam_zero_trust",
    "cloud_container_security": "cloud_security",
    "appsec_devsecops": "application_security_devsecops",
    "network_sase_security": "network_security_sase",
    "data_protection": "data_security_privacy",
    "awareness_training": "security_awareness_training",
}


def test_taxonomy_has_exactly_the_19_locked_canonical_ids() -> None:
    assert {family.value for family in CyberServiceFamily} == EXPECTED_IDS
    assert len(CyberServiceFamily) == 19


def test_legacy_persisted_ids_parse_to_canonical_values() -> None:
    for legacy, canonical in LEGACY_IDS.items():
        assert parse_service_family(legacy).value == canonical
        assert parse_service_family(canonical).value == canonical


def test_read_identifiers_include_canonical_and_legacy_persisted_values() -> None:
    identifiers = service_family_identifiers("iam_iga_pam_zero_trust")

    assert identifiers[0] == "iam_pam_zero_trust"
    assert "iam_iga_pam_zero_trust" in identifiers
    assert len(identifiers) == len(set(identifiers))


def test_classifier_has_a_positive_fixture_for_every_service_family() -> None:
    for family, phrase in PHRASES.items():
        matches = classify_service_families(phrase)
        assert family in {match.family for match in matches}


def test_classifier_keeps_multilingual_aliases() -> None:
    matches = classify_service_families(
        "audit de sécurité, gestion des vulnérabilités et sécurité cloud"
    )
    families = {match.family for match in matches}
    assert CyberServiceFamily.AUDIT_RISK_ASSESSMENT in families
    assert CyberServiceFamily.VULNERABILITY_ATTACK_SURFACE in families
    assert CyberServiceFamily.CLOUD_CONTAINER_SECURITY in families
