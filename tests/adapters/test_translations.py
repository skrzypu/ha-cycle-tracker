"""Key parity across the integration translation files.

Home Assistant tolerates missing translation keys by falling back to English,
but a key that exists in one file and not another is almost always a typo or an
untranslated addition. This test keeps ``strings.json``, ``translations/en.json``
and ``translations/pl.json`` structurally in lockstep without importing Home
Assistant or the integration.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

COMPONENT_DIR = Path(__file__).parents[2] / "custom_components" / "cycle_tracker"

TRANSLATION_FILES = {
    "strings.json": COMPONENT_DIR / "strings.json",
    "translations/en.json": COMPONENT_DIR / "translations" / "en.json",
    "translations/pl.json": COMPONENT_DIR / "translations" / "pl.json",
}

HISTORY_WINDOW_KEY = "history_window"


def _nested_keys(value: Any, prefix: str = "") -> set[str]:
    """Return every nested key path, recursing through JSON objects only."""
    keys: set[str] = set()
    if not isinstance(value, dict):
        return keys
    for key, child in value.items():
        path = f"{prefix}.{key}" if prefix else key
        keys.add(path)
        keys.update(_nested_keys(child, path))
    return keys


def _load(path: Path) -> Any:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def test_translation_files_expose_identical_keys() -> None:
    """All three translation files must define exactly the same keys."""
    key_sets = {
        name: _nested_keys(_load(path)) for name, path in TRANSLATION_FILES.items()
    }

    baseline = key_sets["strings.json"]
    assert baseline, "strings.json must define at least one key"

    for name, keys in key_sets.items():
        missing = sorted(baseline - keys)
        extra = sorted(keys - baseline)
        assert not missing, f"{name} is missing keys from strings.json: {missing}"
        assert not extra, f"{name} adds keys not present in strings.json: {extra}"


def test_history_window_is_labelled_in_both_forms() -> None:
    """The same key carries a non-empty label in each file, in both forms."""
    for name, path in TRANSLATION_FILES.items():
        payload = _load(path)
        for section, step in (("config", "preferences"), ("options", "init")):
            data = payload[section]["step"][step]["data"]
            assert HISTORY_WINDOW_KEY in data, f"{name} missing {section}.{step}"
            assert str(data[HISTORY_WINDOW_KEY]).strip(), f"{name} has empty label"
