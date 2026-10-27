"""Weekly quota windows anchored at a local weekday and hour.

A weekly window starts at the anchor's weekday and hour on the wall clock of the
anchor's time zone, so a window that spans a daylight-saving change lasts one hour
more or less than seven days of elapsed time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class WeeklyAnchor:
    """The local wall-clock instant each weekly window starts at.

    ``weekday`` counts from Monday as 0, as :meth:`datetime.weekday` does; ``hour``
    is the hour of that day in ``zone``.
    """

    weekday: int
    hour: int
    zone: ZoneInfo


def window_start(when: datetime, anchor: WeeklyAnchor) -> datetime:
    """Return the start of the weekly window holding the aware datetime ``when``.

    The start is the latest anchor instant at or before ``when``, expressed in the
    anchor's zone.
    """
    local = when.astimezone(anchor.zone).replace(tzinfo=None)
    shifted = local - timedelta(hours=anchor.hour)
    days_back = (shifted.weekday() - anchor.weekday) % 7
    day = (shifted - timedelta(days=days_back)).date()
    return datetime(day.year, day.month, day.day, anchor.hour, tzinfo=anchor.zone)
