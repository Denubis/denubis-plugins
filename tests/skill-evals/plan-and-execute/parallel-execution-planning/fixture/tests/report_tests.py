import unittest

from tally.report import render_text


class ReportTests(unittest.TestCase):
    def test_text(self) -> None:
        self.assertEqual(render_text([("apples", 3)]), "apples: 3\n")


if __name__ == "__main__":
    unittest.main()
