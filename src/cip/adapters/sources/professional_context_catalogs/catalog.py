from __future__ import annotations

from dataclasses import dataclass

from cip.modules.professional_context.domain import CommunityAcquisitionMode


@dataclass(frozen=True, slots=True)
class ProfessionalSourceCandidate:
    source_id: str
    source_kind: str
    acquisition_mode: CommunityAcquisitionMode
    purpose: str
    allowed_fields: tuple[str, ...]
    authorization_required: bool = True
    executable: bool = False
    approved_hosts: tuple[str, ...] = ()
    approved_paths: tuple[str, ...] = ()
    runtime_adapter: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip() or len(self.source_id) > 200:
            raise ValueError("source_id must be between 1 and 200 characters")
        if not self.source_kind.strip() or len(self.source_kind) > 100:
            raise ValueError("source_kind must be between 1 and 100 characters")
        if not self.purpose.strip() or len(self.purpose) > 300:
            raise ValueError("purpose must be between 1 and 300 characters")
        if not self.allowed_fields:
            raise ValueError("professional source candidate requires bounded fields")
        if self.executable:
            raise ValueError("Lot 21 professional source candidates cannot be executable")
        if self.approved_hosts or self.approved_paths or self.runtime_adapter is not None:
            raise ValueError("Lot 21 source candidates cannot contain runtime execution scope")
        if not self.authorization_required:
            raise ValueError("professional source candidates require explicit authorization review")


PROFESSIONAL_CONTEXT_SOURCE_CANDIDATES = (
    ProfessionalSourceCandidate(
        source_id="organization_public_team_metadata",
        source_kind="organization_published_professional_context",
        acquisition_mode=CommunityAcquisitionMode.MANUAL_REVIEWED_IMPORT,
        purpose="Bounded organization-published roles, teams and business contact metadata.",
        allowed_fields=(
            "display_name",
            "role_title",
            "team_name",
            "business_email",
            "business_email_pattern",
            "switchboard",
            "contact_form_url",
            "source_url",
            "observed_at",
        ),
    ),
    ProfessionalSourceCandidate(
        source_id="licensed_professional_directory_metadata",
        source_kind="authorized_professional_directory",
        acquisition_mode=CommunityAcquisitionMode.APPROVED_API,
        purpose="Licensed or explicitly authorized public professional directory metadata.",
        allowed_fields=(
            "display_name",
            "role_title",
            "organization_name",
            "public_professional_profile_url",
            "source_record_key",
            "observed_at",
        ),
    ),
    ProfessionalSourceCandidate(
        source_id="authorized_community_context_metadata",
        source_kind="authorized_public_community_context",
        acquisition_mode=CommunityAcquisitionMode.AUTHORIZED_EXPORT,
        purpose="Metadata from an approved export, API, or administrator-consented integration.",
        allowed_fields=(
            "community_name",
            "context_type",
            "context_value",
            "authorization_reference",
            "source_record_key",
            "observed_at",
        ),
    ),
)
