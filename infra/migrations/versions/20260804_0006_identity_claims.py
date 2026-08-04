"""Create source-specific organization identity claims.

Revision ID: 20260804_0006
Revises: 20260804_0005
Create Date: 2026-08-04
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260804_0006"
down_revision: str | Sequence[str] | None = "20260804_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organization_identity_claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identity_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("source_record_key", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("selected_fields", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash_sha256", sa.String(length=64), nullable=True),
        sa.Column("conflict_fields", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["identity_id"],
            ["organization_identities.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            "source_record_key",
            name="uq_organization_identity_claim_source_record",
        ),
    )
    op.create_index(
        "ix_organization_identity_claims_identity_id",
        "organization_identity_claims",
        ["identity_id"],
    )
    op.create_index(
        "ix_organization_identity_claims_source_id",
        "organization_identity_claims",
        ["source_id"],
    )
    op.create_index(
        "ix_organization_identity_claims_observed_at",
        "organization_identity_claims",
        ["observed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organization_identity_claims_observed_at",
        table_name="organization_identity_claims",
    )
    op.drop_index(
        "ix_organization_identity_claims_source_id",
        table_name="organization_identity_claims",
    )
    op.drop_index(
        "ix_organization_identity_claims_identity_id",
        table_name="organization_identity_claims",
    )
    op.drop_table("organization_identity_claims")
