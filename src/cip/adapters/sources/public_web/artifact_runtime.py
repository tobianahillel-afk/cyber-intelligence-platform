from __future__ import annotations

from dataclasses import dataclass, field

from playwright.sync_api import Page

from cip.adapters.sources.public_web.artifact_context import BrowserArtifactExecutionContext
from cip.adapters.sources.public_web.artifact_download import collect_governed_download
from cip.adapters.sources.public_web.artifact_policy import (
    BrowserArtifactPolicyError,
    BrowserArtifactUsage,
)
from cip.adapters.sources.public_web.artifact_screenshot import capture_governed_screenshot
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.artifacts import BrowserEvidenceArtifact
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionKind,
    BrowserActionPlan,
    BrowserActionStep,
)
from cip.modules.public_footprint.domain.models import PublicFootprintProjection
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


@dataclass(slots=True)
class BrowserArtifactRuntimeState:
    usage: BrowserArtifactUsage = field(default_factory=BrowserArtifactUsage)
    artifacts: list[BrowserEvidenceArtifact] = field(default_factory=list)
    projections: list[PublicFootprintProjection] = field(default_factory=list)


def execute_artifact_step(
    page: Page,
    target: PublicWebTarget,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    step: BrowserActionStep,
    context: BrowserArtifactExecutionContext | None,
    state: BrowserArtifactRuntimeState,
    *,
    timeout_ms: int,
) -> None:
    if context is None:
        raise BrowserArtifactPolicyError("browser_artifact_execution_context_required")
    if step.kind is BrowserActionKind.SCREENSHOT:
        state.artifacts.append(
            capture_governed_screenshot(
                page,
                target,
                entry,
                plan,
                step,
                context,
                state.usage,
            )
        )
        return
    if step.kind is BrowserActionKind.DOWNLOAD:
        artifact, projection = collect_governed_download(
            page,
            target,
            entry,
            plan,
            step,
            context,
            state.usage,
            timeout_ms=timeout_ms,
        )
        state.artifacts.append(artifact)
        state.projections.append(projection)
        return
    raise BrowserArtifactPolicyError("browser_artifact_action_kind_invalid")
