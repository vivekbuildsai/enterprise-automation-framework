from __future__ import annotations

import time

from framework.telemetry import RunTimer


def test_run_id_has_the_documented_format() -> None:
    timer = RunTimer()
    assert timer.run_id.startswith("RUN-")
    assert len(timer.run_id) == len("RUN-XXXX")


def test_two_timers_get_different_run_ids() -> None:
    assert RunTimer().run_id != RunTimer().run_id


def test_phase_records_a_real_elapsed_duration() -> None:
    timer = RunTimer()
    with timer.phase("Widget extraction"):
        time.sleep(0.01)

    assert len(timer.phases) == 1
    assert timer.phases[0].name == "Widget extraction"
    assert timer.phases[0].seconds >= 0.01


def test_phase_still_records_duration_when_the_block_raises() -> None:
    timer = RunTimer()
    try:
        with timer.phase("Database"):
            raise ValueError("boom")
    except ValueError:
        pass

    assert len(timer.phases) == 1
    assert timer.phases[0].name == "Database"


def test_total_seconds_sums_every_recorded_phase() -> None:
    timer = RunTimer()
    with timer.phase("A"):
        time.sleep(0.01)
    with timer.phase("B"):
        time.sleep(0.01)

    assert timer.total_seconds >= 0.02
    assert timer.total_seconds == sum(p.seconds for p in timer.phases)


def test_summary_lists_every_phase_and_a_total_row() -> None:
    timer = RunTimer()
    with timer.phase("Browser startup"):
        pass
    with timer.phase("Navigation"):
        pass

    summary = timer.summary()

    assert timer.run_id in summary
    assert "Browser startup" in summary
    assert "Navigation" in summary
    assert "Total" in summary


def test_summary_with_no_phases_does_not_crash() -> None:
    summary = RunTimer().summary()
    assert "no phases recorded" in summary
