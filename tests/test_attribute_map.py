import pytest

from labeling_etl.attribute_map import (
    AttributeMapper,
    COUNTRY_CODES,
    country_code,
    map_attribute,
)


def test_known_country_maps_to_code():
    assert country_code("Hungary") == "HU"
    assert country_code("Germany") == "DE"


def test_case_insensitive_lookup():
    assert country_code("germany") == "DE"
    assert country_code("hungary") == "HU"


def test_existing_code_passes_through():
    assert country_code("HU") == "HU"
    assert country_code("DE") == "DE"


def test_unknown_strict_raises():
    with pytest.raises(ValueError):
        country_code("Atlantis")


def test_unknown_non_strict_passes_through():
    mapper = AttributeMapper(COUNTRY_CODES, strict=False)
    assert mapper("Atlantis") == "Atlantis"


def test_case_sensitive_mode():
    mapper = AttributeMapper(COUNTRY_CODES, case_insensitive=False)
    assert mapper("Germany") == "DE"
    with pytest.raises(ValueError):
        mapper("germany")


def test_map_attribute_helper():
    records = [{"country": "Hungary"}, {"country": "Germany"}]
    mapped = list(map_attribute(records, "country", country_code))
    assert [r["country"] for r in mapped] == ["HU", "DE"]
    # originals untouched
    assert records[0]["country"] == "Hungary"
