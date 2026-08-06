"""Create canonical incidents and immutable claim snapshots.

Revision ID: 20260806_0014
Revises: 20260806_0013
Create Date: 2026-08-06
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260806_0014"
down_revision: str | Sequence[str] | None = "20260806_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_key", sa.String(length=500), nullable=False),
        sa.Column("incident_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=1_000), nullable=False),
        sa.Column("summary", sa.String(length=8_000), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("organization_link_status", sa.String(length=80), nullable=False),
        sa.Column("occurrence_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("occurrence_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claim_count", sa.Integer(), nullable=False),
        sa.Column("independent_source_count", sa.Integer(), nullable=False),
        sa.Column("officially_confirmed", sa.Boolean(), nullable=False),
        sa.Column("has_denial", sa.Boolean(), nullable=False),
        sa.Column("has_retraction", sa.Boolean(), nullable=False),
        sa.Column("historical_only", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("incident_key"),
    )
    _create_indexes(
        "incidents",
        (
            "incident_key",
            "incident_type",
            "status",
            "organization_id",
            "organization_link_status",
            "occurrence_start_at",
            "occurrence_end_at",
            "discovered_at",
            "first_published_at",
            "confirmed_at",
            "last_updated_at",
            "officially_confirmed",
            "has_denial",
            "has_retraction",
            "historical_only",
            "updated_at",
        ),
    )
    op.create_table(
        "incident_claim_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_key", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=200), nullable=False),
        sa.Column("source_kind", sa.String(length=80), nullable=False),
        sa.Column("source_record_key", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.String(length=2_048), nullable=False),
        sa.Column("incident_key", sa.String(length=500), nullable=False),
        sa.Column("claim_type", sa.String(length=80), nullable=False),
        sa.Column("incident_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=1_000), nullable=False),
        sa.Column("summary", sa.String(length=8_000), nullable=False),
        sa.Column("claimed_organization_name", sa.String(length=500), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("organization_link_status", sa.String(length=80), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("occurrence_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("occurrence_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("independence_key", sa.String(length=500), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("historical_only", sa.Boolean(), nullable=False),
        sa.Column("metadata_only", sa.Boolean(), nullable=False),
        sa.Column("supersedes_record_key", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_key", name="uq_incident_claim_snapshot"),
    )
    _create_indexes(
        "incident_claim_snapshots",
        (
            "incident_id",
            "source_id",
            "source_kind",
            "source_record_key",
            "incident_key",
            "claim_type",
            "incident_type",
            "claimed_organization_name",
            "organization_id",
            "organization_link_status",
            "published_at",
            "modified_at",
            "occurrence_start_at",
            "occurrence_end_at",
            "discovered_at",
            "confirmed_at",
            "independence_key",
            "active",
            "historical_only",
            "supersedes_record_key",
        ),
    )
    op.create_index(
        "ix_incident_claim_source_record",
        "incident_claim_snapshots",
        ["source_id", "source_record_key"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_incident_claim_source_record",
        table_name="incident_claim_snapshots",
    )
    _drop_indexes(
        "incident_claim_snapshots",
        (
            "supersedes_record_key",
            "historical_only",
            "active",
            "independence_key",
            "confirmed_at",
            "discovered_at",
            "occurrence_end_at",
            "occurrence_start_at",
            "modified_at",
            "published_at",
            "organization_link_status",
            "organization_id",
            "claimed_organization_name",
            "incident_type",
            "claim_type",
            "incident_key",
            "source_record_key",
            "source_kind",
            "source_id",
            "incident_id",
        ),
    )
    op.drop_table("incident_claim_snapshots")
    _drop_indexes(
        "incidents",
        (
            "updated_at",
            "historical_only",
            "has_retraction",
            "has_denial",
            "officially_confirmed",
            "last_updated_at",
            "confirmed_at",
            "first_published_at",
            "discovered_at",
            "occurrence_end_at",
            "occurrence_start_at",
            "organization_link_status",
            "organization_id",
            "status",
            "incident_type",
            "incident_key",
        ),
    )
    op.drop_table("incidents")


def _create_indexes(table_name: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(f"ix_{table_name}_{column}", table_name, [column])


def _drop_indexes(table_name: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.drop_index(f"ix_{table_name}_{column}", table_name=table_name)
