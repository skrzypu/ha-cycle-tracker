"""Tests for the framework-free Sheets serial-date helper."""

from __future__ import annotations

from datetime import date

from domain.date_serial import SHEETS_EPOCH, serial_to_date


def test_serial_zero_is_epoch() -> None:
    assert serial_to_date(0) == SHEETS_EPOCH


def test_serial_one_is_day_after_epoch() -> None:
    assert serial_to_date(1) == date(1899, 12, 31)


def test_serial_converts_known_date() -> None:
    days = (date(2026, 1, 1) - SHEETS_EPOCH).days
    assert serial_to_date(days) == date(2026, 1, 1)


def test_float_serial_is_accepted() -> None:
    assert serial_to_date(1.0) == date(1899, 12, 31)
