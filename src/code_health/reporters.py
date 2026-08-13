"""Human-readable, JSON, and SARIF output adapters."""

from __future__ import annotations

import json
from typing import Any

from code_health import __version__
from code_health.models import ScanReport, Severity

PROJECT_URL = "https://github.com/Johnkothapalli/python-code-health-analyzer"

RULES = {
    "CH000": "Source could not be parsed",
    "CH001": "Mutable default argument",
    "CH002": "Unsafe dynamic execution or deserialization",
    "CH003": "Overly broad exception handler",
    "CH004": "Blocking call in async code",
    "CH005": "High cyclomatic complexity",
}


def render_text(report: ScanReport) -> str:
    lines = [
        f"Code health score: {report.score}/100",
        f"Scanned {len(report.files)} file(s); found {len(report.findings)} issue(s).",
    ]
    for finding in report.findings:
        symbol = f" [{finding.symbol}]" if finding.symbol else ""
        lines.append(
            f"{finding.path}:{finding.line}:{finding.column} "
            f"{finding.severity.value.upper():6} {finding.rule_id}{symbol} {finding.message}"
        )
    for cycle in report.dependency_cycles:
        lines.append(f"IMPORT CYCLE: {' -> '.join(cycle)} -> {cycle[0]}")
    if not report.findings and not report.dependency_cycles:
        lines.append("No code-health issues detected.")
    return "\n".join(lines)


def render_json(report: ScanReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True)


def _sarif_level(severity: Severity) -> str:
    if severity is Severity.HIGH:
        return "error"
    if severity is Severity.MEDIUM:
        return "warning"
    return "note"


def sarif_payload(report: ScanReport) -> dict[str, Any]:
    used_rules = sorted({finding.rule_id for finding in report.findings})
    results: list[dict[str, Any]] = []
    for finding in report.findings:
        results.append(
            {
                "ruleId": finding.rule_id,
                "level": _sarif_level(finding.severity),
                "message": {"text": finding.message},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": finding.path},
                            "region": {
                                "startLine": finding.line,
                                "startColumn": finding.column,
                            },
                        }
                    }
                ],
            }
        )
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "python-code-health-analyzer",
                        "version": __version__,
                        "informationUri": PROJECT_URL,
                        "rules": [
                            {
                                "id": rule_id,
                                "shortDescription": {"text": RULES.get(rule_id, rule_id)},
                            }
                            for rule_id in used_rules
                        ],
                    }
                },
                "results": results,
            }
        ],
    }


def render_sarif(report: ScanReport) -> str:
    return json.dumps(sarif_payload(report), indent=2, sort_keys=True)
