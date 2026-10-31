"""Transform stage: parse raw CSV strings into typed records.

- ``label_size`` uses a decimal comma ("0,5" -> 0.5).
- ``label_coordinates`` is a JSON string; it is normalised so the stored value
  is canonical (sorted keys, fixed separators) and therefore comparable as a
  string — important because coordinates are part of a label's identity.
- ``country`` names are mapped to ISO codes through the attribute map.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

from .attribute_map import country_code as default_country_code


def parse_float(s: str) -> float:
    """Parse a float that may use a decimal comma."""
    return float(str(s).strip().replace(",", "."))


def parse_int(s: str) -> int:
    return int(str(s).strip())


def normalize_coordinates(s: str) -> str:
    """Normalise a JSON coordinate string to a canonical form."""
    return json.dumps(json.loads(s), sort_keys=True, separators=(", ", ": "))


@dataclass(frozen=True)
class ImageRecord:
    record_file_name: str
    timestamp: int
    image_format: str
    image_path: str
    country: str

    @property
    def key(self) -> tuple:
        return (self.record_file_name, self.timestamp)

    def as_row(self) -> tuple:
        return (
            self.record_file_name,
            self.timestamp,
            self.image_format,
            self.image_path,
            self.country,
        )


@dataclass(frozen=True)
class LabelRecord:
    record_file_name: str
    timestamp: int
    label_type: str
    label_size: float
    label_coordinates: str
    version: int

    @property
    def key(self) -> tuple:
        # version is NOT part of the identity: a higher version of the same
        # coordinates is a re-labelling handled by the dedup step.
        return (self.record_file_name, self.timestamp, self.label_coordinates)

    def as_row(self) -> tuple:
        return (
            self.record_file_name,
            self.timestamp,
            self.label_type,
            self.label_size,
            self.label_coordinates,
            self.version,
        )


def to_image(raw: dict, country_mapper: Callable[[str], str] = default_country_code) -> ImageRecord:
    return ImageRecord(
        record_file_name=raw["record_file_name"],
        timestamp=parse_int(raw["timestamp"]),
        image_format=raw["image_format"],
        image_path=raw["image_path"],
        country=country_mapper(raw["country"]),
    )


def to_label(raw: dict) -> LabelRecord:
    return LabelRecord(
        record_file_name=raw["record_file_name"],
        timestamp=parse_int(raw["timestamp"]),
        label_type=raw["label_type"],
        label_size=parse_float(raw["label_size"]),
        label_coordinates=normalize_coordinates(raw["label_coordinates"]),
        version=parse_int(raw["version"]),
    )


def split_kumquat_row(raw: dict, country_mapper: Callable[[str], str] = default_country_code) -> tuple[ImageRecord, LabelRecord]:
    """Split a denormalised Kumquat row into its image and label parts."""
    return to_image(raw, country_mapper), to_label(raw)
