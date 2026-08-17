from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from uuid import UUID

from cip.adapters.sources.public_web.semantic_html import extract_semantic_html
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.application.delegated_provider_session_service import (
    DelegatedAuthenticatedPage,
)
from cip.modules.source_governance.domain.models import DataCategory

_AUTHENTICATED_ADAPTER_ID = "public-web-delegated-session"
_AUTHENTICATED_SCHEMA = "authenticated-web-page-v1"


@dataclass(frozen=True, slots=True)
class DelegatedAuthenticatedEvidence:
    observation: RawObservation
    structured_record_count: int
    structured_text_sha256: str | None
    semantic_text_sha256: str | None

    @property
    def structured_extracted(self) -> bool:
        return self.structured_record_count > 0 and self.structured_text_sha256 is not None


def build_delegated_authenticated_evidence(
    page: DelegatedAuthenticatedPage,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> DelegatedAuthenticatedEvidence:
    if not page.html:
        raise ValueError("authenticated rendered page html is required")
    semantic = extract_semantic_html(page.html)
    observation = RawObservation(
        source_id=page.source_id,
        adapter_id=_AUTHENTICATED_ADAPTER_ID,
        adapter_version="1",
        collection_job_id=collection_job_id,
        source_record_type="authenticated_web_page",
        source_record_key=f"delegated:{page.identity_id}:{page.final_url}",
        source_url=page.final_url,
        payload_hash_sha256=sha256(page.html).hexdigest(),
        data_categories=frozenset({DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}),
        collected_at=collected_at,
        observed_at=collected_at,
        source_updated_at=semantic.source_updated_at,
        schema_fingerprint=_AUTHENTICATED_SCHEMA,
        classification="internal",
        retention_until=retention_until,
    )
    return DelegatedAuthenticatedEvidence(
        observation=observation,
        structured_record_count=semantic.structured_record_count,
        structured_text_sha256=_hash_optional(semantic.structured_text),
        semantic_text_sha256=_hash_optional(semantic.semantic_text),
    )


def _hash_optional(value: str) -> str | None:
    return sha256(value.encode("utf-8")).hexdigest() if value else None
