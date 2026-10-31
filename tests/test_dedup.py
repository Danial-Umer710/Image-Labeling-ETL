from labeling_etl.dedup import deduplicate_labels


def test_dedup_deletes_superseded_versions(papaya_loaded):
    conn, _ = papaya_loaded
    deleted = deduplicate_labels(conn)
    assert deleted == 5
    remaining = conn.execute("SELECT COUNT(*) FROM labels").fetchone()[0]
    assert remaining == 13


def test_dedup_keeps_latest_versions(papaya_loaded):
    conn, _ = papaya_loaded
    deduplicate_labels(conn)
    types = {
        row[0]
        for row in conn.execute(
            'SELECT label_type FROM labels WHERE record_file_name = ? AND "timestamp" = 10',
            ("hungary_budapest_20220222",),
        )
    }
    assert types == {"motorbyke", "train", "cyclist"}


def test_dedup_leaves_unique_labels(papaya_loaded):
    conn, _ = papaya_loaded
    deduplicate_labels(conn)
    dupes = conn.execute(
        """
        SELECT record_file_name, "timestamp", label_coordinates, COUNT(*) AS n
        FROM labels
        GROUP BY record_file_name, "timestamp", label_coordinates
        HAVING n > 1
        """
    ).fetchall()
    assert dupes == []


def test_dedup_is_idempotent(papaya_loaded):
    conn, _ = papaya_loaded
    deduplicate_labels(conn)
    assert deduplicate_labels(conn) == 0
