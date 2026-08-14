"""Content-addressed SQLite cache safe for concurrent scanner workers."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from code_health.models import FileReport


class SQLiteCache:
    """Persist reports by absolute path and SHA-256 source digest."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                    CREATE TABLE IF NOT EXISTS reports (
                        path TEXT NOT NULL,
                        digest TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        PRIMARY KEY (path, digest)
                    )
                    """
            )

    def get(self, path: Path, cache_key: str) -> FileReport | None:
        resolved_path = str(path.resolve())
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload FROM reports WHERE path = ? AND digest = ?",
                (resolved_path, cache_key),
            ).fetchone()
            if row is None:
                return None
            raw_payload = str(row[0])
            try:
                payload = json.loads(raw_payload)
                return FileReport.from_dict(payload).as_cached()
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                with connection:
                    connection.execute(
                        "DELETE FROM reports WHERE path = ? AND digest = ? AND payload = ?",
                        (resolved_path, cache_key, raw_payload),
                    )
                return None

    def put(self, path: Path, cache_key: str, report: FileReport) -> None:
        payload = json.dumps(report.to_dict(), separators=(",", ":"), sort_keys=True)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "INSERT OR REPLACE INTO reports(path, digest, payload) VALUES (?, ?, ?)",
                (str(path.resolve()), cache_key, payload),
            )
