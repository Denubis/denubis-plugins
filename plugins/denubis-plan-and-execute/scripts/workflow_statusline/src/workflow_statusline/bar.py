"""Boss HP bar — visual context window usage indicator."""

from __future__ import annotations

from workflow_statusline.colours import (
    CYAN,
    DIM,
    GREEN,
    MAGENTA,
    RED,
    RST,
    YELLOW,
)

BAR_WIDTH = 20
FILLED = "\u2588"  # █
UNFILLED = "\u2592"  # ▒

# 1M segment colours in order (each segment = 20% = 200k tokens).
_SEGMENT_COLOURS = [GREEN, CYAN, YELLOW, MAGENTA, RED]


def _segment_index(pct: int) -> int:
    """Return 0-based segment index for a percentage (clamped to 0-4)."""
    if pct >= 100:
        return 4
    return min(pct // 20, 4)


def _large_bar(used_pct: int) -> str:
    """Render the bar for >= 500k context windows (segment-aware)."""
    filled_count = round(used_pct / 100 * BAR_WIDTH)
    filled_count = max(0, min(BAR_WIDTH, filled_count))
    unfilled_count = BAR_WIDTH - filled_count

    seg = _segment_index(used_pct)
    fg = _SEGMENT_COLOURS[seg]

    # Prior segment colour for unfilled; segment 1 uses GREEN.
    prior = _SEGMENT_COLOURS[max(seg - 1, 0)]

    parts: list[str] = []
    if filled_count:
        parts.append(f"{fg}{FILLED * filled_count}{RST}")
    if unfilled_count:
        parts.append(f"{DIM}{prior}{UNFILLED * unfilled_count}{RST}")

    return "".join(parts)


def _small_bar(used_pct: int) -> str:
    """Render the bar for < 500k context windows (simple threshold)."""
    filled_count = round(used_pct / 100 * BAR_WIDTH)
    filled_count = max(0, min(BAR_WIDTH, filled_count))
    unfilled_count = BAR_WIDTH - filled_count

    if used_pct >= 90:
        colour = RED
    elif used_pct >= 70:
        colour = YELLOW
    else:
        colour = GREEN

    parts: list[str] = []
    if filled_count:
        parts.append(f"{colour}{FILLED * filled_count}{RST}")
    if unfilled_count:
        parts.append(f"{DIM}{colour}{UNFILLED * unfilled_count}{RST}")

    return "".join(parts)


def boss_hp_bar(used_pct: int, context_window_tokens: int) -> str:
    """Return a 20-char wide ANSI-coloured context usage bar.

    Parameters
    ----------
    used_pct:
        Percentage of context window used (0-100).
    context_window_tokens:
        Total context window size in tokens.

    """
    if context_window_tokens >= 500_000:
        return _large_bar(used_pct)
    return _small_bar(used_pct)
