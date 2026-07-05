# ADR 0003 — Crash marker tracks the live transcript via a SessionStart hook

**Status:** Proposed (2026-06-16) — moves to Accepted after the DR1/DR9 UAT confirms a real `/clear`-then-crash resumes the right session.

**Decision authors:** crash-detection Phase 2 close (correlation revision)

**Supersedes:** `docs/design-plans/2026-06-12-crash-detection-correlation-revision.md` (the forensic, timestamp-only correlation revision — retired).

**Touches:** `docs/design-plans/2026-06-12-crash-detection.md` § Stage-1 correlation; Phase 2 Task 4; `plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh`; `plugins/denubis-plan-and-execute/hooks/hooks.json`.

**Implemented as (2026-06-17):** `plugins/denubis-plan-and-execute/hooks/update-live-marker.py` — stdlib-only Python, invoked via plain `python3` from a second `SessionStart` command in `denubis-plan-and-execute`'s `hooks.json`. An initial bash/`sed` implementation was rewritten to Python after the `sed` replacement position bred a `&`-expansion marker-corruption bug; the Python form (a single-line, regex-gated, atomic rewrite) eliminates that injection class. See `phase_02b.md` Task 1 "REVISED 2026-06-17". Pinned by `tests/test_update_live_marker.bats`.

## Context

The 2026-06-12 design and Phase 2 Task 4 rest on one sentence: *"the wrapper stamps a canonical `session_id` into each `.live`, so `correlate()` matches a marker to `<session_id>.jsonl` exactly — a direct, unambiguous match for every future session."* That sentence is false after a `/clear`.

A read-only diagnostic over `~/.claude/projects` (operator consent) found, for the very session doing the diagnosis:

- The process/harness session id is `43e087fc` (it is also this session's `/tmp` task-dir name).
- The **live transcript** being written is `57fcf857.jsonl` — a different uuid, in a different namespace.
- `43e087fc.jsonl` is frozen: its last real entry is `2026-06-14T11:11:17Z`; `57fcf857.jsonl`'s first entry is `2026-06-14T11:11:27Z` (10 s later) and it is still being written.

What rotated them, verified from the records:

- `43e087fc.jsonl` contains a `/compact` **in place** at record 847 (`type=system` with `compactMetadata`, then a `user` record with `isCompactSummary=True`) and kept being written afterward — so `/compact` does **not** rotate the file.
- `57fcf857.jsonl` opens fresh (`type=mode` → `file-history-snapshot` → `attachment` with `entrypoint`/`version`, a brand-new `sessionId`, no compact-summary header, no back-link to `43e`). That is a **new-session spawn** — a `/clear`, which Claude Code implements as a new session id **and** a new `<uuid>.jsonl` (confirmed against the hooks/sessions docs and issue #37451).

The wrapper writes the marker **once at launch** and never updates it. So after a `/clear`, the marker names the abandoned launch transcript while the operator's live work is a different file.

**Impact (operator-confirmed: common and frustrating).** On a crash after one or more `/clear`s, the leftover `.live` marker — the only proof a *system* crash happened — binds to the abandoned launch transcript. Triage then offers `claudew --resume <abandoned-uuid>`, while the real post-clear work appears only as a quieter markerless row (`borderline`/`concluded`). The misdirection is worst on reboot: the boot-mismatch rule (`classify.py` rule 4, wildcard tail) classifies the stale file `HARD_CRASH` with confidence. No work is lost (every transcript is swept by `_walk_jsonl_only`), but the crash flag lands on the wrong session.

**Rejected alternative — forensic correlation.** A prior revision proposed fixing this inside `correlate()` by reconstructing, at death-time, which file was live: detect a transcript "handoff" from timestamps (`Y.first-entry-ts >= X.last-entry-ts`), or gate the direct-match on a `CONCLUDED` tail. Rejected because:

- There is no machine-followable cross-file link (`57f`'s records do not reference `43e`), and no official JSONL schema to build on.
- Timestamps truncate to whole seconds, so a same-second rotation is indistinguishable from same-second concurrency under any `>`/`>=` choice.
- A `CONCLUDED` tail cannot distinguish a rotated-away ancestor from a session merely killed while idle between turns — both tail `CONCLUDED`.
- It reconstructs at death-time a fact the runtime already has, and it leaves the wrapper *also* guessing the id at launch. Two guessers for one fact.

## Decision

**Keep the marker honest at runtime; do not reconstruct it after death.**

1. A `SessionStart` hook (fires on `startup`/`resume`/`clear`/`compact` — `SessionStart:clear` is observed firing in the diagnosing session) reads the hook payload's **`transcript_path`** from stdin and rewrites the marker's `session_id=` line to `basename(transcript_path)` without its `.jsonl` suffix.
2. **Key off `transcript_path`, not the stdin `session_id`.** The two are different namespaces (`43e` vs `57f`); `transcript_path` is the live file *by construction*, and its basename drops straight into the existing `session_id=` field, so `correlate()` needs no change.
3. The wrapper `export`s `CR_LIVE_FILE` (today a local variable) so the hook can locate the marker. The marker is PID-keyed (`$$.live`) and the wrapper PID is stable across `/clear`, so the hook always updates the same file.
4. **`correlate()` is unchanged.** With a fresh marker, the existing `DIRECT_MATCH(session_id)` is correct. Phase 2 Task 4 closes as **correct as built** — the bug was a stale input, not the matcher.
5. The wrapper's launch-time `CR_SESSION_ID` derivation (the `--resume`/`--session-id`/`EXTRA_ARGS` parsing) is reduced to a one-shot bootstrap stamp; the hook is the **single authoritative writer** of the live uuid. The forensic revision doc is retired.

### Hook contract (load-bearing)

- Replace **only** the `session_id=` line. Preserve `cwd`, `started`, `argv`, `boot_id`, `start_time`, and the PID-keyed filename verbatim. `start_time` drives `pid_alive_checked`; a naive regenerate would recompute or drop it and break PID-reuse rejection.
- Write atomically (`tmp` + `mv`), same as the wrapper.
- No-op and exit 0 when `CR_LIVE_FILE` is unset or the marker is missing. Never block session start; never touch a marker outside `claudew`.
- Multi-clear A→B→C leaves the marker at C (each `SessionStart` re-stamps the latest live transcript).

## Consequences

**Positive:**
- One writer of the live uuid; no death-time guessing and no launch-time guessing.
- `correlate()` untouched — the 210 pytest + 18 bats stay green; no precedence-test churn.
- Multi-rotation handled for free.

**Negative / residual:**
- The hook only fires while Claude runs and only on `SessionStart` events. A transcript rotation triggered by an event that fires no `SessionStart` (none known) would leave the marker stale — the same failure mode as today, not a new one.
- Forward-only: sessions launched by the pre-export wrapper get no hook update (no `CR_LIVE_FILE`), and legacy markers fall back to current behaviour.

**Verification honesty:**
- The hook is unit-testable: marker rewrite, field preservation, atomicity, the unset/missing no-op, and multi-clear. The crash_recovery suite proves all of these.
- "Real `/clear`, then crash → triage points at the live session" is Claude Code behaviour the unit suite **cannot** prove. It folds into the existing `DR1/DR9` UAT entry ("the resume line brings back the *right* session"). A green unit suite does not imply this end-to-end claim.

## Verification

- **RED-before-build (diagnostic, no commit):** a logging-only `SessionStart` hook appends `session_id` and `transcript_path` to a temp file; one real `/clear` confirms `basename(transcript_path)` equals the new live `.jsonl` and differs from the launch `session_id`. This validates the linchpin before the real hook is written.
- **Unit:** the hook updater rewrites `session_id=` and preserves every other line; is atomic; no-ops when `CR_LIVE_FILE` is unset or the marker is absent; A→B→C ends at C.
- **bats:** through `claudew`, `CR_LIVE_FILE` is exported and a stubbed `SessionStart` invocation updates the marker; the clean/abnormal-exit cleanup contract (AC4.5) stays green.
- **UAT (DR1/DR9):** after a real `/clear` and a forced kill, `triage` flags the live transcript as the crash victim and the `claudew --resume <uuid>` line reopens it.
