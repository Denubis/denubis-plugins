# Coherence Review: Phase 8 — Wrapper patch in denubis-plan-and-execute and version coordination

Reviewer: Claude Opus 4.7
Date: 2026-05-20
Phase file: /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/crash-recovery/docs/implementation-plans/2026-05-08-crash-recovery/phase_08.md
Design plan: /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/crash-recovery/docs/design-plans/2026-05-08-crash-recovery.md
Diff range: d3ec33f..451bf3b
Architecture docs: /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/crash-recovery/docs/architecture/

## Conformance

The implementation conforms to the design's architectural intent, with two surfaced plan defects (already disclosed by the orchestrator) and one structural addition that the design plan did not anticipate.

**Matches design intent:**
- Liveness writer block (claude-wrapper.sh:89–101) writes the four mandated keys (`cwd`, `started`, `argv`, `boot_id`) atomically via `tempfile + mv`, exactly as specified in DR2, DR7, the "Liveness file format" data-model section, and AC5.1.
- Conditional cleanup block (claude-wrapper.sh:140–147) gates on `EXIT_CODE -eq 0 || EXIT_CODE -eq 130` rather than `trap EXIT` — DR8 verbatim.
- Version coordination matches the contract: `denubis-plan-and-execute` 2.32.1→2.32.2, `denubis-crash-recovery` 0.1.0→1.0.0, marketplace.json synced, two CHANGELOG entries in expected order (crash-recovery first, plan-and-execute second). AC8.2/AC8.3 satisfied.
- UAT runbooks for AC5.6 and AC6.4 render with "Expected observation" lines as the phase template required.

**Erosion findings: none.** The wrapper's `set -euo pipefail` interaction (line 33) caused the original phase plan's "no `exec` to replace, EXIT_CODE=$? capture at line 89–90" claim to be wrong: under `set -e`, a non-zero `claude` exit would have aborted the wrapper before reaching either the transcript-archive block or the new cleanup block. This was a **plan defect**, not erosion — the implementation correctly added `|| EXIT_CODE=$?` and a `${EXIT_CODE:-0}` default to preserve the intended contract. Disclosed in orchestrator context and queued for an implementation-time ADR in Stage 1.

**Drift findings: one structural, several documentary.**

1. **Drift (structural):** The phase plan in Block B (line 77) said "insert immediately BEFORE `exit $EXIT_CODE` at line 121" — i.e. cleanup runs *after* the transcript-archive prompt regardless of exit code. The shipped implementation instead **gates the entire transcript-archive prompt on `EXIT_CODE -eq 0`** (claude-wrapper.sh:109) and the cleanup block sits outside that gate. This means: on a non-zero exit, the transcript-archive prompt is now skipped entirely; on a clean exit, the prompt still fires and *then* cleanup runs. The phase plan was silent on whether the transcript-archive prompt should fire on abnormal exits — see Baked-In Assumption #1 below. Code review found this (Minor #1) and accepted the resolution as APPROVED.

2. **Drift (documentary):** The phase file's bats template used `REAL_CLAUDE` as the stub-binary env-var, but the wrapper's actual external knob is `CLAUDE_REAL_BINARY` (introduced 2026-04-29 in commit 31e42d0, predating the phase plan by ~10 days). Implementor corrected in-line. Disclosed in orchestrator context; queued for an implementation-time ADR in Stage 1.

3. **Drift (naming):** The design plan's AC5.5 narrative describes "the wrapper exits with non-zero status" when Claude is killed independently. The bats lifecycle suite tests Claude exits 137/139/1 but does not exercise the "Claude killed mid-run while wrapper is alive" path explicitly — it only tests "Claude returned exit code X." This is a faithful subset (the wrapper sees only the exit code regardless of how Claude died), but the bats test names use "Claude exit 137 (SIGKILL)" framing which is slightly different from AC5.5's "Claude is killed independently of the wrapper." Behavioural equivalence holds; naming is honest enough. **Low** — note for completeness, not an action item.

## Traceability

