from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from cip.modules.research_orchestration.api.source_schemas import (
    ResearchSourceOptionResponse,
    ResearchSourceOptionsResponse,
)
from cip.modules.research_orchestration.infrastructure.source_selection import (
    select_ranked_research_sources,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.shared.persistence.dependencies import get_database_session

router = APIRouter()
SessionDependency = Annotated[Session, Depends(get_database_session)]


@router.get("/source-options", response_model=ResearchSourceOptionsResponse)
def list_source_options(
    session: SessionDependency,
    purpose: Annotated[str, Query(min_length=1, max_length=300)] = "organization-research",
    data_category: DataCategory = DataCategory.ORGANIZATION_METADATA,
) -> ResearchSourceOptionsResponse:
    candidates = select_ranked_research_sources(
        session,
        purpose=purpose,
        data_category=data_category,
        now=datetime.now(UTC),
    )
    return ResearchSourceOptionsResponse(
        purpose=purpose,
        data_category=data_category.value,
        items=[
            ResearchSourceOptionResponse(
                rank=index,
                source_id=candidate.source_id,
                tool_id=candidate.tool_id,
                mode=candidate.mode.value,
                authorized=candidate.authorized,
                executable=candidate.executable,
                manual_link_allowed=candidate.manual_link_allowed,
                freshness_score=candidate.freshness_score,
                value_score=candidate.value_score,
                estimated_cost=candidate.estimated_cost,
                quota_remaining=candidate.quota_remaining,
                risk_level=candidate.risk_level.value,
            )
            for index, candidate in enumerate(candidates, start=1)
        ],
    )
