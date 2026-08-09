from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class ProfessionalDeletionAuditRecord(Base):
    __tablename__ = "professional_deletion_audit"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    person_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("professional_people.id", ondelete="SET NULL"), nullable=True, index=True
    )
    subject_hash: Mapped[str] = mapped_column(String(64), index=True)
    channel: Mapped[str] = mapped_column(String(40), index=True)
    reason: Mapped[str] = mapped_column(String(40), index=True)
    source: Mapped[str] = mapped_column(String(200))
    actor: Mapped[str] = mapped_column(String(200))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    suppression_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
