-- SQLite-compatible version of the provided images.sql / labels.sql.
-- The originals mix PostgreSQL (INT8, FLOAT8) and SQL Server (VARCHAR(max))
-- type names; SQLite rejects VARCHAR(max), so the types are mapped here.
-- The column names and order are identical to the originals.
CREATE TABLE IF NOT EXISTS images (
    record_file_name VARCHAR(270),
    "timestamp" INTEGER,
    image_format VARCHAR(10),
    image_path VARCHAR(110),
    country VARCHAR(110)
);

CREATE TABLE IF NOT EXISTS labels (
    record_file_name VARCHAR(270),
    "timestamp" INTEGER,
    label_type VARCHAR(20),
    label_size REAL,
    label_coordinates TEXT,
    "version" INTEGER
);

-- Indexes on the natural keys used by delta loading, deduplication and the queries.
CREATE INDEX IF NOT EXISTS ix_images_key ON images (record_file_name, "timestamp");
CREATE INDEX IF NOT EXISTS ix_labels_key ON labels (record_file_name, "timestamp", label_coordinates, "version");
