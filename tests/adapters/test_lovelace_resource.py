"""Tests for the Lovelace resource upsert and cleanup."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.cycle_tracker as integration_module
from custom_components.cycle_tracker.const import (
    CONF_CYCLE_LENGTH,
    CONF_LAST_PERIOD_START,
    CONF_PERIOD_LENGTH,
    CONF_PREDICTION_ALGORITHM,
    DOMAIN,
)

CARD_URL = "/cycle_tracker/cycle-tracker-card.js"

MANIFEST = (
    Path(__file__).resolve().parents[2]
    / "custom_components"
    / "cycle_tracker"
    / "manifest.json"
)


def _manifest_version() -> str:
    """Return the integration version straight from the manifest file."""
    return str(json.loads(MANIFEST.read_text(encoding="utf-8"))["version"])


class FakeResourceCollection:
    """In-memory stand-in for the Lovelace resources storage collection."""

    def __init__(self, items: list[dict[str, Any]] | None = None) -> None:
        self.items = items if items is not None else []
        self.created: list[dict[str, Any]] = []
        self.updated: list[tuple[str, dict[str, Any]]] = []
        self.deleted: list[str] = []

    async def async_load(self) -> None:
        """Load the stored items (already in memory)."""

    def async_items(self) -> list[dict[str, Any]]:
        """Return the stored items."""
        return self.items

    async def async_create_item(self, data: dict[str, Any]) -> None:
        """Create an item, mirroring the storage collection's id/type/url keys."""
        item = {
            "id": f"id-{len(self.items)}",
            "type": data["res_type"],
            "url": data["url"],
        }
        self.items.append(item)
        self.created.append(data)

    async def async_update_item(self, item_id: str, updates: dict[str, Any]) -> None:
        """Update an item's type and url in place."""
        for item in self.items:
            if item["id"] == item_id:
                item["type"] = updates["res_type"]
                item["url"] = updates["url"]
        self.updated.append((item_id, updates))

    async def async_delete_item(self, item_id: str) -> None:
        """Delete an item by id."""
        self.items = [item for item in self.items if item["id"] != item_id]
        self.deleted.append(item_id)


@pytest.fixture
def lovelace_storage(hass: HomeAssistant) -> FakeResourceCollection:
    """Install a fake storage-mode Lovelace resources collection."""
    fake = FakeResourceCollection()
    hass.data["lovelace"] = SimpleNamespace(mode="storage", resources=fake)
    return fake


class ExplodingResourceCollection(FakeResourceCollection):
    """A collection whose load fails, as a storage backend could."""

    async def async_load(self) -> None:
        """Fail the way a broken resources store would."""
        raise RuntimeError("resources store unavailable")


def _entry_data() -> dict[str, Any]:
    """Return setup data for an entry the integration can set up offline."""
    return {
        CONF_CYCLE_LENGTH: 28,
        CONF_PERIOD_LENGTH: 5,
        CONF_LAST_PERIOD_START: "2026-01-01",
        CONF_PREDICTION_ALGORITHM: "weighted_moving_average",
    }


async def test_lovelace_resource_is_upserted_once(
    hass: HomeAssistant,
    lovelace_storage: FakeResourceCollection,
) -> None:
    """Two upsert runs leave exactly one resource with the versioned URL."""
    await integration_module._async_upsert_lovelace_resource(hass)
    await integration_module._async_upsert_lovelace_resource(hass)

    assert len(lovelace_storage.items) == 1
    assert lovelace_storage.items[0]["url"] == f"{CARD_URL}?v={_manifest_version()}"
    assert len(lovelace_storage.created) == 1


async def test_lovelace_resource_is_wired_once_across_two_starts(
    hass: HomeAssistant,
    lovelace_storage: FakeResourceCollection,
) -> None:
    """The started event and the immediate run leave one resource, no duplicate."""
    integration_module._LOVELACE_WIRED = False
    integration_module._wire_lovelace_resource(hass)

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    assert len(lovelace_storage.items) == 1
    assert lovelace_storage.items[0]["url"] == f"{CARD_URL}?v={_manifest_version()}"


async def test_lovelace_resource_skips_yaml_mode(hass: HomeAssistant) -> None:
    """YAML-mode Lovelace is left untouched."""
    fake = FakeResourceCollection()
    hass.data["lovelace"] = SimpleNamespace(mode="yaml", resources=fake)

    await integration_module._async_upsert_lovelace_resource(hass)

    assert fake.items == []
    assert fake.created == []


async def test_upsert_reads_the_renamed_resource_mode(hass: HomeAssistant) -> None:
    """Home Assistant 2026.11 exposes the mode as ``resource_mode``."""
    fake = FakeResourceCollection()
    hass.data["lovelace"] = SimpleNamespace(resource_mode="storage", resources=fake)

    await integration_module._async_upsert_lovelace_resource(hass)

    assert len(fake.items) == 1


async def test_upsert_warns_instead_of_raising_when_the_collection_fails(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A broken collection is logged as a warning, not raised into the task."""
    hass.data["lovelace"] = SimpleNamespace(
        mode="storage", resources=ExplodingResourceCollection()
    )

    with caplog.at_level(logging.WARNING):
        await integration_module._async_upsert_lovelace_resource(hass)

    warnings = [
        record
        for record in caplog.records
        if record.levelno == logging.WARNING and "Lovelace resource" in record.message
    ]
    assert warnings, caplog.text
    assert warnings[0].exc_info is not None


async def test_setup_entry_upserts_the_lovelace_resource(
    hass: HomeAssistant,
    lovelace_storage: FakeResourceCollection,
) -> None:
    """Setting up an entry at runtime creates the card resource."""
    entry = MockConfigEntry(domain=DOMAIN, data=_entry_data())
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert [item["url"] for item in lovelace_storage.items] == [
        f"{CARD_URL}?v={_manifest_version()}"
    ]
    assert len(lovelace_storage.created) == 1


async def test_card_resource_url_uses_the_manifest_version(
    hass: HomeAssistant,
) -> None:
    """The served URL appends the manifest version as a cache-buster."""
    assert await integration_module._card_resource_url(hass) == (
        f"{CARD_URL}?v={_manifest_version()}"
    )


async def test_remove_entry_keeps_resource_while_another_entry_remains(
    hass: HomeAssistant,
    lovelace_storage: FakeResourceCollection,
) -> None:
    """Removing one of two entries keeps the shared resource."""
    await integration_module._async_upsert_lovelace_resource(hass)
    assert len(lovelace_storage.items) == 1

    first = MockConfigEntry(domain=DOMAIN)
    first.add_to_hass(hass)
    second = MockConfigEntry(domain=DOMAIN)
    second.add_to_hass(hass)

    await integration_module.async_remove_entry(hass, first)

    assert len(lovelace_storage.items) == 1
    assert lovelace_storage.deleted == []


async def test_remove_entry_deletes_resource_for_the_last_entry(
    hass: HomeAssistant,
    lovelace_storage: FakeResourceCollection,
) -> None:
    """Removing the last entry deletes the shared resource."""
    await integration_module._async_upsert_lovelace_resource(hass)
    assert len(lovelace_storage.items) == 1
    resource_id = lovelace_storage.items[0]["id"]

    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    await integration_module.async_remove_entry(hass, entry)

    assert lovelace_storage.items == []
    assert lovelace_storage.deleted == [resource_id]
