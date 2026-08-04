from __future__ import annotations

PROCUREMENT_SIGNAL_TERMS = (
    "siem",
    "soc",
    "security operations center",
    "cybersecurity",
    "cyber security",
    "cybersécurité",
    "cybersecurite",
    "managed detection and response",
    "mdr",
    "xdr",
    "security monitoring",
    "supervision de sécurité",
    "centre opérationnel de sécurité",
)


def matched_procurement_terms(*texts: str) -> tuple[str, ...]:
    normalized = " ".join(texts).casefold()
    return tuple(term for term in PROCUREMENT_SIGNAL_TERMS if term in normalized)
