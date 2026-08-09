from __future__ import annotations

from collections.abc import Iterable

from cip.modules.source_activation.domain.models import ActivationAudit, ActivationRecord


def audit_inventory(records: Iterable[ActivationRecord]) -> ActivationAudit:
    ordered = tuple(records)
    _ensure_unique_source_ids(ordered)
    source_ids = {record.source_id for record in ordered}
    _ensure_references_exist(ordered, source_ids)

    integrated = tuple(record for record in ordered if record.is_fully_integrated)
    resolved = tuple(
        record for record in ordered if record.is_resolved and not record.is_fully_integrated
    )
    unresolved = tuple(
        sorted(record.source_id for record in ordered if not record.is_resolved)
    )
    return ActivationAudit(
        total=len(ordered),
        fully_integrated=len(integrated),
        resolved_non_executable=len(resolved),
        unresolved=unresolved,
    )


def _ensure_unique_source_ids(records: tuple[ActivationRecord, ...]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for record in records:
        if record.source_id in seen:
            duplicates.add(record.source_id)
        seen.add(record.source_id)
    if duplicates:
        joined = ", ".join(sorted(duplicates))
        raise ValueError(f"duplicate source activation records: {joined}")


def _ensure_references_exist(
    records: tuple[ActivationRecord, ...], source_ids: set[str]
) -> None:
    for record in records:
        for reference in (record.replacement_source_id, record.duplicate_of_source_id):
            if reference is not None and reference not in source_ids:
                raise ValueError(
                    f"{record.source_id} references unknown activation source {reference}"
                )
