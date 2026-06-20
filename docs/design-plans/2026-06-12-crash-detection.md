# Post-mortem crash detection — correlation join Design

**GitHub Issue:** None

**Seed / requirements:** `docs/design-plans/2026-05-19-post-mortem-crash-detection.md` (problem statement, empirical algorithm, gotchas, three 2026-06-12 addenda, operator binding requirements). **Parent design:** `docs/design-plans/2026-05-08-crash-recovery.md`.

## Summary

The crash-recovery plugin already classifies sessions as `hard_crash` when their liveness marker is present and the process is dead. In practice, zero crash victims surfaced: measurement against the operator's machine showed the correlation join that maps a `.live` marker to its JSONL session returning `no_match` for 33 of 36 markers, and 1013 of 1292 sessions classifying as `irrecoverable/missing_cwd`. The root cause was a single-line read: both `scan.py` and `correlate.py` read only the first line of a transcript to extract `cwd`, but 957 of 1301 transcripts now begin with a snapshot record and carry `cwd` on a later line. The read failed silently, the project-directory lookup failed, and the `.live` signal was discarded before the classifier ever saw it.

This design repairs the join rather than the classifier. A bounded forward scan replaces the line-1 read, shared by both modules. Going forward, the wrapper stamps each `.live` with `session_id` and `start_time`, allowing exact match to `<session_id>.jsonl` and start-time-checked liveness that rejects recycled PIDs. For the existing id-less backlog, a tighter mtime window corroborated by the tmux-resurrect pane set resolves most ambiguity without silent guessing. Scan deduplication prevents the UNIQUE constraint violation that would otherwise crash `triage` once correlation succeeds. Phase 4 adds a prioritised `## Probable system-crash victims` render section and two new `sessions` columns (`pane_title`, `last_substantive`) via an idempotent migration. Phase 5 extends `prune` to reap dead markers whose session is now classified. Truly marker-less victims (crashes that predate wrapper install) are out of scope — see DR9.

## Definition of Done

1. `crash-recovery triage` surfaces same-boot crash victims (`.live`-present **and** PID-dead, start-time-checked) as `hard_crash` in a dedicated, prioritised render section with full resumable UUIDs — not buried under "Needs investigation".
2. The line-1-only `cwd` read is replaced by a bounded forward scan, so sessions whose `cwd` appears on a later JSONL line are no longer misclassified `irrecoverable/missing_cwd`, and `.live`→JSONL correlation succeeds for them.
3. The scan is dedup-safe: a single scan never emits two facts for one UUID, so `triage` cannot crash with a `classification_history` UNIQUE violation once correlation succeeds.
4. The wrapper records `session_id` and `start_time` in each `.live`; future sessions correlate by exact session id, and PID-liveness is start-time-checked so a recycled PID cannot masquerade as alive.
5. Render is all-means-all: every in-scope session appears; crash victims are a prioritised highlight, never a filter; rows are keyed on pane-title, last-substantive activity, last-activity timestamp, and full UUID.
6. tmux-resurrect snapshots enrich the backlog: pane-title labels and pane∩mtime-cluster corroboration for id-less `.live` files.
7. Dead `~/.claude/run` markers can be reaped through the existing gated `prune`.
8. All new behaviour is covered by tests (pytest + bats); the existing 179 pytest + 13 liveness-bats baselines still pass.

## Acceptance Criteria

### crash-detection.AC1: Crash victims surface as hard_crash
- **crash-detection.AC1.1 Success:** A `.live` that is present, PID-dead, boot-current, with a dead-pid tail kind classifies as `hard_crash`.
- **crash-detection.AC1.2 Success:** A `hard_crash` row renders in `## Probable system-crash victims` with its full UUID and a `claudew --resume <full-uuid>` line.
- **crash-detection.AC1.3 Edge:** A `.live` present + PID-alive (start-time matched) classifies `live`, not `hard_crash`.

### crash-detection.AC2: Forward cwd read repairs correlation and the missing_cwd mislabel
- **crash-detection.AC2.1 Success:** A JSONL whose `cwd` is on a later line (line 1 a snapshot record) yields its real cwd, not `""`, and is not classified `irrecoverable/missing_cwd`.
- **crash-detection.AC2.2 Success:** A `.live` whose session's cwd is on a later line correlates (DIRECT or MTIME), not `no_match`.
- **crash-detection.AC2.3 Edge:** A JSONL with no `cwd` anywhere in the scan window still classifies `irrecoverable/missing_cwd` (genuine case preserved).

### crash-detection.AC3: Dedup-safe scan
- **crash-detection.AC3.1 Success:** A scan where two `.live` files resolve to the same UUID completes without `IntegrityError` and writes one `sessions` row.
- **crash-detection.AC3.2 Success:** Deterministic precedence — when one UUID is both a direct-match and an ambiguous candidate, the direct-match fact wins.

