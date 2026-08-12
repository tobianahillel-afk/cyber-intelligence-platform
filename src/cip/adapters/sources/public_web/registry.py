from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from ipaddress import ip_address
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml

from cip.modules.public_footprint.domain.scope import CrawlScope
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl, same_origin
from cip.shared.kernel.time import require_aware_utc

_NON_PUBLIC_HOST_SUFFIXES = (
    ".home",
    ".internal",
    ".lan",
    ".local",
    ".localhost",
)
_SECURITY_TXT_PATH = "/.well-known/security.txt"


@dataclass(frozen=True, slots=True)
class PublicWebTarget:
    id: str
    organization_id: UUID
    canonical_name: str
    base_url: str
    sitemap_urls: tuple[str, ...]
    allowed_path_prefixes: tuple[str, ...]
    enabled: bool
    authorization_reference: str | None
    authorization_reviewed_at: datetime | None
    authorization_expires_at: datetime | None = None
    terms_url: str | None = None
    feed_urls: tuple[str, ...] = ()
    seed_urls: tuple[str, ...] = ()
    discover_security_txt: bool = False
    source_id: str | None = None
    max_link_depth: int = 0
    max_pages: int = 100
    max_total_bytes: int = 10_000_000
    max_resource_bytes: int = 1_000_000
    max_redirects: int = 3

    def __post_init__(self) -> None:
        identifier = self.id.strip()
        name = self.canonical_name.strip()
        if not identifier or not name:
            raise ValueError("public web target id and canonical_name are required")
        if not 0 <= self.max_link_depth <= 20:
            raise ValueError("max_link_depth must be between 0 and 20")
        base = CanonicalUrl(self.base_url)
        _validate_public_hostname(base.host)
        seeds = _same_origin_urls(base, self.seed_urls, label="seed")
        sitemaps = _same_origin_urls(base, self.sitemap_urls, label="sitemap")
        feeds = _same_origin_urls(base, self.feed_urls, label="feed")
        if not seeds and not sitemaps and not feeds and not self.discover_security_txt:
            raise ValueError("public web target requires an explicit discovery path")
        reviewed_at = _optional_time(
            self.authorization_reviewed_at,
            field_name="authorization_reviewed_at",
        )
        expires_at = _optional_time(
            self.authorization_expires_at,
            field_name="authorization_expires_at",
        )
        if reviewed_at is not None and expires_at is not None and expires_at <= reviewed_at:
            raise ValueError("authorization expiry must follow its review time")
        reference = _optional_text(self.authorization_reference)
        if self.enabled and (reference is None or reviewed_at is None):
            raise ValueError("enabled public web target requires reviewed authorization")
        source_id = _optional_text(self.source_id) or identifier
        terms_url = CanonicalUrl(self.terms_url).value if self.terms_url else None
        prefixes = self.allowed_path_prefixes
        if self.discover_security_txt and _SECURITY_TXT_PATH not in prefixes:
            prefixes = (*prefixes, _SECURITY_TXT_PATH)
        scope = CrawlScope(
            allowed_hosts=frozenset({base.host}),
            allowed_path_prefixes=prefixes,
            max_depth=max(1, self.max_link_depth),
            max_pages=self.max_pages,
            max_total_bytes=self.max_total_bytes,
            max_resource_bytes=self.max_resource_bytes,
            max_redirects=self.max_redirects,
        )
        object.__setattr__(self, "id", identifier)
        object.__setattr__(self, "canonical_name", name)
        object.__setattr__(self, "base_url", base.value)
        object.__setattr__(self, "seed_urls", seeds)
        object.__setattr__(self, "sitemap_urls", sitemaps)
        object.__setattr__(self, "feed_urls", feeds)
        object.__setattr__(self, "allowed_path_prefixes", scope.allowed_path_prefixes)
        object.__setattr__(self, "authorization_reference", reference)
        object.__setattr__(self, "authorization_reviewed_at", reviewed_at)
        object.__setattr__(self, "authorization_expires_at", expires_at)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "terms_url", terms_url)

    @property
    def host(self) -> str:
        return CanonicalUrl(self.base_url).host

    @property
    def robots_url(self) -> str:
        return f"{CanonicalUrl(self.base_url).origin}/robots.txt"

    @property
    def security_txt_url(self) -> str:
        return f"{CanonicalUrl(self.base_url).origin}{_SECURITY_TXT_PATH}"

    @property
    def crawl_scope(self) -> CrawlScope:
        return CrawlScope(
            allowed_hosts=frozenset({self.host}),
            allowed_path_prefixes=self.allowed_path_prefixes,
            max_depth=max(1, self.max_link_depth),
            max_pages=self.max_pages,
            max_total_bytes=self.max_total_bytes,
            max_resource_bytes=self.max_resource_bytes,
            max_redirects=self.max_redirects,
        )

    def executable_at(self, now: datetime) -> bool:
        current = require_aware_utc(now, field_name="now")
        return bool(
            self.enabled
            and self.authorization_reference
            and self.authorization_reviewed_at
            and (
                self.authorization_expires_at is None
                or self.authorization_expires_at > current
            )
        )


