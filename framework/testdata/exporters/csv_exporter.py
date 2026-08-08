from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path
from typing import Any


class CsvExporter:
    """Writes a list of dicts (e.g. builder output run through
    `dataclasses.asdict`) out to a CSV file — for handing generated test
    data to a non-technical stakeholder, or archiving a dataset used in a
    specific test run as a CI artifact.
    """

    @staticmethod
    def export(records: Sequence[dict[str, Any]], path: str | Path) -> Path:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if not records:
            file_path.write_text("", encoding="utf-8")
            return file_path

        fieldnames = list(records[0].keys())
        with file_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        return file_path
