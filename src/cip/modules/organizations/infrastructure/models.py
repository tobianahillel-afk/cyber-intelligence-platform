from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class OrganizationRecord(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(300), index=True)
    legal_name: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    website_url: Mapped[str | None] = mapped_column(String(2_048), nullable=True)
    registration_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
