import pytest

from labeling_etl.transform import (
    ImageRecord,
    LabelRecord,
    normalize_coordinates,
    parse_float,
    parse_int,
    split_kumquat_row,
    to_image,
    to_label,
)


def test_parse_float_decimal_comma():
    assert parse_float("0,5") == 0.5
    assert parse_float("2") == 2.0
    assert parse_float("1,75") == 1.75


def test_parse_int():
    assert parse_int("10") == 10
    assert isinstance(parse_int("10"), int)


def test_normalize_coordinates_canonical():
    a = '{"x0": 1, "y0": 2, "x1": 3, "y1": 4}'
    b = '{"y1":4,"x1":3,"y0":2,"x0":1}'
    assert normalize_coordinates(a) == normalize_coordinates(b)


def test_image_and_label_keys():
    img = ImageRecord("file", 10, "v1", "path", "HU")
    assert img.key == ("file", 10)
    lab = LabelRecord("file", 10, "car", 0.5, "{}", 1)
    assert lab.key == ("file", 10, "{}")


def test_to_image_maps_country():
    raw = {
        "record_file_name": "f",
        "timestamp": "10",
        "image_format": "v1",
        "image_path": "p",
        "country": "Hungary",
    }
    img = to_image(raw)
    assert img.country == "HU"
    assert img.timestamp == 10


def test_to_image_custom_mapper():
    raw = {
        "record_file_name": "f",
        "timestamp": "10",
        "image_format": "v1",
        "image_path": "p",
        "country": "X",
    }
    img = to_image(raw, country_mapper=lambda v: v.lower())
    assert img.country == "x"


def test_to_label_parses_and_normalises():
    raw = {
        "record_file_name": "f",
        "timestamp": "20",
        "label_type": "car",
        "label_size": "0,5",
        "label_coordinates": '{"y0": 2, "x0": 1}',
        "version": "3",
    }
    lab = to_label(raw)
    assert lab.label_size == 0.5
    assert lab.version == 3
    assert lab.label_coordinates == normalize_coordinates(raw["label_coordinates"])


def test_split_kumquat_row():
    raw = {
        "record_file_name": "hungary_debrecen_20220222",
        "timestamp": "10",
        "image_format": "v1",
        "image_path": "my_server/my_folder/hungary_debrecen_20220222_10",
        "country": "Hungary",
        "label_type": "car",
        "label_size": "2",
        "label_coordinates": '{"x0": 1, "y0": 2}',
        "version": "1",
    }
    image, label = split_kumquat_row(raw)
    assert isinstance(image, ImageRecord) and isinstance(label, LabelRecord)
    assert image.key == ("hungary_debrecen_20220222", 10)
    assert image.country == "HU"
    assert label.label_type == "car"
    assert label.label_size == 2.0
    assert label.version == 1
