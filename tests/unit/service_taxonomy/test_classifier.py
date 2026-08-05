from cip.modules.service_taxonomy.domain.classifier import (
    classify_service_families,
    contains_cyber_relevance,
)
from cip.modules.service_taxonomy.domain.models import CyberServiceFamily


def test_classifier_covers_multiple_independent_service_families() -> None:
    matches = classify_service_families(
        "Audit ISO 27001, PAM, pentest and incident response support"
    )

    assert {match.family for match in matches} == {
        CyberServiceFamily.AUDIT_RISK_ASSESSMENT,
        CyberServiceFamily.GRC_COMPLIANCE,
        CyberServiceFamily.PENETRATION_TESTING,
        CyberServiceFamily.INCIDENT_RESPONSE_DFIR,
        CyberServiceFamily.IAM_IGA_PAM_ZERO_TRUST,
    }
    assert all(0.0 < match.confidence <= 0.95 for match in matches)


def test_classifier_does_not_default_to_siem_for_generic_cyber_text() -> None:
    assert contains_cyber_relevance("Programme global de cybersécurité") is True
    assert classify_service_families("Programme global de cybersécurité") == ()


def test_classifier_returns_no_match_for_unrelated_procurement() -> None:
    assert contains_cyber_relevance("Fourniture de mobilier de bureau") is False
    assert classify_service_families("Fourniture de mobilier de bureau") == ()
