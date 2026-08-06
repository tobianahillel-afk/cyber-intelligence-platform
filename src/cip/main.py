from __future__ import annotations

from fastapi import FastAPI

from cip import __version__
from cip.modules.incident_intelligence.api.routes import router as incident_router
from cip.modules.opportunities.api.routes import router as opportunities_router
from cip.modules.organizations.api.routes import router as organizations_router
from cip.modules.procurement_history.api.routes import router as procurement_history_router
from cip.modules.provider_onboarding.api.routes import router as provider_onboarding_router
from cip.modules.public_footprint.api.routes import router as public_footprint_router
from cip.modules.source_governance.api.routes import router as source_governance_router
from cip.modules.source_portfolio.api.routes import router as source_portfolio_router
from cip.modules.vulnerability_knowledge.api.routes import router as vulnerability_router


def create_app() -> FastAPI:
    application = FastAPI(
        title="Cyber Intelligence Platform",
        version=__version__,
        description=(
            "Standalone human-operated cyber revenue intelligence and commercial "
            "operations API with explicit source governance, provenance, official "
            "organization identity, provider onboarding, source portfolio health, "
            "procurement contract history, public footprint evidence, canonical "
            "vulnerability knowledge, public incident intelligence, and "
            "evidence-backed opportunity discovery."
        ),
    )
    application.include_router(source_governance_router)
    application.include_router(provider_onboarding_router)
    application.include_router(source_portfolio_router)
    application.include_router(procurement_history_router)
    application.include_router(public_footprint_router)
    application.include_router(vulnerability_router)
    application.include_router(incident_router)
    application.include_router(organizations_router)
    application.include_router(opportunities_router)

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": application.version}

    return application


app = create_app()
