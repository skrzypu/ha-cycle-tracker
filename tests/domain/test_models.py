"""Value objects of the prediction domain (task 2.1)."""

from __future__ import annotations

import dataclasses
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from domain.models import (
    ConfidenceBand,
    Cycle,
    CyclePhase,
    DataWarning,
    Period,
    Prediction,
    WarningKind,
    legacy_period_id,
)


def test_period_only_requires_an_id_and_a_start_date() -> None:
    period = Period(id=uuid4(), start=date(2026, 1, 1))

    assert period.end is None
    assert period.flow is None
    assert period.notes is None
    assert period.updated_at is None


def test_period_records_everything_logging_can_capture() -> None:
    updated_at = datetime(2026, 1, 5, 9, 30, tzinfo=UTC)
    period = Period(
        id=uuid4(),
        start=date(2026, 1, 1),
        end=date(2026, 1, 5),
        flow="heavy",
        notes="cramps",
        updated_at=updated_at,
    )

    assert period.start == date(2026, 1, 1)
    assert period.end == date(2026, 1, 5)
    assert period.flow == "heavy"
    assert period.notes == "cramps"
    assert period.updated_at == updated_at


def test_period_is_frozen() -> None:
    period = Period(id=uuid4(), start=date(2026, 1, 1))

    with pytest.raises(dataclasses.FrozenInstanceError):
        period.start = date(2026, 1, 2)  # type: ignore[misc]


def test_two_periods_with_the_same_values_are_equal() -> None:
    period_id = uuid4()

    assert Period(id=period_id, start=date(2026, 1, 1)) == Period(
        id=period_id, start=date(2026, 1, 1)
    )


def test_legacy_period_id_is_stable_for_the_same_start_date() -> None:
    start = date(2026, 3, 1)

    assert legacy_period_id(start) == legacy_period_id(start)


def test_legacy_period_id_is_a_uuid_5() -> None:
    assert isinstance(legacy_period_id(date(2026, 3, 1)), UUID)
    assert legacy_period_id(date(2026, 3, 1)).version == 5


def test_legacy_period_ids_differ_between_start_dates() -> None:
    assert legacy_period_id(date(2026, 3, 1)) != legacy_period_id(date(2026, 3, 2))


def test_cycle_links_a_length_back_to_the_period_that_started_it() -> None:
    start = date(2026, 1, 29)
    cycle = Cycle(start=start, length_days=28, period_id=legacy_period_id(start))

    assert cycle.start == start
    assert cycle.length_days == 28
    assert cycle.period_id == legacy_period_id(start)


def test_warning_kinds_name_the_data_problems() -> None:
    assert WarningKind.OUTLIER == "outlier"
    assert WarningKind.GAP == "gap"
    assert WarningKind.MISSING_FLOW == "missing_flow"
    assert {kind.value for kind in WarningKind} == {
        "outlier",
        "gap",
        "missing_flow",
    }


def test_data_warning_identifies_the_affected_period() -> None:
    period_id = uuid4()
    warning = DataWarning(kind=WarningKind.GAP, period_id=period_id)

    assert warning.kind is WarningKind.GAP
    assert warning.period_id == period_id


def test_confidence_bands_and_phases_are_string_enums() -> None:
    assert ConfidenceBand.LOW == "low"
    assert ConfidenceBand.MEDIUM == "medium"
    assert ConfidenceBand.HIGH == "high"
    assert CyclePhase.MENSTRUAL == "menstrual"
    assert CyclePhase.FOLLICULAR == "follicular"
    assert CyclePhase.OVULATORY == "ovulatory"
    assert CyclePhase.LUTEAL == "luteal"
    assert CyclePhase("luteal") is CyclePhase.LUTEAL


def test_prediction_carries_dates_windows_and_state() -> None:
    period_id = uuid4()
    prediction = Prediction(
        next_period=date(2026, 12, 1),
        cycle_length_days=28,
        uncertainty=(date(2026, 11, 29), date(2026, 12, 3)),
        ovulation=(date(2026, 11, 15), date(2026, 11, 19)),
        ovulation_center=date(2026, 11, 17),
        fertile=(date(2026, 11, 12), date(2026, 11, 17)),
        confidence=0.33,
        confidence_band=ConfidenceBand.LOW,
        is_late=False,
        days_late=0,
        days_until_period=3,
        days_until_ovulation=2,
        warnings=(DataWarning(kind=WarningKind.MISSING_FLOW, period_id=period_id),),
        usable_cycle_count=2,
    )

    assert prediction.next_period == date(2026, 12, 1)
    assert prediction.cycle_length_days == 28
    assert prediction.uncertainty == (date(2026, 11, 29), date(2026, 12, 3))
    assert prediction.ovulation == (date(2026, 11, 15), date(2026, 11, 19))
    assert prediction.ovulation_center == date(2026, 11, 17)
    assert prediction.fertile == (date(2026, 11, 12), date(2026, 11, 17))
    assert prediction.confidence == 0.33
    assert prediction.confidence_band is ConfidenceBand.LOW
    assert prediction.is_late is False
    assert prediction.days_late == 0
    assert prediction.days_until_period == 3
    assert prediction.days_until_ovulation == 2
    assert prediction.warnings == (
        DataWarning(kind=WarningKind.MISSING_FLOW, period_id=period_id),
    )
    assert prediction.usable_cycle_count == 2
