"""Tests for the coordinator read-through cache with a remote repository."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID, uuid4

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from custom_components.cycle_tracker.coordinator import CycleTrackerCoordinator
from custom_components.cycle_tracker.domain.models import Period


class FailingRepository:
    """Remote repository that always raises on read."""

    def __init__(self) -> None:
        self.read_calls = 0

    async def read_all(self) -> list[Period]:
        self.read_calls += 1
        raise RuntimeError("sheet unavailable")

    async def upsert(self, period: Period) -> None:
        pass

    async def delete(self, period_id: UUID) -> None:
        pass


class CannedRepository:
    """Remote repository that returns a fixed list of periods."""

    def __init__(self, periods: list[Period]) -> None:
        self.periods = periods

    async def read_all(self) -> list[Period]:
        return list(self.periods)

    async def upsert(self, period: Period) -> None:
        pass

    async def delete(self, period_id: UUID) -> None:
        pass


@pytest.fixture
def cache_store(hass: HomeAssistant) -> Store[dict[str, Any]]:
    """Return an isolated in-memory cache store."""
    return Store(hass, 1, "test_sync_cache")


async def test_coordinator_keeps_cache_on_failure_and_becomes_unavailable_after_three(
    hass: HomeAssistant,
    config_entry: Any,
    cache_store: Store[dict[str, Any]],
) -> None:
    """After a success, repeated failures fall back to the cached snapshot."""
    period_id = uuid4()
    cached_rows = [
        {
            "period_id": str(period_id),
            "start_date": "2026-01-01",
            "end_date": "2026-01-05",
            "flow_intensity": "medium",
            "notes": None,
            "updated_at": None,
        }
    ]
    await cache_store.async_save(
        {
            "periods": cached_rows,
            "last_sync": "2026-01-01T00:00:00+00:00",
            "last_error": None,
            "consecutive_failures": 0,
        }
    )

    repo = FailingRepository()
    coordinator = CycleTrackerCoordinator(
        hass, config_entry, repo=repo, cache_store=cache_store
    )

    await coordinator.async_refresh()
    assert coordinator.get_periods() == cached_rows
    assert coordinator.consecutive_failures == 1
    assert coordinator.available is True
    assert coordinator.last_error == "sheet unavailable"

    await coordinator.async_refresh()
    assert coordinator.consecutive_failures == 2
    assert coordinator.available is True

    await coordinator.async_refresh()
    assert coordinator.consecutive_failures == 3
    assert coordinator.available is False

    cached = await cache_store.async_load()
    assert cached is not None
    assert cached["periods"] == cached_rows
    assert cached["consecutive_failures"] == 3
    assert cached["last_error"] == "sheet unavailable"


async def test_coordinator_resets_failure_count_after_success(
    hass: HomeAssistant,
    config_entry: Any,
    cache_store: Store[dict[str, Any]],
) -> None:
    """A successful read zeros the failure counter and marks available."""
    await cache_store.async_save(
        {
            "periods": [],
            "last_sync": None,
            "last_error": "old error",
            "consecutive_failures": 5,
        }
    )
    period = Period(id=uuid4(), start=date(2026, 1, 1), end=date(2026, 1, 5))
    coordinator = CycleTrackerCoordinator(
        hass,
        config_entry,
        repo=CannedRepository([period]),
        cache_store=cache_store,
    )

    await coordinator.async_refresh()

    assert coordinator.consecutive_failures == 0
    assert coordinator.available is True
    assert coordinator.last_error is None
    assert coordinator.last_sync is not None
    cached = await cache_store.async_load()
    assert cached["consecutive_failures"] == 0
    assert cached["last_error"] is None


async def test_local_repository_path_ignores_cache_store(
    hass: HomeAssistant,
    config_entry: Any,
) -> None:
    """When a local repository is injected, the coordinator does not cache."""
    from custom_components.cycle_tracker.repository import LocalStoreRepository

    coordinator = CycleTrackerCoordinator(
        hass,
        config_entry,
        repo=LocalStoreRepository(hass),
    )

    assert coordinator.sync_status == {
        "last_sync": None,
        "last_error": None,
        "consecutive_failures": 0,
    }
    assert coordinator.available is True
