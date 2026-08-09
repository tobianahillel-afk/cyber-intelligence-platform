from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).parents[2]
MODULE = ROOT / "src" / "cip" / "modules" / "source_activation"
DOMAIN = MODULE / "domain"

MODULE_FORBIDDEN = (
    "httpx",
    "requests",
    "playwright",
    "selenium",
    "cip.adapters",
    "cip.modules.collection_orchestration",
    "cip.modules.opportunities",
    "cip.modules.outreach",
)
DOMAIN_FORBIDDEN = (
    *MODULE_FORBIDDEN,
    "yaml",
    "fastapi",
    "sqlalchemy",
    "cip.modules.source_activation.infrastructure",
)


def test_source_activation_module_cannot_collect_or_project_commercial_state() -> None:
    assert _violations(MODULE, MODULE_FORBIDDEN) == []


def test_source_activation_domain_points_inward_only() -> None:
    assert _violations(DOMAIN, DOMAIN_FORBIDDEN) == []


def _violations(root: Path, forbidden: tuple[str, ...]) -> list[str]:
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            module = _module_name(node)
            if module and module.startswith(forbidden):
                violations.append(f"{path.relative_to(ROOT)} imports {module}")
    return violations


def _module_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.ImportFrom):
        return node.module
    if isinstance(node, ast.Import) and node.names:
        return node.names[0].name
    return None
