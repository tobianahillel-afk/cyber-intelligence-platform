from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from cip.modules.organizations.domain.identifiers import OfficialIdentifier
from cip.shared.kernel.time import require_aware_utc, utc_now


class IdentityKind(StrEnum):
    LEGAL_UNIT = "legal_unit"
    ESTABLISHMENT = "establishment"
    BRAND = "brand"
    GROUP = "group"


class IdentityStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"
    CEASED = "ceased"
    DISSOLVED = "dissolved"
    STRUCK_OFF = "struck_off"
    UNKNOWN = "unknown"


class RelationshipType(StrEnum):
    ESTABLISHMENT_OF = "establishment_of"
    HEADQUARTERS_OF = "headquarters_of"
    DIRECT_PARENT = "direct_parent"
    ULTIMATE_PARENT = "ultimate_parent"
    SUBSIDIARY_OF = "subsidiary_of"
    BRAND_OF = "brand_of"


class MatchMethod(StrEnum):
    EXACT_IDENTIFIER = "exact_identifier"
    EXACT_NAME_AND_POSTCODE = "exact_name_and_postcode"
    EXACT_NORMALIZED_NAME = "exact_normalized_name"
    CROSS_REGISTRY_CORROBORATION = "cross_registry_corroboration"
    CONFLICTING_IDENTIFIERS = "conflicting_identifiers"


class MatchState(StrEnum):
    AUTO_CONFIRMED = "auto_confirmed"
    NEEDS_REVIEW = "needs_review"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class OrganizationIdentity:
    kind: IdentityKind
    official_name: str
    country_code: str
    source_id: str
    source_record_key: str
    source_url: str
    confidence: float
    observed_at: datetime
    id: UUID = field(default_factory=uuid4)
    organization_id: UUID | None = None
    status: IdentityStatus = IdentityStatus.UNKNOWN
    identifiers: tuple[OfficialIdentifier, ...] = ()
    aliases: tuple[str, ...] = ()
    legal_form: str | None = None
    activity_code: str | None = None
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    is_headquarters: bool = False
    valid_from: date | None = None
    valid_until: date | None = None

    def __post_init__(self) -> None:
        _set_required_text(self, "official_name", maximum=300)
        _set_required_text(self, "source_id", maximum=100)
        _set_required_text(self, "source_record_key", maximum=500)
        country = self.country_code.strip().upper()
        if len(country) != 2 or not country.isalpha():
            raise ValueError("country_code must be an ISO alpha-2 code")
        object.__setattr__(self, "country_code", country)
        parsed = urlsplit(self.source_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("source_url must be an absolute HTTPS URL")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(
            self,
            "observed_at",
            require_aware_utc(self.observed_at, field_name="observed_at"),
        )
        aliases = _unique_text(self.aliases, maximum=300)
        official_key = self.official_name.casefold()
        if official_key in {alias.casefold() for alias in aliases}:
            aliases = tuple(
                alias for alias in aliases if alias.casefold() != official_key
            )
        object.__setattr__(self, "aliases", aliases)
        _validate_optional_text(self, "legal_form", maximum=300)
        _validate_optional_text(self, "activity_code", maximum=20)
        _validate_optional_text(self, "address", maximum=500)
        _validate_optional_text(self, "postal_code", maximum=20)
        _validate_optional_text(self, "city", maximum=200)
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("valid_until cannot precede valid_from")
        keys = [identifier.exact_key for identifier in self.identifiers]
        if len(keys) != len(set(keys)):
            raise ValueError("identity identifiers must be unique")

    @property
    def deterministic_key(self) -> str:
        if self.identifiers:
            return sorted(identifier.exact_key for identifier in self.identifiers)[0]
        return f"{self.source_id}:{self.source_record_key}"

    @classmethod
    def deterministic_id(cls, key: str) -> UUID:
        return uuid5(NAMESPACE_URL, f"organization-identity:{key}")


@dataclass(frozen=True, slots=True)
class IdentityRelationship:
    subject_identity_id: UUID
    object_identity_id: UUID
    relationship_type: RelationshipType
    source_id: str
    source_url: str
    confidence: float
    observed_at: datetime
    id: UUID = field(default_factory=uuid4)
    valid_from: date | None = None
    valid_until: date | None = None

    def __post_init__(self) -> None:
        if self.subject_identity_id == self.object_identity_id:
            raise ValueError("identity relationship cannot be self-referential")
        _set_required_text(self, "source_id", maximum=100)
        parsed = urlsplit(self.source_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("source_url must be an absolute HTTPS URL")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(
            self,
            "observed_at",
            require_aware_utc(self.observed_at, field_name="observed_at"),
        )
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("valid_until cannot precede valid_from")


@dataclass(frozen=True, slots=True)
class IdentityMergeCandidate:
    identity_id: UUID
    organization_id: UUID
    method: MatchMethod
    score: float
    reasons: tuple[str, ...]
    state: MatchState
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    review_note: str | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 1:
            raise ValueError("score must be between 0 and 1")
        reasons = _unique_text(self.reasons, maximum=500)
        if not reasons:
            raise ValueError("at least one match reason is required")
        object.__setattr__(self, "reasons", reasons)
        object.__setattr__(
            self,
            "created_at",
            require_aware_utc(self.created_at, field_name="created_at"),
        )
        if self.reviewed_at is not None:
            object.__setattr__(
                self,
                "reviewed_at",
                require_aware_utc(self.reviewed_at, field_name="reviewed_at"),
            )
        if (
            self.state is MatchState.AUTO_CONFIRMED
            and self.method is not MatchMethod.EXACT_IDENTIFIER
        ):
            raise ValueError("only exact identifier matches can be auto-confirmed")
        if self.state in {MatchState.CONFIRMED, MatchState.REJECTED}:
            if self.reviewed_at is None or not self.reviewed_by:
                raise ValueError("reviewed candidates require reviewer and timestamp")


def _set_required_text(instance: object, field_name: str, *, maximum: int) -> None:
    value = str(getattr(instance, field_name)).strip()
    if not value:
        raise ValueError(f"{field_name} is required")
    if len(value) > maximum:
        raise ValueError(f"{field_name} cannot exceed {maximum} characters")
    object.__setattr__(instance, field_name, value)


def _validate_optional_text(
    instance: object,
    field_name: str,
    *,
    maximum: int,
) -> None:
    value = getattr(instance, field_name)
    if value is None:
        return
    normalized = str(value).strip()
    if not normalized:
        object.__setattr__(instance, field_name, None)
        return
    if len(normalized) > maximum:
        raise ValueError(f"{field_name} cannot exceed {maximum} characters")
    object.__setattr__(instance, field_name, normalized)


def _unique_text(values: tuple[str, ...], *, maximum: int) -> tuple[str, ...]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        if len(normalized) > maximum:
            raise ValueError(f"text value cannot exceed {maximum} characters")
        key = normalized.casefold()
        if key not in seen:
            seen.add(key)
            unique.append(normalized)
    return tuple(unique)
