from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from cip.adapters.sources.organization_identity.registry import OrganizationIdentityTarget
from cip.modules.collection_orchestration.application.brreg_identity_adapter import (
    BrregIdentityAdapter,
)
from cip.modules.organizations.domain.identifiers import IdentifierScheme
from cip.modules.source_governance.infrastructure.registry import load_source_registry

POLICY_PATH = Path("policies/sources.company_identity_expansion.yml")
VALIDATION_ORG_NUMBER = "974760673"


def main() -> None:
    entry = next(
        item
        for item in load_source_registry(POLICY_PATH)
        if item.policy.id == "brreg-enhetsregisteret"
    )
    target = OrganizationIdentityTarget(
        id="brreg-source-operator-live-validation",
        organization_id=UUID("7f3ea686-13c2-5c32-9a20-d3ed5c6fab2c"),
        canonical_name="Brønnøysundregistrene",
        country_code="NO",
        query="Brønnøysundregistrene",
        foreign_registration=VALIDATION_ORG_NUMBER,
        enabled=True,
    )
    now = datetime.now(UTC)
    batch = BrregIdentityAdapter(entry, (target,), timeout_seconds=30).collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=now,
        retention_until=now + timedelta(days=365),
    )
    if len(batch.observations) != 1 or len(batch.identity_projections) != 1:
        raise RuntimeError("BRREG live validation did not return one canonical entity")
    projection = batch.identity_projections[0]
    identifiers = projection.identity.identifiers
    if not identifiers or identifiers[0].scheme is not IdentifierScheme.FOREIGN_REGISTRATION:
        raise RuntimeError("BRREG live validation lost the official organisation identifier")
    if identifiers[0].value != VALIDATION_ORG_NUMBER:
        raise RuntimeError("BRREG live validation returned an unexpected organisation")
    if projection.attached_organization is None:
        raise RuntimeError("BRREG exact identifier did not auto-attach validation target")
    if batch.not_modified:
        raise RuntimeError("BRREG first live collection unexpectedly reported not-modified")
    print(
        "SA-11 BRREG live validation passed: "
        f"observations={len(batch.observations)} "
        f"identity_projections={len(batch.identity_projections)}"
    )


if __name__ == "__main__":
    main()
