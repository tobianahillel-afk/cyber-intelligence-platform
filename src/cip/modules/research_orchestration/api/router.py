from __future__ import annotations

from fastapi import APIRouter, Depends

from cip.modules.research_orchestration.api.plan_routes import router as plan_router
from cip.modules.research_orchestration.api.step_routes import router as step_router
from cip.modules.source_portfolio.api.dependencies import require_control_plane

router = APIRouter(
    prefix="/v1/research",
    tags=["research"],
    dependencies=[Depends(require_control_plane)],
)
router.include_router(plan_router)
router.include_router(step_router)
