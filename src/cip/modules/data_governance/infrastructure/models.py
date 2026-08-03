from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class SuppressionRecord(Base):
    __tablename__ = "suppressions"
    __table_args__ = (
        UniqueConstraint(
            "subject_hash",
            "channel",
            name="uq_suppression_subject_channel",
        ),
        Index("ix_suppressions_active_lookup", "subject_hash", "channel", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    subject_hash: Mapped[str] = mapped_column(String(64), index=True)
    channel: Mapped[str] = mapped_column(String(32), index=True)
    reason: Mapped[str] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
