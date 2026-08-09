# ADR 0005 — A SessionStart hook appends with one bounded write and never takes a lock

**Status:** Accepted (2026-08-09) — shipped in `denubis-notes-advisory` 0.2.0 (`2a3fddd`).

**Decision authors:** codex prompt 07 supervision pass, session `a711c799`. Codex raised the question against its own draft; the supervisor ruled.

**Touches:** `plugins/denubis-notes-advisory/hooks/session-notes-advisory.py:222-287`; `tests/test_notes_advisory_hook.py`; `codex-prompts/07-notes-advisory-fire-log.md` § B.

## Context

`denubis-notes-advisory` shipped a SessionStart hook with no way to tell whether
it changes anything. The fix was a fire log: one JSON row per firing under
`~/.claude/notes-advisory/log/YYYY-MM-DD.jsonl`, so "did the hook work" becomes a
question about counts instead of impressions.

Every Claude Code session on the machine fires this hook, and several can start
at once. So the log has concurrent writers by construction.

Codex's own proleptic challenge against its first draft found a blocking
`fcntl.flock(..., LOCK_EX)` with no timeout, and asked whether the standing
requirement — *the hook must never block session start* — forbids it.

**It does.** A lock that can wait forever on another process is blocking session
start, not an edge case of it. The failure mode is the worst available: a stale
lock or a wedged writer does not degrade the log, it delays or hangs every new
session on the machine, for a feature whose entire purpose is observability.

### A supervisor error, recorded because it caused the draft

The prompt cited `update-live-marker.py` as the pattern to follow. It meant that
file's **never-block discipline** — diagnostic to stderr, always exit 0. Codex
reasonably read it as the **write mechanism** and reproduced temp-file plus
`os.replace`, which is how a file is safely *rewritten* and the wrong tool for
appending: concurrent writers under it lose rows rather than interleaving them.
The lock was then added to make the rewrite safe. The supervisor's wording
produced the draft; the supervisor corrected it mid-task.

### Rejected alternative — bound the lock with a timeout

Rejected. A bounded lock still blocks, just for less time, and it adds a second
failure mode where the row is silently dropped on timeout. It keeps `fcntl`,
which is Unix-only, for no gain over not locking at all.

## Decision

**Serialise the row to one line and append it in a single `write()`.**

1. Open with `os.O_WRONLY | os.O_CREAT | os.O_APPEND`, mode `0o600`. One
   `os.write()` of the whole line. No lock, no timeout, no `fcntl`, no temp
   file, no rewrite.
2. **Bound the row under `PIPE_BUF` (4096 bytes).** A single `O_APPEND` write
   below that size is atomic on POSIX, so concurrent sessions interleave whole
   rows and never tear one.
3. Where a row would exceed the budget, **truncate a field rather than
   reintroduce a lock.** Truncation runs in a fixed order that keeps the
   correlation fields — session id, source, dispatch — longest.
4. The silent path stays ahead of all logging: a project with no `.notes/`
   writes nothing and does not create the log directory.
5. Every logging failure becomes one stderr diagnostic and **exit 0**, with
   stdout byte-for-byte unchanged.

## Consequences

**Positive:**
- No mechanism exists by which the hook can delay session start, so the
  requirement holds by construction rather than by care.
- Dropping `fcntl` removes the Unix-only portability concern the challenge
  raised.
- Rows are append-only and self-describing; a reader tolerates a partially
  written tail by parsing line by line.

**Negative / residual:**
- Rows are capped at 4096 bytes, so a pathological path can be truncated. Chosen
  over losing the row.
- Atomicity is a **POSIX local-filesystem** guarantee. A home directory on NFS
  is outside it. Not currently the case on this machine, and not detected.
- The log is per-machine and unrotated. Growth is one short line per session
  start; no rotation policy is in place, and that is a known gap rather than a
  decision.

**Verification honesty:**
- Concurrency was exercised with **12 concurrent writers on Linux only**. macOS,
  Windows, and NFS were not tested. Codex disclosed this rather than being
  caught at it.
- The concurrency and mode-000 tests were written **after** the no-lock ruling,
  so they were never asserted to fail against the prohibited locking draft. The
  two test functions they extend did have recorded REDs against the original
  un-logged hook. The refinements themselves are unproven-by-RED, and are
  recorded as such rather than counted as test-first.
- A green suite says the hook does not block *in the tested conditions*. It does
  not prove the absence of a blocking path on a filesystem nobody ran it on.

## Verification

- **Independently re-run by the supervisor**, not read off codex's report:
  `rg -c 'fcntl|flock|LOCK_EX'` over the hook returns **0**; the write is
  `os.O_WRONLY | os.O_CREAT | os.O_APPEND` with one `os.write()`; the hook run
  by hand against a project with no `.notes/` exits 0 and leaves the log
  directory empty.
- **Suite:** `uv run pytest -q` → 1 failed, 1480 passed, the sole failure the
  carried `using-code-search` description-length one.
- **Unproven and deliberately so:** behaviour on NFS, macOS, and Windows.
