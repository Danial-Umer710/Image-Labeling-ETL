"""Deduplication: keep only the highest ``version`` of each label.

Labels are identified by (record_file_name, timestamp, label_coordinates); a
higher version of the same label is a re-labelling, so older versions are
deleted.

Uses SQLite's ``rowid``; on PostgreSQL the physical row id would be ``ctid``
(and on other engines a surrogate key would be added).
"""

from __future__ import annotations

import sqlite3

_DEDUP_SQL = """
DELETE FROM labels
WHERE rowid IN (
    SELECT rowid FROM (
        SELECT rowid,
               ROW_NUMBER() OVER (PARTITION BY record_file_name, "timestamp", label_coordinates
                                  ORDER BY "version" DESC) AS rn
        FROM labels
    ) WHERE rn > 1
);
"""


def deduplicate_labels(conn: sqlite3.Connection) -> int:
    """Delete superseded label versions; return the number of rows deleted."""
    with conn:
        cursor = conn.execute(_DEDUP_SQL)
    return cursor.rowcount
