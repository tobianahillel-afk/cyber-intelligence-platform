from __future__ import annotations

from cip.modules.service_taxonomy.domain.models import CyberServiceFamily, ServiceFamilyMatch

_SERVICE_TERMS: dict[CyberServiceFamily, tuple[str, ...]] = {
    CyberServiceFamily.STRATEGY_VCISO: (
        "vciso",
        "virtual ciso",
        "rssI externalisé",
        "rssi externalise",
        "cyber strategy",
        "stratégie cybersécurité",
        "strategie cybersecurite",
    ),
    CyberServiceFamily.AUDIT_RISK_ASSESSMENT: (
        "security audit",
        "audit de sécurité",
        "audit de securite",
        "risk assessment",
        "analyse de risques",
        "ebios",
    ),
    CyberServiceFamily.GRC_COMPLIANCE: (
        "grc",
        "governance risk compliance",
        "iso 27001",
        "nis2",
        "dora",
        "conformité",
        "conformite",
        "homologation",
    ),
    CyberServiceFamily.PENETRATION_TESTING: (
        "penetration test",
        "penetration testing",
        "pentest",
        "test d'intrusion",
        "tests d'intrusion",
    ),
    CyberServiceFamily.RED_PURPLE_TEAMING: (
        "red team",
        "purple team",
        "adversary emulation",
        "simulation d'attaque",
        "simulation d’attaque",
    ),
    CyberServiceFamily.VULNERABILITY_ATTACK_SURFACE: (
        "vulnerability management",
        "gestion des vulnérabilités",
        "gestion des vulnerabilites",
        "attack surface",
        "surface d'attaque",
        "surface d’attaque",
        "asm",
    ),
    CyberServiceFamily.SOC_SIEM_MDR_XDR_SOAR: (
        "siem",
        "soc",
        "security operations center",
        "centre opérationnel de sécurité",
        "centre operationnel de securite",
        "mdr",
        "xdr",
        "soar",
        "security monitoring",
        "supervision de sécurité",
        "supervision de securite",
    ),
    CyberServiceFamily.INCIDENT_RESPONSE_DFIR: (
        "incident response",
        "réponse à incident",
        "reponse a incident",
        "dfir",
        "forensic",
        "investigation numérique",
        "investigation numerique",
    ),
    CyberServiceFamily.RESILIENCE_CRISIS_READINESS: (
        "cyber resilience",
        "cyber résilience",
        "cyber resilience",
        "crisis management",
        "gestion de crise",
        "business continuity",
        "continuité d'activité",
        "continuite d'activite",
        "disaster recovery",
        "reprise d'activité",
        "reprise d’activite",
    ),
    CyberServiceFamily.IAM_IGA_PAM_ZERO_TRUST: (
        "identity and access management",
        "iam",
        "iga",
        "pam",
        "privileged access",
        "zero trust",
        "gestion des identités",
        "gestion des identites",
    ),
    CyberServiceFamily.CLOUD_CONTAINER_SECURITY: (
        "cloud security",
        "sécurité cloud",
        "securite cloud",
        "container security",
        "kubernetes security",
        "cspm",
        "cnapp",
    ),
    CyberServiceFamily.APPSEC_DEVSECOPS: (
        "application security",
        "appsec",
        "devsecops",
        "secure code review",
        "sécurité applicative",
        "securite applicative",
        "sast",
        "dast",
    ),
    CyberServiceFamily.NETWORK_SASE_SECURITY: (
        "network security",
        "sécurité réseau",
        "securite reseau",
        "sase",
        "sd-wan security",
        "firewall",
        "pare-feu",
        "zero trust network access",
        "ztna",
    ),
    CyberServiceFamily.DATA_PROTECTION: (
        "data protection",
        "protection des données",
        "protection des donnees",
        "data loss prevention",
        "dlp",
        "encryption",
        "chiffrement",
    ),
    CyberServiceFamily.THIRD_PARTY_SUPPLY_CHAIN: (
        "third-party risk",
        "third party risk",
        "supplier risk",
        "supply chain security",
        "risque fournisseur",
        "risques fournisseurs",
        "chaîne d'approvisionnement",
        "chaine d'approvisionnement",
    ),
    CyberServiceFamily.OT_ICS_IOT_SECURITY: (
        "ot security",
        "ics security",
        "industrial control system",
        "sécurité industrielle",
        "securite industrielle",
        "iot security",
        "iiot",
    ),
    CyberServiceFamily.AWARENESS_TRAINING: (
        "security awareness",
        "cyber awareness",
        "sensibilisation",
        "formation cybersécurité",
        "formation cybersecurite",
        "phishing simulation",
    ),
    CyberServiceFamily.PRODUCT_INTEGRATION_MIGRATION: (
        "security integration",
        "intégration de sécurité",
        "integration de securite",
        "migration siem",
        "migration sécurité",
        "migration securite",
        "déploiement de solution",
        "deploiement de solution",
    ),
    CyberServiceFamily.CYBER_INSURANCE_READINESS: (
        "cyber insurance",
        "assurance cyber",
        "cyber-insurance readiness",
        "questionnaire assurance",
    ),
}

_GENERIC_CYBER_TERMS = (
    "cybersecurity",
    "cyber security",
    "cybersécurité",
    "cybersecurite",
    "sécurité des systèmes d'information",
    "securite des systemes d'information",
)


def classify_service_families(*texts: str) -> tuple[ServiceFamilyMatch, ...]:
    normalized = " ".join(texts).casefold()
    matches: list[ServiceFamilyMatch] = []
    for family, terms in _SERVICE_TERMS.items():
        matched = tuple(term for term in terms if term.casefold() in normalized)
        if matched:
            matches.append(
                ServiceFamilyMatch(
                    family=family,
                    matched_terms=matched,
                    confidence=min(0.95, 0.72 + 0.06 * len(matched)),
                )
            )
    return tuple(matches)


def contains_cyber_relevance(*texts: str) -> bool:
    normalized = " ".join(texts).casefold()
    if any(term in normalized for term in _GENERIC_CYBER_TERMS):
        return True
    return bool(classify_service_families(normalized))
