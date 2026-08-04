from __future__ import annotations

import ast
from pathlib import Path

SOURCE_ROOT = Path("src/cip")
_FRAMEWORK_PREFIXES = ("alembic", "fastapi", "httpx", "sqlalchemy")
_DOMAIN_FORBIDDEN_FRAGMENTS = (".adapters", ".api", ".infrastructure")
_CONNECTOR_FORBIDDEN_PREFIXES = (
    "cip.modules.evidence.infrastructure",
    "cip.modules.opportunities.infrastructure",
    "cip.modules.organizations.infrastructure",
    "sqlalchemy",
)


def test_domain_modules_depend_only_on_inner_layers() -> None:
    violations: list[str] = []
    for path in _domain_files():
        for module, lineno in _imports(path):
            if module.startswith(_FRAMEWORK_PREFIXES) or any(
                fragment in module for fragment in _DOMAIN_FORBIDDEN_FRAGMENTS
            ):
                violations.append(f"{path}:{lineno} imports {module}")

    assert violations == [], "Domain layer violations: " + "; ".join(violations)


def test_external_connectors_do_not_import_database_implementations() -> None:
    violations: list[str] = []
    for path in sorted((SOURCE_ROOT / "adapters").rglob("*.py")):
        for module, lineno in _imports(path):
            if module.startswith(_CONNECTOR_FORBIDDEN_PREFIXES):
                violations.append(f"{path}:{lineno} imports {module}")

    assert violations == [], "Connector layer violations: " + "; ".join(violations)


def _domain_files() -> tuple[Path, ...]:
    return tuple(
        path
        for path in sorted(SOURCE_ROOT.rglob("*.py"))
        if "domain" in path.parts
    )


def _imports(path: Path) -> tuple[tuple[str, int], ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.module, node.lineno))
    return tuple(imports)
