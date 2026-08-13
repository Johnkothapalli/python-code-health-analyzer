from pathlib import Path

import pytest

from code_health import AnalyzerConfig, CodeAnalyzer, Severity


def write_source(tmp_path: Path, source: str, name: str = "sample.py") -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def test_detects_builtin_rules_and_metrics(tmp_path: Path) -> None:
    path = write_source(
        tmp_path,
        """
import time

def append_item(items=[]):
    try:
        return eval("1 + 1")
    except Exception:
        return items

async def fetch():
    time.sleep(1)
""".strip(),
    )

    report = CodeAnalyzer().scan(path)

    assert {finding.rule_id for finding in report.findings} == {
        "CH001",
        "CH002",
        "CH003",
        "CH004",
    }
    assert report.files[0].metrics.functions == 2
    assert report.files[0].metrics.async_functions == 1
    assert report.findings[0].path == "sample.py"
    assert report.score == 72


def test_complexity_threshold_is_configurable(tmp_path: Path) -> None:
    path = write_source(
        tmp_path,
        """
def classify(value):
    if value > 10:
        return "large"
    if value > 0:
        return "small"
    return "other"
""".strip(),
    )

    report = CodeAnalyzer(AnalyzerConfig(max_complexity=2)).scan(path)

    finding = next(item for item in report.findings if item.rule_id == "CH005")
    assert finding.symbol == "classify"
    assert "complexity is 3" in finding.message


def test_syntax_error_becomes_a_finding(tmp_path: Path) -> None:
    path = write_source(tmp_path, "def broken(:\n    pass")

    report = CodeAnalyzer().scan(path)

    assert report.findings[0].rule_id == "CH000"
    assert report.findings[0].severity is Severity.HIGH


def test_invalid_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="max_complexity"):
        AnalyzerConfig(max_complexity=0)
    with pytest.raises(ValueError, match="workers"):
        AnalyzerConfig(workers=0)


def test_invalid_utf8_produces_ch000_finding(tmp_path: Path) -> None:
    path = tmp_path / "bad_encoding.py"
    path.write_bytes(b"\x80\x81\x82\x83")

    report = CodeAnalyzer().scan(path)

    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.rule_id == "CH000"
    assert finding.severity is Severity.HIGH
    assert "Could not read source" in finding.message


def test_empty_directory_produces_no_findings(tmp_path: Path) -> None:
    report = CodeAnalyzer().scan(tmp_path)

    assert report.files == ()
    assert report.findings == ()
    assert report.score == 100


def test_directory_with_non_python_files(tmp_path: Path) -> None:
    (tmp_path / "readme.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "data.json").write_text('{"key": "value"}', encoding="utf-8")

    report = CodeAnalyzer().scan(tmp_path)

    assert report.files == ()
    assert report.findings == ()
    assert report.score == 100


def test_non_python_file_target_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("not python", encoding="utf-8")

    report = CodeAnalyzer().scan(path)

    assert report.files == ()
    assert report.findings == ()
