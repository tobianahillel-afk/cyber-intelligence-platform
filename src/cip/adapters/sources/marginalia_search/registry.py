from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

MARGINALIA_API_HOST = "api2.marginalia-search.com"


class _MarginaliaEntitlementModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_host: str = Field(default=MARGINALIA_API_HOST, min_length=1, max_length=253)
    commercial_use_rights: bool = False
    plan: str = Field(default="unprovisioned", min_length=1, max_length=100)
    evidence_reference: str | None = Field(default=None, max_length=1_000)
    api_key_secret_ref: str | None = Field(default=None, max_length=1_000)


class _MarginaliaRegistryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    entitlement: _MarginaliaEntitlementModel


@dataclass(frozen=True, slots=True)
class MarginaliaSearchEntitlement:
    api_host: str = MARGINALIA_API_HOST
    commercial_use_rights: bool = False
    api_key_secret_ref: str | None = None
    plan: str = "unprovisioned"
    evidence_reference: str | None = None

    def __post_init__(self) -> None:
        host = self.api_host.strip().casefold()
        if host != MARGINALIA_API_HOST:
            raise ValueError("Marginalia API host is not approved")
        object.__setattr__(self, "api_host", host)

        plan = self.plan.strip()
        if not plan:
            raise ValueError("Marginalia plan is required")
        object.__setattr__(self, "plan", plan)

        secret_ref = _normalize_optional(self.api_key_secret_ref)
        evidence_reference = _normalize_optional(self.evidence_reference)
        object.__setattr__(self, "api_key_secret_ref", secret_ref)
        object.__setattr__(self, "evidence_reference", evidence_reference)

        if self.commercial_use_rights and evidence_reference is None:
            raise ValueError(
                "Marginalia commercial-use rights require an evidence reference"
            )

    def assert_live_collection_ready(self) -> None:
        if not self.commercial_use_rights:
            raise PermissionError(
                "Marginalia production collection requires commercial-use rights"
            )
        if self.evidence_reference is None:
            raise PermissionError(
                "Marginalia production collection requires entitlement evidence"
            )
        if self.api_key_secret_ref is None:
            raise PermissionError(
                "Marginalia production collection requires an API-key secret ref"
            )


def load_marginalia_search_entitlement(path: Path) -> MarginaliaSearchEntitlement:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    parsed = _MarginaliaRegistryModel.model_validate(payload)
    item = parsed.entitlement
    return MarginaliaSearchEntitlement(
        api_host=item.api_host,
        commercial_use_rights=item.commercial_use_rights,
        api_key_secret_ref=item.api_key_secret_ref,
        plan=item.plan,
        evidence_reference=item.evidence_reference,
    )


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise ValueError("optional Marginalia references must be non-empty when provided")
    return normalized
