"""Static analysis tools for measuring Python code health."""

from importlib.metadata import PackageNotFoundError, version

from code_health.analyzer import AnalyzerConfig, CodeAnalyzer
from code_health.models import FileReport, Finding, ScanReport, Severity

try:
    __version__ = version("python-code-health-analyzer")
except PackageNotFoundError:  # pragma: no cover - only an unpackaged source tree
    __version__ = "0.1.0"

__all__ = [
    "AnalyzerConfig",
    "CodeAnalyzer",
    "FileReport",
    "Finding",
    "ScanReport",
    "Severity",
]
