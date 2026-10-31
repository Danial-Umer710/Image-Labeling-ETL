-- Q3: Find the image which has the most labels with at least 0.6 label_size.
-- Ties are kept: every image sharing the highest count is returned.
-- As in Q2, only the latest version of each label is counted.
WITH latest_labels AS (
    SELECT record_file_name,
           "timestamp",
           label_size,
           ROW_NUMBER() OVER (
               PARTITION BY record_file_name, "timestamp", label_coordinates
               ORDER BY "version" DESC
           ) AS version_rn
    FROM labels
),
label_counts AS (
    SELECT i.record_file_name,
           i."timestamp",
           i.image_path,
           i.country,
           COUNT(*) AS big_label_count
    FROM images AS i
    JOIN latest_labels AS l
      ON l.record_file_name = i.record_file_name
     AND l."timestamp"     = i."timestamp"
    WHERE l.version_rn = 1
      AND l.label_size >= 0.6
    GROUP BY i.record_file_name, i."timestamp", i.image_path, i.country
),
ranked AS (
    SELECT *,
           RANK() OVER (ORDER BY big_label_count DESC) AS count_rank
    FROM label_counts
)
SELECT record_file_name,
       "timestamp",
       image_path,
       country,
       big_label_count
FROM ranked
WHERE count_rank = 1
ORDER BY record_file_name, "timestamp";
