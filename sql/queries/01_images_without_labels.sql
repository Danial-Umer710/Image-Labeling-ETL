-- Q1: List of images that do not have any labels on them.
-- An image is identified by (record_file_name, timestamp); labels reference
-- the image through the same two columns.
SELECT i.record_file_name,
       i."timestamp",
       i.image_format,
       i.image_path,
       i.country
FROM images AS i
LEFT JOIN labels AS l
       ON l.record_file_name = i.record_file_name
      AND l."timestamp"     = i."timestamp"
WHERE l.record_file_name IS NULL
ORDER BY i.record_file_name, i."timestamp";
