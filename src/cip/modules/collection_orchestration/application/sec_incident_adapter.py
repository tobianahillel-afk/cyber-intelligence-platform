from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

import httpx
from pydantic import ValidationError

from cip.adapters.sources.incident_catalogs.mappers import map_official_disclosure
from cip.adapters.sources.incident_catalogs.schemas import (
    OfficialDisclosureKind,
    OfficialIncidentDisclosure,
    OrganizationReference,
    PublicIncidentKind,
)
from cip.adapters.sources.incident_catalogs.sec_registry import SecIncidentTarget
from cip.adapters.sources.incident_catalogs.sec_schemas import (
    SecCyberFilingRecord,
    SecSubmissionResponse,
)
from cip.modules.collection_orchestration.application.intelligence_adapter_support import (
    IntelligenceObservationContext,
    authorize_intelligence_request,
    get_json,
    raw_intelligence_observation,
)
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.incident_intelligence.domain.models import IncidentClaimSnapshot
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc

_ALLOWED_FORMS = frozenset({"8-K", "8-K12B", "8-K12G3", "8-K15D5"})
_ITEM_105 = re.compile(r"(?:^|[,;\s])1\.05(?:$|[,;\s])")
_MAX_CYBER_FILINGS_PER_RUN = 100
_MAX_CURSOR_TARGETS = 500
PURPOSE = "incident-intelligence"


