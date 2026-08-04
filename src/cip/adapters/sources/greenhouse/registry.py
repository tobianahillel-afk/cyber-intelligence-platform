from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_BOARD_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True, slots=True)
class GreenhouseBoard:
    id: str
    board_token: str
    canonical_name: str
    country_code: str | None = None
    enabled: bool = True

    def __post_init__(self) -> None:
        for field_name in ("id", "board_token", "canonical_name"):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} is required")
            object.__setattr__(self, field_name, value)
        if not _BOARD_TOKEN_PATTERN.fullmatch(self.board_token):
            raise ValueError("board_token contains unsupported characters")
        if self.country_code is not None:
            country = self.country_code.strip().upper()
            if len(country) != 2 or not country.isalpha():
                raise ValueError("country_code must be an ISO alpha-2 code")
            object.__setattr__(self, "country_code", country)


def load_greenhouse_boards(path: Path) -> tuple[GreenhouseBoard, ...]:
    payload = _load_yaml_mapping(path)
    if _positive_int(payload, "version") != 1:
        raise ValueError("unsupported Greenhouse board registry version")
    raw_boards = payload.get("boards")
    if not isinstance(raw_boards, list):
        raise ValueError("boards must be a list")
    boards: list[GreenhouseBoard] = []
    identities: set[str] = set()
    tokens: set[str] = set()
    for raw in raw_boards:
        if not isinstance(raw, dict):
            raise ValueError("each Greenhouse board must be a mapping")
        board = _parse_board(raw)
        if board.id in identities:
            raise ValueError(f"duplicate Greenhouse board id: {board.id}")
        if board.board_token in tokens:
            raise ValueError(f"duplicate Greenhouse board token: {board.board_token}")
        identities.add(board.id)
        tokens.add(board.board_token)
        boards.append(board)
    return tuple(boards)


def _parse_board(payload: dict[str, Any]) -> GreenhouseBoard:
    country = payload.get("country_code")
    if country is not None and not isinstance(country, str):
        raise ValueError("country_code must be a string or null")
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean")
    return GreenhouseBoard(
        id=_required_string(payload, "id"),
        board_token=_required_string(payload, "board_token"),
        canonical_name=_required_string(payload, "canonical_name"),
        country_code=country,
        enabled=enabled,
    )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("Greenhouse board registry root must be a mapping")
    return loaded


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _positive_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{key} must be a positive integer")
    return value
