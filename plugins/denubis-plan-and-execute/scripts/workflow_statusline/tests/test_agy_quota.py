from __future__ import annotations

import os
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

from workflow_statusline import agy_quota, cache


class AgyQuotaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_timezone = os.environ.get("TZ")
        os.environ["TZ"] = "Australia/Sydney"
        time.tzset()
        cls.module = agy_quota

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.original_timezone is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = cls.original_timezone
        time.tzset()

    def test_snapshot_path_matches_cache_writer_with_and_without_xdg(self) -> None:
        orig_xdg = os.environ.get("XDG_CACHE_HOME")
        orig_home = os.environ.get("HOME")
        try:
            os.environ["XDG_CACHE_HOME"] = "/xdg-test"
            self.assertEqual(
                self.module.snapshot_path(),
                Path("/xdg-test") / "agy-statusline" / "quota-seven_day",
            )
            os.environ.pop("XDG_CACHE_HOME", None)
            os.environ.pop("HOME", None)
            self.assertEqual(
                self.module.snapshot_path(),
                Path(
                    cache.quota_snapshot_path(
                        "seven_day", namespace=cache.AGY_NAMESPACE
                    )
                ),
            )
        finally:
            if orig_xdg is None:
                os.environ.pop("XDG_CACHE_HOME", None)
            else:
                os.environ["XDG_CACHE_HOME"] = orig_xdg
            if orig_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = orig_home

    def _write_snapshot(self, directory: Path, line: str) -> Path:
        target = directory / "quota-seven_day"
        target.write_text(line)
        return target

    def test_missing_file_renders_nothing(self) -> None:
        missing = Path("/nonexistent-agy-quota-test/quota-seven_day")
        self.assertEqual(self.module.status_text(missing, now=1000.0), "")

    def test_malformed_and_nonfinite_snapshots_render_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for bad in (
                "garbage\n",
                "1000|nan|90000\n",
                "1000|20|inf\n",
                "1000|20|1e20\n",
                "inf|20|90000\n",
            ):
                with self.subTest(bad=bad):
                    path = self._write_snapshot(Path(tmp), bad)
                    self.assertEqual(self.module.status_text(path, now=1000.0), "")
            binary_path = Path(tmp) / "quota-seven_day"
            binary_path.write_bytes(b"\xff\xfe\xfd")
            self.assertEqual(self.module.status_text(binary_path, now=1000.0), "")

    def test_expired_and_exact_reset_boundary_render_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for resets_at in (900.0, 1000.0):
                with self.subTest(resets_at=resets_at):
                    path = self._write_snapshot(Path(tmp), f"500|40|{resets_at}\n")
                    self.assertEqual(self.module.status_text(path, now=1000.0), "")

    def test_renders_used_and_pace_with_turned_v_separator(self) -> None:
        # Window: 2026-08-11 22:00 -> 2026-08-18 22:00 Sydney.
        # Active hours 07:00-22:00 give 15h/day, 105h total.
        # At 2026-08-13 22:00, 30h active elapsed -> pace 30/105*100 = 28.57 -> 29.
        resets_at = datetime(2026, 8, 18, 22, 0).timestamp()
        now = datetime(2026, 8, 13, 22, 0).timestamp()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_snapshot(Path(tmp), f"{now - 60}|34|{resets_at}\n")
            rendered = self.module.status_text(path, now=now)
        self.assertEqual(rendered, "#[bg=#0e3147,fg=#ff8585]34\u024529 Tu#[default]")

    def test_at_exact_pace_renders_red(self) -> None:
        # Window: 2026-08-11 07:00 -> 2026-08-18 07:00 Sydney (105 active h).
        # After 3.5 active days (2026-08-14 14:30 -> 52.5/105 = 50.0% exactly).
        resets_at = datetime(2026, 8, 18, 7, 0).timestamp()
        now = datetime(2026, 8, 14, 14, 30).timestamp()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_snapshot(Path(tmp), f"{now - 60}|50.0|{resets_at}\n")
            rendered = self.module.status_text(path, now=now)
        self.assertEqual(rendered, "#[bg=#0e3147,fg=#ff8585]50\u024550 Tu#[default]")

    def test_under_pace_renders_green(self) -> None:
        resets_at = datetime(2026, 8, 18, 22, 0).timestamp()
        now = datetime(2026, 8, 13, 22, 0).timestamp()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_snapshot(Path(tmp), f"{now - 60}|5|{resets_at}\n")
            rendered = self.module.status_text(path, now=now)
        self.assertEqual(rendered, "#[bg=#0e3147,fg=#86efac]5\u024529 Tu#[default]")

    def test_reset_switches_weekday_to_hour_at_24h_and_minutes_in_last_hour(
        self,
    ) -> None:
        reset = datetime(2026, 9, 17, 14, 30).timestamp()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_snapshot(Path(tmp), f"{reset - 100_000}|34|{reset}\n")
            for remaining, label in (
                (86_401, "Th"),
                (86_400, "14h"),
                (3_601, "14h"),
                (3_600, "14:30"),
                (60, "14:30"),
            ):
                with self.subTest(remaining=remaining):
                    rendered = self.module.status_text(path, now=reset - remaining)
                    self.assertEqual(rendered.split()[-1], label + "#[default]")


if __name__ == "__main__":
    unittest.main()
