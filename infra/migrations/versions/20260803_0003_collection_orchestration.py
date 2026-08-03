"""Create durable collection orchestration tables.

Revision ID: 20260803_0003
Revises: 20260803_0002
Create Date: 2026-08-03
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260803_0003"
down_revision: str | Sequence[str] | None = "20260803_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _create_jobs()
    _create_checkpoints()
    _create_circuits()
    _create_dead_letters()


def _create_jobs() -> None:
    op.create_table(
        "collection_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("adapter_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("lease_seconds", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("base_delay_seconds", sa.Integer(), nullable=False),
        sa.Column("max_delay_seconds", sa.Integer(), nullable=False),
        sa.Column("circuit_failure_threshold", sa.Integer(), nullable=False),
        sa.Column("circuit_reset_seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_owner", sa.String(length=200), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("observations_written", sa.Integer(), nullable=False),
        sa.Column("not_modified", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_collection_jobs_idempotency_key"),
    )
    op.create_index("ix_collection_jobs_source_id", "collection_jobs", ["source_id"])
    op.create_index("ix_collection_jobs_adapter_id", "collection_jobs", ["adapter_id"])
    op.create_index("ix_collection_jobs_status", "collection_jobs", ["status"])
    op.create_index("ix_collection_jobs_scheduled_for", "collection_jobs", ["scheduled_for"])
    op.create_index("ix_collection_jobs_available_at", "collection_jobs", ["available_at"])
    op.create_index("ix_collection_jobs_created_at", "collection_jobs", ["created_at"])
    op.create_index("ix_collection_jobs_lease_owner", "collection_jobs", ["lease_owner"])
    op.create_index("ix_collection_jobs_lease_expires_at", "collection_jobs", ["lease_expires_at"])
    op.create_index(
        "ix_collection_jobs_claim",
        "collection_jobs",
        ["status", "available_at", "scheduled_for"],
    )
    op.create_index(
        "ix_collection_jobs_source_schedule",
        "collection_jobs",
        ["source_id", "adapter_id", "scheduled_for"],
    )
    op.create_index(
        "ix_collection_jobs_lease_expiry",
        "collection_jobs",
        ["status", "lease_expires_at"],
    )


def _create_checkpoints() -> None:
    op.create_table(
        "collection_checkpoints",
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("adapter_id", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_observation_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("source_id", "adapter_id"),
    )
    op.create_index(
        "ix_collection_checkpoints_last_success",
        "collection_checkpoints",
        ["last_success_at"],
    )
    op.create_index(
        "ix_collection_checkpoints_last_observation",
        "collection_checkpoints",
        ["last_observation_at"],
    )


def _create_circuits() -> None:
    op.create_table(
        "collection_circuits",
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("adapter_id", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reopen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("source_id", "adapter_id"),
    )
    op.create_index("ix_collection_circuits_state", "collection_circuits", ["state"])
    op.create_index(
        "ix_collection_circuits_reopen",
        "collection_circuits",
        ["state", "reopen_at"],
    )


def _create_dead_letters() -> None:
    op.create_table(
        "collection_dead_letters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("adapter_id", sa.String(length=100), nullable=False),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("checkpoint_snapshot", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["collection_jobs.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", name="uq_collection_dead_letters_job_id"),
    )
    op.create_index("ix_collection_dead_letters_job_id", "collection_dead_letters", ["job_id"])
    op.create_index("ix_collection_dead_letters_source_id", "collection_dead_letters", ["source_id"])
    op.create_index("ix_collection_dead_letters_adapter_id", "collection_dead_letters", ["adapter_id"])
    op.create_index("ix_collection_dead_letters_failed_at", "collection_dead_letters", ["failed_at"])
    op.create_index(
        "ix_collection_dead_letters_source_failed",
        "collection_dead_letters",
        ["source_id", "adapter_id", "failed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_collection_dead_letters_source_failed", table_name="collection_dead_letters")
    op.drop_index("ix_collection_dead_letters_failed_at", table_name="collection_dead_letters")
    op.drop_index("ix_collection_dead_letters_adapter_id", table_name="collection_dead_letters")
    op.drop_index("ix_collection_dead_letters_source_id", table_name="collection_dead_letters")
    op.drop_index("ix_collection_dead_letters_job_id", table_name="collection_dead_letters")
    op.drop_table("collection_dead_letters")
    op.drop_index("ix_collection_circuits_reopen", table_name="collection_circuits")
    op.drop_index("ix_collection_circuits_state", table_name="collection_circuits")
    op.drop_table("collection_circuits")
    op.drop_index(
        "ix_collection_checkpoints_last_observation",
        table_name="collection_checkpoints",
    )
    op.drop_index("ix_collection_checkpoints_last_success", table_name="collection_checkpoints")
    op.drop_table("collection_checkpoints")
    op.drop_index("ix_collection_jobs_lease_expiry", table_name="collection_jobs")
    op.drop_index("ix_collection_jobs_source_schedule", table_name="collection_jobs")
    op.drop_index("ix_collection_jobs_claim", table_name="collection_jobs")
    op.drop_index("ix_collection_jobs_lease_expires_at", table_name="collection_jobs")
    op.drop_index("ix_collection_jobs_lease_owner", table_name="collection_jobs")
    op.drop_index("ix_collection_jobs_created_at", table_name="collection_jobs")
    op.drop_index("ix_collection_jobs_available_at", table_name="collection_jobs")
    op.drop_index("ix_collection_jobs_scheduled_for", table_name="collection_jobs")
    op.drop_index("ix_collection_jobs_status", table_name="collection_jobs")
    op.drop_index("ix_collection_jobs_adapter_id", table_name="collection_jobs")
    op.drop_index("ix_collection_jobs_source_id", table_name="collection_jobs")
    op.drop_table("collection_jobs")
