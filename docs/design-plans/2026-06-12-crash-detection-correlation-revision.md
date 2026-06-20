# Correlation revision: freshness-gated session_id (root fix)

> **RETIRED / SUPERSEDED (2026-06-16) by [ADR 0003](../architecture/decisions/0003-marker-tracks-live-transcript-via-sessionstart-hook.md).**
> This document proposed fixing stale-marker correlation *forensically* inside `correlate()` —
> reconstructing the live transcript at death-time from timestamp handoff signatures and a
> conclude-signal gate. That approach was abandoned. Root cause: the marker's `session_id` is
> stamped once at launch and goes stale when `/clear` rotates the transcript to a new uuid+file.
> The fix is to keep the marker honest at runtime — a `SessionStart` hook rewrites `session_id=`
> to `basename(transcript_path)` on each rotation — so `correlate()` needs no change at all.
> Phase 2 Task 4 closes **as built**. The analysis below is kept for the evidence and the
> rejected-alternative record; do not implement it.

**Status:** RETIRED. Superseded by ADR 0003 (runtime marker maintenance via `SessionStart` hook).
The historical status was: design validated (behaviour approved by operator 2026-06-16), not yet
implemented — and it never will be in this form.

**Supersedes the assumption in:** `docs/design-plans/2026-06-12-crash-detection.md` correlation
strategy, and Phase 2 Task 4 (`correlate prefers exact session_id`), which made `session_id`
a precedence-0 DIRECT_MATCH on the mere existence of `<session_id>.jsonl`.

---

## The problem (verified, not inferred)

Phase 2's `correlate()` returns `DIRECT_MATCH(session_id)` whenever `<session_id>.jsonl`
exists. But a launch-time `session_id` can name a **stale ancestor** transcript, because a
logical conversation's live transcript can rotate to a new uuid mid-life.

Demonstrated live in this session (read-only diagnostic over `~/.claude/projects`, operator
consent):

- Process/session identity: `43e087fc-…`. Its transcript `43e087fc.jsonl` is **frozen at
  2026-06-14 21:11:17** (last write), carries an `isCompactSummary` record.
- The **actually-live** transcript is `57fcf857.jsonl` (contains this very conversation;
  first entry `2026-06-14T11:11:27Z`, i.e. 21:11:27 local — **10 s after** `43e087fc` went
  quiet), still being written.
- So `session_id` (`43e087fc`) ≠ live transcript uuid (`57fcf857`).

If this session crashed now, Phase 2 would `DIRECT_MATCH` `43e087fc.jsonl` (a 2-day-stale
file) with full confidence and never reach the mtime fallback — the operator would resume the
wrong, old session. The "highest-confidence" path is, after a rotation, confidently **wrong**.

### Two hard facts that constrain any fix

1. **No machine-followable cross-file link.** Of `57fcf857`'s 473 `parentUuid` records,
   **zero** point into `43e087fc`'s 1004 uuids; no `logicalParentUuid`; the ancestor's leaf
   uuid is never referenced. You cannot *follow* a session_id to its rotated continuation —
   there is nothing to follow. (There is also **no official JSONL schema** — issue tracker
   confirms it is reverse-engineered — so building on a presumed `session_id ↔ live-file`
   invariant is building on sand.)
2. **Same-cwd concurrency happens** (operator-confirmed). Several sessions can be live in one
   cwd with overlapping windows. So pure "freshest transcript in cwd" (cc-search-chats'
   `rank_sessions` philosophy) is **insufficient** — it would point every overlapping marker
   at the same file. `session_id` must remain the per-marker binding key.

### Prior art (verified locally)