### crash-detection.AC4: Wrapper stamps and start-time-checked liveness
- **crash-detection.AC4.1 Success:** The wrapper writes `session_id=` and `start_time=` into the `.live` at startup, for both fresh and resumed sessions.
- **crash-detection.AC4.2 Success:** A marker whose stored `start_time` matches `/proc/<pid>/stat` is alive; a recycled-PID marker (mismatched `start_time`) is dead.
- **crash-detection.AC4.3 Success:** A `session_id`-bearing marker direct-matches `<session_id>.jsonl`.
- **crash-detection.AC4.4 Back-compat:** A legacy marker without `start_time` falls back to `kill -0`; without `session_id` falls to Stage-2.
- **crash-detection.AC4.5 Regression:** Clean exit (0/130) still removes the `.live`; abnormal exit (137/139/non-zero) preserves it.
- **crash-detection.AC4.6 Success (marker stays live):** A `SessionStart` hook rewrites the marker's `session_id=` line to `basename(transcript_path)` on `startup`/`resume`/`clear`/`compact`, preserving every other line (`cwd`/`started`/`argv`/`boot_id`/`start_time`) and the PID-keyed filename verbatim. After a `/clear` (and across multiple clears A→B→C), the marker names the **live** transcript, not the abandoned launch one. (See ADR 0003.)
- **crash-detection.AC4.7 Safety:** The hook is a no-op that exits 0 when `CR_LIVE_FILE` is unset or the marker is absent — `claude` run outside `claudew`, or a pre-write race, never blocks session start and never touches a marker the hook does not own.

### crash-detection.AC5: All-means-all render
- **crash-detection.AC5.1 Success:** Every in-scope session renders; the crash highlight adds a section, never drops a roster row.
- **crash-detection.AC5.2 Success:** Row header uses the full UUID (not `uuid[:8]`); pane-title, last-substantive, and `jsonl_last_ts` appear when available.
- **crash-detection.AC5.3 Success:** Render is byte-identical for identical DB state.

### crash-detection.AC6: Backlog disambiguation with tmux-resurrect
- **crash-detection.AC6.1 Success:** A backlog marker with exactly one in-tight-window JSONL resolves to `MTIME_MATCH`.
- **crash-detection.AC6.2 Success:** A multi-candidate set corroborated by exactly one resurrect `claude` pane resolves to that candidate.
- **crash-detection.AC6.3 Edge:** An uncorroborated multi-candidate set stays `borderline/ambiguous_match`, listing all candidates (never silently picks).
- **crash-detection.AC6.4 Success:** `resurrect.py` parses `pane` lines by field order, filters to `claude`/`✳` panes, and selects the latest snapshot at/just before `started`.

### crash-detection.AC7: Schema migration
- **crash-detection.AC7.1 Success:** `open_db()` on a pre-existing DB lacking the new columns adds `pane_title`/`last_substantive` without data loss; re-running is a no-op.
- **crash-detection.AC7.2 Success:** A fresh `init()` creates the columns from DDL.
- **crash-detection.AC7.3 Edge:** `render()` on a not-yet-migrated DB (no scan since upgrade) does not raise `no such column`; it renders with the new fields treated as absent.

### crash-detection.AC8: Reaping ~/.claude/run
- **crash-detection.AC8.1 Success:** `prune --dry-run` lists dead, start-time-checked markers whose session is `concluded`/`hard_crash`, without deleting.
- **crash-detection.AC8.2 Success:** `prune --confirm` removes them.
- **crash-detection.AC8.3 Failure:** Alive markers and uncorrelated markers are never reaped.

### crash-detection.AC9: Baselines preserved
- **crash-detection.AC9.1 Regression:** The existing 179 crash_recovery pytest pass.
- **crash-detection.AC9.2 Regression:** The existing 13 liveness bats pass.

## Glossary

