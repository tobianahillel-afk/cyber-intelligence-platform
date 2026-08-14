from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from uuid import UUID

from cip.adapters.sources.public_web.client import PublicWebFetchResult
from cip.modules.public_footprint.domain import PublicSurfaceKind, PublicSurfaceReference
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl

_MAX_SURFACES = 256
_MAX_RAW_URL_LENGTH = 2_048
_FEED_TYPES = {"application/atom+xml", "application/rss+xml"}
_RESOURCE_LINK_RELS = {"icon", "manifest", "modulepreload", "prefetch", "preload"}
_DOCUMENT_EXTENSIONS = {".doc", ".docx", ".pdf", ".ppt", ".pptx", ".txt", ".xls", ".xlsx"}
_DOCUMENT_MIME_TYPES = {
    "application/msword",
    "application/pdf",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


def extract_public_surface_references(
    result: PublicWebFetchResult,
    *,
    organization_id: UUID,
    resource_version_id: UUID,
) -> tuple[PublicSurfaceReference, ...]:
    descriptors: list[dict[str, str | PublicSurfaceKind | None]] = []
    for name, value in result.response_headers:
        descriptors.append(
            {
                "kind": PublicSurfaceKind.RESPONSE_HEADER,
                "source_locator": f"header:{name}",
                "name": name,
                "value": value,
            }
        )
    if result.mime_type == "text/html" and result.body:
        parser = _SurfaceParser(result.fetched_url, remaining=_MAX_SURFACES - len(descriptors))
        parser.feed(result.body.decode("utf-8", errors="replace"))
        parser.close()
        descriptors.extend(parser.descriptors)
    surfaces: dict[str, PublicSurfaceReference] = {}
    for descriptor in descriptors[:_MAX_SURFACES]:
        surface = PublicSurfaceReference(
            organization_id=organization_id,
            resource_version_id=resource_version_id,
            kind=_kind(descriptor),
            source_locator=str(descriptor["source_locator"]),
            target_url=_string(descriptor.get("target_url")),
            relation=_string(descriptor.get("relation")),
            http_method=_string(descriptor.get("http_method")),
            media_type=_string(descriptor.get("media_type")),
            name=_string(descriptor.get("name")),
            value=_string(descriptor.get("value")),
        )
        surfaces[surface.identity_key] = surface
    return tuple(surfaces.values())


class _SurfaceParser(HTMLParser):
    def __init__(self, base_url: str, *, remaining: int) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.remaining = max(0, remaining)
        self.descriptors: list[dict[str, str | PublicSurfaceKind | None]] = []
        self._seen: set[tuple[object, ...]] = set()

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if len(self.descriptors) >= self.remaining:
            return
        attributes = {name.casefold(): value for name, value in attrs if value is not None}
        normalized_tag = tag.casefold()
        if normalized_tag == "link":
            self._link(attributes)
        elif normalized_tag == "script":
            self._url_surface(
                PublicSurfaceKind.SCRIPT,
                attributes.get("src"),
                "html:script[src]",
                media_type=attributes.get("type"),
            )
        elif normalized_tag == "form":
            self._url_surface(
                PublicSurfaceKind.FORM_ENDPOINT,
                attributes.get("action") or self.base_url,
                "html:form[action]",
                http_method=(attributes.get("method") or "GET"),
                media_type=attributes.get("enctype"),
            )
        elif normalized_tag == "a":
            self._anchor(attributes)
        elif normalized_tag in {"img", "video", "audio", "source"}:
            self._media(normalized_tag, attributes)
        elif normalized_tag == "iframe":
            self._url_surface(
                PublicSurfaceKind.RESOURCE_REFERENCE,
                attributes.get("src"),
                "html:iframe[src]",
            )
        elif normalized_tag == "object":
            self._url_surface(
                PublicSurfaceKind.RESOURCE_REFERENCE,
                attributes.get("data"),
                "html:object[data]",
                media_type=attributes.get("type"),
            )
        elif normalized_tag == "embed":
            self._url_surface(
                PublicSurfaceKind.RESOURCE_REFERENCE,
                attributes.get("src"),
                "html:embed[src]",
                media_type=attributes.get("type"),
            )

    def _link(self, attributes: dict[str, str]) -> None:
        href = attributes.get("href")
        relations = _relations(attributes.get("rel"))
        media_type = attributes.get("type")
        relation = " ".join(sorted(relations)) or None
        if "canonical" in relations:
            self._url_surface(
                PublicSurfaceKind.CANONICAL_LINK,
                href,
                "html:link[rel=canonical]",
                relation=relation,
                media_type=media_type,
            )
        if "alternate" in relations and _normalized_media_type(media_type) not in _FEED_TYPES:
            self._url_surface(
                PublicSurfaceKind.ALTERNATE_LINK,
                href,
                "html:link[rel=alternate]",
                relation=relation,
                media_type=media_type,
            )
        if "stylesheet" in relations:
            self._url_surface(
                PublicSurfaceKind.STYLESHEET,
                href,
                "html:link[rel=stylesheet]",
                relation=relation,
                media_type=media_type,
            )
        if relations.intersection(_RESOURCE_LINK_RELS):
            self._url_surface(
                PublicSurfaceKind.RESOURCE_REFERENCE,
                href,
                "html:link[resource]",
                relation=relation,
                media_type=media_type,
            )

    def _anchor(self, attributes: dict[str, str]) -> None:
        href = attributes.get("href")
        media_type = _normalized_media_type(attributes.get("type"))
        if not _looks_like_document(href, media_type):
            return
        self._url_surface(
            PublicSurfaceKind.DOCUMENT_LINK,
            href,
            "html:a[document]",
            media_type=media_type,
        )

    def _media(self, tag: str, attributes: dict[str, str]) -> None:
        self._url_surface(
            PublicSurfaceKind.MEDIA_LINK,
            attributes.get("src"),
            f"html:{tag}[src]",
            media_type=attributes.get("type"),
        )
        if tag == "video":
            self._url_surface(
                PublicSurfaceKind.MEDIA_LINK,
                attributes.get("poster"),
                "html:video[poster]",
            )

    def _url_surface(
        self,
        kind: PublicSurfaceKind,
        raw_url: str | None,
        source_locator: str,
        *,
        relation: str | None = None,
        http_method: str | None = None,
        media_type: str | None = None,
    ) -> None:
        if len(self.descriptors) >= self.remaining:
            return
        target = _resolved_url(self.base_url, raw_url)
        if target is None:
            return
        descriptor = {
            "kind": kind,
            "source_locator": source_locator,
            "target_url": target,
            "relation": relation,
            "http_method": http_method,
            "media_type": _normalized_media_type(media_type),
        }
        key = tuple(descriptor.items())
        if key in self._seen:
            return
        self._seen.add(key)
        self.descriptors.append(descriptor)


def _resolved_url(base_url: str, raw_url: str | None) -> str | None:
    if raw_url is None:
        return None
    candidate = raw_url.strip()
    if not candidate or len(candidate) > _MAX_RAW_URL_LENGTH:
        return None
    try:
        return CanonicalUrl(urljoin(base_url, candidate)).value
    except ValueError:
        return None


def _looks_like_document(raw_url: str | None, media_type: str | None) -> bool:
    if media_type in _DOCUMENT_MIME_TYPES:
        return True
    if raw_url is None:
        return False
    path = urlsplit(raw_url).path.casefold()
    return any(path.endswith(extension) for extension in _DOCUMENT_EXTENSIONS)


def _relations(raw: str | None) -> set[str]:
    return {token.casefold() for token in raw.split()} if raw else set()


def _normalized_media_type(raw: str | None) -> str | None:
    if raw is None:
        return None
    normalized = raw.split(";", 1)[0].strip().casefold()
    return normalized or None


def _kind(descriptor: dict[str, str | PublicSurfaceKind | None]) -> PublicSurfaceKind:
    value = descriptor["kind"]
    assert isinstance(value, PublicSurfaceKind)
    return value


def _string(value: str | PublicSurfaceKind | None) -> str | None:
    return value if isinstance(value, str) else None
