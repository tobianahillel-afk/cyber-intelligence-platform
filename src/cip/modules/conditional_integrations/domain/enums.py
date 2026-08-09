from __future__ import annotations

from enum import StrEnum


class ConditionalProviderKind(StrEnum):
    LINKEDIN = "linkedin"
    DISCORD = "discord"
    BRIXHUB = "brixhub"
    PREMIUM_CTI = "premium_cti"
    COMMERCIAL_DATA = "commercial_data"
    OTHER = "other"


class ConditionalAccessMethod(StrEnum):
    OFFICIAL_API = "official_api"
    LICENSED_API = "licensed_api"
    ADMIN_INSTALLED_CONNECTOR = "admin_installed_connector"
    AUTHORIZED_EXPORT = "authorized_export"
    CUSTOMER_PROVIDED_ACCESS = "customer_provided_access"
    MANUAL_IMPORT = "manual_import"


class ApprovalState(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PAUSED = "paused"


class TermsReviewState(StrEnum):
    CURRENT = "current"
    CHANGED = "changed"
    REVIEW_REQUIRED = "review_required"


class ProviderControlAction(StrEnum):
    PAUSE = "pause"
    RESUME = "resume"
    ACTIVATE_KILL_SWITCH = "activate_kill_switch"
    CLEAR_KILL_SWITCH = "clear_kill_switch"


class ConditionalBlockReason(StrEnum):
    ALLOWED = "allowed"
    DOSSIER_NOT_APPROVED = "dossier_not_approved"
    DOSSIER_EXPIRED = "dossier_expired"
    DOSSIER_REVOKED = "dossier_revoked"
    DOSSIER_PAUSED = "dossier_paused"
    SOURCE_MISMATCH = "source_mismatch"
    ACCESS_METHOD_NOT_APPROVED = "access_method_not_approved"
    PROVIDER_METHOD_NOT_PERMITTED = "provider_method_not_permitted"
    SCOPE_NOT_APPROVED = "scope_not_approved"
    FIELD_NOT_APPROVED = "field_not_approved"
    PURPOSE_NOT_APPROVED = "purpose_not_approved"
    CATEGORY_NOT_APPROVED = "category_not_approved"
    RETENTION_EXCEEDS_APPROVAL = "retention_exceeds_approval"
    AUTOMATION_NOT_APPROVED = "automation_not_approved"
    ONBOARDING_NOT_READY = "onboarding_not_ready"
    SOURCE_POLICY_DENIED = "source_policy_denied"
    SOURCE_PORTFOLIO_NOT_EXECUTABLE = "source_portfolio_not_executable"
    CAPABILITY_MISSING = "capability_missing"
    PROVIDER_PAUSED = "provider_paused"
    KILL_SWITCH_ACTIVE = "kill_switch_active"
    QUOTA_EXHAUSTED = "quota_exhausted"
    COST_BUDGET_EXHAUSTED = "cost_budget_exhausted"
    TERMS_REVIEW_REQUIRED = "terms_review_required"
    ACCOUNT_MISMATCH = "account_mismatch"