| Design decision | Code | Test | Doc |
|---|---|---|---|
| DR2 (PID-keyed liveness file) | claude-wrapper.sh:92 `CR_LIVE_FILE="$CR_RUN_DIR/$$.live"` | test_claude_wrapper_liveness.bats AC5.1 + AC5.4 | CHANGELOG 2.32.2 entry; README Troubleshooting writer-side section |
| DR7 (boot_id in liveness file) | claude-wrapper.sh:98 `printf 'boot_id=%s\n' "$(cat /proc/sys/kernel/random/boot_id …)"` | test_claude_wrapper_liveness.bats AC5.1 (matches `$(cat /proc/sys/kernel/random/boot_id)`) | CHANGELOG 2.32.2 Compatibility cell; README AC5.6 UAT runbook |
| DR8 (conditional cleanup by exit status, NOT `trap EXIT`) | claude-wrapper.sh:140–147 with cite-comment | test_claude_wrapper_liveness.bats AC5.2 (×2), AC5.3, AC5.5 (×3), AC5.4 | CHANGELOG; phase file Task 1 Block B; README troubleshooting |
| Atomic tempfile + rename | claude-wrapper.sh:99–100 `mv "$CR_LIVE_TMP" "$CR_LIVE_FILE"  # atomic via rename(2) on the same filesystem` | test_claude_wrapper_liveness.bats "no .tmp residue after clean completion" | README troubleshooting wrapper-side entry on orphaned `.tmp` files |
| DR3 (patch wrapper directly, version-bump both plugins) | plugin.json + marketplace.json + CHANGELOG bumps | tests/test_crash_recovery_smoke.bats AC8.1 grep test (locks dependency text) | CHANGELOG entries (both plugins) |
| Writer/reader separation (design plan §Architecture point 1) | Writer = wrapper. Reader = `crash-recovery scan` (Phase 4 code unchanged here). | Writer-side: bats lifecycle. Reader-side: existing test_scan.py and test_liveness.py. | README "Wrapper-side failure modes" subsection (writer); existing reader troubleshooting unchanged |

**Gaps:**

- **DR7 boot_id → architecture doc:** `constraints.md`'s "Boot-aware liveness" row (line 48) still ends "Reboot UAT deferred to Phase 8." The UAT now exists (README AC5.6) but `constraints.md` was not refreshed by Phase 8. Likewise the "Liveness file four-key format" row (line 49) ends "Writer side lands in Phase 8." — this is now true but undocumented. **Routes to Stage 1.**
- **DR8 conditional cleanup → architecture doc:** `constraints.md` has no row for the writer-side liveness-lifecycle contract. The DR8 rationale lives only in the wrapper's inline cite-comment plus the CHANGELOG. A new "Writer-side liveness lifecycle (Phase 8)" constraint row would lock the four-mode behaviour (write at start, retain on 1/137/139, remove on 0/130, remove unaffected by transcript-archive prompt because that block is now gated on exit 0). **Routes to Stage 1.**
- **`set -e` + `|| EXIT_CODE=$?` interaction → ADR + doc:** No architecture/constraints row captures *why* the wrapper now uses `|| EXIT_CODE=$?` instead of bare `EXIT_CODE=$?`. Without that, a future cleanup pass could "simplify" the line back to bare `EXIT_CODE=$?` and silently re-introduce the bug. Already scheduled as an implementation-time ADR in Stage 1; the constraint-doc row should pair with that ADR.
- **AC5.6 / AC6.4 UAT deferral:** The orchestrator context records that AC5.6 (post-reboot) and AC6.4 (idle-kill) are mechanical integration-tests-by-hand that have been deferred to live operation, and notes two real-crash empirical verifications (2026-05-18, 2026-05-20). This is a **recorded decision**, not a gap — but the recording currently lives only in the orchestrator's task list and this review. **Routes to Stage 1** for an explicit decision-record entry, or for the README to add a short "UAT verification status" note alongside the runbooks.

