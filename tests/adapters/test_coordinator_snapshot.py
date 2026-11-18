"""Tests for the coordinator as an adapter over the prediction domain."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cycle_tracker.const import DOMAIN
from custom_components.cycle_tracker.coordinator import CycleTrackerCoordinator
from custom_components.cycle_tracker.domain.models import legacy_period_id


async def test_snapshot_is_cached_for_the_same_reference_date(
    coordinator: CycleTrackerCoordinator,
    frozen_today: date,
) -> None:
    """Reading twice on the same day reuses the derived snapshot."""
    first = coordinator.snapshot
    second = coordinator.snapshot

    assert second is first
    assert first.reference_date == frozen_today


async def test_snapshot_rebuilds_when_the_reference_date_changes(
    coordinator: CycleTrackerCoordinator,
    freezer,
) -> None:
    """A new local date invalidates the cached snapshot."""
    freezer.move_to("2026-11-13 12:00:00")
    first = coordinator.snapshot

    freezer.move_to("2026-11-14 12:00:00")
    second = coordinator.snapshot

    assert second is not first
    assert second.reference_date == date(2026, 11, 14)


async def test_snapshot_rebuilds_when_periods_change(
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    frozen_today: date,
) -> None:
    """Recording a period invalidates the cached snapshot."""
    before = coordinator.snapshot

    coordinator.add_period(period_row(frozen_today - timedelta(days=10)))

    assert coordinator.snapshot is not before


async def test_legacy_rows_are_adapted_with_stable_ids(
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
) -> None:
    """Stored rows keep their shape and gain a stable domain identity."""
    first_start = date(2026, 1, 1)
    second_start = date(2026, 1, 29)
    coordinator.add_period(period_row(first_start, length=5))
    coordinator.add_period(period_row(second_start, length=4, flow="heavy"))

    periods = coordinator.get_domain_periods()

    assert [period.start for period in periods] == [first_start, second_start]
    assert periods[0].end == date(2026, 1, 5)
    assert periods[0].flow == "medium"
    assert periods[1].end == date(2026, 2, 1)
    assert periods[1].flow == "heavy"
    assert periods[0].id == legacy_period_id(first_start)
    assert [period.id for period in coordinator.get_domain_periods()] == [
        legacy_period_id(first_start),
        legacy_period_id(second_start),
    ]


async def test_a_freshly_logged_period_is_adapted_as_open(
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    frozen_today: date,
) -> None:
    """A period whose end equals its start is still open, not one day long.

    ``log_start`` stores ``end_date == start_date`` until ``log_end`` records a
    real end, so period-length statistics must not count that row.
    """
    closed_start = frozen_today - timedelta(days=33)
    open_start = frozen_today - timedelta(days=1)
    coordinator.add_period(period_row(closed_start, length=5))
    coordinator.add_period(period_row(open_start, length=1))

    periods = coordinator.get_domain_periods()

    assert [(period.start, period.end) for period in periods] == [
        (closed_start, closed_start + timedelta(days=4)),
        (open_start, None),
    ]
    statistics = coordinator.snapshot.statistics
    assert statistics.average_period_length == 5.0
    assert statistics.total_cycles_tracked == 2


async def test_legacy_rows_produce_a_prediction(
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    frozen_today: date,
) -> None:
    """Two usable cycle lengths are enough for a prediction."""
    coordinator.add_period(period_row(frozen_today - timedelta(days=88)))
    coordinator.add_period(period_row(frozen_today - timedelta(days=60)))
    coordinator.add_period(period_row(frozen_today - timedelta(days=32)))

    prediction = coordinator.snapshot.prediction

    assert prediction is not None
    assert prediction.cycle_length_days == 28
    assert prediction.next_period == frozen_today - timedelta(days=4)
    assert prediction.usable_cycle_count == 2


async def test_malformed_rows_warn_instead_of_crashing(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    sheet_emulator: Any,
    period_row: Callable[..., dict[str, Any]],
    caplog,
) -> None:
    """Malformed sheet rows are dropped with a warning, not an exception."""
    valid_row = period_row(date(2026, 2, 1))
    sheet_emulator.seed(
        [
            # End before start, then an unparsable start, then one valid row.
            ["", "2026-01-01", "2025-12-31", "medium", "", ""],
            ["", "not-a-date", "2026-01-02", "medium", "", ""],
            [
                valid_row["period_id"],
                valid_row["start_date"],
                valid_row["end_date"],
                valid_row["flow_intensity"],
                "",
                "",
            ],
        ]
    )

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    with caplog.at_level(logging.WARNING, logger="custom_components.cycle_tracker"):
        await coordinator.async_refresh()
        periods = coordinator.get_domain_periods()

    assert [period.start for period in periods] == [date(2026, 2, 1)]
    assert coordinator.snapshot is not None
    assert "missing or unparsable start_date" in caplog.text
    assert "end_date precedes start_date" in caplog.text

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
