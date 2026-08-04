from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from uuid import UUID

from pydantic import ValidationError

from cip.adapters.sources.organization_identity.registry import OrganizationIdentityTarget
from cip.adapters.sources.recherche_entreprises.client import RechercheEntreprisesClient
from cip.adapters.sources.recherche_entreprises.mapper import (
    RechercheMappedResult,
    map_recherche_entreprise,
)
from cip.adapters.sources.recherche_entreprises.schemas import RechercheEntreprisesResponse
from cip.modules.organizations.application.identity import IdentityProjection
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    SourceRuntimeState,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc


class RechercheEntreprisesCollectionDeniedError(RuntimeError):
    pass


class RechercheEntreprisesSourceSchemaError(RuntimeError):
    pass


class RechercheEntreprisesSourceWindowError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RechercheEntreprisesCheckpoint:
    fingerprints: Mapping[str, Mapping[str, str]]

    def __post_init__(self) -> None:
        copied = {
            target_id: MappingProxyType(dict(values))
            for target_id, values in self.fingerprints.items()
        }
        object.__setattr__(self, "fingerprints", MappingProxyType(copied))


@dataclass(frozen=True, slots=True)
class RechercheEntreprisesCollectionBatch:
    observations: tuple[RawObservation, ...]
    projections: tuple[IdentityProjection, ...]
    checkpoint: RechercheEntreprisesCheckpoint
    not_modified: bool


def collect_recherche_entreprises(
    client: RechercheEntreprisesClient,
    entry: SourceRegistryEntry,
    targets: tuple[OrganizationIdentityTarget, ...],
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: RechercheEntreprisesCheckpoint | None = None,
) -> RechercheEntreprisesCollectionBatch:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    enabled_targets = tuple(target for target in targets if target.enabled and target.country_code == "FR")
    if not enabled_targets:
        raise ValueError("at least one French organization identity target must be enabled")
    previous = checkpoint.fingerprints if checkpoint else {}
    current: dict[str, dict[str, str]] = {}
    observations: list[RawObservation] = []
    projections: list[IdentityProjection] = []
    for target in enabled_targets:
        _authorize(entry, client.search_url, collected_at=collected)
        fetched = client.search(target.query, page=1, per_page=25)
        response = _parse_response(fetched.body)
        if response.total_pages > 1 or response.total_results > 25:
            raise RechercheEntreprisesSourceWindowError(
                f"target {target.id} returned an ambiguous result window"
            )
        target_fingerprints: dict[str, str] = {}
        for result in response.results:
            if result.siren in target_fingerprints:
                raise RechercheEntreprisesSourceSchemaError(
                    f"duplicate SIREN for target {target.id}: {result.siren}"
                )
            mapped = map_recherche_entreprise(
                target,
                result,
                request_url=fetched.request_url,
                collection_job_id=collection_job_id,
                collected_at=collected,
                retention_until=retention_until,
            )
            if mapped is None:
                continue
            _append_mapped(
                mapped,
                previous_fingerprint=previous.get(target.id, {}).get(result.siren),
                observations=observations,
                projections=projections,
            )
            target_fingerprints[result.siren] = mapped.fingerprint
        current[target.id] = target_fingerprints
    current_checkpoint = RechercheEntreprisesCheckpoint(current)
    return RechercheEntreprisesCollectionBatch(
        observations=tuple(observations),
        projections=tuple(projections),
        checkpoint=current_checkpoint,
        not_modified=_checkpoint_equal(previous, current_checkpoint.fingerprints),
    )


def _append_mapped(
    mapped: RechercheMappedResult,
    *,
    previous_fingerprint: str | None,
    observations: list[RawObservation],
    projections: list[IdentityProjection],
) -> None:
    projections.extend(mapped.projections)
    if previous_fingerprint != mapped.fingerprint:
        observations.extend(mapped.observations)


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
        raise RechercheEntreprisesCollectionDeniedError(decision.reason.value)


def _parse_response(body: bytes) -> RechercheEntreprisesResponse:
    try:
        return RechercheEntreprisesResponse.model_validate_json(body)
    except ValidationError as exc:
        raise RechercheEntreprisesSourceSchemaError(
            "Recherche d'entreprises response schema validation failed"
        ) from exc


def _checkpoint_equal(
    previous: Mapping[str, Mapping[str, str]],
    current: Mapping[str, Mapping[str, str]],
) -> bool:
    return {
        target_id: dict(values) for target_id, values in previous.items()
    } == {target_id: dict(values) for target_id, values in current.items()}
