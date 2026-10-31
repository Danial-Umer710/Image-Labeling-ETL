-- Q2: For each image, list the two biggest labels based on label_size.
-- Ties are kept: RANK() gives equal rank to equal sizes, so every label that
-- ranks 1st or 2nd is returned (possibly more than two rows per image).
-- Only the latest version of each label should be considered, which is what the
-- deduplication module guarantees; the ROW_NUMBER() filter below makes the query
-- robust even if deduplication has not been run yet.
WITH latest_labels AS (
    SELECT record_file_name,
           "timestamp",
           label_type,
           label_size,
           label_coordinates,
           "version",
           ROW_NUMBER() OVER (
               PARTITION BY record_file_name, "timestamp", label_coordinates
               ORDER BY "version" DESC
           ) AS version_rn
    FROM labels
),
ranked AS (
    SELECT i.record_file_name,
           i."timestamp",
           i.image_path,
           l.label_type,
           l.label_size,
           l.label_coordinates,
           l."version",
           RANK() OVER (
               PARTITION BY i.record_file_name, i."timestamp"
               ORDER BY l.label_size DESC
           ) AS size_rank
    FROM images AS i
    JOIN latest_labels AS l
      ON l.record_file_name = i.record_file_name
     AND l."timestamp"     = i."timestamp"
    WHERE l.version_rn = 1
)
SELECT record_file_name,
       "timestamp",
       image_path,
       label_type,
       label_size,
       label_coordinates,
       "version",
       size_rank
FROM ranked
WHERE size_rank <= 2
ORDER BY record_file_name, "timestamp", size_rank, label_type;
