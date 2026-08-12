from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from cip.modules.collection_orchestration.application.adapter_composition import (
    RuntimeSecretProviders,
)
from cip.modules.collection_orchestration.application.provider_secret_supplier import (
    connected_secret_supplier,
)
from cip.modules.collection_orchestration.application.search_archive_registration import (
    SearchArchiveSecretProviders,
)


def build_runtime_secret_providers(
    factory: sessionmaker[Session],
) -> RuntimeSecretProviders:
    return RuntimeSecretProviders(
        search_archives=SearchArchiveSecretProviders(
            brave_token_provider=connected_secret_supplier(
                factory,
                source_id="brave-search-api",
                secret_name="api_token",
            ),
            github_code_search_token_provider=connected_secret_supplier(
                factory,
                source_id="github-code-search-metadata",
                secret_name="api_token",
            ),
            patentsview_api_key_provider=connected_secret_supplier(
                factory,
                source_id="patentsview-patent-metadata",
                secret_name="api_key",
            ),
            mojeek_api_key_provider=connected_secret_supplier(
                factory,
                source_id="mojeek-web-search-metadata",
                secret_name="api_key",
            ),
            marginalia_api_key_provider=connected_secret_supplier(
                factory,
                source_id="marginalia-web-search-metadata",
                secret_name="api_key",
            ),
        ),
        certspotter_token_provider=connected_secret_supplier(
            factory,
            source_id="certspotter-ct",
            secret_name="api_token",
        ),
        phishtank_token_provider=connected_secret_supplier(
            factory,
            source_id="phishtank-verified-online",
            secret_name="api_token",
        ),
        teamtailor_token_provider=connected_secret_supplier(
            factory,
            source_id="teamtailor-public-jobs",
            secret_name="api_token",
        ),
    )
