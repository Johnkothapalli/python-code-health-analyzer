import json
from pathlib import Path

import pytest

from code_health import __version__
from code_health.cli import main


def test_cli_writes_json_and_honors_failure_threshold(tmp_path: Path) -> None:
    source = tmp_path / "unsafe.py"
    source.write_text("result = eval('40 + 2')\n", encoding="utf-8")
    output = tmp_path / "report.json"

    exit_code = main(
        [
            "scan",
            str(source),
            "--format",
            "json",
            "--output",
            str(output),
            "--no-cache",
            "--fail-on",
            "high",
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert payload["summary"]["findings"] == 1
    assert payload["files"][0]["findings"][0]["rule_id"] == "CH002"


def test_clean_cli_text_output(tmp_path: Path, capsys: object) -> None:
    source = tmp_path / "clean.py"
    source.write_text("answer = 42\n", encoding="utf-8")

    assert main(["scan", str(source), "--no-cache"]) == 0


def test_cli_excludes_repeated_directory_names(tmp_path: Path, capsys: object) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "clean.py").write_text("answer = 42\n", encoding="utf-8")
    for directory in ("generated", "vendor"):
        (tmp_path / directory).mkdir()
        (tmp_path / directory / "unsafe.py").write_text(
            "result = eval('40 + 2')\n", encoding="utf-8"
        )

    exit_code = main(
        [
            "scan",
            str(tmp_path),
            "--exclude-dir",
            "generated",
            "--exclude-dir",
            "vendor",
            "--no-cache",
            "--fail-on",
            "high",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "Scanned 1 file(s)" in output


def test_cli_reports_package_version(capsys: object) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"code-health {__version__}"  # type: ignore[attr-defined]


def test_sarif_uses_release_metadata(tmp_path: Path) -> None:
    source = tmp_path / "unsafe.py"
    source.write_text("result = eval('40 + 2')\n", encoding="utf-8")
    output = tmp_path / "report.sarif"

    assert main(["scan", str(source), "--format", "sarif", "--output", str(output)]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    driver = payload["runs"][0]["tool"]["driver"]
    assert payload["version"] == "2.1.0"
    assert driver["version"] == __version__
    assert driver["informationUri"].endswith("/python-code-health-analyzer")


@pytest.mark.parametrize("option", ["--workers", "--max-complexity"])
@pytest.mark.parametrize("value", ["0", "-1"])
def test_cli_rejects_non_positive_numeric_options(
    tmp_path: Path, capsys: object, option: str, value: str
) -> None:
    """Zero and negative values are usage errors, not tracebacks or silent defaults."""
    source = tmp_path / "clean.py"
    source.write_text("answer = 42\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exit_info:
        main(["scan", str(source), option, value, "--no-cache"])

    assert exit_info.value.code == 2
    stderr = capsys.readouterr().err  # type: ignore[attr-defined]
    assert f"argument {option}" in stderr
    assert "must be at least 1" in stderr


@pytest.mark.parametrize("option", ["--workers", "--max-complexity"])
def test_cli_rejects_non_integer_numeric_options(
    tmp_path: Path, capsys: object, option: str
) -> None:
    source = tmp_path / "clean.py"
    source.write_text("answer = 42\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exit_info:
        main(["scan", str(source), option, "many", "--no-cache"])

    assert exit_info.value.code == 2
    assert "expected an integer" in capsys.readouterr().err  # type: ignore[attr-defined]


@pytest.mark.parametrize(("option", "value"), [("--workers", "2"), ("--max-complexity", "1")])
def test_cli_accepts_explicit_positive_values(
    tmp_path: Path, capsys: object, option: str, value: str
) -> None:
    source = tmp_path / "clean.py"
    source.write_text("answer = 42\n", encoding="utf-8")

    assert main(["scan", str(source), option, value, "--no-cache"]) == 0


def test_cli_without_numeric_options_keeps_defaults(tmp_path: Path, capsys: object) -> None:
    """Omitting both options must still fall back to AnalyzerConfig's defaults."""
    from code_health.analyzer import AnalyzerConfig
    from code_health.cli import _parser

    source = tmp_path / "clean.py"
    source.write_text("answer = 42\n", encoding="utf-8")
    parsed = _parser().parse_args(["scan", str(source), "--no-cache"])

    assert parsed.workers is None
    assert parsed.max_complexity == AnalyzerConfig().max_complexity
    assert main(["scan", str(source), "--no-cache"]) == 0


def test_analyzer_config_still_validates_for_api_callers() -> None:
    """CLI validation is additive; direct API callers keep their own guard."""
    from code_health.analyzer import AnalyzerConfig

    with pytest.raises(ValueError, match="workers must be at least 1"):
        AnalyzerConfig(workers=0)
    with pytest.raises(ValueError, match="max_complexity must be at least 1"):
        AnalyzerConfig(max_complexity=0)
