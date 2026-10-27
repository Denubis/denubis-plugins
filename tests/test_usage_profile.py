"""The usage profile command: extraction, weekly hourly series and the backtest.

Expected values are worked by hand. Sydney's 2026 daylight-saving changes fall on
Sunday 2026-04-05 (03:00 AEDT back to 02:00 AEST) and Sunday 2026-10-04 (02:00 AEST
forward to 03:00 AEDT). The weekly window starts Friday 16:00 Sydney wall-clock time.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "usage_profile.py"
WINDOW_HOURS = 168


@pytest.fixture(scope="module")
def up() -> ModuleType:
    spec = importlib.util.spec_from_file_location("usage_profile", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Dataclasses resolve their module through sys.modules while it executes.
    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(sys.modules, spec.name, module)
        spec.loader.exec_module(module)
    return module


def _utc(*fields: int) -> datetime:
    return datetime(*fields, tzinfo=UTC)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
    )


def _assistant(
    message_id: str,
    *,
    timestamp: str,
    output: int,
    session: str = "s-main",
    sidechain: bool = False,
    tokens: tuple[int, int, int] = (3, 200, 5000),
    model: str = "claude-opus-4-7",
) -> dict:
    input_tokens, cache_creation, cache_read = tokens
    return {
        "type": "assistant",
        "sessionId": session,
        "cwd": "/work",
        "isSidechain": sidechain,
        "timestamp": timestamp,
        "message": {
            "id": message_id,
            "model": model,
            "usage": {
                "input_tokens": input_tokens,
                "cache_creation_input_tokens": cache_creation,
                "cache_read_input_tokens": cache_read,
                "output_tokens": output,
            },
        },
    }


# --- extract -----------------------------------------------------------------


def test_extract_writes_one_row_per_message_with_its_peak_usage_at_its_origin(
    tmp_path, up
):
    root = tmp_path / "projects"
    _write_jsonl(
        root / "-work" / "s-main.jsonl",
        [
            # A streamed message: the first record is partial, the second complete.
            _assistant("msg_A", timestamp="2026-10-01T10:00:00Z", output=1),
            _assistant(
                "msg_A",
                timestamp="2026-10-01T10:00:02Z",
                output=120,
                tokens=(4, 210, 9000),
            ),
        ],
    )
    _write_jsonl(
        root / "-work" / "s-main" / "subagents" / "agent-1.jsonl",
        [
            # The subagent replays msg_A earlier; msg_A stays a main message.
            _assistant(
                "msg_A",
                timestamp="2026-10-01T09:59:00Z",
                output=50,
                session="s-sub",
                sidechain=True,
            ),
            _assistant(
                "msg_B",
                timestamp="2026-10-01T09:30:00Z",
                output=7,
                session="s-sub",
                sidechain=True,
                tokens=(1, 2, 3),
                model="claude-sonnet-4-6",
            ),
        ],
    )
    out = tmp_path / "rows.tsv"

    status = up.main(["--projects-root", str(root), "extract", "--output", str(out)])

    assert status == 0
    with out.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh, delimiter="\t"))
    assert rows == [
        [
            "timestamp",
            "model",
            "input_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
            "output_tokens",
            "session_id",
        ],
        [
            "2026-10-01T09:30:00+00:00",
            "claude-sonnet-4-6",
            "1",
            "2",
            "3",
            "7",
            "s-sub",
        ],
        [
            "2026-10-01T10:00:00+00:00",
            "claude-opus-4-7",
            "4",
            "210",
            "9000",
            "120",
            "s-main",
        ],
    ]


# --- hourly series within a weekly window -------------------------------------


def _observation(up, when: datetime, units: float = 1.0):
    return up.Observation(when=when, model="m", session="s", context=0, units=units)


def test_hours_entering_daylight_saving_skip_the_missing_wall_clock_hour(up):
    # Window from Friday 2026-10-02 16:00 AEST (06:00Z). Sunday 01:30 AEST
    # (2026-10-03T15:30Z) is wall-clock hour 33; the next hour on the clock is
    # 03:00 AEDT, so Sunday 03:30 AEDT (16:30Z) is hour 35 and hour 34 never occurs.
    start = _utc(2026, 10, 2, 6, 0)
    observations = [
        _observation(up, _utc(2026, 10, 3, 15, 30), 2.0),
        _observation(up, _utc(2026, 10, 3, 16, 30), 3.0),
    ]

    windows = up.hourly_windows(observations)

    assert list(windows) == [start]
    assert windows[start][33:36] == [2.0, 0.0, 3.0]
    assert sum(windows[start]) == 5.0


def test_hours_leaving_daylight_saving_merge_the_repeated_wall_clock_hour(up):
    # Window from Friday 2026-04-03 16:00 AEDT (05:00Z). Sunday 02:30 occurs twice,
    # at 15:30Z (AEDT) and 16:30Z (AEST); both are wall-clock hour 34. Friday
    # 2026-04-10 15:30 AEST (05:30Z) is the last hour of the window, hour 167.
    start = _utc(2026, 4, 3, 5, 0)
    observations = [
        _observation(up, _utc(2026, 4, 4, 15, 30), 2.0),
        _observation(up, _utc(2026, 4, 4, 16, 30), 3.0),
        _observation(up, _utc(2026, 4, 10, 5, 30), 7.0),
    ]

    windows = up.hourly_windows(observations)

    assert list(windows) == [start]
    assert len(windows[start]) == WINDOW_HOURS
    assert windows[start][34] == 5.0
    assert windows[start][167] == 7.0
    assert sum(windows[start]) == 12.0


def test_friday_1559_and_1600_sydney_fall_in_consecutive_windows(up):
    # Friday 2026-10-16 15:59 AEDT is 04:59Z, the last hour of the window from
    # 2026-10-09 05:00Z; 16:00 AEDT (05:00Z) is hour 0 of the next window.
    windows = up.hourly_windows(
        [
            _observation(up, _utc(2026, 10, 16, 4, 59), 1.0),
            _observation(up, _utc(2026, 10, 16, 5, 0), 4.0),
        ]
    )

    assert windows[_utc(2026, 10, 9, 5, 0)][167] == 1.0
    assert windows[_utc(2026, 10, 16, 5, 0)][0] == 4.0


# --- selecting windows to evaluate ---------------------------------------------


def test_only_complete_windows_from_since_with_enough_units_are_evaluated(up):
    def week(units: float) -> list[float]:
        return [units / WINDOW_HOURS] * WINDOW_HOURS

    windows = {
        _utc(2026, 5, 29, 6, 0): week(100),  # starts before `since`
        _utc(2026, 6, 5, 6, 0): week(100),  # kept
        _utc(2026, 6, 12, 6, 0): week(10),  # too few units
        _utc(2026, 6, 19, 6, 0): week(100),  # still open when observed
    }

    selected = up.evaluable_starts(
        windows,
        since=_utc(2026, 6, 1, 0, 0),
        min_units=50,
        observed_until=_utc(2026, 6, 24, 0, 0),
    )

    assert selected == [_utc(2026, 6, 5, 6, 0)]


# --- the walk-forward backtest -------------------------------------------------
#
# Three prior windows use 1 unit every hour; the evaluated fourth uses 2. The
# median profile is 1 per hour. At h hours in, 2h units are used and 2(168 - h)
# remain, out of a total of 336.
#
# - Linear pace forecasts 2h / h * (168 - h) = 2(168 - h): error 0.
# - The raw profile forecasts 168 - h: error (168 - h) / 336.
# - The profile scaled by intensity with shrink s forecasts
#   (168 - h)(2h + s h) / (h + s h) = (168 - h)(2 + s) / (1 + s); with s = 1 that is
#   1.5(168 - h), so the error is 0.5(168 - h) / 336 = (168 - h) / 672.
# - Blending with weight w moves the forecast toward the exact linear one, which
#   scales that error by 1 - w.

SERIES = [[1.0] * WINDOW_HOURS] * 3 + [[2.0] * WINDOW_HOURS]
HORIZONS = range(12, WINDOW_HOURS, 12)


def test_linear_pace_is_exact_when_the_window_keeps_one_pace(up):
    errors = up.walk_forward(SERIES, up.linear)

    assert {h: errors[h] for h in HORIZONS} == {h: [0.0] for h in HORIZONS}


def test_raw_profile_error_is_the_unexpected_extra_usage(up):
    errors = up.walk_forward(SERIES, up.profile_raw)

    for h in HORIZONS:
        assert errors[h] == [pytest.approx((168 - h) / 336)]


def test_blend_from_168_returns_the_profile_only_errors(up):
    errors = up.walk_forward(SERIES, up.blended(shrink=1.0, blend_from=168))

    for h in HORIZONS:
        assert errors[h] == [pytest.approx((168 - h) / 672)]


def test_blend_from_72_moves_later_horizons_toward_the_linear_forecast(up):
    errors = up.walk_forward(SERIES, up.blended(shrink=1.0, blend_from=72))

    # w = 0 up to 72 hours; w = (h - 72) / 96 after.
    assert errors[48] == [pytest.approx(120 / 672)]
    assert errors[72] == [pytest.approx(96 / 672)]
    assert errors[120] == [pytest.approx(0.5 * 48 / 672)]
    assert errors[144] == [pytest.approx(0.25 * 24 / 672)]


def test_windows_with_fewer_than_three_prior_windows_are_not_evaluated(up):
    errors = up.walk_forward(SERIES[:3], up.linear)

    assert all(errors[h] == [] for h in HORIZONS)


# --- the command end to end ----------------------------------------------------


def test_profile_and_backtest_run_over_a_small_corpus(tmp_path, up, capsys):
    root = tmp_path / "projects"
    # Six weekly windows from 2026-06-05, each with one 100M-unit message
    # (20M output tokens at weight 5), so every window passes the 50M default.
    records = [
        _assistant(
            f"msg_{week}",
            timestamp=f"2026-06-{6 + 7 * week:02d}T02:00:00Z",
            output=20_000_000,
            tokens=(0, 0, 0),
        )
        for week in range(4)
    ] + [
        _assistant(
            f"msg_{4 + week}",
            timestamp=f"2026-07-{4 + 7 * week:02d}T02:00:00Z",
            output=20_000_000,
            tokens=(0, 0, 0),
        )
        for week in range(2)
    ]
    _write_jsonl(root / "-work" / "s-main.jsonl", records)

    assert up.main(["--projects-root", str(root), "profile"]) == 0
    assert up.main(["--projects-root", str(root), "backtest"]) == 0
    assert capsys.readouterr().out
