from pathlib import Path

from cip.modules.source_activation.domain.models import (
    ActivationDisposition,
    ActivationStage,
)
from cip.modules.source_activation.infrastructure.inventory import load_activation_inventory

ACTIVATION_PATH = Path("policies/source_activation.yml")
MATRIX_PATH = Path("docs/source_activation/SOURCE_COVERAGE_MATRIX.md")
REVIEW_PATH = Path("docs/source_activation/SA_08_BRIXHUB_ACCESS_REVIEW.md")

FORBIDDEN_STAGES = {
    ActivationStage.ADAPTER_PRESENT,
    ActivationStage.AUTHORIZED,
    ActivationStage.EXECUTABLE,
    ActivationStage.SCHEDULED,
    ActivationStage.LIVE_TESTED,
}


def test_brixhub_remains_terminal_fail_closed_after_sa08_review() -> None:
    record = next(
        record
        for record in load_activation_inventory(ACTIVATION_PATH)
        if record.source_id == "brixhub"
    )

    assert record.disposition is ActivationDisposition.BLOCKED
    assert record.activation_wave == "SA-08"
    assert record.reason
    assert record.is_resolved
    assert record.stages.isdisjoint(FORBIDDEN_STAGES)


def test_brixhub_review_and_matrix_preserve_blocked_state_and_safe_actions() -> None:
    review = REVIEW_PATH.read_text(encoding="utf-8")
    matrix = MATRIX_PATH.read_text(encoding="utf-8")

    assert "`brixhub` remains terminal `blocked`" in review
    assert "create or register a BrixHub account" in review
    assert "Discord OAuth" in review
    assert "cryptocurrency transfer" in review
    assert "use Tor" in review
    assert "download a sample" in review
    assert "add a browser runtime or provider adapter" in review
    assert "`brixhub`" in matrix
    assert "BLOCKED pending access/licence/data review" in matrix
