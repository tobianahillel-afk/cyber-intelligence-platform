"""Add explicit procurement contract notification dates.

Revision ID: 20260805_0011
Revises: 20260805_0010
Create Date: 2026-08-05
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260805_0011"
down_revision: str | Sequence[str] | None = "20260805_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "procurement_contracts",
        sa.Column("notification_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "procurement_contracts",
        sa.Column(
            "notification_date_basis",
            sa.String(length=40),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.create_index(
        "ix_procurement_contracts_notification_date",
        "procurement_contracts",
        ["notification_date"],
    )
    op.alter_column(
        "procurement_contracts",
        "notification_date_basis",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_procurement_contracts_notification_date",
        table_name="procurement_contracts",
    )
    op.drop_column("procurement_contracts", "notification_date_basis")
    op.drop_column("procurement_contracts", "notification_date")
