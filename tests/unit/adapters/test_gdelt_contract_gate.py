from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from cip.adapters.sources.gdelt.contract import (
    GdeltApiContract,
    GdeltContractStatus,
    GdeltContractUnavailable,
    load_gdelt_api_contract,
)

_POLICY_PATH = Path("policies/gdelt_api_contract.yml")


def test_checked_in_gdelt_contract_is_fail_closed() -> None:
    contract = load_gdelt_api_contract(_POLICY_PATH)

    assert contract.product_generation == "GDELT 5"
    assert contract.status is GdeltContractStatus.AWAITING_OFFICIAL_CONTRACT
    assert contract.api_base_url is None
    assert contract.api_version is None
    assert contract.schema_reference is None
    assert contract.storage_terms_reference is None
    assert contract.adapter_implementation_allowed is False
    with pytest.raises(GdeltContractUnavailable):
        contract.require_adapter_contract()


def test_stable_contract_requires_endpoint_version_and_schema(tmp_path: Path) -> None:
    policy = tmp_path / "gdelt.yml"
    policy.write_text(
        """version: 1
contract:
  product_generation: GDELT 5
  status: stable_public_contract
  reviewed_at: 2026-08-12
  official_references:
    - https://blog.gdeltproject.org/2026/06/
  api_base_url: null
  api_version: null
  schema_reference: null
  storage_terms_reference: null
""",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="requires API base URL"):
        load_gdelt_api_contract(policy)


@pytest.mark.parametrize(
    "legacy_url",
    (
        "https://api.gdeltproject.org/api/v1/search",
        "https://api.gdeltproject.org/api/v2/doc/doc",
    ),
)
def test_legacy_api_cannot_satisfy_gdelt5_gate(tmp_path: Path, legacy_url: str) -> None:
    policy = tmp_path / "gdelt.yml"
    policy.write_text(
        _stable_contract_yaml(api_base_url=legacy_url),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="legacy GDELT API endpoints"):
        load_gdelt_api_contract(policy)


@pytest.mark.parametrize(
    "untrusted_url",
    (
        "https://example.com/future-api",
        "https://evilgdeltproject.org/future-api",
        "https://gdeltproject.org.example.com/future-api",
    ),
)
def test_future_stable_contract_rejects_non_gdelt_lookalikes(
    tmp_path: Path,
    untrusted_url: str,
) -> None:
    policy = tmp_path / "gdelt.yml"
    policy.write_text(
        _stable_contract_yaml(api_base_url=untrusted_url),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="official HTTPS GDELT host"):
        load_gdelt_api_contract(policy)


def test_complete_official_future_contract_opens_only_the_contract_gate(tmp_path: Path) -> None:
    policy = tmp_path / "gdelt.yml"
    policy.write_text(
        _stable_contract_yaml(api_base_url="https://api.gdeltproject.org/future-api"),
        encoding="utf-8",
    )

    contract = load_gdelt_api_contract(policy)

    assert isinstance(contract, GdeltApiContract)
    assert contract.adapter_implementation_allowed is True
    contract.require_adapter_contract()


def _stable_contract_yaml(*, api_base_url: str) -> str:
    return f"""version: 1
contract:
  product_generation: GDELT 5
  status: stable_public_contract
  reviewed_at: 2026-08-12
  official_references:
    - https://blog.gdeltproject.org/2026/06/
  api_base_url: {api_base_url}
  api_version: future-contract-version
  schema_reference: https://gdeltproject.org/future-schema
  storage_terms_reference: https://gdeltproject.org/future-storage-terms
"""
