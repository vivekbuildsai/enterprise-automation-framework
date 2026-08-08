from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from framework.exceptions import TestDataError


class JsonImporter:
    """Imports an arbitrary JSON file — see `CsvImporter`'s docstring for
    when to prefer this over `DatasetLoader.load_json`.
    """

    @staticmethod
    def import_file(path: str | Path) -> Any:
        file_path = Path(path)
        if not file_path.exists():
            raise TestDataError(f"No JSON file at '{file_path}'")
        return json.loads(file_path.read_text(encoding="utf-8"))
