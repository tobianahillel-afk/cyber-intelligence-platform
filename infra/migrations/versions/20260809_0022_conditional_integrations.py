"""Create conditional provider approval and execution audit records.

Revision ID: 20260809_0022
Revises: 20260809_0021
Create Date: 2026-08-09
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0022"
down_revision: str | Sequence[str] | None = "20260809_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _create_approvals()
    _create_approval_revisions()
    _create_runtime_controls()
    _create_control_decisions()
    _create_execution_decisions()


def downgrade() -> None:
    for table_name in reversed(_TABLES):
        _drop_indexes(table_name)
        op.drop_table(table_name)


def _create_approvals() -> None:
    table = "conditional_provider_approvals"
    op.create_table(
        table,
        *_identity_columns(),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("provider_kind", sa.String(40), nullable=False),
        sa.Column("access_method", sa.String(60), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        *_approval_reference_columns(),
        *_approval_scope_columns(),
        *_approval_time_columns(),
        sa.Column("paused_reason", sa.String(500), nullable=True),
        sa.Column("current_revision_key", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_id"),
    )
    _indexes(
        table,
        "source_id",
        "provider_kind",
        "access_method",
        "state",
        "terms_state",
        "current_revision_key",
    )


def _create_approval_revisions() -> None:
    table = "conditional_provider_approval_revisions"
    op.create_table(
        table,
        *_identity_columns(),
        sa.Column("approval_id", sa.Uuid(), nullable=False),
        sa.Column("revision_key", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("provider_kind", sa.String(40), nullable=False),
        sa.Column("access_method", sa.String(60), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        *_approval_reference_columns(),
        *_approval_scope_columns(),
        *_approval_time_columns(),
        sa.Column("paused_reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        _fk("approval_id", "conditional_provider_approvals.id", ondelete="CASCADE"),
        sa.UniqueConstraint("revision_key"),
    )
    _indexes(
        table,
        "approval_id",
        "source_id",
        "provider_kind",
        "access_method",
        "state",
        "terms_state",
        "created_at",
    )


def _create_runtime_controls() -> None:
    table = "conditional_provider_runtime_controls"
    op.create_table(
        table,
        *_identity_columns(),
        sa.Column("approval_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("paused", sa.Boolean(), nullable=False),
        sa.Column("kill_switch_active", sa.Boolean(), nullable=False),
        sa.Column("paused_reason", sa.String(1000), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        _fk("approval_id", "conditional_provider_approvals.id", ondelete="CASCADE"),
        sa.UniqueConstraint("approval_id"),
        sa.UniqueConstraint("source_id"),
    )
    _indexes(table, "source_id", "paused", "kill_switch_active", "updated_at")


def _create_control_decisions() -> None:
    table = "conditional_provider_control_decisions"
    op.create_table(
        table,
        *_identity_columns(),
        sa.Column("control_id", sa.Uuid(), nullable=False),
        sa.Column("decision_key", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("actor", sa.String(200), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("resulting_paused", sa.Boolean(), nullable=False),
        sa.Column("resulting_kill_switch_active", sa.Boolean(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        _fk(
            "control_id",
            "conditional_provider_runtime_controls.id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("decision_key"),
    )
    _indexes(table, "control_id", "source_id", "action", "decided_at")


def _create_execution_decisions() -> None:
    table = "conditional_execution_decisions"
    op.create_table(
        table,
        *_identity_columns(),
        sa.Column("approval_id", sa.Uuid(), nullable=False),
        sa.Column("decision_key", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("access_method", sa.String(60), nullable=False),
        sa.Column("purpose", sa.String(300), nullable=False),
        sa.Column("data_category", sa.String(80), nullable=False),
        sa.Column("requested_scopes", sa.JSON(), nullable=False),
        sa.Column("requested_fields", sa.JSON(), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("automated", sa.Boolean(), nullable=False),
        sa.Column("account_reference", sa.String(500), nullable=True),
        sa.Column("onboarding_state", sa.String(60), nullable=False),
        sa.Column("source_policy_allowed", sa.Boolean(), nullable=False),
        sa.Column("adapter_capability_present", sa.Boolean(), nullable=False),
        sa.Column("provider_paused", sa.Boolean(), nullable=False),
        sa.Column("kill_switch_active", sa.Boolean(), nullable=False),
        sa.Column("quota_remaining", sa.Integer(), nullable=True),
        sa.Column("monthly_cost_used", sa.Float(), nullable=False),
        sa.Column("monthly_cost_limit", sa.Float(), nullable=True),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        _fk("approval_id", "conditional_provider_approvals.id", ondelete="CASCADE"),
        sa.UniqueConstraint("decision_key"),
    )
    _indexes(
        table,
        "approval_id",
        "source_id",
        "access_method",
        "purpose",
        "data_category",
        "onboarding_state",
        "allowed",
        "evaluated_at",
    )


def _identity_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def _approval_reference_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("authorization_document_reference", sa.String(500), nullable=True),
        sa.Column("licence_reference", sa.String(500), nullable=True),
        sa.Column("terms_reference", sa.String(500), nullable=True),
        sa.Column("terms_state", sa.String(40), nullable=False),
    )


def _approval_scope_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("approved_scopes", sa.JSON(), nullable=False),
        sa.Column("approved_fields", sa.JSON(), nullable=False),
        sa.Column("approved_purposes", sa.JSON(), nullable=False),
        sa.Column("approved_data_categories", sa.JSON(), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=True),
        sa.Column("automated_collection_allowed", sa.Boolean(), nullable=False),
        sa.Column("account_reference", sa.String(500), nullable=True),
    )


def _approval_time_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
    "conditional_provider_approvals",
    "conditional_provider_approval_revisions",
    "conditional_provider_runtime_controls",
    "conditional_provider_control_decisions",
    "conditional_execution_decisions",
)

_PREFIXES = {
    "conditional_provider_approvals": "cp_approval",
    "conditional_provider_approval_revisions": "cp_revision",
    "conditional_provider_runtime_controls": "cp_control",
    "conditional_provider_control_decisions": "cp_cd",
    "conditional_execution_decisions": "cp_exec",
}

_INDEXES = {
    "conditional_provider_approvals": (
        "source_id",
        "provider_kind",
        "access_method",
        "state",
        "terms_state",
        "current_revision_key",
    ),
    "conditional_provider_approval_revisions": (
        "approval_id",
        "source_id",
        "provider_kind",
        "access_method",
        "state",
        "terms_state",
        "created_at",
    ),
    "conditional_provider_runtime_controls": (
        "source_id",
        "paused",
        "kill_switch_active",
        "updated_at",
    ),
    "conditional_provider_control_decisions": (
        "control_id",
        "source_id",
        "action",
        "decided_at",
    ),
    "conditional_execution_decisions": (
        "approval_id",
        "source_id",
        "access_method",
        "purpose",
        "data_category",
        "onboarding_state",
        "allowed",
        "evaluated_at",
    ),
}
