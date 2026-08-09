"""Create governed analyst research orchestration records.

Revision ID: 20260809_0023
Revises: 20260809_0022
Create Date: 2026-08-09
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0023"
down_revision: str | Sequence[str] | None = "20260809_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _create_plans()
    _create_plan_revisions()
    _create_steps()
    _create_plan_decisions()
    _create_step_decisions()
    _create_attempts()
    _create_results()


def downgrade() -> None:
    for table_name in reversed(_TABLES):
        _drop_indexes(table_name)
        op.drop_table(table_name)


def _create_plans() -> None:
    table = "research_plans"
    op.create_table(
        table,
        *_id_columns(),
        sa.Column("question", sa.String(1000), nullable=False),
        sa.Column("purpose", sa.String(300), nullable=False),
        sa.Column("data_category", sa.String(80), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        *_budget_columns(),
        *_scope_columns(),
        sa.Column("max_risk_level", sa.String(30), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_revision_key", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    _indexes(table, "purpose", "data_category", "state", "current_revision_key", "updated_at")


def _create_plan_revisions() -> None:
    table = "research_plan_revisions"
    op.create_table(
        table,
        *_id_columns(),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("revision_key", sa.String(64), nullable=False),
        sa.Column("question", sa.String(1000), nullable=False),
        sa.Column("purpose", sa.String(300), nullable=False),
        sa.Column("data_category", sa.String(80), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("budget", sa.JSON(), nullable=False),
        *_scope_columns(),
        sa.Column("max_risk_level", sa.String(30), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actor", sa.String(200), nullable=False),
        sa.Column("change_reason", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        _fk("plan_id", "research_plans.id", ondelete="CASCADE"),
        sa.UniqueConstraint("revision_key"),
    )
    _indexes(table, "plan_id", "state", "created_at")


def _create_steps() -> None:
    table = "research_steps"
    op.create_table(
        table,
        *_id_columns(),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("step_key", sa.String(150), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("tool_id", sa.String(150), nullable=False),
        sa.Column("mode", sa.String(40), nullable=False),
        sa.Column("purpose", sa.String(300), nullable=False),
        sa.Column("data_category", sa.String(80), nullable=False),
        sa.Column("estimated_cost", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(30), nullable=False),
        sa.Column("target_url", sa.String(2048), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=True),
        sa.Column("ingestion_path_id", sa.String(150), nullable=True),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        _fk("plan_id", "research_plans.id", ondelete="CASCADE"),
        sa.UniqueConstraint("plan_id", "step_key"),
        sa.UniqueConstraint("plan_id", "sequence"),
    )
    _indexes(table, "plan_id", "step_key", "sequence", "source_id", "tool_id", "mode", "state")


def _create_plan_decisions() -> None:
    table = "research_plan_decisions"
    op.create_table(
        table,
        *_id_columns(),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("decision_key", sa.String(64), nullable=False),
        sa.Column("decision_type", sa.String(40), nullable=False),
        sa.Column("actor", sa.String(200), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("previous_state", sa.String(40), nullable=False),
        sa.Column("resulting_state", sa.String(40), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        _fk("plan_id", "research_plans.id", ondelete="CASCADE"),
        sa.UniqueConstraint("decision_key"),
    )
    _indexes(table, "plan_id", "decision_type", "resulting_state", "decided_at")


def _create_step_decisions() -> None:
    table = "research_step_decisions"
    op.create_table(
        table,
        *_id_columns(),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("step_id", sa.Uuid(), nullable=False),
        sa.Column("decision_key", sa.String(64), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.Column("next_state", sa.String(40), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("usage_snapshot", sa.JSON(), nullable=False),
        sa.Column("runtime_snapshot", sa.JSON(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        _fk("plan_id", "research_plans.id", ondelete="CASCADE"),
        _fk("step_id", "research_steps.id", ondelete="CASCADE"),
        sa.UniqueConstraint("decision_key"),
    )
    _indexes(table, "plan_id", "step_id", "allowed", "next_state", "evaluated_at")


def _create_attempts() -> None:
    table = "research_step_attempts"
    op.create_table(
        table,
        *_id_columns(),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("step_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_key", sa.String(64), nullable=False),
        sa.Column("mode", sa.String(40), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("actor", sa.String(200), nullable=False),
        sa.Column("external_action_started", sa.Boolean(), nullable=False),
        sa.Column("external_action_reference", sa.String(500), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        _fk("plan_id", "research_plans.id", ondelete="CASCADE"),
        _fk("step_id", "research_steps.id", ondelete="CASCADE"),
        sa.UniqueConstraint("attempt_key"),
    )
    _indexes(table, "plan_id", "step_id", "mode", "state", "started_at", "updated_at")


def _create_results() -> None:
    table = "research_results"
    op.create_table(
        table,
        *_id_columns(),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("step_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=True),
        sa.Column("result_key", sa.String(64), nullable=False),
        sa.Column("result_type", sa.String(60), nullable=False),
        sa.Column("evidence_reference", sa.String(500), nullable=False),
        sa.Column("provenance_reference", sa.String(500), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("summary", sa.String(1000), nullable=True),
        sa.Column("recorded_by", sa.String(200), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        _fk("plan_id", "research_plans.id", ondelete="CASCADE"),
        _fk("step_id", "research_steps.id", ondelete="CASCADE"),
        _fk("attempt_id", "research_step_attempts.id", ondelete="SET NULL"),
        sa.UniqueConstraint("result_key"),
    )
    _indexes(table, "plan_id", "step_id", "attempt_id", "result_type", "source_id", "recorded_at")


def _id_columns() -> tuple[sa.Column, ...]:
    return (sa.Column("id", sa.Uuid(), nullable=False), sa.PrimaryKeyConstraint("id"))


def _budget_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("max_steps", sa.Integer(), nullable=False),
        sa.Column("max_automated_steps", sa.Integer(), nullable=False),
        sa.Column("max_total_cost", sa.Float(), nullable=False),
        sa.Column("max_step_cost", sa.Float(), nullable=False),
    )


def _scope_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("allowed_source_ids", sa.JSON(), nullable=False),
        sa.Column("allowed_tool_ids", sa.JSON(), nullable=False),
        sa.Column("approved_step_keys", sa.JSON(), nullable=False),
        sa.Column("allowed_hosts", sa.JSON(), nullable=False),
        sa.Column("allowed_path_prefixes", sa.JSON(), nullable=False),
    )


def _fk(column: str, target: str, *, ondelete: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint([column], [target], ondelete=ondelete)


def _indexes(table_name: str, *columns: str) -> None:
    for column in columns:
        op.create_index(_index_name(table_name, column), table_name, [column])


def _drop_indexes(table_name: str) -> None:
    for column in reversed(_INDEXES[table_name]):
        op.drop_index(_index_name(table_name, column), table_name=table_name)


def _index_name(table_name: str, column: str) -> str:
    return f"ix_{_PREFIXES[table_name]}_{column}"


_TABLES = (
    "research_plans",
    "research_plan_revisions",
    "research_steps",
    "research_plan_decisions",
    "research_step_decisions",
    "research_step_attempts",
    "research_results",
)
_PREFIXES = {
    "research_plans": "research_plan",
    "research_plan_revisions": "research_revision",
    "research_steps": "research_step",
    "research_plan_decisions": "research_pd",
    "research_step_decisions": "research_sd",
    "research_step_attempts": "research_attempt",
    "research_results": "research_result",
}
_INDEXES = {
    "research_plans": ("purpose", "data_category", "state", "current_revision_key", "updated_at"),
    "research_plan_revisions": ("plan_id", "state", "created_at"),
    "research_steps": ("plan_id", "step_key", "sequence", "source_id", "tool_id", "mode", "state"),
    "research_plan_decisions": ("plan_id", "decision_type", "resulting_state", "decided_at"),
    "research_step_decisions": ("plan_id", "step_id", "allowed", "next_state", "evaluated_at"),
    "research_step_attempts": ("plan_id", "step_id", "mode", "state", "started_at", "updated_at"),
    "research_results": ("plan_id", "step_id", "attempt_id", "result_type", "source_id", "recorded_at"),
}
