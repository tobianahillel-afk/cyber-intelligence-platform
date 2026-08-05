from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class ProcurementProcedureRecord(Base):
    __tablename__ = "procurement_procedures"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    canonical_key: Mapped[str] = mapped_column(String(300), unique=True, index=True)
    buyer_organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(4_000))
    status: Mapped[str] = mapped_column(String(40), index=True)
    first_published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    latest_published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    source_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ProcurementPublicationRecord(Base):
    __tablename__ = "procurement_publications"
    __table_args__ = (
        UniqueConstraint("revision_key", name="uq_procurement_publication_revision"),
        Index(
            "ix_procurement_publication_source_record",
            "source_id",
            "source_record_key",
        ),
        Index(
            "ix_procurement_publication_procedure_time",
            "procedure_id",
            "published_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    procedure_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_procedures.id", ondelete="CASCADE"),
        index=True,
    )
    evidence_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("evidence.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_id: Mapped[str] = mapped_column(String(100), index=True)
    source_record_key: Mapped[str] = mapped_column(String(300), index=True)
    revision_key: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(40), index=True)
    procedure_status: Mapped[str] = mapped_column(String(40), index=True)
    source_url: Mapped[str] = mapped_column(String(2_048))
    content_hash_sha256: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(4_000))
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class ProcurementContractRecord(Base):
    __tablename__ = "procurement_contracts"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    contract_key: Mapped[str] = mapped_column(String(300), unique=True, index=True)
    procedure_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_procedures.id", ondelete="CASCADE"),
        index=True,
    )
    buyer_organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        index=True,
    )
    latest_publication_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_publications.id", ondelete="RESTRICT"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(4_000))
    status: Mapped[str] = mapped_column(String(40), index=True)
    amount_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    amount_upper_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True, index=True)
    amount_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    award_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    conclusion_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    conclusion_date_basis: Mapped[str] = mapped_column(String(40))
    notification_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    notification_date_basis: Mapped[str] = mapped_column(String(40))
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    start_date_basis: Mapped[str] = mapped_column(String(40))
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    end_date_basis: Mapped[str] = mapped_column(String(40))
    renewal_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    renewal_date_basis: Mapped[str] = mapped_column(String(40), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ProcurementContractPartyRecord(Base):
    __tablename__ = "procurement_contract_parties"

    contract_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_contracts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    party_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    role: Mapped[str] = mapped_column(String(40), index=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    published_name: Mapped[str] = mapped_column(String(500), index=True)
    resolution_status: Mapped[str] = mapped_column(String(40), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    official_identifier: Mapped[str | None] = mapped_column(String(200), nullable=True)


class ProcurementServiceClassificationRecord(Base):
    __tablename__ = "procurement_service_classifications"

    contract_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_contracts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    family: Mapped[str] = mapped_column(String(100), primary_key=True)
    matched_terms: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float)
