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
