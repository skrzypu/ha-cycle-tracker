"""Framework-free value objects of the cycle-tracking domain.

``Period`` is the only entity that is stored; ``Cycle`` and ``Prediction`` are
derived on read. Everything here is a frozen dataclass so the pipeline stays a
pure function of its inputs (ADR-0006).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

#: Namespace used to derive ids for period rows that predate stored ids.
PERIOD_ID_NAMESPACE = uuid.NAMESPACE_URL


def legacy_period_id(start: date) -> UUID:
    """Derive a stable id for a period that has no stored one.

    Stored rows are still ``{start_date, end_date, flow_intensity}``, but data
    warnings and phase lookups need an identity that survives a restart, so the
    id is a UUIDv5 over the ISO start date. Storage stays untouched until the
    logging use case writes real ids (design decision 10).
    """
    return uuid.uuid5(PERIOD_ID_NAMESPACE, start.isoformat())


@dataclass(frozen=True)
class Period:
    """A recorded period.

    ``flow`` is one of ``spotting``, ``light``, ``medium``, ``heavy`` or
    ``None`` when the user did not record it. ``end`` is ``None`` while the
    period is still open.
    """

    id: UUID
    start: date
    end: date | None = None
    flow: str | None = None
    notes: str | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class Cycle:
    """A start-to-start cycle length derived from two consecutive periods."""

    start: date
    length_days: int
    period_id: UUID


class WarningKind(StrEnum):
    """Kinds of data problem a prediction reports."""

    OUTLIER = "outlier"
    GAP = "gap"
    MISSING_FLOW = "missing_flow"


@dataclass(frozen=True)
class DataWarning:
    """A data problem, pointing at the period it concerns."""

    kind: WarningKind
    period_id: UUID


class ConfidenceBand(StrEnum):
    """Verbal band of a confidence value."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CyclePhase(StrEnum):
    """Phase of a cycle day."""

    MENSTRUAL = "menstrual"
    FOLLICULAR = "follicular"
    OVULATORY = "ovulatory"
    LUTEAL = "luteal"


@dataclass(frozen=True)
class Prediction:
    """Everything the product promises about the next period.

    The predicted date is frozen once computed: a late period flips ``is_late``
    and grows ``days_late``, it never moves ``next_period`` (BDR-0004).
    """

    next_period: date
    cycle_length_days: int
    uncertainty: tuple[date, date]
    ovulation: tuple[date, date]
    ovulation_center: date
    fertile: tuple[date, date]
    confidence: float
    confidence_band: ConfidenceBand
    is_late: bool
    days_late: int
    days_until_period: int
    days_until_ovulation: int
    warnings: tuple[DataWarning, ...]
    usable_cycle_count: int
