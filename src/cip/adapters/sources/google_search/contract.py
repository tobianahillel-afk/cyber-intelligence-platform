from __future__ import annotations

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
    canonical_replacement_source_ids: tuple[str, ...]
    analyst_route_enabled: bool

    @property
    def automated_route_available(self) -> bool:
        return self.status is not GoogleSearchContractStatus.AWAITING_ELIGIBLE_ROUTE

    def require_automated_route(self) -> None:
        if not self.automated_route_available:
            raise GoogleSearchRouteUnavailable(
                "Google automated search is unavailable until an eligible existing-customer API, "
                "provider-authorized browser route, or approved canonical replacement is recorded"
            )


def load_google_search_contract(path: Path) -> GoogleSearchContract:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    parsed = _GoogleSearchRegistryModel.model_validate(payload).contract
    return GoogleSearchContract(
        reviewed_at=parsed.reviewed_at,
        status=parsed.status,
        api_base_url=parsed.custom_search_api.api_base_url,
        existing_customer_sunset=parsed.custom_search_api.existing_customer_sunset,
        entitlement_evidence_id=parsed.custom_search_api.entitlement_evidence_id,
        api_key_secret_ref=parsed.custom_search_api.api_key_secret_ref,
        search_engine_id_secret_ref=parsed.custom_search_api.search_engine_id_secret_ref,
        browser_enabled=parsed.browser_route.enabled,
        browser_permission_evidence_id=parsed.browser_route.provider_permission_evidence_id,
        canonical_replacement_source_ids=parsed.canonical_replacement.approved_source_ids,
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
        if not contract.browser_route.enabled:
            raise ValueError(
                "provider-authorized browser status requires the browser route enabled"
            )
    elif contract.status is GoogleSearchContractStatus.CANONICAL_REPLACEMENT:
        if not contract.canonical_replacement.approved_source_ids:
            raise ValueError("canonical replacement status requires at least one approved source")
