from __future__ import annotations

from fastapi import FastAPI

from cip import __version__
from cip.modules.opportunities.api.routes import router as opportunities_router
from cip.modules.organizations.api.routes import router as organizations_router
from cip.modules.provider_onboarding.api.routes import router as provider_onboarding_router
from cip.modules.source_governance.api.routes import router as source_governance_router


def create_app() -> FastAPI:
    application = FastAPI(
        title="Cyber Intelligence Platform",
        version=__version__,
        description=(
            "Standalone human-operated cyber revenue intelligence and commercial "
            "operations API with explicit source governance, provenance, official "
            "organization identity, provider onboarding, and evidence-backed "
            "opportunity discovery."
        ),
    )
    application.include_router(source_governance_router)
    application.include_router(provider_onboarding_router)
    application.include_router(organizations_router)
    application.include_router(opportunities_router)

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": application.version}

    return application


app = create_app()
