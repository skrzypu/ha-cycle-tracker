"""End-to-end prediction through the integration's public surface.

Every test sets up the real config entry, records history only through the
``log_start``/``log_end`` services, and reads the result only from entity
states. The expectations are hard-coded from ``docs/guide/algorithms.md`` — the
shipped contract — instead of being computed with the domain functions under
test, so a wrong default strategy, a wrong history window or a broken adapter
surfaces as a wrong number rather than as agreement with itself.

The reference date is the shared ``frozen_today`` fixture, 2026-11-13.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date

import pytest

from custom_components.cycle_tracker.const import (
    ATTR_AVERAGE_CYCLE_LENGTH,
    ATTR_AVERAGE_PERIOD_LENGTH,
    ATTR_CONFIDENCE_BAND,
    ATTR_DAYS_LATE,
    ATTR_DAYS_UNTIL_PERIOD,
    ATTR_FERTILE_WINDOW_END,
    ATTR_FERTILE_WINDOW_START,
    ATTR_IS_LATE,
    ATTR_LONGEST_CYCLE,
    ATTR_OVULATION_WINDOW_END,
    ATTR_OVULATION_WINDOW_START,
    ATTR_PREDICTED_CYCLE_LENGTH,
    ATTR_PREDICTION_CONFIDENCE,
    ATTR_SHORTEST_CYCLE,
    ATTR_STD_DEV_CYCLE,
    ATTR_TOTAL_CYCLES_TRACKED,
    ATTR_UNCERTAINTY_END,
    ATTR_UNCERTAINTY_START,
    ATTR_USABLE_CYCLE_COUNT,
    ATTR_WARNINGS,
)

CYCLE_DAY = "sensor.cycle_tracker_cycle_day"
CYCLE_PHASE = "sensor.cycle_tracker_cycle_phase"
NEXT_PERIOD = "sensor.cycle_tracker_next_period_date"
NEXT_OVULATION = "sensor.cycle_tracker_next_ovulation_date"
DAYS_UNTIL_PERIOD = "sensor.cycle_tracker_days_until_period"
DAYS_UNTIL_OVULATION = "sensor.cycle_tracker_days_until_ovulation"
STATISTICS = "sensor.cycle_tracker_statistics"

PREDICTION_ENTITIES = (
    CYCLE_DAY,
    CYCLE_PHASE,
    NEXT_PERIOD,
    NEXT_OVULATION,
    DAYS_UNTIL_PERIOD,
    DAYS_UNTIL_OVULATION,
)

LogPeriod = Callable[..., Awaitable[None]]
ClosedPeriod = Callable[..., Awaitable[None]]


async def test_a_fresh_install_reports_unknown_without_zeroes(
    started_entry,
    state_of,
    calendar_events: Callable[[date, date], Awaitable[list[dict[str, object]]]],
) -> None:
    """With no recorded period every prediction entity is unknown, not zero.

    The entry carries a configured ``last_period_start`` but no stored rows; the
    contract says the configured cycle length is never used as a fake
    prediction, and the calendar starts out empty.
    """
    for entity_id in PREDICTION_ENTITIES:
        assert state_of(entity_id).state == "unknown", entity_id

    statistics = state_of(STATISTICS)
    assert statistics.state == "0"
    assert statistics.attributes[ATTR_AVERAGE_CYCLE_LENGTH] == 28.0
    assert statistics.attributes[ATTR_AVERAGE_PERIOD_LENGTH] == 5.0
    assert statistics.attributes[ATTR_PREDICTION_CONFIDENCE] is None
    assert statistics.attributes[ATTR_CONFIDENCE_BAND] is None

    assert await calendar_events(date(2026, 1, 1), date(2027, 1, 1)) == []


async def test_one_logged_period_still_reports_no_prediction(
    log_period: LogPeriod,
    state_of,
) -> None:
    """One period is zero completed cycles: the prediction stays unknown.

    The cycle day is still derived (day 25 on 2026-11-13 for a start on
    2026-10-20), but nothing that depends on two completed cycles appears.
    """
    await log_period(date(2026, 10, 20))

    assert state_of(CYCLE_DAY).state == "25"
    assert state_of(CYCLE_PHASE).state == "unknown"
    for entity_id in (
        NEXT_PERIOD,
        NEXT_OVULATION,
        DAYS_UNTIL_PERIOD,
        DAYS_UNTIL_OVULATION,
    ):
        assert state_of(entity_id).state == "unknown", entity_id

    statistics = state_of(STATISTICS)
    assert statistics.state == "1"
    assert statistics.attributes[ATTR_PREDICTION_CONFIDENCE] is None
    assert statistics.attributes[ATTR_CONFIDENCE_BAND] is None


async def test_three_logged_periods_predict_with_the_weighted_moving_average(
    closed_period: ClosedPeriod,
    log_period: LogPeriod,
    state_of,
) -> None:
    """The default strategy is the weighted moving average, not the mean.

    Three starts with cycle lengths 30 and 25 days:
    weighted = (1*30 + 2*25) / 3 = 26.67 -> 27, while the arithmetic mean and
    the median both give 28. The asserted date, windows and confidence therefore
    fail if the default strategy or the ±σ/±2-day floor wiring is wrong.
    """
    await closed_period(date(2026, 9, 16))
    await closed_period(date(2026, 10, 16))
    await log_period(date(2026, 11, 10))  # open, the latest start

    next_period = state_of(NEXT_PERIOD)
    assert next_period.state == "2026-12-07"  # 2026-11-10 + 27
    assert next_period.attributes[ATTR_PREDICTED_CYCLE_LENGTH] == 27
    assert next_period.attributes[ATTR_USABLE_CYCLE_COUNT] == 2
    # Population σ of [30, 25] is 2.5, so the half-width rounds up to 3 days.
    assert next_period.attributes[ATTR_UNCERTAINTY_START] == "2026-12-04"
    assert next_period.attributes[ATTR_UNCERTAINTY_END] == "2026-12-10"

    ovulation = state_of(NEXT_OVULATION)
    assert ovulation.state == "2026-11-23"  # 2026-12-07 - 14
    assert ovulation.attributes[ATTR_OVULATION_WINDOW_START] == "2026-11-21"
    assert ovulation.attributes[ATTR_OVULATION_WINDOW_END] == "2026-11-25"
    assert ovulation.attributes[ATTR_FERTILE_WINDOW_START] == "2026-11-18"
    assert ovulation.attributes[ATTR_FERTILE_WINDOW_END] == "2026-11-23"

    assert state_of(CYCLE_DAY).state == "4"
    assert state_of(CYCLE_PHASE).state == "menstrual"
    assert state_of(DAYS_UNTIL_PERIOD).state == "24"
    assert state_of(DAYS_UNTIL_PERIOD).attributes[ATTR_IS_LATE] is False
    assert state_of(DAYS_UNTIL_OVULATION).state == "10"

    statistics = state_of(STATISTICS)
    assert statistics.state == "3"
    assert statistics.attributes[ATTR_TOTAL_CYCLES_TRACKED] == 3
    assert statistics.attributes[ATTR_AVERAGE_CYCLE_LENGTH] == 27.5
    assert statistics.attributes[ATTR_STD_DEV_CYCLE] == 2.5
    assert statistics.attributes[ATTR_AVERAGE_PERIOD_LENGTH] == 5.0
    assert statistics.attributes[ATTR_SHORTEST_CYCLE] == 25
    assert statistics.attributes[ATTR_LONGEST_CYCLE] == 30
    # (1 - 2.5/27.5) * (2/6) = 0.9091 * 0.3333
    assert statistics.attributes[ATTR_PREDICTION_CONFIDENCE] == pytest.approx(
        0.3030303, abs=1e-6
    )
    assert statistics.attributes[ATTR_CONFIDENCE_BAND] == "low"
    assert statistics.attributes[ATTR_WARNINGS] == []


DOCUMENTED_STATISTICS_ATTRIBUTES = {
    "average_cycle_length",
    "average_period_length",
    "cycle_length_std_dev",
    "period_length_std_dev",
    "shortest_cycle",
    "longest_cycle",
    "total_cycles_tracked",
    "prediction_confidence",
    "confidence_band",
}
PREDICTION_ONLY_STATISTICS_ATTRIBUTES = {"usable_cycle_count", "warnings"}


async def test_statistics_attributes_match_the_documented_names(
    closed_period: ClosedPeriod,
    log_period: LogPeriod,
    state_of,
) -> None:
    """The statistics sensor exposes the documented attribute names verbatim.

    README and ``docs/guide/algorithms.md`` name the attributes as literal
    strings. Asserting only through imported constants would keep passing after
    a constant's value drifted from the docs (as ``std_dev_cycle`` did), so this
    test spells every key out, checks the pre-rename spellings are gone, and
    checks that ``usable_cycle_count`` and ``warnings`` appear only once a
    prediction exists.
    """
    await closed_period(date(2026, 9, 16))
    statistics = state_of(STATISTICS)

    assert DOCUMENTED_STATISTICS_ATTRIBUTES <= set(statistics.attributes)
    assert PREDICTION_ONLY_STATISTICS_ATTRIBUTES.isdisjoint(statistics.attributes)
    assert "std_dev_cycle" not in statistics.attributes
    assert "std_dev_period" not in statistics.attributes

    await closed_period(date(2026, 10, 16))
    await log_period(date(2026, 11, 10))

    attributes = state_of(STATISTICS).attributes
    assert DOCUMENTED_STATISTICS_ATTRIBUTES <= set(attributes)
    assert PREDICTION_ONLY_STATISTICS_ATTRIBUTES <= set(attributes)

    assert attributes["average_cycle_length"] == 27.5
    assert attributes["average_period_length"] == 5.0
    assert attributes["cycle_length_std_dev"] == 2.5
    assert attributes["period_length_std_dev"] == 0.0
    assert attributes["shortest_cycle"] == 25
    assert attributes["longest_cycle"] == 30
    assert attributes["total_cycles_tracked"] == 3
    assert attributes["prediction_confidence"] == pytest.approx(0.3030303, abs=1e-6)
    assert attributes["confidence_band"] == "low"
    assert attributes["usable_cycle_count"] == 2
    assert attributes["warnings"] == []


@pytest.mark.parametrize(
    ("algorithm", "next_period_date", "predicted_length", "uncertainty_start"),
    [
        # Lengths [35, 25, 27]: mean 29, weighted (35+2*25+3*27)/6 = 27.67 -> 28,
        # median 27 (the middle of 25, 27, 35). The three dates differ.
        ("arithmetic_mean", "2026-12-09", 29, "2026-12-04"),
        ("weighted_moving_average", "2026-12-08", 28, "2026-12-03"),
        ("median", "2026-12-07", 27, "2026-12-02"),
    ],
)
async def test_the_selected_algorithm_changes_the_predicted_date(
    algorithm: str,
    next_period_date: str,
    predicted_length: int,
    uncertainty_start: str,
    closed_period: ClosedPeriod,
    log_period: LogPeriod,
    set_algorithm: Callable[[str], Awaitable[None]],
    state_of,
) -> None:
    """The same three complete cycles yield a different date per algorithm.

    The history is recorded once per run and the algorithm is changed through
    the options dialog, so this also covers the option → coordinator → entity
    wiring. σ stays 4.32 for every run, which keeps confidence and the 5-day
    half-width identical while the predicted date moves.
    """
    for start in (date(2026, 8, 15), date(2026, 9, 19), date(2026, 10, 14)):
        await closed_period(start)
    await log_period(date(2026, 11, 10))

    await set_algorithm(algorithm)

    next_period = state_of(NEXT_PERIOD)
    assert next_period.state == next_period_date
    assert next_period.attributes[ATTR_PREDICTED_CYCLE_LENGTH] == predicted_length
    assert next_period.attributes[ATTR_USABLE_CYCLE_COUNT] == 3
    assert next_period.attributes[ATTR_UNCERTAINTY_START] == uncertainty_start

    statistics = state_of(STATISTICS)
    assert statistics.attributes[ATTR_TOTAL_CYCLES_TRACKED] == 4
    assert statistics.attributes[ATTR_AVERAGE_CYCLE_LENGTH] == 29.0
    assert statistics.attributes[ATTR_STD_DEV_CYCLE] == pytest.approx(
        4.3204938, abs=1e-6
    )
    assert statistics.attributes[ATTR_SHORTEST_CYCLE] == 25
    assert statistics.attributes[ATTR_LONGEST_CYCLE] == 35
    # (1 - 4.32/29) * (3/6), independent of the chosen strategy.
    assert statistics.attributes[ATTR_PREDICTION_CONFIDENCE] == pytest.approx(
        0.4255087, abs=1e-6
    )
    assert statistics.attributes[ATTR_CONFIDENCE_BAND] == "medium"


async def test_a_long_gap_restarts_the_history_window(
    closed_period: ClosedPeriod,
    log_period: LogPeriod,
    state_of,
) -> None:
    """A >90-day break discards everything before it, then needs two cycles.

    Three old 28-day cycles are followed by a 104-day gap and five new cycles
    (26, 27, 28, 29, 30). The weighted average of only the new five is
    430/15 = 28.67 -> 29, so the next period is 2026-11-03 + 29 = 2026-12-02.
    Keeping the pre-gap cycles would include a sixth 28-day cycle and predict
    2026-12-01, so the asserted date proves the window really restarted.
    """
    old_starts = (date(2026, 1, 7), date(2026, 2, 4), date(2026, 3, 4))
    new_starts = (
        date(2026, 6, 16),  # 104 days after 2026-03-04, the gap
        date(2026, 7, 12),
        date(2026, 8, 8),
        date(2026, 9, 5),
        date(2026, 10, 4),
        date(2026, 11, 3),
    )
    for start in (*old_starts, *new_starts[:-1]):
        await closed_period(start)
    await log_period(new_starts[-1])

    next_period = state_of(NEXT_PERIOD)
    assert next_period.state == "2026-12-02"
    assert next_period.attributes[ATTR_PREDICTED_CYCLE_LENGTH] == 29
    assert next_period.attributes[ATTR_USABLE_CYCLE_COUNT] == 5
    # σ of [26, 27, 28, 29, 30] is √2 ≈ 1.42, so the floor of ±2 wins.
    assert next_period.attributes[ATTR_UNCERTAINTY_START] == "2026-11-30"
    assert next_period.attributes[ATTR_UNCERTAINTY_END] == "2026-12-04"

    ovulation = state_of(NEXT_OVULATION)
    assert ovulation.state == "2026-11-18"
    assert ovulation.attributes[ATTR_OVULATION_WINDOW_START] == "2026-11-16"
    assert ovulation.attributes[ATTR_OVULATION_WINDOW_END] == "2026-11-20"
    assert ovulation.attributes[ATTR_FERTILE_WINDOW_START] == "2026-11-13"
    assert ovulation.attributes[ATTR_FERTILE_WINDOW_END] == "2026-11-18"

    assert state_of(CYCLE_DAY).state == "11"
    assert state_of(CYCLE_PHASE).state == "follicular"
    assert state_of(DAYS_UNTIL_PERIOD).state == "19"
    assert state_of(DAYS_UNTIL_OVULATION).state == "5"

    statistics = state_of(STATISTICS)
    assert statistics.state == "9"
    assert statistics.attributes[ATTR_TOTAL_CYCLES_TRACKED] == 9
    assert statistics.attributes[ATTR_AVERAGE_CYCLE_LENGTH] == 28.0
    assert statistics.attributes[ATTR_STD_DEV_CYCLE] == pytest.approx(
        1.4142136, abs=1e-6
    )
    assert statistics.attributes[ATTR_SHORTEST_CYCLE] == 26
    assert statistics.attributes[ATTR_LONGEST_CYCLE] == 30
    # (1 - √2/28) * (5/6) = 0.9495 * 0.8333
    assert statistics.attributes[ATTR_PREDICTION_CONFIDENCE] == pytest.approx(
        0.7912436, abs=1e-6
    )
    assert statistics.attributes[ATTR_CONFIDENCE_BAND] == "high"

    warnings = statistics.attributes[ATTR_WARNINGS]
    assert [warning["kind"] for warning in warnings] == ["gap"]
    assert isinstance(warnings[0]["period_id"], str)


async def test_only_the_six_most_recent_cycles_feed_the_prediction(
    closed_period: ClosedPeriod,
    log_period: LogPeriod,
    state_of,
) -> None:
    """The oldest of seven usable cycles does not influence the date.

    The last six lengths are 25, 30, 30, 30, 30, 30, so the weighted average is
    (25 + 2*30 + ... + 6*30)/21 = 625/21 = 29.76 -> 30 and the next period is
    2026-11-10 + 30 = 2026-12-10. The seventh, oldest cycle is 15 days; a
    seven-cycle window would average it in, predict 29 days and land on
    2026-12-09, so the date pins the cap at six.
    """
    starts = (
        date(2026, 5, 4),
        date(2026, 5, 19),
        date(2026, 6, 13),
        date(2026, 7, 13),
        date(2026, 8, 12),
        date(2026, 9, 11),
        date(2026, 10, 11),
        date(2026, 11, 10),
    )
    for start in starts[:-1]:
        await closed_period(start)
    await log_period(starts[-1])

    next_period = state_of(NEXT_PERIOD)
    assert next_period.state == "2026-12-10"
    assert next_period.attributes[ATTR_PREDICTED_CYCLE_LENGTH] == 30
    assert next_period.attributes[ATTR_USABLE_CYCLE_COUNT] == 6
    assert next_period.attributes[ATTR_UNCERTAINTY_START] == "2026-12-08"
    assert next_period.attributes[ATTR_UNCERTAINTY_END] == "2026-12-12"

    statistics = state_of(STATISTICS)
    assert statistics.state == "8"
    assert statistics.attributes[ATTR_AVERAGE_CYCLE_LENGTH] == pytest.approx(
        29.1666667, abs=1e-6
    )
    assert statistics.attributes[ATTR_STD_DEV_CYCLE] == pytest.approx(
        1.8633900, abs=1e-6
    )
    # (1 - 1.8634/29.1667) * (6/6)
    assert statistics.attributes[ATTR_PREDICTION_CONFIDENCE] == pytest.approx(
        0.9361123, abs=1e-6
    )
    assert statistics.attributes[ATTR_CONFIDENCE_BAND] == "high"


async def test_the_period_due_today_is_not_late(
    closed_period: ClosedPeriod,
    log_period: LogPeriod,
    state_of,
) -> None:
    """Due today reads zero days until and no late flag.

    Two 28-day cycles whose latest start is 2026-10-16 predict 2026-11-13, the
    frozen reference date. An off-by-one late check would flip the flag here,
    while the sensor must still report the date itself as today.
    """
    await closed_period(date(2026, 8, 21))
    await closed_period(date(2026, 9, 18))
    await log_period(date(2026, 10, 16))

    assert state_of(NEXT_PERIOD).state == "2026-11-13"
    days_until = state_of(DAYS_UNTIL_PERIOD)
    assert days_until.state == "0"
    assert days_until.attributes[ATTR_IS_LATE] is False
    assert days_until.attributes[ATTR_DAYS_LATE] == 0
    assert state_of(CYCLE_DAY).state == "29"
    assert state_of(CYCLE_PHASE).state == "luteal"


async def test_a_late_period_freezes_the_date_and_clamps_days_until(
    closed_period: ClosedPeriod,
    log_period: LogPeriod,
    state_of,
) -> None:
    """A period four days overdue keeps its old date and is flagged late.

    Two stable 28-day cycles put the predicted date at 2026-11-09, four days
    before the frozen 2026-11-13. The date must stay in the past, the days
    count must clamp to zero, and the late flag plus the late count carry the
    distinction from "due today".
    """
    await closed_period(date(2026, 8, 17))
    await closed_period(date(2026, 9, 14))
    await log_period(date(2026, 10, 12))

    next_period = state_of(NEXT_PERIOD)
    assert next_period.state == "2026-11-09"
    assert next_period.attributes[ATTR_PREDICTED_CYCLE_LENGTH] == 28

    days_until = state_of(DAYS_UNTIL_PERIOD)
    assert days_until.state == "0"
    assert days_until.attributes[ATTR_DAYS_UNTIL_PERIOD] == 0
    assert days_until.attributes[ATTR_IS_LATE] is True
    assert days_until.attributes[ATTR_DAYS_LATE] == 4

    assert state_of(DAYS_UNTIL_OVULATION).state == "0"
    assert state_of(CYCLE_DAY).state == "33"
    assert state_of(CYCLE_PHASE).state == "luteal"

    statistics = state_of(STATISTICS)
    assert statistics.attributes[ATTR_STD_DEV_CYCLE] == 0.0
    assert statistics.attributes[ATTR_PREDICTION_CONFIDENCE] == pytest.approx(1 / 3)
    assert statistics.attributes[ATTR_CONFIDENCE_BAND] == "low"


async def test_a_short_outlier_is_excluded_before_the_window(
    closed_period: ClosedPeriod,
    log_period: LogPeriod,
    state_of,
) -> None:
    """A 10-day cycle is excluded before the window, not averaged in.

    Lengths 28, 10, 29: the 10-day cycle leaves the window and a warning, so
    the default weighted average of the remaining [28, 29] is
    (28 + 2*29)/3 = 28.67 -> 29 and the date is 2026-11-07 + 29 = 2026-12-06.
    Including the outlier would predict a 23-day cycle and move the date.
    """
    await closed_period(date(2026, 9, 1))
    await closed_period(date(2026, 9, 29))
    await closed_period(date(2026, 10, 9))  # ten days after the previous start
    await log_period(date(2026, 11, 7))

    next_period = state_of(NEXT_PERIOD)
    assert next_period.state == "2026-12-06"
    assert next_period.attributes[ATTR_PREDICTED_CYCLE_LENGTH] == 29
    assert next_period.attributes[ATTR_USABLE_CYCLE_COUNT] == 2
    # σ of [28, 29] is 0.5, so the ±2-day floor applies.
    assert next_period.attributes[ATTR_UNCERTAINTY_START] == "2026-12-04"
    assert next_period.attributes[ATTR_UNCERTAINTY_END] == "2026-12-08"

    assert state_of(CYCLE_DAY).state == "7"
    assert state_of(CYCLE_PHASE).state == "follicular"
    assert state_of(DAYS_UNTIL_PERIOD).state == "23"
    assert state_of(DAYS_UNTIL_OVULATION).state == "9"

    statistics = state_of(STATISTICS)
    assert statistics.attributes[ATTR_TOTAL_CYCLES_TRACKED] == 4
    assert statistics.attributes[ATTR_AVERAGE_CYCLE_LENGTH] == 28.5
    # (1 - 0.5/28.5) * (2/6)
    assert statistics.attributes[ATTR_PREDICTION_CONFIDENCE] == pytest.approx(
        0.3274854, abs=1e-6
    )
    assert statistics.attributes[ATTR_CONFIDENCE_BAND] == "low"
    warnings = statistics.attributes[ATTR_WARNINGS]
    assert [warning["kind"] for warning in warnings] == ["outlier"]
