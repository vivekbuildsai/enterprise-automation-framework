from __future__ import annotations

from datetime import date

from playwright.sync_api import Page

from framework.components.base_component import BaseComponent


class DatePickerComponent(BaseComponent):
    """Calendar-style date picker. `select_date` accepts either a `date`
    object or a pre-formatted string, since some pickers want a typed value
    (`fill()` on the input) and others want calendar-cell clicks — both
    paths are exposed so a Page Object can use whichever the real widget needs.
    """

    def __init__(
        self,
        page: Page,
        root_selector: str = "[data-testid='date-picker']",
        *,
        input_selector: str = "input",
        trigger_selector: str = "[data-testid='date-picker-trigger']",
        next_month_selector: str = "[data-testid='date-picker-next']",
        previous_month_selector: str = "[data-testid='date-picker-prev']",
    ) -> None:
        super().__init__(page, root_selector)
        self._input_selector = input_selector
        self._trigger_selector = trigger_selector
        self._next_month_selector = next_month_selector
        self._previous_month_selector = previous_month_selector

    def open(self) -> None:
        self.click(self._trigger_selector, description="Date picker trigger")

    def type_date(self, value: date | str, *, fmt: str = "%Y-%m-%d") -> None:
        text = value.strftime(fmt) if isinstance(value, date) else value
        self.fill(self._input_selector, text, description="Date picker input")

    def select_day_cell(self, day: int) -> None:
        """Clicks a specific day cell in the currently-shown month grid —
        for pickers where the input isn't directly typeable.
        """
        self.root.get_by_role("button", name=str(day), exact=True).click()

    def next_month(self) -> None:
        self.click(self._next_month_selector, description="Next month")

    def previous_month(self) -> None:
        self.click(self._previous_month_selector, description="Previous month")

    def selected_value(self) -> str:
        return self.child(self._input_selector).input_value()
