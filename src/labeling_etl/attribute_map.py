"""Attribute mapping: translate raw attribute values (e.g. country names)
into canonical values (ISO 3166-1 alpha-2 country codes)."""

from __future__ import annotations

from typing import Callable, Iterable, Iterator, Mapping

COUNTRY_CODES: dict[str, str] = {
    "Hungary": "HU",
    "Germany": "DE",
    "Austria": "AT",
    "France": "FR",
    "Italy": "IT",
    "Spain": "ES",
    "Poland": "PL",
    "Czech Republic": "CZ",
    "Slovakia": "SK",
    "Romania": "RO",
    "Netherlands": "NL",
    "Belgium": "BE",
    "United States": "US",
    "United Kingdom": "GB",
    "Japan": "JP",
    "China": "CN",
}


class AttributeMapper:
    """Callable mapping raw values to canonical values.

    - Values already equal to a target code (e.g. "HU") pass through unchanged.
    - With ``case_insensitive=True`` lookup ignores case ("germany" -> "DE").
    - Unknown values raise ``ValueError`` when ``strict=True``; otherwise they
      are returned unchanged.
    """

    def __init__(self, mapping: Mapping[str, str], *, strict: bool = True, case_insensitive: bool = True) -> None:
        self.mapping = dict(mapping)
        self.strict = strict
        self.case_insensitive = case_insensitive
        self._codes = set(mapping.values())
        if case_insensitive:
            self._lookup = {k.lower(): v for k, v in mapping.items()}
        else:
            self._lookup = dict(mapping)

    def __call__(self, value: str) -> str:
        if value is None:
            raise ValueError("cannot map None")
        cleaned = value.strip()
        if cleaned in self._codes:
            return cleaned
        key = cleaned.lower() if self.case_insensitive else cleaned
        if key in self._lookup:
            return self._lookup[key]
        if self.strict:
            raise ValueError(f"unknown attribute value: {value!r}")
        return value


country_code = AttributeMapper(COUNTRY_CODES)


def map_attribute(
    records: Iterable[dict],
    column: str,
    mapper: Callable[[str], str],
) -> Iterator[dict]:
    """Apply ``mapper`` to ``column`` of each record, yielding updated dicts."""
    for record in records:
        yield {**record, column: mapper(record[column])}
