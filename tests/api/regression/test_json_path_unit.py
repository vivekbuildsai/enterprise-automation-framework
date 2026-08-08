import pytest

from framework.api.validators.json_path import resolve_json_path


@pytest.mark.api
@pytest.mark.regression
class TestJsonPath:
    def test_simple_key(self) -> None:
        assert resolve_json_path({"a": 1}, "a") == 1

    def test_nested_keys(self) -> None:
        assert resolve_json_path({"a": {"b": {"c": 3}}}, "a.b.c") == 3

    def test_bracket_index(self) -> None:
        assert resolve_json_path({"items": [10, 20]}, "items[1]") == 20

    def test_dotted_digit_index(self) -> None:
        assert resolve_json_path({"items": [10, 20]}, "items.1") == 20

    def test_missing_key_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="missing"):
            resolve_json_path({"a": 1}, "missing")

    def test_index_into_non_list_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="non-list"):
            resolve_json_path({"a": 1}, "a[0]")

    def test_out_of_range_bracket_index_raises_index_error(self) -> None:
        with pytest.raises(IndexError):
            resolve_json_path({"items": [1]}, "items[5]")

    def test_out_of_range_dotted_index_raises_index_error(self) -> None:
        with pytest.raises(IndexError):
            resolve_json_path({"items": [1]}, "items.5")

    def test_resolving_key_on_scalar_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="Cannot resolve"):
            resolve_json_path({"a": 1}, "a.b")
