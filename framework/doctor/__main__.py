"""Environment doctor — inspects the host machine (OS, Python, Node,
browsers, FFmpeg, Docker, Git) and reports what this framework can
actually do here, before any analysis/discovery/scaffold command runs.
Read-only by default; only `--fix` ever writes anything, and only to
`.env` (this framework's existing, already-gitignored config override
layer — see `framework.doctor.env_writer`), never blindly overwriting a
value that's already set to something else.

    poetry run python -m framework doctor
    poetry run python -m framework doctor --check
    poetry run python -m framework doctor --fix
    poetry run python -m framework doctor --fix --dry-run
    poetry run python -m framework doctor --browser firefox
    poetry run python -m framework doctor --report doctor_report.json

`--browser <chromium|edge|chrome|firefox|safari>` explicitly requests one
`BrowserType` — if it isn't available, doctor reports exactly why and
never silently substitutes a different one (see `framework.doctor.report`
for why Firefox/Safari selection depends on Playwright's *own* bundled
builds, not the system browser). Omit it to let doctor auto-select the
best available option (bundled Chromium first, then Edge, Chrome,
Firefox, WebKit).

Exit codes: 0 = every required capability present; 3 = a required
capability is missing (see docs/FrameworkSync.md "Exit codes" — matches
`framework.extension.run`'s exit-code table so CI can treat 3 uniformly
as "environment problem" from either entry point).
"""

from __future__ import annotations

import argparse
import sys

from framework.cli_common import run_command
from framework.doctor.detectors import detect_all
from framework.doctor.env_writer import apply_env_change, plan_env_change
from framework.doctor.models import DoctorReport
from framework.doctor.report import (
    apply_not_required_downgrades,
    format_capability_matrix,
    format_summary_line,
    recommend_browser,
)

_EXIT_OK = 0
_EXIT_ENVIRONMENT_FAILURE = 3


def _build_report(args: argparse.Namespace) -> DoctorReport:
    capabilities = detect_all(ffmpeg_required=False)
    browser, reason = recommend_browser(capabilities, requested=args.browser)
    capabilities = apply_not_required_downgrades(capabilities, selected_browser=browser)
    return DoctorReport(
        capabilities=capabilities, recommended_browser=browser, recommendation_reason=reason
    )


def _print_fix_plan(report: DoctorReport, *, dry_run: bool, force: bool) -> None:
    if not report.recommended_browser:
        print(f"\nNo browser to configure — {report.recommendation_reason}")
        return

    change = plan_env_change("AUTOMATION_BROWSER", report.recommended_browser, force=force)
    print("\nPROPOSED .env CHANGES")
    if change.action == "unchanged":
        print(f"  AUTOMATION_BROWSER already set to {change.new_value!r} — no change needed.")
    elif change.action == "add":
        print(f"  + AUTOMATION_BROWSER={change.new_value}")
    elif change.action == "update":
        print(f"  ~ AUTOMATION_BROWSER={change.old_value!r} -> {change.new_value!r} (--force)")
    elif change.action == "skipped_conflict":
        print(
            f"  AUTOMATION_BROWSER is already set to {change.old_value!r} (recommended: "
            f"{change.new_value!r}) — left unchanged. Pass --force to override."
        )

    if dry_run:
        print("\n--dry-run: no files were written.")
        return

    apply_env_change(change)
    if change.action in ("add", "update"):
        print(f"\nWrote AUTOMATION_BROWSER={change.new_value} to .env")


def _cmd_doctor(args: argparse.Namespace) -> int:
    report = _build_report(args)

    print(format_capability_matrix(report.capabilities))
    print()
    print(f"Recommended browser: {report.recommended_browser or '(none)'}")
    print(f"  {report.recommendation_reason}")
    print()
    print(format_summary_line(report))

    if args.fix:
        _print_fix_plan(report, dry_run=args.dry_run, force=args.force)

    if args.report:
        report.save(args.report)
        print(f"\nFull capability report saved to {args.report}")

    return _EXIT_OK if report.passed else _EXIT_ENVIRONMENT_FAILURE


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m framework.doctor", description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Explicit CI-friendly alias — behavior is identical to the default (both exit "
        "non-zero when a required capability is missing).",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Propose (and, unless --dry-run, apply) an AUTOMATION_BROWSER .env update based "
        "on the recommended browser.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="With --fix, show proposed changes without writing"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="With --fix, allow overwriting an existing conflicting .env value",
    )
    parser.add_argument(
        "--browser",
        choices=["chromium", "edge", "chrome", "firefox", "safari"],
        default=None,
        help="Explicitly request one browser instead of auto-selecting",
    )
    parser.add_argument("--report", default=None, help="Optional path to save the JSON report")
    parser.set_defaults(func=_cmd_doctor)

    args = parser.parse_args(argv)
    return run_command(args.func, args)


if __name__ == "__main__":
    sys.exit(main())
