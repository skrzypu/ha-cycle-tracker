"""Copy contract for the fertility estimate (BDR-0004, variant A).

Only the keys added by this feature are checked for the copy ban: older copy in
the same files may legitimately contain one of the banned Polish words in an
unrelated context. The disclaimer itself is quoted verbatim from BDR-0004.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

COMPONENT_DIR = Path(__file__).parents[2] / "custom_components" / "cycle_tracker"
TRANSLATION_FILES = {
    "en": COMPONENT_DIR / "translations" / "en.json",
    "pl": COMPONENT_DIR / "translations" / "pl.json",
}

FERTILITY_STATE_KEYS = {
    "outside_estimated_fertile_window": "poza szacowanym oknem płodnym",
    "within_estimated_fertile_window": "w szacowanym oknie płodnym",
    "unknown": "brak danych",
}
DISCLAIMER = (
    "Oparty na długościach Twoich cykli szacunek kalendarzowy. "
    "Nie jest metodą antykoncepcyjną i nie gwarantuje płodności ani jej braku. "
    "Decyzję o współżyciu podejmij samodzielnie, nie opierając się wyłącznie "
    "na tym szacunku."
)
BANNED_WORDS = ("bezpieczny", "dni bezpieczne", "możesz", "ryzyko zajścia")


def _load(language: str) -> dict[str, Any]:
    with TRANSLATION_FILES[language].open(encoding="utf-8") as file:
        payload: dict[str, Any] = json.load(file)
    return payload


def _new_copy(payload: dict[str, Any]) -> dict[str, str]:
    """Return only the strings added for the fertility-estimate feature."""
    options = payload["options"]["step"]["init"]
    entity = payload["entity"]["sensor"]["fertility_estimate"]
    return {
        "options.label": options["data"]["enable_fertility_estimate"],
        "options.description": options["data_description"]["enable_fertility_estimate"],
        "entity.name": entity["name"],
        **{f"entity.state.{key}": value for key, value in entity["state"].items()},
    }


@pytest.mark.parametrize("language", sorted(TRANSLATION_FILES))
def test_translation_file_is_valid_json(language: str) -> None:
    assert isinstance(_load(language), dict)


@pytest.mark.parametrize("language", sorted(TRANSLATION_FILES))
def test_fertility_keys_exist_in_both_files(language: str) -> None:
    copy = _new_copy(_load(language))

    assert copy["options.label"].strip()
    assert copy["options.description"].strip()
    assert copy["entity.name"].strip()
    assert set(copy) == {
        "options.label",
        "options.description",
        "entity.name",
        *(f"entity.state.{key}" for key in FERTILITY_STATE_KEYS),
    }


def test_polish_state_labels_are_exact() -> None:
    states = _load("pl")["entity"]["sensor"]["fertility_estimate"]["state"]

    assert states == FERTILITY_STATE_KEYS


def test_bdr_disclaimer_is_present_verbatim() -> None:
    payload = _load("pl")
    description = payload["options"]["step"]["init"]["data_description"][
        "enable_fertility_estimate"
    ]

    assert description == DISCLAIMER


@pytest.mark.parametrize("language", sorted(TRANSLATION_FILES))
def test_new_copy_contains_no_banned_words(language: str) -> None:
    for path, text in _new_copy(_load(language)).items():
        lowered = text.casefold()
        for word in BANNED_WORDS:
            assert word not in lowered, f"{language}:{path} contains {word!r}"
