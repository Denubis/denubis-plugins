# Coherence Review: Phase 2b — Marker tracks the live transcript (SessionStart hook)

Reviewer: claude-opus-4-8
Date: 2026-06-17
Phase file: /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/crash-detection/docs/implementation-plans/2026-06-12-crash-detection/phase_02b.md
Design intent: docs/architecture/decisions/0003-marker-tracks-live-transcript-via-sessionstart-hook.md (ADR 0003); docs/design-plans/2026-06-12-crash-detection.md § Stage-1
Diff range: 368ca55..dafddbf

## Summary verdict

**Coheres.** The implementation matches ADR 0003's intent on every load-bearing point, the keystone claim ("`correlate()` unchanged, correct as built") is verified in code and guarded by tests, and the foundation supports the Phase 4 DR1/DR9 UAT. Findings are concentrated in one cluster: architecture docs outside the ADR still describe the marker as a static four-key write whose `session_id` matching is "planned," when in fact `session_id` is now a runtime-maintained, single-authoritative-writer field consumed by a shipped `correlate()` branch. Those are Medium documentation-staleness items, not implementation defects.

Gates verified green during this review:
- `bats tests/test_update_live_marker.bats` — 17/17.
- `bats tests/test_claude_wrapper_liveness.bats` — green (incl. new AC4.6 export test; the existing AC4.1/AC4.2/AC4.5/M1 wrapper contract stays green).
- `correlate.py` and the `crash_recovery` package are untouched in this diff (confirmed by `git diff --stat`).

## Conformance

Checked the implementation (`plugins/denubis-plan-and-execute/hooks/update-live-marker.py`, the wrapper export, `hooks.json`) against ADR 0003's "Decision" and "Hook contract (load-bearing)."

