"""Create temporal corporate knowledge graph and entity-resolution records.

Revision ID: 20260808_0020
Revises: 20260807_0019
Create Date: 2026-08-08
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260808_0020"
down_revision: str | Sequence[str] | None = "20260807_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _create_nodes()
    _create_node_snapshots()
    _create_edges()
    _create_edge_snapshots()
    _create_resolution_candidates()
    _create_resolution_decisions()
    _create_resolution_bindings()


def downgrade() -> None:
    for table_name in (
        "entity_resolution_bindings",
        "entity_resolution_decisions",
        "entity_resolution_candidates",
        "corporate_graph_edge_snapshots",
        "corporate_graph_edges",
        "corporate_graph_node_snapshots",
        "corporate_graph_nodes",
    ):
        _drop_indexes(table_name)
        op.drop_table(table_name)


def _create_nodes() -> None:
    op.create_table(
        "corporate_graph_nodes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("node_key", sa.String(length=500), nullable=False),
        sa.Column("node_type", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=500), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("current", sa.Boolean(), nullable=False),
        sa.Column("suppressed", sa.Boolean(), nullable=False),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("node_key"),
    )
    _indexes("corporate_graph_nodes", "node_key", "node_type", "organization_id", "current")


def _create_node_snapshots() -> None:
    op.create_table(
        "corporate_graph_node_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("node_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_key", sa.String(length=64), nullable=False),
        sa.Column("node_key", sa.String(length=500), nullable=False),
        sa.Column("node_type", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=500), nullable=False),
        sa.Column("source_module", sa.String(length=100), nullable=False),
        sa.Column("source_entity_type", sa.String(length=100), nullable=False),
        sa.Column("source_record_key", sa.String(length=500), nullable=False),
        sa.Column("source_entity_id", sa.Uuid(), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("source_url", sa.String(length=2_048), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("suppressed", sa.Boolean(), nullable=False),
        sa.Column("metadata_only", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["corporate_graph_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_key", name="uq_corporate_graph_node_snapshot"),
    )
    _indexes(
        "corporate_graph_node_snapshots",
        "node_id",
        "node_key",
        "source_module",
        "source_record_key",
        "organization_id",
        "observed_at",
    )


def _create_edges() -> None:
    op.create_table(
        "corporate_graph_edges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("edge_key", sa.String(length=500), nullable=False),
        sa.Column("source_node_key", sa.String(length=500), nullable=False),
        sa.Column("target_node_key", sa.String(length=500), nullable=False),
        sa.Column("edge_type", sa.String(length=80), nullable=False),
        sa.Column("source_module", sa.String(length=100), nullable=False),
        sa.Column("source_evidence_class", sa.String(length=100), nullable=False),
        sa.Column("review_state", sa.String(length=80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("current", sa.Boolean(), nullable=False),
        sa.Column("suppressed", sa.Boolean(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_node_key"], ["corporate_graph_nodes.node_key"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_node_key"], ["corporate_graph_nodes.node_key"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("edge_key"),
    )
    _indexes(
        "corporate_graph_edges",
        "edge_key",
        "source_node_key",
        "target_node_key",
        "edge_type",
        "current",
        "review_state",
    )


def _create_edge_snapshots() -> None:
    op.create_table(
        "corporate_graph_edge_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("edge_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_key", sa.String(length=64), nullable=False),
        sa.Column("edge_key", sa.String(length=500), nullable=False),
        sa.Column("source_node_key", sa.String(length=500), nullable=False),
        sa.Column("target_node_key", sa.String(length=500), nullable=False),
        sa.Column("edge_type", sa.String(length=80), nullable=False),
        sa.Column("source_module", sa.String(length=100), nullable=False),
        sa.Column("source_record_key", sa.String(length=500), nullable=False),
        sa.Column("source_evidence_class", sa.String(length=100), nullable=False),
        sa.Column("claim_type", sa.String(length=80), nullable=False),
        sa.Column("review_state", sa.String(length=80), nullable=False),
        sa.Column("source_url", sa.String(length=2_048), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("suppressed", sa.Boolean(), nullable=False),
        sa.Column("supersedes_record_key", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["edge_id"], ["corporate_graph_edges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_key", name="uq_corporate_graph_edge_snapshot"),
    )
    _indexes(
        "corporate_graph_edge_snapshots",
        "edge_id",
        "edge_key",
        "source_module",
        "source_record_key",
        "claim_type",
        "observed_at",
    )


def _create_resolution_candidates() -> None:
    op.create_table(
        "entity_resolution_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("node_key", sa.String(length=500), nullable=False),
        sa.Column("candidate_organization_id", sa.Uuid(), nullable=False),
        sa.Column("method", sa.String(length=80), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reasons_json", sa.Text(), nullable=False),
        sa.Column("conflicting_organization_ids_json", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=80), nullable=False),
        sa.Column("requires_review", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["node_key"], ["corporate_graph_nodes.node_key"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["candidate_organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "node_key",
            "candidate_organization_id",
            "method",
            name="uq_entity_resolution_candidate_identity",
        ),
    )
    _indexes(
        "entity_resolution_candidates",
        "node_key",
        "candidate_organization_id",
        "state",
        "requires_review",
    )


def _create_resolution_decisions() -> None:
    op.create_table(
        "entity_resolution_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("node_key", sa.String(length=500), nullable=False),
        sa.Column("decision_type", sa.String(length=80), nullable=False),
        sa.Column("actor", sa.String(length=200), nullable=False),
        sa.Column("reason", sa.String(length=1_000), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("reverses_decision_id", sa.Uuid(), nullable=True),
        sa.Column("blast_radius_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["entity_resolution_candidates.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["reverses_decision_id"], ["entity_resolution_decisions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    _indexes(
        "entity_resolution_decisions",
        "candidate_id",
        "node_key",
        "decision_type",
        "organization_id",
        "decided_at",
    )


def _create_resolution_bindings() -> None:
    op.create_table(
        "entity_resolution_bindings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("node_key", sa.String(length=500), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=True),
        sa.Column("decision_id", sa.Uuid(), nullable=True),
        sa.Column("method", sa.String(length=80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("current", sa.Boolean(), nullable=False),
        sa.Column("bound_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["node_key"], ["corporate_graph_nodes.node_key"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["entity_resolution_candidates.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["decision_id"], ["entity_resolution_decisions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("node_key"),
    )
    _indexes("entity_resolution_bindings", "node_key", "organization_id", "current")


def _indexes(table_name: str, *columns: str) -> None:
    for column in columns:
        op.create_index(_index_name(table_name, column), table_name, [column])


def _drop_indexes(table_name: str) -> None:
    indexes = {
        "corporate_graph_nodes": ("node_key", "node_type", "organization_id", "current"),
        "corporate_graph_node_snapshots": (
            "node_id",
            "node_key",
            "source_module",
            "source_record_key",
            "organization_id",
            "observed_at",
        ),
        "corporate_graph_edges": (
            "edge_key",
            "source_node_key",
            "target_node_key",
            "edge_type",
            "current",
            "review_state",
        ),
        "corporate_graph_edge_snapshots": (
            "edge_id",
            "edge_key",
            "source_module",
            "source_record_key",
            "claim_type",
            "observed_at",
        ),
        "entity_resolution_candidates": (
            "node_key",
            "candidate_organization_id",
            "state",
            "requires_review",
        ),
        "entity_resolution_decisions": (
            "candidate_id",
            "node_key",
            "decision_type",
            "organization_id",
            "decided_at",
        ),
        "entity_resolution_bindings": ("node_key", "organization_id", "current"),
    }
    for column in reversed(indexes[table_name]):
        op.drop_index(_index_name(table_name, column), table_name=table_name)


def _index_name(table_name: str, column: str) -> str:
    prefixes = {
        "corporate_graph_nodes": "cg_node",
        "corporate_graph_node_snapshots": "cg_ns",
        "corporate_graph_edges": "cg_edge",
        "corporate_graph_edge_snapshots": "cg_es",
        "entity_resolution_candidates": "er_candidate",
        "entity_resolution_decisions": "er_decision",
        "entity_resolution_bindings": "er_binding",
    }
    return f"ix_{prefixes[table_name]}_{column}"
