#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["denubis-agent-logs"]
#
# [tool.uv.sources.denubis-agent-logs]
# path = "../plugins/denubis-token-estimator/scripts/agent_logs"
# editable = true
# ///
"""Profile weekly Claude usage and backtest forecasts of what remains of a window.

A repository-only research tool, not a shipped command (ticket L5b's adopted
default). It replaces the 2026-10-09 probe scripts once kept in
`docs/usage-forecast-probe/` (ADR 0045); their findings are in
`docs/handover-usage-forecast-model.md`.

Claude Code transcripts, subagents included, are read once and read-only through
`denubis-agent-logs`. Each message counts once under the token-estimator's audited
rule: the maximum output per message id, at the message's origin time. (The probe kept
the first record per session and message id, which undercounts streamed output.)

Subcommands:
  extract   one TSV row per message: origin, model, four token counts, session
  profile   weekday-by-hour profile, model mix, concurrency, context size and the
            totals of recent weekly windows
  backtest  walk-forward error of linear and profile forecasts of the remainder of
            a weekly window

Cost units use the uncalibrated proxy `denubis_agent_logs.usage.UNCALIBRATED_WEIGHTS`.
Weekly windows start Friday 16:00 Australia/Sydney wall-clock time, the reset recorded
in section 0 of the handover; hours within a window are wall-clock hours.

Run it from anywhere with `uv run --script scripts/usage_profile.py <subcommand>`.
"""

from __future__ import annotations

import argparse
import collections
import csv
import statistics
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from denubis_agent_logs.claude import deduplicate, iter_usage_records, transcript_files
from denubis_agent_logs.records import ReadReport, summarise
from denubis_agent_logs.usage import cost_units
from denubis_agent_logs.windows import WeeklyAnchor, window_start

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from typing import TextIO

    from denubis_agent_logs.claude import ClaudeMessage

    type Forecast = Callable[[Sequence[float], float, int], float]

SYDNEY = ZoneInfo("Australia/Sydney")
WEEKLY_RESET = WeeklyAnchor(weekday=4, hour=16, zone=SYDNEY)
WINDOW_HOURS = 7 * 24
HORIZONS = tuple(range(12, WINDOW_HOURS, 12))
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MILLION = 1e6
TSV_COLUMNS = (
    "timestamp",
    "model",
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
    "session_id",
)
# The probe's evaluation choices: windows from June 2026 on, ignoring near-idle weeks.
DEFAULT_SINCE = datetime(2026, 6, 1, tzinfo=SYDNEY)
DEFAULT_MIN_UNITS = 50 * MILLION


@dataclass(frozen=True, slots=True)
class Observation:
    """One message as the profile and the backtest see it."""

    when: datetime  # origin, in Sydney time
    model: str
    session: str | None
    context: int  # input, cache-creation and cache-read tokens
    units: float


# --- reading ----------------------------------------------------------------------


def read_messages(
    root: Path | None, report: ReadReport
) -> tuple[list[tuple[datetime, ClaudeMessage]], int]:
    """Return each Claude message once, with its origin, in origin order.

    Also returns how many messages were left out because none of their records has
    a timestamp with an offset.
    """
    transcripts = transcript_files(root, include_subagents=True)
    messages = deduplicate(iter_usage_records(transcripts, report))
    dated = [
        (message.origin, message) for message in messages if message.origin is not None
    ]
    dated.sort(key=lambda pair: pair[0])
    return dated, len(messages) - len(dated)


def observations(dated: Sequence[tuple[datetime, ClaudeMessage]]) -> list[Observation]:
    return [
        Observation(
            when=origin.astimezone(SYDNEY),
            model=message.peak.model,
            session=message.peak.session_id,
            context=message.peak.input_tokens
            + message.peak.cache_creation_input_tokens
            + message.peak.cache_read_input_tokens,
            units=cost_units(message.peak),
        )
        for origin, message in dated
    ]


# --- extract ----------------------------------------------------------------------


def write_tsv(dated: Sequence[tuple[datetime, ClaudeMessage]], stream: TextIO) -> None:
    writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
    writer.writerow(TSV_COLUMNS)
    for origin, message in dated:
        peak = message.peak
        writer.writerow(
            [
                origin.isoformat(),
                peak.model,
                peak.input_tokens,
                peak.cache_creation_input_tokens,
                peak.cache_read_input_tokens,
                peak.output_tokens,
                peak.session_id or "",
            ]
        )


