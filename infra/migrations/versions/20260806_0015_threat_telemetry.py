"""Create canonical threat indicators, immutable snapshots, and relations.

Revision ID: 20260806_0015
Revises: 20260806_0014
Create Date: 2026-08-06
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260806_0015"
down_revision: str | Sequence[str] | None = "20260806_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "threat_indicators",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("indicator_key", sa.String(length=2_200), nullable=False),
        sa.Column("indicator_type", sa.String(length=80), nullable=False),
        sa.Column("indicator_value", sa.String(length=2_048), nullable=False),
        sa.Column("state", sa.String(length=80), nullable=False),
        sa.Column("observed_states", sa.String(length=1_000), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("independent_source_count", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("shared_infrastructure", sa.Boolean(), nullable=False),
        sa.Column("historical_only", sa.Boolean(), nullable=False),
        sa.Column("has_conflict", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("indicator_key"),
    )
    _create_indexes(
        "threat_indicators",
        (
            "indicator_key",
            "indicator_type",
            "indicator_value",
            "state",
            "first_seen_at",
            "last_seen_at",
            "expires_at",
            "last_updated_at",
            "active",
            "shared_infrastructure",
            "historical_only",
            "has_conflict",
            "updated_at",
        ),
    )
    op.create_table(
        "threat_indicator_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("indicator_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_key", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=200), nullable=False),
        sa.Column("source_kind", sa.String(length=80), nullable=False),
        sa.Column("source_record_key", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.String(length=2_048), nullable=False),
        sa.Column("indicator_type", sa.String(length=80), nullable=False),
        sa.Column("indicator_value", sa.String(length=2_048), nullable=False),
        sa.Column("state", sa.String(length=80), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("independence_key", sa.String(length=500), nullable=False),
        sa.Column("sensor_scope", sa.String(length=80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source_precedence", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("shared_infrastructure", sa.Boolean(), nullable=False),
        sa.Column("historical_only", sa.Boolean(), nullable=False),
        sa.Column("metadata_only", sa.Boolean(), nullable=False),
        sa.Column("binary_payload_present", sa.Boolean(), nullable=False),
        sa.Column("direct_validation_performed", sa.Boolean(), nullable=False),
        sa.Column("supersedes_record_key", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["indicator_id"], ["threat_indicators.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_key", name="uq_threat_indicator_snapshot"),
    )
    _create_indexes(
        "threat_indicator_snapshots",
        (
            "indicator_id",
            "source_id",
            "source_kind",
            "source_record_key",
            "indicator_type",
            "indicator_value",
            "state",
            "published_at",
            "modified_at",
            "first_seen_at",
            "last_seen_at",
            "expires_at",
            "independence_key",
            "sensor_scope",
            "active",
            "shared_infrastructure",
            "historical_only",
            "supersedes_record_key",
        ),
    )
    op.create_index(
        "ix_threat_indicator_snapshot_source_record",
        "threat_indicator_snapshots",
        ["source_id", "source_record_key"],
    )
    op.create_table(
        "threat_indicator_relations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("relation_key", sa.String(length=64), nullable=False),
        sa.Column("relation_type", sa.String(length=80), nullable=False),
        sa.Column("target_key", sa.String(length=500), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["threat_indicator_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("relation_key", name="uq_threat_indicator_relation"),
    )
    _create_indexes(
        "threat_indicator_relations",
        ("snapshot_id", "relation_type", "target_key"),
    )


def downgrade() -> None:
    _drop_indexes(
        "threat_indicator_relations",
        ("target_key", "relation_type", "snapshot_id"),
    )
    op.drop_table("threat_indicator_relations")
    op.drop_index(
        "ix_threat_indicator_snapshot_source_record",
        table_name="threat_indicator_snapshots",
    )
    _drop_indexes(
        "threat_indicator_snapshots",
        (
            "supersedes_record_key",
            "historical_only",
            "shared_infrastructure",
            "active",
            "sensor_scope",
            "independence_key",
            "expires_at",
            "last_seen_at",
            "first_seen_at",
            "modified_at",
            "published_at",
            "state",
            "indicator_value",
            "indicator_type",
            "source_record_key",
            "source_kind",
            "source_id",
            "indicator_id",
        ),
    )
    op.drop_table("threat_indicator_snapshots")
    _drop_indexes(
        "threat_indicators",
        (
            "updated_at",
            "has_conflict",
            "historical_only",
            "shared_infrastructure",
            "active",
            "last_updated_at",
            "expires_at",
            "last_seen_at",
            "first_seen_at",
            "state",
            "indicator_value",
            "indicator_type",
            "indicator_key",
        ),
    )
    op.drop_table("threat_indicators")


def _create_indexes(table_name: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(f"ix_{table_name}_{column}", table_name, [column])


def _drop_indexes(table_name: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.drop_index(f"ix_{table_name}_{column}", table_name=table_name)
