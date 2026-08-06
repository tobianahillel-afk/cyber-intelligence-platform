from __future__ import annotations

import ast
from pathlib import Path

MODULE_ROOT = Path("src/cip/modules/threat_telemetry")
FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "httpx",
    "requests",
    "socket",
    "subprocess",
    "urllib.request",
    "cip.modules.opportunities",
    "cip.modules.organizations",
)


def test_threat_telemetry_module_has_no_network_or_commercial_dependencies() -> None:
    violations: list[str] = []
    for path in sorted(MODULE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported = _imported_modules(node)
            for module_name in imported:
                if module_name.startswith(FORBIDDEN_IMPORT_PREFIXES):
                    violations.append(f"{path}:{node.lineno}: {module_name}")

    assert violations == []


def test_threat_telemetry_domain_has_no_organization_identifier() -> None:
    domain_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((MODULE_ROOT / "domain").glob("*.py"))
    )

    assert "organization_id" not in domain_text
    assert "opportunity" not in domain_text.casefold()


def _imported_modules(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        return (node.module,)
    return ()
