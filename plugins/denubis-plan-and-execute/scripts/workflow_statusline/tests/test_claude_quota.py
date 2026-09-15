from __future__ import annotations

import os
import time
import unittest
from datetime import datetime
from pathlib import Path

from workflow_statusline import claude_quota


class ClaudeQuotaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_timezone = os.environ.get("TZ")
        os.environ["TZ"] = "Australia/Sydney"
        time.tzset()
        cls.module = claude_quota

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.original_timezone is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = cls.original_timezone
        time.tzset()

    # -- snapshot parsing ---------------------------------------------------
    def test_parses_valid_snapshot_line(self) -> None:
        snapshot = self.module.parse_snapshot("1000.5|34.0|90000.0\n")
        self.assertEqual(snapshot, (1000.5, 34.0, 90000.0))

    def test_rejects_malformed_lines(self) -> None:
        for text in ("", "garbage", "1|2", "a|b|c", "1000|-5|90000", "1000|101|90000"):
            with self.subTest(text=text):
                self.assertIsNone(self.module.parse_snapshot(text))

    def test_rejects_nonpositive_reset(self) -> None:
        self.assertIsNone(self.module.parse_snapshot("1000|50|0"))

    # -- snapshot path ------------------------------------------------------
    def test_snapshot_path_honours_xdg_cache_home(self) -> None:
        original = os.environ.get("XDG_CACHE_HOME")
        os.environ["XDG_CACHE_HOME"] = "/xdg-test"
        try:
            path = self.module.snapshot_path()
        finally:
            if original is None:
                os.environ.pop("XDG_CACHE_HOME", None)
            else:
                os.environ["XDG_CACHE_HOME"] = original
        self.assertEqual(
            path, Path("/xdg-test") / "claude-statusline" / "quota-seven_day"
        )

    # -- status text --------------------------------------------------------
    def _write_snapshot(self, directory: Path, line: str) -> Path:
        target = directory / "quota-seven_day"
        target.write_text(line)
        return target

    def test_missing_file_renders_nothing(self) -> None:
        missing = Path("/nonexistent-claude-quota-test/quota-seven_day")
        self.assertEqual(self.module.status_text(missing, now=1000.0), "")

    def test_expired_window_renders_nothing(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_snapshot(Path(tmp), "500|40|900\n")
            self.assertEqual(self.module.status_text(path, now=1000.0), "")

    def test_renders_used_and_pace_with_star_separator(self) -> None:
        # Window: 2026-08-11 22:00 -> 2026-08-18 22:00 Sydney.
        # Active hours 07:00-22:00 give 15h/day, 105h total.
        # At 2026-08-13 22:00, 30h active elapsed -> pace 30/105*100 = 28.57 -> 29.
        import tempfile

        resets_at = datetime(2026, 8, 18, 22, 0).timestamp()
        now = datetime(2026, 8, 13, 22, 0).timestamp()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_snapshot(Path(tmp), f"{now - 60}|34|{resets_at}\n")
            rendered = self.module.status_text(path, now=now)
        self.assertEqual(rendered, "#[fg=red]34*29 Tue#[default]")

    def test_under_pace_renders_green(self) -> None:
        import tempfile

        resets_at = datetime(2026, 8, 18, 22, 0).timestamp()
        now = datetime(2026, 8, 13, 22, 0).timestamp()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_snapshot(Path(tmp), f"{now - 60}|5|{resets_at}\n")
            rendered = self.module.status_text(path, now=now)
        self.assertEqual(rendered, "#[fg=green]5*29 Tue#[default]")

    def test_reset_switches_from_weekday_to_local_time_at_24_hours(self) -> None:
        import tempfile

        reset = datetime(2026, 9, 17, 14, 30).timestamp()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_snapshot(Path(tmp), f"{reset - 100_000}|34|{reset}\n")
            for remaining, label in (
                (86_401, "Thu"),
                (86_400, "14:30"),
                (3_600, "14:30"),
            ):
                with self.subTest(remaining=remaining):
                    rendered = self.module.status_text(path, now=reset - remaining)
                    self.assertEqual(rendered.split()[-1], label + "#[default]")


if __name__ == "__main__":
    unittest.main()
