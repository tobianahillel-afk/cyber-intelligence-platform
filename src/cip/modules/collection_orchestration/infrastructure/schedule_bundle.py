from __future__ import annotations

from pathlib import Path

from cip.modules.collection_orchestration.domain.models import SourceSchedule
from cip.modules.collection_orchestration.infrastructure.schedule_loader import (
    load_collection_schedules,
)


def load_collection_schedule_bundle(*paths: Path) -> tuple[SourceSchedule, ...]:
    schedules: list[SourceSchedule] = []
    identities: set[tuple[str, str]] = set()
    for path in paths:
        for schedule in load_collection_schedules(path):
            identity = (schedule.source_id, schedule.adapter_id)
            if identity in identities:
                raise ValueError(
                    "duplicate collection schedule across registries: "
                    f"{identity[0]}/{identity[1]}"
                )
            identities.add(identity)
            schedules.append(schedule)
    return tuple(schedules)
