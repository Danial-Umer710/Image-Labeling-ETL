"""Database helpers: connection factory and schema creation."""

from __future__ import annotations

import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_PATH = REPO_ROOT / "sql" / "schema" / "schema_sqlite.sql"


def connect(path: str | Path = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def create_schema(conn: sqlite3.Connection, schema_path: str | Path = DEFAULT_SCHEMA_PATH) -> None:
    script = Path(schema_path).read_text(encoding="utf-8")
    conn.executescript(script)
    conn.commit()
