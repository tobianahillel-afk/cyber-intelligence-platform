from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256
from types import MappingProxyType
from uuid import UUID

from pydantic import ValidationError

from cip.adapters.sources.gleif.client import GleifClient
from cip.adapters.sources.gleif.mapper import (
    GleifMappedRecord,
    build_parent_relationship,
    map_gleif_record,
    parent_lei,
)
from cip.adapters.sources.gleif.schemas import (
    GleifRecordResponse,
    GleifRelationshipResponse,
)
from cip.adapters.sources.organization_identity.registry import OrganizationIdentityTarget
from cip.modules.organizations.application.identity import IdentityProjection
from cip.modules.organizations.domain.identity import RelationshipType
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    SourceRuntimeState,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc


class GleifCollectionDeniedError(RuntimeError):
    pass


class GleifSourceSchemaError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class GleifCheckpoint:
    fingerprints: Mapping[str, Mapping[str, str]]

    def __post_init__(self) -> None:
        copied = {
            target_id: MappingProxyType(dict(values))
            for target_id, values in self.fingerprints.items()
        }
        object.__setattr__(self, "fingerprints", MappingProxyType(copied))


@dataclass(frozen=True, slots=True)
class GleifCollectionBatch:
    observations: tuple[RawObservation, ...]
    projections: tuple[IdentityProjection, ...]
    checkpoint: GleifCheckpoint
    not_modified: bool


def collect_gleif_identities(
    client: GleifClient,
    entry: SourceRegistryEntry,
    targets: tuple[OrganizationIdentityTarget, ...],
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: GleifCheckpoint | None = None,
) -> GleifCollectionBatch:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    enabled_targets = tuple(target for target in targets if target.enabled and target.lei)
    if not enabled_targets:
        raise ValueError("at least one organization identity target with LEI must be enabled")
    previous = checkpoint.fingerprints if checkpoint else {}
    current: dict[str, dict[str, str]] = {}
    observations: list[RawObservation] = []
    projections: list[IdentityProjection] = []
    for target in enabled_targets:
        assert target.lei is not None
        mapped_records, relationship_hashes = _collect_target(
            client,
            entry,
            target,
            collection_job_id=collection_job_id,
            collected_at=collected,
            retention_until=retention_until,
        )
        target_fingerprints = {
            mapped.projection.identity.source_record_key: mapped.fingerprint
            for mapped in mapped_records
        }
        target_fingerprints.update(relationship_hashes)
        current[target.id] = target_fingerprints
        previous_target = previous.get(target.id, {})
        for mapped in mapped_records:
            key = mapped.projection.identity.source_record_key
            projections.append(mapped.projection)
            if previous_target.get(key) != mapped.fingerprint:
                observations.append(mapped.observation)
    current_checkpoint = GleifCheckpoint(current)
    return GleifCollectionBatch(
        observations=tuple(observations),
        projections=tuple(projections),
        checkpoint=current_checkpoint,
        not_modified=_checkpoint_equal(previous, current_checkpoint.fingerprints),
    )


def _collect_target(
    client: GleifClient,
    entry: SourceRegistryEntry,
    target: OrganizationIdentityTarget,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> tuple[tuple[GleifMappedRecord, ...], dict[str, str]]:
    assert target.lei is not None
    main_response, main_url = _fetch_record(client, entry, target.lei, collected_at)
    main = map_gleif_record(
        main_response,
        request_url=main_url,
        collection_job_id=collection_job_id,
        collected_at=collected_at,
        retention_until=retention_until,
        target=target,
    )
    relationship_results: dict[str, tuple[GleifRelationshipResponse | None, str]] = {}
    for relationship in ("direct-parent", "ultimate-parent"):
        relationship_results[relationship] = _fetch_relationship(
            client,
            entry,
            target.lei,
            relationship,
            collected_at,
        )
    parent_leis = {
        relationship: parent_lei(response, child_lei=target.lei)
        for relationship, (response, _) in relationship_results.items()
    }
    parent_records: dict[str, GleifMappedRecord] = {}
    for lei in sorted({value for value in parent_leis.values() if value is not None}):
        response, request_url = _fetch_record(client, entry, lei, collected_at)
        parent_records[lei] = map_gleif_record(
            response,
            request_url=request_url,
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
        )
    relationships = []
    for label, parent_value in parent_leis.items():
        if parent_value is None:
            continue
        parent = parent_records[parent_value]
        relationship_type = (
            RelationshipType.DIRECT_PARENT
            if label == "direct-parent"
            else RelationshipType.ULTIMATE_PARENT
        )
        relationships.append(
            build_parent_relationship(
                main.projection.identity,
                parent.projection.identity,
                relationship_type,
                request_url=relationship_results[label][1],
                observed_at=collected_at,
            )
        )
    main = replace(
        main,
        projection=replace(main.projection, relationships=tuple(relationships)),
    )
    relationship_hashes = {
        f"relationship:{label}": _relationship_fingerprint(response)
        for label, (response, _) in relationship_results.items()
    }
    return (main, *parent_records.values()), relationship_hashes


def _fetch_record(
    client: GleifClient,
    entry: SourceRegistryEntry,
    lei: str,
    collected_at: datetime,
) -> tuple[GleifRecordResponse, str]:
    url = client.record_url(lei)
    _authorize(entry, url, collected_at=collected_at)
    fetched = client.fetch_record(lei)
    return _parse_record(fetched.body), fetched.request_url


def _fetch_relationship(
    client: GleifClient,
    entry: SourceRegistryEntry,
    lei: str,
    relationship: str,
    collected_at: datetime,
) -> tuple[GleifRelationshipResponse | None, str]:
    url = client.relationship_url(lei, relationship)
    _authorize(entry, url, collected_at=collected_at)
    fetched = client.fetch_relationship(lei, relationship)
    if fetched is None:
        return None, url
    return _parse_relationship(fetched.body), fetched.request_url


def _authorize(
    entry: SourceRegistryEntry,
    target_url: str,
    *,
    collected_at: datetime,
) -> None:
    decision = entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.ORGANIZATION_METADATA,
            target_url=target_url,
            purpose="organization-identity-resolution",
            automated=True,
            store_raw_content=False,
            human_review_completed=False,
        ),
        entry.authorization,
        SourceRuntimeState(remaining_requests=1),
        now=collected_at,
    )
    if not decision.allowed:
        raise GleifCollectionDeniedError(decision.reason.value)


def _parse_record(body: bytes) -> GleifRecordResponse:
    try:
        return GleifRecordResponse.model_validate_json(body)
    except ValidationError as exc:
        raise GleifSourceSchemaError("GLEIF record schema validation failed") from exc


def _parse_relationship(body: bytes) -> GleifRelationshipResponse:
    try:
        return GleifRelationshipResponse.model_validate_json(body)
    except ValidationError as exc:
        raise GleifSourceSchemaError("GLEIF relationship schema validation failed") from exc


def _relationship_fingerprint(response: GleifRelationshipResponse | None) -> str:
    payload = response.model_dump(mode="json", exclude_none=True) if response else None
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def _checkpoint_equal(
    previous: Mapping[str, Mapping[str, str]],
    current: Mapping[str, Mapping[str, str]],
) -> bool:
    return {
        target_id: dict(values) for target_id, values in previous.items()
    } == {target_id: dict(values) for target_id, values in current.items()}
