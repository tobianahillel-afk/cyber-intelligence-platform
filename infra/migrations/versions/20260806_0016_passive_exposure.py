"""Create passive assets, immutable observations, and technology details.

Revision ID: 20260806_0016
Revises: 20260806_0015
Create Date: 2026-08-06
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260806_0016"
down_revision: str | Sequence[str] | None = "20260806_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "passive_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_key", sa.String(length=2_200), nullable=False),
        sa.Column("asset_kind", sa.String(length=80), nullable=False),
        sa.Column("asset_value", sa.String(length=2_048), nullable=False),
        sa.Column("state", sa.String(length=80), nullable=False),
        sa.Column("observed_states", sa.String(length=1_000), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("independent_source_count", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("historical_only", sa.Boolean(), nullable=False),
        sa.Column("has_conflict", sa.Boolean(), nullable=False),
        sa.Column("organization_link_status", sa.String(length=80), nullable=False),
        sa.Column("exact_organization_id", sa.Uuid(), nullable=True),
        sa.Column("candidate_organization_ids", sa.Text(), nullable=False),
        sa.Column("organization_link_reasons", sa.Text(), nullable=False),
        sa.Column("attribution_risks", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["exact_organization_id"], ["organizations.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_key"),
    )
    _create_indexes(
        "passive_assets",
        (
            "asset_key",
            "asset_kind",
            "asset_value",
            "state",
            "first_seen_at",
            "last_seen_at",
            "expires_at",
            "last_updated_at",
            "active",
            "historical_only",
            "has_conflict",
            "organization_link_status",
            "exact_organization_id",
            "updated_at",
        ),
    )
    op.create_table(
        "passive_observation_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_key", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=200), nullable=False),
        sa.Column("source_record_key", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.String(length=2_048), nullable=False),
        sa.Column("asset_kind", sa.String(length=80), nullable=False),
        sa.Column("asset_value", sa.String(length=2_048), nullable=False),
        sa.Column("observation_kind", sa.String(length=80), nullable=False),
        sa.Column("state", sa.String(length=80), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("independence_key", sa.String(length=500), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("organization_link_status", sa.String(length=80), nullable=False),
        sa.Column("organization_link_method", sa.String(length=80), nullable=False),
        sa.Column("organization_link_confidence", sa.Float(), nullable=False),
        sa.Column("organization_link_reasons", sa.Text(), nullable=False),
        sa.Column("attribution_risks", sa.Text(), nullable=False),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("protocol", sa.String(length=32), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("historical_only", sa.Boolean(), nullable=False),
        sa.Column("metadata_only", sa.Boolean(), nullable=False),
        sa.Column("passive_only", sa.Boolean(), nullable=False),
        sa.Column("active_probe_performed", sa.Boolean(), nullable=False),
        sa.Column("credentials_used", sa.Boolean(), nullable=False),
        sa.Column("access_control_bypassed", sa.Boolean(), nullable=False),
        sa.Column("exploit_attempted", sa.Boolean(), nullable=False),
        sa.Column("direct_validation_performed", sa.Boolean(), nullable=False),
        sa.Column(
            "vulnerability_applicability_assessed", sa.Boolean(), nullable=False
        ),
        sa.Column("exposure_verified", sa.Boolean(), nullable=False),
        sa.Column("supersedes_record_key", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["passive_assets.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_key", name="uq_passive_observation_snapshot"
        ),
    )
    _create_indexes(
        "passive_observation_snapshots",
        (
            "asset_id",
            "source_id",
            "source_record_key",
            "asset_kind",
            "asset_value",
            "observation_kind",
            "state",
            "observed_at",
            "published_at",
            "modified_at",
            "expires_at",
            "independence_key",
            "organization_id",
            "organization_link_status",
            "organization_link_method",
            "port",
            "protocol",
            "active",
            "historical_only",
            "supersedes_record_key",
        ),
    )
    op.create_index(
        "ix_passive_observation_source_record",
        "passive_observation_snapshots",
        ["source_id", "source_record_key"],
    )
    op.create_table(
        "passive_technologies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("technology_key", sa.String(length=64), nullable=False),
        sa.Column("evidence_level", sa.String(length=80), nullable=False),
        sa.Column("product_name", sa.String(length=300), nullable=True),
        sa.Column("product_version", sa.String(length=200), nullable=True),
        sa.Column("component_name", sa.String(length=300), nullable=True),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["passive_observation_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("technology_key", name="uq_passive_technology"),
    )
    _create_indexes(
        "passive_technologies",
        (
            "snapshot_id",
            "evidence_level",
            "product_name",
            "product_version",
            "component_name",
        ),
    )


def downgrade() -> None:
    _drop_indexes(
        "passive_technologies",
        (
            "component_name",
            "product_version",
            "product_name",
            "evidence_level",
            "snapshot_id",
        ),
    )
    op.drop_table("passive_technologies")
    op.drop_index(
        "ix_passive_observation_source_record",
        table_name="passive_observation_snapshots",
    )
    _drop_indexes(
        "passive_observation_snapshots",
        (
            "supersedes_record_key",
            "historical_only",
            "active",
            "protocol",
            "port",
            "organization_link_method",
            "organization_link_status",
            "organization_id",
            "independence_key",
            "expires_at",
            "modified_at",
            "published_at",
            "observed_at",
            "state",
            "observation_kind",
            "asset_value",
            "asset_kind",
            "source_record_key",
            "source_id",
            "asset_id",
        ),
    )
    op.drop_table("passive_observation_snapshots")
    _drop_indexes(
        "passive_assets",
        (
            "updated_at",
            "exact_organization_id",
            "organization_link_status",
            "has_conflict",
            "historical_only",
            "active",
            "last_updated_at",
            "expires_at",
            "last_seen_at",
            "first_seen_at",
            "state",
            "asset_value",
            "asset_kind",
            "asset_key",
        ),
    )
    op.drop_table("passive_assets")


def _create_indexes(table_name: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(f"ix_{table_name}_{column}", table_name, [column])


def _drop_indexes(table_name: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.drop_index(f"ix_{table_name}_{column}", table_name=table_name)
