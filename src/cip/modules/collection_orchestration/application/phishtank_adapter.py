from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from urllib.parse import quote
from uuid import UUID

import httpx
from pydantic import TypeAdapter, ValidationError

from cip.adapters.sources.threat_catalogs.mappers import map_phishing_metadata
from cip.adapters.sources.threat_catalogs.phishtank_schemas import PhishTankFeedRecord
from cip.adapters.sources.threat_catalogs.schemas import (
    ObservableType,
    PhishingMetadataRecord,
    ProviderState,
)
from cip.modules.collection_orchestration.application.intelligence_adapter_support import (
    HARD_MAX_JSON_BYTES,
    IntelligenceObservationContext,
    authorize_intelligence_request,
    get_json,
    raw_intelligence_observation,
)
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.modules.threat_telemetry.domain.models import IndicatorSnapshot
from cip.shared.kernel.time import require_aware_utc

_MAX_FEED_RECORDS = 100_000
_MAX_PROJECTED_RECORDS = 1_000
_FRESHNESS = timedelta(hours=2)
PURPOSE = "threat-telemetry"


class PhishTankAdapter:
    source_id = "phishtank-verified-online"
    adapter_id = "phishtank-online-valid-json"
    adapter_version = "1"
    data_category = DataCategory.TECHNOLOGY_OBSERVATION

    def __init__(
        self,
        entry: SourceRegistryEntry,
        *,
        token_provider: Callable[[], str | None],
        user_agent: str | None,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("PhishTank adapter requires phishtank-verified-online policy")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._entry = entry
        self._token_provider = token_provider
        self._user_agent = user_agent.strip() if user_agent else None
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch:
        del checkpoint_payload
        token = self._token_provider()
        if token is None or not token.strip():
            raise AdapterExecutionError(
                "PhishTank automated feed requires an application key",
                error_code="provider_not_connected",
                retryable=False,
            )
        if self._user_agent is None:
            raise AdapterExecutionError(
                "PhishTank automated feed requires a descriptive User-Agent",
                error_code="provider_not_configured",
                retryable=False,
            )
        request_url = (
            f"{self._entry.policy.base_url}{quote(token.strip(), safe='')}/online-valid.json"
        )
        authorize_intelligence_request(
            self._entry,
            category=self.data_category,
            purpose=PURPOSE,
            target_url=request_url,
            collected_at=collected_at,
        )
        records = self._fetch(request_url)
        selected = tuple(
            sorted(records, key=lambda record: record.phish_id, reverse=True)[
                :_MAX_PROJECTED_RECORDS
            ]
        )
        context = IntelligenceObservationContext(
            source_id=self.source_id,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            collection_job_id=collection_job_id,
            data_category=self.data_category,
            collected_at=collected_at,
            retention_until=retention_until,
        )
        observations = []
        snapshots = []
        safe_source_url = f"{self._entry.policy.base_url}online-valid.json"
        for record in selected:
            snapshot = _map_record(record, collected_at=collected_at)
            if snapshot is None:
                continue
            observations.append(
                raw_intelligence_observation(
                    record,
                    context=context,
                    source_url=safe_source_url,
                    source_record_key=str(record.phish_id),
                    source_record_type="phishtank-verified-online",
                    observed_at=record.submission_time,
                    published_at=record.verification_time,
                    source_updated_at=collected_at,
                )
            )
            snapshots.append(snapshot)
        return AdapterCollectionBatch(
            observations=tuple(observations),
            threat_indicator_snapshots=tuple(snapshots),
            checkpoint_payload={"feed_size": len(records)},
            not_modified=not snapshots,
        )

    def _fetch(self, request_url: str) -> tuple[PhishTankFeedRecord, ...]:
        with httpx.Client(
            timeout=self._timeout_seconds,
            follow_redirects=False,
            transport=self._transport,
        ) as client:
            body = get_json(
                client,
                request_url,
                headers={"User-Agent": self._user_agent or ""},
                max_bytes=HARD_MAX_JSON_BYTES,
            )
        try:
            records = tuple(TypeAdapter(list[PhishTankFeedRecord]).validate_json(body))
        except ValidationError as exc:
            raise AdapterExecutionError(
                "PhishTank feed schema changed",
                error_code="source_schema_drift",
                retryable=False,
            ) from exc
        if len(records) > _MAX_FEED_RECORDS:
            raise AdapterExecutionError(
                "PhishTank feed exceeds record bound",
                error_code="source_page_too_large",
                retryable=False,
            )
        return records


def _map_record(
    record: PhishTankFeedRecord,
    *,
    collected_at: datetime,
) -> IndicatorSnapshot | None:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    submitted = require_aware_utc(record.submission_time, field_name="submission_time")
    verified = require_aware_utc(record.verification_time, field_name="verification_time")
    modified = max(verified, collected)
    try:
        metadata = PhishingMetadataRecord(
            record_id=str(record.phish_id),
            source_url=(
                "https://www.phishtank.com/phish_detail.php?phish_id="
                f"{record.phish_id}"
            ),
            observable_type=ObservableType.URL,
            value=record.url,
            state=ProviderState.MALICIOUS,
            published_at=verified,
            modified_at=modified,
            first_seen_at=submitted,
            last_seen_at=collected,
            expires_at=collected + _FRESHNESS,
            confidence=0.95,
            source_precedence=80,
            independence_key=PhishTankAdapter.source_id,
            sensor_scope="provider_aggregate",
            historical_only=False,
            active=True,
        )
        return map_phishing_metadata(metadata, source_id=PhishTankAdapter.source_id)
    except ValueError:
        return None
