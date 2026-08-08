"""Public CLI wiring for opt-in Discovery network capture."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import ModuleType

import pytest

from framework.discovery import __main__ as discovery_cli
from framework.discovery.models import DiscoveredPage

pytestmark = pytest.mark.discovery


class _FakeBrowser:
    def new_page(self) -> object:
        return object()

    def close(self) -> None:
        pass


class _FakePlaywrightContext:
    chromium = None

    def __init__(self) -> None:
        self.chromium = self

    def __enter__(self) -> _FakePlaywrightContext:
        return self

    def __exit__(self, *_: object) -> None:
        pass

    def launch(self, *, headless: bool) -> _FakeBrowser:
        assert headless
        return _FakeBrowser()


class _FakeEngine:
    calls: list[tuple[str, bool, str, bool]] = []

    def __init__(self, _page: object) -> None:
        pass

    def discover_page(
        self, url: str, *, capture_network: bool, network_url_pattern: str
    ) -> DiscoveredPage:
        self.calls.append((url, capture_network, network_url_pattern, False))
        return DiscoveredPage(url=url)

    def crawl(
        self, url: str, *, max_pages: int, capture_network: bool, network_url_pattern: str
    ) -> list[DiscoveredPage]:
        assert max_pages == 3
        self.calls.append((url, capture_network, network_url_pattern, True))
        return [DiscoveredPage(url=url)]


def _sync_playwright() -> _FakePlaywrightContext:
    return _FakePlaywrightContext()


@pytest.fixture(autouse=True)
def fake_playwright_and_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeEngine.calls.clear()
    sync_api = ModuleType("playwright.sync_api")
    sync_api.sync_playwright = _sync_playwright  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api)
    monkeypatch.setattr(discovery_cli, "UIDiscoveryEngine", _FakeEngine)


def _args(report: Path, *, crawl: bool) -> argparse.Namespace:
    return argparse.Namespace(
        url="https://new.example.test/employees",
        report=str(report),
        crawl=crawl,
        max_pages=3,
        headed=False,
        capture_network=True,
        network_url_pattern="**/api/**",
    )


def test_ui_cli_threads_opt_in_capture_to_single_page_discovery(tmp_path: Path) -> None:
    discovery_cli._cmd_ui(_args(tmp_path / "report.json", crawl=False))

    assert _FakeEngine.calls == [("https://new.example.test/employees", True, "**/api/**", False)]


def test_ui_cli_threads_opt_in_capture_to_crawl_discovery(tmp_path: Path) -> None:
    discovery_cli._cmd_ui(_args(tmp_path / "report.json", crawl=True))

    assert _FakeEngine.calls == [("https://new.example.test/employees", True, "**/api/**", True)]
