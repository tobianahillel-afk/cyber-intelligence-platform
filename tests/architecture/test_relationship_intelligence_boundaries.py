from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path("src/cip/modules/relationship_intelligence")
DISALLOWED = (
    "httpx",
    "requests",
    "urllib.request",
    "cip.adapters.sources",
    "cip.modules.opportunities",
)


def test_relationship_intelligence_has_no_network_or_opportunity_imports() -> None:
    violations: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            for module in _imports(node):
                if module.startswith(DISALLOWED):
                    violations.append(f"{path}:{node.lineno}: {module}")

    assert not violations, "\n".join(violations)


def _imports(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module:
        return (node.module,)
    return ()
