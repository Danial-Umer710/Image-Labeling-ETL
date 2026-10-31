"""Extract stage: read tool-export CSV files.

Files are ';'-delimited, UTF-8 with BOM. Headers and values are stripped of
surrounding whitespace.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator


def read_csv(path: str | Path) -> Iterator[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        if reader.fieldnames:
            reader.fieldnames = [name.strip() for name in reader.fieldnames]
        for row in reader:
            yield {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
