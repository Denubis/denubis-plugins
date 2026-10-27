"""Log timestamps parse to aware datetimes, and anything else parses to None."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from denubis_agent_logs.timestamps import parse_timestamp


def test_zulu_timestamp_parses_to_that_utc_instant():
    parsed = parse_timestamp("2026-10-27T03:16:00.123Z")

    assert parsed == datetime(2026, 10, 27, 3, 16, 0, 123000, tzinfo=UTC)
    assert parsed is not None
    assert parsed.tzinfo is not None


def test_offset_timestamp_parses_to_the_same_instant_in_utc():
    assert parse_timestamp("2026-10-27T14:16:00+11:00") == datetime(
        2026, 10, 27, 3, 16, tzinfo=UTC
    )


@pytest.mark.parametrize(
    "value",
    [
        "2026-10-27T03:16:00",  # no offset: the instant is unknown
        "2026-10-27",  # a date alone has no offset either
        "yesterday",
        "",
        None,
        1_761_534_960,
        b"2026-10-27T03:16:00Z",
    ],
)
def test_values_that_are_not_offset_timestamps_parse_to_none(value):
    assert parse_timestamp(value) is None
