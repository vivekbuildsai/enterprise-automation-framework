from __future__ import annotations

import csv
from pathlib import Path

from framework.exceptions import TestDataError


class CsvImporter:
    """Imports an arbitrary CSV file — not necessarily under `data/testdata/`
    (e.g. a file handed off ad hoc by QA or another team) — into a list of
    dicts. For files that already live under `data/testdata/` and follow
    this project's convention, prefer `DatasetLoader.load_csv` instead.
    """

    @staticmethod
    def import_file(path: str | Path) -> list[dict[str, str]]:
        file_path = Path(path)
        if not file_path.exists():
            raise TestDataError(f"No CSV file at '{file_path}'")
        with file_path.open(newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))
