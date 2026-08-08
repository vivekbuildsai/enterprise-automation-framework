from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import Locator, Page

from framework.exceptions import ValidationError
from framework.logger import get_logger
from framework.project_root import PROJECT_ROOT

_logger = get_logger("VisualComparator")
_BASELINES_DIR = PROJECT_ROOT / "artifacts" / "visual_baselines"
_DIFFS_DIR = PROJECT_ROOT / "artifacts" / "visual_diffs"

# Per-channel difference below this is treated as anti-aliasing/rendering
# noise, not a real visual change — otherwise nearly every screenshot would
# "differ" by a handful of sub-pixel-rounding pixels.
_PIXEL_NOISE_THRESHOLD = 10


@dataclass(frozen=True)
class VisualComparisonResult:
    name: str
    baseline_created: bool
    diff_percentage: float
    diff_image_path: Path | None


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)


def _diff_percentage(baseline: Image.Image, actual: Image.Image) -> tuple[float, Image.Image]:
    if baseline.size != actual.size:
        # Can't do a meaningful pixel diff across different dimensions —
        # treat as a full mismatch and return the actual image as the "diff"
        # so a reviewer can see what changed layout-wise.
        return 100.0, actual.convert("RGB")

    diff = ImageChops.difference(baseline.convert("RGB"), actual.convert("RGB"))
    gray = diff.convert("L")
    histogram = gray.histogram()
    total_pixels = gray.size[0] * gray.size[1]
    differing_pixels = sum(histogram[_PIXEL_NOISE_THRESHOLD + 1 :])
    return (differing_pixels / total_pixels) * 100, diff


class VisualComparator:
    """Screenshot-comparison visual regression testing. First run for a
    given `name` establishes the baseline (this is the standard convention
    — there's no "correct" baseline to compare against yet); subsequent
    runs diff against it and fail if more than `threshold`% of pixels
    differ beyond rendering noise. A diff image is saved for any mismatch
    so a reviewer doesn't have to reproduce the failure to see what changed.
    """

    @staticmethod
    def compare_page(
        page: Page,
        name: str,
        *,
        threshold: float = 0.1,
        update_baseline: bool = False,
        full_page: bool = True,
    ) -> VisualComparisonResult:
        screenshot_bytes = page.screenshot(full_page=full_page)
        return VisualComparator._compare_bytes(
            screenshot_bytes, name, threshold=threshold, update_baseline=update_baseline
        )

    @staticmethod
    def compare_element(
        locator: Locator, name: str, *, threshold: float = 0.1, update_baseline: bool = False
    ) -> VisualComparisonResult:
        screenshot_bytes = locator.screenshot()
        return VisualComparator._compare_bytes(
            screenshot_bytes, name, threshold=threshold, update_baseline=update_baseline
        )

    @staticmethod
    def assert_matches(result: VisualComparisonResult, *, threshold: float = 0.1) -> None:
        """Raises `ValidationError` if `result` exceeds `threshold`% — split
        from `compare_*` so a caller can decide whether to assert immediately
        or inspect the result (e.g. log-only in a non-blocking visual suite).
        """
        if result.baseline_created:
            return
        if result.diff_percentage > threshold:
            raise ValidationError(
                f"Visual regression on '{result.name}': {result.diff_percentage:.2f}% of pixels "
                f"differ (threshold {threshold}%). Diff image: {result.diff_image_path}"
            )

    @staticmethod
    def _compare_bytes(
        screenshot_bytes: bytes, name: str, *, threshold: float, update_baseline: bool
    ) -> VisualComparisonResult:
        _BASELINES_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = _safe_name(name)
        baseline_path = _BASELINES_DIR / f"{safe_name}.png"
        actual_image = Image.open(io.BytesIO(screenshot_bytes))

        if update_baseline or not baseline_path.exists():
            action = "Updating" if baseline_path.exists() else "Creating"
            actual_image.save(baseline_path)
            _logger.info(f"{action} visual baseline: {baseline_path}")
            return VisualComparisonResult(
                name=name, baseline_created=True, diff_percentage=0.0, diff_image_path=None
            )

        baseline_image = Image.open(baseline_path)
        diff_pct, diff_image = _diff_percentage(baseline_image, actual_image)

        diff_image_path: Path | None = None
        if diff_pct > threshold:
            _DIFFS_DIR.mkdir(parents=True, exist_ok=True)
            diff_image_path = _DIFFS_DIR / f"{safe_name}_diff.png"
            diff_image.save(diff_image_path)
            _logger.warning(
                f"Visual diff for '{name}': {diff_pct:.2f}% — saved to {diff_image_path}"
            )
        else:
            _logger.info(f"Visual comparison for '{name}' passed: {diff_pct:.2f}% diff")

        return VisualComparisonResult(
            name=name,
            baseline_created=False,
            diff_percentage=diff_pct,
            diff_image_path=diff_image_path,
        )
