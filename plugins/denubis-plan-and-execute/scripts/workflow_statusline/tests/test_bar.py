"""Tests for boss HP context bar rendering."""

from __future__ import annotations

import re

import pytest

from workflow_statusline import bar
from workflow_statusline.colours import CYAN, DIM, GREEN, MAGENTA, RED, YELLOW

# Strip ANSI escape sequences for visible-length checks.
_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


# ---------------------------------------------------------------------------
# AC2.1 — visible length is always 20
# ---------------------------------------------------------------------------
class TestBarVisibleLength:
    @pytest.mark.parametrize(
        "pct, ctx",
        [
            (0, 1_000_000),
            (10, 1_000_000),
            (50, 1_000_000),
            (99, 1_000_000),
            (100, 1_000_000),
            (0, 200_000),
            (50, 200_000),
            (100, 200_000),
        ],
    )
    def test_visible_length_is_20(self, pct: int, ctx: int) -> None:
        result = bar.boss_hp_bar(pct, ctx)
        visible = _strip_ansi(result)
        assert len(visible) == 20, f"pct={pct}, ctx={ctx}: got len {len(visible)}"


# ---------------------------------------------------------------------------
# AC2.2 — 1M context segment colours
# ---------------------------------------------------------------------------
class TestLargeContextSegmentColours:
    @pytest.mark.parametrize(
        "pct, expected_colour",
        [
            (10, GREEN),
            (30, CYAN),
            (50, YELLOW),
            (70, MAGENTA),
            (90, RED),
        ],
    )
    def test_filled_colour(self, pct: int, expected_colour: str) -> None:
        result = bar.boss_hp_bar(pct, 1_000_000)
        # The filled portion must contain the expected colour escape.
        assert expected_colour in result, (
            f"pct={pct}: expected {expected_colour!r} in bar"
        )


# ---------------------------------------------------------------------------
# AC2.3 — 1M unfilled portion uses dimmed prior segment colour
# ---------------------------------------------------------------------------
class TestLargeContextUnfilledColour:
    def test_segment2_unfilled_is_dimmed_green(self) -> None:
        """At 30% (segment 2/CYAN), unfilled should be DIM + GREEN."""
        result = bar.boss_hp_bar(30, 1_000_000)
        assert DIM in result
        # The unfilled section should reference GREEN (prior segment).
        # Find the unfilled portion: after the filled CYAN block.
        unfilled_start = result.rfind(DIM)
        unfilled = result[unfilled_start:]
        assert GREEN in unfilled

    def test_segment1_unfilled_is_dimmed_green(self) -> None:
        """At 10% (segment 1), remainder is DIM + GREEN."""
        result = bar.boss_hp_bar(10, 1_000_000)
        assert DIM in result
        unfilled_start = result.rfind(DIM)
        unfilled = result[unfilled_start:]
        assert GREEN in unfilled


# ---------------------------------------------------------------------------
# AC2.4 — 200k context simple colour thresholds
# ---------------------------------------------------------------------------
class TestSmallContextColours:
    def test_green_at_50(self) -> None:
        result = bar.boss_hp_bar(50, 200_000)
        assert GREEN in result

    def test_yellow_at_75(self) -> None:
        result = bar.boss_hp_bar(75, 200_000)
        assert YELLOW in result

    def test_red_at_95(self) -> None:
        result = bar.boss_hp_bar(95, 200_000)
        assert RED in result