class SecCyberDisclosureAdapter:
    source_id = "sec-cyber-disclosures"
    adapter_id = "sec-submissions-item-1-05"
    adapter_version = "1"
    data_category = DataCategory.PUBLIC_INCIDENT_METADATA

    def __init__(
        self,
        entry: SourceRegistryEntry,
        targets: tuple[SecIncidentTarget, ...],
        *,
        user_agent: str | None,
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("SEC adapter requires sec-cyber-disclosures policy")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._entry = entry
        self._targets = tuple(target for target in targets if target.enabled)
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
        target, next_index = _next_target(self._targets, checkpoint_payload)
        if target is None:
            return _empty_batch()
        if self._user_agent is None:
            raise AdapterExecutionError(
                "SEC automated access requires a declared User-Agent",
                error_code="provider_not_configured",
                retryable=False,
            )
        target_url = f"{self._entry.policy.base_url}CIK{target.cik}.json"
        authorize_intelligence_request(
            self._entry,
            category=self.data_category,
            purpose=PURPOSE,
            target_url=target_url,
            collected_at=collected_at,
        )
        response = self._fetch(target_url)
        _validate_response_cik(response.cik, target.cik)
        cursors = _cursor_map(checkpoint_payload, self._targets)
        newest_accession = (
            response.filings.recent.accessionNumber[0]
            if response.filings.recent.accessionNumber
            else None
        )
        filings = _new_cyber_filings(
            response,
            stop_at=cursors.get(target.target_id),
        )
        if newest_accession is not None:
            cursors[target.target_id] = newest_accession
        context = IntelligenceObservationContext(
            source_id=self.source_id,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            collection_job_id=collection_job_id,
            data_category=self.data_category,
            collected_at=collected_at,
            retention_until=retention_until,
        )
        observations = tuple(
            raw_intelligence_observation(
                filing,
                context=context,
                source_url=target_url,
                source_record_key=filing.accession_number,
                source_record_type="sec-item-1-05-filing",
                published_at=filing.accepted_at,
                source_updated_at=filing.accepted_at,
            )
            for filing in filings
        )
        claims = tuple(
            _map_filing(
                filing,
                target=target,
                issuer_name=response.name,
                source_url=target_url,
            )
            for filing in filings
        )
        return AdapterCollectionBatch(
            observations=observations,
            incident_claims=claims,
            checkpoint_payload={
                "target_index": next_index,
                "last_accession_by_target": cursors,
            },
            not_modified=not claims,
        )

    def _fetch(self, target_url: str) -> SecSubmissionResponse:
        with httpx.Client(
            timeout=self._timeout_seconds,
            follow_redirects=False,
            transport=self._transport,
        ) as client:
            body = get_json(
                client,
                target_url,
                headers={"User-Agent": self._user_agent or ""},
            )
        try:
            return SecSubmissionResponse.model_validate_json(body)
        except ValidationError as exc:
            raise AdapterExecutionError(
                "SEC submissions response schema changed",
                error_code="source_schema_drift",
                retryable=False,
            ) from exc


def _new_cyber_filings(
    response: SecSubmissionResponse,
    *,
    stop_at: str | None,
) -> tuple[SecCyberFilingRecord, ...]:
    recent = response.filings.recent
    records: list[SecCyberFilingRecord] = []
    for index, accession in enumerate(recent.accessionNumber):
        if accession == stop_at:
            break
        form = recent.form[index].strip().upper()
        items = recent.items[index]
        if form not in _ALLOWED_FORMS or _ITEM_105.search(items) is None:
            continue
        records.append(
            SecCyberFilingRecord(
                accession_number=accession,
                form=form,
                item="1.05",
                filing_date=recent.filingDate[index],
                accepted_at=require_aware_utc(
                    recent.acceptanceDateTime[index],
                    field_name="acceptanceDateTime",
                ),
            )
        )
        if len(records) >= _MAX_CYBER_FILINGS_PER_RUN:
            break
    return tuple(records)


def _map_filing(
    filing: SecCyberFilingRecord,
    *,
    target: SecIncidentTarget,
    issuer_name: str,
    source_url: str,
) -> IncidentClaimSnapshot:
    record = OfficialIncidentDisclosure(
        record_id=filing.accession_number,
        incident_key=f"sec-item-1.05:{target.cik}:{filing.accession_number}",
        source_url=source_url,
        disclosure_kind=OfficialDisclosureKind.COMPANY_CONFIRMATION,
        incident_kind=PublicIncidentKind.UNKNOWN,
        title=f"SEC {filing.form} Item 1.05 cybersecurity incident disclosure",
        summary=(
            "Official SEC filing metadata indicates a material cybersecurity incident "
            "disclosure under Item 1.05. The filing narrative was not collected by SA-04."
        ),
        organization=OrganizationReference(
            claimed_name=issuer_name,
            exact_registration_id=f"SEC-CIK:{target.cik}",
            exact_organization_id=str(target.organization_id),
        ),
        published_at=filing.accepted_at,
        modified_at=filing.accepted_at,
        confirmed_at=filing.accepted_at,
    )
    return map_official_disclosure(record, source_id=SecCyberDisclosureAdapter.source_id)


def _validate_response_cik(value: str | int, expected: str) -> None:
    normalized = str(value).strip().zfill(10)
    if normalized != expected:
        raise AdapterExecutionError(
            "SEC response CIK does not match requested target",
            error_code="source_identity_mismatch",
            retryable=False,
        )


def _cursor_map(
    payload: Mapping[str, object] | None,
    targets: tuple[SecIncidentTarget, ...],
) -> dict[str, str]:
    if payload is None:
        return {}
    raw = payload.get("last_accession_by_target", {})
    if not isinstance(raw, dict) or len(raw) > _MAX_CURSOR_TARGETS:
        raise _invalid_checkpoint()
    known_ids = {target.target_id for target in targets}
    result: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise _invalid_checkpoint()
        if key in known_ids:
            result[key] = value
    return result


def _next_target(
    targets: tuple[SecIncidentTarget, ...],
    payload: Mapping[str, object] | None,
) -> tuple[SecIncidentTarget | None, int]:
    if not targets:
        return None, 0
    value = 0 if payload is None else payload.get("target_index", 0)
    if not isinstance(value, int) or value < 0:
        raise _invalid_checkpoint()
    index = value % len(targets)
    return targets[index], 0 if index + 1 >= len(targets) else index + 1


def _invalid_checkpoint() -> AdapterExecutionError:
    return AdapterExecutionError(
        "invalid SEC incident checkpoint",
        error_code="invalid_checkpoint",
        retryable=False,
    )


def _empty_batch() -> AdapterCollectionBatch:
    return AdapterCollectionBatch(
        observations=(),
        incident_claims=(),
        checkpoint_payload={"target_index": 0, "last_accession_by_target": {}},
        not_modified=True,
    )
