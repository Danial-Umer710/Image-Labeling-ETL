"""Run the SQL answer scripts in sql/queries/."""

from __future__ import annotations

import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
QUERIES_DIR = REPO_ROOT / "sql" / "queries"


def run_query_file(conn: sqlite3.Connection, path: str | Path) -> list[sqlite3.Row]:
    script = Path(path).read_text(encoding="utf-8")
    return conn.execute(script).fetchall()


def run_all(conn: sqlite3.Connection, queries_dir: str | Path = QUERIES_DIR) -> dict[str, list[sqlite3.Row]]:
    results: dict[str, list[sqlite3.Row]] = {}
    for path in sorted(Path(queries_dir).glob("*.sql")):
        results[path.stem] = run_query_file(conn, path)
    return results