**Candidate fitness functions / test-requirements entries:**
- The CHANGELOG 2.32.2 entry claims "On clean exit (status 0) or Ctrl-C (status 130), the file is removed." This is verified by bats AC5.2 (×2). Already a fitness function.
- The CHANGELOG 2.32.2 entry claims "Any other exit status leaves the file in place." Verified by bats AC5.5 (×3, codes 1/137/139). Already a fitness function.
- **Missing fitness function:** there is no automated test asserting that the *transcript-archive prompt does not fire on non-zero exit*. The new exit-0 gate is a behaviour change to plan-and-execute users (an abnormal exit no longer prompts for transcript archival). A bats test like "Claude exit 1 does not emit the 'Press Enter to archive' prompt" would lock the gate. Recommend adding to `test-requirements.md` (the post-implementation step the orchestrator already has scheduled). **Severity: Medium** — this is the exact spot where a future refactor could silently flip the contract.
- **Missing fitness function:** no test asserts that the wrapper writes a liveness file *before* `claude` is invoked (timing-sensitive but matters for AC5.3 when claude is short-lived). The AC5.3 bats test uses a sleeping stub and asserts the file exists "pre-kill"; that catches the gross case but the structural guarantee is in the ordering of lines 89–103. Could be locked via grep-based structural test: `grep -B 5 '"$REAL_CLAUDE"' claude-wrapper.sh` must show the `mv` line above. **Severity: Low** — structural ordering is highly visible and unlikely to drift unnoticed; not worth adding.

## Baked-In Assumptions

### Assumption #1 — Transcript-archive prompt gated on EXIT_CODE -eq 0 (concerning → notable, resolved as accepted)

