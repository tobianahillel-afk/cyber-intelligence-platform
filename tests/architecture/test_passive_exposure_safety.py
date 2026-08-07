from __future__ import annotations

import ast
from pathlib import Path

MODULE_ROOT = Path("src/cip/modules/passive_exposure")
DOMAIN_ROOT = MODULE_ROOT / "domain"
FORBIDDEN_MODULE_IMPORT_PREFIXES = (
    "aiohttp",
    "httpx",
    "requests",
    "socket",
    "subprocess",
    "urllib.request",
    "cip.adapters",
    "cip.modules.opportunities",
)
FORBIDDEN_DOMAIN_IMPORT_PREFIXES = (
    "fastapi",
    "sqlalchemy",
    "cip.modules.organizations",
    "cip.modules.vulnerability_knowledge",
)


def test_passive_exposure_module_has_no_network_or_opportunity_dependency() -> None:
    violations = _violations(MODULE_ROOT, FORBIDDEN_MODULE_IMPORT_PREFIXES)

    assert violations == []


def test_passive_exposure_domain_remains_framework_and_resolution_independent() -> None:
    violations = _violations(DOMAIN_ROOT, FORBIDDEN_DOMAIN_IMPORT_PREFIXES)

    assert violations == []


def test_passive_exposure_domain_has_no_positive_exposure_state() -> None:
    domain_text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(DOMAIN_ROOT.glob("*.py"))
    )

    assert "VERIFIED_EXPOSURE" not in domain_text
    assert "AFFECTED_VERSION" not in domain_text
    assert "COMPROMISED" not in domain_text
    assert "can_support_exposure_conclusion(self) -> bool:\n        return False" in domain_text


def _violations(root: Path, forbidden: tuple[str, ...]) -> list[str]:
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            for module_name in _imported_modules(node):
                if module_name.startswith(forbidden):
                    violations.append(f"{path}:{node.lineno}: {module_name}")
    return violations


def _imported_modules(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        return (node.module,)
    return ()
