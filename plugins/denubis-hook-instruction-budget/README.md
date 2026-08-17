# Instruction-budget alarm

This advisory `SessionStart` hook measures the always-on global and project
instruction chain against the intersection of two limits:

- no more than 200 lines; and
- no more than 32,768 bytes.

The limits apply to the combined global and local chain even though Codex's
actual 32 KiB loader cap applies only to its project chain. The stricter combined
policy catches context and adherence pressure before mechanical truncation.

Claude measurement includes `CLAUDE.md`, `CLAUDE.local.md`, `.claude/CLAUDE.md`,
unconditional `.claude/rules/*.md`, and recursive `@file` imports. Codex
measurement includes the global override/default file and one configured
override/default/fallback file at each directory from the project root to the
working directory. A Codex project chain above its configured loader cap is
reported separately from the combined policy alarm.

The hook returns only `systemMessage`. It does not add `additionalContext`, block
startup, or run after resume and compaction events.
