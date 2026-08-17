"""Add durable human checkpoints for resumable authenticated collection.

Revision ID: 20260817_0032
Revises: 20260816_0031
Create Date: 2026-08-17
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260817_0032"
down_revision: str | Sequence[str] | None = "20260816_0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "collection_jobs",
        sa.Column(
            "human_resume_pending",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_table(
        "collection_human_checkpoints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("adapter_id", sa.String(length=100), nullable=False),
        sa.Column("delegated_identity_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("correlation_digest", sa.String(length=64), nullable=False),
        sa.Column("session_reference", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["collection_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["delegated_identity_id"],
            ["delegated_browser_identities.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in (
        ("ix_collection_human_checkpoints_job", ["job_id"]),
        ("ix_collection_human_checkpoints_source", ["source_id"]),
        ("ix_collection_human_checkpoints_adapter", ["adapter_id"]),
        ("ix_collection_human_checkpoints_identity", ["delegated_identity_id"]),
        ("ix_collection_human_checkpoints_purpose", ["purpose"]),
        ("ix_collection_human_checkpoints_kind", ["kind"]),
        ("ix_collection_human_checkpoints_state", ["state"]),
        ("ix_collection_human_checkpoints_created", ["created_at"]),
        ("ix_collection_human_checkpoints_expires", ["expires_at"]),
        ("ix_collection_human_checkpoints_job_state", ["job_id", "state"]),
        ("ix_collection_human_checkpoints_expiry", ["state", "expires_at"]),
        (
            "ix_collection_human_checkpoints_identity_state",
            ["delegated_identity_id", "state"],
        ),
    ):
        op.create_index(name, "collection_human_checkpoints", columns)
    op.create_table(
        "collection_human_checkpoint_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("checkpoint_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_reference", sa.String(length=200), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(
            ["checkpoint_id"],
            ["collection_human_checkpoints.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["job_id"], ["collection_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in (
        ("ix_collection_human_checkpoint_events_checkpoint", ["checkpoint_id"]),
        ("ix_collection_human_checkpoint_events_job", ["job_id"]),
        ("ix_collection_human_checkpoint_events_type", ["event_type"]),
        ("ix_collection_human_checkpoint_events_time", ["occurred_at"]),
        (
            "ix_collection_human_checkpoint_events_checkpoint_time",
            ["checkpoint_id", "occurred_at"],
        ),
        (
            "ix_collection_human_checkpoint_events_job_time",
            ["job_id", "occurred_at"],
        ),
    ):
        op.create_index(name, "collection_human_checkpoint_events", columns)


def downgrade() -> None:
    op.drop_table("collection_human_checkpoint_events")
    op.drop_table("collection_human_checkpoints")
    op.drop_column("collection_jobs", "human_resume_pending")
