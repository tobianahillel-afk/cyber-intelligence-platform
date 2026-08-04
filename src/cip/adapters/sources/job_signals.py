from __future__ import annotations

JOB_SIGNAL_TERMS = (
    "soc analyst",
    "soc manager",
    "soc engineer",
    "siem engineer",
    "security operations",
    "security operations center",
    "detection engineer",
    "detection engineering",
    "threat detection",
    "incident response",
    "security monitoring",
    "log management",
    "managed detection and response",
    "microsoft sentinel",
    "azure sentinel",
    "splunk enterprise security",
    "splunk es",
    "sekoia",
    "qradar",
    "xdr",
    "mdr",
)


def matched_job_terms(*texts: str) -> tuple[str, ...]:
    normalized = " ".join(texts).casefold()
    return tuple(term for term in JOB_SIGNAL_TERMS if term in normalized)