- **`.live` file (liveness marker)**: A file in `~/.claude/run/` written by the wrapper when a Claude Code session starts and removed on clean exit. Its presence with a dead PID signals a crash.
- **`~/.claude/run/` (run dir)**: Directory holding one `.live` marker per active or crashed session. Distinct from the JSONL transcript store.
- **boot-current**: A `.live` marker is boot-current if the session started in the current OS boot. A marker from a previous boot is not a crash victim — the process was legitimately killed when the machine went down.
- **JSONL transcript**: The per-session log file (`<uuid>.jsonl`) that Claude Code writes during a session. Each line is a JSON record. `cwd`, timestamps, and message content are recovered from these files.
- **snapshot record**: A JSONL record with fields `type`, `messageId`, `snapshot`, `isSnapshotUpdate` written by Claude Code at session start. Because it is now the first line of most transcripts, the prior line-1 `cwd` read produced an empty string instead of the working directory.
- **bounded forward scan**: The replacement for the line-1 read. Scans the first N lines of a JSONL file to find the first record containing a non-empty `cwd`, shared by `scan.py` and `correlate.py` via a helper in `jsonl.py`.
- **correlation join**: The step that maps a `.live` file to its JSONL session. When it returns `no_match`, the marker's liveness signal is discarded and the session cannot be classified `hard_crash`.
- **Stage-1 correlation (exact)**: Matches a `.live` to its transcript by `session_id` recorded in the marker. Deterministic; available for all future sessions. A `SessionStart` hook keeps `session_id` pointed at the live transcript across `/clear` rotation (ADR 0003), so the match stays correct, not merely exact.
- **Stage-2 correlation (heuristic)**: Matches id-less backlog markers by a tight mtime window (upper and lower bound on first-entry timestamp) corroborated by the tmux-resurrect pane set.
- **`session_id`**: The UUID of the session's live transcript, recorded in the `.live`. The wrapper bootstraps it at launch; a `SessionStart` hook rewrites it to `basename(transcript_path)` on each rotation so it names the live `<uuid>.jsonl` (not the abandoned launch one), enabling exact match without mtime heuristics.
- **`start_time`**: The process start time from `/proc/self/stat` field 22 (clock ticks since boot), stamped into each `.live`. Used to detect PID reuse: a live-looking PID whose `start_time` does not match the stored value is treated as dead.
- **PID reuse**: Linux recycles process IDs. Without `start_time` checking, a new process that happens to inherit the PID of a crashed Claude session would appear alive.
- **mtime window**: The time range used in Stage-2 to find JSONL files whose first-entry timestamp falls near a marker's `started` time. The prior implementation used a lower bound only, causing over-collection and `AMBIGUOUS` results.
- **tmux-resurrect / byobu**: tmux-resurrect periodically saves a snapshot of all tmux pane states to `~/.byobu-sessions/tmux_resurrect_*.txt`. The snapshot records the window title, current path, and command for each pane. Used in Stage-2 to corroborate which JSONL candidate matches a given marker.
- **pane-title slug (`✳`)**: The Unicode `✳` character in Claude Code's tmux window title while a session is active (followed by the `exec-session-naming` slug). The resurrect parser filters to panes bearing this marker to identify Claude sessions.
- **`hard_crash`**: Classification given to a session whose `.live` is present, PID is dead, and boot-currency checks pass. Represents lost work requiring user attention.
- **`irrecoverable/missing_cwd`**: The classification previously applied to sessions whose JSONL yielded an empty `cwd` on line 1. Most were false positives caused by the snapshot-record issue; the forward scan corrects them.
- **`concluded`**: Classification for a session that exited cleanly. A `concluded` session's dead `.live` marker is reapable by `prune`.
- **`borderline/ambiguous_match`**: Classification for a backlog marker with multiple plausible JSONL candidates that corroboration cannot resolve. The tool lists all candidates and never picks silently.
- **dedup-safe scan**: The property that a single scan pass never writes two facts for one UUID. Required because two `.live` files can resolve to the same UUID once correlation succeeds, which would otherwise produce a `(uuid, scan_id)` UNIQUE violation crashing `triage`.
- **`classification_history`**: A table recording every classification transition per session per scan, with a UNIQUE constraint on `(uuid, scan_id)`. The dedup fix prevents duplicate-insert failures against this constraint.
- **functional core / imperative shell**: Architectural pattern used throughout crash-recovery. Pure functions (`classify()`, `render()`, JSONL helpers) contain logic; `scan_db.py` owns all DB writes. New helpers follow this split.
- **idempotent migration**: The schema-change pattern for the new columns. `ALTER TABLE ADD COLUMN` is guarded by `PRAGMA table_info` so re-running `open_db()` on a DB that already has the columns is a no-op. **[Superseded by the Phase 4 C1 fix: DDL runs only from `init()`, the deliberate upgrade command; `open_db()` no longer migrates — it asserts the additive columns are present and refuses an un-migrated DB. The `table_info` guard keeps `init()` idempotent.]**
- **`last_substantive`**: A new `sessions` column holding the last human/assistant text from the transcript, extracted by skipping content-level bookkeeping (`<usage>`, `<summary>`, `</task-notification>`, post-compaction boilerplate).
- **`prune` / reaping**: The existing `prune` subcommand with `--dry-run`/`--confirm` gates, extended to remove dead, start-time-checked `.live` markers whose session is `concluded` or `hard_crash`.
- **`claudew --resume <uuid>`**: The resume invocation shown in render output. `claudew` is the wrapper script; resuming through it means the resumed session also gets a fresh `.live` marker.

## Architecture

