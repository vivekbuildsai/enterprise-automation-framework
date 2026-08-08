from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from openpyxl import Workbook

from framework.exceptions import TestDataError


class ExcelExporter:
    @staticmethod
    def export(
        records: Sequence[dict[str, Any]], path: str | Path, *, sheet_name: str = "Sheet1"
    ) -> Path:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        workbook = Workbook()
        sheet = workbook.active
        if sheet is None:
            raise TestDataError("Newly created workbook has no active sheet")
        sheet.title = sheet_name

        if records:
            headers = list(records[0].keys())
            sheet.append(headers)
            for record in records:
                sheet.append([record.get(header) for header in headers])

        workbook.save(file_path)
        return file_path
