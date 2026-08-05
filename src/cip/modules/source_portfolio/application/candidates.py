from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

from sqlalchemy.orm import Session

from cip.modules.source_portfolio.application.catalog import sync_source_portfolio
from cip.modules.source_portfolio.domain.models import CatalogStatus, SourceCatalogEntry


@dataclass(frozen=True, slots=True)
class CatalogCandidateInput:
    display_name: str
    canonical_url: str
    category: str
    commercial_use_cases: tuple[str, ...] = ("source_discovery",)
    metadata: dict[str, object] | None = None


def import_catalog_candidates(
    session: Session,
    origin: str,
    candidates: Sequence[CatalogCandidateInput],
    *,
    now: datetime,
) -> tuple[str, ...]:
    normalized_origin = origin.strip()
    if not normalized_origin:
        raise ValueError("catalog candidate origin is required")
    entries = tuple(
        SourceCatalogEntry(
            source_id=_candidate_id(normalized_origin, candidate.canonical_url),
            display_name=candidate.display_name,
            canonical_url=candidate.canonical_url,
            category=candidate.category,
            status=CatalogStatus.CANDIDATE,
            freshness_max_age_seconds=2_592_000,
            commercial_use_cases=candidate.commercial_use_cases,
            candidate_origin=normalized_origin,
            metadata={
                "executable": False,
                "authorization_required": True,
                **(candidate.metadata or {}),
            },
        )
        for candidate in candidates
    )
    return sync_source_portfolio(session, entries, now=now)


def _candidate_id(origin: str, canonical_url: str) -> str:
    normalized_url = canonical_url.strip().lower()
    digest = sha256(f"{origin}:{normalized_url}".encode()).hexdigest()[:20]
    return f"candidate-{digest}"
