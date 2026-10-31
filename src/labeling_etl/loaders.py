"""Loader classes for the two labelling tool exports.

Papaya exports two CSVs (one for images, one for labels). Kumquat exports a
single denormalised CSV where every row carries both the image columns and one
label's columns; images are deduplicated within the file by their key.

Each loader exposes explicit extract / transform / load stages and a ``run``
method orchestrating them.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .extract import read_csv
from .load import load_images_delta, load_labels_delta
from .transform import ImageRecord, LabelRecord, split_kumquat_row, to_image, to_label


@dataclass(frozen=True)
class LoadResult:
    images_inserted: int = 0
    labels_inserted: int = 0


class BaseLoader:
    def extract(self) -> None:
        raise NotImplementedError

    def transform(self) -> None:
        raise NotImplementedError

    def load(self, conn: sqlite3.Connection) -> LoadResult:
        """Shared load step: delta-insert the transformed records."""
        return LoadResult(
            images_inserted=load_images_delta(conn, self._images),
            labels_inserted=load_labels_delta(conn, self._labels),
        )

    def run(self, conn: sqlite3.Connection) -> LoadResult:
        self.extract()
        self.transform()
        return self.load(conn)


class PapayaLoader(BaseLoader):
    def __init__(self, images_csv: str | Path, labels_csv: str | Path) -> None:
        self.images_csv = Path(images_csv)
        self.labels_csv = Path(labels_csv)
        self._raw_images: list[dict] = []
        self._raw_labels: list[dict] = []
        self._images: list[ImageRecord] = []
        self._labels: list[LabelRecord] = []

    def extract(self) -> None:
        self._raw_images = list(read_csv(self.images_csv))
        self._raw_labels = list(read_csv(self.labels_csv))

    def transform(self) -> None:
        self._images = [to_image(raw) for raw in self._raw_images]
        self._labels = [to_label(raw) for raw in self._raw_labels]


class KumquatLoader(BaseLoader):
    def __init__(self, csv_path: str | Path) -> None:
        self.csv_path = Path(csv_path)
        self._raw_rows: list[dict] = []
        self._images: list[ImageRecord] = []
        self._labels: list[LabelRecord] = []

    def extract(self) -> None:
        self._raw_rows = list(read_csv(self.csv_path))

    def transform(self) -> None:
        seen_image_keys: set[tuple] = set()
        self._images = []
        self._labels = []
        for raw in self._raw_rows:
            image, label = split_kumquat_row(raw)
            if image.key not in seen_image_keys:
                seen_image_keys.add(image.key)
                self._images.append(image)
            self._labels.append(label)
