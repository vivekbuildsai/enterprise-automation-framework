from __future__ import annotations

from axe_playwright_python.base import AxeResults
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import Page

from framework.exceptions import ValidationError
from framework.logger import get_logger

_logger = get_logger("AccessibilityChecker")
_axe = Axe()

_DEFAULT_FAILING_IMPACTS = frozenset({"critical", "serious"})


class AccessibilityChecker:
    """Wraps `axe-playwright-python` (axe-core) so accessibility checks are
    one call from a test: `AccessibilityChecker.check(page)`. Violations are
    filtered by impact before deciding pass/fail — `minor`/`moderate`
    findings are logged but don't fail the run by default, since gating on
    every axe finding (including ones with no real user impact) is how
    accessibility suites get disabled/ignored in practice; `critical`/`serious`
    are the ones worth blocking on.
    """

    @staticmethod
    def run(
        page: Page, *, context: str | list[str] | dict[str, object] | None = None
    ) -> AxeResults:
        """Runs the full axe-core scan and returns the raw results — use
        this when a test wants to inspect violations itself rather than
        have `check()` assert on them.
        """
        return _axe.run(page, context=context)

    @staticmethod
    def check(
        page: Page,
        *,
        context: str | list[str] | dict[str, object] | None = None,
        failing_impacts: frozenset[str] = _DEFAULT_FAILING_IMPACTS,
    ) -> AxeResults:
        """Runs axe-core and raises `ValidationError` if any violation's
        impact is in `failing_impacts`. Always logs the full violation
        report, even for impacts that don't fail the check, so lower-impact
        findings stay visible without blocking the build.
        """
        results = AccessibilityChecker.run(page, context=context)

        if results.violations_count == 0:
            _logger.info(f"Accessibility check passed: 0 violations on {page.url}")
            return results

        report = results.generate_report()
        _logger.warning(f"Accessibility violations found on {page.url}:\n{report}")

        blocking = [v for v in results.response["violations"] if v.get("impact") in failing_impacts]
        if blocking:
            ids = ", ".join(v["id"] for v in blocking)
            raise ValidationError(
                f"{len(blocking)} accessibility violation(s) with impact in "
                f"{sorted(failing_impacts)} found on {page.url}: {ids}\n{report}"
            )

        return results
