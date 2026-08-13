"""Command-line interface for code-health scans."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from code_health import __version__
from code_health.analyzer import AnalyzerConfig, CodeAnalyzer
from code_health.cache import SQLiteCache
from code_health.models import ScanReport, Severity
from code_health.reporters import render_json, render_sarif, render_text


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="code-health",
        description="Analyze Python code health without executing the target project.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser("scan", help="scan a Python file or directory")
    scan.add_argument("target", nargs="?", default=".", type=Path)
    scan.add_argument("--format", choices=("text", "json", "sarif"), default="text")
    scan.add_argument("--output", type=Path, help="write the report to a file")
    scan.add_argument("--max-complexity", type=int, default=10)
    scan.add_argument("--workers", type=int, default=None)
    scan.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        metavar="NAME",
        help="exclude a directory name; repeat the option to exclude multiple names",
    )
    scan.add_argument("--no-cache", action="store_true")
    scan.add_argument("--cache", type=Path, default=Path(".code-health/cache.db"))
    scan.add_argument(
        "--fail-on",
        choices=("never", "info", "low", "medium", "high"),
        default="never",
        help="return exit code 1 when an issue meets this severity",
    )
    return parser


def _render(report: ScanReport, output_format: str) -> str:
    if output_format == "json":
        return render_json(report)
    if output_format == "sarif":
        return render_sarif(report)
    return render_text(report)


def _should_fail(report: ScanReport, threshold: str) -> bool:
    if threshold == "never":
        return False
    minimum = Severity(threshold)
    return any(finding.severity.rank >= minimum.rank for finding in report.findings)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command != "scan":
        return 2
    if not args.target.exists():
        raise SystemExit(f"Target does not exist: {args.target}")

    defaults = AnalyzerConfig()
    excluded_dirs = defaults.excluded_dirs | frozenset(args.exclude_dir)
    config = AnalyzerConfig(
        max_complexity=args.max_complexity,
        workers=args.workers or defaults.workers,
        excluded_dirs=excluded_dirs,
    )
    cache = None if args.no_cache else SQLiteCache(args.cache)
    report = CodeAnalyzer(config, cache=cache).scan(args.target)
    rendered = _render(report, args.format)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(f"{rendered}\n", encoding="utf-8")
        print(f"Wrote {args.format} report to {args.output}")
    else:
        print(rendered)
    return int(_should_fail(report, args.fail_on))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
