"""Tests for sheet-row validation rules exercised in plain Python."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from domain.models import Period
from domain.validation import InvalidRowReport, validate_period_rows


def test_missing_start_is_reported() -> None:
    candidates = [(None, 2)]

    valid, reports = validate_period_rows(candidates)

    assert valid == []
    assert reports == [InvalidRowReport(2, "missing or unparsable start_date")]


def test_end_before_start_is_reported() -> None:
    period = Period(
        id=uuid4(), start=date(2026, 1, 5), end=date(2026, 1, 1), flow="medium"
    )

    valid, reports = validate_period_rows([(period, 4)])

    assert valid == []
    assert reports == [InvalidRowReport(4, "end_date precedes start_date")]


def test_overlap_is_reported_for_later_starting_row() -> None:
    earlier = Period(id=uuid4(), start=date(2026, 1, 1), end=date(2026, 1, 5))
    later = Period(id=uuid4(), start=date(2026, 1, 4), end=date(2026, 1, 10))

    valid, reports = validate_period_rows([(earlier, 2), (later, 3)])

    assert valid == [earlier]
    assert reports == [InvalidRowReport(3, "overlaps an earlier valid row")]


def test_non_overlapping_rows_are_both_valid() -> None:
    a = Period(id=uuid4(), start=date(2026, 1, 1), end=date(2026, 1, 5))
    b = Period(id=uuid4(), start=date(2026, 1, 10), end=date(2026, 1, 15))

    valid, reports = validate_period_rows([(a, 2), (b, 3)])

    assert valid == [a, b]
    assert reports == []


def test_duplicate_period_id_keeps_newest_updated_at() -> None:
    period_id = uuid4()
    older = Period(
        id=period_id,
        start=date(2026, 1, 1),
        end=date(2026, 1, 5),
        updated_at=datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC),
    )
    newer = Period(
        id=period_id,
        start=date(2026, 1, 1),
        end=date(2026, 1, 6),
        updated_at=datetime(2026, 1, 2, 10, 0, 0, tzinfo=UTC),
    )

    valid, reports = validate_period_rows([(older, 2), (newer, 3)])

    assert valid == [newer]
    assert reports == [InvalidRowReport(2, "duplicate period_id (superseded)")]


def test_duplicate_period_id_with_no_updated_at_keeps_smaller_row_number() -> None:
    """With no timestamps the top row (smaller row number) wins the tie-break."""
    period_id = uuid4()
    top = Period(id=period_id, start=date(2026, 1, 1), end=date(2026, 1, 5))
    lower = Period(id=period_id, start=date(2026, 1, 1), end=date(2026, 1, 6))

    valid, reports = validate_period_rows([(top, 2), (lower, 3)])

    assert valid == [top]
    assert reports == [InvalidRowReport(3, "duplicate period_id (superseded)")]


def test_duplicate_with_timestamp_beats_untimestamped_row() -> None:
    """An updated_at still wins even on the lower row when its twin has none."""
    period_id = uuid4()
    untimestamped = Period(id=period_id, start=date(2026, 1, 1), end=date(2026, 1, 5))
    timestamped = Period(
        id=period_id,
        start=date(2026, 1, 1),
        end=date(2026, 1, 6),
        updated_at=datetime(2026, 1, 2, 10, 0, 0, tzinfo=UTC),
    )

    valid, reports = validate_period_rows([(untimestamped, 2), (timestamped, 3)])

    assert valid == [timestamped]
    assert reports == [InvalidRowReport(2, "duplicate period_id (superseded)")]


def test_duplicate_top_row_with_timestamp_still_wins() -> None:
    """The timestamp rule takes precedence regardless of row position."""
    period_id = uuid4()
    timestamped = Period(
        id=period_id,
        start=date(2026, 1, 1),
        end=date(2026, 1, 5),
        updated_at=datetime(2026, 1, 2, 10, 0, 0, tzinfo=UTC),
    )
    untimestamped = Period(id=period_id, start=date(2026, 1, 1), end=date(2026, 1, 6))

    valid, reports = validate_period_rows([(timestamped, 2), (untimestamped, 3)])

    assert valid == [timestamped]
    assert reports == [InvalidRowReport(3, "duplicate period_id (superseded)")]


def test_unparsable_start_still_reported_alongside_valid_rows() -> None:
    """A non-blank row with no parseable start stays invalid; valid rows survive."""
    valid = Period(id=uuid4(), start=date(2026, 1, 1), end=date(2026, 1, 5))

    kept, reports = validate_period_rows([(None, 2), (valid, 3)])

    assert kept == [valid]
    assert reports == [InvalidRowReport(2, "missing or unparsable start_date")]


def test_valid_rows_are_sorted_by_start_date() -> None:
    b = Period(id=uuid4(), start=date(2026, 2, 1), end=date(2026, 2, 5))
    a = Period(id=uuid4(), start=date(2026, 1, 1), end=date(2026, 1, 5))

    valid, _ = validate_period_rows([(b, 2), (a, 3)])

    assert valid == [a, b]
