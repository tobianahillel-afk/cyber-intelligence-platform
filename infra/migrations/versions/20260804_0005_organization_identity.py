"""Create organization identity and merge-review tables.

Revision ID: 20260804_0005
Revises: 20260803_0004
Create Date: 2026-08-04
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260804_0005"
down_revision: str | Sequence[str] | None = "20260803_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _create_identities()
    _create_identifiers()
    _create_aliases()
    _create_relationships()
    _create_merge_candidates()
    _create_evidence_links()


def _create_identities() -> None:
    op.create_table(
        "organization_identities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("official_name", sa.String(length=300), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("legal_form", sa.String(length=300), nullable=True),
        sa.Column("activity_code", sa.String(length=20), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("city", sa.String(length=200), nullable=True),
        sa.Column("is_headquarters", sa.Boolean(), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("source_record_key", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            "source_record_key",
            name="uq_organization_identity_source_record",
        ),
    )
    for column in (
        "organization_id",
        "kind",
        "official_name",
        "country_code",
        "status",
        "activity_code",
        "postal_code",
        "city",
        "is_headquarters",
        "source_id",
        "observed_at",
        "updated_at",
    ):
        op.create_index(
            f"ix_organization_identities_{column}",
            "organization_identities",
            [column],
        )


def _create_identifiers() -> None:
    op.create_table(
        "organization_identifiers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identity_id", sa.Uuid(), nullable=False),
        sa.Column("scheme", sa.String(length=32), nullable=False),
        sa.Column("value", sa.String(length=100), nullable=False),
        sa.Column("issuing_country", sa.String(length=2), nullable=True),
        sa.Column("exact_key", sa.String(length=180), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["identity_id"],
            ["organization_identities.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exact_key", name="uq_organization_identifiers_exact_key"),
    )
    for column in (
        "identity_id",
        "scheme",
        "value",
        "issuing_country",
        "exact_key",
        "source_id",
        "verified_at",
        "is_current",
    ):
        op.create_index(
            f"ix_organization_identifiers_{column}",
            "organization_identifiers",
            [column],
        )


def _create_aliases() -> None:
    op.create_table(
        "organization_aliases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identity_id", sa.Uuid(), nullable=False),
        sa.Column("value", sa.String(length=300), nullable=False),
        sa.Column("normalized_value", sa.String(length=300), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["identity_id"],
            ["organization_identities.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "identity_id",
            "normalized_value",
            name="uq_organization_alias_identity_value",
        ),
    )
    op.create_index("ix_organization_aliases_identity_id", "organization_aliases", ["identity_id"])
    op.create_index("ix_organization_aliases_value", "organization_aliases", ["value"])
    op.create_index(
        "ix_organization_aliases_normalized_value",
        "organization_aliases",
        ["normalized_value"],
    )
    op.create_index("ix_organization_aliases_source_id", "organization_aliases", ["source_id"])


def _create_relationships() -> None:
    op.create_table(
        "organization_relationships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject_identity_id", sa.Uuid(), nullable=False),
        sa.Column("object_identity_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(
            ["subject_identity_id"],
            ["organization_identities.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["object_identity_id"],
            ["organization_identities.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "subject_identity_id",
            "object_identity_id",
            "relationship_type",
            "source_id",
            name="uq_organization_relationship_source",
        ),
    )
    for column in (
        "subject_identity_id",
        "object_identity_id",
        "relationship_type",
        "source_id",
        "observed_at",
    ):
        op.create_index(
            f"ix_organization_relationships_{column}",
            "organization_relationships",
            [column],
        )


def _create_merge_candidates() -> None:
    op.create_table(
        "organization_merge_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identity_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("method", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(length=200), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["identity_id"],
            ["organization_identities.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "identity_id",
            "organization_id",
            name="uq_organization_merge_candidate_pair",
        ),
    )
    for column in (
        "identity_id",
        "organization_id",
        "method",
        "score",
        "state",
        "created_at",
    ):
        op.create_index(
            f"ix_organization_merge_candidates_{column}",
            "organization_merge_candidates",
            [column],
        )


def _create_evidence_links() -> None:
    op.create_table(
        "organization_identity_evidence",
        sa.Column("identity_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["identity_id"],
            ["organization_identities.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("identity_id", "evidence_id"),
    )


def downgrade() -> None:
    op.drop_table("organization_identity_evidence")
    for column in (
        "created_at",
        "state",
        "score",
        "method",
        "organization_id",
        "identity_id",
    ):
        op.drop_index(
            f"ix_organization_merge_candidates_{column}",
            table_name="organization_merge_candidates",
        )
    op.drop_table("organization_merge_candidates")
    for column in (
        "observed_at",
        "source_id",
        "relationship_type",
        "object_identity_id",
        "subject_identity_id",
    ):
        op.drop_index(
            f"ix_organization_relationships_{column}",
            table_name="organization_relationships",
        )
    op.drop_table("organization_relationships")
    op.drop_index("ix_organization_aliases_source_id", table_name="organization_aliases")
    op.drop_index(
        "ix_organization_aliases_normalized_value",
        table_name="organization_aliases",
    )
    op.drop_index("ix_organization_aliases_value", table_name="organization_aliases")
    op.drop_index("ix_organization_aliases_identity_id", table_name="organization_aliases")
    op.drop_table("organization_aliases")
    for column in (
        "is_current",
        "verified_at",
        "source_id",
        "exact_key",
        "issuing_country",
        "value",
        "scheme",
        "identity_id",
    ):
        op.drop_index(
            f"ix_organization_identifiers_{column}",
            table_name="organization_identifiers",
        )
    op.drop_table("organization_identifiers")
    for column in (
        "updated_at",
        "observed_at",
        "source_id",
        "is_headquarters",
        "city",
        "postal_code",
        "activity_code",
        "status",
        "country_code",
        "official_name",
        "kind",
        "organization_id",
    ):
        op.drop_index(
            f"ix_organization_identities_{column}",
            table_name="organization_identities",
        )
    op.drop_table("organization_identities")
