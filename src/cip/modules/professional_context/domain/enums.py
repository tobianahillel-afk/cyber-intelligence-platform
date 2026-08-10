from __future__ import annotations

from enum import StrEnum


class ProfessionalClaimType(StrEnum):
    ASSERTION = "assertion"
    DISPUTE = "dispute"
    CORRECTION = "correction"
    RETRACTION = "retraction"


class ProfessionalReviewState(StrEnum):
    UNREVIEWED = "unreviewed"
    REVIEW_REQUIRED = "review_required"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class OrganizationLinkStatus(StrEnum):
    UNRESOLVED = "unresolved"
    EXACT = "exact"
    CANDIDATE = "candidate"
    REVIEW_REQUIRED = "review_required"
    REJECTED = "rejected"


class LawfulBasis(StrEnum):
    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    LEGITIMATE_INTERESTS = "legitimate_interests"
    PUBLIC_TASK = "public_task"
    REVIEW_REQUIRED = "review_required"


class ContactChannelType(StrEnum):
    BUSINESS_EMAIL = "business_email"
    BUSINESS_EMAIL_PATTERN = "business_email_pattern"
    SWITCHBOARD = "switchboard"
    CONTACT_FORM = "contact_form"
    PROFESSIONAL_PROFILE = "professional_profile"


class ContactEvidenceScope(StrEnum):
    ORGANIZATION_PUBLISHED = "organization_published"
    PUBLIC_PROFESSIONAL = "public_professional"
    AUTHORIZED_DIRECTORY = "authorized_directory"


class CommunityAcquisitionMode(StrEnum):
    APPROVED_API = "approved_api"
    ADMIN_INSTALLED_INTEGRATION = "admin_installed_integration"
    AUTHORIZED_EXPORT = "authorized_export"
    MANUAL_REVIEWED_IMPORT = "manual_reviewed_import"
    GOVERNED_LOCAL_TOOL = "governed_local_tool"


class EmploymentState(StrEnum):
    CURRENT = "current"
    HISTORICAL = "historical"
    STALE = "stale"
    DISPUTED = "disputed"
    RETRACTED = "retracted"
    UNKNOWN = "unknown"
