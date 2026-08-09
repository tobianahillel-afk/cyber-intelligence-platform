from __future__ import annotations

import ast
from pathlib import Path

MODULE_ROOT = Path("src/cip/modules/conditional_integrations")
DOMAIN_ROOT = MODULE_ROOT / "domain"

_FORBIDDEN_MODULE_IMPORTS = (
    "httpx",
    "requests",
    "urllib.request",
    "playwright",
    "selenium",
    "cip.adapters",
    "cip.modules.collection_orchestration",
    "cip.modules.opportunities",
    "cip.modules.outreach",
)
_FORBIDDEN_DOMAIN_IMPORTS = (
    "fastapi",
    "sqlalchemy",
    "cip.modules.conditional_integrations.api",
    "cip.modules.conditional_integrations.infrastructure",
)


def test_conditional_integrations_domain_cannot_execute_provider_network_paths() -> None:
    violations = _find_forbidden_imports(MODULE_ROOT, _FORBIDDEN_MODULE_IMPORTS)

    assert violations == []


def test_conditional_integrations_domain_is_framework_and_infrastructure_free() -> None:
    violations = _find_forbidden_imports(DOMAIN_ROOT, _FORBIDDEN_DOMAIN_IMPORTS)

    assert violations == []


def test_conditional_integrations_has_no_browser_or_bypass_runtime() -> None:
    forbidden_tokens = (
        "webdriver",
        "browser.new_page",
        "page.goto(",
        "captcha_solver",
        "copy_cookies",
        "proxy_rotation",
        "discord.Client",
        "linkedin_api",
    )
    violations: list[str] = []
    for path in _python_files(MODULE_ROOT):
        text = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            if token in text:
                violations.append(f"{path}:{token}")

    assert violations == []


def _find_forbidden_imports(root: Path, prefixes: tuple[str, ...]) -> list[str]:
    violations: list[str] = []
    for path in _python_files(root):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            for imported in _imported_names(node):
                if any(
                    imported == prefix or imported.startswith(f"{prefix}.")
                    for prefix in prefixes
                ):
                    violations.append(f"{path}:{node.lineno}:{imported}")
    return sorted(violations)


def _imported_names(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        return (node.module,)
    return ()


def _python_files(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(path for path in root.rglob("*.py") if path.is_file()))
