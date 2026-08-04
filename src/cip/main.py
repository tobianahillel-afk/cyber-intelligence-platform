from __future__ import annotations

from fastapi import FastAPI

from cip.modules.opportunities.api.routes import router as opportunities_router
from cip.modules.source_governance.api.routes import router as source_governance_router


def create_app() -> FastAPI:
    application = FastAPI(
        title="Cyber Intelligence Platform",
        version="0.7.0",
        description=(
            "Human-operated cyber revenue intelligence API with explicit source governance, "
            "provenance, and evidence-backed opportunity discovery."
        ),
    )
    application.include_router(source_governance_router)
    application.include_router(opportunities_router)

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": application.version}

    return application


app = create_app()
