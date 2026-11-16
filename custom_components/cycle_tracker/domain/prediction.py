"""The prediction pipeline: periods, configuration and a date in, a snapshot out.

``predict()`` is a pure function. It derives history through ``build_history``,
applies the configured strategy to the usable window, and turns the result into
dates, windows, a confidence value, a late state and data warnings. There is no
fallback to the configured cycle length: below two usable cycles the domain
answers ``None``, which the adapters surface as ``unknown`` (design decision 2).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

# The absolute import below resolves to the standard library even though the
# package also has a ``statistics`` module.
from statistics import fmean, pstdev

from .events import CycleEvent, project_events
from .history import History, build_history
from .models import CyclePhase, Period, Prediction
from .ports import PredictionConfig
from .statistics import (
    MINIMUM_USABLE_CYCLES,
    CycleStatistics,
    confidence_band,
    confidence_score,
    statistics,
)
from .strategies import get_strategy
from .windows import (
    OVULATION_LEAD_DAYS,
    OVULATION_WINDOW_HALF_WIDTH_DAYS,
    cycle_windows,
)

#: The uncertainty window is never narrower than the predicted date ± this.
MIN_UNCERTAINTY_HALF_WIDTH_DAYS = 2


def predict(
    periods: Sequence[Period],
    config: PredictionConfig,
    strategy_name: str,
    today: date,
) -> Prediction | None:
    """Predict the next period from the recorded periods, or ``None``."""
    history = build_history(periods, config)
    return predict_from_history(periods, config, strategy_name, today, history=history)


def predict_from_history(
    periods: Sequence[Period],
    config: PredictionConfig,
    strategy_name: str,
    today: date,
    *,
    history: History,
) -> Prediction | None:
    """Predict from an already derived ``History``.

    Callers that also need statistics build ``build_history`` once and pass it
    here, so the prediction and the statistics cannot disagree about the data.
    """
    if len(history.usable) < MINIMUM_USABLE_CYCLES:
        return None
    latest_start = latest_period_start(periods)
    if latest_start is None:
        return None

    lengths = tuple(cycle.length_days for cycle in history.usable)
    predicted_length = get_strategy(strategy_name)(lengths)
    windows = cycle_windows(latest_start, predicted_length, config.period_length)

    mean_length = fmean(lengths)
    sigma_length = pstdev(lengths)
    half_width = max(MIN_UNCERTAINTY_HALF_WIDTH_DAYS, math.ceil(sigma_length))
    score = confidence_score(
        mean=mean_length,
        sigma=sigma_length,
        count=len(lengths),
        target=config.history_window,
    )
    is_late = today > windows.next_period

    return Prediction(
        next_period=windows.next_period,
        cycle_length_days=predicted_length,
        uncertainty=(
            max(windows.next_period - timedelta(days=half_width), latest_start),
            windows.next_period + timedelta(days=half_width),
        ),
        ovulation=windows.ovulation,
        ovulation_center=windows.ovulation_center,
        fertile=windows.fertile,
        confidence=score,
        confidence_band=confidence_band(score),
        is_late=is_late,
        days_late=(today - windows.next_period).days if is_late else 0,
        days_until_period=max(0, (windows.next_period - today).days),
        days_until_ovulation=max(0, (windows.ovulation_center - today).days),
        warnings=history.warnings,
        usable_cycle_count=len(lengths),
    )


def latest_period_start(periods: Sequence[Period]) -> date | None:
    """The most recent recorded period start, even while that period is open."""
    if not periods:
        return None
    return max(period.start for period in periods)


def cycle_day(periods: Sequence[Period], today: date) -> int | None:
    """Elapsed day of the current cycle, day 1 on the start date.

    The count never wraps at the configured length; a late period keeps counting
    and the prediction's late flag carries the distinction (BDR-0004).
    """
    starts = [period.start for period in periods if period.start <= today]
    if not starts:
        return None
    return (today - max(starts)).days + 1


def phase_at(
    periods: Sequence[Period],
    prediction: Prediction | None,
    config: PredictionConfig,
    reference_date: date,
) -> CyclePhase | None:
    """Derive the phase of one date from the ovulation center of its cycle.

    A completed cycle uses its actual next start, so its phases are stable once
    the next period is logged; only the current cycle follows the prediction.
    The configured period length wins over the ovulation window, and when the
    window collapses there is no ovulatory phase at all.
    """
    if prediction is None:
        return None

    starts = sorted({period.start for period in periods})
    if not starts or reference_date < starts[0]:
        return None

    cycle_start = max(start for start in starts if start <= reference_date)
    next_start = _following_start(starts, cycle_start, prediction)
    center = next_start - timedelta(days=OVULATION_LEAD_DAYS)
    ovulation_start = max(
        center - timedelta(days=OVULATION_WINDOW_HALF_WIDTH_DAYS),
        cycle_start + timedelta(days=config.period_length),
    )
    ovulation_end = min(
        center + timedelta(days=OVULATION_WINDOW_HALF_WIDTH_DAYS),
        next_start - timedelta(days=1),
    )

    day = (reference_date - cycle_start).days + 1
    if day <= config.period_length:
        return CyclePhase.MENSTRUAL
    if reference_date < ovulation_start:
        return CyclePhase.FOLLICULAR
    if reference_date <= ovulation_end:
        return CyclePhase.OVULATORY
    return CyclePhase.LUTEAL


def _following_start(
    starts: Sequence[date], cycle_start: date, prediction: Prediction
) -> date:
    """The next actual start for a completed cycle, else the predicted one."""
    position = starts.index(cycle_start)
    if position + 1 < len(starts):
        return starts[position + 1]
    return prediction.next_period


@dataclass(frozen=True)
class Snapshot:
    """Everything the entities show, derived once for one reference date."""

    reference_date: date
    prediction: Prediction | None
    cycle_day: int | None
    phase: CyclePhase | None
    statistics: CycleStatistics
    events: tuple[CycleEvent, ...]


def build_snapshot(
    periods: Sequence[Period],
    config: PredictionConfig,
    strategy_name: str,
    today: date,
) -> Snapshot:
    """Derive history once and feed prediction, statistics, phase and events."""
    history = build_history(periods, config)
    prediction = predict_from_history(
        periods, config, strategy_name, today, history=history
    )
    return Snapshot(
        reference_date=today,
        prediction=prediction,
        cycle_day=cycle_day(periods, today),
        phase=phase_at(periods, prediction, config, today),
        statistics=statistics(periods, history, config),
        events=project_events(prediction, config) if prediction else (),
    )
