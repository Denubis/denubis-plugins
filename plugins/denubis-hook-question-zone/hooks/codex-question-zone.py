#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# dependencies = ["websockets==16.0"]
# [tool.ty.environment]
# python-version = "3.14"
# ///

"""Check a native Codex question before its presentation."""

from question_zone_codex.runtime import main

if __name__ == "__main__":
    raise SystemExit(main())