# --- profile ----------------------------------------------------------------------


def last_weeks(seen: Sequence[Observation], weeks: int) -> list[Observation]:
    """Return the observations within ``weeks`` of the latest one."""
    cut = seen[-1].when - timedelta(weeks=weeks)
    return [o for o in seen if o.when >= cut]


def weekday_hour_means(seen: Sequence[Observation]) -> dict[tuple[int, int], float]:
    """Mean units per (weekday, hour), over the dates of that weekday seen."""
    totals: dict[tuple[int, int], float] = collections.defaultdict(float)
    dates: dict[int, set] = collections.defaultdict(set)
    for o in seen:
        totals[o.when.weekday(), o.when.hour] += o.units
        dates[o.when.weekday()].add(o.when.date())
    return {
        (day, hour): totals[day, hour] / max(1, len(dates[day]))
        for day in range(7)
        for hour in range(24)
    }


def model_mix(seen: Sequence[Observation], top: int = 8) -> list[tuple[str, float]]:
    """The ``top`` models by units, largest first, with their share of all units."""
    units: dict[str, float] = collections.defaultdict(float)
    for o in seen:
        units[o.model] += o.units
    total = sum(units.values())
    ranked = sorted(units.items(), key=lambda item: item[1], reverse=True)[:top]
    return [(model, value / total if total else 0.0) for model, value in ranked]


