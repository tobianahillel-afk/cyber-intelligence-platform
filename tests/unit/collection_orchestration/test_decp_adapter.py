from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.decp.client import DecpCheckpoint, DecpSourceResponseError
from cip.adapters.sources.decp.collector import (
    DecpCollectionBatch,
    DecpCollectionDeniedError,
    DecpSourceSchemaError,
    DecpSourceWindowError,
)
from cip.modules.collection_orchestration.application import decp_adapter as adapter_module
from cip.modules.collection_orchestration.application.decp_adapter import DecpAdapter
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 5, 10, 0, tzinfo=UTC)


def _entry() -> SourceRegistryEntry:
    return load_source_registry(Path("policies/sources.decp.yml"))[0]


def test_decp_adapter_propagates_checkpoint_and_procurement_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_collect(client: object, entry: object, **kwargs: object) -> DecpCollectionBatch:
        del client, entry
        captured.update(kwargs)
        return DecpCollectionBatch(
            observations=(),
            buyers=(),
            procurement=(),
            checkpoint=DecpCheckpoint(
                latest_revision_key="new-revision",
                latest_publication_date="2026-09-02",
            ),
            not_modified=True,
        )

    monkeypatch.setattr(adapter_module, "collect_decp_contracts", fake_collect)
    batch = DecpAdapter(_entry()).collect(
        collection_job_id=uuid4(),
        checkpoint_payload={
            "latest_revision_key": "old-revision",
            "latest_publication_date": "2026-09-01",
        },
        collected_at=NOW,
        retention_until=NOW + timedelta(days=3650),
    )

    checkpoint = captured["checkpoint"]
    assert isinstance(checkpoint, DecpCheckpoint)
    assert checkpoint.latest_revision_key == "old-revision"
    assert batch.not_modified is True
    assert batch.commercial_projections == ()
    assert batch.procurement_organizations == ()
    assert batch.procurement_projections == ()
    assert batch.checkpoint_payload == {
        "latest_revision_key": "new-revision",
        "latest_publication_date": "2026-09-02",
    }


def test_decp_adapter_validates_constructor_and_checkpoint() -> None:
    with pytest.raises(ValueError, match="timeout"):
        DecpAdapter(_entry(), timeout_seconds=0)
    for key in ("latest_revision_key", "latest_publication_date"):
        with pytest.raises(AdapterExecutionError, match=key) as error:
            DecpAdapter(_entry()).collect(
                collection_job_id=uuid4(),
                checkpoint_payload={key: 42},
                collected_at=NOW,
                retention_until=NOW + timedelta(days=3650),
            )
        assert error.value.error_code == "invalid_checkpoint"
        assert error.value.retryable is False


@pytest.mark.parametrize(
    ("exception", "error_code", "retryable"),
    [
        (DecpCollectionDeniedError("blocked"), "source_policy_denied", False),
        (DecpSourceSchemaError("drift"), "source_schema_drift", False),
        (DecpSourceWindowError("overflow"), "source_window_exceeded", False),
        (DecpSourceResponseError("unsafe"), "unsafe_source_response", True),
        (httpx.ReadTimeout("timeout"), "source_transport_error", True),
    ],
)
def test_decp_adapter_normalizes_errors(
    monkeypatch: pytest.MonkeyPatch,
    exception: Exception,
    error_code: str,
    retryable: bool,
) -> None:
    monkeypatch.setattr(
        adapter_module,
        "collect_decp_contracts",
        lambda *args, **kwargs: (_ for _ in ()).throw(exception),
    )

    with pytest.raises(AdapterExecutionError) as error:
        DecpAdapter(_entry()).collect(
            collection_job_id=uuid4(),
            checkpoint_payload=None,
            collected_at=NOW,
            retention_until=NOW + timedelta(days=3650),
        )

    assert error.value.error_code == error_code
    assert error.value.retryable is retryable
