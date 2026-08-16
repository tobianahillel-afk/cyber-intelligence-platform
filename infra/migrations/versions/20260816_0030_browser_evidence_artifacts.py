"""Add governed browser evidence artifact metadata.

Revision ID: 20260816_0030
Revises: 20260816_0029
Create Date: 2026-08-16
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260816_0030"
down_revision: str | Sequence[str] | None = "20260816_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "browser_evidence_artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("artifact_key", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=200), nullable=False),
        sa.Column("provider_id", sa.String(length=200), nullable=False),
        sa.Column("target_id", sa.String(length=200), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("plan_version", sa.Integer(), nullable=False),
        sa.Column("step_id", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("page_url", sa.String(length=2_048), nullable=False),
        sa.Column("source_url", sa.String(length=2_048), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(length=200), nullable=False),
        sa.Column("source_locator", sa.String(length=500), nullable=False),
        sa.Column("raw_retention_allowed", sa.Boolean(), nullable=False),
        sa.Column("raw_retained", sa.Boolean(), nullable=False),
        sa.Column("storage_uri", sa.String(length=2_048), nullable=True),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("screenshot_mode", sa.String(length=40), nullable=True),
        sa.Column("viewport_width", sa.Integer(), nullable=True),
        sa.Column("viewport_height", sa.Integer(), nullable=True),
        sa.Column("element_selector", sa.String(length=1_000), nullable=True),
        sa.Column("original_filename", sa.String(length=500), nullable=True),
        sa.Column("extracted_text_hash_sha256", sa.String(length=64), nullable=True),
        sa.Column("excerpt", sa.String(length=1_000), nullable=True),
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_id", "plan_version"],
            ["browser_action_plans.plan_id", "browser_action_plans.plan_version"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "artifact_key",
            name="uq_browser_evidence_artifact_identity",
        ),
    )
    for name, columns in (
        ("ix_browser_evidence_artifacts_source_id", ["source_id"]),
        ("ix_browser_evidence_artifacts_provider_id", ["provider_id"]),
        ("ix_browser_evidence_artifacts_target_id", ["target_id"]),
        ("ix_browser_evidence_artifacts_job_id", ["job_id"]),
        ("ix_browser_evidence_artifacts_kind", ["kind"]),
        ("ix_browser_evidence_artifacts_state", ["state"]),
        ("ix_browser_evidence_artifacts_captured_at", ["captured_at"]),
        ("ix_browser_evidence_artifacts_content_hash_sha256", ["content_hash_sha256"]),
        ("ix_browser_evidence_artifacts_media_type", ["media_type"]),
        ("ix_browser_evidence_artifacts_retention_until", ["retention_until"]),
        ("ix_browser_evidence_artifacts_source_kind", ["source_id", "kind"]),
        ("ix_browser_evidence_artifacts_plan", ["plan_id", "plan_version"]),
    ):
        op.create_index(name, "browser_evidence_artifacts", columns)


def downgrade() -> None:
    for name in (
        "ix_browser_evidence_artifacts_plan",
        "ix_browser_evidence_artifacts_source_kind",
        "ix_browser_evidence_artifacts_retention_until",
        "ix_browser_evidence_artifacts_media_type",
        "ix_browser_evidence_artifacts_content_hash_sha256",
        "ix_browser_evidence_artifacts_captured_at",
        "ix_browser_evidence_artifacts_state",
        "ix_browser_evidence_artifacts_kind",
        "ix_browser_evidence_artifacts_job_id",
        "ix_browser_evidence_artifacts_target_id",
        "ix_browser_evidence_artifacts_provider_id",
        "ix_browser_evidence_artifacts_source_id",
    ):
        op.drop_index(name, table_name="browser_evidence_artifacts")
    op.drop_table("browser_evidence_artifacts")
