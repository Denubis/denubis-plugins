import sys

from tally.parse import parse_lines
from tally.report import render_text


def main(argv: list[str] | None = None) -> int:
    sys.stdout.write(render_text(parse_lines(sys.stdin.read())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
