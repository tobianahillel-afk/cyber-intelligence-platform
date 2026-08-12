from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class GdeltContractStatus(StrEnum):
    AWAITING_OFFICIAL_CONTRACT = "awaiting_official_contract"
    STABLE_PUBLIC_CONTRACT = "stable_public_contract"


class GdeltContractUnavailable(RuntimeError):
    """Raised when the current official GDELT API contract is not implementation-ready."""


class _GdeltContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_generation: str = Field(min_length=1, max_length=100)
    status: GdeltContractStatus
    reviewed_at: date
    official_references: tuple[str, ...] = Field(min_length=1)
    api_base_url: str | None = None
    api_version: str | None = Field(default=None, max_length=100)
    schema_reference: str | None = None
    storage_terms_reference: str | None = None

    @model_validator(mode="after")
    def validate_contract_readiness(self) -> _GdeltContractModel:
        _validate_official_references(self.official_references)
        if self.status is GdeltContractStatus.STABLE_PUBLIC_CONTRACT:
            if not self.api_base_url or not self.api_version or not self.schema_reference:
                raise ValueError(
                    "stable GDELT contract requires API base URL, version, and schema reference"
                )
            _validate_current_endpoint(self.api_base_url)
            _validate_official_url(self.schema_reference)
        return self


class _GdeltRegistryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    contract: _GdeltContractModel


@dataclass(frozen=True, slots=True)
class GdeltApiContract:
    product_generation: str
    status: GdeltContractStatus
    reviewed_at: date
    official_references: tuple[str, ...]
    api_base_url: str | None
    api_version: str | None
    schema_reference: str | None
    storage_terms_reference: str | None

    @property
    def adapter_implementation_allowed(self) -> bool:
        return self.status is GdeltContractStatus.STABLE_PUBLIC_CONTRACT

    def require_adapter_contract(self) -> None:
        if not self.adapter_implementation_allowed:
            raise GdeltContractUnavailable(
                "GDELT adapter implementation is blocked until an official stable current API "
                "contract is published and recorded"
            )


def load_gdelt_api_contract(path: Path) -> GdeltApiContract:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    parsed = _GdeltRegistryModel.model_validate(payload).contract
    return GdeltApiContract(
        product_generation=parsed.product_generation.strip(),
        status=parsed.status,
        reviewed_at=parsed.reviewed_at,
        official_references=parsed.official_references,
        api_base_url=parsed.api_base_url,
        api_version=parsed.api_version,
        schema_reference=parsed.schema_reference,
        storage_terms_reference=parsed.storage_terms_reference,
    )


def _validate_official_references(references: tuple[str, ...]) -> None:
    for reference in references:
        _validate_official_url(reference)


def _validate_official_url(value: str) -> None:
    parsed = urlparse(value)
    host = (parsed.hostname or "").casefold()
    if parsed.scheme != "https" or not _is_official_gdelt_host(host):
        raise ValueError("GDELT contract references must use an official HTTPS GDELT host")


def _is_official_gdelt_host(host: str) -> bool:
    return host == "gdeltproject.org" or host.endswith(".gdeltproject.org")


def _validate_current_endpoint(value: str) -> None:
    _validate_official_url(value)
    path = urlparse(value).path.casefold()
    if "/api/v1/" in path or "/api/v2/" in path:
        raise ValueError(
            "legacy GDELT API endpoints cannot satisfy the current GDELT contract gate"
        )
