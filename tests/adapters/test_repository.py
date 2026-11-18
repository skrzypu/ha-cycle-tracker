"""Tests for the local Store-backed period repository."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from custom_components.cycle_tracker.const import STORAGE_KEY, STORAGE_VERSION
from custom_components.cycle_tracker.domain.models import Period, legacy_period_id
from custom_components.cycle_tracker.repository import LocalStoreRepository


async def test_repository_round_trip_persists_period_id(
    hass: HomeAssistant,
) -> None:
    """A Period written to the store is read back with the same UUID identity."""
    repo = LocalStoreRepository(hass)
    period_id = uuid4()
    period = Period(
        id=period_id,
        start=date(2026, 1, 1),
        end=date(2026, 1, 5),
        flow="heavy",
        notes="a note",
    )

    await repo.upsert(period)
    loaded = await repo.read_all()

    assert len(loaded) == 1
    assert loaded[0].id == period_id
    assert loaded[0].start == date(2026, 1, 1)
    assert loaded[0].end == date(2026, 1, 5)
    assert loaded[0].flow == "heavy"
    assert loaded[0].notes == "a note"

    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    stored = await store.async_load()
    assert stored == {
        "periods": [
            {
                "period_id": str(period_id),
                "start_date": "2026-01-01",
                "end_date": "2026-01-05",
                "flow_intensity": "heavy",
                "notes": "a note",
                "updated_at": None,
            }
        ]
    }


async def test_repository_migrates_legacy_rows_on_first_read(
    hass: HomeAssistant,
) -> None:
    """Rows without a period_id get a stable derived id and are persisted back."""
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    await store.async_save(
        {
            "periods": [
                {
                    "start_date": "2026-01-01",
                    "end_date": "2026-01-05",
                    "flow_intensity": "medium",
                }
            ]
        }
    )

    repo = LocalStoreRepository(hass)
    periods = await repo.read_all()

    assert len(periods) == 1
    expected_id = legacy_period_id(date(2026, 1, 1))
    assert periods[0].id == expected_id

    stored = await store.async_load()
    assert stored["periods"][0]["period_id"] == str(expected_id)


async def test_repository_upsert_replaces_by_id(hass: HomeAssistant) -> None:
    """Upserting a period with a known id updates that row, not its neighbors."""
    repo = LocalStoreRepository(hass)
    first_id = uuid4()
    second_id = uuid4()
    await repo.upsert(Period(id=first_id, start=date(2026, 1, 1), end=date(2026, 1, 5)))
    await repo.upsert(
        Period(id=second_id, start=date(2026, 1, 29), end=date(2026, 2, 2))
    )

    await repo.upsert(
        Period(
            id=first_id,
            start=date(2026, 1, 1),
            end=date(2026, 1, 6),
            flow="light",
        )
    )

    loaded = await repo.read_all()
    assert [period.id for period in loaded] == [first_id, second_id]
    assert loaded[0].end == date(2026, 1, 6)
    assert loaded[0].flow == "light"


async def test_repository_delete_removes_matching_row(hass: HomeAssistant) -> None:
    """Deleting by id removes only the matching period."""
    repo = LocalStoreRepository(hass)
    first_id = uuid4()
    second_id = uuid4()
    await repo.upsert(Period(id=first_id, start=date(2026, 1, 1), end=date(2026, 1, 5)))
    await repo.upsert(
        Period(id=second_id, start=date(2026, 1, 29), end=date(2026, 2, 2))
    )

    await repo.delete(first_id)

    loaded = await repo.read_all()
    assert [period.id for period in loaded] == [second_id]


async def test_repository_skips_malformed_rows_without_raising(
    hass: HomeAssistant,
) -> None:
    """Malformed rows are dropped with a warning instead of crashing the load."""
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    await store.async_save(
        {
            "periods": [
                {"start_date": "2026-01-01", "end_date": "2025-12-31"},
                {"start_date": "not-a-date", "end_date": "2026-01-02"},
                {"period_id": str(uuid4()), "start_date": "2026-02-01"},
            ]
        }
    )

    repo = LocalStoreRepository(hass)
    periods = await repo.read_all()

    assert [period.start for period in periods] == [date(2026, 2, 1)]


async def test_repository_open_period_is_stored_with_end_equal_to_start(
    hass: HomeAssistant,
) -> None:
    """An open period round-trips through the end_date == start_date convention."""
    repo = LocalStoreRepository(hass)
    period_id = uuid4()
    await repo.upsert(Period(id=period_id, start=date(2026, 3, 1), end=None))

    loaded = await repo.read_all()
    assert len(loaded) == 1
    assert loaded[0].end is None

    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    stored = await store.async_load()
    assert stored["periods"][0]["end_date"] == "2026-03-01"
