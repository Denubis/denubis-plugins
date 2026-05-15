# UAT Requirements — denubis-crash-recovery

Human-judgement falsification entries. Each requires a human to USE the built thing
and exercise judgement that automated tests cannot capture.

Quality gate: every entry must have (1) what the human DOES (an action, not inspection),
(2) what they're JUDGING (subjective quality), (3) what FAILURE looks like (concrete experience).

The `exec-uat-gate` skill reads this file during execution to surface human-touchpoint
verifications between phase completion and merge approval.

---

## Phase 7: Skill file and skill ↔ CLI integration

### Prune-gate prompt clarity

**This decision assumes:** the AskUserQuestion prompt text in the triage skill's prune flow makes the destructiveness of `crash-recovery prune --confirm` clear enough that a user pressing "yes" understands what will be deleted.

**To shatter it:** invoke `/denubis-crash-recovery:triage` against a fixture DB containing 5 prune candidates (concluded sessions with vanished JSONLs). Walk the skill's prompts to the point where it surfaces the prune dry-run output and asks for confirmation. Read the prompt as if you were encountering the skill for the first time, without recourse to the README or design plan.

**It's wrong if:** you later say "I didn't realise that would delete sessions" or "I thought it would archive them somewhere", OR you ask "where are the deleted entries now?", OR the prompt's wording leaves ambiguity about whether the deletion is reversible (it isn't — Phase 6's prune flow does not log deletions and there is no audit trail in v0.1.0).

**Acceptance threshold:** the human evaluator can articulate, after reading the prompt only, that (a) the deletion is permanent, (b) the affected rows can be enumerated from the dry-run output above the prompt, (c) user-annotated sessions are excluded.

---

## Phase 8: Wrapper patch in denubis-plan-and-execute and version coordination

### AC5.6 — Boot_id mismatch correctly identifies post-reboot casualties

**This decision assumes:** the `boot_id` comparison correctly identifies sessions that cannot have survived a reboot, AND that the classification reaches the user's resume report as a `hard_crash` with reason `liveness_boot_id_mismatch`.

**To shatter it:** start a wrapped Claude session in a known cwd (see the README runbook); confirm the liveness file exists at `~/.claude/run/<wrapper-pid>.live`; reboot the machine; after reboot, run `crash-recovery scan && crash-recovery triage` and inspect the rendered "Idle-live killed" section.

**It's wrong if:** the pre-reboot session is NOT classified `hard_crash` with reason `liveness_boot_id_mismatch`, OR a different session in the same project directory is misattributed as the post-reboot casualty, OR the session is silently dropped from the report. Any of these means the reboot-safety mechanism (DR7 in the design plan) didn't engage as specified.

**Acceptance threshold:** the rendered triage report explicitly names the pre-reboot session UUID under "Idle-live killed" with the correct reason string. Independent inspection of the SQLite DB confirms `classification = 'hard_crash'` and `classification_reason = 'liveness_boot_id_mismatch'` for that UUID.

**Note on reproducibility:** this UAT requires a real machine reboot. It cannot be safely automated in CI. The runbook in `plugins/denubis-crash-recovery/README.md` (Phase 8 Task 5) is the user's reference for executing it.

### AC6.4 — Idle session killed via SIGKILL is detected via liveness mechanism

**This decision assumes:** an idle session whose wrapper was SIGKILLed (so no graceful cleanup ran) and whose JSONL was stale at kill time (no fresh trailing entries) gets classified as crashed VIA the liveness mechanism, NOT via the JSONL-tail-only heuristic that would have classified it as `concluded`.

**To shatter it:** start a wrapped Claude session in a known cwd; have one normal exchange (the JSONL records a clean assistant turn); leave the session idle for 5+ minutes (the JSONL receives no further entries); confirm the liveness file exists; SIGKILL the wrapper PID; confirm the liveness file persists (the wrapper had no chance to clean up); run `crash-recovery scan && crash-recovery triage`.

**It's wrong if:** the session is classified `concluded` (which would mean the classifier is relying on the JSONL tail only and ignoring the liveness signal), OR the session does NOT appear at all (which would mean the liveness file wasn't correlated to a UUID at scan time), OR the classification appears but the reason is something other than `liveness_dead_pid_unknown_tail` or `liveness_dead_pid_tool_use_no_result` (which would mean Phase 2's rule selection is wrong for this case).

**Acceptance threshold:** the rendered triage report names the session UUID under "Idle-live killed" with `classification = 'hard_crash'` and a `liveness_dead_pid_*` reason. The point of this UAT is to prove that the liveness mechanism catches what JSONL-tail-only would miss — without this mechanism, the test session would look concluded.

**Note on reproducibility:** the design plan's intent for this UAT is that an experienced developer follows the README runbook on a real machine and judges whether the outcome matches the design's promise. The bats test in Phase 8 Task 2 exercises the same machinery against a stub `claude` binary, but only the manual UAT against a real Claude Code session can verify the end-to-end story holds.

---

## Coverage Summary

- **Total UAT entries: 3.**
  - Phase 7: prune-prompt clarity (genuinely subjective — usability judgement).
  - Phase 8 AC5.6: post-reboot mismatch (mixed — automated rule plus manual reboot proof).
  - Phase 8 AC6.4: idle-kill detection (manual real-machine reproduction).

- **Routing during execution:**
  - Phase 7 routes to `exec-uat-gate` for the prune-prompt clarity check after code-review passes.
  - Phase 8 routes to `exec-uat-gate` for both AC5.6 and AC6.4 after the bats tests pass.
  - Phases 1–6 have NO UAT entries and route to `exec-coherence-review` instead — they are foundational phases without user-facing surfaces of their own (the surfaces appear in Phase 5's render and Phase 7's skill).

- **What `exec-uat-gate` expects:** for each entry above, the human evaluator should be able to (a) follow the "To shatter it" runbook, (b) observe the outcome, (c) compare against the "It's wrong if" criteria, (d) sign off on the acceptance threshold or escalate.

- **Cross-reference to test-requirements.md:** the AUTOMATED side of AC5.6 (the rule wiring and DB write) is verified by `test_scan_classifies_boot_mismatch_as_hard_crash_even_if_pid_alive` in Phase 4. The MIXED designation captures that the rule logic is automatable but the post-reboot proof is not. AC6.4 has no automated counterpart — it is the pure-UAT case where stubbed bats tests cannot substitute for a real idle session followed by a SIGKILL.
