from __future__ import annotations

from dataclasses import dataclass

MARGINALIA_API_HOST = "api2.marginalia-search.com"


@dataclass(frozen=True, slots=True)
class MarginaliaSearchEntitlement:
    api_host: str = MARGINALIA_API_HOST
    commercial_use_rights: bool = False
    api_key_secret_ref: str | None = None

    def __post_init__(self) -> None:
        host = self.api_host.strip().casefold()
        if host != MARGINALIA_API_HOST:
            raise ValueError("Marginalia API host is not approved")
        object.__setattr__(self, "api_host", host)

        if self.api_key_secret_ref is not None:
            secret_ref = self.api_key_secret_ref.strip()
            if not secret_ref:
                raise ValueError("api_key_secret_ref must be non-empty when provided")
            object.__setattr__(self, "api_key_secret_ref", secret_ref)

    def assert_live_collection_ready(self) -> None:
        if not self.commercial_use_rights:
            raise PermissionError(
                "Marginalia production collection requires commercial-use rights"
            )
        if self.api_key_secret_ref is None:
            raise PermissionError(
                "Marginalia production collection requires an API-key secret ref"
            )
