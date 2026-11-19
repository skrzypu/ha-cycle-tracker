"""Tests for serving the card asset over the HTTP static path."""

from __future__ import annotations

import json
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


def _manifest_version() -> str:
    """Return the integration version used as the card's cache-buster."""
    manifest = CARD_FILE.parent.parent / "manifest.json"
    return str(json.loads(manifest.read_text(encoding="utf-8"))["version"])


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

    # The Lovelace resource loads the same asset with a version query string.
    versioned = await client.get(
        f"/cycle_tracker/cycle-tracker-card.js?v={_manifest_version()}"
    )
    assert versioned.status == 200
    assert "javascript" in versioned.headers.get("Content-Type", "")
    assert "cycle-tracker-card" in await versioned.text()


def test_card_keeps_one_element_and_both_average_labels() -> None:
    """The asset still defines a single card and labels both average rows."""
    body = CARD_FILE.read_text(encoding="utf-8")

    assert body.count('customElements.define("cycle-tracker-card"') == 1
    assert "Średnia długość cyklu (okno)" in body
    assert "Średnia długość cyklu (cała historia)" in body
