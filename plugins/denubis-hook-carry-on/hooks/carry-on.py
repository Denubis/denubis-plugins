#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# dependencies = ["websockets==16.0"]
# [tool.ty.environment]
# python-version = "3.14"
# ///

"""Codex-only lifecycle entry point and continuation watcher controls."""

from carry_on.runtime import main

if __name__ == "__main__":
    raise SystemExit(main())
