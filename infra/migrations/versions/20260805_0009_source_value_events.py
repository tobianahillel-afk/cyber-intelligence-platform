"""Create idempotent source value events for ablation analysis.

Revision ID: 20260805_0009
Revises: 20260805_0008
Create Date: 2026-08-05
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260805_0009"
down_revision: str | Sequence[str] | None = "20260805_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_value_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "source_id",
            sa.String(length=100),
            sa.ForeignKey("source_portfolio.source_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("execution_mode", sa.String(length=40), nullable=False),
        sa.Column("observations_written", sa.Integer(), nullable=False),
        sa.Column("commercial_projections", sa.Integer(), nullable=False),
        sa.Column("identity_projections", sa.Integer(), nullable=False),
        sa.Column("request_cost", sa.Float(), nullable=False),
        sa.Column("not_modified", sa.Boolean(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            "execution_id",
            "execution_mode",
            name="uq_source_value_event_execution",
        ),
    )
    op.create_index(
        "ix_source_value_events_source_id",
        "source_value_events",
        ["source_id"],
    )
    op.create_index(
        "ix_source_value_events_execution_id",
        "source_value_events",
        ["execution_id"],
    )
    op.create_index(
        "ix_source_value_events_execution_mode",
        "source_value_events",
        ["execution_mode"],
    )
    op.create_index(
        "ix_source_value_events_occurred_at",
        "source_value_events",
        ["occurred_at"],
    )
    op.create_index(
        "ix_source_value_events_source_time",
        "source_value_events",
        ["source_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_source_value_events_source_time", table_name="source_value_events")
    op.drop_index("ix_source_value_events_occurred_at", table_name="source_value_events")
    op.drop_index("ix_source_value_events_execution_mode", table_name="source_value_events")
    op.drop_index("ix_source_value_events_execution_id", table_name="source_value_events")
    op.drop_index("ix_source_value_events_source_id", table_name="source_value_events")
    op.drop_table("source_value_events")
