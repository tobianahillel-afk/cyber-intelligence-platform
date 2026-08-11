from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from cip.modules.opportunities.application.hypothesis_views import NeedHypothesisView


class SourceContributionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    independence_key: str
    polarity: str
    signal_ids: tuple[UUID, ...]
    max_confidence: float = Field(ge=0.0, le=1.0)
    contribution: float = Field(ge=-1.0, le=1.0)


class NeedHypothesisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    organization_id: UUID
    organization: str
    family: str
    status: str
    hypothesis_class: str
    service_families: tuple[str, ...]
    confidence: float = Field(ge=0.0, le=1.0)
    urgency: str
    horizon: str
    rationale: str
    applicable_offers: tuple[str, ...]
    signal_ids: tuple[UUID, ...]
    evidence_ids: tuple[UUID, ...]
    conflicting_signal_ids: tuple[UUID, ...]
    negative_signal_ids: tuple[UUID, ...]
    source_contributions: tuple[SourceContributionResponse, ...]
    rule_id: str
    rule_version: str
    taxonomy_version: str
    generated_at: datetime
    expires_at: datetime

    @classmethod
    def from_view(cls, view: NeedHypothesisView) -> NeedHypothesisResponse:
        return cls(
            id=view.id,
            organization_id=view.organization_id,
            organization=view.organization,
            family=view.family,
            status=view.status,
            hypothesis_class=view.hypothesis_class,
            service_families=view.service_families,
            confidence=view.confidence,
            urgency=view.urgency,
            horizon=view.horizon,
            rationale=view.rationale,
            applicable_offers=view.applicable_offers,
            signal_ids=view.signal_ids,
            evidence_ids=view.evidence_ids,
            conflicting_signal_ids=view.conflicting_signal_ids,
            negative_signal_ids=view.negative_signal_ids,
            source_contributions=tuple(
                SourceContributionResponse(
                    independence_key=item.independence_key,
                    polarity=item.polarity,
                    signal_ids=item.signal_ids,
                    max_confidence=item.max_confidence,
                    contribution=item.contribution,
                )
                for item in view.source_contributions
            ),
            rule_id=view.rule_id,
            rule_version=view.rule_version,
            taxonomy_version=view.taxonomy_version,
            generated_at=view.generated_at,
            expires_at=view.expires_at,
        )


class NeedHypothesisListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: tuple[NeedHypothesisResponse, ...]


class NeedHypothesisRecomputeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: UUID
    hypothesis_ids: tuple[UUID, ...]
    generated_count: int = Field(ge=0)
