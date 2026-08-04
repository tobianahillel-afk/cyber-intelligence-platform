from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

SOURCE_ROOT = Path("src/cip")
HARD_MAX_SOURCE_LINES = 400


def test_application_modules_stay_below_hard_line_limit() -> None:
    oversized = {
        str(path): _line_count(path)
        for path in _python_files()
        if _line_count(path) > HARD_MAX_SOURCE_LINES
    }

    assert oversized == {}, (
        f"Application modules must stay <= {HARD_MAX_SOURCE_LINES} lines; "
        f"split these files: {oversized}"
    )


def test_scopes_do_not_redefine_top_level_functions_or_classes() -> None:
    duplicates: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        duplicates.extend(_duplicate_definitions(path, tree, scope="module"))

    assert duplicates == [], "Duplicate definitions found: " + "; ".join(duplicates)


def _duplicate_definitions(
    path: Path,
    node: ast.Module | ast.ClassDef,
    *,
    scope: str,
) -> list[str]:
    definitions = [
        child
        for child in node.body
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    counts = Counter(definition.name for definition in definitions)
    duplicates = [
        f"{path}:{scope}:{name}"
        for name, count in sorted(counts.items())
        if count > 1
    ]
    for definition in definitions:
        if isinstance(definition, ast.ClassDef):
            duplicates.extend(
                _duplicate_definitions(
                    path,
                    definition,
                    scope=f"{scope}.{definition.name}",
                )
            )
    return duplicates


def _python_files() -> tuple[Path, ...]:
    return tuple(sorted(SOURCE_ROOT.rglob("*.py")))


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())