def load_public_web_targets(path: Path) -> tuple[PublicWebTarget, ...]:
    payload = _load_yaml_mapping(path)
    if _positive_int(payload, "version") != 1:
        raise ValueError("unsupported public web target registry version")
    raw_targets = payload.get("targets")
    if not isinstance(raw_targets, list):
        raise ValueError("public web targets must be a list")
    targets: list[PublicWebTarget] = []
    target_ids: set[str] = set()
    organization_origins: set[tuple[UUID, str]] = set()
    for raw in raw_targets:
        if not isinstance(raw, dict):
            raise ValueError("each public web target must be a mapping")
        target = _parse_target(raw)
        if target.id in target_ids:
            raise ValueError(f"duplicate public web target id: {target.id}")
        origin_key = (target.organization_id, CanonicalUrl(target.base_url).origin)
        if origin_key in organization_origins:
            raise ValueError("duplicate organization and origin in public web targets")
        target_ids.add(target.id)
        organization_origins.add(origin_key)
        targets.append(target)
    return tuple(targets)


def _parse_target(payload: dict[str, Any]) -> PublicWebTarget:
    authorization = _required_mapping(payload, "authorization")
    limits = _required_mapping(payload, "limits")
    return PublicWebTarget(
        id=_required_string(payload, "id"),
        organization_id=UUID(_required_string(payload, "organization_id")),
        canonical_name=_required_string(payload, "canonical_name"),
        base_url=_required_string(payload, "base_url"),
        seed_urls=_string_tuple(payload, "seed_urls", minimum=0),
        sitemap_urls=_string_tuple(payload, "sitemap_urls", minimum=0),
        feed_urls=_string_tuple(payload, "feed_urls", minimum=0),
        discover_security_txt=_optional_bool(payload, "discover_security_txt", default=False),
        source_id=_optional_string(payload, "source_id"),
        allowed_path_prefixes=_string_tuple(
            payload,
            "allowed_path_prefixes",
            minimum=1,
        ),
        enabled=_required_bool(payload, "enabled"),
        authorization_reference=_optional_string(
            authorization,
            "document_reference",
        ),
        authorization_reviewed_at=_optional_datetime(
            authorization,
            "reviewed_at",
        ),
        authorization_expires_at=_optional_datetime(
            authorization,
            "expires_at",
        ),
        terms_url=_optional_string(payload, "terms_url"),
        max_link_depth=_optional_bounded_int(
            limits,
            "max_link_depth",
            default=0,
            minimum=0,
            maximum=20,
        ),
        max_pages=_bounded_int(limits, "max_pages", minimum=1, maximum=1_000),
        max_total_bytes=_bounded_int(
            limits,
            "max_total_bytes",
            minimum=1,
            maximum=100_000_000,
        ),
        max_resource_bytes=_bounded_int(
            limits,
            "max_resource_bytes",
            minimum=1,
            maximum=20_000_000,
        ),
        max_redirects=_bounded_int(limits, "max_redirects", minimum=0, maximum=10),
    )


def _same_origin_urls(
    base: CanonicalUrl,
    values: tuple[str, ...],
    *,
    label: str,
) -> tuple[str, ...]:
    urls = tuple(CanonicalUrl(value).value for value in values)
    if any(not same_origin(base, url) for url in urls):
        raise ValueError(f"public web {label} URLs must share the target origin")
    if len(set(urls)) != len(urls):
        raise ValueError(f"public web {label} URLs must be unique")
    return urls


def _validate_public_hostname(host: str) -> None:
    normalized = host.rstrip(".").casefold()
    if normalized == "localhost" or normalized.endswith(_NON_PUBLIC_HOST_SUFFIXES):
        raise ValueError("public web target host must not be local or internal")
    try:
        parsed_address = ip_address(normalized)
    except ValueError:
        parsed_address = None
    if parsed_address is not None:
        raise ValueError("public web target host must not be an IP literal")
    if "." not in normalized:
        raise ValueError("public web target host must be a public DNS name")


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("public web target registry root must be a mapping")
    return loaded


def _required_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping")
    return value


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string or null")
    return _optional_text(value)


def _required_bool(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def _optional_bool(payload: dict[str, Any], key: str, *, default: bool) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def _string_tuple(
    payload: dict[str, Any],
    key: str,
    *,
    minimum: int,
) -> tuple[str, ...]:
    value = payload.get(key, [])
    if not isinstance(value, list) or len(value) < minimum:
        raise ValueError(f"{key} must contain at least {minimum} item(s)")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{key} items must be non-empty strings")
        result.append(item)
    return tuple(result)


def _bounded_int(
    payload: dict[str, Any],
    key: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    value = payload.get(key)
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or not minimum <= value <= maximum
    ):
        raise ValueError(f"{key} must be between {minimum} and {maximum}")
    return value


def _optional_bounded_int(
    payload: dict[str, Any],
    key: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    value = payload.get(key, default)
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or not minimum <= value <= maximum
    ):
        raise ValueError(f"{key} must be between {minimum} and {maximum}")
    return value


def _positive_int(payload: dict[str, Any], key: str) -> int:
    return _bounded_int(payload, key, minimum=1, maximum=2_147_483_647)


def _optional_datetime(payload: dict[str, Any], key: str) -> datetime | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, datetime):
        return require_aware_utc(value, field_name=key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be an ISO datetime or null")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{key} must be an ISO datetime or null") from exc
    return require_aware_utc(parsed, field_name=key)


def _optional_time(value: datetime | None, *, field_name: str) -> datetime | None:
    if value is None:
        return None
    return require_aware_utc(value, field_name=field_name)


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
