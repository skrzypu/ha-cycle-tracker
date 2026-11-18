"""Framework-free conversion for Google Sheets date serials.

Google Sheets stores dates as serial offsets from 1899-12-30. This module lets
the adapter convert raw cell values without pulling in any framework imports.
"""

from __future__ import annotations

from datetime import date, timedelta

SHEETS_EPOCH = date(1899, 12, 30)


def serial_to_date(serial: float) -> date:
    """Convert a Google Sheets date serial to a Python date."""
    return SHEETS_EPOCH + timedelta(days=float(serial))
