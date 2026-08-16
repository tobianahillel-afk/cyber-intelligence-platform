from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKeyConstraint, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class BrowserActionPlanRecord(Base):
    __tablename__ = "browser_action_plans"

    plan_id: Mapped[UUID] = mapped_column(primary_key=True)
    plan_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    provider_id: Mapped[str] = mapped_column(String(200), index=True)
    target_id: Mapped[str] = mapped_column(String(200), index=True)
    purpose: Mapped[str] = mapped_column(String(500))
    payload_hash_sha256: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BrowserActionCheckpointRecord(Base):
    __tablename__ = "browser_action_checkpoints"
    __table_args__ = (
        ForeignKeyConstraint(
            ["plan_id", "plan_version"],
            ["browser_action_plans.plan_id", "browser_action_plans.plan_version"],
            ondelete="CASCADE",
        ),
    )

    plan_id: Mapped[UUID] = mapped_column(primary_key=True)
    plan_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    step_states: Mapped[list[str]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
