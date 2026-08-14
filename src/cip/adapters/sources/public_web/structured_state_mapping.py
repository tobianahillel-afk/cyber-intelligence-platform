from __future__ import annotations

from uuid import UUID

from cip.adapters.sources.public_web.client import PublicWebFetchResult
from cip.adapters.sources.public_web.structured_fetch_result import structured_states_for_result
from cip.modules.public_footprint.domain.structured_state import PublicStructuredState


def map_structured_states(
    result: PublicWebFetchResult,
    *,
    organization_id: UUID,
    resource_version_id: UUID,
) -> tuple[PublicStructuredState, ...]:
    records: list[PublicStructuredState] = []
    for captured in structured_states_for_result(result):
        records.append(
            PublicStructuredState(
                organization_id=organization_id,
                resource_version_id=resource_version_id,
                kind=captured.kind,
                page_url=result.fetched_url,
                source_locator=captured.source_locator,
                payload_json=captured.payload_json,
                source_url=captured.source_url,
                http_status=captured.http_status,
                media_type=captured.media_type,
                extractor_id=captured.extractor_id,
            )
        )
    return tuple(records)
