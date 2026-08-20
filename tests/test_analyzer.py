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


def write_bytes(tmp_path: Path, raw: bytes, name: str = "sample.py") -> Path:
    path = tmp_path / name
    path.write_bytes(raw)
    return path


def test_latin1_source_with_a_cookie_scans_normally(tmp_path: Path) -> None:
    """PEP 263: a declared non-UTF-8 encoding is valid Python, not a read error."""
    path = write_bytes(
        tmp_path,
        "# -*- coding: latin-1 -*-\nlabel = 'café'\nresult = eval('40 + 2')\n".encode("latin-1"),
    )

    report = CodeAnalyzer(AnalyzerConfig(workers=1)).scan(path)

    assert [f.rule_id for f in report.findings] == ["CH002"]
    # Metrics come from the decoded text, so they are produced normally too.
    assert report.files[0].metrics.physical_lines == 3


def test_utf8_source_without_a_cookie_is_unchanged(tmp_path: Path) -> None:
    path = write_bytes(tmp_path, "label = 'café'\n".encode())

    report = CodeAnalyzer(AnalyzerConfig(workers=1)).scan(path)

    assert report.findings == ()


def test_utf8_source_with_a_cookie_is_unchanged(tmp_path: Path) -> None:
    path = write_bytes(tmp_path, "# -*- coding: utf-8 -*-\nlabel = 'café'\n".encode())

    report = CodeAnalyzer(AnalyzerConfig(workers=1)).scan(path)

    assert report.findings == ()


def test_unknown_encoding_declaration_is_one_ch000(tmp_path: Path) -> None:
    path = write_bytes(tmp_path, b"# -*- coding: latin-99 -*-\nx = 1\n")

    report = CodeAnalyzer(AnalyzerConfig(workers=1)).scan(path)

    assert len(report.findings) == 1
    assert report.findings[0].rule_id == "CH000"
    assert report.findings[0].severity is Severity.HIGH
    assert "unknown encoding: latin-99" in report.findings[0].message


def test_bom_conflicting_with_the_cookie_is_one_ch000(tmp_path: Path) -> None:
    path = write_bytes(tmp_path, b"\xef\xbb\xbf# -*- coding: latin-1 -*-\nx = 1\n")

    report = CodeAnalyzer(AnalyzerConfig(workers=1)).scan(path)

    assert len(report.findings) == 1
    assert report.findings[0].rule_id == "CH000"
    assert "encoding problem: utf-8" in report.findings[0].message


def test_undecodable_bytes_without_a_declaration_still_ch000(tmp_path: Path) -> None:
    """Issue #7's path must keep working: no cookie, bytes that aren't UTF-8."""
    path = write_bytes(tmp_path, b"label = '\xff\xfe'\n")

    report = CodeAnalyzer(AnalyzerConfig(workers=1)).scan(path)

    assert len(report.findings) == 1
    assert report.findings[0].rule_id == "CH000"
    assert "Could not read source" in report.findings[0].message


def test_bytes_that_contradict_a_valid_declaration_are_ch000(tmp_path: Path) -> None:
    """A cookie the file's own bytes don't satisfy is a decode failure, not a crash."""
    path = write_bytes(tmp_path, b"# -*- coding: ascii -*-\nlabel = '\xe9'\n")

    report = CodeAnalyzer(AnalyzerConfig(workers=1)).scan(path)

    assert len(report.findings) == 1
    assert report.findings[0].rule_id == "CH000"


def test_digest_is_computed_from_the_original_bytes(tmp_path: Path) -> None:
    import hashlib

    raw = "# -*- coding: latin-1 -*-\nlabel = 'café'\n".encode("latin-1")
    path = write_bytes(tmp_path, raw)

    report = CodeAnalyzer(AnalyzerConfig(workers=1)).scan(path)

    assert report.files[0].digest == hashlib.sha256(raw).hexdigest()
