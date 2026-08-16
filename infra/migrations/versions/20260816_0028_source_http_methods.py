"""Add approved HTTP methods to source authorization.

Revision ID: 20260816_0028
Revises: 20260816_0027
Create Date: 2026-08-16
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260816_0028"
down_revision: str | Sequence[str] | None = "20260816_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sources",
        sa.Column(
            "approved_http_methods",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[\"GET\"]'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("sources", "approved_http_methods")
