from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from cip.adapters.sources.public_web.collector import PageCheckpoint, PublicWebCheckpoint
from cip.modules.public_footprint.domain import DiscoveryMethod, PublicResourceKind
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl

_MAX_TEXT = 2_000
_MAX_FEEDS = 100


class PublicWebCheckpointError(ValueError):
    """A durable public-web checkpoint is malformed or unsafe to replay."""


def load_checkpoint(payload: Mapping[str, object] | None) -> PublicWebCheckpoint | None:
    if payload is None:
        return None
    raw_pages = payload.get("pages")
    if not isinstance(raw_pages, dict):
        raise PublicWebCheckpointError("checkpoint pages must be a mapping")
    pages: dict[str, PageCheckpoint] = {}
    for raw_url, raw_state in raw_pages.items():
        if not isinstance(raw_url, str) or not isinstance(raw_state, dict):
            raise PublicWebCheckpointError("checkpoint page entries are invalid")
        pages[CanonicalUrl(raw_url).value] = _page_state(raw_state)
    return PublicWebCheckpoint(
        pages=pages,
        feed_urls=_feed_urls(payload.get("feed_urls", [])),
    )


def dump_checkpoint(checkpoint: PublicWebCheckpoint) -> dict[str, object]:
    return {
        "pages": {
            url: {
                "content_hash_sha256": state.content_hash_sha256,
                "version_id": str(state.version_id),
                "canonical_url": state.canonical_url,
                "resource_kind": state.resource_kind.value,
                "etag": state.etag,
                "last_modified": state.last_modified,
                "mime_type": state.mime_type,
                "byte_size": state.byte_size,
                "discovery_method": (
                    state.discovery_method.value
                    if state.discovery_method is not None
                    else None
                ),
                "source_locator": state.source_locator,
                "depth": state.depth,
                "security_txt": state.security_txt,
            }
            for url, state in sorted(checkpoint.pages.items())
        },
        "feed_urls": list(checkpoint.feed_urls),
    }


def _page_state(raw: Mapping[object, object]) -> PageCheckpoint:
    content_hash = raw.get("content_hash_sha256")
    version_id = raw.get("version_id")
    canonical_url = raw.get("canonical_url")
    resource_kind = raw.get("resource_kind", PublicResourceKind.WEB_PAGE.value)
    if not all(isinstance(value, str) for value in (
        content_hash,
        version_id,
        canonical_url,
        resource_kind,
    )):
        raise PublicWebCheckpointError("checkpoint page state is invalid")
    try:
        return PageCheckpoint(
            content_hash_sha256=str(content_hash),
            version_id=UUID(str(version_id)),
            canonical_url=CanonicalUrl(str(canonical_url)).value,
            resource_kind=PublicResourceKind(str(resource_kind)),
            etag=_text(raw, "etag"),
            last_modified=_text(raw, "last_modified"),
            mime_type=_text(raw, "mime_type"),
            byte_size=_non_negative_int(raw, "byte_size"),
            discovery_method=_discovery_method(raw),
            source_locator=_text(raw, "source_locator"),
            depth=_depth(raw),
            security_txt=_boolean(raw, "security_txt", default=False),
        )
    except (TypeError, ValueError) as exc:
        raise PublicWebCheckpointError("checkpoint page state is invalid") from exc


def _feed_urls(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list) or len(raw) > _MAX_FEEDS:
        raise PublicWebCheckpointError("checkpoint feed URLs are invalid")
    urls: list[str] = []
    try:
        for value in raw:
            if not isinstance(value, str):
                raise ValueError("feed URL must be text")
            canonical = CanonicalUrl(value).value
            if canonical not in urls:
                urls.append(canonical)
    except ValueError as exc:
        raise PublicWebCheckpointError("checkpoint feed URLs are invalid") from exc
    return tuple(urls)


def _text(raw: Mapping[object, object], key: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or not value
        or len(value) > _MAX_TEXT
        or "\r" in value
        or "\n" in value
    ):
        raise PublicWebCheckpointError(f"checkpoint {key} is invalid")
    return value


def _non_negative_int(raw: Mapping[object, object], key: str) -> int | None:
    value = raw.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PublicWebCheckpointError(f"checkpoint {key} is invalid")
    return value


def _depth(raw: Mapping[object, object]) -> int | None:
    value = _non_negative_int(raw, "depth")
    if value is not None and value > 20:
        raise PublicWebCheckpointError("checkpoint depth is invalid")
    return value


def _discovery_method(raw: Mapping[object, object]) -> DiscoveryMethod | None:
    value = raw.get("discovery_method")
    if value is None:
        return None
    if not isinstance(value, str):
        raise PublicWebCheckpointError("checkpoint discovery_method is invalid")
    return DiscoveryMethod(value)


def _boolean(raw: Mapping[object, object], key: str, *, default: bool) -> bool:
    value = raw.get(key, default)
    if not isinstance(value, bool):
        raise PublicWebCheckpointError(f"checkpoint {key} is invalid")
    return value
