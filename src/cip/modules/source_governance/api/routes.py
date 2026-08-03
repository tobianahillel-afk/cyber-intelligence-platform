from __future__ import annotations

from fastapi import APIRouter, HTTPException

from cip.modules.source_governance.api.schemas import (
    CollectionDecisionOutput,
    SourceEvaluationInput,
    SourcePolicyInput,
)

router = APIRouter(prefix="/v1/source-governance", tags=["source-governance"])


@router.post("/policies/validate", response_model=SourcePolicyInput)
def validate_policy(payload: SourcePolicyInput) -> SourcePolicyInput:
    try:
        payload.to_domain()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return payload


@router.post("/evaluate", response_model=CollectionDecisionOutput)
def evaluate_collection(payload: SourceEvaluationInput) -> CollectionDecisionOutput:
    try:
        decision = payload.policy.to_domain().evaluate(
            payload.request.to_domain(),
            payload.authorization.to_domain(),
            payload.runtime.to_domain(),
            now=payload.now,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return CollectionDecisionOutput.from_domain(decision)
