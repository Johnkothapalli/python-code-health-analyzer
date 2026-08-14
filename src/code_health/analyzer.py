"""Concurrent orchestration for Python source analysis."""

from __future__ import annotations

import ast
import hashlib
import io
import os
import tokenize
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path

from code_health.cache import SQLiteCache
from code_health.graph import ImportGraph
from code_health.metrics import collect_metrics, function_complexity
from code_health.models import FileMetrics, FileReport, Finding, ScanReport, Severity
from code_health.rules import default_rules
from code_health.rules.base import Rule


def _decode_source(raw: bytes) -> str:
    """Decode source bytes using the file's own encoding declaration (PEP 263).

    ``tokenize.detect_encoding`` is the same detection CPython itself uses: it
    reads the first two lines for a coding cookie, honours a UTF-8 BOM, and
    defaults to UTF-8. It raises SyntaxError for an unknown encoding name or a
    BOM that contradicts the cookie, which the caller turns into CH000.

    The raw bytes are left untouched so the digest keeps hashing what is on
    disk, not the decoded text.
    """
    encoding, _ = tokenize.detect_encoding(io.BytesIO(raw).readline)
    return raw.decode(encoding)


def _read_source(path: Path, display_path: str) -> tuple[bytes, str] | FileReport:
    try:
        raw = path.read_bytes()
        return raw, _decode_source(raw)
    # SyntaxError covers an unknown or self-contradicting encoding declaration;
    # UnicodeError covers bytes that the declared encoding can't actually decode.
    except (OSError, UnicodeError, SyntaxError) as error:
        return FileReport(
            path=display_path,
            digest="",
            metrics=FileMetrics(),
            findings=(
                Finding(
                    rule_id="CH000",
                    severity=Severity.HIGH,
                    message=f"Could not read source: {error}",
                    path=display_path,
                    line=1,
                    column=1,
                ),
            ),
        )


def _syntax_error_report(
    display_path: str, digest: str, source: str, error: SyntaxError
) -> FileReport:
    return FileReport(
        path=display_path,
        digest=digest,
        metrics=FileMetrics(physical_lines=len(source.splitlines())),
        findings=(
            Finding(
                rule_id="CH000",
                severity=Severity.HIGH,
                message=f"Syntax error: {error.msg}",
                path=display_path,
                line=error.lineno or 1,
                column=error.offset or 1,
            ),
        ),
    )


def _complexity_findings(tree: ast.AST, path: str, maximum: int) -> list[Finding]:
    findings: list[Finding] = []
    functions = (
        node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    for node in functions:
        complexity = function_complexity(node)
        if complexity <= maximum:
            continue
        findings.append(
            Finding(
                rule_id="CH005",
                severity=Severity.MEDIUM,
                message=f"Cyclomatic complexity is {complexity}; configured maximum is {maximum}.",
                path=path,
                line=node.lineno,
                column=node.col_offset + 1,
                symbol=node.name,
            )
        )
    return findings


@dataclass(frozen=True, slots=True)
class AnalyzerConfig:
    """Runtime options kept separate from the analysis engine."""

    max_complexity: int = 10
    workers: int = field(default_factory=lambda: min(32, (os.cpu_count() or 1) + 4))
    excluded_dirs: frozenset[str] = frozenset(
        {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".venv", "venv"}
    )

    def __post_init__(self) -> None:
        if self.max_complexity < 1:
            raise ValueError("max_complexity must be at least 1")
        if self.workers < 1:
            raise ValueError("workers must be at least 1")


class CodeAnalyzer:
    """Analyze files concurrently while returning deterministic reports."""

    def __init__(
        self,
        config: AnalyzerConfig | None = None,
        *,
        rules: tuple[Rule, ...] | None = None,
        cache: SQLiteCache | None = None,
    ) -> None:
        self.config = config or AnalyzerConfig()
        self.rules = rules or default_rules()
        self.cache = cache

    def discover(self, target: Path) -> tuple[Path, ...]:
        target = target.resolve()
        if target.is_file():
            return (target,) if target.suffix == ".py" else ()
        files = (
            path
            for path in target.rglob("*.py")
            if not any(part in self.config.excluded_dirs for part in path.relative_to(target).parts)
        )
        return tuple(sorted(files))

    def _cache_key(self, source_digest: str) -> str:
        rule_ids = ",".join(rule.rule_id for rule in self.rules)
        profile = f"v1:{source_digest}:{self.config.max_complexity}:{rule_ids}"
        return hashlib.sha256(profile.encode()).hexdigest()

    def _cached_report(self, path: Path, cache_key: str) -> FileReport | None:
        return self.cache.get(path, cache_key) if self.cache is not None else None

    def _store_report(self, path: Path, cache_key: str, report: FileReport) -> None:
        if self.cache is not None:
            self.cache.put(path, cache_key, report)

    def analyze_file(self, path: Path, *, display_root: Path | None = None) -> FileReport:
        resolved = path.resolve()
        display_path = (
            resolved.relative_to(display_root).as_posix()
            if display_root is not None and resolved.is_relative_to(display_root)
            else resolved.as_posix()
        )
        loaded = _read_source(resolved, display_path)
        if isinstance(loaded, FileReport):
            return loaded
        raw, source = loaded

        digest = hashlib.sha256(raw).hexdigest()
        cache_key = self._cache_key(digest)
        cached = self._cached_report(resolved, cache_key)
        if cached is not None:
            return cached

        try:
            tree = ast.parse(source, filename=display_path)
        except SyntaxError as error:
            report = _syntax_error_report(display_path, digest, source, error)
            self._store_report(resolved, cache_key, report)
            return report

        findings = [finding for rule in self.rules for finding in rule.analyze(tree, display_path)]
        findings.extend(_complexity_findings(tree, display_path, self.config.max_complexity))

        report = FileReport(
            path=display_path,
            digest=digest,
            metrics=collect_metrics(tree, source),
            findings=tuple(
                sorted(findings, key=lambda item: (item.line, item.column, item.rule_id))
            ),
        )
        self._store_report(resolved, cache_key, report)
        return report

    def scan(self, target: Path) -> ScanReport:
        target = target.resolve()
        root = target.parent if target.is_file() else target
        files = self.discover(target)
        analyze = partial(self.analyze_file, display_root=root)
        with ThreadPoolExecutor(max_workers=self.config.workers) as executor:
            reports = tuple(executor.map(analyze, files))
        graph = ImportGraph.build(root, files)
        return ScanReport(
            root=root.as_posix(),
            files=tuple(sorted(reports, key=lambda item: item.path)),
            dependency_cycles=graph.cycles(),
        )
