from __future__ import annotations

from urllib.parse import urlencode

from cip.modules.public_footprint.domain import SearchQueryTemplate

_GOOGLE_SEARCH_URL = "https://www.google.com/search"


def build_google_analyst_search_url(
    template: SearchQueryTemplate,
    organization: str,
) -> str:
    """Build an analyst-opened Google search URL without performing network I/O."""
    query = template.render(organization)
    return f"{_GOOGLE_SEARCH_URL}?{urlencode({'q': query})}"
