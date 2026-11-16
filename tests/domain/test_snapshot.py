"""The snapshot the adapters consume (tasks 3.5 and 9.1 seam)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

import domain.prediction as prediction_module
import pytest
from domain.events import EventKind
from domain.history import History
from domain.models import CyclePhase, Period
from domain.ports import PredictionConfig
from domain.prediction import Snapshot, build_snapshot
from domain.strategies import DEFAULT_STRATEGY

CONFIG = PredictionConfig(period_length=5, cycle_length=28)
TODAY = date(2026, 11, 13)


def test_a_snapshot_reports_every_derived_value_at_once(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28], first=date(2026, 9, 8))

    snapshot = build_snapshot(periods, CONFIG, DEFAULT_STRATEGY, TODAY)

    assert isinstance(snapshot, Snapshot)
    assert snapshot.reference_date == TODAY
    assert snapshot.prediction is not None
    assert snapshot.prediction.next_period == date(2026, 12, 1)
    assert snapshot.cycle_day == 11
    assert snapshot.phase is CyclePhase.FOLLICULAR
    assert snapshot.statistics.total_cycles_tracked == 3
    assert snapshot.statistics.average_cycle_length == 28.0
    assert len(snapshot.events) == 36
    assert snapshot.events[0].kind is EventKind.PERIOD
    assert snapshot.events[0].start == date(2026, 12, 1)


def test_a_fresh_install_reports_unknowns_without_zeroes() -> None:
    snapshot = build_snapshot([], CONFIG, DEFAULT_STRATEGY, TODAY)

    assert snapshot.prediction is None
    assert snapshot.cycle_day is None
    assert snapshot.phase is None
    assert snapshot.events == ()
    assert snapshot.statistics.total_cycles_tracked == 0
    assert snapshot.statistics.confidence is None


def test_history_stays_visible_after_a_gap_without_a_prediction(
    make_period: Callable[..., Period],
) -> None:
    periods = [
        make_period(date(2026, 1, 1)),
        make_period(date(2026, 1, 29)),
        make_period(date(2026, 2, 26)),
        make_period(date(2026, 9, 1)),
        make_period(date(2026, 9, 29)),
    ]

    snapshot = build_snapshot(periods, CONFIG, DEFAULT_STRATEGY, TODAY)

    assert snapshot.prediction is None
    assert snapshot.phase is None
    assert snapshot.events == ()
    assert snapshot.cycle_day == 46
    assert snapshot.statistics.total_cycles_tracked == 5


def test_history_is_built_once_and_shared_with_every_consumer(
    monkeypatch: pytest.MonkeyPatch,
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28], first=date(2026, 9, 8))
    real_build_history = prediction_module.build_history
    real_predict = prediction_module.predict_from_history
    real_statistics = prediction_module.statistics

    built: list[History] = []
    seen: dict[str, History] = {}

    def counting_build_history(
        recorded: list[Period], config: PredictionConfig
    ) -> History:
        history = real_build_history(recorded, config)
        built.append(history)
        return history

    def recording_predict(
        recorded: list[Period],
        config: PredictionConfig,
        strategy_name: str,
        today: date,
        *,
        history: History,
    ):  # type: ignore[no-untyped-def]
        seen["prediction"] = history
        return real_predict(recorded, config, strategy_name, today, history=history)

    def recording_statistics(
        recorded: list[Period], history: History, config: PredictionConfig
    ):  # type: ignore[no-untyped-def]
        seen["statistics"] = history
        return real_statistics(recorded, history, config)

    monkeypatch.setattr(prediction_module, "build_history", counting_build_history)
    monkeypatch.setattr(prediction_module, "predict_from_history", recording_predict)
    monkeypatch.setattr(prediction_module, "statistics", recording_statistics)

    snapshot = build_snapshot(periods, CONFIG, DEFAULT_STRATEGY, TODAY)

    assert len(built) == 1
    assert seen["prediction"] is built[0]
    assert seen["statistics"] is built[0]
    assert snapshot.prediction is not None
    assert snapshot.prediction.warnings == built[0].warnings


def test_a_snapshot_is_deterministic(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28], first=date(2026, 9, 8))

    assert build_snapshot(periods, CONFIG, DEFAULT_STRATEGY, TODAY) == (
        build_snapshot(periods, CONFIG, DEFAULT_STRATEGY, TODAY)
    )
