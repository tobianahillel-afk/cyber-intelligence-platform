from __future__ import annotations

from cip.modules.service_taxonomy.domain.classifier import matched_cyber_terms


def matched_procurement_terms(*texts: str) -> tuple[str, ...]:
    return matched_cyber_terms(*texts)
