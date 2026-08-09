"""Create professional organization context and privacy lifecycle records.

Revision ID: 20260809_0021
Revises: 20260808_0020
Create Date: 2026-08-09
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0021"
down_revision: str | Sequence[str] | None = "20260808_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _create_people()
    _create_person_snapshots()
    _create_roles()
    _create_role_snapshots()
    _create_reporting_lines()
    _create_reporting_snapshots()
    _create_contacts()
    _create_contact_snapshots()
    _create_community()
    _create_community_snapshots()
    _create_service_relevance()
    _create_deletion_audit()


def downgrade() -> None:
    for table_name in reversed(_TABLES):
        _drop_indexes(table_name)
        op.drop_table(table_name)


def _create_people() -> None:
    op.create_table(
        "professional_people",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("person_key", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(300), nullable=True),
        sa.Column("source_id", sa.String(200), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("review_state", sa.String(32), nullable=False),
        *_processing_columns(),
        sa.Column("current", sa.Boolean(), nullable=False),
        sa.Column("suppressed", sa.Boolean(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("person_key"),
    )
    _indexes("professional_people", "person_key", "source_id", "current", "deleted")


def _create_person_snapshots() -> None:
    op.create_table(
        "professional_person_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_key", sa.String(64), nullable=False),
        sa.Column("person_key", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(300), nullable=True),
        sa.Column("source_id", sa.String(200), nullable=False),
        sa.Column("source_kind", sa.String(80), nullable=False),
        sa.Column("source_record_key", sa.String(500), nullable=True),
        sa.Column("source_url", sa.String(2_048), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("review_state", sa.String(32), nullable=False),
        *_snapshot_processing_columns(),
        *_snapshot_flags(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["professional_people.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_key"),
    )
    _indexes("professional_person_snapshots", "person_id", "person_key", "observed_at", "deleted")


def _create_roles() -> None:
    op.create_table(
        "professional_roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_key", sa.String(500), nullable=False),
        sa.Column("person_key", sa.String(200), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("claimed_organization_name", sa.String(500), nullable=True),
        sa.Column("role_title", sa.String(300), nullable=True),
        sa.Column("team_name", sa.String(300), nullable=True),
        sa.Column("employment_state", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("review_state", sa.String(32), nullable=False),
        *_processing_columns(),
        sa.Column("suppressed", sa.Boolean(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_key"),
    )
    _indexes("professional_roles", "claim_key", "person_key", "organization_id", "employment_state", "deleted")


def _create_role_snapshots() -> None:
    op.create_table(
        "professional_role_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_key", sa.String(64), nullable=False),
        sa.Column("claim_key", sa.String(500), nullable=False),
        sa.Column("person_key", sa.String(200), nullable=False),
        *_source_columns(),
        sa.Column("role_title", sa.String(300), nullable=True),
        sa.Column("team_name", sa.String(300), nullable=True),
        sa.Column("claimed_organization_name", sa.String(500), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("organization_link_status", sa.String(32), nullable=False),
        sa.Column("claim_type", sa.String(32), nullable=False),
        sa.Column("review_state", sa.String(32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("historical_only", sa.Boolean(), nullable=False),
        sa.Column("suppressed", sa.Boolean(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column("supersedes_record_key", sa.String(500), nullable=True),
        *_snapshot_processing_columns(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["professional_roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_key"),
    )
    _indexes("professional_role_snapshots", "role_id", "person_key", "organization_id", "observed_at", "deleted")


def _create_reporting_lines() -> None:
    op.create_table(
        "professional_reporting_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_key", sa.String(500), nullable=False),
        sa.Column("subject_person_key", sa.String(200), nullable=False),
        sa.Column("manager_person_key", sa.String(200), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("review_state", sa.String(32), nullable=False),
        *_processing_columns(),
        sa.Column("current", sa.Boolean(), nullable=False),
        sa.Column("suppressed", sa.Boolean(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_key"),
    )
    _indexes("professional_reporting_lines", "claim_key", "subject_person_key", "manager_person_key", "current", "deleted")


def _create_reporting_snapshots() -> None:
    op.create_table(
        "professional_reporting_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reporting_line_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_key", sa.String(64), nullable=False),
        sa.Column("claim_key", sa.String(500), nullable=False),
        sa.Column("subject_person_key", sa.String(200), nullable=False),
        sa.Column("manager_person_key", sa.String(200), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        *_source_columns(),
        sa.Column("claim_type", sa.String(32), nullable=False),
        sa.Column("review_state", sa.String(32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        *_snapshot_flags(),
        sa.Column("supersedes_record_key", sa.String(500), nullable=True),
        *_snapshot_processing_columns(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["reporting_line_id"], ["professional_reporting_lines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_key"),
    )
    _indexes("professional_reporting_snapshots", "reporting_line_id", "subject_person_key", "manager_person_key", "observed_at", "deleted")


def _create_contacts() -> None:
    op.create_table(
        "professional_contacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("contact_key", sa.String(500), nullable=False),
        sa.Column("channel_type", sa.String(40), nullable=False),
        sa.Column("value", sa.String(2_048), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("person_key", sa.String(200), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("review_state", sa.String(32), nullable=False),
        *_processing_columns(),
        sa.Column("current", sa.Boolean(), nullable=False),
        sa.Column("suppressed", sa.Boolean(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contact_key"),
    )
    _indexes("professional_contacts", "contact_key", "channel_type", "organization_id", "person_key", "current", "deleted")


def _create_contact_snapshots() -> None:
    op.create_table(
        "professional_contact_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_key", sa.String(64), nullable=False),
        sa.Column("contact_key", sa.String(500), nullable=False),
        sa.Column("channel_type", sa.String(40), nullable=False),
        sa.Column("evidence_scope", sa.String(40), nullable=False),
        sa.Column("value", sa.String(2_048), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("person_key", sa.String(200), nullable=True),
        *_source_columns(),
        sa.Column("claim_type", sa.String(32), nullable=False),
        sa.Column("review_state", sa.String(32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        *_snapshot_flags(),
        sa.Column("supersedes_record_key", sa.String(500), nullable=True),
        *_snapshot_processing_columns(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["contact_id"], ["professional_contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_key"),
    )
    _indexes("professional_contact_snapshots", "contact_id", "channel_type", "person_key", "observed_at", "deleted")


def _create_community() -> None:
    op.create_table(
        "professional_community_contexts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("context_key", sa.String(500), nullable=False),
        sa.Column("community_name", sa.String(300), nullable=False),
        sa.Column("context_type", sa.String(100), nullable=False),
        sa.Column("context_value", sa.String(500), nullable=True),
        sa.Column("acquisition_mode", sa.String(50), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("person_key", sa.String(200), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("review_state", sa.String(32), nullable=False),
        *_processing_columns(),
        sa.Column("current", sa.Boolean(), nullable=False),
        sa.Column("suppressed", sa.Boolean(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("context_key"),
    )
    _indexes("professional_community_contexts", "context_key", "community_name", "person_key", "current", "deleted")


def _create_community_snapshots() -> None:
    op.create_table(
        "professional_community_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("context_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_key", sa.String(64), nullable=False),
        sa.Column("context_key", sa.String(500), nullable=False),
        sa.Column("community_name", sa.String(300), nullable=False),
        sa.Column("context_type", sa.String(100), nullable=False),
        sa.Column("context_value", sa.String(500), nullable=True),
        sa.Column("acquisition_mode", sa.String(50), nullable=False),
        sa.Column("authorization_reference", sa.String(500), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("person_key", sa.String(200), nullable=True),
        *_source_columns(),
        sa.Column("claim_type", sa.String(32), nullable=False),
        sa.Column("review_state", sa.String(32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        *_snapshot_flags(),
        sa.Column("metadata_only", sa.Boolean(), nullable=False),
        sa.Column("supersedes_record_key", sa.String(500), nullable=True),
        *_snapshot_processing_columns(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["context_id"], ["professional_community_contexts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_key"),
    )
    _indexes("professional_community_snapshots", "context_id", "community_name", "person_key", "observed_at", "deleted")


def _create_service_relevance() -> None:
    op.create_table(
        "professional_service_relevance",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("mapping_key", sa.String(500), nullable=False),
        sa.Column("person_key", sa.String(200), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("service_family", sa.String(80), nullable=False),
        sa.Column("rationale", sa.String(500), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source_claim_keys", sa.JSON(), nullable=False),
        sa.Column("review_state", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mapping_key"),
    )
    _indexes("professional_service_relevance", "mapping_key", "person_key", "organization_id", "service_family")


def _create_deletion_audit() -> None:
    op.create_table(
        "professional_deletion_audit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=True),
        sa.Column("subject_hash", sa.String(64), nullable=False),
        sa.Column("channel", sa.String(40), nullable=False),
        sa.Column("reason", sa.String(40), nullable=False),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("actor", sa.String(200), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("suppression_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["professional_people.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    _indexes("professional_deletion_audit", "person_id", "subject_hash", "channel", "requested_at")


def _processing_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("lawful_basis", sa.String(40), nullable=False),
        sa.Column("lawful_basis_reference", sa.String(500), nullable=False),
        sa.Column("processing_purpose", sa.String(300), nullable=False),
    )


def _snapshot_processing_columns() -> tuple[sa.Column, ...]:
    return (*_processing_columns(),
        sa.Column("processing_reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=False),
    )


def _source_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("source_id", sa.String(200), nullable=False),
        sa.Column("source_record_key", sa.String(500), nullable=True),
        sa.Column("source_url", sa.String(2_048), nullable=True),
    )


def _snapshot_flags() -> tuple[sa.Column, ...]:
    return (
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("suppressed", sa.Boolean(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
    )


def _indexes(table_name: str, *columns: str) -> None:
    for column in columns:
        op.create_index(_index_name(table_name, column), table_name, [column])


def _drop_indexes(table_name: str) -> None:
    for column in reversed(_INDEXES[table_name]):
        op.drop_index(_index_name(table_name, column), table_name=table_name)


def _index_name(table_name: str, column: str) -> str:
    return f"ix_{_PREFIXES[table_name]}_{column}"


_TABLES = (
    "professional_people",
    "professional_person_snapshots",
    "professional_roles",
    "professional_role_snapshots",
    "professional_reporting_lines",
    "professional_reporting_snapshots",
    "professional_contacts",
    "professional_contact_snapshots",
    "professional_community_contexts",
    "professional_community_snapshots",
    "professional_service_relevance",
    "professional_deletion_audit",
)

_PREFIXES = {
    "professional_people": "pro_people",
    "professional_person_snapshots": "pro_ps",
    "professional_roles": "pro_role",
    "professional_role_snapshots": "pro_rs",
    "professional_reporting_lines": "pro_rl",
    "professional_reporting_snapshots": "pro_rls",
    "professional_contacts": "pro_contact",
    "professional_contact_snapshots": "pro_cs",
    "professional_community_contexts": "pro_comm",
    "professional_community_snapshots": "pro_cms",
    "professional_service_relevance": "pro_sr",
    "professional_deletion_audit": "pro_del",
}

_INDEXES = {
    "professional_people": ("person_key", "source_id", "current", "deleted"),
    "professional_person_snapshots": ("person_id", "person_key", "observed_at", "deleted"),
    "professional_roles": ("claim_key", "person_key", "organization_id", "employment_state", "deleted"),
    "professional_role_snapshots": ("role_id", "person_key", "organization_id", "observed_at", "deleted"),
    "professional_reporting_lines": ("claim_key", "subject_person_key", "manager_person_key", "current", "deleted"),
    "professional_reporting_snapshots": ("reporting_line_id", "subject_person_key", "manager_person_key", "observed_at", "deleted"),
    "professional_contacts": ("contact_key", "channel_type", "organization_id", "person_key", "current", "deleted"),
    "professional_contact_snapshots": ("contact_id", "channel_type", "person_key", "observed_at", "deleted"),
    "professional_community_contexts": ("context_key", "community_name", "person_key", "current", "deleted"),
    "professional_community_snapshots": ("context_id", "community_name", "person_key", "observed_at", "deleted"),
    "professional_service_relevance": ("mapping_key", "person_key", "organization_id", "service_family"),
    "professional_deletion_audit": ("person_id", "subject_hash", "channel", "requested_at"),
}
