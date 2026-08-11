from __future__ import annotations

from pathlib import Path

import pytest

from cip.adapters.sources.ashby.registry import AshbyBoard, load_ashby_boards


@pytest.mark.parametrize("field_name", ["id", "board_name", "canonical_name"])
def test_board_rejects_blank_required_fields(field_name: str) -> None:
    values: dict[str, object] = {
        "id": "ashby",
        "board_name": "Ashby",
        "canonical_name": "Ashby",
    }
    values[field_name] = " "
    with pytest.raises(ValueError, match=f"{field_name} is required"):
        AshbyBoard(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("country_code", ["F", "123", "F1"])
def test_board_rejects_invalid_country_codes(country_code: str) -> None:
    with pytest.raises(ValueError, match="ISO alpha-2"):
        AshbyBoard("ashby", "Ashby", "Ashby", country_code=country_code)


def test_board_normalizes_values_and_rejects_path_like_name() -> None:
    board = AshbyBoard(" ashby ", "Ashby", " Ashby Inc ", country_code=" fr ")
    assert board.id == "ashby"
    assert board.canonical_name == "Ashby Inc"
    assert board.country_code == "FR"

    with pytest.raises(ValueError, match="unsupported characters"):
        AshbyBoard("bad", "bad/path", "Bad")


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ("- item\n", "root must be a mapping"),
        ("version: 0\nboards: []\n", "positive integer"),
        ("version: 2\nboards: []\n", "unsupported"),
        ("version: 1\nboards: {}\n", "boards must be a list"),
        ("version: 1\nboards:\n  - bad\n", "must be a mapping"),
        (
            "version: 1\nboards:\n"
            "  - id: ashby\n"
            "    board_name: Ashby\n"
            "    canonical_name: Ashby\n"
            "    country_code: 123\n"
            "    enabled: true\n",
            "country_code must be a string",
        ),
        (
            "version: 1\nboards:\n"
            "  - id: ashby\n"
            "    board_name: Ashby\n"
            "    canonical_name: Ashby\n"
            "    enabled: null\n",
            "enabled must be a boolean",
        ),
        (
            "version: 1\nboards:\n"
            "  - id: ''\n"
            "    board_name: Ashby\n"
            "    canonical_name: Ashby\n"
            "    enabled: true\n",
            "id must be a non-empty string",
        ),
    ],
)
def test_registry_rejects_invalid_shapes(
    tmp_path: Path,
    payload: str,
    message: str,
) -> None:
    path = tmp_path / "ashby.yml"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_ashby_boards(path)


def test_registry_rejects_duplicate_board_names(tmp_path: Path) -> None:
    path = tmp_path / "ashby.yml"
    path.write_text(
        "version: 1\nboards:\n"
        "  - id: one\n"
        "    board_name: Ashby\n"
        "    canonical_name: One\n"
        "    enabled: true\n"
        "  - id: two\n"
        "    board_name: ashby\n"
        "    canonical_name: Two\n"
        "    enabled: true\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate Ashby board name"):
        load_ashby_boards(path)


def test_registry_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_ashby_boards(tmp_path / "missing.yml")
