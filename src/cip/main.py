from __future__ import annotations

from fastapi import FastAPI

from cip.compliance.source_policy import SourcePolicy

app = FastAPI(
    title="Cyber Intelligence Platform",
    version="0.1.0",
    description=(
        "Compliance-first API for public and licensed cyber intelligence, "
        "company research, and evidence-backed opportunity discovery."
    ),
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version}


@app.post("/v1/source-policies/validate", response_model=SourcePolicy, tags=["governance"])
def validate_source_policy(policy: SourcePolicy) -> SourcePolicy:
    """Validate a source configuration without persisting it."""

    return policy
