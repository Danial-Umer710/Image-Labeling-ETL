# Image Labeling ETL Pipeline

A Python + SQL ETL pipeline that ingests image-annotation exports from two
different labelling tools into a single normalized SQLite database, keeps only
the latest version of each label, and answers analytics questions with SQL.

The two tool exports have different shapes:

- **Papaya** (legacy tool): two normalized CSVs (`images` + `labels`).
- **Kumquat** (new tool): one denormalized CSV where every row mixes image
  metadata with one label.

Both land in the same `images` and `labels` tables.

## Design decisions

- **Image identity** is `(record_file_name, timestamp)` — an image is a frame
  of a recording.
- **Label identity** is `(record_file_name, timestamp, label_coordinates)`.
  `version` is *not* part of the identity: a higher `version` of the same
  coordinates is a re-labelling (e.g. `car` v1 re-labelled as `motorbyke` v2).
- **Delta loading**: only records not yet present in the DB are inserted. For
  labels, a row is inserted only when its `version` is strictly higher than
  what the DB already has for that identity, so the pipeline is fully
  idempotent — rerunning it inserts 0 rows.
- **Deduplication**: `deduplicate_labels` deletes every row that is not the
  highest version of its identity, using a single `ROW_NUMBER()` window query.
- **Coordinates** are part of a label's identity, so the JSON string is
  normalised on ingest (`json.dumps(..., sort_keys=True)`) to make two
  differently-formatted serialisations of the same box comparable as strings.
- **Attribute mapping**: `country` names are translated to ISO 3166-1 alpha-2
  codes (`Hungary -> HU`, `Germany -> DE`, ...). The mapper runs in strict
  mode — an unknown country fails loudly instead of silently storing bad data.
- **SQLite** for zero-setup portability (`INT8`/`FLOAT8`/`VARCHAR(max)` types
  from the source DDL are mapped in `sql/schema/schema_sqlite.sql`).

## CSV quirks handled

- `;`-delimited, UTF-8 with BOM (`encoding="utf-8-sig"`)
- European decimal commas in `label_size` (`0,5` -> `0.5`)
- `label_coordinates` stored as JSON strings, normalised for comparison

## Project structure

```
├── data/                     # tool exports (input)
├── sql/
│   ├── schema/               # DDL for images/labels tables
│   └── queries/              # analytics queries
├── src/labeling_etl/
│   ├── db.py                 # connection factory + schema creation
│   ├── extract.py            # CSV reading (extract stage)
│   ├── transform.py          # parsing, coordinate normalisation, records
│   ├── attribute_map.py      # value mapping (country name -> ISO code)
│   ├── load.py               # delta inserts (load stage)
│   ├── loaders.py            # PapayaLoader / KumquatLoader (ETL orchestration)
│   ├── dedup.py              # keep only the latest label version
│   └── queries.py            # run the SQL scripts in sql/queries
├── tests/                    # pytest suite (in-memory DB, real CSVs)
├── run_pipeline.py           # CLI entry point
└── requirements.txt          # pytest only; the package itself is stdlib-only
```

## How to run

Requires Python 3.10+ (stdlib `sqlite3` with window-function support); the
only third-party dependency is `pytest`.

```bash
pip install -r requirements.txt
python run_pipeline.py --reset   # fresh load + dedup + query answers
python run_pipeline.py           # second run: delta load inserts 0 rows
pytest                           # 30 unit tests
```

`--db PATH` selects a different SQLite file (default `./labeling.db`).

## ETL design

Each loader exposes the three ETL stages explicitly (`extract()`, `transform()`,
`load()`), orchestrated by `run(conn)`:

- **Extract** (`extract.read_csv`): `csv.DictReader` with `;` delimiter and
  `utf-8-sig`, headers and values stripped.
- **Transform** (`transform`): raw dicts become typed `ImageRecord` /
  `LabelRecord` dataclasses — decimal-comma floats, int parsing, canonical
  coordinate JSON, and the `country` attribute map. `KumquatLoader.transform`
  splits each denormalised row and deduplicates images within the file.
- **Load** (`load`): *delta* insert — existing identities are fetched once into
  a set/dict, then a single `executemany` inside one transaction inserts only
  records not already present (in the DB or earlier in the same batch). For
  labels, only a strictly higher `version` of an existing identity inserts.
- **Dedup** (`dedup.deduplicate_labels`): one `DELETE` using
  `ROW_NUMBER() OVER (PARTITION BY identity ORDER BY version DESC)`, keeping
  `rn = 1`. Uses SQLite `rowid`; on PostgreSQL `ctid` would replace it.

## Example output

```
Papaya load:  10 images, 18 labels inserted
Kumquat load: 8 images, 13 labels inserted
Dedup:        5 superseded label versions deleted
Totals:       18 images, 26 labels
```

Second run — fully idempotent:

```
Papaya load:  0 images, 0 labels inserted
Kumquat load: 0 images, 0 labels inserted
Dedup:        0 superseded label versions deleted
```

### Q1 — images without labels (`sql/queries/01_images_without_labels.sql`)

`LEFT JOIN labels` on the image key, `WHERE l.record_file_name IS NULL` —
returns the 2 unlabeled frames.

### Q2 — two biggest labels per image (`sql/queries/02_two_biggest_labels_per_image.sql`)

`RANK() OVER (PARTITION BY image ORDER BY label_size DESC)` with `rank <= 2`;
ties are kept, so images with equal sizes return more than two rows.

### Q3 — image with the most labels of size >= 0.6 (`sql/queries/03_image_with_most_labels_min_size.sql`)

Counts qualifying labels per image, `RANK() OVER (ORDER BY count DESC)`,
returns all images tied at rank 1.

## Scaling notes

- **Staging table + anti-join** for very large files: bulk-load the CSV into a
  temp table and `INSERT ... SELECT ... WHERE NOT EXISTS` instead of fetching
  all keys into a Python set.
- **PRIMARY KEY / UNIQUE constraints** on the natural keys to enforce identity
  at the schema level (currently enforced in the loader).
- **PostgreSQL port**: replace `rowid` with `ctid` in dedup, `INT8`/`FLOAT8`
  DDL, `INSERT ... ON CONFLICT DO NOTHING` for delta loads.
- **Incremental file watermarks**: persist per-file load state (name +
  mtime/hash or max timestamp) to skip already-processed exports entirely.
