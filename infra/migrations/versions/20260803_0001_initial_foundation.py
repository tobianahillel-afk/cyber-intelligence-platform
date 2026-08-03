"""Create source, organization, evidence, and raw observation tables.

Revision ID: 20260803_0001
Revises: None
Create Date: 2026-08-03
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260803_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("base_url", sa.String(length=2048), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("owner", sa.String(length=200), nullable=False),
        sa.Column("terms_url", sa.String(length=2048), nullable=True),
        sa.Column("licence", sa.String(length=200), nullable=True),
        sa.Column("allowed_data_categories", sa.JSON(), nullable=False),
        sa.Column("prohibited_data_categories", sa.JSON(), nullable=False),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=True),
        sa.Column("retention_days", sa.Integer(), nullable=True),
        sa.Column("attribution_required", sa.Boolean(), nullable=False),
        sa.Column("raw_content_storage", sa.Boolean(), nullable=False),
        sa.Column("human_review_required", sa.Boolean(), nullable=False),
        sa.Column("authorization_status", sa.String(length=32), nullable=False),
        sa.Column("authorization_document_reference", sa.String(length=500), nullable=True),
        sa.Column("authorization_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("authorization_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_hosts", sa.JSON(), nullable=False),
        sa.Column("approved_path_prefixes", sa.JSON(), nullable=False),
        sa.Column("approved_purposes", sa.JSON(), nullable=False),
        sa.Column("automated_collection_allowed", sa.Boolean(), nullable=False),
        sa.Column("raw_storage_allowed", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sources_status", "sources", ["status"])
    op.create_index("ix_sources_source_type", "sources", ["source_type"])
    op.create_index(
        "ix_sources_authorization_status",
        "sources",
        ["authorization_status"],
    )
    op.create_index(
        "ix_sources_authorization_expires_at",
        "sources",
        ["authorization_expires_at"],
    )

    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("canonical_name", sa.String(length=300), nullable=False),
        sa.Column("legal_name", sa.String(length=300), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("website_url", sa.String(length=2048), nullable=True),
        sa.Column("registration_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organizations_canonical_name", "organizations", ["canonical_name"])
    op.create_index("ix_organizations_legal_name", "organizations", ["legal_name"])
    op.create_index("ix_organizations_country_code", "organizations", ["country_code"])
    op.create_index("ix_organizations_updated_at", "organizations", ["updated_at"])

    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("source_record_key", sa.String(length=500), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash_sha256", sa.String(length=64), nullable=True),
        sa.Column("raw_storage_uri", sa.String(length=2048), nullable=True),
        sa.Column("raw_storage_permitted", sa.Boolean(), nullable=False),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_source_id", "evidence", ["source_id"])
    op.create_index("ix_evidence_collected_at", "evidence", ["collected_at"])
    op.create_index("ix_evidence_content_hash_sha256", "evidence", ["content_hash_sha256"])
    op.create_index("ix_evidence_retention_until", "evidence", ["retention_until"])

    op.create_table(
        "raw_observations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("adapter_id", sa.String(length=100), nullable=False),
        sa.Column("adapter_version", sa.String(length=50), nullable=False),
        sa.Column("collection_job_id", sa.Uuid(), nullable=False),
        sa.Column("source_record_key", sa.String(length=500), nullable=True),
        sa.Column("source_record_type", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_reference", sa.String(length=2048), nullable=True),
        sa.Column("payload_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("schema_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("content_language", sa.String(length=32), nullable=True),
        sa.Column("data_categories", sa.JSON(), nullable=False),
        sa.Column("classification", sa.String(length=32), nullable=False),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            "source_record_key",
            "payload_hash_sha256",
            name="uq_raw_observation_deduplication",
        ),
    )
    op.create_index("ix_raw_observations_source_id", "raw_observations", ["source_id"])
    op.create_index(
        "ix_raw_observations_collection_job_id",
        "raw_observations",
        ["collection_job_id"],
    )
    op.create_index(
        "ix_raw_observations_source_record_type",
        "raw_observations",
        ["source_record_type"],
    )
    op.create_index(
        "ix_raw_observations_collected_at",
        "raw_observations",
        ["collected_at"],
    )
    op.create_index(
        "ix_raw_observations_payload_hash_sha256",
        "raw_observations",
        ["payload_hash_sha256"],
    )
    op.create_index(
        "ix_raw_observations_retention_until",
        "raw_observations",
        ["retention_until"],
    )
    op.create_index(
        "ix_raw_observations_source_collected",
        "raw_observations",
        ["source_id", "collected_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_raw_observations_source_collected", table_name="raw_observations")
    op.drop_index("ix_raw_observations_retention_until", table_name="raw_observations")
    op.drop_index("ix_raw_observations_payload_hash_sha256", table_name="raw_observations")
    op.drop_index("ix_raw_observations_collected_at", table_name="raw_observations")
    op.drop_index("ix_raw_observations_source_record_type", table_name="raw_observations")
    op.drop_index("ix_raw_observations_collection_job_id", table_name="raw_observations")
    op.drop_index("ix_raw_observations_source_id", table_name="raw_observations")
    op.drop_table("raw_observations")

    op.drop_index("ix_evidence_retention_until", table_name="evidence")
    op.drop_index("ix_evidence_content_hash_sha256", table_name="evidence")
    op.drop_index("ix_evidence_collected_at", table_name="evidence")
    op.drop_index("ix_evidence_source_id", table_name="evidence")
    op.drop_table("evidence")

    op.drop_index("ix_organizations_updated_at", table_name="organizations")
    op.drop_index("ix_organizations_country_code", table_name="organizations")
    op.drop_index("ix_organizations_legal_name", table_name="organizations")
    op.drop_index("ix_organizations_canonical_name", table_name="organizations")
    op.drop_table("organizations")

    op.drop_index("ix_sources_authorization_expires_at", table_name="sources")
    op.drop_index("ix_sources_authorization_status", table_name="sources")
    op.drop_index("ix_sources_source_type", table_name="sources")
    op.drop_index("ix_sources_status", table_name="sources")
    op.drop_table("sources")
