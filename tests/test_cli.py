import json
from pathlib import Path

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
