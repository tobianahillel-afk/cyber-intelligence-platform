from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from cip.modules.public_footprint.domain.structured_state import PublicStructuredStateKind

_SENSITIVE_KEY_MARKERS = (
    "token",
    "secret",
    "password",
    "passwd",
    "apikey",
    "api_key",
    "authorization",
    "credential",
    "session",
    "cookie",
    "csrf",
    "xsrf",
    "nonce",
)
_JSON_MIME_TYPES = frozenset({"application/json", "text/json"})
_DROP = object()

PUBLIC_SCRIPT_STATE_EXTRACTOR_ID = "public-known-globals-v1"
PUBLIC_SCRIPT_STATE_GLOBALS = (
    "__NEXT_DATA__",
    "__NUXT__",
    "__APOLLO_STATE__",
    "__INITIAL_STATE__",
    "__PRELOADED_STATE__",
)
PUBLIC_SCRIPT_STATE_JS = """() => {
  const names = [
    "__NEXT_DATA__", "__NUXT__", "__APOLLO_STATE__",
    "__INITIAL_STATE__", "__PRELOADED_STATE__"
  ];
  const result = {};
  for (const name of names) {
    const value = window[name];
    if (value === undefined || value === null) continue;
    try {
      JSON.stringify(value);
      result[name] = value;
    } catch (_) {
      continue;
    }
  }
  return result;
}"""


@dataclass(frozen=True, slots=True)
class StructuredStateCaptureLimits:
    max_json_responses: int = 8
    max_response_bytes: int = 32_768
    max_total_json_bytes: int = 131_072
    max_depth: int = 12
    max_scalars: int = 256
    max_key_chars: int = 200
    max_string_chars: int = 1_000
    max_script_states: int = 5
    max_total_script_bytes: int = 65_536

    def __post_init__(self) -> None:
        _bounded(self.max_json_responses, 1, 64, "max_json_responses")
        _bounded(self.max_response_bytes, 256, 262_144, "max_response_bytes")
        _bounded(self.max_total_json_bytes, self.max_response_bytes, 1_048_576, "max_total_json_bytes")
        _bounded(self.max_depth, 1, 32, "max_depth")
        _bounded(self.max_scalars, 1, 4_096, "max_scalars")
        _bounded(self.max_key_chars, 16, 1_000, "max_key_chars")
        _bounded(self.max_string_chars, 16, 8_000, "max_string_chars")
        _bounded(self.max_script_states, 1, len(PUBLIC_SCRIPT_STATE_GLOBALS), "max_script_states")
        _bounded(self.max_total_script_bytes, 256, 262_144, "max_total_script_bytes")


@dataclass(frozen=True, slots=True)
class CapturedStructuredState:
    kind: PublicStructuredStateKind
    source_locator: str
    payload_json: str
    source_url: str | None = None
    http_status: int | None = None
    media_type: str | None = None
    extractor_id: str | None = None


@dataclass(slots=True)
class StructuredStateCapture:
    limits: StructuredStateCaptureLimits
    json_responses: int = 0
    json_bytes: int = 0
    script_states: int = 0
    script_bytes: int = 0

    def capture_network_json(
        self,
        *,
        source_url: str,
        status: int,
        media_type: str,
        body: bytes,
    ) -> CapturedStructuredState | None:
        normalized_mime = media_type.split(";", 1)[0].strip().casefold()
        if not 200 <= status <= 299 or not _is_json_mime(normalized_mime):
            return None
        if self.json_responses >= self.limits.max_json_responses:
            return None
        if len(body) > self.limits.max_response_bytes:
            return None
        if self.json_bytes + len(body) > self.limits.max_total_json_bytes:
            return None
        payload = _load_and_sanitize(body, self.limits)
        if payload is None:
            return None
        self.json_responses += 1
        self.json_bytes += len(body)
        return CapturedStructuredState(
            kind=PublicStructuredStateKind.NETWORK_JSON,
            source_locator=source_url,
            source_url=source_url,
            http_status=status,
            media_type=normalized_mime,
            payload_json=payload,
        )

    def capture_script_states(self, raw: object) -> tuple[CapturedStructuredState, ...]:
        if not isinstance(raw, dict):
            return ()
        result: list[CapturedStructuredState] = []
        for name in PUBLIC_SCRIPT_STATE_GLOBALS:
            if name not in raw or self.script_states >= self.limits.max_script_states:
                continue
            payload = _sanitize_value_to_json(raw[name], self.limits)
            if payload is None:
                continue
            payload_bytes = len(payload.encode("utf-8"))
            if self.script_bytes + payload_bytes > self.limits.max_total_script_bytes:
                continue
            self.script_states += 1
            self.script_bytes += payload_bytes
            result.append(
                CapturedStructuredState(
                    kind=PublicStructuredStateKind.SCRIPT_STATE,
                    source_locator=f"window.{name}",
                    extractor_id=PUBLIC_SCRIPT_STATE_EXTRACTOR_ID,
                    payload_json=payload,
                )
            )
        return tuple(result)


def _load_and_sanitize(body: bytes, limits: StructuredStateCaptureLimits) -> str | None:
    try:
        raw: Any = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError):
        return None
    return _sanitize_value_to_json(raw, limits)


def _sanitize_value_to_json(raw: object, limits: StructuredStateCaptureLimits) -> str | None:
    budget = _ScalarBudget(limits.max_scalars)
    try:
        sanitized = _sanitize(raw, limits=limits, budget=budget, depth=0, key=None)
    except RecursionError:
        return None
    if sanitized is _DROP or not isinstance(sanitized, dict | list) or not sanitized:
        return None
    encoded = json.dumps(sanitized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if len(encoded) > 32_768:
        return None
    return encoded


@dataclass(slots=True)
class _ScalarBudget:
    remaining: int


def _sanitize(
    value: object,
    *,
    limits: StructuredStateCaptureLimits,
    budget: _ScalarBudget,
    depth: int,
    key: str | None,
) -> object:
    if depth > limits.max_depth or budget.remaining <= 0:
        return _DROP
    if key is not None and _is_sensitive_key(key):
        return _DROP
    if isinstance(value, dict):
        result: dict[str, object] = {}
        for child_key, child_value in value.items():
            if not isinstance(child_key, str) or len(child_key) > limits.max_key_chars:
                continue
            sanitized = _sanitize(
                child_value,
                limits=limits,
                budget=budget,
                depth=depth + 1,
                key=child_key,
            )
            if sanitized is not _DROP:
                result[child_key] = sanitized
            if budget.remaining <= 0:
                break
        return result if result else _DROP
    if isinstance(value, list):
        result_list: list[object] = []
        for child in value:
            sanitized = _sanitize(
                child,
                limits=limits,
                budget=budget,
                depth=depth + 1,
                key=key,
            )
            if sanitized is not _DROP:
                result_list.append(sanitized)
            if budget.remaining <= 0:
                break
        return result_list if result_list else _DROP
    if value is None or isinstance(value, bool | int | float | str):
        budget.remaining -= 1
        if isinstance(value, str):
            return value[: limits.max_string_chars]
        return value
    return _DROP


def _is_sensitive_key(key: str) -> bool:
    compact = key.casefold().replace("-", "").replace("_", "")
    return any(marker.replace("_", "") in compact for marker in _SENSITIVE_KEY_MARKERS)


def _is_json_mime(mime_type: str) -> bool:
    return mime_type in _JSON_MIME_TYPES or mime_type.endswith("+json")


def _bounded(value: int, minimum: int, maximum: int, field_name: str) -> None:
    if not minimum <= value <= maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}")
