from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from workflow_statusline import codex_quota


def _rate_event(
    *, primary: dict | None, secondary: dict | None, limit_id: str | None = None
) -> str:
    return json.dumps(
        {
            "timestamp": "2026-08-11T08:00:00Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "rate_limits": {
                    "limit_id": limit_id,
                    "primary": primary,
                    "secondary": secondary,
                },
            },
        }
    )


class CodexQuotaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_timezone = os.environ.get("TZ")
        os.environ["TZ"] = "Australia/Sydney"
        time.tzset()

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.original_timezone is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = cls.original_timezone
        time.tzset()

    def test_selects_the_seven_day_window_when_it_is_primary(self) -> None:
        quota = codex_quota
        event = json.loads(
            _rate_event(
                primary={
                    "used_percent": 14.0,
                    "window_minutes": 10_080,
                    "resets_at": 1_787_011_993,
                },
                secondary=None,
            )
        )

        self.assertEqual(
            quota.quota_from_event(event),
            (14.0, 10_080, 1_787_011_993),
        )

    def test_selects_the_seven_day_window_when_it_is_secondary(self) -> None:
        quota = codex_quota
        event = json.loads(
            _rate_event(
                primary={
                    "used_percent": 40.0,
                    "window_minutes": 300,
                    "resets_at": 1_786_000_000,
                },
                secondary={
                    "used_percent": 15.0,
                    "window_minutes": 10_080,
                    "resets_at": 1_787_011_993,
                },
            )
        )

        self.assertEqual(
            quota.quota_from_event(event),
            (15.0, 10_080, 1_787_011_993),
        )

    def test_reads_main_quota_before_newer_spark_event(self) -> None:
        quota = codex_quota
        main = _rate_event(
            primary={
                "used_percent": 24.0,
                "window_minutes": 10_080,
                "resets_at": 1_789_860_845,
            },
            secondary=None,
            limit_id="codex",
        )
        spark = _rate_event(
            primary={
                "used_percent": 0.0,
                "window_minutes": 300,
                "resets_at": 1_789_447_457,
            },
            secondary={
                "used_percent": 0.0,
                "window_minutes": 10_080,
                "resets_at": 1_790_034_257,
            },
            limit_id="codex_bengalfox",
        )
        with tempfile.TemporaryDirectory() as directory:
            rollout = Path(directory) / "rollout.jsonl"
            rollout.write_text(main + "\n" + spark + "\n")
            self.assertEqual(
                quota.quota_from_rollout(rollout), (24.0, 10_080, 1_789_860_845)
            )

    def test_only_main_and_legacy_buckets_are_accepted(self) -> None:
        quota = codex_quota
        for limit_id in ("codex", None, "codex_bengalfox", "another_pool"):
            with self.subTest(limit_id=limit_id):
                event = json.loads(
                    _rate_event(
                        primary={
                            "used_percent": 24.0,
                            "window_minutes": 10_080,
                            "resets_at": 1_789_860_845,
                        },
                        secondary=None,
                        limit_id=limit_id,
                    )
                )
                expected = (
                    (24.0, 10_080, 1_789_860_845)
                    if limit_id in ("codex", None)
                    else None
                )
                self.assertEqual(quota.quota_from_event(event), expected)
        del event["payload"]["rate_limits"]["limit_id"]
        self.assertEqual(quota.quota_from_event(event), (24.0, 10_080, 1_789_860_845))

    def test_pace_uses_the_same_active_hours_as_claude(self) -> None:
        quota = codex_quota
        start = time.mktime((2026, 8, 11, 7, 0, 0, 0, 0, -1))
        reset = start + 7 * 86_400

        at_8am = quota.pace_percent(
            now=start + 3_600,
            resets_at=reset,
            window_minutes=10_080,
        )
        at_10pm = quota.pace_percent(
            now=start + 15 * 3_600,
            resets_at=reset,
            window_minutes=10_080,
        )
        next_7am = quota.pace_percent(
            now=start + 24 * 3_600,
            resets_at=reset,
            window_minutes=10_080,
        )

        self.assertAlmostEqual(at_8am, 100 / 105)
        self.assertEqual(next_7am, at_10pm)

    def test_renders_usage_over_pace_in_red(self) -> None:
        quota = codex_quota
        reset = time.mktime((2026, 8, 18, 10, 13, 0, 0, 0, -1))

        self.assertEqual(
            quota.render_quota(14.0, 7.0, reset, now=reset - 2 * 86_400),
            "#[fg=red]14 7 Tue#[default]",
        )

    def test_renders_usage_under_pace_in_green(self) -> None:
        quota = codex_quota
        reset = time.mktime((2026, 8, 18, 10, 13, 0, 0, 0, -1))

        self.assertEqual(
            quota.render_quota(6.0, 7.0, reset, now=reset - 2 * 86_400),
            "#[fg=green]6 7 Tue#[default]",
        )

    def test_reset_switches_from_weekday_to_local_time_at_24_hours(self) -> None:
        quota = codex_quota
        reset = time.mktime((2026, 9, 17, 14, 30, 0, 0, 0, -1))
        for remaining, label in ((86_401, "Thu"), (86_400, "14:30"), (3_600, "14:30")):
            with self.subTest(remaining=remaining):
                self.assertEqual(
                    quota.status_text(
                        Path("/not/read"),
                        now=reset - remaining,
                        snapshot=(10.0, 10_080, int(reset)),
                    ).split()[-1],
                    label + "#[default]",
                )

    def test_reads_the_latest_local_rollout(self) -> None:
        quota = codex_quota
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory) / ".codex"
            sessions = codex_home / "sessions"
            sessions.mkdir(parents=True)
            older = sessions / "older.jsonl"
            newest = sessions / "newest.jsonl"
            older.write_text(
                _rate_event(
                    primary={
                        "used_percent": 3.0,
                        "window_minutes": 10_080,
                        "resets_at": 1_787_011_993,
                    },
                    secondary=None,
                )
                + "\n"
            )
            newest.write_text(
                _rate_event(
                    primary={
                        "used_percent": 14.0,
                        "window_minutes": 10_080,
                        "resets_at": 1_787_011_993,
                    },
                    secondary=None,
                )
                + "\n{partially-written"
            )

            database = sqlite3.connect(codex_home / "state_5.sqlite")
            database.execute(
                "CREATE TABLE threads ("
                "rollout_path TEXT NOT NULL, updated_at_ms INTEGER NOT NULL)"
            )
            database.executemany(
                "INSERT INTO threads VALUES (?, ?)",
                [(os.fspath(older), 1), (os.fspath(newest), 2)],
            )
            database.commit()
            database.close()

            self.assertEqual(
                quota.latest_quota(codex_home),
                (14.0, 10_080, 1_787_011_993),
            )

    def test_thread_activity_does_not_override_newer_quota_evidence(self) -> None:
        quota = codex_quota
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            paths = [home / f"thread-{i}.jsonl" for i in range(3)]
            for path, used, stamp in zip(
                paths,
                (27, 24, 25),
                (
                    "2026-09-10T08:00:00Z",
                    "2026-09-14T22:00:00Z",
                    "2026-09-14T23:00:00Z",
                ),
                strict=True,
            ):
                event = json.loads(
                    _rate_event(
                        primary={
                            "used_percent": used,
                            "window_minutes": 10_080,
                            "resets_at": 1_789_860_845,
                        },
                        secondary=None,
                        limit_id="codex",
                    )
                )
                event["timestamp"] = stamp
                path.write_text(json.dumps(event) + "\n")
            # A complete non-event JSON line has no timestamp and must not hide
            # the newest quota record earlier in that file.
            with paths[-1].open("a") as stream:
                stream.write("{}\n")
            # The busiest thread has the oldest main-quota evidence.
            with sqlite3.connect(home / "state_5.sqlite") as connection:
                connection.execute(
                    "CREATE TABLE threads (rollout_path TEXT, updated_at_ms INTEGER)"
                )
                connection.executemany(
                    "INSERT INTO threads VALUES (?, ?)",
                    [(str(path), 3 - i) for i, path in enumerate(paths)],
                )
            self.assertEqual(quota.latest_quota(home), (25.0, 10_080, 1_789_860_845))

    def test_does_not_display_an_expired_snapshot(self) -> None:
        quota = codex_quota
        self.assertEqual(
            quota.status_text(
                Path("/not/read"),
                now=200.0,
                snapshot=(14.0, 10_080, 199),
            ),
            "",
        )


if __name__ == "__main__":
    unittest.main()
