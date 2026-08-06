from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit

from cip.modules.passive_exposure.domain.asset_models import (
    OrganizationLink,
    PassiveAsset,
    TechnologyObservation,
)
from cip.modules.passive_exposure.domain.enums import (
    TERMINAL_STATES,
    PassiveObservationKind,
    PassiveObservationState,
    TechnologyEvidenceLevel,
)
from cip.modules.passive_exposure.domain.normalization import (
    normalize_port,
    normalize_protocol,
)
from cip.shared.kernel.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class PassiveObservationSnapshot:
    source_id: str
    source_record_key: str
    source_url: str
    asset: PassiveAsset
    observation_kind: PassiveObservationKind
    state: PassiveObservationState
    observed_at: datetime
    published_at: datetime
    modified_at: datetime
    confidence: float
    organization_link: OrganizationLink
    expires_at: datetime | None = None
    independence_key: str | None = None
    technology: TechnologyObservation | None = None
    port: int | None = None
    protocol: str | None = None
    active: bool = True
    historical_only: bool = False
    metadata_only: bool = True
    passive_only: bool = True
    active_probe_performed: bool = False
    credentials_used: bool = False
    access_control_bypassed: bool = False
    exploit_attempted: bool = False
    direct_validation_performed: bool = False
    vulnerability_applicability_assessed: bool = False
    exposure_verified: bool = False
    supersedes_record_key: str | None = None

    def __post_init__(self) -> None:
        source_id = _bounded(self.source_id, "source_id", maximum=200)
        source_record_key = _bounded(
            self.source_record_key,
            "source_record_key",
            maximum=500,
        )
        source_url = _normalize_source_url(self.source_url)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "source_record_key", source_record_key)
        object.__setattr__(self, "source_url", source_url)
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        _validate_safety_flags(self)
        _normalize_timestamps(self)
        if self.modified_at < self.published_at:
            raise ValueError("modified_at cannot precede published_at")
        if self.published_at < self.observed_at:
            raise ValueError("published_at cannot precede observed_at")
        if self.expires_at is not None and self.expires_at < self.observed_at:
            raise ValueError("expires_at cannot precede observed_at")
        if self.state in TERMINAL_STATES and self.active:
            raise ValueError("expired, retracted, or deleted observations cannot be active")
        if self.state is PassiveObservationState.HISTORICAL:
            if self.active:
                raise ValueError("historical observations cannot be active")
            if not self.historical_only:
                raise ValueError("historical observations must be historical-only")
        if self.historical_only and self.state is PassiveObservationState.CURRENT:
            raise ValueError("historical-only observations cannot be current")
        _normalize_service_fields(self)
        if self.observation_kind in {
            PassiveObservationKind.PRODUCT,
            PassiveObservationKind.VERSION,
            PassiveObservationKind.TECHNOLOGY_MENTION,
        } and self.technology is None:
            raise ValueError("technology observations require technology metadata")
        if (
            self.observation_kind is PassiveObservationKind.VERSION
            and (
                self.technology is None
                or self.technology.evidence_level
                is not TechnologyEvidenceLevel.OBSERVED_VERSION
            )
        ):
            raise ValueError("version observations require observed-version evidence")
        if self.independence_key is None:
            object.__setattr__(self, "independence_key", source_id)
        else:
            object.__setattr__(
                self,
                "independence_key",
                _bounded(self.independence_key, "independence_key", maximum=500),
            )
        if self.supersedes_record_key is not None:
            object.__setattr__(
                self,
                "supersedes_record_key",
                _bounded(
                    self.supersedes_record_key,
                    "supersedes_record_key",
                    maximum=500,
                ),
            )

    @property
    def observation_key(self) -> str:
        service = ""
        if self.port is not None and self.protocol is not None:
            service = f":{self.port}/{self.protocol}"
        return f"{self.asset.key}:{self.observation_kind.value}{service}"

    @property
    def can_support_exposure_conclusion(self) -> bool:
        return False


def _normalize_source_url(value: str) -> str:
    normalized = value.strip()
    parsed = urlsplit(normalized)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("source_url must be an absolute HTTPS URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("source_url cannot contain embedded credentials")
    return normalized


def _normalize_timestamps(snapshot: PassiveObservationSnapshot) -> None:
    for field_name in ("observed_at", "published_at", "modified_at", "expires_at"):
        value = getattr(snapshot, field_name)
        if value is not None:
            object.__setattr__(
                snapshot,
                field_name,
                require_aware_utc(value, field_name=field_name),
            )


def _normalize_service_fields(snapshot: PassiveObservationSnapshot) -> None:
    if snapshot.port is not None:
        object.__setattr__(snapshot, "port", normalize_port(snapshot.port))
    if snapshot.protocol is not None:
        object.__setattr__(snapshot, "protocol", normalize_protocol(snapshot.protocol))
    requires_service = snapshot.observation_kind in {
        PassiveObservationKind.PORT,
        PassiveObservationKind.SERVICE,
    }
    if requires_service and (snapshot.port is None or snapshot.protocol is None):
        raise ValueError("port and service observations require port and protocol")
    if (snapshot.port is None) != (snapshot.protocol is None):
        raise ValueError("port and protocol must be provided together")


def _validate_safety_flags(snapshot: PassiveObservationSnapshot) -> None:
    if not snapshot.metadata_only or not snapshot.passive_only:
        raise ValueError("passive exposure accepts passive metadata only")
    if any(
        (
            snapshot.active_probe_performed,
            snapshot.credentials_used,
            snapshot.access_control_bypassed,
            snapshot.exploit_attempted,
            snapshot.direct_validation_performed,
        )
    ):
        raise ValueError("active validation and access-control bypass are forbidden")
    if snapshot.vulnerability_applicability_assessed or snapshot.exposure_verified:
        raise ValueError("Lot 16 cannot assess vulnerability applicability or verify exposure")


def _bounded(value: str, field_name: str, *, maximum: int) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{field_name} must be between 1 and {maximum} characters")
    return normalized
