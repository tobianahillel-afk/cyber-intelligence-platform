from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import pytest

from cip.adapters.sources.public_web.delegated_authenticated_evidence import (
    build_delegated_authenticated_evidence,
)
from cip.modules.source_governance.application.delegated_provider_session_service import (
    DelegatedAuthenticatedPage,
)


def _page(html: bytes) -> DelegatedAuthenticatedPage:
    return DelegatedAuthenticatedPage(
        identity_id=uuid4(),
        source_id="controlled-auth-provider",
        final_url="https://provider.example/private",
        html=html,
        session_established=False,
        session_reused=True,
        requests_seen=1,
        redirects_seen=0,
    )


def test_authenticated_evidence_preserves_provenance_without_secret_body() -> None:
    now = datetime(2026, 8, 17, 12, tzinfo=UTC)
    html = b"""<html><head>
<meta property="og:title" content="Authenticated evidence">
<script type="application/json">{
  "name":"Authorized portal",
  "provider":"Controlled provider",
  "sessionToken":"must-not-persist",
  "password":"must-not-persist-either"
}</script></head><body><main>private account evidence</main></body></html>"""
    page = _page(html)

    evidence = build_delegated_authenticated_evidence(
        page,
        collection_job_id=uuid4(),
        collected_at=now,
        retention_until=now + timedelta(days=1),
    )

    observation = evidence.observation
    assert observation.source_id == page.source_id
    assert observation.adapter_id == "public-web-delegated-session"
    assert observation.source_record_type == "authenticated_web_page"
    assert observation.source_url == page.final_url
    assert str(page.identity_id) in (observation.source_record_key or "")
    assert observation.payload_hash_sha256 == sha256(html).hexdigest()
    assert observation.classification == "internal"
    assert evidence.structured_record_count == 1
    assert evidence.structured_extracted
    expected_structured = "Authorized portal Controlled provider"
    assert evidence.structured_text_sha256 == sha256(expected_structured.encode()).hexdigest()
    assert evidence.semantic_text_sha256 == sha256(b"Authenticated evidence").hexdigest()
    assert "must-not-persist" not in repr(evidence)
    assert "private account evidence" not in repr(evidence)


def test_authenticated_evidence_without_structured_json_is_explicit() -> None:
    now = datetime(2026, 8, 17, 12, tzinfo=UTC)
    evidence = build_delegated_authenticated_evidence(
        _page(b"<html><body><main>semantic-only evidence</main></body></html>"),
        collection_job_id=uuid4(),
        collected_at=now,
        retention_until=now + timedelta(days=1),
    )

    assert evidence.structured_record_count == 0
    assert not evidence.structured_extracted
    assert evidence.structured_text_sha256 is None
    assert evidence.semantic_text_sha256 is None


def test_authenticated_evidence_rejects_missing_rendered_body() -> None:
    now = datetime(2026, 8, 17, 12, tzinfo=UTC)
    with pytest.raises(ValueError, match="rendered page html"):
        build_delegated_authenticated_evidence(
            _page(b""),
            collection_job_id=uuid4(),
            collected_at=now,
            retention_until=now + timedelta(days=1),
        )
