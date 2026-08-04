from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base
from cip.shared.persistence.types import UTCDateTime


class EvidenceRecord(Base):
    __tablename__ = "evidence"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(String(64), index=True)
    source_record_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_url: Mapped[str] = mapped_column(String(2_048))
    summary: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    collected_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    content_hash_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    raw_storage_uri: Mapped[str | None] = mapped_column(String(2_048), nullable=True)
    raw_storage_permitted: Mapped[bool] = mapped_column(Boolean, default=False)
    retention_until: Mapped[datetime | None] = mapped_column(
        UTCDateTime(),
        nullable=True,
        index=True,
    )
