from pathlib import Path

from cip.modules.source_activation.domain.models import ActivationStage
from cip.modules.source_activation.infrastructure.inventory import load_activation_inventory

ACTIVATION_PATH = Path("policies/source_activation.yml")
PYPROJECT_PATH = Path("pyproject.toml")
WEB_PACKAGE_PATH = Path("apps/web/package.json")
DECISION_PATH = Path("docs/source_activation/SA_09_BROWSER_RUNTIME_DECISION.md")

BROWSER_DEPENDENCY_TOKENS = (
    "playwright",
    "selenium",
    "puppeteer",
)


def test_sa09_does_not_add_browser_automation_dependencies() -> None:
    manifests = (
        PYPROJECT_PATH.read_text(encoding="utf-8").lower(),
        WEB_PACKAGE_PATH.read_text(encoding="utf-8").lower(),
    )

    for manifest in manifests:
        for token in BROWSER_DEPENDENCY_TOKENS:
            assert token not in manifest


def test_sa09_creates_no_executable_browser_activation() -> None:
    records = load_activation_inventory(ACTIVATION_PATH)
    sa09_records = [record for record in records if record.activation_wave == "SA-09"]

    assert all(ActivationStage.EXECUTABLE not in record.stages for record in sa09_records)


def test_sa09_decision_records_false_trigger_and_reopening_boundary() -> None:
    decision = DECISION_PATH.read_text(encoding="utf-8")

    assert "browser trigger is **false**" in decision
    assert "adds **no browser runtime**" in decision
    assert "official API, feed/export, static HTTP" in decision
    assert "CAPTCHA/MFA" in decision
    assert "proxy/Tor" in decision
    assert "isolated disposable environment" in decision
    assert "generic arbitrary browsing service" in decision
