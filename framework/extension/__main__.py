"""CLI for the "new UI + existing API + existing database" extension
capability — bridges a `framework.sync` capability catalog (what the
existing, mature framework already has) with a `framework.discovery`
report (what a brand-new, zero-test UI actually does), and answers: what
can be reused, what needs extending, and what genuinely needs to be
created?

    # One-shot: analyze the existing framework AND discover the new UI in
    # a single command (the normal customer path — no need to run three
    # separate CLIs by hand).
    poetry run python -m framework.extension analyze \\
        --framework /path/to/existing-framework \\
        --url https://new-ui.example.com \\
        --output extension_report.json \\
        [--mode reuse-analysis|extension-plan|ai-recommendations] \\
        [--crawl --max-pages 5] [--env dev --ai-output extension_ai_recommendations.json]

    # Advanced: reuse already-computed reports instead of re-running
    # analysis/discovery (e.g. CI re-runs correlation against a report
    # produced earlier).
    poetry run python -m framework.extension analyze \\
        --sync-report existing_framework_analysis.json \\
        --discovery-report new_ui_discovery_report.json \\
        --output extension_report.json

    # Framework-native scaffold — writes NEW automation only for items the
    # extension analysis classified CREATE_NEW/EXTEND_EXISTING, in the
    # customer's own detected language/framework/test-runner style. Always
    # a preview until --approve is passed; --dry-run always previews.
    poetry run python -m framework.extension scaffold \\
        --extension-report extension_report.json \\
        --sync-report existing_framework_analysis.json \\
        --discovery-report new_ui_discovery_report.json \\
        --output-dir generated/extension \\
        [--approve] [--overwrite] [--dry-run]

This CLI never runs discovery or repository analysis a second time behind
your back — `analyze --framework/--url` runs them internally by calling
the exact same `RepositoryAnalyzer`/`UIDiscoveryEngine` the standalone
`python -m framework.sync`/`python -m framework.discovery` CLIs use, and
also saves the intermediate `--sync-report`/`--discovery-report` files so
a later `scaffold` run (or a rerun of `analyze`) can reuse them instead of
repeating the work.

The four customer-choice modes this capability supports:

    DISCOVER ONLY              -> just run `python -m framework.discovery`
                                   (this CLI is not involved at all)
    DISCOVER + REUSE ANALYSIS  -> `analyze --mode reuse-analysis`
                                   (UI/API/DB correlations only)
    DISCOVER + EXTENSION PLAN  -> `analyze --mode extension-plan` (default)
                                   (adds the extension gap report, reuse
                                   matrix, and test opportunity inventory)
    DISCOVER + OPTIONAL AI     -> `analyze --mode ai-recommendations`
                                   (adds AI suggestions for whatever the
                                   deterministic pass left as
                                   MANUAL_REVIEW/UNKNOWN — gated by
                                   `ai.enabled`, see `framework.ai`)

Never modifies the existing framework's repository or the new UI's
source. `analyze` writes plain, inspectable JSON reports a human reviews
before acting on anything. `scaffold` writes actual draft source files,
but ONLY under `--output-dir` (which must resolve inside
`framework.project_root.PROJECT_ROOT`), ONLY after `--approve`, and NEVER
by overwriting an existing file unless `--overwrite` is also given (same
"the report/plan is the checkpoint" precedent as `framework.discovery`/
`framework.sync`, extended with an explicit human-approval gate before
anything is actually written).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from framework.cli_common import run_command
from framework.discovery.models import DiscoveredNetworkCall, DiscoveredPage, DiscoveryReport
from framework.exceptions import ConfigurationError
from framework.extension.ai_recommendations import recommend_for_ambiguous_items
from framework.extension.correlation import correlate_database_usage, correlate_network_calls
from framework.extension.discovery_quality import compute_discovery_quality
from framework.extension.gap_analysis import (
    build_extension_items,
    build_test_opportunities,
    format_reuse_matrix,
)
from framework.extension.models import DiscoveryQualityLevel, ExtensionReport, ScaffoldTarget
from framework.extension.network_classification import classify_network_calls, page_host_from_url
from framework.extension.paths import resolve_scaffold_output_dir
from framework.extension.scaffold import build_scaffold_plan, write_scaffold_plan
from framework.sync.models import RepositoryAnalysis

_MODES = ("reuse-analysis", "extension-plan", "ai-recommendations")


def _all_network_calls(discovery_report: DiscoveryReport) -> list[DiscoveredNetworkCall]:
    return [call for page in discovery_report.pages for call in page.network_calls]


def _load_or_analyze_framework(args: argparse.Namespace) -> RepositoryAnalysis:
    if args.framework:
        from framework.sync.__main__ import _resolve_source
        from framework.sync.analyzer import RepositoryAnalyzer

        source = _resolve_source(args.framework)
        root = source.materialize()
        try:
            analysis = RepositoryAnalyzer().analyze(root, source=args.framework)
        finally:
            source.cleanup()
        analysis.save(args.sync_report)
        print(
            f"Analyzed existing framework ({analysis.structure.total_files} files, "
            f"{analysis.primary_language}) — saved to {args.sync_report}"
        )
        return analysis

    if not Path(args.sync_report).exists():
        raise ConfigurationError(
            f"--sync-report {args.sync_report!r} does not exist and --framework was not given "
            "— pass --framework to analyze the existing repository fresh, or point "
            "--sync-report at an already-computed `python -m framework.sync analyze` report."
        )
    return RepositoryAnalysis.load(args.sync_report)


def _discover_or_load_new_ui(args: argparse.Namespace) -> DiscoveryReport:
    if args.url:
        from playwright.sync_api import sync_playwright

        from framework.discovery.ui_discovery import UIDiscoveryEngine

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not args.headed)
            page = browser.new_page()
            engine = UIDiscoveryEngine(page)
            pages = (
                engine.crawl(
                    args.url,
                    max_pages=args.max_pages,
                    capture_network=True,
                    network_url_pattern=args.network_url_pattern,
                )
                if args.crawl
                else [
                    engine.discover_page(
                        args.url,
                        capture_network=True,
                        network_url_pattern=args.network_url_pattern,
                    )
                ]
            )
            browser.close()

        discovery_report = DiscoveryReport(source=args.url, pages=pages)
        discovery_report.save(args.discovery_report)
        print(f"Discovered {len(pages)} new-UI page(s) — saved to {args.discovery_report}")
        return discovery_report

    if not Path(args.discovery_report).exists():
        raise ConfigurationError(
            f"--discovery-report {args.discovery_report!r} does not exist and --url was not "
            "given — pass --url to discover the new UI fresh, or point --discovery-report at "
            "an already-computed `python -m framework.discovery ui --capture-network` report."
        )
    return DiscoveryReport.load(args.discovery_report)


def _filter_pages_to_kept_calls(
    pages: list[DiscoveredPage], kept_calls: list[DiscoveredNetworkCall]
) -> list[DiscoveredPage]:
    """Rebuilds `pages` with each page's `network_calls` restricted to
    `kept_calls` (equality, not identity — `DiscoveredNetworkCall` is a
    plain Pydantic model, so two structurally identical calls compare
    equal even across different page/call instances) — the same list
    `build_extension_items`/`build_test_opportunities` should see, so
    static/framework/analytics/third-party noise never reaches the reuse
    matrix or test opportunity inventory either, not just `correlations`.
    """
    return [
        page.model_copy(
            update={"network_calls": [c for c in page.network_calls if c in kept_calls]}
        )
        for page in pages
    ]


def _cmd_analyze(args: argparse.Namespace) -> None:
    analysis = _load_or_analyze_framework(args)
    discovery_report = _discover_or_load_new_ui(args)
    catalog = analysis.capability_catalog

    calls = _all_network_calls(discovery_report)
    page_host = page_host_from_url(discovery_report.pages[0].url) if discovery_report.pages else ""
    classification = classify_network_calls(calls, page_host=page_host)
    quality = compute_discovery_quality(
        discovery_report.pages, requested_url=args.url, classification=classification
    )
    application_calls = classification.application_and_auth_calls()

    correlations = correlate_network_calls(application_calls, catalog) + correlate_database_usage(
        application_calls, catalog
    )

    report = ExtensionReport(
        existing_framework_source=analysis.source,
        new_ui_source=discovery_report.source,
        correlations=correlations,
        network_classification=classification,
        discovery_quality=quality,
    )

    if args.mode in ("extension-plan", "ai-recommendations"):
        filtered_pages = _filter_pages_to_kept_calls(discovery_report.pages, application_calls)
        report.extension_items = build_extension_items(filtered_pages, catalog)
        report.test_opportunities = build_test_opportunities(filtered_pages, catalog)

    report.save(args.output)

    summary = classification.summary
    print(
        f"\nNetwork classification: {summary.raw_count} raw call(s) -> "
        f"{len(classification.classified_calls)} after deduplication -> "
        f"{summary.application_candidate_count} application API, "
        f"{summary.authentication_count} authentication, "
        f"{summary.static_or_framework_ignored} static/framework, "
        f"{summary.analytics_ignored} analytics, {summary.third_party_ignored} third-party, "
        f"{summary.document_ignored} document, {summary.unknown_count} unknown."
    )
    print(f"Discovery quality: {quality.level.value.upper()} ({quality.score}/100)")
    for reason in quality.reasons:
        print(f"  - {reason}")
    if quality.level == DiscoveryQualityLevel.BLOCKED:
        print(
            "\nWARNING: discovery quality is BLOCKED — this report likely reflects an "
            "authentication redirect rather than the actual application. Do not scaffold "
            "from it; re-run discovery with a valid authenticated session."
        )

    print(
        f"\n{len(report.correlations)} UI/API/database correlation(s) against the existing "
        "catalog (static/framework/analytics/third-party noise excluded)."
    )
    if report.extension_items:
        counts = Counter(item.classification.value for item in report.extension_items)
        breakdown = ", ".join(f"{name}={count}" for name, count in sorted(counts.items()))
        print(f"Extension classification breakdown: {breakdown}")
        print()
        print(format_reuse_matrix(report.extension_items))
    if report.test_opportunities:
        print(f"\n{len(report.test_opportunities)} test opportunity/opportunities inventoried.")
    print(f"\nFull extension report saved to {args.output} — review before acting on it.")

    if args.mode == "ai-recommendations":
        from framework.ai import get_provider
        from framework.config.settings import get_settings
        from framework.enums.environment import Environment

        settings = get_settings(Environment(args.env))
        provider = get_provider(settings.ai)
        recommendations = recommend_for_ambiguous_items(report.extension_items, provider)
        Path(args.ai_output).write_text(
            json.dumps([r.model_dump(mode="json") for r in recommendations], indent=2),
            encoding="utf-8",
        )
        print(
            f"{len(recommendations)} AI recommendation(s) from provider '{provider.name}' for "
            f"ambiguous items written to {args.ai_output} — review before acting on any of them."
        )


def _cmd_scaffold(args: argparse.Namespace) -> None:
    analysis = RepositoryAnalysis.load(args.sync_report)
    discovery_report = DiscoveryReport.load(args.discovery_report)
    extension_report = ExtensionReport.load(args.extension_report)
    target = ScaffoldTarget(args.target) if args.target else None

    files, manifest = build_scaffold_plan(
        analysis, discovery_report, extension_report, target=target
    )

    print(f"Detected scaffold target: {manifest.target.value}")
    print(f"{len(files)} file(s) in the plan:")
    for file in files:
        print(f"  {file.relative_path}")
    if manifest.reused_capabilities:
        print(f"\nReused capabilities ({len(manifest.reused_capabilities)}):")
        for name in manifest.reused_capabilities:
            print(f"  - {name}")
    if manifest.manual_review_items:
        print(f"\n{len(manifest.manual_review_items)} item(s) need manual review (not scaffolded):")
        for item in manifest.manual_review_items:
            print(f"  - {item}")

    if args.dry_run or not args.approve:
        reason = "--dry-run" if args.dry_run else "no --approve given"
        print(f"\nPreview only ({reason}) — no files written. Pass --approve to write them.")
        return

    written = write_scaffold_plan(files, args.output_dir, overwrite=args.overwrite)
    output_root = resolve_scaffold_output_dir(args.output_dir)
    manifest_path = output_root / "extension-manifest.json"
    manifest.save(manifest_path)

    print(f"\n{len(written)} file(s) written under {output_root}.")
    print(f"Manifest: {manifest_path}")
    print(
        "GENERATED SCAFFOLD — REVIEW REQUIRED. Review every TODO and run the customer's "
        "normal test command before treating any of this as real automation."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m framework.extension", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Correlate a new UI against an existing framework's capability catalog",
    )
    analyze_parser.add_argument(
        "--framework",
        default=None,
        help="Existing framework: local directory, .zip file, or git URL. Analyzed fresh and "
        "saved to --sync-report. Omit to reuse an already-computed --sync-report instead.",
    )
    analyze_parser.add_argument("--sync-report", default="existing_framework_analysis.json")
    analyze_parser.add_argument(
        "--url",
        default=None,
        help="New UI URL. Discovered fresh (with network capture) and saved to "
        "--discovery-report. Omit to reuse an already-computed --discovery-report instead.",
    )
    analyze_parser.add_argument("--discovery-report", default="new_ui_discovery_report.json")
    analyze_parser.add_argument("--crawl", action="store_true", help="Used only with --url")
    analyze_parser.add_argument("--max-pages", type=int, default=5, help="Used only with --url")
    analyze_parser.add_argument("--headed", action="store_true", help="Used only with --url")
    analyze_parser.add_argument(
        "--network-url-pattern", default="**/*", help="Used only with --url"
    )
    analyze_parser.add_argument("--output", default="extension_report.json")
    analyze_parser.add_argument(
        "--mode",
        choices=_MODES,
        default="extension-plan",
        help=(
            "'reuse-analysis' (UI/API/DB correlations only), 'extension-plan' (default; "
            "adds the extension gap report, reuse matrix, and test opportunity inventory), or "
            "'ai-recommendations' (adds optional AI suggestions for ambiguous items)"
        ),
    )
    analyze_parser.add_argument(
        "--env", default="dev", help="Used only with --mode ai-recommendations"
    )
    analyze_parser.add_argument(
        "--ai-output",
        default="extension_ai_recommendations.json",
        help="Used only with --mode ai-recommendations",
    )
    analyze_parser.set_defaults(func=_cmd_analyze)

    scaffold_parser = subparsers.add_parser(
        "scaffold",
        help="Generate framework-native scaffold code for CREATE_NEW/EXTEND_EXISTING items",
    )
    scaffold_parser.add_argument("--extension-report", required=True, help="Output of `analyze`")
    scaffold_parser.add_argument(
        "--sync-report",
        required=True,
        help="Used to detect the existing framework's own language/framework/test-runner style",
    )
    scaffold_parser.add_argument(
        "--discovery-report", required=True, help="Used for discovered page/element data"
    )
    scaffold_parser.add_argument("--output-dir", default="generated/extension")
    scaffold_parser.add_argument(
        "--target",
        choices=[t.value for t in ScaffoldTarget],
        default=None,
        help="Override the auto-detected scaffold target",
    )
    scaffold_parser.add_argument(
        "--approve",
        action="store_true",
        help="Actually write the generated files (default: preview only, nothing written)",
    )
    scaffold_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Always preview only, even if --approve is also passed",
    )
    scaffold_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting a file that already exists at a generated path",
    )
    scaffold_parser.set_defaults(func=_cmd_scaffold)

    # Deferred: `framework.extension.run` imports several private helpers
    # back from this module (`_load_or_analyze_framework`, etc.) to reuse
    # them rather than duplicating the logic — a top-level import here
    # would be circular. By the time `main()` runs, this module has
    # already finished defining everything, so the import is safe here.
    from framework.extension.run import run as _cmd_run

    run_parser = subparsers.add_parser(
        "run",
        help="One-command pipeline: preflight -> analyze -> discover -> classify -> correlate "
        "-> plan -> safety-gate -> optional scaffold. See framework.extension.run for the exit "
        "code table.",
    )
    run_parser.add_argument(
        "--framework",
        default=None,
        help="Existing framework: local directory, .zip file, or git URL",
    )
    run_parser.add_argument("--url", default=None, help="New UI URL to discover")
    run_parser.add_argument("--crawl", action="store_true", help="Used only with --url")
    run_parser.add_argument("--max-pages", type=int, default=5, help="Used only with --url")
    run_parser.add_argument("--headed", action="store_true", help="Used only with --url")
    run_parser.add_argument("--network-url-pattern", default="**/*", help="Used only with --url")
    run_parser.add_argument("--output-dir", default="extension-output")
    run_parser.add_argument(
        "--skip-doctor", action="store_true", help="Skip the environment preflight check"
    )
    run_parser.add_argument(
        "--scaffold",
        action="store_true",
        help="Also generate scaffold code (default: analysis only)",
    )
    run_parser.add_argument(
        "--target",
        choices=[t.value for t in ScaffoldTarget],
        default=None,
        help="Override the auto-detected scaffold target",
    )
    run_parser.add_argument(
        "--yes", action="store_true", help="Skip the interactive scaffold-write confirmation"
    )
    run_parser.add_argument(
        "--allow-dirty", action="store_true", help="Allow scaffolding with uncommitted git changes"
    )
    run_parser.add_argument(
        "--overwrite", action="store_true", help="Allow overwriting an existing scaffold file"
    )
    run_parser.add_argument(
        "--dry-run", action="store_true", help="Preview the scaffold plan; never write files"
    )
    run_parser.set_defaults(func=_cmd_run)

    args = parser.parse_args(argv)
    return run_command(args.func, args)


if __name__ == "__main__":
    sys.exit(main())
