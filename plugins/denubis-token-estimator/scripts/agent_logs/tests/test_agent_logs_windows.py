"""Weekly windows start at a fixed local weekday and hour, across daylight saving.

Brian reported the weekly quota reset as Friday 16:00 Australia/Sydney, observed as
`resets_at` 2026-10-09T05:00Z (docs/handover-usage-forecast-model.md section 0).
Sydney left daylight saving at 03:00 on Sunday 2026-04-05 (UTC+11 to UTC+10) and
entered it at 02:00 on Sunday 2026-10-04 (UTC+10 to UTC+11). Every expected instant
below was converted to UTC by hand from those offsets.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from denubis_agent_logs.windows import WeeklyAnchor, window_start

FRIDAY_1600_SYDNEY = WeeklyAnchor(weekday=4, hour=16, zone=ZoneInfo("Australia/Sydney"))


def _utc(*fields: int) -> datetime:
    return datetime(*fields, tzinfo=UTC)


def test_friday_1559_sydney_belongs_to_the_previous_window():
    # Friday 2026-10-16 15:59 AEDT (UTC+11) is 04:59Z; the window began a week
    # earlier, Friday 2026-10-09 16:00 AEDT, which is 05:00Z.
    assert window_start(_utc(2026, 10, 16, 4, 59), FRIDAY_1600_SYDNEY) == _utc(
        2026, 10, 9, 5, 0
    )


def test_friday_1600_sydney_starts_a_new_window():
    assert window_start(_utc(2026, 10, 16, 5, 0), FRIDAY_1600_SYDNEY) == _utc(
        2026, 10, 16, 5, 0
    )


def test_the_window_start_is_expressed_in_the_anchor_zone():
    start = window_start(_utc(2026, 10, 16, 5, 0), FRIDAY_1600_SYDNEY)

    assert (start.weekday(), start.hour, start.minute) == (4, 16, 0)
    assert start.utcoffset() == timedelta(hours=11)


def test_week_entering_daylight_saving_runs_from_1600_aest_to_1600_aedt():
    # Window from Friday 2026-10-02 16:00 AEST (06:00Z) to Friday 2026-10-09
    # 16:00 AEDT (05:00Z): 167 elapsed hours.
    start = _utc(2026, 10, 2, 6, 0)
    next_start = _utc(2026, 10, 9, 5, 0)
    inside = [
        start,
        _utc(2026, 10, 3, 15, 59),  # Sunday 01:59 AEST, just before the change
        _utc(2026, 10, 3, 16, 0),  # Sunday 03:00 AEDT, just after it
        _utc(2026, 10, 9, 4, 59),  # Friday 15:59 AEDT
    ]

    assert [window_start(t, FRIDAY_1600_SYDNEY) for t in inside] == [start] * 4
    assert window_start(next_start, FRIDAY_1600_SYDNEY) == next_start
    assert next_start - start == timedelta(hours=167)


def test_week_leaving_daylight_saving_runs_from_1600_aedt_to_1600_aest():
    # Window from Friday 2026-04-03 16:00 AEDT (05:00Z) to Friday 2026-04-10
    # 16:00 AEST (06:00Z): 169 elapsed hours.
    start = _utc(2026, 4, 3, 5, 0)
    next_start = _utc(2026, 4, 10, 6, 0)
    inside = [
        start,
        _utc(2026, 4, 4, 15, 30),  # Sunday 02:30 AEDT, the first 02:30
        _utc(2026, 4, 4, 16, 30),  # Sunday 02:30 AEST, the repeated 02:30
        _utc(2026, 4, 10, 5, 59),  # Friday 15:59 AEST
    ]

    assert [window_start(t, FRIDAY_1600_SYDNEY) for t in inside] == [start] * 4
    assert window_start(next_start, FRIDAY_1600_SYDNEY) == next_start
    assert next_start - start == timedelta(hours=169)
