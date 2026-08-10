from __future__ import annotations

from datetime import datetime

from cip.adapters.sources.sherlock_local.mapper import map_sherlock_finding
from cip.adapters.sources.sherlock_local.registry import SherlockTarget
from cip.adapters.sources.sherlock_local.runner import SherlockLocalRunner
from cip.modules.professional_context.domain import PublicCommunityContext


class SherlockLocalAdapter:
    source_id = "sherlock-local"

    def __init__(self, runner: SherlockLocalRunner) -> None:
        self._runner = runner

    def collect(
        self,
        target: SherlockTarget,
        *,
        observed_at: datetime,
    ) -> tuple[PublicCommunityContext, ...]:
        findings = self._runner.collect(target)
        return tuple(
            map_sherlock_finding(target, finding, observed_at=observed_at)
            for finding in findings
        )
