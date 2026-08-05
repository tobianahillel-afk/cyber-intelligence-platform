"""Create procurement history, contract, party, and service classification tables.

Revision ID: 20260805_0010
Revises: 20260805_0009
Create Date: 2026-08-05
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260805_0010"
down_revision: str | Sequence[str] | None = "20260805_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "procurement_procedures",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("canonical_key", sa.String(length=300), nullable=False),
        sa.Column("buyer_organization_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=4_000), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("first_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["buyer_organization_id"],
            ["organizations.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_key"),
    )
    _procedure_indexes()

    op.create_table(
        "procurement_publications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("procedure_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=True),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("source_record_key", sa.String(length=300), nullable=False),
        sa.Column("revision_key", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("procedure_status", sa.String(length=40), nullable=False),
        sa.Column("source_url", sa.String(length=2_048), nullable=False),
        sa.Column("content_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=4_000), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["procedure_id"],
            ["procurement_procedures.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "revision_key",
            name="uq_procurement_publication_revision",
        ),
    )
    _publication_indexes()

    op.create_table(
        "procurement_contracts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("contract_key", sa.String(length=300), nullable=False),
        sa.Column("procedure_id", sa.Uuid(), nullable=False),
        sa.Column("buyer_organization_id", sa.Uuid(), nullable=False),
        sa.Column("latest_publication_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=4_000), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("amount_value", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("amount_upper_value", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("amount_type", sa.String(length=40), nullable=True),
        sa.Column("award_date", sa.Date(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("start_date_basis", sa.String(length=40), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("end_date_basis", sa.String(length=40), nullable=False),
        sa.Column("renewal_date", sa.Date(), nullable=True),
        sa.Column("renewal_date_basis", sa.String(length=40), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["procedure_id"],
            ["procurement_procedures.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["buyer_organization_id"],
            ["organizations.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["latest_publication_id"],
            ["procurement_publications.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contract_key"),
    )
    _contract_indexes()

    op.create_table(
        "procurement_contract_parties",
        sa.Column("contract_id", sa.Uuid(), nullable=False),
        sa.Column("party_key", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("published_name", sa.String(length=500), nullable=False),
        sa.Column("resolution_status", sa.String(length=40), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("official_identifier", sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["procurement_contracts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("contract_id", "party_key"),
    )
    op.create_index(
        "ix_procurement_contract_parties_role",
        "procurement_contract_parties",
        ["role"],
    )
    op.create_index(
        "ix_procurement_contract_parties_organization_id",
        "procurement_contract_parties",
        ["organization_id"],
    )
    op.create_index(
        "ix_procurement_contract_parties_published_name",
        "procurement_contract_parties",
        ["published_name"],
    )
    op.create_index(
        "ix_procurement_contract_parties_resolution_status",
        "procurement_contract_parties",
        ["resolution_status"],
    )

    op.create_table(
        "procurement_service_classifications",
        sa.Column("contract_id", sa.Uuid(), nullable=False),
        sa.Column("family", sa.String(length=100), nullable=False),
        sa.Column("matched_terms", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["procurement_contracts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("contract_id", "family"),
    )


def downgrade() -> None:
    op.drop_table("procurement_service_classifications")
    op.drop_index(
        "ix_procurement_contract_parties_resolution_status",
        table_name="procurement_contract_parties",
    )
    op.drop_index(
        "ix_procurement_contract_parties_published_name",
        table_name="procurement_contract_parties",
    )
    op.drop_index(
        "ix_procurement_contract_parties_organization_id",
        table_name="procurement_contract_parties",
    )
    op.drop_index(
        "ix_procurement_contract_parties_role",
        table_name="procurement_contract_parties",
    )
    op.drop_table("procurement_contract_parties")
    _drop_contract_indexes()
    op.drop_table("procurement_contracts")
    _drop_publication_indexes()
    op.drop_table("procurement_publications")
    _drop_procedure_indexes()
    op.drop_table("procurement_procedures")


def _procedure_indexes() -> None:
    for name, columns in (
        ("ix_procurement_procedures_canonical_key", ["canonical_key"]),
        ("ix_procurement_procedures_buyer_organization_id", ["buyer_organization_id"]),
        ("ix_procurement_procedures_status", ["status"]),
        ("ix_procurement_procedures_first_published_at", ["first_published_at"]),
        ("ix_procurement_procedures_latest_published_at", ["latest_published_at"]),
        ("ix_procurement_procedures_updated_at", ["updated_at"]),
    ):
        op.create_index(name, "procurement_procedures", columns)


def _publication_indexes() -> None:
    indexes = (
        ("ix_procurement_publications_procedure_id", ["procedure_id"]),
        ("ix_procurement_publications_evidence_id", ["evidence_id"]),
        ("ix_procurement_publications_source_id", ["source_id"]),
        ("ix_procurement_publications_source_record_key", ["source_record_key"]),
        ("ix_procurement_publications_kind", ["kind"]),
        ("ix_procurement_publications_procedure_status", ["procedure_status"]),
        ("ix_procurement_publications_published_at", ["published_at"]),
        ("ix_procurement_publications_collected_at", ["collected_at"]),
        (
            "ix_procurement_publication_source_record",
            ["source_id", "source_record_key"],
        ),
        (
            "ix_procurement_publication_procedure_time",
            ["procedure_id", "published_at"],
        ),
    )
    for name, columns in indexes:
        op.create_index(name, "procurement_publications", columns)


def _contract_indexes() -> None:
    for name, columns in (
        ("ix_procurement_contracts_contract_key", ["contract_key"]),
        ("ix_procurement_contracts_procedure_id", ["procedure_id"]),
        ("ix_procurement_contracts_buyer_organization_id", ["buyer_organization_id"]),
        ("ix_procurement_contracts_latest_publication_id", ["latest_publication_id"]),
        ("ix_procurement_contracts_status", ["status"]),
        ("ix_procurement_contracts_currency", ["currency"]),
        ("ix_procurement_contracts_award_date", ["award_date"]),
        ("ix_procurement_contracts_start_date", ["start_date"]),
        ("ix_procurement_contracts_end_date", ["end_date"]),
        ("ix_procurement_contracts_renewal_date", ["renewal_date"]),
        ("ix_procurement_contracts_renewal_date_basis", ["renewal_date_basis"]),
        ("ix_procurement_contracts_updated_at", ["updated_at"]),
    ):
        op.create_index(name, "procurement_contracts", columns)


def _drop_contract_indexes() -> None:
    for name in (
        "ix_procurement_contracts_updated_at",
        "ix_procurement_contracts_renewal_date_basis",
        "ix_procurement_contracts_renewal_date",
        "ix_procurement_contracts_end_date",
        "ix_procurement_contracts_start_date",
        "ix_procurement_contracts_award_date",
        "ix_procurement_contracts_currency",
        "ix_procurement_contracts_status",
        "ix_procurement_contracts_latest_publication_id",
        "ix_procurement_contracts_buyer_organization_id",
        "ix_procurement_contracts_procedure_id",
        "ix_procurement_contracts_contract_key",
    ):
        op.drop_index(name, table_name="procurement_contracts")


def _drop_publication_indexes() -> None:
    for name in (
        "ix_procurement_publication_procedure_time",
        "ix_procurement_publication_source_record",
        "ix_procurement_publications_collected_at",
        "ix_procurement_publications_published_at",
        "ix_procurement_publications_procedure_status",
        "ix_procurement_publications_kind",
        "ix_procurement_publications_source_record_key",
        "ix_procurement_publications_source_id",
        "ix_procurement_publications_evidence_id",
        "ix_procurement_publications_procedure_id",
    ):
        op.drop_index(name, table_name="procurement_publications")


def _drop_procedure_indexes() -> None:
    for name in (
        "ix_procurement_procedures_updated_at",
        "ix_procurement_procedures_latest_published_at",
        "ix_procurement_procedures_first_published_at",
        "ix_procurement_procedures_status",
        "ix_procurement_procedures_buyer_organization_id",
        "ix_procurement_procedures_canonical_key",
    ):
        op.drop_index(name, table_name="procurement_procedures")
