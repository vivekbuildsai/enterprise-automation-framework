from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pytest

from framework.exceptions import TestDataError
from framework.testdata.builders import SubscriberBuilder
from framework.testdata.exporters import CsvExporter, ExcelExporter, JsonExporter
from framework.testdata.importers import CsvImporter, ExcelImporter, JsonImporter

pytestmark = pytest.mark.testdata


@pytest.fixture
def sample_records() -> list[dict[str, object]]:
    return [asdict(s) for s in SubscriberBuilder().build_many(3)]


def test_csv_export_import_round_trip(
    tmp_path: Path, sample_records: list[dict[str, object]]
) -> None:
    path = CsvExporter.export(sample_records, tmp_path / "subs.csv")
    imported = CsvImporter.import_file(path)
    assert len(imported) == 3
    assert imported[0]["subscriber_id"] == sample_records[0]["subscriber_id"]


def test_json_export_import_round_trip(
    tmp_path: Path, sample_records: list[dict[str, object]]
) -> None:
    path = JsonExporter.export(sample_records, tmp_path / "subs.json")
    imported = JsonImporter.import_file(path)
    assert imported == sample_records


def test_excel_export_import_round_trip(
    tmp_path: Path, sample_records: list[dict[str, object]]
) -> None:
    path = ExcelExporter.export(sample_records, tmp_path / "subs.xlsx")
    imported = ExcelImporter.import_file(path)
    assert len(imported) == 3
    assert imported[0]["subscriber_id"] == sample_records[0]["subscriber_id"]


def test_csv_exporter_handles_empty_records(tmp_path: Path) -> None:
    path = CsvExporter.export([], tmp_path / "empty.csv")
    assert path.exists()


def test_importer_raises_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(TestDataError):
        CsvImporter.import_file(tmp_path / "does_not_exist.csv")
