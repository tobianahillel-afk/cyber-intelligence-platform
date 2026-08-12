from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class GoogleSearchContractStatus(StrEnum):
    AWAITING_ELIGIBLE_ROUTE = "awaiting_eligible_route"
    EXISTING_CUSTOMER_API = "existing_customer_api"
    PROVIDER_AUTHORIZED_BROWSER = "provider_authorized_browser"
    CANONICAL_REPLACEMENT = "canonical_replacement"


class GoogleSearchRouteUnavailable(RuntimeError):
    """Raised when no governed automated Google-search route is currently eligible."""


class _CustomSearchApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    closed_to_new_customers: bool
    existing_customer_sunset: date
    api_base_url: str
    entitlement_evidence_id: str | None = Field(default=None, max_length=200)
    api_key_secret_ref: str | None = Field(default=None, max_length=300)
    search_engine_id_secret_ref: str | None = Field(default=None, max_length=300)


class _BrowserRouteModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    provider_permission_evidence_id: str | None = Field(default=None, max_length=200)
    provider_permission_verified: bool = False
    provider_permission_issued_at: date | None = None
    provider_permission_expires_at: date | None = None
    human_checkpoint_required: bool
    captcha_bypass_allowed: bool
    anti_bot_bypass_allowed: bool


class _CanonicalReplacementModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved_source_ids: tuple[str, ...] = ()


class _AnalystRouteModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


class _GoogleSearchContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewed_at: date
    status: GoogleSearchContractStatus
    official_references: tuple[str, ...] = Field(min_length=1)
    custom_search_api: _CustomSearchApiModel
    browser_route: _BrowserRouteModel
    canonical_replacement: _CanonicalReplacementModel
    analyst_route: _AnalystRouteModel

    @model_validator(mode="after")
    def validate_route(self) -> _GoogleSearchContractModel:
        _validate_official_references(self.official_references)
        _validate_google_api_url(self.custom_search_api.api_base_url)
        _validate_browser_safety(self.browser_route)
        _validate_status_requirements(self)
        return self


class _GoogleSearchRegistryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    contract: _GoogleSearchContractModel


@dataclass(frozen=True, slots=True)
class GoogleSearchContract:
    reviewed_at: date
    status: GoogleSearchContractStatus
    api_base_url: str
    existing_customer_sunset: date
    entitlement_evidence_id: str | None
    api_key_secret_ref: str | None
    search_engine_id_secret_ref: str | None
    browser_enabled: bool
    browser_permission_evidence_id: str | None
    browser_permission_verified: bool
    browser_permission_issued_at: date | None
    browser_permission_expires_at: date | None
    canonical_replacement_source_ids: tuple[str, ...]
    canonical_live_source_ids: tuple[str, ...]
    analyst_route_enabled: bool

    @property
    def automated_route_available(self) -> bool:
        if self.status is GoogleSearchContractStatus.AWAITING_ELIGIBLE_ROUTE:
            return False
        if self.status is GoogleSearchContractStatus.CANONICAL_REPLACEMENT:
            return bool(self.canonical_live_source_ids)
        return True

    def require_automated_route(self) -> None:
        if not self.automated_route_available:
            raise GoogleSearchRouteUnavailable(
                "Google automated search is unavailable until an eligible existing-customer API, "
                "provider-authorized browser route, or approved live-tested canonical replacement "
                "is recorded"
            )


def load_google_search_contract(
    path: Path,
    *,
    live_tested_source_ids: Collection[str] = (),
) -> GoogleSearchContract:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    parsed = _GoogleSearchRegistryModel.model_validate(payload).contract
    browser = parsed.browser_route
    approved = parsed.canonical_replacement.approved_source_ids
    live_ids = frozenset(live_tested_source_ids)
    canonical_live = tuple(source_id for source_id in approved if source_id in live_ids)
    return GoogleSearchContract(
        reviewed_at=parsed.reviewed_at,
        status=parsed.status,
        api_base_url=parsed.custom_search_api.api_base_url,
        existing_customer_sunset=parsed.custom_search_api.existing_customer_sunset,
        entitlement_evidence_id=parsed.custom_search_api.entitlement_evidence_id,
        api_key_secret_ref=parsed.custom_search_api.api_key_secret_ref,
        search_engine_id_secret_ref=parsed.custom_search_api.search_engine_id_secret_ref,
        browser_enabled=browser.enabled,
        browser_permission_evidence_id=browser.provider_permission_evidence_id,
        browser_permission_verified=browser.provider_permission_verified,
        browser_permission_issued_at=browser.provider_permission_issued_at,
        browser_permission_expires_at=browser.provider_permission_expires_at,
        canonical_replacement_source_ids=approved,
        canonical_live_source_ids=canonical_live,
        analyst_route_enabled=parsed.analyst_route.enabled,
    )


def _validate_official_references(references: tuple[str, ...]) -> None:
    for reference in references:
        parsed = urlparse(reference)
        host = (parsed.hostname or "").casefold()
        if parsed.scheme != "https" or host not in {
            "developers.google.com",
            "support.google.com",
        }:
            raise ValueError("Google contract references must use approved official HTTPS hosts")


def _validate_google_api_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname != "customsearch.googleapis.com":
        raise ValueError("Google Custom Search API must use the official HTTPS API host")
    if parsed.path.rstrip("/") != "/customsearch/v1":
        raise ValueError("Google Custom Search API path must be /customsearch/v1")


def _validate_browser_safety(route: _BrowserRouteModel) -> None:
    if route.captcha_bypass_allowed or route.anti_bot_bypass_allowed:
        raise ValueError("Google browser automation cannot permit CAPTCHA or anti-bot bypass")
    if route.enabled and not route.provider_permission_evidence_id:
        raise ValueError("enabled Google browser automation requires provider permission evidence")


def _validate_status_requirements(contract: _GoogleSearchContractModel) -> None:
    if contract.status is GoogleSearchContractStatus.EXISTING_CUSTOMER_API:
        api = contract.custom_search_api
        if not api.entitlement_evidence_id or not api.api_key_secret_ref:
            raise ValueError("existing-customer API route requires entitlement and API-key refs")
        if not api.search_engine_id_secret_ref:
            raise ValueError("existing-customer API route requires a search-engine-id ref")
    elif contract.status is GoogleSearchContractStatus.PROVIDER_AUTHORIZED_BROWSER:
        browser = contract.browser_route
        if not browser.enabled:
            raise ValueError(
                "provider-authorized browser status requires the browser route enabled"
            )
        if not browser.provider_permission_verified:
            raise ValueError("provider-authorized browser requires verified provider permission")
        if not browser.provider_permission_issued_at or not browser.provider_permission_expires_at:
            raise ValueError("provider-authorized browser requires permission validity dates")
        if browser.provider_permission_expires_at < browser.provider_permission_issued_at:
            raise ValueError("provider browser permission expiry cannot precede issuance")
        if browser.provider_permission_expires_at < contract.reviewed_at:
            raise ValueError("provider browser permission is expired at contract review date")
    elif contract.status is GoogleSearchContractStatus.CANONICAL_REPLACEMENT:
        if not contract.canonical_replacement.approved_source_ids:
            raise ValueError("canonical replacement status requires at least one approved source")
