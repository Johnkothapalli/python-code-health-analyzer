"""Useful built-in checks implemented with Python's standard AST module."""

from __future__ import annotations

import ast
from collections.abc import Iterable

from code_health.models import Finding, Severity
from code_health.rules.base import CollectingVisitor, Rule


def _qualified_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _qualified_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _is_mutable_default(node: ast.expr) -> bool:
    if isinstance(node, (ast.List, ast.Dict, ast.Set)):
        return True
    return isinstance(node, ast.Call) and _qualified_name(node.func) in {"dict", "list", "set"}


class _MutableDefaultVisitor(CollectingVisitor):
    rule_id = "CH001"
    severity = Severity.HIGH

    def _check(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        defaults: list[ast.expr] = list(node.args.defaults)
        defaults.extend(item for item in node.args.kw_defaults if item is not None)
        for default in defaults:
            if _is_mutable_default(default):
                self.add(
                    default,
                    "Mutable default arguments persist across calls; "
                    "use None and create the value inside.",
                    node.name,
                )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check(node)


class MutableDefaultRule(Rule):
    rule_id = "CH001"
    severity = Severity.HIGH
    description = "Mutable function default"

    def analyze(self, tree: ast.AST, path: str) -> Iterable[Finding]:
        visitor = _MutableDefaultVisitor(path)
        visitor.visit(tree)
        return visitor.findings


class _DangerousCallVisitor(CollectingVisitor):
    rule_id = "CH002"
    severity = Severity.HIGH
    dangerous = {"eval", "exec", "pickle.load", "pickle.loads", "yaml.load"}

    def visit_Call(self, node: ast.Call) -> None:
        name = _qualified_name(node.func)
        if name in self.dangerous:
            self.add(node, f"Avoid `{name}` with untrusted input; use a safe parser instead.", name)
        self.generic_visit(node)


class DangerousCallRule(Rule):
    rule_id = "CH002"
    severity = Severity.HIGH
    description = "Potentially unsafe dynamic execution or deserialization"

    def analyze(self, tree: ast.AST, path: str) -> Iterable[Finding]:
        visitor = _DangerousCallVisitor(path)
        visitor.visit(tree)
        return visitor.findings


class _ExceptionVisitor(CollectingVisitor):
    rule_id = "CH003"
    severity = Severity.MEDIUM

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self.add(
                node,
                "Bare `except` also catches process-exit exceptions; catch a specific error.",
            )
        elif _qualified_name(node.type) in {"Exception", "BaseException"}:
            self.add(
                node,
                "Broad exception handling can hide programming errors; narrow the exception.",
            )
        self.generic_visit(node)


class BroadExceptionRule(Rule):
    rule_id = "CH003"
    severity = Severity.MEDIUM
    description = "Bare or overly broad exception handler"

    def analyze(self, tree: ast.AST, path: str) -> Iterable[Finding]:
        visitor = _ExceptionVisitor(path)
        visitor.visit(tree)
        return visitor.findings


class _BlockingAsyncVisitor(CollectingVisitor):
    rule_id = "CH004"
    severity = Severity.MEDIUM
    blocking_calls = {
        "requests.delete",
        "requests.get",
        "requests.patch",
        "requests.post",
        "requests.put",
        "subprocess.call",
        "subprocess.run",
        "time.sleep",
    }

    def __init__(self, path: str) -> None:
        super().__init__(path)
        self._async_context: list[bool] = []

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._async_context.append(True)
        self.generic_visit(node)
        self._async_context.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._async_context.append(False)
        self.generic_visit(node)
        self._async_context.pop()

    def visit_Call(self, node: ast.Call) -> None:
        name = _qualified_name(node.func)
        if self._async_context and self._async_context[-1] and name in self.blocking_calls:
            self.add(
                node,
                f"Blocking call `{name}` inside async code can stall the event loop.",
                name,
            )
        self.generic_visit(node)


class BlockingAsyncRule(Rule):
    rule_id = "CH004"
    severity = Severity.MEDIUM
    description = "Blocking operation inside an async function"

    def analyze(self, tree: ast.AST, path: str) -> Iterable[Finding]:
        visitor = _BlockingAsyncVisitor(path)
        visitor.visit(tree)
        return visitor.findings


def default_rules() -> tuple[Rule, ...]:
    """Create the default immutable rule set."""

    return (
        MutableDefaultRule(),
        DangerousCallRule(),
        BroadExceptionRule(),
        BlockingAsyncRule(),
    )
