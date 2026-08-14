"""Add version-bound public structured state records.

Revision ID: 20260814_0026
Revises: 20260814_0025
Create Date: 2026-08-14
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_0026"
down_revision: str | Sequence[str] | None = "20260814_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "public_structured_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("state_key", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("resource_version_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("page_url", sa.String(length=2_048), nullable=False),
        sa.Column("source_locator", sa.String(length=2_048), nullable=False),
        sa.Column("source_url", sa.String(length=2_048), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("media_type", sa.String(length=200), nullable=True),
        sa.Column("extractor_id", sa.String(length=100), nullable=True),
        sa.Column("payload_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resource_version_id"],
            ["public_resource_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state_key", name="uq_public_structured_state_identity"),
    )
    for name, columns in (
        ("ix_public_structured_states_organization_id", ["organization_id"]),
        ("ix_public_structured_states_resource_version_id", ["resource_version_id"]),
        ("ix_public_structured_states_kind", ["kind"]),
        ("ix_public_structured_state_organization_kind", ["organization_id", "kind"]),
        ("ix_public_structured_state_version_kind", ["resource_version_id", "kind"]),
        ("ix_public_structured_states_payload_hash_sha256", ["payload_hash_sha256"]),
    ):
        op.create_index(name, "public_structured_states", columns)


def downgrade() -> None:
    for name in (
        "ix_public_structured_states_payload_hash_sha256",
        "ix_public_structured_state_version_kind",
        "ix_public_structured_state_organization_kind",
        "ix_public_structured_states_kind",
        "ix_public_structured_states_resource_version_id",
        "ix_public_structured_states_organization_id",
    ):
        op.drop_index(name, table_name="public_structured_states")
    op.drop_table("public_structured_states")