- **Design said:** silent. The phase plan said the cleanup block goes "immediately BEFORE `exit $EXIT_CODE` at line 121" with the explicit rationale that the cleanup must NOT run before the user-blocking transcript prompt so that a `kill -9` during the prompt leaves the liveness file in place. The phase plan was silent on whether the transcript prompt itself should fire on abnormal exit.
- **Implementation chose:** Wrap the entire transcript-archive block (including the `IS_RESUMED` reminder) in `if [[ "$EXIT_CODE" -eq 0 ]]; then … fi`. This means: a Claude exit-code 1 / 137 / 139 / etc. no longer prompts "Press Enter to archive transcript." The original wrapper's transcript-archive block ran regardless of exit code.
- **Rating:** **notable** (downgraded from concerning by Phase 8 code review's Minor #1 review-and-accept cycle).
- **Forward impact:** **Behaviour change to plan-and-execute users.** Pre-Phase-8, a Claude that crashed (exit 1, OOM-kill, segfault) would still prompt the user about archiving the partial transcript on a transcripting project. Post-Phase-8, those abnormal exits skip the prompt entirely. This is arguably *better* (a crashed session is unlikely to have a clean transcript worth archiving) but it IS a behaviour change that:
  1. is not called out in CHANGELOG 2.32.2 (which only describes the liveness-file additions, not the transcript-archive gating);
  2. has no automated test pinning it;
  3. could surprise users on a transcripting project who relied on the post-crash prompt as a recovery hook.
- **Recommendation:** Add a one-sentence note to the CHANGELOG 2.32.2 entry ("Side-effect: the transcript-archive prompt is now gated on clean exit only — abnormal exits skip the prompt"). Add the fitness function suggested in Traceability above. Route to Stage 1 for the ADR (the `set -e` ADR can absorb this as a paired consequence). **Severity: Medium** in the Findings Summary.

### Assumption #2 — `$*` argv joining instead of `$@`

- **Design said:** The phase plan's Task 1 explicitly chose `$*` (line 73) and gave the rationale ("explicit single-string semantics"). This was a *design-time* baked-in assumption that the implementation faithfully executed.
- **Implementation chose:** `printf 'argv=%s\n' "$*"` — preserves argv as a single space-joined string.
- **Rating:** **benign**.
- **Forward impact:** When `_extract_resume_uuid` (Phase 3) parses `argv=…` via `shlex.split`, a user passing `--resume "uuid with spaces"` (impossible for real UUIDs, but possible for adversarial cwds containing spaces) would round-trip incorrectly. The argv shows the joined form, not the original token boundaries. This is essentially the same problem the original Phase 3 design accepted. Not worsened.

### Assumption #3 — `boot_id=unknown` fallback on non-Linux (or `/proc` unreadable)

- **Design said:** The phase plan called out this fallback explicitly (Task 1 line 75) and provided the resolution logic for the reader side. Documented before implementation.
- **Implementation chose:** Exactly as designed.
- **Rating:** **benign**.
- **Forward impact:** None — already reasoned through in phase plan and README troubleshooting.

### Assumption #4 — Test #10 atomic-write test does not actually exercise a race

- **Design said:** silent on whether the atomic-write test should prove atomicity or merely the absence of residue.
- **Implementation chose:** Test 10 (renamed during code-review fix from "wrapper writes liveness file atomically via tempfile + mv (no .tmp residue)" to "no .tmp residue after clean completion") only asserts that no `.tmp` files persist after the wrapper completes. It does NOT race the wrapper against a reader to verify a reader never sees a half-written file. The rename-was-used assertion is purely structural (a `.tmp` file would only leak if the `mv` failed or the wrapper crashed between `>` and `mv`).
- **Rating:** **benign** — the code review fix (Minor #3 Part 2) acknowledged this and renamed the test to be honest about what it actually checks.
- **Forward impact:** None — the rename was a deliberate honesty fix.

### Assumption #5 — Per-PID file naming relies on no PID recycling within a single boot

- **Design said:** silent. DR2 says "wrapper's PID … per-invocation uniqueness" but does not address the PID-recycling-within-a-boot edge case (rare but possible on systems with PID-reuse pressure, e.g. machines starting hundreds of short-lived processes).
- **Implementation chose:** Just `$$.live`. If PID N exits (cleanly, removing its file), and then PID N is reassigned to a new wrapper later in the same boot, the new wrapper writes a fresh file at the same path. This is fine. The dangerous case is: wrapper PID N dies *abnormally* (file persists), and PID N is reassigned to a non-wrapper process, then to a new wrapper which writes a new file overwriting the old. The boot_id is the same for both files (same boot), so the reader has no way to tell that the file used to describe a different wrapper. The new wrapper's content is correct, but the old wrapper's casualty record has been overwritten.
- **Rating:** **notable**, very edge.
- **Forward impact:** On a typical desktop with PID space 32k+ and few short-lived processes, PID recycling between two wrapper sessions in the same boot is extremely unlikely (would require either thousands of intervening processes or an explicit fork-bomb). On a CI machine running many containers, more plausible. The mitigation is "live with it" — the new wrapper IS describing a real session, so the file is correct *now*; the old casualty record was lost. The reader still has the partial JSONL on disk for the lost session. **Severity: Low** — note for completeness; not worth adding a fitness function (the cost of detecting and disambiguating would exceed the rarity of the case).

### Assumption #6 — Wrapper-side smoke test does not exist as part of the bats suite

- **Design said:** silent on whether the wrapper itself should be invokable end-to-end against a real (or stub) claude binary in CI.
- **Implementation chose:** Bats lifecycle covers the liveness lifecycle behaviours but does NOT verify (a) that the wrapper continues to work for its non-liveness contract — `--disallowedTools`, `--teammate-mode=auto`, the transcript-archive prompt, the resume-detection logic — after the patch, or (b) that `denubis-plan-and-execute`'s normal "run claude" path is unchanged for users not using crash-recovery. The bats tests stub `claude` itself, so any wrapper-side argv-construction regression would not be caught.
- **Rating:** **notable**.
- **Forward impact:** The wrapper is a critical-path script for everyone who installs `denubis-plan-and-execute`, regardless of whether they install `denubis-crash-recovery`. A future refactor could break `--teammate-mode=auto` or the `SHOULD_TRANSCRIPT` branch without the bats suite noticing. **Severity: Medium** — recommend adding a bats test in `test-requirements.md` that verifies the wrapper correctly passes the `--disallowedTools` flag through to the stub claude (i.e. the stub asserts on its own argv). The Phase 8 work added wrapper-touching behaviour to a plugin many users depend on without expanding the test coverage of the wrapper's non-crash-recovery contracts.

## Forward Fitness

No future implementation phases — Phase 8 is the final one. Forward-fitness here means: **will this implementation support the system's live operation, and will it support the Stage 1 / Stage 2 / final code review / test analysis / critical peer review work that the orchestrator has queued?**

**Will support:**

- **Live operation as the crash detector.** The user's two recent real-world crashes (2026-05-18 Phase 7 dogfood, 2026-05-20 today) plus the deferred UAT decision (AC5.6/AC6.4) imply that the system will be tested in operation, not by re-running the formal UAT runbooks. The implementation supports this: the bats lifecycle suite covers every exit-code class deterministically; the next real crash will exercise AC6.4's idle-kill scenario for real; the next reboot exercises AC5.6 for real. This is a coherent posture given the orchestrator's stated "live operation" plan.

- **Final code review (pre-merge SCOPE).** The wrapper change is well-localised (one file, ~50 lines), inline-commented at the `set -e` decision point and the atomic-rename point, and the cite-comment to DR8 is present. A pre-merge SCOPE reviewer will be able to follow the chain plan → DR8 → comment → code → test.

- **Test analysis.** The bats lifecycle suite is structured with one assertion per AC (AC5.1, AC5.2 × 2, AC5.3, AC5.4, AC5.5 × 3, plus argv-verbatim and no-tmp-residue). Each test is named with its AC. The test analyst will find the mapping trivial.

**A hostile reviewer would flag:**

1. **The transcript-archive gate is a wrapper-contract change that ships unannounced.** Phase 8's stated scope was "land the liveness-tracking patch." The transcript-archive block being newly gated on `EXIT_CODE -eq 0` is a side effect of the `|| EXIT_CODE=$?` fix that affects users *not* installing crash-recovery. A hostile reviewer would say "you shipped a behaviour change to all plan-and-execute users in a CHANGELOG entry that only mentions liveness files." This is the strongest finding and ties to Baked-In Assumption #1. **High** severity if you accept the framing that wrapper contract changes warrant explicit CHANGELOG callouts; **Medium** if you accept that the gate is a defensible improvement that the code-review pass accepted.

2. **The "Phase 8 done when" criterion "Manual UAT script in README is runnable and documented" is met by writing the runbook, but the orchestrator context records the actual UAT verification has been deferred to live operation.** A hostile reviewer would want to see this deferral as an explicit decision-record entry, not as a footnote in an orchestrator message. The user has already empirically verified through two real crashes — but that empirical evidence is not yet linked to the AC5.6/AC6.4 records anywhere a future maintainer would find it.

3. **The wrapper smoke-test gap (Assumption #6).** A reviewer looking at "what could break silently" would identify that the wrapper's non-crash-recovery contracts are now unprotected.

4. **The boot_id reader path has no current test against the writer's new live-file output.** Phase 3 tests boot_id parsing against synthetic liveness files. Phase 8 writes real liveness files. There is no integration test that wires the two: write a real file via the wrapper, then read it via `crash_recovery.liveness.read_liveness()`. The bats AC5.1 test verifies the file format from the shell side; pytest tests verify the parser against fixtures. There is no test bridging the two. **Medium** — recommend adding to test-requirements.md as a writer-output → reader-input round-trip test.

## Situated Accountability

This phase touches the writer side of a contract that the rest of the design plan presumes — and the writer's *exit-code policy* is a domain-encoding decision about which kinds of session death "count." That makes situated accountability a live concern, not a checkbox.

**Whose perspective shaped the wrapper's exit-code policy?**

- The DR8 design decision was framed by the user's own debugging journey (two real crashes on this user's machine; a "five sessions lost on 2026-05-18" event that surfaced the post-mortem-detection limitation now captured in the design seed). The policy "clean exit removes the file; everything else preserves it" is shaped by the user's experience of how Claude dies on the user's machine: SIGKILL from OOM, SIGSEGV from internal crashes, generic non-zero from network failures. The 130-allowlist captures the user's specific Ctrl-C habit.

- The transcript-archive gate added in Phase 8 is shaped by the implementor's perspective on which exit codes are "worth prompting about." The user's Phase 7 dogfood proved that crashed sessions matter — but the implementor's choice was to *not* prompt about the transcript on abnormal exit. This may be correct, but it was decided silently. The user-as-end-user is the absent perspective on this gate.

**Who bears costs that are not visible in the code?**

- **Users on non-Linux hosts** who install `denubis-plan-and-execute` (for its design/execute/transcript-archive features) but cannot install `denubis-crash-recovery` (Linux-only) still get the wrapper-side liveness-write code. The `boot_id=unknown` fallback means their `~/.claude/run/` accumulates files they cannot scan. The README troubleshooting "Liveness-file write permission errors" entry helps but does not mention "macOS users: this directory will accumulate files you cannot scan; you may want to periodically clear it manually."

- **Users with multiple home directories or NFS-mounted homes** bear the cost that the wrapper writes to whatever `CRASH_RECOVERY_RUN_DIR` resolves to in *its* environment, which may not match the scan-time `CRASH_RECOVERY_RUN_DIR`. The README troubleshooting entry covers this. Acceptable.

- **Users who use the transcript-archive feature on a crash-prone project** lose the post-abnormal-exit transcript prompt. Cost is borne silently.

**What's absent?**

- **The post-mortem-crash perspective** (the "I crashed before installing the wrapper" case) was surfaced during Phase 7 dogfood and is explicitly out of scope for Phase 8 with a design seed at `docs/design-plans/2026-05-19-post-mortem-crash-detection.md`. This absence is *recorded*. Good.

- **The "new user installs both plugins, then crashes before the wrapper has ever run" perspective** — first-launch case. Wrapper has never written a liveness file, no `.live` files exist, first crash is invisible to crash-recovery. README's "Currently unfinished" section mentions retroactive recovery limitations; the orchestrator notes this is captured. Acceptable.

- **The "user runs the wrapper without crash-recovery installed" perspective** — also recorded in CHANGELOG 2.32.2 Compatibility cell ("the wrapper itself runs cross-platform … the wrapper-side fallback exists so that the plugin remains usable on macOS / BSD for the rest of its features"). The transcript-archive gate change is the one user-visible impact this doesn't address.

- **The "implementor's perspective from 2026-05-13" vs "reality at 2026-05-20" mismatch.** The phase plan was written assuming wrapper line numbers and `set -e` behaviour that turned out not to match. Two plan defects already surfaced. A third may exist that wasn't surfaced because tests pass. **Severity: Low** — both plan defects are scheduled for Stage 1 ADRs. The pattern (stale plan → re-verify before implementing) is captured.

## Architecture Doc Updates

Phase 8 has not yet touched architecture docs. Per the orchestrator context, these are queued for Stage 1. The coherence review's role is to validate the scheduling is sufficient and to flag the specific updates needed.

**Scheduled (orchestrator context — Stage 1):**

1. `docs/architecture/plugins/denubis-crash-recovery/0-context.md` — author from scratch (deferred Phase 7 M3). Author as a thin overview: purpose, public surface (CLI subcommands + triage skill), key modules, environment variables, dependencies (sibling-plugin wrapper), pointers to design/implementation plans.

2. `docs/architecture/README.md` — bump "Plugin Contexts (14)" to (15) once 0-context.md lands.

3. `docs/architecture/constraints.md` — Phase 7 L3 deferred item: tighten "Deterministic classification" verification cell to cite `test_classify.py::test_every_rule_classifies_its_fixture`.

4. `docs/architecture/constraints.md` — Phase 2 situated-accountability anchor: add "Crash-Recovery bookkeeping deny-list re-sampling cadence" row.

**Coherence review adds to the Stage 1 list:**

5. `docs/architecture/constraints.md` — flip "implemented through Phase 7" header (line 40) to "implemented through Phase 8" once Stage 1 lands. Add a new constraint row "Writer-side liveness lifecycle (Phase 8)" with these requirements: writes `~/.claude/run/$$.live` at startup atomically; retains the file on exit codes ≠ 0 and ≠ 130; removes on exit codes 0 or 130; the cleanup is unaffected by whether the transcript-archive prompt fires. Verification: bats lifecycle suite (cite test names). This locks the four-mode contract.

6. `docs/architecture/constraints.md` — update the "Boot-aware liveness" row (line 48) — replace the trailing "Reboot UAT deferred to Phase 8" with a citation of README AC5.6 and a note that AC5.6/AC6.4 have been deferred to live operation. Update the "Liveness file four-key format" row (line 49) — replace "Writer side lands in Phase 8" with a citation of the wrapper code (claude-wrapper.sh:89–101) and the bats AC5.1 test.

7. `docs/architecture/constraints.md` — extend the Local-filesystem refusal row (line 52) — replace the trailing "Writer-side liveness guarantee (CA3) deferred to Phase 8" with the actual writer-side stance: the wrapper does NOT make the local-FS check by design; the reader-side guard catches the unsafe configuration. This is already documented in the CHANGELOG 2.32.2 Compatibility cell and the README troubleshooting; the constraint doc should match.

8. `docs/architecture/plugins/denubis-plan-and-execute/0-context.md` — add a brief mention of the liveness-file write block on `claude-wrapper.sh`, noting it depends on the boot_id reader in the sibling `denubis-crash-recovery` plugin. The existing 0-context.md describes the wrapper but does not call out this cross-plugin coupling.

9. **New implementation-time ADR (Stage 1 captures):** the `set -e + || EXIT_CODE=$?` decision. The constraint-doc row paired with this ADR should say: "The wrapper's main `claude` invocation must be followed by `|| EXIT_CODE=$?` (not bare `EXIT_CODE=$?`) and an `EXIT_CODE=${EXIT_CODE:-0}` default. The `set -euo pipefail` at line 33 would otherwise abort the wrapper on non-zero exits before the cleanup block runs. Discovered during Phase 8 implementation (2026-05-19); the original phase plan and code-review "wrapper structurally ready" assertion both missed this." Locked by bats AC5.5 (×3) tests.

10. **New implementation-time ADR (Stage 1 captures):** the bats env-var name correction. The constraint-doc row paired with this ADR should say: "Tests invoking the wrapper must use `CLAUDE_REAL_BINARY` (not `REAL_CLAUDE`). The wrapper's `claude-wrapper.sh:41` reads `CLAUDE_REAL_BINARY`. Phase 8's bats template referenced the wrong name; corrected in-line."

11. **Recommended Stage 1 doc addition:** add the AC5.6/AC6.4 UAT deferral as an explicit recorded decision — either in `docs/architecture/constraints.md` as a row, or in a new `decisions/` doc, or as a final paragraph in `docs/design-plans/2026-05-08-crash-recovery.md`. Stating: "AC5.6 and AC6.4 are mechanical integration-tests-by-hand (literal output match), not human-judgment items. They are deferred to live operation. Empirical verification has occurred via two real-world crashes (2026-05-18, 2026-05-20)." This converts a hallway decision into a document.

**Existing doc that this phase contradicts:** none. The Phase 7-era line "Reboot UAT deferred to Phase 8" in constraints.md (line 48) is *consistent with* Phase 8 having landed the UAT runbook; it just needs updating to reflect that Phase 8 is now done. Not erosion.

## Findings Summary

### High (count: 0)

None. All structural concerns have already been routed through code review and accepted, or are scheduled for Stage 1.

### Medium (count: 5)

- **M1 — Unannounced wrapper-contract change (Baked-In Assumption #1):** The transcript-archive prompt is now gated on `EXIT_CODE -eq 0`, which is a behaviour change for `denubis-plan-and-execute` users who do not install crash-recovery. CHANGELOG 2.32.2 should call this out; an automated test should lock it. Severity Medium because (a) it ships unannounced, (b) it has no test, (c) it could be silently flipped by a future refactor. *Action:* extend CHANGELOG 2.32.2 entry, add fitness function to test-requirements.md, capture in the Stage 1 `set -e` ADR.

- **M2 — DR8 writer-side contract has no architecture constraint row:** The four-mode writer-side liveness lifecycle is documented only in CHANGELOG, inline cite-comments, and the phase plan. A constraint row would lock it for future maintainers. *Action:* Stage 1 (item 5 above).

- **M3 — Writer-output → reader-input integration test gap:** Phase 3 tests the parser against synthetic files; Phase 8 writes real files via the wrapper; no test bridges the two. *Action:* add to test-requirements.md (Stage 1 / post-impl phase).

- **M4 — Wrapper non-crash-recovery contracts unprotected by the new bats suite (Baked-In Assumption #6):** The wrapper is a critical path for everyone who installs `denubis-plan-and-execute`; the new bats lifecycle covers the liveness paths only. A wrapper-argv-passthrough test would lock the `--disallowedTools` and `--teammate-mode=auto` contracts. *Action:* add to test-requirements.md.

- **M5 — AC5.6/AC6.4 UAT deferral is a hallway decision:** The orchestrator context records the deferral and the empirical evidence, but no design plan / architecture doc / README captures it. *Action:* Stage 1 — add to one of those three locations (item 11 above).

### Low (count: 3)

- **L1 — AC5.5 bats test naming uses "Claude exit X" rather than the design's "Claude killed independently" framing.** Behavioural equivalence holds; naming is honest. Note for completeness.

- **L2 — PID recycling within a single boot (Baked-In Assumption #5)** could silently overwrite an old casualty record. Edge case; mitigation cost would exceed value. Note for completeness.

- **L3 — The "no .tmp residue" test (Test #10) does not prove rename atomicity, only post-completion absence.** Code-review already renamed the test to reflect this. Note for completeness.

## Overall Assessment

**Coheres.** The Phase 8 implementation matches the design's architectural intent: the wrapper writes a four-key liveness file atomically at startup, removes it conditionally on clean-or-Ctrl-C exit, retains it on any other exit; the version coordination across both plugins satisfies AC8.2/AC8.3; the UAT runbooks render with the contract the phase template required.

Two plan defects (`set -e` interaction, bats env-var name) surfaced and were correctly fixed inline. Both are scheduled for Stage 1 implementation-time ADRs — that scheduling is sufficient.

The one concerning baked-in assumption — the silent transcript-archive gate — has been routed through code review and accepted, but warrants a CHANGELOG callout, a fitness function, and an ADR pairing. M1 above captures this.

Architecture-doc updates are not yet written but are scheduled in Stage 1. The scheduling is sufficient *for items already on the Stage 1 list*; this review adds items 5–11 above to that list.

The deferred UAT decision (AC5.6/AC6.4 to live operation) is a defensible choice given the deferred items are mechanical integration-tests-by-hand and have been empirically verified via real crashes. The decision should be promoted from a hallway record to a document in Stage 1.

**Requirements for proceeding to Stage 1:**

1. Accept the M1 transcript-archive gate as a deliberate side-effect (or revert the gate — but the gate is defensible). If accepting: extend CHANGELOG 2.32.2 with a one-sentence note before merge, OR record the side-effect in the `set -e` ADR.
2. Confirm Stage 1 will pick up the additional constraint-doc rows (items 5–11) and the AC5.6/AC6.4 UAT deferral record.
3. Confirm test-requirements.md will absorb the three Medium-severity test gaps (transcript-gate fitness function, writer→reader round-trip, wrapper-non-CR-contracts).

No High-severity blockers. Proceed to Stage 1.
