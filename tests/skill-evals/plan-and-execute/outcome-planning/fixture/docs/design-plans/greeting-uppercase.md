# Uppercase greeting design

**Status:** Current design

## Purpose

Allow callers to request an uppercase greeting without changing existing output.

## Current state

`greeting.greet(name)` returns `Hello, <name>.` and README usage documents that call.

## Design

Add a keyword-only `uppercase: bool = False` option to `greet`. Construct the ordinary
greeting first and uppercase the complete result only when the option is true. Existing
callers remain unchanged.

## Acceptance criteria

- `greet("Brian")` returns `Hello, Brian.`.
- `greet("Brian", uppercase=True)` returns `HELLO, BRIAN.`.
- The README shows the optional uppercase call.

The result is deterministic and introduces no human-only acceptance judgment.

