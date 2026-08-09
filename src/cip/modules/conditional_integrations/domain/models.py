from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from cip.modules.conditional_integrations.domain.enums import (
    ApprovalState,
    ConditionalAccessMethod,
    ConditionalBlockReason,
    ConditionalProviderKind,
    TermsReviewState,
)
from cip.modules.provider_onboarding.domain.models import OnboardingState
from cip.modules.source_governance.domain.models import DataCategory
from cip.shared.kernel.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class ProviderApprovalDossier:
    source_id: str
    provider_kind: ConditionalProviderKind
    access_method: ConditionalAccessMethod
    state: ApprovalState
    authorization_document_reference: str | None
    licence_reference: str | None
    terms_reference: str | None
    terms_state: TermsReviewState
    approved_scopes: frozenset[str] = field(default_factory=frozenset)
    approved_fields: frozenset[str] = field(default_factory=frozenset)
    approved_purposes: frozenset[str] = field(default_factory=frozenset)
    approved_data_categories: frozenset[DataCategory] = field(default_factory=frozenset)
    retention_days: int | None = None
    automated_collection_allowed: bool = False
    account_reference: str | None = None
    reviewed_at: datetime | None = None
    review_due_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    paused_reason: str | None = None

    def __post_init__(self) -> None:
        source_id = self.source_id.strip()
        if not source_id or len(source_id) > 100:
            raise ValueError("source_id is required and cannot exceed 100 characters")
        object.__setattr__(self, "source_id", source_id)
        for field_name in (
            "authorization_document_reference",
            "licence_reference",
            "terms_reference",
            "account_reference",
            "paused_reason",
        ):
            _normalize_optional_text(self, field_name, maximum=500)
        for field_name in ("approved_scopes", "approved_fields", "approved_purposes"):
            _normalize_set(self, field_name)
        if self.retention_days is not None and self.retention_days < 1:
            raise ValueError("retention_days must be positive")
        for field_name in ("reviewed_at", "review_due_at", "expires_at", "revoked_at"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    require_aware_utc(value, field_name=field_name),
                )
        if self.state is ApprovalState.APPROVED:
            self._validate_approved()
        if self.state is ApprovalState.REVOKED and self.revoked_at is None:
            raise ValueError("revoked dossier requires revoked_at")
        if self.state is ApprovalState.PAUSED and self.paused_reason is None:
            raise ValueError("paused dossier requires paused_reason")

    def _validate_approved(self) -> None:
        if not self.authorization_document_reference:
            raise ValueError("approved dossier requires authorization document reference")
        if not self.terms_reference:
            raise ValueError("approved dossier requires terms reference")
        if self.terms_state is not TermsReviewState.CURRENT:
            raise ValueError("approved dossier requires current terms review")
        if self.reviewed_at is None:
            raise ValueError("approved dossier requires reviewed_at")
        if not self.approved_purposes or not self.approved_data_categories:
            raise ValueError("approved dossier requires purpose and data-category scopes")
        if self.retention_days is None:
            raise ValueError("approved dossier requires an explicit retention limit")
        licensed_methods = {
            ConditionalAccessMethod.LICENSED_API,
            ConditionalAccessMethod.CUSTOMER_PROVIDED_ACCESS,
        }
        if self.access_method in licensed_methods and not self.licence_reference:
            raise ValueError("licensed access requires a licence reference")


@dataclass(frozen=True, slots=True)
class ConditionalExecutionRequest:
    source_id: str
    access_method: ConditionalAccessMethod
    purpose: str
    data_category: DataCategory
    requested_scopes: frozenset[str] = field(default_factory=frozenset)
    requested_fields: frozenset[str] = field(default_factory=frozenset)
    retention_days: int = 1
    automated: bool = True
    account_reference: str | None = None

    def __post_init__(self) -> None:
        source_id = self.source_id.strip()
        purpose = self.purpose.strip()
        if not source_id:
            raise ValueError("source_id is required")
        if not purpose:
            raise ValueError("purpose is required")
        if self.retention_days < 1:
            raise ValueError("retention_days must be positive")
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "purpose", purpose)
        _normalize_set(self, "requested_scopes")
        _normalize_set(self, "requested_fields")
        _normalize_optional_text(self, "account_reference", maximum=500)


@dataclass(frozen=True, slots=True)
class ConditionalRuntimeDependencies:
    onboarding_state: OnboardingState
    source_policy_allowed: bool
    adapter_capability_present: bool
    kill_switch_active: bool = False
    quota_remaining: int | None = None
    monthly_cost_used: float = 0.0
    monthly_cost_limit: float | None = None

    def __post_init__(self) -> None:
        if self.quota_remaining is not None and self.quota_remaining < 0:
            raise ValueError("quota_remaining cannot be negative")
        if self.monthly_cost_used < 0:
            raise ValueError("monthly_cost_used cannot be negative")
        if self.monthly_cost_limit is not None and self.monthly_cost_limit < 0:
            raise ValueError("monthly_cost_limit cannot be negative")


@dataclass(frozen=True, slots=True)
class ConditionalExecutionDecision:
    allowed: bool
    reasons: tuple[ConditionalBlockReason, ...]

    def __post_init__(self) -> None:
        if self.allowed and self.reasons != (ConditionalBlockReason.ALLOWED,):
            raise ValueError("allowed decision must contain only the allowed reason")
        if not self.allowed and ConditionalBlockReason.ALLOWED in self.reasons:
            raise ValueError("blocked decision cannot contain the allowed reason")
        if not self.reasons:
            raise ValueError("decision requires at least one reason")


def _normalize_optional_text(instance: object, field_name: str, *, maximum: int) -> None:
    value = getattr(instance, field_name)
    if value is None:
        return
    normalized = value.strip()
    if not normalized:
        object.__setattr__(instance, field_name, None)
        return
    if len(normalized) > maximum:
        raise ValueError(f"{field_name} cannot exceed {maximum} characters")
    object.__setattr__(instance, field_name, normalized)


def _normalize_set(instance: object, field_name: str) -> None:
    values = getattr(instance, field_name)
    normalized = frozenset(value.strip() for value in values if value.strip())
    if any(len(value) > 300 for value in normalized):
        raise ValueError(f"{field_name} values cannot exceed 300 characters")
    object.__setattr__(instance, field_name, normalized)
