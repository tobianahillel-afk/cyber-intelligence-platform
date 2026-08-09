from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from cip.modules.conditional_integrations.domain.enums import ProviderControlAction
from cip.shared.kernel.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class ProviderRuntimeControl:
    source_id: str
    paused: bool
    kill_switch_active: bool
    paused_reason: str | None
    updated_at: datetime

    def __post_init__(self) -> None:
        source_id = self.source_id.strip()
        if not source_id:
            raise ValueError("source_id is required")
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(
            self,
            "updated_at",
            require_aware_utc(self.updated_at, field_name="updated_at"),
        )
        reason = self.paused_reason.strip() if self.paused_reason else None
        if self.paused and not reason:
            raise ValueError("paused control requires paused_reason")
        if not self.paused:
            reason = None
        object.__setattr__(self, "paused_reason", reason)


@dataclass(frozen=True, slots=True)
class ProviderControlDecision:
    source_id: str
    action: ProviderControlAction
    actor: str
    reason: str
    decided_at: datetime

    def __post_init__(self) -> None:
        for field_name in ("source_id", "actor", "reason"):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} is required")
            if len(value) > 1000:
                raise ValueError(f"{field_name} cannot exceed 1000 characters")
            object.__setattr__(self, field_name, value)
        object.__setattr__(
            self,
            "decided_at",
            require_aware_utc(self.decided_at, field_name="decided_at"),
        )


def apply_control_decision(
    current: ProviderRuntimeControl,
    decision: ProviderControlDecision,
) -> ProviderRuntimeControl:
    if current.source_id != decision.source_id:
        raise ValueError("control decision source_id must match current state")
    if decision.decided_at < current.updated_at:
        raise ValueError("control decision cannot predate current state")
    if decision.action is ProviderControlAction.PAUSE:
        return replace(
            current,
            paused=True,
            paused_reason=decision.reason,
            updated_at=decision.decided_at,
        )
    if decision.action is ProviderControlAction.RESUME:
        return replace(
            current,
            paused=False,
            paused_reason=None,
            updated_at=decision.decided_at,
        )
    if decision.action is ProviderControlAction.ACTIVATE_KILL_SWITCH:
        return replace(
            current,
            kill_switch_active=True,
            updated_at=decision.decided_at,
        )
    return replace(
        current,
        kill_switch_active=False,
        updated_at=decision.decided_at,
    )
