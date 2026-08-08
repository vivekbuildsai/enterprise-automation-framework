"""CLI for the "new UI + existing API + existing database" extension
capability — bridges a `framework.sync` capability catalog (what the
existing, mature framework already has) with a `framework.discovery`
report (what a brand-new, zero-test UI actually does), and answers: what
can be reused, what needs extending, and what genuinely needs to be
created?

    poetry run python -m framework.extension analyze \\
        --discovery-report new_ui_discovery_report.json \\
        --sync-report existing_repository_analysis.json \\
        --output extension_report.json \\
        [--mode reuse-analysis|extension-plan|ai-recommendations] \\
        [--env dev --ai-output extension_ai_recommendations.json]

This CLI never runs discovery or repository analysis itself — it only
reads the two reports those already-existing, independently-runnable
commands produce (`python -m framework.discovery ui ... --report ...`
with network capture, and `python -m framework.sync analyze ...`), which
is the whole "reuse before create" point of this capability: it would be
absurd to re-implement UI/API/DB discovery a second time just to compare
it against the first.

The four customer-choice modes this capability supports:

    DISCOVER ONLY              -> just run `python -m framework.discovery`
                                   (this CLI is not involved at all)
    DISCOVER + REUSE ANALYSIS  -> `analyze --mode reuse-analysis`
                                   (UI/API/DB correlations only)
    DISCOVER + EXTENSION PLAN  -> `analyze --mode extension-plan` (default)
                                   (adds the extension gap report + test
                                   opportunity inventory)
    DISCOVER + OPTIONAL AI     -> `analyze --mode ai-recommendations`
                                   (adds AI suggestions for whatever the
                                   deterministic pass left as
                                   MANUAL_REVIEW/UNKNOWN — gated by
                                   `ai.enabled`, see `framework.ai`)

Never modifies the existing framework's repository or the new UI's
source. `--output` is the only file this command writes to besides the
optional `--ai-output` — both are plain, inspectable JSON a human reviews
before acting on anything (same "the report is the checkpoint" precedent
as `framework.discovery`/`framework.sync`).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from framework.cli_common import run_command
from framework.discovery.models import DiscoveredNetworkCall, DiscoveryReport
from framework.extension.ai_recommendations import recommend_for_ambiguous_items
from framework.extension.correlation import correlate_database_usage, correlate_network_calls
from framework.extension.gap_analysis import build_extension_items, build_test_opportunities
from framework.extension.models import ExtensionReport
from framework.sync.models import RepositoryAnalysis

_MODES = ("reuse-analysis", "extension-plan", "ai-recommendations")


def _all_network_calls(discovery_report: DiscoveryReport) -> list[DiscoveredNetworkCall]:
    return [call for page in discovery_report.pages for call in page.network_calls]


def _cmd_analyze(args: argparse.Namespace) -> None:
    discovery_report = DiscoveryReport.load(args.discovery_report)
    analysis = RepositoryAnalysis.load(args.sync_report)
    catalog = analysis.capability_catalog

    calls = _all_network_calls(discovery_report)
    correlations = correlate_network_calls(calls, catalog) + correlate_database_usage(
        calls, catalog
    )

    report = ExtensionReport(
        existing_framework_source=analysis.source,
        new_ui_source=discovery_report.source,
        correlations=correlations,
    )

    if args.mode in ("extension-plan", "ai-recommendations"):
        report.extension_items = build_extension_items(discovery_report.pages, catalog)
        report.test_opportunities = build_test_opportunities(discovery_report.pages, catalog)

    report.save(args.output)
    print(
        f"{len(report.correlations)} UI/API/database correlation(s) against the existing catalog."
    )
    if report.extension_items:
        counts = Counter(item.classification.value for item in report.extension_items)
        breakdown = ", ".join(f"{name}={count}" for name, count in sorted(counts.items()))
        print(f"Extension classification breakdown: {breakdown}")
    if report.test_opportunities:
        print(f"{len(report.test_opportunities)} test opportunity/opportunities inventoried.")
    print(f"Full extension report saved to {args.output} — review before acting on it.")

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m framework.extension", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser(
        "analyze", help="Correlate a new-UI discovery report against an existing capability catalog"
    )
    analyze_parser.add_argument(
        "--discovery-report", required=True, help="Report from `python -m framework.discovery`"
    )
    analyze_parser.add_argument(
        "--sync-report", required=True, help="Report from `python -m framework.sync analyze`"
    )
    analyze_parser.add_argument("--output", default="extension_report.json")
    analyze_parser.add_argument(
        "--mode",
        choices=_MODES,
        default="extension-plan",
        help=(
            "'reuse-analysis' (UI/API/DB correlations only), 'extension-plan' (default; "
            "adds the extension gap report + test opportunity inventory), or "
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

    args = parser.parse_args(argv)
    return run_command(args.func, args)


if __name__ == "__main__":
    sys.exit(main())
