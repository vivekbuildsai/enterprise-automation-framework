from __future__ import annotations

from playwright.sync_api import Browser, Playwright
from playwright.sync_api import BrowserType as PlaywrightBrowserType

from framework.config.models import BrowserConfig
from framework.enums.browser_type import BrowserType
from framework.exceptions import DriverInitializationError
from framework.logger import get_logger

_logger = get_logger("BrowserFactory")

# Maps our vendor-neutral BrowserType to the Playwright engine + launch channel.
# Edge and Chrome both run on the Chromium engine via a "channel" build;
# Safari is exercised through the WebKit engine (Playwright ships its own
# WebKit build — there is no way to drive real Safari.app on macOS/Windows,
# and Safari cannot run headless or on Linux/Docker).
_ENGINE_CHANNEL_MAP: dict[BrowserType, tuple[str, str | None]] = {
    BrowserType.CHROMIUM: ("chromium", None),
    BrowserType.CHROME: ("chromium", "chrome"),
    BrowserType.EDGE: ("chromium", "msedge"),
    BrowserType.FIREFOX: ("firefox", None),
    BrowserType.SAFARI: ("webkit", None),
}


class BrowserFactory:
    """Factory Pattern: translates our BrowserConfig into a launched
    Playwright Browser, hiding engine/channel selection from callers.
    """

    @staticmethod
    def launch(playwright: Playwright, config: BrowserConfig) -> Browser:
        if config.browser not in _ENGINE_CHANNEL_MAP:
            raise DriverInitializationError(f"Unsupported browser type: {config.browser}")

        engine_name, channel = _ENGINE_CHANNEL_MAP[config.browser]
        engine: PlaywrightBrowserType = getattr(playwright, engine_name)

        launch_kwargs: dict[str, object] = {
            "headless": config.headless,
            "slow_mo": config.slow_mo_ms,
        }
        if channel:
            launch_kwargs["channel"] = channel

        try:
            browser = engine.launch(**launch_kwargs)  # type: ignore[arg-type]
        except Exception as exc:
            raise DriverInitializationError(
                f"Failed to launch {config.browser.value} "
                f"(engine={engine_name}, channel={channel}): {exc}"
            ) from exc

        _logger.info(f"Launched {config.browser.value} (headless={config.headless})")
        return browser
