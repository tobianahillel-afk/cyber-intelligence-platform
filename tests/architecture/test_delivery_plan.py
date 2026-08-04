from __future__ import annotations

import re
from pathlib import Path

PLAN_PATH = Path("docs/PROJECT_DELIVERY_PLAN.md")
EXPECTED_LOTS = tuple(range(27))
REQUIRED_LABELS = (
    "**Status:**",
    "**Objective:**",
    "**Dependencies:**",
    "**Deliverables:**",
    "**Tests:**",
    "**Exit gate:**",
    "**Non-goals:**",
)
LOT_HEADING = re.compile(r"^## Lot (\d{2}) — .+$", re.MULTILINE)
DETAIL_STATUS = re.compile(r"\*\*Status:\*\* `([A-Z_]+)`")
TABLE_ROW = re.compile(r"^\| (\d{2}) \| .+ \| `([A-Z_]+)` \|$", re.MULTILINE)


def test_plan_contains_every_lot_without_gaps() -> None:
    sections = _sections()

    assert tuple(sections) == EXPECTED_LOTS
    for number, section in sections.items():
        missing = [label for label in REQUIRED_LABELS if label not in section]
        assert missing == [], f"Lot {number:02d} is missing: {missing}"


def test_plan_summary_matches_detailed_statuses() -> None:
    content = PLAN_PATH.read_text(encoding="utf-8")
    detailed = {
        number: _status(number, section) for number, section in _sections().items()
    }
    summary = {int(number): status for number, status in TABLE_ROW.findall(content)}

    assert summary == detailed


def test_completed_lots_form_one_contiguous_prefix() -> None:
    statuses = {
        number: _status(number, section) for number, section in _sections().items()
    }
    completed = tuple(
        number
        for number, status in statuses.items()
        if status == "IMPLEMENTED_VALIDATED"
    )
    active = tuple(
        number for number, status in statuses.items() if status == "IN_PROGRESS"
    )

    assert completed == tuple(range(len(completed)))
    assert len(active) <= 1
    if active:
        assert active == (len(completed),)


def _sections() -> dict[int, str]:
    content = PLAN_PATH.read_text(encoding="utf-8")
    matches = tuple(LOT_HEADING.finditer(content))
    sections: dict[int, str] = {}
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        number = int(match.group(1))
        assert number not in sections, f"Duplicate lot: {number:02d}"
        sections[number] = content[start:end]
    return sections


def _status(number: int, section: str) -> str:
    match = DETAIL_STATUS.search(section)
    assert match is not None, f"Lot {number:02d} has no status"
    return match.group(1)
