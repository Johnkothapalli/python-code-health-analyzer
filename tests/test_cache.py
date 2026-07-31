from pathlib import Path

from code_health import CodeAnalyzer
from code_health.cache import SQLiteCache


def test_cache_hits_and_content_change_invalidates(tmp_path: Path) -> None:
    source = tmp_path / "module.py"
    source.write_text("answer = 42\n", encoding="utf-8")
    analyzer = CodeAnalyzer(cache=SQLiteCache(tmp_path / "cache" / "reports.db"))

    first = analyzer.scan(source)
    second = analyzer.scan(source)
    source.write_text("answer = 43\n", encoding="utf-8")
    third = analyzer.scan(source)

    assert first.files[0].cached is False
    assert second.files[0].cached is True
    assert third.files[0].cached is False
    assert first.files[0].digest != third.files[0].digest
