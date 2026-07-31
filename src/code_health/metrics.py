"""Explainable source and cyclomatic-complexity metrics."""

from __future__ import annotations

import ast
import io
import tokenize
from dataclasses import dataclass

from code_health.models import FileMetrics


class _ComplexityCounter(ast.NodeVisitor):
    def __init__(self) -> None:
        self.value = 1

    def visit_If(self, node: ast.If) -> None:
        self.value += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.value += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.value += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.value += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.value += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.value += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.value += max(0, len(node.values) - 1)
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.value += 1 + len(node.ifs)
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        self.value += max(0, len(node.cases) - 1)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Nested functions have their own complexity score.
        return None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return None


def function_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    counter = _ComplexityCounter()
    for statement in node.body:
        counter.visit(statement)
    return counter.value


@dataclass(slots=True)
class _MetricVisitor(ast.NodeVisitor):
    functions: int = 0
    async_functions: int = 0
    classes: int = 0
    imports: int = 0
    max_complexity: int = 1

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, *, is_async: bool) -> None:
        self.functions += 1
        self.async_functions += int(is_async)
        self.max_complexity = max(self.max_complexity, function_complexity(node))
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function(node, is_async=True)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes += 1
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        self.imports += len(node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.imports += len(node.names)


def _code_line_count(source: str) -> int:
    lines: set[int] = set()
    ignored = {
        tokenize.ENCODING,
        tokenize.ENDMARKER,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.NEWLINE,
        tokenize.NL,
        tokenize.COMMENT,
    }
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type not in ignored and token.string.strip():
                lines.add(token.start[0])
    except (IndentationError, tokenize.TokenError):
        return sum(bool(line.strip()) for line in source.splitlines())
    return len(lines)


def collect_metrics(tree: ast.AST, source: str) -> FileMetrics:
    visitor = _MetricVisitor()
    visitor.visit(tree)
    return FileMetrics(
        physical_lines=len(source.splitlines()),
        code_lines=_code_line_count(source),
        functions=visitor.functions,
        async_functions=visitor.async_functions,
        classes=visitor.classes,
        imports=visitor.imports,
        max_complexity=visitor.max_complexity,
    )
