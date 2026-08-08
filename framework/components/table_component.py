from __future__ import annotations

from typing import Any, TypedDict

from playwright.sync_api import Page

from framework.components.base_component import BaseComponent
from framework.exceptions import ElementNotFoundError

_EXTRACT_TABLE_JS = """
(root, args) => {
    const headerRow = root.querySelector(args.headerRowSelector);
    const headers = headerRow
        ? Array.from(headerRow.querySelectorAll(args.headerCellSelector)).map(el => el.innerText)
        : [];
    const bodyRows = Array.from(root.querySelectorAll(args.bodyRowSelector));
    const rows = bodyRows.map(row =>
        Array.from(row.querySelectorAll(args.bodyCellSelector)).map(el => el.innerText)
    );
    return { headers, rows };
}
"""


class _ExtractedTable(TypedDict):
    headers: list[str]
    rows: list[list[str]]


class TableComponent(BaseComponent):
    """Data table — the component every list/search-results screen in an
    enterprise app leans on. Extracts headers/rows as plain strings so
    `UIAssert.table_data()` (or a straight Python comparison) can assert on
    them without the caller touching Playwright locators at all.

    Extraction is one `evaluate()` call into the page rather than one
    Playwright round-trip per row — `rows()` on a locator-per-row basis
    turns into hundreds of IPC calls on a table with hundreds of rows;
    this framework is meant to scale to thousands of tests, and it's the
    same cost either way, so it's paid once per call instead of once per row.
    """

    def __init__(
        self,
        page: Page,
        root_selector: str = "table",
        *,
        header_row_selector: str = "thead tr",
        body_row_selector: str = "tbody tr",
        header_cell_selector: str = "th",
        body_cell_selector: str = "td",
    ) -> None:
        super().__init__(page, root_selector)
        self._header_row_selector = header_row_selector
        self._body_row_selector = body_row_selector
        self._header_cell_selector = header_cell_selector
        self._body_cell_selector = body_cell_selector

    def _extract(self) -> _ExtractedTable:
        args: dict[str, Any] = {
            "headerRowSelector": self._header_row_selector,
            "headerCellSelector": self._header_cell_selector,
            "bodyRowSelector": self._body_row_selector,
            "bodyCellSelector": self._body_cell_selector,
        }
        result: _ExtractedTable = self.root.evaluate(_EXTRACT_TABLE_JS, args)
        return result

    def headers(self) -> list[str]:
        return self._extract()["headers"]

    def row_count(self) -> int:
        return len(self._extract()["rows"])

    def rows(self) -> list[list[str]]:
        return self._extract()["rows"]

    def cell(self, row_index: int, column_index: int) -> str:
        rows = self._extract()["rows"]
        if row_index >= len(rows):
            raise ElementNotFoundError(f"Table has no row {row_index} (only {len(rows)} rows)")
        row = rows[row_index]
        if column_index >= len(row):
            raise ElementNotFoundError(f"Row {row_index} has no column {column_index}")
        return row[column_index]

    def find_row_index(self, text: str) -> int | None:
        """Index of the first row containing `text` in any cell, or `None`
        if no row matches — the building block for "find the subscriber row
        by name/ID and act on it" without hardcoding a row position.
        """
        for i, row in enumerate(self.rows()):
            if any(text in cell for cell in row):
                return i
        return None

    def click_row_action(self, row_index: int, action_label: str) -> None:
        """Clicks a link/button (e.g. "Edit"/"Delete") within a specific row."""
        row_locator = self.child(self._body_row_selector).nth(row_index)
        row_locator.get_by_text(action_label, exact=False).click()

    def sort_by_column(self, header_text: str) -> None:
        """Clicks a column header to trigger client-side/server-side sort —
        assumes the app makes header cells clickable for sortable columns,
        which is the common convention.
        """
        header_row = self.child(self._header_row_selector).first
        header_row.get_by_text(header_text, exact=False).click()
