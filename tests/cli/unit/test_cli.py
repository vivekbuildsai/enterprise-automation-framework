from __future__ import annotations

import json

import pytest

from framework.cli import main

pytestmark = pytest.mark.cli


def test_no_args_prints_help_and_exits_zero(capsys) -> None:
    exit_code = main([])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "discover" in captured.out
    assert "sync" in captured.out
    assert "extension" in captured.out


def test_unknown_command_exits_nonzero(capsys) -> None:
    exit_code = main(["bogus-command"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Unknown command" in captured.err


class TestValidateErrorHandling:
    def test_missing_expected_file_is_a_clean_error_not_a_traceback(self, tmp_path, capsys) -> None:
        actual = tmp_path / "actual.json"
        actual.write_text("{}")

        exit_code = main(
            ["validate", "--expected", str(tmp_path / "missing.json"), "--actual", str(actual)]
        )
        captured = capsys.readouterr()

        assert exit_code == 1
        assert "Error:" in captured.err
        assert "Traceback" not in captured.err

    def test_malformed_json_is_a_clean_error_not_a_traceback(self, tmp_path, capsys) -> None:
        expected = tmp_path / "expected.json"
        actual = tmp_path / "actual.json"
        expected.write_text("not valid json")
        actual.write_text("{}")

        exit_code = main(["validate", "--expected", str(expected), "--actual", str(actual)])
        captured = capsys.readouterr()

        assert exit_code == 1
        assert "Error:" in captured.err
        assert "Traceback" not in captured.err


class TestValidate:
    def test_matching_files_exit_zero(self, tmp_path, capsys) -> None:
        expected = tmp_path / "expected.json"
        actual = tmp_path / "actual.json"
        expected.write_text(json.dumps({"total": 100}))
        actual.write_text(json.dumps({"total": 100}))

        exit_code = main(["validate", "--expected", str(expected), "--actual", str(actual)])
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "MATCH" in captured.out

    def test_mismatching_files_exit_nonzero(self, tmp_path, capsys) -> None:
        expected = tmp_path / "expected.json"
        actual = tmp_path / "actual.json"
        expected.write_text(json.dumps({"total": 100}))
        actual.write_text(json.dumps({"total": 200}))

        exit_code = main(["validate", "--expected", str(expected), "--actual", str(actual)])
        captured = capsys.readouterr()

        assert exit_code == 1
        assert "MISMATCH" in captured.out

    def test_fields_flag_restricts_compared_fields(self, tmp_path, capsys) -> None:
        expected = tmp_path / "expected.json"
        actual = tmp_path / "actual.json"
        expected.write_text(json.dumps({"total": 100, "ignored": "x"}))
        actual.write_text(json.dumps({"total": 100, "ignored": "y"}))

        exit_code = main(
            ["validate", "--expected", str(expected), "--actual", str(actual), "--fields", "total"]
        )

        assert exit_code == 0

    def test_timing_flag_prints_a_phase_summary_to_stderr_not_stdout(
        self, tmp_path, capsys
    ) -> None:
        expected = tmp_path / "expected.json"
        actual = tmp_path / "actual.json"
        expected.write_text(json.dumps({"total": 100}))
        actual.write_text(json.dumps({"total": 100}))

        exit_code = main(
            ["validate", "--expected", str(expected), "--actual", str(actual), "--timing"]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "MATCH" in captured.out
        assert "RUN-" not in captured.out  # timing summary must not pollute stdout
        assert "RUN-" in captured.err
        assert "Total" in captured.err

    def test_without_timing_flag_stderr_stays_empty(self, tmp_path, capsys) -> None:
        expected = tmp_path / "expected.json"
        actual = tmp_path / "actual.json"
        expected.write_text(json.dumps({"total": 100}))
        actual.write_text(json.dumps({"total": 100}))

        main(["validate", "--expected", str(expected), "--actual", str(actual)])
        captured = capsys.readouterr()

        assert captured.err == ""


class TestReport:
    def test_missing_allure_binary_reports_a_clear_error(self, monkeypatch, capsys) -> None:
        import subprocess

        def fake_run(*args, **kwargs):
            raise FileNotFoundError("allure not found")

        monkeypatch.setattr(subprocess, "run", fake_run)

        exit_code = main(["report", "generate"])
        captured = capsys.readouterr()

        assert exit_code == 1
        assert "allure" in captured.err.lower()


class TestDelegation:
    def test_discover_delegates_to_the_discovery_cli(self, capsys) -> None:
        # argparse's --help raises SystemExit(0) after printing — proves
        # `discover` actually reached framework.discovery's own parser
        # rather than framework.cli's.
        with pytest.raises(SystemExit) as exc_info:
            main(["discover", "--help"])
        captured = capsys.readouterr()

        assert exc_info.value.code == 0
        assert "Application Discovery Engine" in captured.out

    def test_sync_delegates_to_the_sync_cli(self, capsys) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["sync", "--help"])
        captured = capsys.readouterr()

        assert exc_info.value.code == 0
        assert "Existing Framework Sync" in captured.out

    def test_extension_delegates_to_the_extension_cli(self, capsys) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["extension", "--help"])
        captured = capsys.readouterr()

        assert exc_info.value.code == 0
        assert "new UI + existing API + existing database" in captured.out
