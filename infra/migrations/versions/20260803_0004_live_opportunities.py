"""Create live opportunity pipeline tables.

Revision ID: 20260803_0004
Revises: 20260803_0003
Create Date: 2026-08-03
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260803_0004"
down_revision: str | Sequence[str] | None = "20260803_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _create_signals()
    _create_hypotheses()
    _create_opportunities()
    _create_score_components()
    _create_evidence_links()
    _create_reviews()


def _create_signals() -> None:
    op.create_table(
        "commercial_signals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("signal_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("matched_terms", sa.JSON(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_commercial_signals_idempotency_key"
        ),
    )
    op.create_index("ix_commercial_signals_organization_id", "commercial_signals", ["organization_id"])
    op.create_index("ix_commercial_signals_evidence_id", "commercial_signals", ["evidence_id"])
    op.create_index("ix_commercial_signals_signal_type", "commercial_signals", ["signal_type"])
    op.create_index("ix_commercial_signals_collected_at", "commercial_signals", ["collected_at"])
    op.create_index("ix_commercial_signals_expires_at", "commercial_signals", ["expires_at"])
    op.create_index(
        "ix_commercial_signals_org_type_effective",
        "commercial_signals",
        ["organization_id", "signal_type", "published_at", "collected_at"],
    )


def _create_hypotheses() -> None:
    op.create_table(
        "need_hypotheses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("family", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rule_id", sa.String(length=100), nullable=False),
        sa.Column("rule_version", sa.String(length=50), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_need_hypotheses_idempotency_key"
        ),
    )
    op.create_index("ix_need_hypotheses_organization_id", "need_hypotheses", ["organization_id"])
    op.create_index("ix_need_hypotheses_family", "need_hypotheses", ["family"])
    op.create_index("ix_need_hypotheses_status", "need_hypotheses", ["status"])
    op.create_index("ix_need_hypotheses_generated_at", "need_hypotheses", ["generated_at"])
    op.create_index("ix_need_hypotheses_expires_at", "need_hypotheses", ["expires_at"])
    op.create_index(
        "ix_need_hypotheses_org_family",
        "need_hypotheses",
        ["organization_id", "family"],
    )
    op.create_table(
        "need_hypothesis_signals",
        sa.Column("hypothesis_id", sa.Uuid(), nullable=False),
        sa.Column("signal_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["hypothesis_id"], ["need_hypotheses.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"], ["commercial_signals.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("hypothesis_id", "signal_id"),
    )


def _create_opportunities() -> None:
    op.create_table(
        "opportunities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("hypothesis_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("recommended_offer", sa.String(length=500), nullable=False),
        sa.Column("relevant_roles", sa.JSON(), nullable=False),
        sa.Column("trigger_summary", sa.Text(), nullable=False),
        sa.Column("next_action", sa.String(length=500), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("raw_score", sa.Float(), nullable=False),
        sa.Column("adjusted_score", sa.Float(), nullable=False),
        sa.Column("score_version", sa.String(length=50), nullable=False),
        sa.Column("config_version", sa.String(length=100), nullable=False),
        sa.Column("calculation_hash", sa.String(length=64), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_evidence_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_quality", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("rejected_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["hypothesis_id"], ["need_hypotheses.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hypothesis_id", name="uq_opportunities_hypothesis_id"),
    )
    op.create_index("ix_opportunities_organization_id", "opportunities", ["organization_id"])
    op.create_index("ix_opportunities_state", "opportunities", ["state"])
    op.create_index("ix_opportunities_adjusted_score", "opportunities", ["adjusted_score"])
    op.create_index("ix_opportunities_calculation_hash", "opportunities", ["calculation_hash"])
    op.create_index("ix_opportunities_expires_at", "opportunities", ["expires_at"])
    op.create_index("ix_opportunities_last_evidence_at", "opportunities", ["last_evidence_at"])
    op.create_index("ix_opportunities_data_quality", "opportunities", ["data_quality"])
    op.create_index("ix_opportunities_updated_at", "opportunities", ["updated_at"])
    op.create_index("ix_opportunities_snoozed_until", "opportunities", ["snoozed_until"])
    op.create_index(
        "ix_opportunities_priority",
        "opportunities",
        ["state", "adjusted_score", "last_evidence_at"],
    )
    op.create_index(
        "ix_opportunities_org_updated",
        "opportunities",
        ["organization_id", "updated_at"],
    )


def _create_score_components() -> None:
    op.create_table(
        "opportunity_score_components",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("contribution", sa.Float(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("analyst_overridden", sa.Boolean(), nullable=False),
        sa.Column("original_value", sa.Float(), nullable=True),
        sa.Column("original_weight", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "opportunity_id", "rule_id", name="uq_opportunity_component_rule"
        ),
    )
    op.create_index(
        "ix_opportunity_score_components_opportunity_id",
        "opportunity_score_components",
        ["opportunity_id"],
    )


def _create_evidence_links() -> None:
    op.create_table(
        "opportunity_evidence",
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["evidence_id"], ["evidence.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("opportunity_id", "evidence_id"),
    )


def _create_reviews() -> None:
    op.create_table(
        "opportunity_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("previous_state", sa.String(length=32), nullable=False),
        sa.Column("new_state", sa.String(length=32), nullable=False),
        sa.Column("actor", sa.String(length=200), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opportunity_reviews_opportunity_id", "opportunity_reviews", ["opportunity_id"])
    op.create_index("ix_opportunity_reviews_action", "opportunity_reviews", ["action"])
    op.create_index("ix_opportunity_reviews_actor", "opportunity_reviews", ["actor"])
    op.create_index("ix_opportunity_reviews_occurred_at", "opportunity_reviews", ["occurred_at"])
    op.create_index(
        "ix_opportunity_reviews_history",
        "opportunity_reviews",
        ["opportunity_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_opportunity_reviews_history", table_name="opportunity_reviews")
    op.drop_index("ix_opportunity_reviews_occurred_at", table_name="opportunity_reviews")
    op.drop_index("ix_opportunity_reviews_actor", table_name="opportunity_reviews")
    op.drop_index("ix_opportunity_reviews_action", table_name="opportunity_reviews")
    op.drop_index("ix_opportunity_reviews_opportunity_id", table_name="opportunity_reviews")
    op.drop_table("opportunity_reviews")
    op.drop_table("opportunity_evidence")
    op.drop_index(
        "ix_opportunity_score_components_opportunity_id",
        table_name="opportunity_score_components",
    )
    op.drop_table("opportunity_score_components")
    op.drop_index("ix_opportunities_org_updated", table_name="opportunities")
    op.drop_index("ix_opportunities_priority", table_name="opportunities")
    op.drop_index("ix_opportunities_snoozed_until", table_name="opportunities")
    op.drop_index("ix_opportunities_updated_at", table_name="opportunities")
    op.drop_index("ix_opportunities_data_quality", table_name="opportunities")
    op.drop_index("ix_opportunities_last_evidence_at", table_name="opportunities")
    op.drop_index("ix_opportunities_expires_at", table_name="opportunities")
    op.drop_index("ix_opportunities_calculation_hash", table_name="opportunities")
    op.drop_index("ix_opportunities_adjusted_score", table_name="opportunities")
    op.drop_index("ix_opportunities_state", table_name="opportunities")
    op.drop_index("ix_opportunities_organization_id", table_name="opportunities")
    op.drop_table("opportunities")
    op.drop_table("need_hypothesis_signals")
    op.drop_index("ix_need_hypotheses_org_family", table_name="need_hypotheses")
    op.drop_index("ix_need_hypotheses_expires_at", table_name="need_hypotheses")
    op.drop_index("ix_need_hypotheses_generated_at", table_name="need_hypotheses")
    op.drop_index("ix_need_hypotheses_status", table_name="need_hypotheses")
    op.drop_index("ix_need_hypotheses_family", table_name="need_hypotheses")
    op.drop_index("ix_need_hypotheses_organization_id", table_name="need_hypotheses")
    op.drop_table("need_hypotheses")
    op.drop_index(
        "ix_commercial_signals_org_type_effective",
        table_name="commercial_signals",
    )
    op.drop_index("ix_commercial_signals_expires_at", table_name="commercial_signals")
    op.drop_index("ix_commercial_signals_collected_at", table_name="commercial_signals")
    op.drop_index("ix_commercial_signals_signal_type", table_name="commercial_signals")
    op.drop_index("ix_commercial_signals_evidence_id", table_name="commercial_signals")
    op.drop_index("ix_commercial_signals_organization_id", table_name="commercial_signals")
    op.drop_table("commercial_signals")
