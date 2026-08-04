"""Create provider onboarding state and audit tables.

Revision ID: 20260804_0007
Revises: 20260804_0006
Create Date: 2026-08-04
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260804_0007"
down_revision: str | Sequence[str] | None = "20260804_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_onboarding",
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("auth_mode", sa.String(length=40), nullable=False),
        sa.Column("state", sa.String(length=50), nullable=False),
        sa.Column("documentation_url", sa.String(length=2048), nullable=False),
        sa.Column("signup_url", sa.String(length=2048), nullable=True),
        sa.Column("console_url", sa.String(length=2048), nullable=True),
        sa.Column("required_secret_names", sa.JSON(), nullable=False),
        sa.Column("human_actions", sa.JSON(), nullable=False),
        sa.Column("automatic_onboarding", sa.Boolean(), nullable=False),
        sa.Column("secret_references", sa.JSON(), nullable=False),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("source_id"),
    )
    for column in (
        "auth_mode",
        "state",
        "last_verified_at",
        "expires_at",
        "updated_at",
    ):
        op.create_index(
            f"ix_provider_onboarding_{column}",
            "provider_onboarding",
            [column],
        )

    op.create_table(
        "provider_onboarding_audit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("previous_state", sa.String(length=50), nullable=True),
        sa.Column("new_state", sa.String(length=50), nullable=False),
        sa.Column("actor", sa.String(length=200), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("source_id", "action", "new_state", "occurred_at"):
        op.create_index(
            f"ix_provider_onboarding_audit_{column}",
            "provider_onboarding_audit",
            [column],
        )


def downgrade() -> None:
    for column in ("occurred_at", "new_state", "action", "source_id"):
        op.drop_index(
            f"ix_provider_onboarding_audit_{column}",
            table_name="provider_onboarding_audit",
        )
    op.drop_table("provider_onboarding_audit")
    for column in (
        "updated_at",
        "expires_at",
        "last_verified_at",
        "state",
        "auth_mode",
    ):
        op.drop_index(
            f"ix_provider_onboarding_{column}",
            table_name="provider_onboarding",
        )
    op.drop_table("provider_onboarding")
