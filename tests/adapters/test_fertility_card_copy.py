"""Static card-copy contract for the two fertility gap edges.

The card is a plain JS asset, so the three scenarios of the delta spec that
needed coverage are checked against its source text. The banned-word assertion
is limited to the fertility block (``FERTILITY_TEXT``, its formatter and
``_renderFertility``) so unrelated, older card copy cannot make it brittle.
"""

from __future__ import annotations

from pathlib import Path

import pytest

CARD_FILE = (
    Path(__file__).resolve().parents[2]
    / "custom_components"
    / "cycle_tracker"
    / "www"
    / "cycle-tracker-card.js"
)

PREVIOUS_LABEL = "poprzedni pas szacunku"
NEXT_LABEL = "następny pas szacunku"
DISCLAIMER = (
    "Oparty na długościach Twoich cykli szacunek kalendarzowy. "
    "Nie jest metodą antykoncepcyjną i nie gwarantuje płodności ani jej braku. "
    "Decyzję o współżyciu podejmij samodzielnie, nie opierając się wyłącznie "
    "na tym szacunku."
)
BANNED_WORDS = ("bezpieczny", "dni bezpieczne", "możesz", "ryzyko zajścia")

TEXT_START = "const FERTILITY_TEXT = Object.freeze({"
FORMAT_START = "function _formatFertilityBand"
STYLES_START = "const CARD_STYLES"
RENDER_START = "  _renderFertility() {"
RENDER_END = 'if (!customElements.get("cycle-tracker-card"))'


def _body() -> str:
    return CARD_FILE.read_text(encoding="utf-8")


def _block(body: str, start: str, end: str) -> str:
    """Return the source between two markers, failing loudly if either is gone."""
    assert start in body, f"missing card marker {start!r}"
    from_index = body.index(start)
    assert end in body[from_index:], f"missing card marker {end!r}"
    return body[from_index : body.index(end, from_index)]


def _text_block(body: str) -> str:
    return _block(body, TEXT_START, FORMAT_START)


def _format_block(body: str) -> str:
    return _block(body, FORMAT_START, STYLES_START)


def _render_block(body: str) -> str:
    return _block(body, RENDER_START, RENDER_END)


# --- two labelled edges --------------------------------------------------------


def test_both_factual_labels_live_in_fertility_text() -> None:
    text = _text_block(_body())

    assert f'previousBandLabel: "{PREVIOUS_LABEL}"' in text
    assert f'nextBandLabel: "{NEXT_LABEL}"' in text


def test_render_fertility_reads_and_labels_both_gap_attributes() -> None:
    render = _render_block(_body())

    assert "attrs.previous_margin_band" in render
    assert "attrs.next_margin_band" in render
    assert 'key: "previous_margin_band"' in render
    assert 'key: "next_margin_band"' in render
    assert "FERTILITY_TEXT.previousBandLabel" in render
    assert "FERTILITY_TEXT.nextBandLabel" in render
    # The edges are only built in the outside state and each becomes a line.
    assert "const gapEdges = isOutside" in render
    assert "for (const edge of gapEdges)" in render
    assert 'edgeEl.setAttribute("data-field", edge.key)' in render
    assert "edge.label" in render


# --- one labelled edge ---------------------------------------------------------


def test_missing_or_invalid_edge_creates_no_line() -> None:
    body = _body()
    formatter = _format_block(body)
    render = _render_block(body)

    # The formatter rejects null (and any malformed band) instead of rendering
    # an empty row, and the render loop skips whatever the formatter rejected.
    assert "Array.isArray(band)" in formatter
    assert "band.length !== 2" in formatter
    assert 'typeof band[0] !== "string"' in formatter
    assert 'typeof band[1] !== "string"' in formatter
    assert "return null;" in formatter
    assert "if (!formatted)" in render
    assert "continue;" in render


# --- disclaimer and copy ban ---------------------------------------------------


def test_bdr_disclaimer_is_present_verbatim_and_rendered() -> None:
    body = _body()

    assert DISCLAIMER in _text_block(body)
    assert "disclaimer.textContent = FERTILITY_TEXT.disclaimer;" in _render_block(body)


@pytest.mark.parametrize("word", BANNED_WORDS)
def test_new_fertility_copy_contains_no_banned_word(word: str) -> None:
    body = _body()
    new_copy = _text_block(body) + _format_block(body) + _render_block(body)

    assert word not in new_copy.casefold(), f"fertility card copy contains {word!r}"
