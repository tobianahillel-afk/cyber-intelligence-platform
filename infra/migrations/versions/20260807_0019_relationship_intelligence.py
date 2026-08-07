"""Create temporal business relationship intelligence projections.

Revision ID: 20260807_0019
Revises: 20260807_0018
Create Date: 2026-08-07
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260807_0019"
down_revision: str | Sequence[str] | None = "20260807_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _create_relationships()
    _create_evidence_snapshots()
    _create_contexts()


def downgrade() -> None:
    _drop_indexes("relationship_contexts", _context_indexes())
    op.drop_table("relationship_contexts")
    _drop_indexes("relationship_evidence_snapshots", _evidence_indexes())
    op.drop_table("relationship_evidence_snapshots")
    _drop_indexes("business_relationships", _relationship_indexes())
    op.drop_table("business_relationships")


def _create_relationships() -> None:
    op.create_table(
        "business_relationships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("relationship_key", sa.String(length=500), nullable=False),
        sa.Column("role", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("source_organization_id", sa.Uuid(), nullable=True),
        sa.Column("target_organization_id", sa.Uuid(), nullable=True),
        sa.Column("source_link_status", sa.String(length=80), nullable=False),
        sa.Column("target_link_status", sa.String(length=80), nullable=False),
        sa.Column("source_name", sa.String(length=500), nullable=True),
        sa.Column("target_name", sa.String(length=500), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("independent_source_count", sa.Integer(), nullable=False),
        sa.Column("strongest_evidence_class", sa.String(length=40), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("has_contract_evidence", sa.Boolean(), nullable=False),
        sa.Column("contract_backed_current", sa.Boolean(), nullable=False),
        sa.Column("next_renewal_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("has_role_conflict", sa.Boolean(), nullable=False),
        sa.Column("has_dispute", sa.Boolean(), nullable=False),
        sa.Column("has_correction", sa.Boolean(), nullable=False),
        sa.Column("has_retraction", sa.Boolean(), nullable=False),
        sa.Column("historical_only", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_organization_id"], ["organizations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["target_organization_id"], ["organizations.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("relationship_key"),
    )
    _create_indexes("business_relationships", _relationship_indexes())


def _create_evidence_snapshots() -> None:
    op.create_table(
        "relationship_evidence_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("relationship_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_key", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=200), nullable=False),
        sa.Column("source_kind", sa.String(length=80), nullable=False),
        sa.Column("source_record_key", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.String(length=2_048), nullable=False),
        sa.Column("relationship_key", sa.String(length=500), nullable=False),
        sa.Column("claim_type", sa.String(length=80), nullable=False),
        sa.Column("role", sa.String(length=80), nullable=False),
        sa.Column("evidence_class", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=1_000), nullable=False),
        sa.Column("excerpt", sa.String(length=500), nullable=False),
        sa.Column("claimed_source_organization_name", sa.String(length=500), nullable=True),
        sa.Column("claimed_target_organization_name", sa.String(length=500), nullable=True),
        sa.Column("source_organization_id", sa.Uuid(), nullable=True),
        sa.Column("target_organization_id", sa.Uuid(), nullable=True),
        sa.Column("source_link_status", sa.String(length=80), nullable=False),
        sa.Column("target_link_status", sa.String(length=80), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contract_reference", sa.String(length=500), nullable=True),
        sa.Column("product_context", sa.String(length=500), nullable=True),
        sa.Column("service_context", sa.String(length=500), nullable=True),
        sa.Column("renewal_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("independence_key", sa.String(length=500), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("historical_only", sa.Boolean(), nullable=False),
        sa.Column("metadata_only", sa.Boolean(), nullable=False),
        sa.Column("supersedes_record_key", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["relationship_id"], ["business_relationships.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_organization_id"], ["organizations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["target_organization_id"], ["organizations.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_key", name="uq_relationship_evidence_snapshot"),
    )
    _create_indexes("relationship_evidence_snapshots", _evidence_indexes())


def _create_contexts() -> None:
    op.create_table(
        "relationship_contexts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("relationship_id", sa.Uuid(), nullable=False),
        sa.Column("context_type", sa.String(length=40), nullable=False),
        sa.Column("value", sa.String(length=500), nullable=False),
        sa.Column("reference", sa.String(length=500), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["relationship_id"], ["business_relationships.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "relationship_id",
            "context_type",
            "value",
            name="uq_relationship_context_value",
        ),
    )
    _create_indexes("relationship_contexts", _context_indexes())


def _relationship_indexes() -> tuple[str, ...]:
    return (
        "relationship_key",
        "role",
        "status",
        "source_organization_id",
        "target_organization_id",
        "source_link_status",
        "target_link_status",
        "source_name",
        "target_name",
        "valid_from",
        "valid_until",
        "first_published_at",
        "last_updated_at",
        "last_observed_at",
        "strongest_evidence_class",
        "has_contract_evidence",
        "contract_backed_current",
        "next_renewal_at",
        "has_role_conflict",
        "has_dispute",
        "has_correction",
        "has_retraction",
        "historical_only",
        "updated_at",
    )


def _evidence_indexes() -> tuple[str, ...]:
    return (
        "relationship_id",
        "source_id",
        "source_kind",
        "source_record_key",
        "relationship_key",
        "claim_type",
        "role",
        "evidence_class",
        "claimed_source_organization_name",
        "claimed_target_organization_name",
        "source_organization_id",
        "target_organization_id",
        "source_link_status",
        "target_link_status",
        "published_at",
        "modified_at",
        "observed_at",
        "valid_from",
        "valid_until",
        "expires_at",
        "renewal_at",
        "independence_key",
        "active",
        "historical_only",
        "supersedes_record_key",
    )


def _context_indexes() -> tuple[str, ...]:
    return ("relationship_id", "context_type", "value")


def _index_name(table_name: str, column: str) -> str:
    prefixes = {
        "business_relationships": "biz_rel",
        "relationship_evidence_snapshots": "rel_ev",
        "relationship_contexts": "rel_ctx",
    }
    return f"ix_{prefixes[table_name]}_{column}"


def _create_indexes(table_name: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(_index_name(table_name, column), table_name, [column])


def _drop_indexes(table_name: str, columns: tuple[str, ...]) -> None:
    for column in reversed(columns):
        op.drop_index(_index_name(table_name, column), table_name=table_name)
