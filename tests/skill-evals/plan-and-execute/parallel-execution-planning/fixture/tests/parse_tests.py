import unittest

from tally.parse import parse_lines


class ParseTests(unittest.TestCase):
    def test_lines(self) -> None:
        self.assertEqual(parse_lines("apples 3\n\npears 5\n"), [("apples", 3), ("pears", 5)])


if __name__ == "__main__":
    unittest.main()
