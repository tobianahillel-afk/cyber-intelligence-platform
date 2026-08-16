from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from cip.adapters.sources.public_web.artifact_context import BrowserArtifactExecutionContext
from cip.adapters.sources.public_web.artifact_policy import BrowserArtifactPolicyError
from cip.adapters.sources.public_web.collection_policy import public_web_raw_storage_allowed
from cip.modules.public_footprint.domain.browser_actions import BrowserActionPlan, BrowserActionStep
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


@dataclass(frozen=True, slots=True)
class ArtifactRetentionResult:
    allowed: bool
    retained: bool
    storage_uri: str | None


def retain_artifact_if_requested(
    content: bytes,
    *,
    media_type: str,
    source_url: str,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    step: BrowserActionStep,
    context: BrowserArtifactExecutionContext,
) -> ArtifactRetentionResult:
    allowed = public_web_raw_storage_allowed(
        entry,
        source_url,
        now=context.captured_at,
        purpose=plan.purpose,
    )
    if not step.retain_raw_artifact:
        return ArtifactRetentionResult(allowed=allowed, retained=False, storage_uri=None)
    if not allowed:
        raise BrowserArtifactPolicyError("browser_artifact_raw_retention_denied")
    if context.store is None:
        raise BrowserArtifactPolicyError("browser_artifact_store_unavailable")
    digest = sha256(content).hexdigest()
    object_key = (
        f"browser-artifacts/{plan.source_id}/{plan.plan_id}/{plan.version}/"
        f"{step.step_id}/{digest}"
    )
    storage_uri = context.store.put(
        object_key=object_key,
        content=content,
        media_type=media_type,
    )
    if not storage_uri.strip():
        raise BrowserArtifactPolicyError("browser_artifact_store_returned_empty_uri")
    return ArtifactRetentionResult(allowed=True, retained=True, storage_uri=storage_uri)
