from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from cip.modules.passive_exposure.domain.models import (
    AttributionRisk,
    OrganizationLink,
    OrganizationLinkMethod,
    OrganizationLinkStatus,
    PassiveAsset,
    PassiveAssetKind,
    PassiveObservationKind,
    PassiveObservationSnapshot,
    PassiveObservationState,
)
from cip.modules.passive_exposure.domain.reconciliation import (
    reconcile_passive_snapshots,
)

NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)


def test_every_attribution_risk_prevents_automatic_exact_projection() -> None:
    for risk in AttributionRisk:
        organization_id = uuid4()
        snapshot = PassiveObservationSnapshot(
            source_id=f"provider-{risk.value}",
            source_record_key=f"record-{risk.value}",
            source_url=f"https://provider.example/records/{risk.value}",
            asset=PassiveAsset(PassiveAssetKind.HOSTNAME, "service.example.com"),
            observation_kind=PassiveObservationKind.PASSIVE_DNS,
            state=PassiveObservationState.CURRENT,
            observed_at=NOW,
            published_at=NOW,
            modified_at=NOW,
            confidence=0.8,
            organization_link=OrganizationLink(
                status=OrganizationLinkStatus.REVIEW_REQUIRED,
                method=OrganizationLinkMethod.PASSIVE_CORRELATION,
                confidence=0.7,
                organization_id=organization_id,
                reasons=(f"Provider reported {risk.value}",),
                attribution_risks=(risk,),
            ),
        )

        result = reconcile_passive_snapshots((snapshot,), at=NOW)[0]

        assert result.organization_link.status is OrganizationLinkStatus.REVIEW_REQUIRED
        assert result.organization_link.exact_organization_id is None
        assert result.organization_link.candidate_organization_ids == (organization_id,)
        assert result.attribution_risks == (risk,)
        assert result.can_support_exposure_conclusion is False
