from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ActivationDisposition(StrEnum):
    ACTIVE = "active"
    PLANNED = "planned"
    MANUAL = "manual"
    BLOCKED = "blocked"
    REPLACED = "replaced"
    DUPLICATE = "duplicate"
    NOT_RELEVANT = "not_relevant"


class ActivationStage(StrEnum):
    CATALOGUED = "catalogued"
    REVIEWED = "reviewed"
    MAPPED = "mapped"
    ADAPTER_PRESENT = "adapter_present"
    AUTHORIZED = "authorized"
    EXECUTABLE = "executable"
    SCHEDULED = "scheduled"
    LIVE_TESTED = "live_tested"


_TERMINAL_NON_EXECUTABLE = {
    ActivationDisposition.MANUAL,
    ActivationDisposition.BLOCKED,
    ActivationDisposition.REPLACED,
    ActivationDisposition.DUPLICATE,
    ActivationDisposition.NOT_RELEVANT,
}


@dataclass(frozen=True, slots=True)
class ActivationRecord:
    source_id: str
    display_name: str
    category: str
    disposition: ActivationDisposition
    stages: frozenset[ActivationStage]
    activation_wave: str | None = None
    requires_schedule: bool = True
    reason: str | None = None
    replacement_source_id: str | None = None
    duplicate_of_source_id: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("source_id", "display_name", "category"):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} is required")
            object.__setattr__(self, field_name, value)
        if ActivationStage.CATALOGUED not in self.stages:
            raise ValueError("every activation record must be catalogued")
        if self.disposition in _TERMINAL_NON_EXECUTABLE and not _clean(self.reason):
            raise ValueError("terminal non-executable dispositions require a reason")
        if self.disposition is ActivationDisposition.REPLACED and not _clean(
            self.replacement_source_id
        ):
            raise ValueError("replaced sources require replacement_source_id")
        if self.disposition is ActivationDisposition.DUPLICATE and not _clean(
            self.duplicate_of_source_id
        ):
            raise ValueError("duplicate sources require duplicate_of_source_id")
        self_reference = (
            self.replacement_source_id == self.source_id
            or self.duplicate_of_source_id == self.source_id
        )
        if self_reference:
            raise ValueError("a source cannot replace or duplicate itself")

    @property
    def is_fully_integrated(self) -> bool:
        required = {
            ActivationStage.CATALOGUED,
            ActivationStage.REVIEWED,
            ActivationStage.MAPPED,
            ActivationStage.ADAPTER_PRESENT,
            ActivationStage.AUTHORIZED,
            ActivationStage.EXECUTABLE,
            ActivationStage.LIVE_TESTED,
        }
        if self.requires_schedule:
            required.add(ActivationStage.SCHEDULED)
        return self.disposition is ActivationDisposition.ACTIVE and required <= self.stages

    @property
    def is_resolved(self) -> bool:
        return self.is_fully_integrated or self.disposition in _TERMINAL_NON_EXECUTABLE

    @property
    def missing_integration_stages(self) -> tuple[ActivationStage, ...]:
        required = [
            ActivationStage.REVIEWED,
            ActivationStage.MAPPED,
            ActivationStage.ADAPTER_PRESENT,
            ActivationStage.AUTHORIZED,
            ActivationStage.EXECUTABLE,
            ActivationStage.LIVE_TESTED,
        ]
        if self.requires_schedule:
            required.append(ActivationStage.SCHEDULED)
        return tuple(stage for stage in required if stage not in self.stages)


@dataclass(frozen=True, slots=True)
class ActivationAudit:
    total: int
    fully_integrated: int
    resolved_non_executable: int
    unresolved: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return (
            not self.unresolved
            and self.total == self.fully_integrated + self.resolved_non_executable
        )


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
