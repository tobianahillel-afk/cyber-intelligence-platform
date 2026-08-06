from __future__ import annotations

import pytest

from cip.modules.threat_telemetry.domain.models import IndicatorType, normalize_indicator


def test_normalizes_public_ip_domain_url_hash_certificate_and_email() -> None:
    assert normalize_indicator(IndicatorType.IPV4, "8.8.8.8") == "8.8.8.8"
    assert (
        normalize_indicator(IndicatorType.IPV6, "2001:4860:4860:0:0:0:0:8888")
        == "2001:4860:4860::8888"
    )
    assert normalize_indicator(IndicatorType.DOMAIN, "BÜCHER.Example.") == (
        "xn--bcher-kva.example"
    )
    assert normalize_indicator(
        IndicatorType.URL,
        "HTTPS://Example.COM:443/path?b=2&a=1#fragment",
    ) == "https://example.com/path?a=1&b=2"
    assert normalize_indicator(IndicatorType.FILE_HASH, "A" * 64) == (
        f"file:sha256:{'a' * 64}"
    )
    assert normalize_indicator(
        IndicatorType.CERTIFICATE_FINGERPRINT,
        ":".join(["AB"] * 20),
    ) == f"certificate:sha1:{'ab' * 20}"
    assert normalize_indicator(
        IndicatorType.EMAIL_ADDRESS,
        "Threat.Actor@BÜCHER.Example",
    ) == "threat.actor@xn--bcher-kva.example"


@pytest.mark.parametrize(
    ("indicator_type", "value", "message"),
    (
        (IndicatorType.IPV4, "10.0.0.1", "non-global"),
        (IndicatorType.IPV6, "::1", "non-global"),
        (IndicatorType.DOMAIN, "localhost", "public multi-label"),
        (IndicatorType.DOMAIN, "host.internal", "internal domain"),
        (IndicatorType.URL, "file:///tmp/sample", "http or https"),
        (IndicatorType.URL, "https://user:pass@example.com", "credentials"),
        (IndicatorType.FILE_HASH, "not-a-hash", "hexadecimal"),
        (IndicatorType.EMAIL_ADDRESS, "missing-at.example", "one @"),
    ),
)
def test_rejects_unsafe_or_malformed_indicators(
    indicator_type: IndicatorType,
    value: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        normalize_indicator(indicator_type, value)
