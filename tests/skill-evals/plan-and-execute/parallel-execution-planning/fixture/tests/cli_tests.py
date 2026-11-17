import io
import unittest
from unittest import mock

from tally.cli import main


class CliTests(unittest.TestCase):
    def test_default_round_trip(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("apples 3\n")), mock.patch(
            "sys.stdout", new_callable=io.StringIO
        ) as out:
            self.assertEqual(main([]), 0)
        self.assertEqual(out.getvalue(), "apples: 3\n")


if __name__ == "__main__":
    unittest.main()
