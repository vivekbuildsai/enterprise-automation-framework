"""CLI for the Application Discovery Engine.

    poetry run python -m framework.discovery ui <url> --report report.json [--crawl] \\
        [--max-pages 5] \\
        [--capture-network] [--network-url-pattern "**/*"]
    poetry run python -m framework.discovery api <openapi.json> --report report.json
    poetry run python -m framework.discovery db <db_key> --env dev --report report.json
    poetry run python -m framework.discovery generate --report report.json --output-dir generated/
    poetry run python -m framework.discovery recommend --report report.json --env dev \
        --output recommendations.json

Each of `ui`/`api`/`db` appends to `--report` (creating it if it doesn't
exist yet), so a full discovery pass against one application is typically:
run `ui`, `api`, and `db` against the same `--report` file, inspect/edit
the resulting JSON by hand (the human review step), then run `generate`.

`recommend` is entirely optional (gated by `ai.enabled` in
config/environments/<env>.yaml — see `framework.ai`): it asks the
configured `AIProvider` for a suggested method name/description per
discovered element and writes them to `--output`, without changing
`--report` or anything under `generated/`. With AI disabled/unconfigured
it still runs and writes recommendations — each one just carries
`RecommendationConfidence.DISCOVERED` ("no AI opinion available") instead
of `AI_SUGGESTED`.

Only run `ui`/`db` against an application/database you are authorized to
access — see `UIDiscoveryEngine`/`DatabaseDiscoveryEngine` docstrings.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from framework.cli_common import run_command
from framework.discovery.ai_recommendations import recommend_for_report
from framework.discovery.api_discovery import discover_from_openapi
from framework.discovery.code_generator import (
    DomainModelGenerator,
    PageObjectGenerator,
    write_generated_file,
)
from framework.discovery.db_discovery import DatabaseDiscoveryEngine
from framework.discovery.models import DiscoveryReport
from framework.discovery.ui_discovery import UIDiscoveryEngine


def _load_or_new_report(path: Path, *, source: str) -> DiscoveryReport:
    if path.exists():
        return DiscoveryReport.load(path)
    return DiscoveryReport(source=source)


def _cmd_ui(args: argparse.Namespace) -> None:
    from playwright.sync_api import sync_playwright

    report_path = Path(args.report)
    report = _load_or_new_report(report_path, source=args.url)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        page = browser.new_page()
        engine = UIDiscoveryEngine(page)
        pages = (
            engine.crawl(
                args.url,
                max_pages=args.max_pages,
                capture_network=args.capture_network,
                network_url_pattern=args.network_url_pattern,
            )
            if args.crawl
            else [
                engine.discover_page(
                    args.url,
                    capture_network=args.capture_network,
                    network_url_pattern=args.network_url_pattern,
                )
            ]
        )
        browser.close()

    report.pages.extend(pages)
    report.save(report_path)
    print(f"Discovered {len(pages)} page(s) — report saved to {report_path}")


def _cmd_api(args: argparse.Namespace) -> None:
    report_path = Path(args.report)
    spec = json.loads(Path(args.openapi_file).read_text(encoding="utf-8"))
    endpoints = discover_from_openapi(spec)

    report = _load_or_new_report(report_path, source=args.openapi_file)
    report.endpoints.extend(endpoints)
    report.save(report_path)
    print(f"Discovered {len(endpoints)} endpoint(s) — report saved to {report_path}")


def _cmd_db(args: argparse.Namespace) -> None:
    from framework.config.settings import get_settings
    from framework.database.connection import DatabaseManager
    from framework.enums.environment import Environment

    report_path = Path(args.report)
    settings = get_settings(Environment(args.env))
    manager = DatabaseManager(settings)
    engine = manager.get_engine(args.db_key)
    tables = DatabaseDiscoveryEngine(engine).discover_tables()
    manager.dispose_all()

    report = _load_or_new_report(report_path, source=f"{args.env}:{args.db_key}")
    report.tables.extend(tables)
    report.save(report_path)
    print(f"Discovered {len(tables)} table(s) — report saved to {report_path}")


def _cmd_generate(args: argparse.Namespace) -> None:
    report = DiscoveryReport.load(args.report)

    written: list[Path] = []
    for index, page in enumerate(report.pages):
        class_name = f"DiscoveredPage{index}"
        content = PageObjectGenerator.generate(page, class_name=class_name)
        written.append(write_generated_file(content, args.output_dir, f"{class_name.lower()}.py"))

    for index, table in enumerate(report.tables):
        class_name = "".join(part.capitalize() for part in table.name.split("_")) or f"Table{index}"
        content = DomainModelGenerator.generate(table, class_name=class_name)
        written.append(write_generated_file(content, args.output_dir, f"{class_name.lower()}.py"))

    for path in written:
        print(f"Generated {path}")
    print(f"\n{len(written)} file(s) written to {args.output_dir} — review before use.")


def _cmd_recommend(args: argparse.Namespace) -> None:
    from framework.ai import get_provider
    from framework.config.settings import get_settings
    from framework.enums.environment import Environment

    report = DiscoveryReport.load(args.report)
    settings = get_settings(Environment(args.env))
    provider = get_provider(settings.ai)

    recommendations = recommend_for_report(report, provider)
    Path(args.output).write_text(
        json.dumps([r.model_dump(mode="json") for r in recommendations], indent=2),
        encoding="utf-8",
    )
    print(
        f"{len(recommendations)} recommendation(s) from provider '{provider.name}' "
        f"written to {args.output} — review before acting on any of them."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m framework.discovery", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    ui_parser = subparsers.add_parser("ui", help="Discover UI pages/elements from a real page")
    ui_parser.add_argument("url")
    ui_parser.add_argument("--report", default="discovery_report.json")
    ui_parser.add_argument("--crawl", action="store_true")
    ui_parser.add_argument("--max-pages", type=int, default=5)
    ui_parser.add_argument("--headed", action="store_true")
    ui_parser.add_argument(
        "--capture-network",
        action="store_true",
        help=(
            "Opt in to shape-only network capture for extension/reuse analysis. "
            "Reports retain paths, methods, statuses, and JSON key names—never values or headers."
        ),
    )
    ui_parser.add_argument(
        "--network-url-pattern",
        default="**/*",
        help="Playwright URL pattern used only with --capture-network (default: **/*)",
    )
    ui_parser.set_defaults(func=_cmd_ui)

    api_parser = subparsers.add_parser("api", help="Discover endpoints from an OpenAPI spec file")
    api_parser.add_argument("openapi_file")
    api_parser.add_argument("--report", default="discovery_report.json")
    api_parser.set_defaults(func=_cmd_api)

    db_parser = subparsers.add_parser("db", help="Discover tables from a configured database")
    db_parser.add_argument("db_key")
    db_parser.add_argument("--env", default="dev")
    db_parser.add_argument("--report", default="discovery_report.json")
    db_parser.set_defaults(func=_cmd_db)

    generate_parser = subparsers.add_parser(
        "generate", help="Generate code from a discovery report"
    )
    generate_parser.add_argument("--report", default="discovery_report.json")
    generate_parser.add_argument("--output-dir", default="generated")
    generate_parser.set_defaults(func=_cmd_generate)

    recommend_parser = subparsers.add_parser(
        "recommend", help="Optional AI-assisted suggestions for discovered elements"
    )
    recommend_parser.add_argument("--report", default="discovery_report.json")
    recommend_parser.add_argument("--env", default="dev")
    recommend_parser.add_argument("--output", default="discovery_recommendations.json")
    recommend_parser.set_defaults(func=_cmd_recommend)

    args = parser.parse_args(argv)
    return run_command(args.func, args)


if __name__ == "__main__":
    sys.exit(main())
