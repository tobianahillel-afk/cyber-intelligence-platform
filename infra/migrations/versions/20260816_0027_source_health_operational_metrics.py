"""Add bounded operational metrics to source health.

Revision ID: 20260816_0027
Revises: 20260814_0026
Create Date: 2026-08-16
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260816_0027"
down_revision: str | Sequence[str] | None = "20260814_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "source_health",
        sa.Column("operational_metrics", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("source_health", "operational_metrics")
