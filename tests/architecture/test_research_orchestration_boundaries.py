from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).parents[2]
MODULE = ROOT / "src" / "cip" / "modules" / "research_orchestration"
DOMAIN = MODULE / "domain"

FORBIDDEN_MODULE_PREFIXES = (
    "httpx",
    "requests",
    "playwright",
    "selenium",
    "cip.adapters",
    "cip.modules.collection_orchestration",
    "cip.modules.opportunities",
    "cip.modules.contacts",
    "cip.modules.outreach",
)
DOMAIN_FORBIDDEN = FORBIDDEN_MODULE_PREFIXES + (
    "fastapi",
    "sqlalchemy",
    "cip.modules.research_orchestration.infrastructure",
)


def test_research_orchestration_has_no_network_browser_or_commercial_side_effect_imports() -> None:
    violations = _violations(MODULE, FORBIDDEN_MODULE_PREFIXES)

    assert violations == []


def test_research_domain_points_inward_only() -> None:
    violations = _violations(DOMAIN, DOMAIN_FORBIDDEN)

    assert violations == []


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
