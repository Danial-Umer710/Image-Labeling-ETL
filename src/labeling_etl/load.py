"""Load stage: delta (incremental) inserts into images and labels.

Delta logic: existing keys are fetched into a set, then only records whose key
is neither in the DB nor already seen in this batch are inserted via a single
``executemany`` in one transaction.

For labels a *new* version of an existing label must still be inserted (it is
a re-labelling, not a duplicate), so the check keeps the highest ``version``
seen per label identity (record_file_name, timestamp, label_coordinates) and
only inserts records whose version is higher — or whose identity is not yet
present. Removing superseded versions is the job of :mod:`labeling_etl.dedup`.

For very large tables a staging table + anti-join (``INSERT ... SELECT ... WHERE
NOT EXISTS``) would be the next step; the set-based check here is O(n) and fine
at this scale.
"""

from __future__ import annotations

import sqlite3
from typing import Iterable

from .transform import ImageRecord, LabelRecord

_INSERT_IMAGE = (
    'INSERT INTO images (record_file_name, "timestamp", image_format, image_path, country) '
    "VALUES (?, ?, ?, ?, ?)"
)
_INSERT_LABEL = (
    'INSERT INTO labels (record_file_name, "timestamp", label_type, label_size, label_coordinates, "version") '
    "VALUES (?, ?, ?, ?, ?, ?)"
)


def load_images_delta(conn: sqlite3.Connection, images: Iterable[ImageRecord]) -> int:
    existing = {
        (row["record_file_name"], row["timestamp"])
        for row in conn.execute('SELECT record_file_name, "timestamp" FROM images')
    }
    rows = []
    for image in images:
        if image.key in existing:
            continue
        existing.add(image.key)
        rows.append(image.as_row())
    with conn:
        conn.executemany(_INSERT_IMAGE, rows)
    return len(rows)


def load_labels_delta(conn: sqlite3.Connection, labels: Iterable[LabelRecord]) -> int:
    latest_version: dict[tuple, int] = {}
    for row in conn.execute(
        'SELECT record_file_name, "timestamp", label_coordinates, MAX("version") AS v '
        'FROM labels GROUP BY 1, 2, 3'
    ):
        latest_version[(row["record_file_name"], row["timestamp"], row["label_coordinates"])] = row["v"]
    rows = []
    for label in labels:
        if latest_version.get(label.key, -1) >= label.version:
            continue
        latest_version[label.key] = label.version
        rows.append(label.as_row())
    with conn:
        conn.executemany(_INSERT_LABEL, rows)
    return len(rows)
