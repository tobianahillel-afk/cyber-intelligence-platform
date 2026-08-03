"""Create hashed suppression records.

Revision ID: 20260803_0002
Revises: 20260803_0001
Create Date: 2026-08-03
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260803_0002"
down_revision: str | Sequence[str] | None = "20260803_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "suppressions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject_hash", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "subject_hash",
            "channel",
            name="uq_suppression_subject_channel",
        ),
    )
    op.create_index("ix_suppressions_subject_hash", "suppressions", ["subject_hash"])
    op.create_index("ix_suppressions_channel", "suppressions", ["channel"])
    op.create_index("ix_suppressions_expires_at", "suppressions", ["expires_at"])
    op.create_index(
        "ix_suppressions_active_lookup",
        "suppressions",
        ["subject_hash", "channel", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_suppressions_active_lookup", table_name="suppressions")
    op.drop_index("ix_suppressions_expires_at", table_name="suppressions")
    op.drop_index("ix_suppressions_channel", table_name="suppressions")
    op.drop_index("ix_suppressions_subject_hash", table_name="suppressions")
    op.drop_table("suppressions")
