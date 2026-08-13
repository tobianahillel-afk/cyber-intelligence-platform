from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from cip.modules.public_footprint.domain.url_identity import CanonicalUrl


class CrawlDecisionReason(StrEnum):
    ALLOWED = "allowed"
    HOST_NOT_ALLOWED = "host_not_allowed"
    PATH_NOT_ALLOWED = "path_not_allowed"
    DEPTH_EXCEEDED = "depth_exceeded"
    PAGE_BUDGET_EXCEEDED = "page_budget_exceeded"
    TOTAL_BYTE_BUDGET_EXCEEDED = "total_byte_budget_exceeded"
    RESOURCE_SIZE_EXCEEDED = "resource_size_exceeded"
    MIME_NOT_ALLOWED = "mime_not_allowed"
    REDIRECT_LIMIT_EXCEEDED = "redirect_limit_exceeded"


@dataclass(frozen=True, slots=True)
class CrawlDecision:
    allowed: bool
    reason: CrawlDecisionReason


@dataclass(frozen=True, slots=True)
class CrawlUsage:
    pages_fetched: int = 0
    bytes_fetched: int = 0

    def __post_init__(self) -> None:
        if self.pages_fetched < 0 or self.bytes_fetched < 0:
            raise ValueError("crawl usage cannot be negative")


@dataclass(frozen=True, slots=True)
class CrawlScope:
    allowed_hosts: frozenset[str]
    allowed_path_prefixes: tuple[str, ...] = ("/",)
    allowed_mime_types: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                "application/atom+xml",
                "application/json",
                "application/ld+json",
                "application/pdf",
                "application/rss+xml",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/xml",
                "text/html",
                "text/plain",
                "text/xml",
            }
        )
    )
    max_depth: int = 3
    max_pages: int = 250
    max_total_bytes: int = 25_000_000
    max_resource_bytes: int = 5_000_000
    max_redirects: int = 5

    def __post_init__(self) -> None:
        hosts = frozenset(_normalize_host(host) for host in self.allowed_hosts)
        if not hosts:
            raise ValueError("at least one allowed host is required")
        prefixes = tuple(_normalize_prefix(prefix) for prefix in self.allowed_path_prefixes)
        if not prefixes:
            raise ValueError("at least one allowed path prefix is required")
        mime_types = frozenset(_normalize_mime_type(value) for value in self.allowed_mime_types)
        if not mime_types:
            raise ValueError("at least one allowed MIME type is required")
        if not 0 <= self.max_depth <= 20:
            raise ValueError("max_depth must be between 0 and 20")
        if not 1 <= self.max_pages <= 10_000:
            raise ValueError("max_pages must be between 1 and 10000")
        if self.max_total_bytes < 1:
            raise ValueError("max_total_bytes must be positive")
        if self.max_resource_bytes < 1:
            raise ValueError("max_resource_bytes must be positive")
        if self.max_resource_bytes > self.max_total_bytes:
            raise ValueError("max_resource_bytes cannot exceed max_total_bytes")
        if not 0 <= self.max_redirects <= 20:
            raise ValueError("max_redirects must be between 0 and 20")
        object.__setattr__(self, "allowed_hosts", hosts)
        object.__setattr__(self, "allowed_path_prefixes", prefixes)
        object.__setattr__(self, "allowed_mime_types", mime_types)

    def evaluate_target(
        self,
        url: str | CanonicalUrl,
        *,
        depth: int,
        redirects: int,
        usage: CrawlUsage,
    ) -> CrawlDecision:
        canonical = url if isinstance(url, CanonicalUrl) else CanonicalUrl(url)
        if canonical.host not in self.allowed_hosts:
            return CrawlDecision(False, CrawlDecisionReason.HOST_NOT_ALLOWED)
        if not any(_path_matches(canonical.path, prefix) for prefix in self.allowed_path_prefixes):
            return CrawlDecision(False, CrawlDecisionReason.PATH_NOT_ALLOWED)
        if depth < 0 or depth > self.max_depth:
            return CrawlDecision(False, CrawlDecisionReason.DEPTH_EXCEEDED)
        if redirects < 0 or redirects > self.max_redirects:
            return CrawlDecision(False, CrawlDecisionReason.REDIRECT_LIMIT_EXCEEDED)
        if usage.pages_fetched >= self.max_pages:
            return CrawlDecision(False, CrawlDecisionReason.PAGE_BUDGET_EXCEEDED)
        if usage.bytes_fetched >= self.max_total_bytes:
            return CrawlDecision(False, CrawlDecisionReason.TOTAL_BYTE_BUDGET_EXCEEDED)
        return CrawlDecision(True, CrawlDecisionReason.ALLOWED)

    def evaluate_response(
        self,
        *,
        mime_type: str,
        resource_bytes: int,
        usage: CrawlUsage,
    ) -> CrawlDecision:
        if resource_bytes < 0 or resource_bytes > self.max_resource_bytes:
            return CrawlDecision(False, CrawlDecisionReason.RESOURCE_SIZE_EXCEEDED)
        if usage.bytes_fetched + resource_bytes > self.max_total_bytes:
            return CrawlDecision(False, CrawlDecisionReason.TOTAL_BYTE_BUDGET_EXCEEDED)
        if _normalize_mime_type(mime_type) not in self.allowed_mime_types:
            return CrawlDecision(False, CrawlDecisionReason.MIME_NOT_ALLOWED)
        return CrawlDecision(True, CrawlDecisionReason.ALLOWED)


def _normalize_host(value: str) -> str:
    host = value.strip().rstrip(".")
    if not host or "://" in host or "/" in host:
        raise ValueError("allowed host must be a bare hostname")
    return host.encode("idna").decode("ascii").casefold()


def _normalize_prefix(value: str) -> str:
    prefix = value.strip()
    if not prefix.startswith("/"):
        raise ValueError("allowed path prefix must start with /")
    if "?" in prefix or "#" in prefix:
        raise ValueError("allowed path prefix cannot contain query or fragment")
    if prefix != "/":
        prefix = prefix.rstrip("/")
    return prefix


def _path_matches(path: str, prefix: str) -> bool:
    if prefix == "/":
        return True
    return path == prefix or path.startswith(f"{prefix}/")


def _normalize_mime_type(value: str) -> str:
    mime_type = value.split(";", 1)[0].strip().casefold()
    if "/" not in mime_type:
        raise ValueError("MIME type must contain a type and subtype")
    return mime_type
