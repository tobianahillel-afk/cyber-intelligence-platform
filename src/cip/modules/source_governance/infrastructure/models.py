from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class SourceRecord(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    base_url: Mapped[str] = mapped_column(String(2_048))
    status: Mapped[str] = mapped_column(String(32), index=True)
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    owner: Mapped[str] = mapped_column(String(200))
    terms_url: Mapped[str | None] = mapped_column(String(2_048), nullable=True)
    licence: Mapped[str | None] = mapped_column(String(200), nullable=True)
    allowed_data_categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    prohibited_data_categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    rate_limit_per_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attribution_required: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_content_storage: Mapped[bool] = mapped_column(Boolean, default=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True)
    authorization_status: Mapped[str] = mapped_column(String(32), default="missing", index=True)
    authorization_document_reference: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    authorization_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    authorization_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    approved_hosts: Mapped[list[str]] = mapped_column(JSON, default=list)
    approved_path_prefixes: Mapped[list[str]] = mapped_column(JSON, default=list)
    approved_purposes: Mapped[list[str]] = mapped_column(JSON, default=list)
    automated_collection_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_storage_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
