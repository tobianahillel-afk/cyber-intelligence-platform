from __future__ import annotations

import pytest

from cip.modules.passive_exposure.domain.normalization import normalize_domain


@pytest.mark.parametrize(
    "value",
    [
        "service.example",
        "service.invalid",
        "service.onion",
        "device.home.arpa",
    ],
)
def test_rejects_reserved_or_non_public_domain_suffixes(value: str) -> None:
    with pytest.raises(ValueError, match="non-public"):
        normalize_domain(value)
