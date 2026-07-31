"""Immutable domain models shared by the analyzer and reporters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from typing import Any


class Severity(StrEnum):
    """Finding severity, ordered from least to most important."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def rank(self) -> int:
        return (Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH).index(self)


@dataclass(frozen=True, slots=True)
class Finding:
    """A single actionable code-health issue."""

    rule_id: str
    severity: Severity
    message: str
    path: str
    line: int
    column: int
    symbol: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["severity"] = self.severity.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Finding:
        return cls(
            rule_id=str(data["rule_id"]),
            severity=Severity(str(data["severity"])),
            message=str(data["message"]),
            path=str(data["path"]),
            line=int(data["line"]),
            column=int(data["column"]),
            symbol=str(data["symbol"]) if data.get("symbol") is not None else None,
        )


@dataclass(frozen=True, slots=True)
class FileMetrics:
    """Small, explainable metrics collected from one Python module."""

    physical_lines: int = 0
    code_lines: int = 0
    functions: int = 0
    async_functions: int = 0
    classes: int = 0
    imports: int = 0
    max_complexity: int = 1

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileMetrics:
        return cls(**{field: int(value) for field, value in data.items()})


@dataclass(frozen=True, slots=True)
class FileReport:
    """Analysis result for one file."""

    path: str
    digest: str
    metrics: FileMetrics
    findings: tuple[Finding, ...] = ()
    cached: bool = False

    def as_cached(self) -> FileReport:
        return replace(self, cached=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "digest": self.digest,
            "cached": self.cached,
            "metrics": asdict(self.metrics),
            "findings": [finding.to_dict() for finding in self.findings],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileReport:
        return cls(
            path=str(data["path"]),
            digest=str(data["digest"]),
            cached=bool(data.get("cached", False)),
            metrics=FileMetrics.from_dict(data["metrics"]),
            findings=tuple(Finding.from_dict(item) for item in data["findings"]),
        )


@dataclass(frozen=True, slots=True)
class ScanReport:
    """Deterministic result for a complete scan."""

    root: str
    files: tuple[FileReport, ...]
    dependency_cycles: tuple[tuple[str, ...], ...] = ()

    @property
    def findings(self) -> tuple[Finding, ...]:
        return tuple(
            sorted(
                (finding for report in self.files for finding in report.findings),
                key=lambda item: (item.path, item.line, item.column, item.rule_id),
            )
        )

    @property
    def score(self) -> int:
        weights = {
            Severity.INFO: 0,
            Severity.LOW: 1,
            Severity.MEDIUM: 4,
            Severity.HIGH: 10,
        }
        cycle_penalty = 5 * len(self.dependency_cycles)
        return max(0, 100 - sum(weights[item.severity] for item in self.findings) - cycle_penalty)

    def to_dict(self) -> dict[str, Any]:
        counts = {
            severity.value: sum(item.severity is severity for item in self.findings)
            for severity in Severity
        }
        return {
            "root": self.root,
            "score": self.score,
            "summary": {
                "files": len(self.files),
                "findings": len(self.findings),
                "cached_files": sum(file.cached for file in self.files),
                "by_severity": counts,
                "dependency_cycles": len(self.dependency_cycles),
            },
            "cycles": [list(cycle) for cycle in self.dependency_cycles],
            "files": [file.to_dict() for file in self.files],
        }
