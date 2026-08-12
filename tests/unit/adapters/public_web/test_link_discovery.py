from cip.adapters.sources.public_web.link_discovery import extract_public_html_links


def test_extract_public_html_links_normalizes_deduplicates_and_skips_nofollow() -> None:
    body = b"""
    <html><body>
      <a href="/about#team">About</a>
      <a href="https://example.com/about">Duplicate</a>
      <a href="/ignored" rel="nofollow external">Ignored</a>
      <a href="mailto:security@example.com">Mail</a>
      <a href="javascript:void(0)">JS</a>
      <a href="?b=2&a=1">Query</a>
    </body></html>
    """

    assert extract_public_html_links(
        body,
        base_url="https://example.com/",
        max_links=10,
    ) == (
        "https://example.com/about",
        "https://example.com/?a=1&b=2",
    )


def test_extract_public_html_links_respects_document_order_and_limit() -> None:
    body = b'<a href="/one">1</a><a href="/two">2</a><a href="/three">3</a>'

    assert extract_public_html_links(
        body,
        base_url="https://example.com/",
        max_links=2,
    ) == ("https://example.com/one", "https://example.com/two")
