"""Source registry, authorization, and delegated-identity persistence adapters."""

from cip.modules.source_governance.infrastructure.delegated_identity_models import (
    DelegatedBrowserIdentityAuditRecord,
    DelegatedBrowserIdentityRecord,
)

__all__ = [
    "DelegatedBrowserIdentityAuditRecord",
    "DelegatedBrowserIdentityRecord",
]
