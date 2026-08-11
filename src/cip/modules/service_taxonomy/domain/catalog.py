from __future__ import annotations

from cip.modules.service_taxonomy.domain.models import CyberServiceFamily

_SERVICE_OFFERS: dict[CyberServiceFamily, tuple[str, ...]] = {
    CyberServiceFamily.STRATEGY_VCISO: ("vCISO", "security strategy roadmap"),
    CyberServiceFamily.AUDIT_RISK_ASSESSMENT: ("security audit", "risk assessment"),
    CyberServiceFamily.GRC_COMPLIANCE: ("GRC program", "compliance readiness"),
    CyberServiceFamily.PENETRATION_TESTING: ("penetration testing",),
    CyberServiceFamily.RED_PURPLE_TEAMING: ("red team", "purple team"),
    CyberServiceFamily.VULNERABILITY_ATTACK_SURFACE: (
        "vulnerability management",
        "attack surface management",
    ),
    CyberServiceFamily.SOC_SIEM_MDR_XDR_SOAR: (
        "SOC/SIEM engineering",
        "MDR and detection engineering",
    ),
    CyberServiceFamily.INCIDENT_RESPONSE_DFIR: ("incident response", "DFIR retainer"),
    CyberServiceFamily.RESILIENCE_CRISIS_READINESS: (
        "business continuity",
        "disaster recovery and crisis readiness",
    ),
    CyberServiceFamily.IAM_IGA_PAM_ZERO_TRUST: ("IAM/PAM program", "Zero Trust"),
    CyberServiceFamily.CLOUD_CONTAINER_SECURITY: ("cloud security",),
    CyberServiceFamily.APPSEC_DEVSECOPS: ("application security", "DevSecOps"),
    CyberServiceFamily.NETWORK_SASE_SECURITY: ("network security", "SASE/SSE"),
    CyberServiceFamily.DATA_PROTECTION: ("data security", "privacy engineering"),
    CyberServiceFamily.THIRD_PARTY_SUPPLY_CHAIN: (
        "third-party risk",
        "supply-chain security",
    ),
    CyberServiceFamily.OT_ICS_IOT_SECURITY: ("OT/ICS/IoT security",),
    CyberServiceFamily.AWARENESS_TRAINING: ("security awareness training",),
    CyberServiceFamily.PRODUCT_INTEGRATION_MIGRATION: (
        "security product integration",
        "security migration",
    ),
    CyberServiceFamily.CYBER_INSURANCE_READINESS: ("cyber-insurance readiness",),
}


def applicable_offers(
    families: tuple[CyberServiceFamily, ...],
) -> tuple[str, ...]:
    offers: list[str] = []
    for family in families:
        offers.extend(_SERVICE_OFFERS[family])
    return tuple(dict.fromkeys(offers))
