"""Single entry point for every CLI capability this framework ships.

    poetry run python -m framework discover ...   # Application Discovery (optional)
    poetry run python -m framework sync ...        # Existing Framework Sync (optional)
    poetry run python -m framework validate --expected e.json --actual a.json
    poetry run python -m framework report generate

This is a thin dispatcher, not a new layer of logic: `discover`/`sync`
delegate straight to their own independently-runnable
`python -m framework.discovery`/`python -m framework.sync` CLIs.
`validate`/`report` are small, self-contained wrappers around existing
core building blocks (`DataComparator`, the `allure` CLI) — core
capabilities, always available, no feature flag.

`validate` does field-by-field, case/whitespace-insensitive comparison
(the real `DataComparator.compare()` behavior). `DataComparator` also
supports numeric tolerance comparison (`Tolerance(percentage=, absolute=)`)
— see `examples/data_validation` — but this CLI subcommand doesn't expose
a flag for it yet; use `DataComparator.compare(..., tolerance=...)`
directly for that.
"""

from __future__ import annotations

import argparse
import json
import subprocess  # nosec B404 - fixed argv, no shell, used for the `allure` CLI only
import sys
from pathlib import Path

from framework.cli_common import run_command


def _cmd_validate(args: argparse.Namespace) -> int:
    from framework.database.utilities.comparison import DataComparator

    expected = json.loads(Path(args.expected).read_text(encoding="utf-8"))
    actual = json.loads(Path(args.actual).read_text(encoding="utf-8"))
    fields = args.fields.split(",") if args.fields else None

    result = DataComparator.compare(
        expected, actual, left_label="expected", right_label="actual", fields=fields
    )
    print(result.to_report())
    return 0 if result.matched else 1


def _cmd_report(args: argparse.Namespace) -> int:
    command = (
        ["allure", "generate", args.results_dir, "-o", args.output_dir, "--clean"]
        if args.action == "generate"
        else ["allure", "open", args.output_dir]
    )
    try:
        subprocess.run(
            command, check=True
        )  # nosec - fixed argv, shell=False, `allure` resolved via PATH intentionally
    except FileNotFoundError:
        print(
            "The `allure` CLI isn't installed/on PATH. Install it "
            "(https://allurereport.org/docs/install/) or use the `allure-report` "
            "docker-compose service instead.",
            file=sys.stderr,
        )
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"allure {args.action} failed (exit {exc.returncode}).", file=sys.stderr)
        return exc.returncode
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    command, rest = argv[0], argv[1:]

    if command == "discover":
        from framework.discovery.__main__ import main as discovery_main

        return discovery_main(rest)

    if command == "sync":
        from framework.sync.__main__ import main as sync_main

        return sync_main(rest)

    if command == "validate":
        parser = argparse.ArgumentParser(prog="python -m framework validate")
        parser.add_argument("--expected", required=True, help="Path to a JSON file")
        parser.add_argument("--actual", required=True, help="Path to a JSON file")
        parser.add_argument(
            "--fields",
            default=None,
            help="Comma-separated field list (default: keys present in both files)",
        )
        return run_command(_cmd_validate, parser.parse_args(rest))

    if command == "report":
        parser = argparse.ArgumentParser(prog="python -m framework report")
        parser.add_argument("action", choices=["generate", "open"])
        parser.add_argument("--results-dir", default="reports/allure-results")
        parser.add_argument("--output-dir", default="reports/allure-report")
        return run_command(_cmd_report, parser.parse_args(rest))

    print(f"Unknown command: {command!r}. Run with --help.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
