from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin

from cip.modules.public_footprint.domain.url_identity import CanonicalUrl


class _AnchorParser(HTMLParser):
    def __init__(self, *, max_links: int) -> None:
        super().__init__(convert_charrefs=True)
        self._max_links = max_links
        self.links: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.casefold() != "a" or len(self.links) >= self._max_links:
            return
        values = {name.casefold(): value for name, value in attrs}
        href = values.get("href")
        if href is None or not href.strip():
            return
        rel = values.get("rel") or ""
        if "nofollow" in {part.casefold() for part in rel.split()}:
            return
        self.links.append(href)


def extract_public_html_links(
    body: bytes,
    *,
    base_url: str,
    max_links: int,
) -> tuple[str, ...]:
    if max_links < 1:
        return ()
    parser = _AnchorParser(max_links=max_links)
    parser.feed(body.decode("utf-8", errors="replace"))
    parser.close()
    discovered: list[str] = []
    seen: set[str] = set()
    for href in parser.links:
        try:
            canonical = CanonicalUrl(urljoin(base_url, href)).value
        except (TypeError, ValueError):
            continue
        if canonical in seen:
            continue
        seen.add(canonical)
        discovered.append(canonical)
        if len(discovered) >= max_links:
            break
    return tuple(discovered)
