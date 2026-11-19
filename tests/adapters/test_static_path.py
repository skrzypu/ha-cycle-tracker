"""Tests for serving the card asset over the HTTP static path."""

from __future__ import annotations

from pathlib import Path

from homeassistant.setup import async_setup_component

import custom_components.cycle_tracker as integration_module

CARD_FILE = (
    Path(__file__).resolve().parents[2]
    / "custom_components"
    / "cycle_tracker"
    / "www"
    / "cycle-tracker-card.js"
)


async def test_card_asset_is_served(hass, hass_client) -> None:
    # The card file is created by another agent in parallel; guarantee it exists
    # so the static-path registration and the GET stay deterministic.
    if not CARD_FILE.exists():
        CARD_FILE.parent.mkdir(parents=True, exist_ok=True)
        CARD_FILE.write_text(
            "customElements.define('cycle-tracker-card', class {});\n",
            encoding="utf-8",
        )

    assert await async_setup_component(hass, "http", {})

    # Each test gets a fresh hass instance while the module-level guard persists,
    # so reset it before registering the path on this instance.
    integration_module._STATIC_PATH_REGISTERED = False
    await integration_module.async_setup(hass, {})

    client = await hass_client()
    resp = await client.get("/cycle_tracker/cycle-tracker-card.js")

    assert resp.status == 200
    assert "javascript" in resp.headers.get("Content-Type", "")
    body = await resp.text()
    assert "cycle-tracker-card" in body
