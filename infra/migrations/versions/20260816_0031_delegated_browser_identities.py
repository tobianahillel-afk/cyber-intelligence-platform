"""Add delegated browser identity and audit control-plane records.

Revision ID: 20260816_0031
Revises: 20260816_0030
Create Date: 2026-08-16
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260816_0031"
down_revision: str | Sequence[str] | None = "20260816_0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "delegated_browser_identities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("external_reference", sa.String(length=500), nullable=False),
        sa.Column("auth_mode", sa.String(length=40), nullable=False),
        sa.Column("account_status", sa.String(length=40), nullable=False),
        sa.Column("authorization_document_reference", sa.String(length=500), nullable=True),
        sa.Column("approved_purposes", sa.JSON(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("owner_kind", sa.String(length=40), nullable=False),
        sa.Column("owner_subject_id", sa.String(length=200), nullable=False),
        sa.Column("purpose", sa.String(length=200), nullable=False),
        sa.Column("approved_scopes", sa.JSON(), nullable=False),
        sa.Column("secret_reference", sa.String(length=500), nullable=True),
        sa.Column("session_reference", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("account_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("renewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reference_rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("session_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reference_version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "owner_kind",
            "owner_subject_id",
            "source_id",
            "purpose",
            "external_reference",
            name="uq_delegated_browser_identity_ownership",
        ),
    )
    for name, columns in (
        ("ix_delegated_browser_identities_source_id", ["source_id"]),
        ("ix_delegated_browser_identities_auth_mode", ["auth_mode"]),
        ("ix_delegated_browser_identities_account_status", ["account_status"]),
        ("ix_delegated_browser_identities_tenant_id", ["tenant_id"]),
        ("ix_delegated_browser_identities_owner_kind", ["owner_kind"]),
        ("ix_delegated_browser_identities_owner_subject_id", ["owner_subject_id"]),
        ("ix_delegated_browser_identities_purpose", ["purpose"]),
        ("ix_delegated_browser_identities_account_expires_at", ["account_expires_at"]),
        ("ix_delegated_browser_identities_revoked_at", ["revoked_at"]),
        ("ix_delegated_browser_identities_deleted_at", ["deleted_at"]),
        ("ix_delegated_browser_identities_session_expires_at", ["session_expires_at"]),
        ("ix_delegated_browser_identities_updated_at", ["updated_at"]),
        (
            "ix_delegated_browser_identities_owner_scope",
            ["tenant_id", "owner_kind", "owner_subject_id", "source_id"],
        ),
    ):
        op.create_index(name, "delegated_browser_identities", columns)

    op.create_table(
        "delegated_browser_identity_audit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identity_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("actor_kind", sa.String(length=40), nullable=False),
        sa.Column("actor_subject_id", sa.String(length=200), nullable=False),
        sa.Column("reference_version", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["identity_id"],
            ["delegated_browser_identities.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in (
        ("ix_delegated_browser_identity_audit_identity_id", ["identity_id"]),
        ("ix_delegated_browser_identity_audit_tenant_id", ["tenant_id"]),
        ("ix_delegated_browser_identity_audit_event_type", ["event_type"]),
        ("ix_delegated_browser_identity_audit_occurred_at", ["occurred_at"]),
        (
            "ix_delegated_browser_identity_audit_identity_time",
            ["identity_id", "occurred_at"],
        ),
    ):
        op.create_index(name, "delegated_browser_identity_audit", columns)


def downgrade() -> None:
    for name in (
        "ix_delegated_browser_identity_audit_identity_time",
        "ix_delegated_browser_identity_audit_occurred_at",
        "ix_delegated_browser_identity_audit_event_type",
        "ix_delegated_browser_identity_audit_tenant_id",
        "ix_delegated_browser_identity_audit_identity_id",
    ):
        op.drop_index(name, table_name="delegated_browser_identity_audit")
    op.drop_table("delegated_browser_identity_audit")

    for name in (
        "ix_delegated_browser_identities_owner_scope",
        "ix_delegated_browser_identities_updated_at",
        "ix_delegated_browser_identities_session_expires_at",
        "ix_delegated_browser_identities_deleted_at",
        "ix_delegated_browser_identities_revoked_at",
        "ix_delegated_browser_identities_account_expires_at",
        "ix_delegated_browser_identities_purpose",
        "ix_delegated_browser_identities_owner_subject_id",
        "ix_delegated_browser_identities_owner_kind",
        "ix_delegated_browser_identities_tenant_id",
        "ix_delegated_browser_identities_account_status",
        "ix_delegated_browser_identities_auth_mode",
        "ix_delegated_browser_identities_source_id",
    ):
        op.drop_index(name, table_name="delegated_browser_identities")
    op.drop_table("delegated_browser_identities")
