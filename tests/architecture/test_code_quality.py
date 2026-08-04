from __future__ import annotations

import ast
from pathlib import Path

SOURCE_ROOT = Path("src/cip")
HARD_MAX_FUNCTION_LINES = 120
HARD_MAX_CLASS_LINES = 300
HARD_MAX_PARAMETERS = 10
HARD_MAX_NESTING_DEPTH = 6

_FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)
_NESTING_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.With,
    ast.AsyncWith,
    ast.Match,
)


def test_functions_stay_within_hard_size_and_parameter_budgets() -> None:
    violations: list[str] = []
    for path, tree in _parsed_source_files():
        for node in ast.walk(tree):
            if not isinstance(node, _FUNCTION_NODES):
                continue
            line_count = _node_line_count(node)
            parameter_count = _parameter_count(node)
            if line_count > HARD_MAX_FUNCTION_LINES:
                violations.append(
                    f"{path}:{node.lineno}:{node.name} has {line_count} lines "
                    f"(max {HARD_MAX_FUNCTION_LINES})"
                )
            if parameter_count > HARD_MAX_PARAMETERS:
                violations.append(
                    f"{path}:{node.lineno}:{node.name} has {parameter_count} parameters "
                    f"(max {HARD_MAX_PARAMETERS})"
                )

    assert violations == [], "Function quality budget violations: " + "; ".join(violations)


def test_classes_stay_within_hard_size_budget() -> None:
    violations = [
        f"{path}:{node.lineno}:{node.name} has {_node_line_count(node)} lines "
        f"(max {HARD_MAX_CLASS_LINES})"
        for path, tree in _parsed_source_files()
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and _node_line_count(node) > HARD_MAX_CLASS_LINES
    ]

    assert violations == [], "Class size budget violations: " + "; ".join(violations)


def test_functions_do_not_exceed_hard_nesting_depth() -> None:
    violations: list[str] = []
    for path, tree in _parsed_source_files():
        for node in ast.walk(tree):
            if not isinstance(node, _FUNCTION_NODES):
                continue
            depth = _max_nesting_depth(node)
            if depth > HARD_MAX_NESTING_DEPTH:
                violations.append(
                    f"{path}:{node.lineno}:{node.name} nesting depth {depth} "
                    f"(max {HARD_MAX_NESTING_DEPTH})"
                )

    assert violations == [], "Nesting-depth violations: " + "; ".join(violations)


def test_application_code_has_no_wildcard_imports() -> None:
    violations = [
        f"{path}:{node.lineno}"
        for path, tree in _parsed_source_files()
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and any(alias.name == "*" for alias in node.names)
    ]

    assert violations == [], "Wildcard imports are forbidden: " + "; ".join(violations)


def _parsed_source_files() -> tuple[tuple[Path, ast.Module], ...]:
    return tuple(
        (
            path,
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path)),
        )
        for path in sorted(SOURCE_ROOT.rglob("*.py"))
    )


def _node_line_count(node: ast.AST) -> int:
    end_lineno = getattr(node, "end_lineno", None)
    lineno = getattr(node, "lineno", None)
    if end_lineno is None or lineno is None:
        raise AssertionError("Python AST node is missing source positions")
    return end_lineno - lineno + 1


def _parameter_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    arguments = node.args
    positional = [*arguments.posonlyargs, *arguments.args]
    if positional and positional[0].arg in {"self", "cls"}:
        positional = positional[1:]
    return (
        len(positional)
        + len(arguments.kwonlyargs)
        + int(arguments.vararg is not None)
        + int(arguments.kwarg is not None)
    )


def _max_nesting_depth(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    def visit(current: ast.AST, depth: int) -> int:
        child_depth = depth + int(isinstance(current, _NESTING_NODES))
        return max(
            [child_depth, *(visit(child, child_depth) for child in ast.iter_child_nodes(current))]
        )

    return max((visit(statement, 0) for statement in node.body), default=0)
