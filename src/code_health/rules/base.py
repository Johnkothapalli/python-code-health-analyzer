"""Rule interface and AST visitor utilities."""

from __future__ import annotations

import ast
from abc import ABC, abstractmethod
from collections.abc import Iterable

from code_health.models import Finding, Severity


class Rule(ABC):
    """A stateless rule that can safely be shared across worker threads."""

    rule_id: str
    severity: Severity
    description: str

    @abstractmethod
    def analyze(self, tree: ast.AST, path: str) -> Iterable[Finding]:
        """Return findings for a parsed module."""


class CollectingVisitor(ast.NodeVisitor):
    """Base visitor with a consistent finding factory."""

    rule_id: str
    severity: Severity

    def __init__(self, path: str) -> None:
        self.path = path
        self.findings: list[Finding] = []

    def add(self, node: ast.AST, message: str, symbol: str | None = None) -> None:
        self.findings.append(
            Finding(
                rule_id=self.rule_id,
                severity=self.severity,
                message=message,
                path=self.path,
                line=getattr(node, "lineno", 1),
                column=getattr(node, "col_offset", 0) + 1,
                symbol=symbol,
            )
        )