`cc-search-chats/core/discovery.py::rank_sessions` is documented as a "crash recovery
heuristic": ranks by mtime DESC then size, **ignoring session_id continuity**. Confirms the
principle (don't trust `<session_id>.jsonl` as the live file) but does not solve per-marker
binding under concurrency — crash-recovery needs more.

---

## Validated behaviour (operator-approved)

Confident-or-borderline (hybrid):

- **Confident `DIRECT_MATCH`** only when `<session_id>.jsonl` is genuinely the session's *live*
  transcript.
- **Borderline / surface candidates** when the named file is stale, missing, or the session
  has rotated — never a confident pointer at a stale file. (Matches the existing
  `BORDERLINE/AMBIGUOUS` class.)

Freshness is the gate. A stale named-session can never again win as a confident match.

---

## Proposed mechanism (link-free, timestamp-only) — to refine in design-write + TDD

The only signals available are the marker (`session_id, cwd, started, pid, start_time,
boot_id`) and each transcript's (`uuid-filename, mtime, first/last-entry-ts, tail shape`).
No links. So detect rotation by the **handoff signature** in timestamps:

> A transcript `X` is a **stale ancestor** if some other transcript `Y` in the same cwd
> *picked up after `X` went quiet* — i.e. `Y.first-entry-ts >= X.last-entry-ts` (a handoff).
> The `43e087fc → 57fcf857` case is exactly this: `X.last = 21:11:17`, `Y.first = 21:11:27`.

This distinguishes **rotation from concurrency** without any link:
- **Rotation / handoff:** successor *starts after* the predecessor goes quiet
  (`Y.first >= X.last`) → predecessor is stale.
- **Concurrency:** sessions *overlap* (`Y.first < X.last`) → not a handoff; both can be live.

### Gate for the `session_id` (and `--resume`) direct-match

Accept `DIRECT_MATCH(uuid=session_id)` iff **all** hold:
1. `<session_id>.jsonl` exists in the cwd's project dir;
2. it was active during this session's life (`last-entry-ts >= started − clock-skew-grace`);
3. it is **not superseded** by a handoff successor in the same cwd (no `Y` with
   `Y.first-entry-ts >= <session_id>.jsonl.last-entry-ts`).

Otherwise (missing / pre-launch-stale / superseded) → **do not** confident-match; fall to the
temporal-window resolution, which yields a single `MTIME_MATCH` when one candidate clearly
overlaps the marker, or `AMBIGUOUS` (borderline, surface candidates) when several do.

**Open decisions for design-write (flag for review, do not hard-code from memory):**
- Exact clock-skew grace for the handoff test (reuse `_CLOCK_SKEW_GRACE_SECONDS = 60`?).
- Whether "supersession" should require the successor to also be plausibly the *same* lineage
  (we have no link, so probably not — any post-quiet handoff in-cwd is enough to drop
  confidence to borderline, which is the safe direction).
- Multiple-handoff chains (A→B→C): does the gate need the *latest* leaf, or is borderline
  acceptable? (Borderline is the honest default.)
- Whether `last-entry-ts` or file `mtime` is the freshness signal (last-entry-ts is robust to
  touch/copy; reuse the existing forward-scan parser).

### Implementation approach (engineer's call, recorded)

**Surgical freshness-gate**, not a full rewrite: keep the `session_id → --resume → mtime`
ladder; add the freshness/handoff gate to the `session_id` and `--resume` DIRECT_MATCH
branches; stale/missing/superseded falls through to the existing mtime-window logic (which
already does temporal filtering + AMBIGUOUS). Smallest change that fixes the root; reuses the
tested mtime path.

---

## Re-plan scope (what this revision touches)

- **Design doc** `2026-06-12-crash-detection.md`: rewrite the correlation-strategy section;
  record this as a decision/ADR with the evidence above.
- **Phase 2 Task 4** (`correlate prefers exact session_id`): rework — the precedence-0
  unconditional direct-match becomes the freshness-gated match. Existing Task-4 tests
  (`test_correlate.py`) that assert "session_id present + jsonl exists → DIRECT_MATCH" must be
  revised to add the freshness/handoff condition, plus new RED→GREEN tests for the
  stale-ancestor and handoff cases (e.g. the `43e087fc/57fcf857` shape: stale named file +
  handoff successor → NOT a confident match → borderline/candidates).
- **Phase 1 `--resume` direct path** (`correlate.py`): same stale-ancestor risk; apply the
  same gate.
- **Phase 3** (`phase_03.md`): its tight-window justification — *"resumed sessions are handled
  by Phase 2's session_id/--resume direct path, so the lower bound is safe"* — is now
  conditional on the freshness gate; revise that note.
- **Wrapper / liveness / scan**: unchanged (the bug is in correlation, not the marker write or
  the start-time-checked liveness — those Phase 2 commits stand).

## Phase 2 close status

Paused at the coherence/refactor gates pending this revision. Already banked and unaffected:
wrapper `session_id`/`start_time` stamps, `pid_alive_checked`, scan PID-reuse rejection, the
seam guard (commits `17b2f3f`, `0506e4b`, `dc6d6e0`, `b445da1`). Only Task 4 (`62a2cf3`) is
reopened by this revision.

## What stays true regardless of the unresolved rotation *trigger*

We did not nail *why* the transcript rotated (compaction-appends-in-place per Tier-1 docs
conflicts with the observed two-file handoff; could be resume/restart or a remote-session
trait). The freshness-gate is robust to the trigger: it keys on "is the named file still the
live one," which is correct whether rotation comes from compaction, resume, or anything else.
