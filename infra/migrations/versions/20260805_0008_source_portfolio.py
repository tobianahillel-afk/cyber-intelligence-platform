"""Create source portfolio, capability, backfill, health, and audit tables.

Revision ID: 20260805_0008
Revises: 20260804_0007
Create Date: 2026-08-05
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260805_0008"
down_revision: str | Sequence[str] | None = "20260804_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "raw_observations",
        sa.Column(
            "source_record_action",
            sa.String(length=32),
            nullable=False,
            server_default="upsert",
        ),
    )
    op.add_column(
        "raw_observations",
        sa.Column("supersedes_observation_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_raw_observations_source_record_action",
        "raw_observations",
        ["source_record_action"],
    )
    op.create_index(
        "ix_raw_observations_supersedes_observation_id",
        "raw_observations",
        ["supersedes_observation_id"],
    )

    op.create_table(
        "source_portfolio",
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("canonical_url", sa.String(length=2048), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("freshness_max_age_seconds", sa.Integer(), nullable=False),
        sa.Column("commercial_use_cases", sa.JSON(), nullable=False),
        sa.Column("authorization_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("candidate_origin", sa.String(length=200), nullable=True),
        sa.Column("monthly_cost_limit", sa.Float(), nullable=True),
        sa.Column("extra_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("source_id"),
    )
    for column in (
        "category",
        "status",
        "authorization_expires_at",
        "review_due_at",
        "updated_at",
    ):
        op.create_index(f"ix_source_portfolio_{column}", "source_portfolio", [column])

    op.create_table(
        "adapter_capabilities",
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("adapter_id", sa.String(length=100), nullable=False),
        sa.Column("adapter_version", sa.String(length=50), nullable=False),
        sa.Column("provider_schema_version", sa.String(length=100), nullable=False),
        sa.Column("modes", sa.JSON(), nullable=False),
        sa.Column("canonical_output_types", sa.JSON(), nullable=False),
        sa.Column("supports_corrections", sa.Boolean(), nullable=False),
        sa.Column("supports_tombstones", sa.Boolean(), nullable=False),
        sa.Column("supports_retractions", sa.Boolean(), nullable=False),
        sa.Column("max_page_size", sa.Integer(), nullable=True),
        sa.Column("max_window_days", sa.Integer(), nullable=True),
        sa.Column("cost_per_request", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("source_id", "adapter_id"),
        sa.UniqueConstraint(
            "source_id", "adapter_id", name="uq_adapter_capability_identity"
        ),
    )

    op.create_table(
        "backfill_partitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("adapter_id", sa.String(length=100), nullable=False),
        sa.Column("partition_key", sa.String(length=300), nullable=False),
        sa.Column("lower_bound", sa.String(length=300), nullable=False),
        sa.Column("upper_bound", sa.String(length=300), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("cursor", sa.JSON(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("records_written", sa.Integer(), nullable=False),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            "adapter_id",
            "partition_key",
            name="uq_backfill_partition_identity",
        ),
    )
    op.create_index("ix_backfill_partitions_source_id", "backfill_partitions", ["source_id"])
    op.create_index("ix_backfill_partitions_adapter_id", "backfill_partitions", ["adapter_id"])
    op.create_index("ix_backfill_partitions_state", "backfill_partitions", ["state"])
    op.create_index("ix_backfill_partitions_updated_at", "backfill_partitions", ["updated_at"])
    op.create_index(
        "ix_backfill_partition_claim",
        "backfill_partitions",
        ["state", "source_id", "created_at"],
    )

    op.create_table(
        "source_health",
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("freshness_state", sa.String(length=50), nullable=False),
        sa.Column("schema_state", sa.String(length=40), nullable=False),
        sa.Column("volume_state", sa.String(length=40), nullable=False),
        sa.Column("field_population_state", sa.String(length=40), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_source_record_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("quota_remaining", sa.Integer(), nullable=True),
        sa.Column("monthly_cost_used", sa.Float(), nullable=False),
        sa.Column("cost_window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_backfill_state", sa.String(length=40), nullable=True),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("source_id"),
    )
    for column in (
        "freshness_state",
        "schema_state",
        "volume_state",
        "field_population_state",
        "updated_at",
    ):
        op.create_index(f"ix_source_health_{column}", "source_health", [column])

    op.create_table(
        "source_quality_baselines",
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("expected_records_per_run", sa.Float(), nullable=True),
        sa.Column("last_records_count", sa.Integer(), nullable=True),
        sa.Column("accepted_schema_fingerprints", sa.JSON(), nullable=False),
        sa.Column("last_schema_fingerprints", sa.JSON(), nullable=False),
        sa.Column("field_population_baseline", sa.JSON(), nullable=False),
        sa.Column("last_field_population", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("source_id"),
    )
    op.create_index(
        "ix_source_quality_baselines_updated_at",
        "source_quality_baselines",
        ["updated_at"],
    )

    op.create_table(
        "source_portfolio_audit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("actor", sa.String(length=200), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("source_id", "action", "occurred_at"):
        op.create_index(
            f"ix_source_portfolio_audit_{column}", "source_portfolio_audit", [column]
        )


def downgrade() -> None:
    for column in ("occurred_at", "action", "source_id"):
        op.drop_index(
            f"ix_source_portfolio_audit_{column}", table_name="source_portfolio_audit"
        )
    op.drop_table("source_portfolio_audit")
    op.drop_index(
        "ix_source_quality_baselines_updated_at",
        table_name="source_quality_baselines",
    )
    op.drop_table("source_quality_baselines")
    for column in (
        "updated_at",
        "field_population_state",
        "volume_state",
        "schema_state",
        "freshness_state",
    ):
        op.drop_index(f"ix_source_health_{column}", table_name="source_health")
    op.drop_table("source_health")
    op.drop_index("ix_backfill_partition_claim", table_name="backfill_partitions")
    for column in ("updated_at", "state", "adapter_id", "source_id"):
        op.drop_index(f"ix_backfill_partitions_{column}", table_name="backfill_partitions")
    op.drop_table("backfill_partitions")
    op.drop_table("adapter_capabilities")
    for column in (
        "updated_at",
        "review_due_at",
        "authorization_expires_at",
        "status",
        "category",
    ):
        op.drop_index(f"ix_source_portfolio_{column}", table_name="source_portfolio")
    op.drop_table("source_portfolio")

    op.drop_index(
        "ix_raw_observations_supersedes_observation_id",
        table_name="raw_observations",
    )
    op.drop_index(
        "ix_raw_observations_source_record_action",
        table_name="raw_observations",
    )
    op.drop_column("raw_observations", "supersedes_observation_id")
    op.drop_column("raw_observations", "source_record_action")
