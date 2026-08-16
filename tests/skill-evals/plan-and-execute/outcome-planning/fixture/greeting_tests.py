import unittest

from greeting import greet


class GreetingTests(unittest.TestCase):
    def test_default_greeting(self) -> None:
        self.assertEqual(greet("Brian"), "Hello, Brian.")


if __name__ == "__main__":
    unittest.main()
