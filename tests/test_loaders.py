from labeling_etl.extract import read_csv
from labeling_etl.load import load_labels_delta
from labeling_etl.loaders import KumquatLoader, PapayaLoader
from labeling_etl.transform import LabelRecord, normalize_coordinates


def _count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _kumquat_distinct_image_keys(csv_path):
    return {(r["record_file_name"], r["timestamp"]) for r in read_csv(csv_path)}


def test_papaya_loader_counts(papaya_loaded):
    conn, result = papaya_loaded
    assert result.images_inserted == 10
    assert result.labels_inserted == 18
    assert _count(conn, "images") == 10
    assert _count(conn, "labels") == 18


def test_papaya_loader_maps_countries(papaya_loaded):
    conn, _ = papaya_loaded
    countries = {row[0] for row in conn.execute("SELECT DISTINCT country FROM images")}
    assert countries == {"HU", "DE"}


def test_papaya_loader_delta_second_run(papaya_loaded):
    conn, _ = papaya_loaded
    from conftest import PAPAYA_IMAGES, PAPAYA_LABELS

    result = PapayaLoader(PAPAYA_IMAGES, PAPAYA_LABELS).run(conn)
    assert result.images_inserted == 0
    assert result.labels_inserted == 0
    assert _count(conn, "images") == 10
    assert _count(conn, "labels") == 18


def test_kumquat_loader_counts(conn, data_dir):
    csv_path = data_dir / "kumquat" / "kumquat_output.csv"
    expected_images = len(_kumquat_distinct_image_keys(csv_path))
    # distinct images in the file: debrecen(2) + pecs_20220216(3) + berlin_20201010(3)
    assert expected_images == 8
    result = KumquatLoader(csv_path).run(conn)
    assert result.images_inserted == 8
    assert result.labels_inserted == 13


def test_kumquat_loader_delta_second_run(conn, data_dir):
    csv_path = data_dir / "kumquat" / "kumquat_output.csv"
    KumquatLoader(csv_path).run(conn)
    result = KumquatLoader(csv_path).run(conn)
    assert result.images_inserted == 0
    assert result.labels_inserted == 0
    assert _count(conn, "images") == 8
    assert _count(conn, "labels") == 13


def test_delta_load_inserts_new_version_but_not_duplicate(conn):
    label = LabelRecord(
        "f",
        10,
        "car",
        1.0,
        normalize_coordinates('{"x0": 1, "y0": 2}'),
        1,
    )
    assert load_labels_delta(conn, [label]) == 1
    # identical row is a duplicate -> skipped
    assert load_labels_delta(conn, [label]) == 0
    # same coordinates, newer version -> inserted (re-labelling)
    label_v2 = LabelRecord("f", 10, "truck", 1.0, label.label_coordinates, 2)
    assert load_labels_delta(conn, [label_v2]) == 1
    assert _count(conn, "labels") == 2


def test_both_loaders_together(papaya_loaded, data_dir):
    conn, _ = papaya_loaded
    result = KumquatLoader(data_dir / "kumquat" / "kumquat_output.csv").run(conn)
    assert result.images_inserted == 8
    assert result.labels_inserted == 13
    assert _count(conn, "images") == 18
    assert _count(conn, "labels") == 31
