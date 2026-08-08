from __future__ import annotations

from dataclasses import dataclass

from framework.database.utilities import ResultMapper


@dataclass(frozen=True, slots=True)
class _Widget:
    widget_id: str
    label: str


def test_to_model_maps_matching_column_names() -> None:
    row = {"widget_id": "W1", "label": "Gadget"}
    assert ResultMapper.to_model(row, _Widget) == _Widget(widget_id="W1", label="Gadget")


def test_to_models_maps_every_row() -> None:
    rows = [{"widget_id": "W1", "label": "A"}, {"widget_id": "W2", "label": "B"}]
    result = ResultMapper.to_models(rows, _Widget)
    assert result == [_Widget("W1", "A"), _Widget("W2", "B")]


def test_single_or_none_returns_none_for_empty_list() -> None:
    assert ResultMapper.single_or_none([]) is None


def test_single_or_none_returns_first_row() -> None:
    rows = [{"a": 1}, {"a": 2}]
    assert ResultMapper.single_or_none(rows) == {"a": 1}
