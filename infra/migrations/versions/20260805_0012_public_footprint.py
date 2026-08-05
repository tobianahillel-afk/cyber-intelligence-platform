"""Create public resources, immutable versions, and extracted claims.

Revision ID: 20260805_0012
Revises: 20260805_0011
Create Date: 2026-08-05
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260805_0012"
down_revision: str | Sequence[str] | None = "20260805_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "public_resources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("source_record_key", sa.String(length=500), nullable=False),
        sa.Column("identity_key", sa.String(length=64), nullable=False),
        sa.Column("corroboration_group_key", sa.String(length=64), nullable=False),
        sa.Column("canonical_url", sa.String(length=2_048), nullable=False),
        sa.Column("source_url", sa.String(length=2_048), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("discovery_method", sa.String(length=40), nullable=False),
        sa.Column("access_state", sa.String(length=40), nullable=False),
        sa.Column("retrieval_state", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=1_000), nullable=True),
        sa.Column("first_discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identity_key", name="uq_public_resource_identity"),
    )
    _resource_indexes()

    op.create_table(
        "public_resource_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("version_key", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.String(length=2_048), nullable=False),
        sa.Column("content_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mime_type", sa.String(length=200), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=1_000), nullable=True),
        sa.Column("language", sa.String(length=35), nullable=True),
        sa.Column("extracted_text_hash_sha256", sa.String(length=64), nullable=True),
        sa.Column("excerpt", sa.String(length=1_000), nullable=True),
        sa.Column("source_locator", sa.String(length=500), nullable=True),
        sa.Column("supersedes_version_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["public_resources.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_version_id"],
            ["public_resource_versions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_key", name="uq_public_resource_version"),
    )
    _version_indexes()

    op.create_table(
        "public_claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_key", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("resource_version_id", sa.Uuid(), nullable=False),
        sa.Column("claim_type", sa.String(length=80), nullable=False),
        sa.Column("statement", sa.String(length=2_000), nullable=False),
        sa.Column("evidence_basis", sa.String(length=80), nullable=False),
        sa.Column("resolution_status", sa.String(length=40), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("corroboration_group_key", sa.String(length=64), nullable=False),
        sa.Column("source_locator", sa.String(length=500), nullable=True),
        sa.Column("excerpt", sa.String(length=1_000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.UniqueConstraint("claim_key", name="uq_public_claim_identity"),
    )
    _claim_indexes()


def downgrade() -> None:
    _drop_claim_indexes()
    op.drop_table("public_claims")
    _drop_version_indexes()
    op.drop_table("public_resource_versions")
    _drop_resource_indexes()
    op.drop_table("public_resources")


def _resource_indexes() -> None:
    for name, columns in (
        ("ix_public_resources_organization_id", ["organization_id"]),
        ("ix_public_resources_source_id", ["source_id"]),
        ("ix_public_resources_source_record_key", ["source_record_key"]),
        ("ix_public_resources_corroboration_group_key", ["corroboration_group_key"]),
        ("ix_public_resources_canonical_url", ["canonical_url"]),
        ("ix_public_resources_kind", ["kind"]),
        ("ix_public_resources_discovery_method", ["discovery_method"]),
        ("ix_public_resources_access_state", ["access_state"]),
        ("ix_public_resources_retrieval_state", ["retrieval_state"]),
        ("ix_public_resources_first_discovered_at", ["first_discovered_at"]),
        ("ix_public_resources_last_seen_at", ["last_seen_at"]),
        ("ix_public_resources_updated_at", ["updated_at"]),
        ("ix_public_resource_source_record", ["source_id", "source_record_key"]),
    ):
        op.create_index(name, "public_resources", columns)


def _version_indexes() -> None:
    for name, columns in (
        ("ix_public_resource_versions_resource_id", ["resource_id"]),
        ("ix_public_resource_versions_content_hash_sha256", ["content_hash_sha256"]),
        ("ix_public_resource_versions_fetched_at", ["fetched_at"]),
        ("ix_public_resource_versions_published_at", ["published_at"]),
        ("ix_public_resource_versions_source_updated_at", ["source_updated_at"]),
        ("ix_public_resource_versions_mime_type", ["mime_type"]),
        ("ix_public_resource_versions_language", ["language"]),
        ("ix_public_resource_versions_supersedes_version_id", ["supersedes_version_id"]),
        (
            "ix_public_resource_version_resource_time",
            ["resource_id", "fetched_at"],
        ),
    ):
        op.create_index(name, "public_resource_versions", columns)


def _claim_indexes() -> None:
    for name, columns in (
        ("ix_public_claims_organization_id", ["organization_id"]),
        ("ix_public_claims_resource_version_id", ["resource_version_id"]),
        ("ix_public_claims_claim_type", ["claim_type"]),
        ("ix_public_claims_evidence_basis", ["evidence_basis"]),
        ("ix_public_claims_resolution_status", ["resolution_status"]),
        ("ix_public_claims_corroboration_group_key", ["corroboration_group_key"]),
        ("ix_public_claims_updated_at", ["updated_at"]),
        ("ix_public_claim_organization_type", ["organization_id", "claim_type"]),
    ):
        op.create_index(name, "public_claims", columns)


def _drop_claim_indexes() -> None:
    for name in (
        "ix_public_claim_organization_type",
        "ix_public_claims_updated_at",
        "ix_public_claims_corroboration_group_key",
        "ix_public_claims_resolution_status",
        "ix_public_claims_evidence_basis",
        "ix_public_claims_claim_type",
        "ix_public_claims_resource_version_id",
        "ix_public_claims_organization_id",
    ):
        op.drop_index(name, table_name="public_claims")


def _drop_version_indexes() -> None:
    for name in (
        "ix_public_resource_version_resource_time",
        "ix_public_resource_versions_supersedes_version_id",
        "ix_public_resource_versions_language",
        "ix_public_resource_versions_mime_type",
        "ix_public_resource_versions_source_updated_at",
        "ix_public_resource_versions_published_at",
        "ix_public_resource_versions_fetched_at",
        "ix_public_resource_versions_content_hash_sha256",
        "ix_public_resource_versions_resource_id",
    ):
        op.drop_index(name, table_name="public_resource_versions")


def _drop_resource_indexes() -> None:
    for name in (
        "ix_public_resource_source_record",
        "ix_public_resources_updated_at",
        "ix_public_resources_last_seen_at",
        "ix_public_resources_first_discovered_at",
        "ix_public_resources_retrieval_state",
        "ix_public_resources_access_state",
        "ix_public_resources_discovery_method",
        "ix_public_resources_kind",
        "ix_public_resources_canonical_url",
        "ix_public_resources_corroboration_group_key",
        "ix_public_resources_source_record_key",
        "ix_public_resources_source_id",
        "ix_public_resources_organization_id",
    ):
        op.drop_index(name, table_name="public_resources")