The crash-recovery pipeline already reads `~/.claude/run/*.live`, classifies `present + dead-PID + boot-current` as `hard_crash`, and re-scans on every `triage`. Measurement this session (against the operator's real machine, read-only into a temp DB) proved the gap is **not** the flag or the classifier but the **correlation join** that maps a `.live` file to its JSONL session:

- `correlate()` returned `no_match` for **33 of 36** `.live` files (25 of 27 dead).
- **1013 of 1292** sessions were classified `irrecoverable/missing_cwd`.
- Result: **0** `hard_crash`, every victim in the `unknown_tail_kind` bin.

Root cause: `scan._first_entry_cwd` and `correlate._cwd_matches_any_jsonl_in` read only the **first** JSONL line, but **957 of 1301** transcripts now begin with a `{type,messageId,snapshot,isSnapshotUpdate}` record and carry `cwd` on a later line. The cwd read fails → the project-dir reverse lookup fails → the `.live` signal is discarded → the session falls to the no-liveness path. This design repairs the join in two stages and surfaces the result.

**Stage-1 correlation (deterministic, exact).** A bounded forward scan finds the first JSONL record with a non-empty string `cwd` (shared helper in `jsonl.py`, consumed by `scan.py` and `correlate.py`). Each `.live` carries a `session_id` naming the session's transcript, so `correlate()` matches a marker to `<session_id>.jsonl` exactly. Precedence: `session_id` → `--resume <uuid>` → Stage-2.

For that exact match to be *correct*, the marker's `session_id` must name the **live** transcript, not merely the launch one. `/clear` spawns a new session id and a new `<uuid>.jsonl` (verified; `/compact` summarises in place and does not rotate the file), so a once-at-launch stamp goes stale and names the abandoned transcript — the crash flag then lands on the session the operator deliberately cleared, while the live work shows only as a quieter markerless row (see **ADR 0003**). A `SessionStart` hook keeps the marker honest: on every `SessionStart` (`startup`/`resume`/`clear`/`compact`) it rewrites the `session_id=` line to `basename(transcript_path)` — the live transcript *by construction*, read from the hook payload rather than the launch-pinned harness `session_id`. The wrapper `export`s `CR_LIVE_FILE` so the hook locates the PID-keyed marker; the hook is the single authoritative writer of the uuid, and `correlate()` is unchanged.

**Stage-2 correlation (heuristic, id-less backlog).** Existing `.live` files predate the `session_id` stamp. For them, the mtime window is narrowed to a first-entry-ts band near `started` (upper **and** lower bound, vs today's lower-bound-only over-collection), corroborated by the tmux-resurrect pane set (`~/.byobu-sessions/tmux_resurrect_*.txt`). A coincidental fsync burst will not also carry a matching live `claude` pane. Residual-ambiguous markers list **all** candidates; the tool never silently picks.

**Liveness hardening.** The wrapper also stamps `start_time` (`/proc/self/stat` field 22). "Alive" becomes `pid_alive AND /proc/<pid>/stat starttime == stored start_time`, so a recycled PID cannot fake "alive". Legacy markers lacking `start_time` fall back to bare `kill -0` with the known reuse caveat.

**Dedup-safe scan.** Once correlation works, two same-cwd `.live` files can resolve to one UUID (or one as direct-match and another as an ambiguous candidate), producing duplicate facts and a `classification_history` `(uuid, scan_id)` UNIQUE violation that crashes `triage`. The walk deduplicates facts by UUID before the write loop, with deterministic precedence (exact > window > ambiguous-candidate; within a rank, live-over-dead, then sorted liveness path — see DR10).

**Render.** `hard_crash` rows route to a new top section `## Probable system-crash victims`; the full six-section roster still renders below (all-means-all). Rows key on the resurrect pane-title (`✳` slug) → last-substantive text → `jsonl_last_ts` (a stored, deterministic value, safe to surface) → full UUID. `pane_title` and `last_substantive` are new `sessions` columns added by an idempotent migration. Last-substantive extraction extends the backward scan to skip content-level bookkeeping (`<usage>`, `<summary>`, `</task-notification>`, post-compaction boilerplate).

**Reaping.** `prune` is extended to remove dead, start-time-checked `.live` markers whose session is now `concluded`/`hard_crash`, gated by the existing `--dry-run`/`--confirm`. **Scope extension (2026-06-17):** the `session_id`-keyed reaper covers only id-bearing markers, but the real backlog is dominated by **id-less** markers (pre-Phase-2 markers, plus an ongoing trickle from `--continue`-without-uuid / `--print` / bare sessions). Reaping must also cover id-less/orphan dead markers — reapable iff they do NOT correlate (via the Phase 3 mtime window) to a *dangling* recoverable session, since removing a marker never deletes a session, only its redundant liveness signal. Criterion validated by a one-time manual sweep; open design questions (gating strictness for fuzzy-correlation deletes, criterion reconciliation, TTL) recorded in `docs/implementation-plans/2026-06-12-crash-detection/phase_05.md` § "Planned scope extension".

## Decision Record

### DR1: Re-anchor on the correlation join, not the addenda's "harden flag + wire classifier"
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If a future Claude Code format again moves `cwd` or changes JSONL record shape; if measurement shows correlation succeeding but victims still buried.

**Decision:** We chose to make the `.live`→JSONL correlation join the primary deliverable, after measuring that the classifier already consumes `.live` and already has the `hard_crash` rules. The seed's addenda assumed the signal was unconsumed; the code consumes it but `correlate()` discards 33/36 markers.

**Consequences:**
- **Enables:** A fix that actually surfaces victims, plus correcting 946 falsely-`irrecoverable` rows as a side effect.
- **Prevents:** Shipping a start-time stamp alone, which would leave correlation broken and victims buried.

**Alternatives considered:**
- **Addenda framing (stamp + wire classifier):** Rejected — measurement shows the classifier is wired; this alone surfaces nothing.
- **Minimal bugfix first (forward-cwd + dedup only):** Rejected by the operator in favour of the full re-anchor.

### DR2: Two-stage correlation (exact-id going forward, tight-window+resurrect for the backlog)
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If the resurrect snapshot format changes; if the tight time-window proves too narrow on slower filesystems.

**Decision:** We chose to split correlation into an exact `session_id` match for future sessions and a heuristic time-window+pane-corroboration path for the id-less backlog, rather than a single mtime-window strategy for all.

**Consequences:**
- **Enables:** Deterministic precise classification for every session created after the wrapper change; best-effort recovery for the existing 27-marker backlog.
- **Prevents:** Relying on mtime heuristics for sessions that could be matched exactly.

**Alternatives considered:**
- **Single mtime-window for all:** Rejected — over-collects (today's `AMBIGUOUS` failure) and is heuristic where an exact id is available.

### DR3: Forward-cwd read via a shared bounded helper in `jsonl.py`
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If transcripts grow a deep prefix of non-`cwd` records beyond the scan bound.

**Decision:** We chose one bounded forward-scan helper in `jsonl.py`, consumed by both `scan._first_entry_cwd` and `correlate._cwd_matches_any_jsonl_in`, over leaving two independent line-1-only reads.

**Consequences:**
- **Enables:** A single fix for both the `missing_cwd` mislabel and the project-dir lookup; one place to test.
- **Prevents:** Divergent cwd-extraction logic drifting between modules.

**Alternatives considered:**
- **Patch each call site independently:** Rejected — duplicated logic, two test surfaces, drift risk.

### DR4: Two wrapper stamps (`session_id` + `start_time`), not a second flag
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If `/proc/self/stat` field 22 proves unstable across the supported platforms.

**Decision:** We chose to harden the existing DR8 liveness file with two stamps — `session_id` (fixes correlation) and `start_time` (fixes PID-reuse) — rather than add a new flag, per the operator's instinct.

**Consequences:**
- **Enables:** Exact correlation and reuse-proof liveness from one file the wrapper already writes.
- **Prevents:** A second lifecycle to maintain and reap.

**Alternatives considered:**
- **New "exited properly" flag:** Rejected — the `.live` file already is that flag; duplicating it adds rot.

### DR5: Dedup-safe scan is a required co-ship
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** None expected; this closes a latent crash.

**Decision:** We chose to make `run_scan`/`_walk_sessions` dedup facts by UUID in the same change as the correlation fix, because correlation success is exactly what triggers the duplicate-fact `(uuid, scan_id)` UNIQUE violation.

**Consequences:**
- **Enables:** `triage` survives once markers correlate.
- **Prevents:** A correlation fix that crashes `triage` on the operator's machine.

**Alternatives considered:**
- **Ship correlation first, dedup later:** Rejected — would ship a known crash.

### DR6: No `CLASSIFIER_VERSION` bump
**Status:** Accepted
**Confidence:** Medium
**Reevaluation triggers:** If the forward-cwd change is found to alter `RULES` semantics rather than only inputs.

**Decision:** We chose not to bump `CLASSIFIER_VERSION`, because the forward-cwd fix changes classifier *inputs*, not the `RULES` table. Walked sessions are upserted every scan and history appends only on change, so the 946 `irrecoverable→concluded` corrections produce a one-time, correct wave of `classification_history` rows. The version-stale path only touches orphan-swept rows, which these are not.

**Consequences:**
- **Enables:** Reclassification with full history audit, no version-machinery churn.
- **Prevents:** Spurious "stale version" prune exclusions.

**Alternatives considered:**
- **Bump version to force reclassification:** Rejected — unnecessary; every scan already re-walks and re-upserts seen rows.

### DR7: New `sessions` columns via idempotent migration (first schema evolution)
**Status:** Accepted
**Confidence:** Medium
**Reevaluation triggers:** dba-reviewer feedback; if column count or render needs grow beyond two fields.

**Decision:** We chose to add `pane_title` and `last_substantive` columns to `sessions`, populated at scan time and read by `render`, via an idempotent `ALTER TABLE ADD COLUMN` migration fired from `open_db()` (guarded by `PRAGMA table_info`) so every read-write path migrates on open. `render()` opens its own read-only connection and so degrades gracefully — it checks `PRAGMA table_info` and treats absent columns as NULL rather than crashing on a not-yet-migrated DB. This is the codebase's first schema evolution.

**Consequences:**
- **Enables:** `render` stays a pure read of `sessions`; new display attributes are first-class, deterministic columns.
- **Prevents:** Overloading `state_summary` or doing filesystem I/O at render time (which would break render's purity/determinism); a render-only call on a pre-migration DB raising `no such column`.

**Alternatives considered:**
- **Overload `state_summary`:** Rejected — fragile parsing, one column with mixed meaning.
- **Render-time resurrect/JSONL lookup:** Rejected — breaks render's "pure function of `sessions`" and byte-identical guarantee.

### DR8: One comprehensive branch, five discrete phases
**Status:** Accepted
**Confidence:** Medium
**Reevaluation triggers:** If review surface proves too large; if an earlier phase is independently valuable enough to merge first.

**Decision:** We chose to design and build all five phases on the `crash-detection` branch and merge together, per operator selection, over staged or two-tranche merges.

**Consequences:**
- **Enables:** One coherent review of the whole join + render story.
- **Prevents:** Earliest-possible landing of the P1 bugfix floor.

**Alternatives considered:**
- **Staged (P1 merges first):** Considered; not chosen.
- **Two tranches (correctness, then UX):** Considered; not chosen.

### DR9: Marker-less (pre-wrapper-install) crash victims are out of scope
**Status:** Accepted
**Confidence:** Medium
**Reevaluation triggers:** If a future crash leaves recoverable lost work with no `.live` file (e.g. the wrapper was bypassed, or a `claude` invocation not going through `claudew`); if the operator asks to recover sessions that predate wrapper install.

**Decision:** We chose to scope `hard_crash` detection to sessions that have a `.live` marker (Stage-1 exact-id going forward; Stage-2 id-less backlog for markers the wrapper already wrote). Truly marker-less victims — the seed's original headline case (the 2026-05-18 crash that predated wrapper install and left **zero** `.live` files) — are explicitly **not** surfaced by this design. The seed's `last`/`journalctl` boot-history + pure-mtime-cluster algorithm (seed steps 1–2) is consciously deferred, not silently dropped.

**Rationale:** The wrapper is now installed and has been writing `.live` markers since ~2026-06-04. Every future session carries a marker, so the marker-less case is a one-time historical backlog (already recovered by hand in May), not a recurring failure. The forward-looking exact-id path prevents recurrence. Building boot-history clustering for a non-recurring backlog is YAGNI.

**Consequences:**
- **Enables:** A focused, deterministic design centred on the signal that now always exists.
- **Prevents:** Recovering a crash where no `.live` was ever written (wrapper bypass, `claude` invoked directly). If that need resurfaces, a future phase adds the seed's clustering path; this DR is the marker.

**Alternatives considered:**
- **Build the seed's marker-less mtime-clustering now:** Rejected as YAGNI — the wrapper closes the recurrence; the historical victims are already recovered.

### DR10: Same-rank dedup tie-break prefers live over dead
**Status:** Accepted (supersedes the sorted-path-only rule stated in DR5's prose)
**Confidence:** High
**Reevaluation triggers:** If a future need arises to distinguish two *dead* same-UUID markers more precisely than by path (e.g. by recency); if dedup ever moves after classification.

**Decision:** When two facts collide on one UUID at the same correlation rank, we break the tie by liveness first — a live fact (pid alive on the current boot) wins over a dead one — and only then by the lexicographically smaller liveness path. The earlier rule (tie-break by sorted path alone) was corrected after the Phase 1 coherence review (F1) showed it could persist a *running* session as `hard_crash`: a session that crashed, was resumed, and is alive again leaves two `--resume <uuid>` markers (both rank 0), and a path-only tie could let the stale dead marker win. Phase 2's `session_id` stamping widens this collision to ordinary resume-after-crash, so the fix lands before Phase 2.

**Consequences:**
- **Enables:** A running session is never reported under "Probable system-crash victims" because a dead sibling's path sorted first. Determinism is preserved (path remains the final tie-break).
- **Prevents:** Distinguishing two *dead* same-UUID markers by anything but path — deemed low-stakes (both classify `hard_crash`; only the reason may differ).

**Alternatives considered:**
- **Sorted path alone (original):** Rejected — order-independent but not correct-winner; mislabels a live session.
- **Add a recency term for two-dead collisions:** Deferred as YAGNI — both dead markers classify `hard_crash`; path suffices for determinism.

## Existing Patterns

This design follows the established crash-recovery architecture (`2026-05-08-crash-recovery.md`):

- **Functional core / imperative shell.** `classify()` and the `jsonl`/`correlate` helpers are pure; `scan_db.py` owns DB writes inside one `with conn:` transaction. New helpers (forward-cwd scan, resurrect parse, tight-window correlation) are pure and unit-tested in isolation.
- **Determinism.** `classify()` and `render()` are bit-identical for identical inputs. New columns are stored, deterministic values; surfacing `jsonl_last_ts` preserves byte-identical render.
- **Env-var overrides for test isolation.** `CRASH_RECOVERY_RUN_DIR`, `CRASH_RECOVERY_PROJECTS_ROOT`, `CRASH_RECOVERY_DB` already exist; a new `CRASH_RECOVERY_RESURRECT_DIR` (default `~/.byobu-sessions`) follows the pattern. The `test_claude_wrapper_liveness.bats` harness already isolates via a temp `CRASH_RECOVERY_RUN_DIR` and a `CLAUDE_REAL_BINARY` stub — new wrapper tests extend it; **no test touches the real `~/.claude/run`** (live fixtures).
- **Schema-from-authoritative-source.** `CLASSIFICATION_VALUES` in `db.py` remains the single source for the classification enum; new columns are added to `db.py`'s DDL plus the migration.
- **Gated destructive ops.** Reaping reuses `prune`'s `--dry-run`/`--confirm` survey/delete split.

New pattern introduced: the first `ALTER TABLE` migration (DR7). It is additive and idempotent; existing DBs gain nullable columns.

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Stage-1 correlation correctness + dedup-safe scan
**Goal:** Repair the cwd read so correlation succeeds and the `missing_cwd` mislabel clears; make the scan dedup-safe so `triage` cannot crash once markers correlate.

**Components:**
- `jsonl.py` — new bounded forward-scan helper returning the first record's non-empty string `cwd` (shared, pure).
- `scan.py` — `_first_entry_cwd` uses the helper; `_walk_sessions`/`run_scan` deduplicate facts by UUID before the write loop with deterministic precedence (exact > window > ambiguous-candidate; within a rank, live-over-dead, then sorted liveness path — see DR10).
- `correlate.py` — `_cwd_matches_any_jsonl_in` and `_jsonl_first_entry_ts_meets_threshold` use forward scans for `cwd`/`timestamp`.
- Tests: `tests/test_jsonl_tail.py` (or new `test_jsonl.py`), `test_scan.py`, `test_correlate.py` — fixtures with `cwd` on line 1, on a later line, and absent; two `.live` files resolving to one UUID must not raise.

**Dependencies:** None (first phase).

**Done when:** Forward-cwd helper covered; a scan over fixtures where two markers share a UUID completes without `IntegrityError`; sessions with later-line `cwd` no longer classify `missing_cwd`. Covers `crash-detection.AC1`, `crash-detection.AC2`.
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Wrapper stamps + start-time-checked liveness + exact-id correlation
**Goal:** Every future session writes a `session_id` and `start_time` into its `.live`; correlation prefers the exact id; liveness rejects PID reuse.

**Components:**
- `claude-wrapper.sh` — write `session_id=` (fresh: the generated `--session-id` uuid; resumed: the `--resume` uuid) and `start_time=` (`/proc/self/stat` field 22, the `starttime` in clock ticks since boot) into the `.live`; keys are additive and back-compatible.
- `liveness.py` — parse optional `session_id`/`start_time` (tolerant parser); add a start-time-checked liveness primitive (`pid_alive AND starttime matches`), falling back to bare `kill -0` when `start_time` is absent. **Robust `/proc/<pid>/stat` parse required:** field 2 (`comm`) can contain spaces and parentheses (`(sd-pam)`, `(kworker/0:1H-kblockd)`), so a naive `split()[21]` reads the wrong field and silently defeats the reuse check. Parse via `rpartition(')')` on the last `)`, then index `starttime` from the remainder (field 22 → index 19 of the post-`)` split). Applies on both the wrapper write (`/proc/self/stat`) and the scan read (`/proc/<pid>/stat`).
- `correlate.py` — precedence `session_id` exact → `--resume <uuid>` → Stage-2 window.
- Tests: `tests/test_claude_wrapper_liveness.bats` (new ACs for the two stamps + back-compat), `test_liveness.py` (start-time match/mismatch/absent), `test_correlate.py` (session_id direct match).

**Dependencies:** Phase 1.

**Done when:** Wrapper writes both keys; a marker with matching `start_time` is alive, a recycled-PID marker (mismatched `start_time`) is dead, a legacy marker (no `start_time`) falls back; a `session_id`-bearing marker direct-matches. Covers `crash-detection.AC3`, `crash-detection.AC4`.
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: Stage-2 backlog disambiguation (tight window + tmux-resurrect)
**Goal:** Resolve id-less backlog markers precisely enough to classify genuine victims as `hard_crash`; corroborate with the resurrect pane set; list all candidates when still ambiguous.

**Components:**
- New `resurrect.py` — pure parser for `~/.byobu-sessions/tmux_resurrect_*.txt`: select the latest snapshot at/just before a marker's `started`; extract `pane` lines' window-title (`✳` slug) and `pane_current_path`; filter to `claude` panes. Env override `CRASH_RECOVERY_RESURRECT_DIR`.
- `correlate.py` — narrow the mtime window to first-entry-ts within `[started, started+Δ]`; corroborate candidates against the resurrect pane set; keep `AMBIGUOUS` (all candidates) only when corroboration cannot disambiguate.
- Tests: new `test_resurrect.py` (field-order parse, claude-pane filter, snapshot selection), `test_correlate.py` (tight-window single match; pane corroboration resolves a multi-candidate set; genuine ambiguity preserved).

**Dependencies:** Phases 1–2.

**Done when:** A backlog marker with one in-window JSONL resolves to `MTIME_MATCH`; a multi-candidate set corroborated by exactly one pane resolves to it; an uncorroborated multi-candidate set stays `AMBIGUOUS` with all candidates. Covers `crash-detection.AC5`, `crash-detection.AC6`.
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: Render overhaul + schema migration
**Goal:** All-means-all render with a prioritised crash-victim section, human-meaningful row keys, and full resumable UUIDs.

**Components:**
- `db.py` — add `pane_title` and `last_substantive` to `SESSIONS_DDL`; idempotent `ALTER TABLE ADD COLUMN` migration guarded by `PRAGMA table_info`, fired from **`open_db()`** (not only `init()`) so every read-write path — `scan`/`triage`/`regenerate`/`prune` — migrates a pre-existing DB on open. **[Superseded by the Phase 4 C1 fix: the migration fires only from `init()`, not `open_db()`. Firing DDL from every read-write open created a TOCTOU race on the first concurrent open after an upgrade; `open_db()` now asserts schema-current and refuses an un-migrated DB (operator runs `crash-recovery init`). `render()` still degrades read-only.]**
- `scan_db.py`/`scan.py` — populate the new columns from resurrect + the last-substantive extraction.
- `jsonl.py` — last-substantive extraction skipping content-level bookkeeping (`<usage>`, `<summary>`, `</task-notification>`, post-compaction boilerplate), surfacing the last real human/assistant text.
- `render.py` — new `## Probable system-crash victims` top section for `hard_crash`; full six-section roster preserved; row header uses full UUID; show pane-title, last-substantive, and `jsonl_last_ts`; resume line stays `claudew --resume <full-uuid>`. **Graceful degradation:** `render()` opens its own read-only connection and cannot run the migration, so it must check `PRAGMA table_info` and treat absent `pane_title`/`last_substantive` as NULL rather than `SELECT`-ing them blindly — a render-only call on a not-yet-migrated DB must not raise `no such column`.
- Tests: `test_render.py` (new section ordering, full-roster preservation, full-UUID header, deterministic output), `test_jsonl*` (bookkeeping skip), migration idempotency test in `test_init.py`/`test_db`.

**Dependencies:** Phases 1–3.

**Done when:** A `hard_crash` row appears in the top section and every other in-scope row still renders; migration is idempotent on a pre-existing DB; render stays byte-identical for identical DB state. Covers `crash-detection.AC5`, `crash-detection.AC7`.
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: Reap `~/.claude/run`
**Goal:** Dead markers have a lifecycle; the run dir does not accumulate stale files indefinitely.

**Components:**
- `prune.py` — extend the survey/delete split to include dead, start-time-checked `.live` markers whose correlated session is `concluded`/`hard_crash`; preserve the four-condition gate philosophy.
- `__main__.py` — `prune` surfaces reapable markers in `--dry-run`; `--confirm` removes them.
- Tests: `test_prune.py` (reapable vs retained markers; alive markers never reaped; `--dry-run`/`--confirm` semantics).

**Dependencies:** Phases 1–4.

**Done when:** `prune --dry-run` lists dead reapable markers without deleting; `--confirm` removes them; alive and uncorrelated markers are retained. Covers `crash-detection.AC8`.
<!-- END_PHASE_5 -->

## Additional Considerations

**Backlog is best-effort.** The achievable count of backlog victims surfaced as `hard_crash` is unmeasured until Stage-2 is built; many dead markers have `concluded` tails (killed after a clean session, not lost work). The design does not promise a victim count — it guarantees victims are no longer *structurally* unable to surface.

**Platform.** `start_time` via `/proc/self/stat` and the resurrect path are Linux/byobu specific; the scan already refuses non-Linux. Legacy markers and non-byobu hosts degrade to the existing behaviour, not an error.

**Live fixtures.** The operator's `~/.claude/run/*.live` markers are live test fixtures. No automated test reads or writes the real run dir; all use a temp `CRASH_RECOVERY_RUN_DIR`.
