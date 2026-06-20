"""Tests for boss HP context bar rendering."""

from __future__ import annotations

import re

import pytest
from workflow_statusline import bar
from workflow_statusline.colours import CYAN, DIM, GREEN, MAGENTA, RED, RST, YELLOW

# Strip ANSI escape sequences for visible-length checks.
_ANSI_RE = re.compile(r"\033\[[0-9;]*m")

# Reset escape used to split filled from unfilled portions.
_RST_ESC = RST


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
        # Isolate the filled portion (before the first RST) to verify colour.
        first_rst = result.index(_RST_ESC)
        filled_portion = result[:first_rst]
        assert expected_colour in filled_portion, (
            f"pct={pct}: expected {expected_colour!r} in filled portion"
            f" {filled_portion!r}"
        )


# ---------------------------------------------------------------------------
# AC2.3 — 1M unfilled portion uses dimmed prior segment colour
# ---------------------------------------------------------------------------
class TestLargeContextUnfilledColour:
    def test_segment2_unfilled_is_dimmed_green(self) -> None:
        """At 30% (segment 2/CYAN), unfilled should be DIM + GREEN."""
        result = bar.boss_hp_bar(30, 1_000_000)
        # Unfilled portion starts after the first RST (end of filled block).
        first_rst = result.index(_RST_ESC)
        unfilled = result[first_rst + len(_RST_ESC) :]
        assert DIM in unfilled, f"DIM not found in unfilled portion: {unfilled!r}"
        assert GREEN in unfilled, f"GREEN not found in unfilled portion: {unfilled!r}"

    def test_segment1_unfilled_is_dimmed_green(self) -> None:
        """At 10% (segment 1), remainder is DIM + GREEN."""
        result = bar.boss_hp_bar(10, 1_000_000)
        # Unfilled portion starts after the first RST (end of filled block).
        first_rst = result.index(_RST_ESC)
        unfilled = result[first_rst + len(_RST_ESC) :]
        assert DIM in unfilled, f"DIM not found in unfilled portion: {unfilled!r}"
        assert GREEN in unfilled, f"GREEN not found in unfilled portion: {unfilled!r}"


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


# ---------------------------------------------------------------------------
# Integration test — boss HP bar via __main__ entry point
# ---------------------------------------------------------------------------
class TestMainEntryPointBarIntegration:
    def test_line2_starts_with_20_char_bar(self) -> None:
        """Pipe JSON with 1M context through main; line 2 should start with
        20-char bar."""
        import io
        import json
        import sys
        from unittest import mock

        payload = {
            "cwd": "/tmp/fake",
            "model": {"display_name": "opus"},
            "context_window": {
                "used_percentage": 40,
                "remaining_percentage": 60,
                "context_window_size": 1_000_000,
            },
            "cost": {"total_cost_usd": 1.23, "total_duration_ms": 60000},
        }

        from workflow_statusline.__main__ import main

        fake_stdin = io.StringIO(json.dumps(payload))
        buf = io.StringIO()
        from workflow_statusline.git import LocationInfo

        with (
            mock.patch.object(sys, "stdin", fake_stdin),
            mock.patch.object(sys, "stdout", buf),
            mock.patch(
                "workflow_statusline.__main__.git_location",
                return_value=LocationInfo(
                    display="/tmp/fake", is_on_main=False, is_worktree=False
                ),
            ),
            mock.patch("workflow_statusline.__main__.git_changes", return_value=(0, 0)),
        ):
            main()

        lines = buf.getvalue().splitlines()
        assert len(lines) == 2, f"Expected 2 lines, got {len(lines)}"
        line2 = lines[1]
        visible = _strip_ansi(line2)
        bar_chars = {"\u2588", "\u2592"}  # █ and ▒
        first_20 = visible[:20]
        assert len(first_20) == 20, f"line2 visible too short: {visible!r}"
        assert all(c in bar_chars for c in first_20), (
            f"First 20 visible chars should be bar chars, got: {first_20!r}"
        )
