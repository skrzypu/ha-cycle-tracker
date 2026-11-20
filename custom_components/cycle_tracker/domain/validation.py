"""Framework-free invariants for recorded periods.

These helpers are consumed by repository implementations to enforce the domain
rules that are independent of any storage technology.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from .models import Period


def is_valid_period(period: Period) -> bool:
    """Return True when the period's dates are internally consistent.

    An open period is always valid. A closed period is invalid when its end
    precedes its start.
    """
    return period.end is None or period.end >= period.start


def _periods_overlap(a: Period, b: Period) -> bool:
    """Return True if two periods share at least one day."""
    a_end = a.end if a.end is not None else date.max
    b_end = b.end if b.end is not None else date.max
    return a.start <= b_end and b.start <= a_end


def period_overlaps_existing(period: Period, existing: list[Period]) -> bool:
    """Return True if the period overlaps any existing period other than itself.

    A period with the same id is ignored so that updating an existing row is
    not reported as an overlap.
    """
    for other in existing:
        if other.id == period.id:
            continue
        if _periods_overlap(period, other):
            return True
    return False


@dataclass(frozen=True)
class InvalidRowReport:
    """Reason a sheet row was excluded from the valid set."""

    row_number: int
    reason: str


def _is_newer_period(
    candidate: Period,
    candidate_row: int,
    existing: Period,
    existing_row: int,
) -> bool:
    """Return True when the candidate should win a duplicate-id tie break."""
    if candidate.updated_at is not None and existing.updated_at is not None:
        return candidate.updated_at > existing.updated_at
    if candidate.updated_at is not None:
        return True
    if existing.updated_at is not None:
        return False
    return candidate_row < existing_row


def validate_period_rows(
    candidates: list[tuple[Period | None, int]],
) -> tuple[list[Period], list[InvalidRowReport]]:
    """Return valid periods and reports for rows that must be excluded.

    Rows are validated in start-date order. A row is reported when its start is
    missing or unparsable, its end precedes its start, its range overlaps an
    already-valid row, or its ``period_id`` duplicates a newer row. When two
    rows share an id, the newest ``updated_at`` wins; if neither has one, the
    row with the smaller row number (higher in the sheet) wins.
    """
    reports: list[InvalidRowReport] = []
    parseable: list[tuple[Period, int]] = []

    for period, row_number in candidates:
        if period is None:
            reports.append(
                InvalidRowReport(row_number, "missing or unparsable start_date")
            )
            continue
        parseable.append((period, row_number))

    newest_by_id: dict[UUID, tuple[Period, int]] = {}
    for period, row_number in parseable:
        existing = newest_by_id.get(period.id)
        if existing is None:
            newest_by_id[period.id] = (period, row_number)
            continue
        existing_period, existing_row = existing
        if _is_newer_period(period, row_number, existing_period, existing_row):
            reports.append(
                InvalidRowReport(existing_row, "duplicate period_id (superseded)")
            )
            newest_by_id[period.id] = (period, row_number)
        else:
            reports.append(
                InvalidRowReport(row_number, "duplicate period_id (superseded)")
            )

    sorted_by_start = sorted(
        newest_by_id.values(), key=lambda item: (item[0].start, item[1])
    )

    valid: list[Period] = []
    for period, row_number in sorted_by_start:
        if period.end is not None and period.end < period.start:
            reports.append(InvalidRowReport(row_number, "end_date precedes start_date"))
            continue
        if period_overlaps_existing(period, valid):
            reports.append(
                InvalidRowReport(row_number, "overlaps an earlier valid row")
            )
            continue
        valid.append(period)

    return valid, reports
