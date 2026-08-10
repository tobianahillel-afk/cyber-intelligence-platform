from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from cip.modules.collection_orchestration.application.phishtank_adapter import PhishTankAdapter
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.source_governance.infrastructure.registry import load_source_registry

NOW = datetime(2026, 8, 9, 23, 30, tzinfo=UTC)


def test_phishtank_transport_error_never_exposes_key_from_request_url() -> None:
    entry = {
        item.policy.id: item
        for item in load_source_registry(Path("policies/sources.threat_telemetry.yml"))
    }["phishtank-verified-online"]

    def failing_transport(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"failed to connect to {request.url}", request=request)

    adapter = PhishTankAdapter(
        entry,
        token_provider=lambda: "secret-key",
        user_agent="CIP contact@example.com",
        transport=httpx.MockTransport(failing_transport),
    )

    with pytest.raises(AdapterExecutionError) as error:
        adapter.collect(
            collection_job_id=UUID("00000000-0000-0000-0000-000000000408"),
            checkpoint_payload=None,
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )

    assert error.value.error_code == "source_transport_error"
    assert error.value.retryable is True
    assert str(error.value) == "intelligence provider transport failure"
    assert "secret-key" not in str(error.value)
