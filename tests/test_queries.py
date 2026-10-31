from labeling_etl.queries import QUERIES_DIR, run_all, run_query_file


def test_q1_images_without_labels(fully_loaded):
    conn, _ = fully_loaded
    rows = run_query_file(conn, QUERIES_DIR / "01_images_without_labels.sql")
    keys = {(r["record_file_name"], r["timestamp"]) for r in rows}
    assert keys == {
        ("hungary_budapest_20220222", 30),
        ("germany_berlin_20211010", 40),
    }
    # every kumquat image has a label, so none may appear
    kumquat_names = {
        "hungary_debrecen_20220222",
        "hungary_pecs_20220216",
        "germany_berlin_20201010",
    }
    assert not any(r["record_file_name"] in kumquat_names for r in rows)


def test_q2_two_biggest_labels_per_image(fully_loaded):
    conn, _ = fully_loaded
    rows = run_query_file(conn, QUERIES_DIR / "02_two_biggest_labels_per_image.sql")
    assert all(r["size_rank"] <= 2 for r in rows)

    by_image = {}
    for r in rows:
        by_image.setdefault((r["record_file_name"], r["timestamp"]), []).append(
            (r["label_type"], r["label_size"], r["size_rank"])
        )

    budapest_10 = by_image[("hungary_budapest_20220222", 10)]
    assert sorted(t for t, _, _ in budapest_10) == ["motorbyke", "train"]
    assert {t: s for t, s, _ in budapest_10} == {"motorbyke": 2.0, "train": 1.0}

    # tie at size 0.1 -> both labels returned
    budapest_20 = by_image[("hungary_budapest_20220222", 20)]
    assert len(budapest_20) == 2
    assert all(s == 0.1 for _, s, _ in budapest_20)


def test_q3_images_with_most_big_labels(fully_loaded):
    conn, _ = fully_loaded
    rows = run_query_file(conn, QUERIES_DIR / "03_image_with_most_labels_min_size.sql")
    result = {(r["record_file_name"], r["timestamp"]): r["big_label_count"] for r in rows}
    assert result == {
        ("hungary_budapest_20220222", 10): 2,
        ("germany_berlin_20211010", 10): 2,
        ("hungary_debrecen_20220222", 10): 2,
        ("germany_berlin_20201010", 10): 2,
    }


def test_run_all_covers_three_queries(fully_loaded):
    conn, _ = fully_loaded
    results = run_all(conn)
    assert len(results) == 3
    assert all(results.values())
