"""Add governed browser action plans and checkpoints.

Revision ID: 20260816_0029
Revises: 20260816_0028
Create Date: 2026-08-16
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260816_0029"
down_revision: str | Sequence[str] | None = "20260816_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "browser_action_plans",
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("plan_version", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(length=200), nullable=False),
        sa.Column("provider_id", sa.String(length=200), nullable=False),
        sa.Column("target_id", sa.String(length=200), nullable=False),
        sa.Column("purpose", sa.String(length=500), nullable=False),
        sa.Column("payload_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("plan_id", "plan_version"),
    )
    for name, columns in (
        ("ix_browser_action_plans_source_id", ["source_id"]),
        ("ix_browser_action_plans_provider_id", ["provider_id"]),
        ("ix_browser_action_plans_target_id", ["target_id"]),
        ("ix_browser_action_plans_payload_hash_sha256", ["payload_hash_sha256"]),
    ):
        op.create_index(name, "browser_action_plans", columns)

    op.create_table(
        "browser_action_checkpoints",
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("plan_version", sa.Integer(), nullable=False),
        sa.Column("step_states", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_id", "plan_version"],
            ["browser_action_plans.plan_id", "browser_action_plans.plan_version"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("plan_id", "plan_version"),
    )
    op.create_index(
        "ix_browser_action_checkpoints_updated_at",
        "browser_action_checkpoints",
        ["updated_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_browser_action_checkpoints_updated_at",
        table_name="browser_action_checkpoints",
    )
    op.drop_table("browser_action_checkpoints")
    for name in (
        "ix_browser_action_plans_payload_hash_sha256",
        "ix_browser_action_plans_target_id",
        "ix_browser_action_plans_provider_id",
        "ix_browser_action_plans_source_id",
    ):
        op.drop_index(name, table_name="browser_action_plans")
    op.drop_table("browser_action_plans")
