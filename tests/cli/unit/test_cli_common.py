from __future__ import annotations

import json

import pytest

from framework.cli_common import run_command
from framework.exceptions import ConfigurationError

pytestmark = pytest.mark.cli


class _Args:
    pass


def test_passes_through_a_successful_int_result() -> None:
    assert run_command(lambda args: 0, _Args()) == 0
    assert run_command(lambda args: 1, _Args()) == 1


def test_none_return_means_success() -> None:
    assert run_command(lambda args: None, _Args()) == 0


def test_file_not_found_becomes_exit_code_one(capsys) -> None:
    def raiser(args: object) -> None:
        raise FileNotFoundError("no such file: x.json")

    exit_code = run_command(raiser, _Args())
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Error:" in captured.err


def test_configuration_error_becomes_exit_code_one(capsys) -> None:
    def raiser(args: object) -> None:
        raise ConfigurationError("missing db_key")

    exit_code = run_command(raiser, _Args())
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "missing db_key" in captured.err


def test_malformed_json_becomes_exit_code_one() -> None:
    def raiser(args: object) -> None:
        json.loads("not json")

    assert run_command(raiser, _Args()) == 1


def test_unexpected_exception_type_still_propagates() -> None:
    """Only known, actionable failure modes are turned into a clean
    message — a genuine bug should still surface as a real traceback,
    not be silently swallowed behind a generic error line.
    """

    def raiser(args: object) -> None:
        raise RuntimeError("this is a real bug, not a user error")

    with pytest.raises(RuntimeError):
        run_command(raiser, _Args())
