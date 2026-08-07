"""Create corporate and regulatory change intelligence projections.

Revision ID: 20260807_0018
Revises: 20260807_0017
Create Date: 2026-08-07
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260807_0018"
down_revision: str | Sequence[str] | None = "20260807_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _create_events()
    _create_claims()
    _create_service_mappings()


def downgrade() -> None:
    _drop_indexes("corporate_change_service_mappings", _mapping_indexes())
    op.drop_table("corporate_change_service_mappings")
    op.drop_index("ix_change_claim_source_record", table_name="corporate_change_claim_snapshots")
    _drop_indexes("corporate_change_claim_snapshots", _claim_indexes())
    op.drop_table("corporate_change_claim_snapshots")
    _drop_indexes("corporate_change_events", _event_indexes())
    op.drop_table("corporate_change_events")


def _create_events() -> None:
    op.create_table(
        "corporate_change_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_key", sa.String(length=500), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=1_000), nullable=False),
        sa.Column("excerpt", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("organization_link_status", sa.String(length=80), nullable=False),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claim_count", sa.Integer(), nullable=False),
        sa.Column("independent_source_count", sa.Integer(), nullable=False),
        sa.Column("officially_confirmed", sa.Boolean(), nullable=False),
        sa.Column("has_dispute", sa.Boolean(), nullable=False),
        sa.Column("has_correction", sa.Boolean(), nullable=False),
        sa.Column("has_retraction", sa.Boolean(), nullable=False),
        sa.Column("historical_only", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_key"),
    )
    _create_indexes("corporate_change_events", _event_indexes())


def _create_claims() -> None:
    op.create_table(
        "corporate_change_claim_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_key", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=200), nullable=False),
        sa.Column("source_kind", sa.String(length=80), nullable=False),
        sa.Column("source_record_key", sa.String(length=500), nullable=False),
        sa.Column("article_id", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.String(length=2_048), nullable=False),
        sa.Column("event_key", sa.String(length=500), nullable=False),
        sa.Column("claim_type", sa.String(length=80), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=1_000), nullable=False),
        sa.Column("excerpt", sa.String(length=500), nullable=False),
        sa.Column("claimed_organization_name", sa.String(length=500), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("organization_link_status", sa.String(length=80), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("independence_key", sa.String(length=500), nullable=False),
        sa.Column("syndication_group_key", sa.String(length=500), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("historical_only", sa.Boolean(), nullable=False),
        sa.Column("metadata_only", sa.Boolean(), nullable=False),
        sa.Column("supersedes_record_key", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["corporate_change_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_key", name="uq_corporate_change_claim_snapshot"),
    )
    _create_indexes("corporate_change_claim_snapshots", _claim_indexes())
    op.create_index(
        "ix_change_claim_source_record",
        "corporate_change_claim_snapshots",
        ["source_id", "source_record_key"],
    )


def _create_service_mappings() -> None:
    op.create_table(
        "corporate_change_service_mappings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("service_family", sa.String(length=120), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["corporate_change_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "service_family", name="uq_change_event_service_family"),
    )
    _create_indexes("corporate_change_service_mappings", _mapping_indexes())


def _event_indexes() -> tuple[str, ...]:
    return (
        "event_key", "event_type", "status", "organization_id",
        "organization_link_status", "event_at", "first_published_at",
        "last_updated_at", "officially_confirmed", "has_dispute",
        "has_correction", "has_retraction", "historical_only", "updated_at",
    )


def _claim_indexes() -> tuple[str, ...]:
    return (
        "event_id", "source_id", "source_kind", "source_record_key", "article_id",
        "event_key", "claim_type", "event_type", "claimed_organization_name",
        "organization_id", "organization_link_status", "published_at", "modified_at",
        "event_at", "expires_at", "independence_key", "syndication_group_key",
        "active", "historical_only", "supersedes_record_key",
    )


def _mapping_indexes() -> tuple[str, ...]:
    return ("event_id", "service_family")


def _index_name(table_name: str, column: str) -> str:
    prefixes = {
        "corporate_change_events": "change_events",
        "corporate_change_claim_snapshots": "change_claims",
        "corporate_change_service_mappings": "change_services",
    }
    return f"ix_{prefixes[table_name]}_{column}"


def _create_indexes(table_name: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(_index_name(table_name, column), table_name, [column])


def _drop_indexes(table_name: str, columns: tuple[str, ...]) -> None:
    for column in reversed(columns):
        op.drop_index(_index_name(table_name, column), table_name=table_name)