def concurrency(seen: Sequence[Observation], cap: int = 6) -> dict[int, list[float]]:
    """Units per five-minute bin, keyed by distinct sessions in the bin (capped)."""
    sessions: dict[datetime, set] = collections.defaultdict(set)
    units: dict[datetime, float] = collections.defaultdict(float)
    for o in seen:
        start = o.when.replace(minute=o.when.minute // 5 * 5, second=0, microsecond=0)
        sessions[start].add(o.session)
        units[start] += o.units
    by_count: dict[int, list[float]] = collections.defaultdict(list)
    for start, active in sessions.items():
        by_count[min(len(active), cap)].append(units[start])
    return dict(sorted(by_count.items()))


def context_buckets(
    seen: Sequence[Observation], step: int = 25_000, last: int = 8
) -> dict[int, list[float]]:
    """Units per message, keyed by context size in steps of ``step`` tokens."""
    buckets: dict[int, list[float]] = collections.defaultdict(list)
    for o in seen:
        buckets[min(o.context // step, last)].append(o.units)
    return dict(sorted(buckets.items()))


def weekly_totals(seen: Sequence[Observation]) -> list[tuple[datetime, float, float]]:
    """(window start, units, Fable or Mythos units) for each weekly window."""
    total: dict[datetime, float] = collections.defaultdict(float)
    fable: dict[datetime, float] = collections.defaultdict(float)
    for o in seen:
        start = window_start(o.when, WEEKLY_RESET)
        total[start] += o.units
        if "fable" in o.model or "mythos" in o.model:
            fable[start] += o.units
    return [(start, total[start], fable[start]) for start in sorted(total)]


def print_profile(seen: Sequence[Observation], weeks: int = 12) -> None:
    if not seen:
        print("no dated messages")
        return
    print("range", seen[0].when.date(), seen[-1].when.date())
    recent = last_weeks(seen, weeks)
    _print_weekday_hours(recent, weeks)
    mix = model_mix(recent)
    print(
        f"\nmodel mix (weighted) last {weeks} weeks:",
        {model: f"{share:.0%}" for model, share in mix},
    )
    print(
        "\nbusy sessions in a 5-min bin -> median & mean units per bin (M), "
        "count of bins"
    )
    for count, values in concurrency(recent).items():
        print(
            count,
            round(statistics.median(values) / MILLION, 2),
            round(statistics.mean(values) / MILLION, 2),
            len(values),
        )
    print("\ncontext bucket (x25k tokens) -> mean units per message (k), n")
    for bucket, values in context_buckets(recent).items():
        print(bucket, round(statistics.mean(values) / 1e3, 1), len(values))
    _print_weekly_totals(seen)


def _print_weekday_hours(recent: Sequence[Observation], weeks: int) -> None:
    means = weekday_hour_means(recent)
    print(
        "\nweekday x hour, mean weighted-token-units per hour (millions), "
        f"last {weeks} weeks"
    )
    print("     " + " ".join(f"{hour:>4}" for hour in range(24)))
    for day, name in enumerate(WEEKDAYS):
        print(
            name,
            " ".join(f"{means[day, hour] / MILLION:4.1f}" for hour in range(24)),
        )
    print(
        "\nper-weekday mean daily units (M):",
        {
            name: round(sum(means[day, hour] for hour in range(24)) / MILLION, 1)
            for day, name in enumerate(WEEKDAYS)
        },
    )


def _print_weekly_totals(seen: Sequence[Observation], last: int = 10) -> None:
    print(
        f"\nweighted units per weekly window (Fri16:00 start), last {last}, M, "
        "and fable share"
    )
    for start, total, fable in weekly_totals(seen)[-last:]:
        print(
            start.date(),
            round(total / MILLION, 1),
            f"{fable / total:.0%}" if total else "",
        )


# --- backtest ---------------------------------------------------------------------


def hour_of_window(when: datetime, start: datetime) -> int:
    """Whole wall-clock hours from a window's start to ``when``, in the reset zone.

    Across a daylight-saving change the skipped hour never occurs and the repeated
    hour falls in one slot, so every window has the same 168 weekday-hour slots.
    """
    zone = WEEKLY_RESET.zone
    local = when.astimezone(zone).replace(tzinfo=None)
    elapsed = local - start.astimezone(zone).replace(tzinfo=None)
    return int(elapsed.total_seconds() // 3600)


def hourly_windows(seen: Sequence[Observation]) -> dict[datetime, list[float]]:
    """Units per wall-clock hour of each weekly window, keyed by window start."""
    windows: dict[datetime, list[float]] = {}
    for o in seen:
        start = window_start(o.when, WEEKLY_RESET)
        series = windows.setdefault(start, [0.0] * WINDOW_HOURS)
        series[hour_of_window(o.when, start)] += o.units
    return windows


def evaluable_starts(
    windows: Mapping[datetime, Sequence[float]],
    *,
    since: datetime,
    min_units: float,
    observed_until: datetime,
) -> list[datetime]:
    """Starts, in order, of complete windows from ``since`` above ``min_units``.

    A window is complete when its end, the next reset, is no later than
    ``observed_until``; a window still open has no final total to forecast.
    """
    return [
        start
        for start in sorted(windows)
        if start >= since
        and _window_end(start) <= observed_until
        and sum(windows[start]) > min_units
    ]


def _window_end(start: datetime) -> datetime:
    # Adding days to a zoned datetime moves its wall clock, so this is the next
    # reset even across a daylight-saving change.
    return start.astimezone(WEEKLY_RESET.zone) + timedelta(days=7)


def walk_forward(
    series: Sequence[Sequence[float]],
    forecast: Forecast,
    *,
    history: int = 8,
    minimum: int = 3,
) -> dict[int, list[float]]:
    """Forecast error at each horizon for each window with enough prior windows.

    The profile is the median, hour by hour, of up to ``history`` prior windows.
    The error is the absolute difference between the forecast and the actual
    remainder, as a share of the window's total.
    """
    errors: dict[int, list[float]] = {hour: [] for hour in HORIZONS}
    for index, window in enumerate(series):
        prior = series[max(0, index - history) : index]
        if len(prior) < minimum:
            continue
        profile = [
            statistics.median(p[hour] for p in prior) for hour in range(WINDOW_HOURS)
        ]
        total = sum(window)
        for hour in HORIZONS:
            used = sum(window[:hour])
            remaining = forecast(profile, used, hour)
            errors[hour].append(abs(remaining - (total - used)) / max(total, 1))
    return errors


def linear(_profile: Sequence[float], used: float, hour: int) -> float:
    """The remainder at the pace so far."""
    return used / hour * (WINDOW_HOURS - hour)


def profile_raw(profile: Sequence[float], _used: float, hour: int) -> float:
    """The remainder the profile expects."""
    return sum(profile[hour:])


def scaled_profile(shrink: float) -> Forecast:
    """The profile's remainder scaled by this window's intensity so far.

    The intensity ratio is shrunk toward 1 by ``shrink`` times the expected usage.
    """

    def forecast(profile: Sequence[float], used: float, hour: int) -> float:
        so_far = sum(profile[:hour])
        ratio = (
            (used + shrink * so_far) / (so_far + shrink * so_far) if so_far > 0 else 1.0
        )
        return sum(profile[hour:]) * ratio

    return forecast


def blended(shrink: float, blend_from: int) -> Forecast:
    """The scaled profile, moving linearly toward linear pace after ``blend_from``."""
    scaled = scaled_profile(shrink)

    def forecast(profile: Sequence[float], used: float, hour: int) -> float:
        weight = blend_weight(hour, blend_from)
        return (1 - weight) * scaled(profile, used, hour) + weight * linear(
            profile, used, hour
        )

    return forecast


def blend_weight(hour: int, blend_from: int) -> float:
    """The linear forecast's share at ``hour``: 0 until ``blend_from``, 1 at the end.

    Blending from the end of the window or later never blends, so the weight stays
    0 and that sweep row is the profile-only baseline.
    """
    if blend_from >= WINDOW_HOURS:
        return 0.0
    return min(1.0, max(0.0, (hour - blend_from) / (WINDOW_HOURS - blend_from)))


def print_backtest(
    seen: Sequence[Observation],
    *,
    since: datetime,
    min_units: float,
    observed_until: datetime,
) -> None:
    windows = hourly_windows(seen)
    starts = evaluable_starts(
        windows, since=since, min_units=min_units, observed_until=observed_until
    )
    evaluated = max(0, len(starts) - 3)
    if not evaluated:
        print(f"windows selected: {len(starts)}; at least 4 are needed to evaluate one")
        return
    print(
        f"windows selected: {len(starts)} ({starts[0].date()} to {starts[-1].date()}); "
        f"evaluated: {evaluated}"
    )
    series = [windows[start] for start in starts]
    shown = [hour for hour in HORIZONS if hour % 24 == 0 or hour == 12]
    for name, forecast in (
        ("linear", linear),
        ("profile_raw", profile_raw),
        ("profile", scaled_profile(0.2)),
    ):
        errors = walk_forward(series, forecast)
        print(
            f"\n{name}: mean abs error of remaining-forecast as % of window total,"
            " by hours into window"
        )
        print(
            "  "
            + "  ".join(
                f"{hour:>3}h:{statistics.mean(errors[hour]) * 100:4.0f}%"
                for hour in shown
            )
        )
    print("\nshrink / blend_from -> error at 24h,48h,96h,144h")
    for shrink in (1.0, 3.0, 10.0, 1e9):
        for blend_from in (72, 120, 168):
            errors = walk_forward(series, blended(shrink, blend_from))
            print(
                f"  shrink={shrink:<6} blend_from={blend_from:<4}",
                "  ".join(
                    f"{hour}h:{statistics.mean(errors[hour]) * 100:3.0f}%"
                    for hour in (24, 48, 96, 144)
                ),
            )


# --- command line -----------------------------------------------------------------


def _sydney_date(value: str) -> datetime:
    day = datetime.strptime(value, "%Y-%m-%d").date()
    return datetime(day.year, day.month, day.day, tzinfo=SYDNEY)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Profile weekly Claude usage and backtest remainder forecasts."
    )
    parser.add_argument(
        "--projects-root",
        type=Path,
        help="Claude projects directory "
        "(default: $CLAUDE_CONFIG_DIR/projects, else ~/.claude/projects)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    extract = commands.add_parser("extract", help="write one TSV row per message")
    extract.add_argument("--output", type=Path, help="TSV file (default: stdout)")
    commands.add_parser("profile", help="print the usage profile")
    backtest = commands.add_parser("backtest", help="backtest remainder forecasts")
    backtest.add_argument(
        "--since",
        type=_sydney_date,
        default=DEFAULT_SINCE,
        help="first window start to evaluate, a Sydney date (default: 2026-06-01)",
    )
    backtest.add_argument(
        "--min-units",
        type=float,
        default=DEFAULT_MIN_UNITS,
        help="skip windows with fewer cost units (default: 50e6)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = ReadReport()
    dated, undated = read_messages(args.projects_root, report)
    sys.stderr.write(summarise("Claude", report))
    sys.stderr.write(
        f"{len(dated):,} messages, each counted once at its maximum output; "
        f"{undated:,} without a timestamp left out\n"
    )
    if args.command == "extract":
        if args.output is None:
            write_tsv(dated, sys.stdout)
        else:
            with args.output.open("w", encoding="utf-8", newline="") as stream:
                write_tsv(dated, stream)
    elif args.command == "profile":
        print_profile(observations(dated))
    else:
        print_backtest(
            observations(dated),
            since=args.since,
            min_units=args.min_units,
            observed_until=datetime.now(UTC),
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
