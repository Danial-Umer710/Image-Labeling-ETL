"""CLI entry point: run the full labeling ETL pipeline.

Loads the Papaya and Kumquat exports into SQLite (delta load), deduplicates
label versions, then runs the three answer queries and prints the results.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from labeling_etl import db
from labeling_etl.dedup import deduplicate_labels
from labeling_etl.loaders import KumquatLoader, PapayaLoader
from labeling_etl.queries import run_all

DATA_DIR = REPO_ROOT / "data"


def print_table(name: str, rows) -> None:
    print(f"\n=== {name} ===")
    if not rows:
        print("(no rows)")
        return
    columns = rows[0].keys()
    widths = {c: len(c) for c in columns}
    for row in rows:
        for c in columns:
            widths[c] = max(widths[c], len(str(row[c])))
    header = "  ".join(c.ljust(widths[c]) for c in columns)
    print(header)
    print("  ".join("-" * widths[c] for c in columns))
    for row in rows:
        print("  ".join(str(row[c]).ljust(widths[c]) for c in columns))
    print(f"({len(rows)} rows)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(REPO_ROOT / "labeling.db"), help="SQLite database path")
    parser.add_argument("--reset", action="store_true", help="delete the database file before loading")
    args = parser.parse_args()

    db_path = Path(args.db)
    if args.reset and db_path.exists():
        db_path.unlink()

    conn = db.connect(db_path)
    db.create_schema(conn)

    papaya = PapayaLoader(
        DATA_DIR / "papaya" / "papaya_output_images.csv",
        DATA_DIR / "papaya" / "papaya_output_labels.csv",
    ).run(conn)
    print(f"Papaya load:  {papaya.images_inserted} images, {papaya.labels_inserted} labels inserted")

    kumquat = KumquatLoader(DATA_DIR / "kumquat" / "kumquat_output.csv").run(conn)
    print(f"Kumquat load: {kumquat.images_inserted} images, {kumquat.labels_inserted} labels inserted")

    deleted = deduplicate_labels(conn)
    print(f"Dedup:        {deleted} superseded label versions deleted")

    print(f"Totals:       {conn.execute('SELECT COUNT(*) FROM images').fetchone()[0]} images, "
          f"{conn.execute('SELECT COUNT(*) FROM labels').fetchone()[0]} labels")

    for name, rows in run_all(conn).items():
        print_table(name, rows)


if __name__ == "__main__":
    main()
