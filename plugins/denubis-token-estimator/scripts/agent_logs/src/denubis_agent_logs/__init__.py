"""Read Claude Code and Codex session logs: roots, tolerant JSONL, usage records.

The modules are the library's public surface:

- :mod:`denubis_agent_logs.roots` resolves the Claude projects root and the Codex
  sessions root.
- :mod:`denubis_agent_logs.records` iterates JSONL files tolerantly and reports
  what it could not read.
- :mod:`denubis_agent_logs.claude` discovers Claude transcripts, extracts assistant
  usage records and user text, and deduplicates usage by message id.
- :mod:`denubis_agent_logs.timestamps` parses log timestamps.
- :mod:`denubis_agent_logs.windows` finds the weekly quota window an instant falls in.
- :mod:`denubis_agent_logs.usage` weighs a usage record's token counts into cost
  units.

Standard library only (ADR 0045).
"""
