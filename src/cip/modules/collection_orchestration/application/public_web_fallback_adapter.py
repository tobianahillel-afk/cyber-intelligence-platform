from __future__ import annotations

from cip.modules.source_governance.domain.models import DataCategory


class PublicWebFallbackAdapter:
    adapter_id = "public-web-browser-fallback"
    data_category = DataCategory.OFFICIAL_DOCUMENT_DISCOVERY
