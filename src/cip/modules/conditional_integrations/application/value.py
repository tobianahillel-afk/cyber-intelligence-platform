from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from cip.modules.source_portfolio.application.value import (
    SourceValueSummary,
    summarize_source_value,
)


@dataclass(frozen=True, slots=True)
class ConditionalProviderValueSummary:
    source_id: str
    source: SourceValueSummary
    portfolio_without_source: SourceValueSummary

    @property
    def evidence_available(self) -> bool:
        return self.source.executions > 0


def summarize_conditional_provider_value(
    session: Session,
    source_id: str,
) -> ConditionalProviderValueSummary:
    normalized = source_id.strip()
    if not normalized:
        raise ValueError("source_id is required")
    return ConditionalProviderValueSummary(
        source_id=normalized,
        source=summarize_source_value(session, source_id=normalized),
        portfolio_without_source=summarize_source_value(
            session,
            excluded_source_id=normalized,
        ),
    )
