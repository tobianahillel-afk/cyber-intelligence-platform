from __future__ import annotations

import ast
from pathlib import Path

MODULE_ROOT = Path("src/cip/modules/corporate_changes")
FORBIDDEN_DOMAIN_PREFIXES = (
    "fastapi",
    "sqlalchemy",
    "httpx",
    "requests",
    "cip.adapters",
    "cip.modules.corporate_changes.api",
    "cip.modules.corporate_changes.infrastructure",
)
FORBIDDEN_MODULE_PREFIXES = (
    "httpx",
    "requests",
    "urllib.request",
    "cip.adapters.sources",
    "cip.modules.opportunities",
    "cip.modules.contacts",
    "cip.modules.outreach",
)


def test_corporate_change_domain_has_no_framework_or_adapter_dependencies() -> None:
    violations = _forbidden_imports(
        MODULE_ROOT / "domain",
        FORBIDDEN_DOMAIN_PREFIXES,
    )

    assert not violations, "\n".join(violations)


def test_corporate_change_module_has_no_network_or_commercial_side_effect_paths() -> None:
    violations = _forbidden_imports(MODULE_ROOT, FORBIDDEN_MODULE_PREFIXES)

    assert not violations, "\n".join(violations)


def _forbidden_imports(root: Path, prefixes: tuple[str, ...]) -> list[str]:
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported = _imported_modules(node)
            for module in imported:
                if module.startswith(prefixes):
                    violations.append(f"{path}:{node.lineno}: forbidden import {module}")
    return violations


def _imported_modules(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module:
        return (node.module,)
    return ()