| ADR 0003 intent | Implementation | Conforms |
|---|---|---|
| Key off `transcript_path`, not stdin `session_id` | `update-live-marker.py:117` reads `payload.get("transcript_path")`; never reads `session_id`. A dedicated discriminating test (test #6) feeds distinct UUIDs and asserts the marker takes the transcript_path value. | Yes |
| Rewrite ONLY the `session_id=` line; preserve `cwd`/`started`/`argv`/`boot_id`/`start_time` and the PID-keyed filename verbatim | `rewritten_marker()` (`:58-69`) substitutes a single `^session_id=.*$` line via `count=1`; pure function. Tests #2 (byte-for-byte non-session_id remainder) and #3 (start_time byte-identical) pin this. | Yes |
| `start_time` preserved (drives `pid_alive_checked`) | Preserved by the line-scoped substitution; test #3 asserts `start_time=987654` is byte-identical post-rewrite. | Yes |
| Atomic write (`tmp` + replace) | `_atomic_write()` (`:72-92`) writes a same-dir `mkstemp` temp, then `os.replace`. Temp cleaned on error; marker mutated only by a successful replace. Test #14 asserts no temp residue. | Yes |
| No-op + exit 0 when `CR_LIVE_FILE` unset/missing | `main()` (`:98-103`) returns 0 before reading stdin when `CR_LIVE_FILE` is empty or not an existing file. Tests #7/#8/#9. | Yes |
| Never block session start; always exit 0 | Module guard (`:141-147`) converts any unexpected exception to a stderr diagnostic + `SystemExit(0)`. JSON-parse / OSError paths each return 0 with a diagnostic. Tests #12 (malformed JSON), #17 (`a&b` basename). | Yes |
| Never touch a marker outside `claudew` | The CR_LIVE_FILE gate + `marker.is_file()` check is the ownership guard; the hook never creates a marker. Test #9 asserts no creation of an absent marker/dir. | Yes |
| Multi-clear A→B→C ends at C | `count=1` substitution keeps exactly one `session_id=` line; test #5 runs the hook twice and asserts a single `session_id=C`. | Yes |
| Wrapper exports `CR_LIVE_FILE`; hook is a *second* SessionStart command | `claude-wrapper.sh:92` `export CR_LIVE_FILE=...`; `hooks.json` appends a second command after `session-start.sh`. New bats integration test confirms the child inherits the exported value. | Yes |
| `correlate()` unchanged; Phase 2 Task 4 closes correct-as-built | No change to `correlate.py` in the diff. The keystone "the matcher reads this field" is verified below (Traceability). | Yes |

**Drift (not erosion), benign:** ADR 0003 and the design plan describe the implementation as a bash hook with a one-line `python3` JSON extraction; the shipped artifact is `update-live-marker.py`, pure stdlib Python. This is a recorded, deliberate evolution (phase_02b.md Task 1 "REVISED 2026-06-17"; commit 96c3ace), not silent drift — the `sed`-replacement bred a `&`-expansion corruption bug (commit cbda210 added a hex shape-guard crutch) and the Python rewrite eliminated the whole `sed`-injection class. The contract is preserved verbatim. **The ADR body and the design plan still say "bash hook" / `.sh`** and were not updated to reflect the Python form. See Architecture Doc Updates (M3).

**Naming divergence, cosmetic:** the phase file's `## Acceptance Criteria Coverage`, Task 1 `Files:`, and Task 2 reference `update-live-marker.sh`; the shipped file is `.py`. Task 1's REVISED note corrects this inline, and commit 3c22114 fixed the stale `.sh` in the wrapper comment, but the rest of the phase file body still says `.sh`. Harmless to the running system (hooks.json invokes the right path), but the phase file is internally inconsistent.

## Traceability

The load-bearing chain is **Decision (ADR 0003) → hook writes `session_id=` → `correlate()` reads it as the highest-confidence match → Phase 4 surfaces that session as the crash victim.** Each link verified:

1. **Decision → Code (write side):** `update-live-marker.py` rewrites `session_id=basename(transcript_path)`. Guarded by `tests/test_update_live_marker.bats` (17 tests). Verified green.

2. **Code → Code (the keystone — does the matcher *read* the field the hook writes?):** **Verified.** `correlate.py:224-234` is an explicit "0. Exact session_id match (Phase 2)" branch that runs *ahead of* the argv `--resume` branch (`:236`): when `liveness.session_id is not None and project_dir is not None`, it lowercases the id, confirms `<sid>.jsonl` exists, and returns `DIRECT_MATCH(sid)`. The hook maintains exactly the field this branch consumes. The ADR's "correlate() needs no change … the bug was a stale input, not the matcher" is true as built.

   *Why this needed explicit checking:* three docs told three different stories about what the exact match keys off — design-plan Stage-1 (line 83) says "by `session_id` recorded in the marker," glossary line 26 says `DIRECT_MATCH (argv --resume <uuid>)` with no session_id field, and crash-recovery 0-context (lines 56, 96) labels session_id matching "**Planned**." That conflict is the CLAUDE.md HALT trigger and a near-replay of the recorded Phase-1 Critical (schema value taken from docs/memory instead of the authoritative file). Reading `correlate.py` resolves it: the code is authoritative, the divergent docs are stale (M1).

3. **Code → Test (read side):** `tests/test_correlate.py` ties the marker's `session_id` to `DIRECT_MATCH` end to end:
   - `test_correlate_direct_match_via_session_id_without_resume` (AC4.3, `:182`) — session_id set, argv lacks `--resume` → DIRECT_MATCH; also pins case-insensitive lowercasing.
   - `test_correlate_session_id_beats_resume_uuid` (`:221`) — session_id=A AND `--resume B` both resolvable → A wins. **This is the test that would break if branch 0 were removed or reordered** — the decision is guarded, not merely implemented.
   - `test_correlate_session_id_missing_jsonl_falls_through_to_mtime` (AC4.4, `:249`) — no false match when the id's JSONL is gone.
   - `test_correlate_legacy_session_id_none_unchanged` (`:281`) — legacy markers (no session_id) behave as before (forward-only consequence guarded).

4. **Decision → Documentation:** the design plan § Stage-1 (lines 46, 83, 85, 115) is fully rewritten and coherent with ADR 0003. The other architecture docs are stale — see Architecture Doc Updates.

**No new candidate fitness functions.** Every coherence concern in this phase that is automatable is already a test: the write side (17 bats), the read side (4 pytest), the precedence (the "beats_resume" test). The one thing units cannot prove — that Claude Code's real `SessionStart` runtime payload carries the `transcript_path` we expect on the `resume` path — is correctly deferred to UAT (next section); it is not unit-automatable and should not be filed as a recurring review item.

## Baked-In Assumptions

Decisions the implementation made where ADR 0003 was silent. Most are sound defaults; surfaced for confirmation.

- **Mode preservation via chmod-before-replace.** *ADR said:* "write atomically (`tmp` + `mv`)" — silent on permission bits. *Implementation chose:* `_atomic_write` captures `os.stat(marker).st_mode` and `os.chmod`s the temp to it before `os.replace` (`:80,85`), because `mkstemp` creates 0600 and the inode swap would otherwise silently narrow the wrapper's mode. **Rating: benign.** It restores parity with the old bash `mv`-of-redirected-temp behaviour and is pinned by test #15. Surfaced because it is a correctness-relevant decision the ADR did not anticipate; it matches intent.

- **UUID-regex as the no-op gate (and the `a&b` defence).** *ADR said:* key off `basename(transcript_path)`; silent on validating its shape. *Implementation chose:* a strict 8-4-4-4-12 hex `_UUID` regex (`:44-47`); a non-match → diagnostic + no-op exit 0 (`:123-125`). This is the principled replacement for the retired `sed` hex shape-guard crutch and makes `a&b.jsonl` a clean rejection. **Rating: notable.** It is correct for Claude Code's UUID-named transcripts, but it is a *hard* assumption that the live transcript basename is always a canonical UUID. If Claude Code ever names a transcript with a non-UUID stem, the hook silently no-ops (the marker stays on the prior transcript) — a stderr diagnostic is emitted, but triage would then misdirect exactly as the pre-2b bug did. The assumption is reasonable on today's evidence (the RED-before-build probe and the diagnostic observed UUID names) and the diagnostic provides a forensic trail; worth the human knowing it is load-bearing on Claude Code's naming convention.

- **The hook fires globally and no-ops unless `CR_LIVE_FILE` is set.** *ADR said:* "never touch a marker outside `claudew`." *Implementation chose:* registration as an unconditional second SessionStart command for *every* session; the CR_LIVE_FILE gate is the sole thing that makes non-claudew sessions a no-op (`:98-100`, checked before stdin is read so silent paths stay silent). **Rating: benign.** This is the correct mechanism given hooks.json cannot scope a command to claudew-launched sessions; the gate is the ownership boundary and is tested (#7). Surfaced because it means the hook executes a `python3` process on every SessionStart of every session in this plugin's scope — a small, bounded cost the ADR did not call out.

- **Two-writers relationship: wrapper bootstrap stamp + runtime hook.** *ADR said:* the hook is "the single authoritative writer of the live uuid" and the wrapper's derivation is "reduced to a one-shot bootstrap stamp." *Implementation chose:* to keep the wrapper's full `CR_SESSION_ID` derivation block intact (`claude-wrapper.sh:110-137`) and only add `export` — so the wrapper still writes a bootstrap `session_id` at launch, and the hook overwrites it on the first SessionStart. **Rating: benign, but worth stating precisely.** There are two writers of the `session_id=` field, not one: the wrapper writes it once before any SessionStart fires (keeping the marker valid in the window before the hook runs), and the hook is authoritative thereafter. The ADR's "single authoritative writer" is true for steady state but not literally for the launch instant. phase_02b.md Task 2 makes this explicit ("the wrapper bootstrap keeps the marker valid before the first SessionStart fires"), so it is recorded intent, not a hidden divergence. The wrapper's bootstrap tests remain load-bearing and stay green.

- **`resume` path written-but-unprobed.** *ADR said:* the hook fires on `startup`/`resume`/`clear`/`compact`. *Implementation/plan chose:* the RED-before-build probe exercised `startup` and `clear` only; `resume` was not probed (phase_02b.md RED note; uat-requirements addendum). **Rating: notable — but honestly recorded** (see Forward Fitness). The hook treats all four sources identically (it never reads `source`), so there is no code-path divergence; the open question is purely whether Claude Code's `resume` payload carries `transcript_path` in the shape the hook expects, which is a runtime fact only UAT can confirm.

## Forward Fitness

**Phase 4 (the DR1/DR9 human-judgment UAT surface) — fit confirmed.** Phase 4 routes `hard_crash → SectionKey.PROBABLE_CRASH_VICTIMS` and renders `claudew --resume <full-uuid>` where the uuid comes from the correlated session (phase_04.md Task 4, lines 147, 151). "The crash flag lands on the *right* session" reduces entirely to "`correlate()` returns DIRECT_MATCH against the marker's `session_id`, and that id names the live (post-clear) transcript." Phase 2b makes the id name the live transcript; `correlate.py` branch 0 turns it into the DIRECT_MATCH; Phase 4 surfaces that uuid. The chain is closed. A hostile reviewer's strongest line — "you proved the hook writes the field but not that the renderer surfaces *that* session" — is answered by the branch-0 precedence in `correlate.py` plus the `session_id_beats_resume` test: the session_id path is highest-confidence and wins over argv, so Phase 4's resume line carries the hook-maintained uuid.

**Phase 3 (tight-window note) — strengthened, not broken.** phase_03.md Task 2 (lines 92, 95) keeps "the `session_id`/`--resume` direct paths (Phase 2) ahead of all this" and justifies the tight window's lower bound by "Resumed sessions, whose first-entry-ts predates `started`, are handled by Phase 2's `session_id`/`--resume` direct path, not here." Phase 2b fires on `resume` and re-stamps `session_id` to the live transcript, so the direct path that this note relies on is *more* reliably correct after 2b, not less. The note's premise holds. No revision required for validity; the only nuance is that the note now leans on the hook keeping the resume-session id honest — which is the very thing folded into the DR1/DR9 UAT.

**Phase 5 (prune) — composes cleanly.** phase_05.md Task 1 (lines 62-63) reaps a dead marker via `lv.session_id`, skipping markers whose session_id is "absent or not a UUID," and reaps only when the correlated row is `concluded`/`hard_crash`. Phase 2b guarantees `session_id` is either a bare canonical UUID (the regex enforces it) or the wrapper's bootstrap value — never a corrupted token — so Phase 5's "is it a UUID" gate composes without surprise. One interaction worth surfacing (benign): after a `/clear`, the marker's `session_id` names the *post-clear* live session, so Phase 5 reaps the marker keyed to the live session's outcome; the abandoned pre-clear transcript is never marker-referenced and is handled by the jsonl-only/orphan sweep, not by marker reaping. That is consistent with ADR 0003's model and with Phase 5's "uncorrelated markers are never reaped" guard.

## Situated Accountability

This phase touches a domain concept (which session is "the live one" / which is the crash victim), so the check applies.

**Whose perspective shaped it:** the operator who runs `claudew` interactively and uses `/clear` mid-session — the exact, named, operator-confirmed pain in ADR 0003 ("common and frustrating," worst on reboot). The design optimises for that operator: the crash flag follows their live work across rotation.

**Who/what bears unstated cost or is absent:**
- **The pre-export-wrapper / legacy-marker operator.** ADR 0003 records this as a forward-only consequence: sessions launched by a wrapper without the `export` get no `CR_LIVE_FILE`, so the hook no-ops and their markers keep the pre-2b behaviour. `test_correlate_legacy_session_id_none_unchanged` guards that they degrade gracefully rather than break. Honestly recorded; the absent party is named.
- **Any rotation triggered by a non-`SessionStart` event.** ADR 0003 "Negative/residual" notes this leaves the marker stale — "the same failure mode as today, not a new one." No such event is known. The residual is the boundary of the situated claim: the design knows *what it does not cover* and says so.
- **The non-UUID transcript-name future.** Not an operator, but an absent assumption: the UUID-regex gate assumes Claude Code's naming convention holds. If it changes, the hook silently no-ops (with a stderr diagnostic). Surfaced under Baked-In Assumptions; the perspective absent here is "a future Claude Code release that names transcripts differently."

Nothing in this phase encodes a hidden value judgment about "usual" operator input in the way a validation rule would; the input it judges is a machine-generated path, and the one shape-assumption it makes is named and diagnostic-logged.

## Architecture Doc Updates

Architecture docs exist (`docs/architecture/{constraints,glossary,README}.md`, `docs/architecture/plugins/*/0-context.md`, ADR directory). A grep across all of them for `update-live-marker`, runtime `session_id` maintenance, `SessionStart`-marker coupling, or `ADR 0003` returns **nothing outside ADR 0003 itself**. Phase 2b introduced a structural change — the marker's `session_id` is now a runtime-maintained, hook-owned field, and a second SessionStart command exists — that no architecture doc reflects. Specific proposed updates (do not auto-apply; for human decision):

- **M1 (Medium) — `docs/architecture/glossary.md`.** Line 22 ("Liveness file") lists required keys `cwd`/`started`/`argv`/`boot_id` and attributes the writer to "Phase 8," with no mention that `session_id` is runtime-maintained. Line 26 ("CorrelationKind") describes `DIRECT_MATCH` as "argv `--resume <uuid>` resolved on disk … prefers argv-direct-match" — which is now **wrong by precedence**: `correlate.py:224` makes the `session_id` exact match the *highest-confidence* branch, ahead of argv. Proposed: add `session_id` (runtime-maintained by the `update-live-marker.py` SessionStart hook, ADR 0003) to the liveness-file entry; correct the CorrelationKind entry to state the precedence order (session_id exact → argv `--resume` → mtime/tight-window).

- **M2 (Medium) — `docs/architecture/plugins/denubis-crash-recovery/0-context.md`.** Lines 56 and 96 label "Stage-1 exact `session_id` match" as "**Planned** (Phase 2)" and line 39 calls `session_id`/`start_time` "(planned)." These shipped in Phase 2 and are consumed by `correlate.py` branch 0 today; Phase 2b completes the picture by keeping the field honest at runtime. Proposed: move session_id matching from "Planned" to shipped, and note the runtime-maintenance hook (ADR 0003) as the reason the exact match stays *correct*, not merely exact.

- **M3 (Medium) — `docs/architecture/plugins/denubis-plan-and-execute/0-context.md` + a paired constraint row.** The hooks table (line 108) lists only `session-start.sh` under SessionStart; the new `update-live-marker.py` command is absent. The wrapper entry (line 116) describes the liveness write as four keys with no mention of the export or the hook. Proposed: add the `update-live-marker.py` hook row (SessionStart, `suppressOutput`, keeps `.live` `session_id` on the live transcript per ADR 0003) and note the `CR_LIVE_FILE` export. Per the ADR README's own guidance ("ADRs may pair with a constraint row that locks the same decision in code"), ADR 0003's load-bearing hook contract has **no paired constraint row** in `constraints.md`; the existing "Liveness file four-key format" (line 49) and "Writer-side liveness lifecycle (Phase 8)" (line 68) rows now describe an incomplete marker. Consider a constraint row: "Live-transcript marker maintenance — the `session_id=` line is rewritten to `basename(transcript_path)` on every SessionStart; only that line changes; pinned by `test_update_live_marker.bats`."

- **M3 also covers** the ADR body itself: ADR 0003 and design-plan § Stage-1 still describe the hook as bash with a `python3` one-liner. The shipped artifact is pure stdlib Python (commit 96c3ace). The ADR's contract is still accurate; only the implementation-form sentence is stale. A one-line addendum to the ADR ("implemented as stdlib `update-live-marker.py`, not bash/`sed` — see phase_02b Task 1 revision") keeps the audit trail honest.

- **Low — ADR status / index.** ADR 0003 is correctly "Proposed (moves to Accepted after DR1/DR9 UAT)." The decisions `README.md` has no per-ADR index table (it never did), so 0003's absence from an index is not a regression — noted only for completeness.

These are documentation-staleness items. None blocks the phase; all are routine maintenance-architecture work and several (M1 line 26, M2 "Planned" labels) predate Phase 2b — they were already stale after Phase 2 shipped session_id matching, and 2b makes the staleness more visible.

## Findings Summary

### High (count: 0)
- None. The keystone risk (matcher ignores the hook-written field → 2b misses its purpose, Phase 4 surfaces by argv) was investigated directly in `correlate.py` and **falsified**: branch 0 reads `session_id` ahead of argv, guarded by `test_correlate_session_id_beats_resume_uuid`.

### Medium (count: 3)
- **M1 — glossary.md CorrelationKind entry is wrong by precedence** and the liveness-file entry omits runtime-maintained `session_id`. `DIRECT_MATCH` is described as argv-keyed; the code makes session_id the highest-confidence branch. Documentation will erode silently against the code.
- **M2 — crash-recovery 0-context.md labels session_id matching "Planned"** when it shipped in Phase 2 and is consumed today; 2b completes it. Stale phase-status.
- **M3 — plan-and-execute 0-context.md omits the `update-live-marker.py` hook and the `CR_LIVE_FILE` export; no paired constraint row exists for ADR 0003's hook contract; the ADR body still says "bash hook."** The largest structural change of the phase is undocumented outside the ADR.

### Low (count: 2)
- Phase file (`phase_02b.md`) is internally inconsistent: Task 1 REVISED note and hooks.json use `.py`, but the AC-coverage section, Task 1 `Files:`, and Task 2 still say `update-live-marker.sh`.
- ADR 0003 absent from a decisions index (no index table exists; not a regression).

### Notable baked-in assumptions for human confirmation
- UUID-regex gate is load-bearing on Claude Code's transcript-naming convention; a non-UUID name → silent no-op (diagnostic logged), reintroducing the pre-2b misdirection for that session.
- `resume`-path payload shape is written-but-unprobed (folded into DR1/DR9 UAT, honestly recorded).

## Overall Assessment

**Coheres.** The implementation matches ADR 0003 on every load-bearing point; the keystone ("correlate() reads the hook-maintained `session_id`, correct as built") is verified in `correlate.py:224-234` and guarded by a precedence test that would break if the decision were reversed; the foundation is forward-fit for Phase 4's DR1/DR9 UAT, strengthens (does not break) Phase 3's tight-window note, and composes cleanly with Phase 5's prune. The end-to-end "`/clear` → crash → triage points at the live session" claim is honestly scoped to UAT, not asserted by units, and the `resume`-path probe gap is recorded in the uat-requirements addendum rather than hidden.

The only required follow-up is documentation: three Medium architecture-doc updates (M1-M3) to bring `glossary.md`, both `0-context.md` files, and a paired constraint row into line with the now-shipped runtime-maintained `session_id` — best handled as a single maintain-architecture pass, partly cleaning up staleness that predates this phase. Two Low items (phase-file `.sh`/`.py` inconsistency; ADR index) are cosmetic. No implementation change is required to proceed.
