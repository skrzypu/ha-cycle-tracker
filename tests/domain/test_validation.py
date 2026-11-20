"""Tests for framework-free period invariants and the repository protocol."""

from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from domain.models import Period
from domain.ports import PeriodRepository
from domain.validation import (
    InvalidRowReport,
    is_valid_period,
    period_overlaps_existing,
    validate_period_rows,
)


class InMemoryRepository:
    """Framework-free stand-in for a ``PeriodRepository``."""

    def __init__(self) -> None:
        self._periods: dict[UUID, Period] = {}

    async def read_all(self) -> list[Period]:
        return sorted(self._periods.values(), key=lambda period: period.start)

    async def upsert(self, period: Period) -> None:
        self._periods[period.id] = period

    async def delete(self, period_id: UUID) -> None:
        self._periods.pop(period_id, None)


async def test_in_memory_repository_upsert_and_delete() -> None:
    """A plain implementation can satisfy the protocol and round-trip periods."""
    repo = InMemoryRepository()
    period = Period(id=uuid4(), start=date(2026, 1, 1), end=date(2026, 1, 5))

    await repo.upsert(period)
    assert await repo.read_all() == [period]

    await repo.delete(period.id)
    assert await repo.read_all() == []


def test_open_period_is_valid() -> None:
    period = Period(id=uuid4(), start=date(2026, 1, 1), end=None)

    assert is_valid_period(period) is True


def test_closed_period_with_end_after_start_is_valid() -> None:
    period = Period(id=uuid4(), start=date(2026, 1, 1), end=date(2026, 1, 5))

    assert is_valid_period(period) is True


def test_closed_period_with_end_equal_to_start_is_valid() -> None:
    period = Period(id=uuid4(), start=date(2026, 1, 1), end=date(2026, 1, 1))

    assert is_valid_period(period) is True


def test_end_before_start_is_invalid() -> None:
    period = Period(id=uuid4(), start=date(2026, 1, 5), end=date(2026, 1, 1))

    assert is_valid_period(period) is False


def test_overlapping_periods_are_detected() -> None:
    a = Period(id=uuid4(), start=date(2026, 1, 1), end=date(2026, 1, 5))
    b = Period(id=uuid4(), start=date(2026, 1, 4), end=date(2026, 1, 10))

    assert period_overlaps_existing(a, [b]) is True


def test_non_overlapping_periods_are_not_detected() -> None:
    a = Period(id=uuid4(), start=date(2026, 1, 1), end=date(2026, 1, 5))
    b = Period(id=uuid4(), start=date(2026, 1, 10), end=date(2026, 1, 15))

    assert period_overlaps_existing(a, [b]) is False


def test_same_id_is_ignored_when_checking_overlap() -> None:
    period_id = uuid4()
    a = Period(id=period_id, start=date(2026, 1, 1), end=date(2026, 1, 5))
    b = Period(id=period_id, start=date(2026, 1, 4), end=date(2026, 1, 10))

    assert period_overlaps_existing(a, [b]) is False


def test_open_period_overlaps_with_overlapping_closed_period() -> None:
    open_period = Period(id=uuid4(), start=date(2026, 1, 10), end=None)
    closed = Period(id=uuid4(), start=date(2026, 1, 5), end=date(2026, 1, 12))

    assert period_overlaps_existing(open_period, [closed]) is True


def test_repository_protocol_membership() -> None:
    assert isinstance(InMemoryRepository(), PeriodRepository)


def test_duplicate_without_timestamps_keeps_topmost_row() -> None:
    """With no updated_at the smaller row number wins the duplicate tie-break."""
    period_id = uuid4()
    top = Period(id=period_id, start=date(2026, 1, 1), end=date(2026, 1, 5))
    lower = Period(id=period_id, start=date(2026, 1, 1), end=date(2026, 1, 6))

    valid, reports = validate_period_rows([(top, 2), (lower, 3)])

    assert valid == [top]
    assert reports == [InvalidRowReport(3, "duplicate period_id (superseded)")]
