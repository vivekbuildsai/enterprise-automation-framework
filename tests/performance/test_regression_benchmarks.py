"""Lightweight, deterministic regression guards for the hot paths touched
by this milestone's optimizations — not a benchmarking framework, not
wall-clock-sensitive enough to be flaky in CI. Each assertion uses a
generous ceiling (5-10x the measured baseline) so normal CI/hardware
variance never fails these; they exist to catch a *real* regression (an
accidentally reintroduced N+1 pattern, a de-optimized import, etc.), not
to enforce a precise SLA. No network, no browser — safe to run on every
commit.
"""

from __future__ import annotations

import time

from framework.database.utilities.comparison import DataComparator, Tolerance
from framework.discovery.models import DiscoveredNetworkCall
from framework.extension.correlation import correlate_network_calls
from framework.network.interceptor import NetworkInterceptor
from framework.sync.models import CapabilityCatalog, CapabilityCategory, ExistingCapability


def test_comparison_scales_linearly_not_quadratically() -> None:
    """1000 fields must not take meaningfully more than ~20x the time of
    100 fields — a quadratic regression would blow this budget by orders
    of magnitude, a linear one comfortably fits it.
    """

    def _time_compare(n: int) -> float:
        expected = {f"f{i}": i * 1.5 for i in range(n)}
        actual = {f"f{i}": i * 1.5 + 0.01 for i in range(n)}
        start = time.perf_counter()
        DataComparator.compare(
            expected, actual, left_label="e", right_label="a", tolerance=Tolerance(percentage=1.0)
        )
        return time.perf_counter() - start

    small = min(_time_compare(100) for _ in range(5))
    large = min(_time_compare(1000) for _ in range(5))

    assert large < small * 25, (
        f"1000-field compare ({large * 1000:.3f}ms) is more than 25x the 100-field "
        f"compare ({small * 1000:.3f}ms) — looks like a quadratic regression, not linear scaling"
    )


def test_comparison_of_1000_fields_stays_well_under_a_generous_ceiling() -> None:
    expected = {f"f{i}": i for i in range(1000)}
    actual = {f"f{i}": i for i in range(1000)}

    start = time.perf_counter()
    result = DataComparator.compare(expected, actual, left_label="e", right_label="a")
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert result.matched
    assert elapsed_ms < 50, f"1000-field compare took {elapsed_ms:.2f}ms (budget: 50ms)"


def test_network_interceptor_url_matching_does_not_recompile_per_call() -> None:
    """Regression guard for the regex-precompilation fix: matching 2000
    URLs against a configured pattern must stay well under a ceiling that
    would only be breached by reintroducing a per-call `re.compile`.
    """
    interceptor = NetworkInterceptor(page=None, url_pattern="**/api/dashboard/**")  # type: ignore[arg-type]
    urls = [f"https://example.test/api/dashboard/widget-{i}?ts={i}" for i in range(2000)]

    start = time.perf_counter()
    for url in urls:
        interceptor._url_matches(url)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 20, f"2000 URL matches took {elapsed_ms:.2f}ms (budget: 20ms)"


def test_database_utilities_import_stays_lightweight() -> None:
    """Regression guard for the lazy-import fix: importing `DataComparator`
    from the package root must not pull in SQLAlchemy or cryptography —
    reintroducing an eager `from .query_executor import ...` at the top of
    `framework/database/utilities/__init__.py` would silently blow this
    budget back up to ~300ms.
    """
    import subprocess
    import sys

    script = (
        "import time; t0=time.perf_counter(); "
        "from framework.database.utilities import DataComparator; "
        "print((time.perf_counter()-t0)*1000)"
    )
    result = subprocess.run(  # nosec B603 - fixed argv, no shell, same interpreter
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=30, check=True
    )
    elapsed_ms = float(result.stdout.strip())

    assert elapsed_ms < 100, (
        f"`from framework.database.utilities import DataComparator` took "
        f"{elapsed_ms:.1f}ms — expected well under 100ms; if this regresses, check "
        f"whether framework/database/utilities/__init__.py started eagerly importing "
        f"query_executor/secrets again"
    )


def test_extension_correlation_does_not_recompile_patterns_per_comparison() -> None:
    """Regression guard for the `@cache` fix on `_pattern_regex`
    (framework/extension/correlation.py): correlating 300 discovered calls
    against 300 existing API capabilities is 90,000 (call, capability)
    comparisons — before caching, each one recompiled a regex from
    scratch, which measured ~6s at a customer-scale (1500-capability)
    catalog. With caching, one compilation per distinct endpoint pattern
    is reused across every comparison, so this must stay well under a
    ceiling only a reintroduced per-comparison `re.compile` would breach.
    """
    capabilities = [
        ExistingCapability(
            category=CapabilityCategory.API_CLIENT,
            name=f"Entity{i}Api.get_entity",
            source_file=f"api/entity_{i}_api.py",
            endpoint_pattern=f"/entities{i}/{{param}}",
            http_method="GET",
        )
        for i in range(300)
    ]
    catalog = CapabilityCatalog(capabilities=capabilities)
    calls = [
        DiscoveredNetworkCall(method="GET", path=f"/entities{i}/{i}", status=200)
        for i in range(300)
    ]

    start = time.perf_counter()
    correlate_network_calls(calls, catalog)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 500, (
        f"300 calls x 300 capabilities took {elapsed_ms:.1f}ms (budget: 500ms) — looks like "
        f"the per-comparison regex-recompilation regression is back"
    )
