from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonExporter:
    @staticmethod
    def export(data: Any, path: str | Path) -> Path:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return file_path
