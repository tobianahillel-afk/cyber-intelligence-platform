"""Add canonical signal-fusion and need-hypothesis fields.

Revision ID: 20260810_0024
Revises: 20260809_0023
Create Date: 2026-08-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0024"
down_revision: str | Sequence[str] | None = "20260809_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LEGACY_TO_CANONICAL = {
    "strategy_vciso": "security_strategy_vciso",
    "audit_risk_assessment": "risk_assessment_audit",
    "red_purple_teaming": "red_team_purple_team",
    "vulnerability_attack_surface": "vulnerability_management_asm",
    "soc_siem_mdr_xdr_soar": "soc_siem_mdr_detection",
    "resilience_crisis_readiness": "resilience_bcp_drp",
    "iam_iga_pam_zero_trust": "iam_pam_zero_trust",
    "cloud_container_security": "cloud_security",
    "appsec_devsecops": "application_security_devsecops",
    "network_sase_security": "network_security_sase",
    "data_protection": "data_security_privacy",
    "awareness_training": "security_awareness_training",
}


def upgrade() -> None:
    _add_signal_columns()
    _add_hypothesis_columns()
    _rewrite_service_family_ids(_LEGACY_TO_CANONICAL)


def downgrade() -> None:
    _rewrite_service_family_ids(
        {canonical: legacy for legacy, canonical in _LEGACY_TO_CANONICAL.items()}
    )
    _drop_hypothesis_columns()
    _drop_signal_columns()


def _add_signal_columns() -> None:
    table = "commercial_signals"
    op.add_column(
        table,
        sa.Column("service_families", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        table,
        sa.Column("hypothesis_classes", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(table, sa.Column("independence_key", sa.String(500), nullable=True))
    op.add_column(
        table, sa.Column("corroboration_group_key", sa.String(500), nullable=True)
    )
    op.add_column(
        table,
        sa.Column("polarity", sa.String(40), nullable=False, server_default="supporting"),
    )
    op.add_column(
        table, sa.Column("is_explicit", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column(
        table,
        sa.Column("historical_only", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        table,
        sa.Column(
            "mapping_rule_id", sa.String(100), nullable=False, server_default="legacy-signal"
        ),
    )
    op.add_column(
        table,
        sa.Column(
            "mapping_rule_version", sa.String(50), nullable=False, server_default="1.0.0"
        ),
    )
    op.create_index(
        "ix_commercial_signals_independence",
        table,
        ["organization_id", "independence_key"],
    )


def _add_hypothesis_columns() -> None:
    table = "need_hypotheses"
    op.add_column(
        table,
        sa.Column(
            "hypothesis_class",
            sa.String(80),
            nullable=False,
            server_default="research_only_weak_signal",
        ),
    )
    op.add_column(
        table,
        sa.Column("service_families", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        table, sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5")
    )
    op.add_column(
        table, sa.Column("urgency", sa.String(40), nullable=False, server_default="low")
    )
    op.add_column(
        table,
        sa.Column("horizon", sa.String(40), nullable=False, server_default="long_term"),
    )
    op.add_column(
        table,
        sa.Column("applicable_offers", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        table,
        sa.Column(
            "conflicting_signal_ids", sa.JSON(), nullable=False, server_default="[]"
        ),
    )
    op.add_column(
        table,
        sa.Column("negative_signal_ids", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        table,
        sa.Column("source_contributions", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        table,
        sa.Column("taxonomy_version", sa.String(40), nullable=False, server_default="2026.08"),
    )
    op.create_index(
        "ix_need_hypotheses_org_class",
        table,
        ["organization_id", "hypothesis_class"],
    )


def _drop_hypothesis_columns() -> None:
    table = "need_hypotheses"
    op.drop_index("ix_need_hypotheses_org_class", table_name=table)
    for column in reversed(
        (
            "hypothesis_class",
            "service_families",
            "confidence",
            "urgency",
            "horizon",
            "applicable_offers",
            "conflicting_signal_ids",
            "negative_signal_ids",
            "source_contributions",
            "taxonomy_version",
        )
    ):
        op.drop_column(table, column)


def _drop_signal_columns() -> None:
    table = "commercial_signals"
    op.drop_index("ix_commercial_signals_independence", table_name=table)
    for column in reversed(
        (
            "service_families",
            "hypothesis_classes",
            "independence_key",
            "corroboration_group_key",
            "polarity",
            "is_explicit",
            "historical_only",
            "mapping_rule_id",
            "mapping_rule_version",
        )
    ):
        op.drop_column(table, column)


def _rewrite_service_family_ids(mapping: dict[str, str]) -> None:
    for old, new in mapping.items():
        for table, column in (
            ("procurement_service_classifications", "family"),
            ("corporate_change_service_mappings", "service_family"),
        ):
            statement = sa.text(
                f"UPDATE {table} SET {column} = :new WHERE {column} = :old"
            )
            op.execute(statement.bindparams(old=old, new=new))
