# tally input and output formats

**Status:** Accepted design

## Purpose

Let `tally` read CSV input and write JSON output, without changing its default behaviour.

## Current state

`tally.parse.parse_lines` reads `name value` lines, `tally.report.render_text` writes
`name: value` lines, and `tally.cli.main` joins them over standard input and output.
README usage documents only the default.

## Design

- Parsing: add `parse_csv(text)` to `tally/parse.py`. It reads `name,value` rows, skips
  blank lines and an optional `name,value` header row, and returns the same
  `list[tuple[str, int]]` as `parse_lines`. A row whose value is not an integer raises
  `ValueError` naming the row number.
- Rendering: add `render_json(rows)` to `tally/report.py`. It returns a JSON array of
  `{"name": ..., "value": ...}` objects, in input order, followed by one newline.
- Command line: `tally.cli.main` takes `--input {lines,csv}` and `--output {text,json}`,
  both defaulting to today's behaviour. A `ValueError` from `parse_csv` prints the message
  to standard error and returns exit status 2; the default `lines` input keeps today's
  behaviour on malformed input.
- Documentation: README usage shows both options. Each user-visible change adds its line
  to `CHANGELOG.md` under `## Unreleased`.

## Acceptance criteria

1. `parse_csv("name,value\napples,3\n\npears,5\n")` returns `[("apples", 3), ("pears", 5)]`.
2. `parse_csv("apples,three\n")` raises `ValueError` whose message names row 1, counting
   input lines from 1.
3. `render_json([("apples", 3)])` returns `[{"name": "apples", "value": 3}]` and a newline.
4. `main(["--input", "csv", "--output", "json"])` over `apples,3` writes the JSON of
   criterion 3 and returns 0; with no options, output is unchanged.
5. A malformed CSV value through `main` writes the error to standard error and returns 2.
6. README usage shows both options, and `CHANGELOG.md` has one line per user-visible change.

Every criterion is deterministic; none needs a human judgment.

## Implementation phases

Parsing and rendering are independent of each other. The command line depends on both.
