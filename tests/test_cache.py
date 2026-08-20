import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

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


@pytest.mark.parametrize("payload", ["{not-json", '{"path":"missing-fields"}'])
def test_malformed_cache_entry_is_replaced_after_analysis(tmp_path: Path, payload: str) -> None:
    source = tmp_path / "module.py"
    source.write_text("answer = 42\n", encoding="utf-8")
    cache_path = tmp_path / "cache" / "reports.db"
    cache = SQLiteCache(cache_path)
    analyzer = CodeAnalyzer(cache=cache)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    cache_key = analyzer._cache_key(digest)

    with closing(sqlite3.connect(cache_path)) as connection, connection:
        connection.execute(
            "INSERT INTO reports(path, digest, payload) VALUES (?, ?, ?)",
            (str(source.resolve()), cache_key, payload),
        )

    first = analyzer.scan(source)
    second = analyzer.scan(source)

    assert first.files[0].cached is False
    assert second.files[0].cached is True
    with closing(sqlite3.connect(cache_path)) as connection:
        stored_payload = connection.execute(
            "SELECT payload FROM reports WHERE path = ? AND digest = ?",
            (str(source.resolve()), cache_key),
        ).fetchone()
    assert stored_payload is not None
    assert stored_payload[0] != payload
