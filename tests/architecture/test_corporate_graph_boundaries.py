from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path("src/cip/modules/corporate_graph")
DOMAIN = ROOT / "domain"
NETWORK_IMPORTS = (
    "httpx",
    "requests",
    "urllib.request",
    "cip.adapters.sources",
    "selenium",
    "playwright",
    "neo4j",
    "networkx",
)
DOMAIN_IMPORTS = (
    "fastapi",
    "sqlalchemy",
    "cip.modules.opportunities",
    "cip.modules.corporate_graph.infrastructure",
)


def test_corporate_graph_has_no_network_collection_or_graph_database_imports() -> None:
    violations = _violations(ROOT, NETWORK_IMPORTS)

    assert not violations, "\n".join(violations)


def test_corporate_graph_domain_is_framework_and_opportunity_independent() -> None:
    violations = _violations(DOMAIN, DOMAIN_IMPORTS)

    assert not violations, "\n".join(violations)


def _violations(root: Path, disallowed: tuple[str, ...]) -> list[str]:
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            for module in _imports(node):
                if module.startswith(disallowed):
                    violations.append(f"{path}:{node.lineno}: {module}")
    return violations


def _imports(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module:
        return (node.module,)
    return ()
