# Labeling ETL Pipeline

A Python and SQL ETL pipeline that takes image-annotation exports from two different labelling tools, normalizes them into one relational SQLite model, and keeps only the latest version of each label. Runs are idempotent (delta loading), every stage is covered by a 30-test `pytest` suite, and analytics questions are answered with SQL window functions.

## Tech Stack

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![SQL](https://img.shields.io/badge/SQL-window%20functions-4479A1)
![pytest](https://img.shields.io/badge/pytest-30%20tests-0A9EDC?logo=pytest&logoColor=white)

- **Python 3.10+** with the standard library only (`csv`, `json`, `sqlite3`, `dataclasses`)
- **SQLite** as the relational store, with DDL and analytics queries as plain `.sql` files
- **pytest** for unit and integration tests (in-memory database, real CSV fixtures)

## Key Engineering Features

- **Explicit ETL stages and loaders.** `PapayaLoader` (two normalized CSVs) and `KumquatLoader` (one denormalized CSV) each expose `extract()`, `transform()` and `load()`, and `run(conn)` calls them in order. Both write to the same `images` and `labels` tables.
- **Delta loading for idempotent runs.** `load.py` reads the identities that already exist in the database once, then inserts only new records in a single `executemany` transaction. For labels, a row is inserted only if its `version` is higher than the stored one. Running the pipeline a second time inserts 0 rows.
- **Version-based deduplication.** A label's identity is `(record_file_name, timestamp, label_coordinates)`. `dedup.py` removes superseded versions with one `DELETE` using `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY version DESC)`. Coordinate JSON is canonicalized (`sort_keys=True`) on ingest so identity comparisons are reliable.
- **Strict attribute mapping and data cleaning.** Country names are mapped to ISO 3166-1 alpha-2 codes (`Hungary -> HU`), and unknown values raise an error instead of storing bad data. The transform stage also handles `;` delimiters, UTF-8 BOM and European decimal commas (`0,5 -> 0.5`).
- **SQL analytics with window functions.** `RANK()` for the top-2 labels per image and for the image with the most large labels (ties kept), and `ROW_NUMBER()` so the queries only count the latest label versions, even before dedup has run.

## Architecture & Workflow

```
 data/papaya/*.csv  (images + labels)      data/kumquat/*.csv  (denormalized)
            │                                          │
            ▼                                          ▼
     PapayaLoader                               KumquatLoader
            │   extract.read_csv    (';' delimiter, utf-8-sig, strip)
            │   transform           (typed ImageRecord / LabelRecord,
            │                        decimal commas, canonical JSON,
            │                        country -> ISO code)
            │   load                (delta insert: skip known identities,
            │                        insert only higher label versions)
            └───────────────┬──────────────────────────┘
                            ▼
              SQLite: images, labels  (sql/schema/schema_sqlite.sql)
                            │
                            ▼
              dedup.deduplicate_labels   (ROW_NUMBER() -> keep latest version)
                            │
                            ▼
              queries.run_all  ->  sql/queries/01..03_*.sql
                 Q1 images without labels         (LEFT JOIN anti-join)
                 Q2 two biggest labels per image  (RANK() per image)
                 Q3 image with most labels >= 0.6 (COUNT + RANK())
```

```
├── data/                 # tool exports (input CSVs)
├── sql/schema/           # DDL for images / labels
├── sql/queries/          # analytics queries (Q1-Q3)
├── src/labeling_etl/     # extract, transform, attribute_map, load, loaders, dedup, queries, db
├── tests/                # 30 pytest tests
└── run_pipeline.py       # CLI entry point
```

## How to Run / Quickstart

Requires Python 3.10+. The pipeline uses only the standard library. `pytest` is the only dependency.

```bash
git clone https://github.com/Danial-Umer710/Image-Labeling-ETL.git
cd Image-Labeling-ETL
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python run_pipeline.py --reset   # fresh load + dedup + analytics queries
python run_pipeline.py           # second run: delta load inserts 0 rows
```

No environment variables are needed. `--db PATH` chooses the SQLite file (default `./labeling.db`), and `--reset` deletes it before loading.

Sample output:

```
Papaya load:  10 images, 18 labels inserted
Kumquat load: 8 images, 13 labels inserted
Dedup:        5 superseded label versions deleted
Totals:       18 images, 26 labels

=== 01_images_without_labels ===
record_file_name           timestamp  image_format  image_path                                        country
-------------------------  ---------  ------------  ------------------------------------------------  -------
germany_berlin_20211010    40         v1            my_server/my_folder/germany_berlin_20211010_40    DE
hungary_budapest_20220222  30         v1            my_server/my_folder/hungary_budapest_20220222_30  HU
(2 rows)
...
```

Second run (idempotent):

```
Papaya load:  0 images, 0 labels inserted
Kumquat load: 0 images, 0 labels inserted
Dedup:        0 superseded label versions deleted
Totals:       18 images, 26 labels
```

## Testing & Verification

`pyproject.toml` already sets `testpaths` and `pythonpath`, so you can run the suite from the repo root:

```bash
pytest            # quiet summary
pytest -v         # one line per test
```

```
..............................                                           [100%]
30 passed in 0.08s
```

| Test module | Tests | What it covers |
|---|---|---|
| `tests/test_transform.py` | 8 | decimal-comma floats, int parsing, canonical coordinate JSON, record keys, Kumquat row splitting |
| `tests/test_attribute_map.py` | 7 | country -> ISO mapping, case handling, strict vs. non-strict mode |
| `tests/test_loaders.py` | 7 | row counts per loader, country mapping, delta second run inserts 0, new label version is inserted |
| `tests/test_dedup.py` | 4 | superseded versions deleted, latest kept, unique labels untouched, dedup is idempotent |
| `tests/test_queries.py` | 4 | expected results for Q1-Q3 and the `run_all` runner |

Each test uses a fresh in-memory SQLite database (`tests/conftest.py`) loaded from the real CSVs in `data/`, so the tests never touch `labeling.db`.
