# RTK / Approver Stall Investigation

**Date:** 2026-05-22 (Phase 1, 2) / 2026-05-23 (Phase 3 falsification)
**Sessions:**
- Phase 1: `154eb6de-9fbf-44a6-8bef-9e4bf8cf6a40` (in `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/`)
- Phase 2 & 3: `1119a896-2eff-4dda-bafe-7eec18a14525` (in `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-approver-rtk/`)
**Status:** **Phase 3 closed — Phase 2's "no-opinion causes stalls" hypothesis FALSIFIED.** Intervention reverted; approver back to baseline. Stalls continue, including on TaskUpdate (not just Bash) and on commands where the approver emitted explicit ask. New observability tool added; investigation needs a fresh hypothesis.

## Symptom

Bash tool runs, tool result returns, the model produces no follow-up response, the turn ends silently. The user has to type a continuation nudge ("please continue", "..." , etc.) before work resumes.

User-reported observation: started happening "since I wired in the auto-approver" (2026-05-21). Multiple sessions affected, multiple bash calls per session.

## Investigation arc

### Attempt 1 (FALSIFIED)

Initial signature: `stop_hook_summary` events with `stopReason: ""` AND `hasOutput: false` mark stalls.

Result: subagent verification on 857 events found 846 had a normal assistant `text` block in the preceding turn. **98.7% false positive rate.** Those fields are uniformly empty in Claude Code 2.1.145 — not stall-specific.

Lesson: do not build signatures on undocumented JSONL fields without empirical falsification. The official Claude Code docs do not define what `stopReason`, `hasOutput`, `stop_hook_summary`, or `away_summary` mean.

### Attempt 2 (DEMONSTRATED within sample)

Verified signature, derived from empirical diff of stalled vs normal turns in the same session:

> A turn is "stalled" iff the immediately-preceding *conversational* event before a `stop_hook_summary` (skipping `attachment` events) is a `user` event with `tool_result` content — i.e. the harness sent a tool result back to the model, the model returned nothing the harness logged, and Stop fired.

Both borders demonstrated in `154eb6de…`:
- Positive: known stall at 00:44:29 UTC matches the pattern.
- Negative: 3 normal turn-ends in the same session preceded by `assistant[text]`, do NOT match.

Tested across 4 recent sessions in the brian-ed3d-plugins and -home-brian directories: 1 stall (the observed one) out of 41 turn-ends. Signature reliable; earlier "26 stalls" and "10 stalls" claims were based on the falsified signature — retracted.

### Wider scan (last 7 days, 107 session files)

| Date | Turn-ends | True stalls | Recap before reply |
|---|---|---|---|
| 2026-05-15 | 89 | 0 | 0 |
| 2026-05-16 | 120 | 0 | 0 |
| 2026-05-17 | 142 | 0 | 0 |
| 2026-05-18 | 77 | 0 | 3 |
| 2026-05-19 | 68 | 0 | 7 |
| 2026-05-20 | 108 | 0 | 27 |
| 2026-05-21 | 127 | **7** | 28 |
| 2026-05-22 | 40 (partial) | **1** | 10 |

**Clean step change on 2026-05-21.** Zero `true_stalls` in 631 turn-ends across the 6 prior days, then 8 stalls in 1.7 days starting 2026-05-21.

First `approver:` string seen in any session file: `2026-05-21T04:23:46Z` — matches the install window. Stalls cluster after that.

## The 8 confirmed stalls

| Timestamp (UTC) | Project | User's next message |
|---|---|---|
| 2026-05-21T07:03:46 | sillytavern-deploy worktree (7536943f) | `"ok..."` |
| 2026-05-21T07:09:07 | sillytavern-deploy worktree (7536943f) | `"um... please continue?"` |
| 2026-05-21T07:17:43 | sillytavern-deploy worktree (65ed22e7) | `"... yes, please continue?"` |
| 2026-05-21T07:19:00 | sillytavern-deploy worktree (65ed22e7) | `"yes, please continue."` |
| 2026-05-21T08:01:59 | sillytavern-deploy worktree (7536943f) | `"Please continue"` |
| 2026-05-21T08:08:46 | sillytavern-deploy worktree (7536943f) | `"ok, continue, character card changes committed."` |
| 2026-05-21T08:36:46 | sillytavern-deploy worktree (65ed22e7) | (none — session ended) |
| 2026-05-22T00:44:29 | brian-ed3d-plugins (154eb6de) | `"no, not just approver..."` |

The user's reply text in every case is a continuation nudge or session-end — independent corroboration of the signature.

## Proximate cause

**Not the approver itself.** In 6 of 8 stalls the approver had `decision: no-opinion` at the closest log entry (within 2–6 seconds of the stall) — meaning it injected no `additionalContext`. The approver was passing silently.

**rtk's command rewriting is what shows up in the tool_result contents:**

| Stall | rtk involvement in the failing tool_result |
|---|---|
| 07:03 | `curl` rewritten to `rtk curl` (Pre vs Post sig differ) |
| 07:09 | tool_result contains `Exit code 127 [rtk: No such file or directory (os error 2)]` |
| 07:19 | `ls` rewritten to `rtk ls` |
| 08:08 | tool_result body is the 10-character truncated string `"ok impleme"` |
| 00:44 (this) | `find` rewritten to `rtk find`; output mangled with `1084F 124D:` marker and `+1034 more` truncation indicator |

The pattern: rtk's rewritten commands return output formats (truncation markers, compressed listings, embedded error strings, or rtk-internal errors) that the model occasionally fails to respond to.

**Why "since the approver":** before the approver auto-allowed bash calls, the user saw each rewritten command in the approval prompt and could intervene on bad rewrites. With the approver running, rtk's edge cases flow through unattended. Approver is the temporal trigger; rtk is the proximate mechanism.

## Architecture finding

rtk (v0.40.0) has no runtime extension mechanism. Rewrite rules are hardcoded Rust at `src/discover/rules.rs`. `filters.toml` is output-only post-processing — it cannot add new rewrites. The only way to add new rewrites is upstream PRs or a fork.

The `denubis-hook-rtk-rewrite` plugin's shell script was a parallel rewriter. For commands rtk-native already handles (find, ls, curl, etc.), the script was a no-op — rtk's hook fires first in the PreToolUse chain and rewrites the command, so the custom script sees `rtk find ...` and exits via `case "$FIRST_CMD" in rtk\ *) exit 0`. The script's unique value was for commands rtk-native does NOT handle: `uv run X`, `uvx X`, `pnpm test`, `vue-tsc`, `bandit` (with `rtk err`/`rtk summary` wrapping).

## Decisions made (2026-05-22)

User chose **Option B (cut losses)**:

1. **Disable** `denubis-hook-rtk-rewrite@denubis-plugins` in `~/.claude/settings.json` (set to `false`). Plugin files left on disk.
2. **Populate** `~/.config/rtk/config.toml` `[hooks].exclude_commands`:
   ```toml
   exclude_commands = [
       "find", "ls", "tree", "grep", "read", "cat", "head", "tail",
       "curl", "wget", "env", "wc", "docker", "kubectl", "aws",
   ]
   ```
3. **Revert** my 13 in-place no-op edits to the cache copy of `pretooluse-bash.sh` (cache file back to original).
4. User to **handle the lost `uv run`/`uvx`/`pnpm test` rewrites through a new mechanism** (TBD).

rtk-native still rewrites git, gh, cargo, vitest, tsc, lint, prisma — the structured-output cases that didn't appear in any stall.

## Verification post-change

`rtk hook claude` dry-run on the excluded commands now returns no rewrite for 9 of 10 sampled cases:

| Command | Result after exclude_commands |
|---|---|
| `find`, `ls`, `curl`, `cat`, `grep`, `docker`, `wget`, `wc`, `env` | NO_REWRITE ✓ |
| `head -10 /etc/hosts` | still rewrites to `rtk read /etc/hosts --max-lines 10` ✗ |
| `git status`, `git diff`, `gh pr list`, `cargo build` | rewrite preserved as designed ✓ |

## Open / follow-up

1. **`head` exclude edge case.** Despite `"head"` being in `exclude_commands`, rtk's parametric `head -N file → rtk read file --max-lines N` rule still fires. Possibly the rule is keyed on `read` rather than the source command. If head-stalls recur, also try adding `"read"` to the exclude list (or investigate rtk source to confirm).

2. **The "new mechanism" the user mentioned.** Replacing `uv run mypy` → `uv run rtk mypy` and similar rewrites — out of scope for this session. Tracked here for the next agent.

3. **Falsification of the causal claim.** Mitigation is in place; we have not yet observed a post-fix session to confirm stall rate drops. The clean test is: work a session with intentional heavy file-ops bash use, count stalls. If rate matches the pre-2026-05-21 baseline (zero in 631 turn-ends), causation is upgraded from "plausible" to "demonstrated".

4. **Approver script itself: probably fine.** It is the *temporal correlate* not the direct mechanism. Investigation did not find evidence that the approver's `additionalContext` injection (`approver: pipeline_safe`, `approver: session_cascade (...)`) caused any of the 8 stalls. Worth re-examining only if stalls persist after rtk is downscoped.

## Files changed by this investigation

| File | Change |
|---|---|
| `~/.claude/settings.json` | line 197: plugin enabled flag `true` → `false` |
| `~/.config/rtk/config.toml` | `[hooks].exclude_commands` populated (15 entries) |
| `~/.claude/plugins/cache/denubis-plugins/denubis-hook-rtk-rewrite/1.1.0/hooks/pretooluse-bash.sh` | 13 `false && echo` no-op edits applied then reverted; file content now identical to repo source |

No changes were made to the `denubis-hook-rtk-rewrite` plugin's source in this repo. If the user later decides to formalise the disable (e.g. delete the plugin from the marketplace), that's a separate change.

## Pointers

- Approver design + layout reference: `notes/approver-reference.md` (this worktree) and `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/reference_approver-script.md`.
- Approver source: `~/.claude/hooks/approver/` (not in this repo).
- rtk source: https://github.com/rtk-ai/rtk @ 7d31049c88e8bd17aaf70949958fbae9158ad99f (per research agent on 2026-05-22).
- `denubis-hook-rtk-rewrite` plugin in this repo: `plugins/denubis-hook-rtk-rewrite/`.
- Original investigation session: `154eb6de-9fbf-44a6-8bef-9e4bf8cf6a40.jsonl`.
- Most stall-dense sessions: `7536943f-4a84-…` and `65ed22e7-05f2-…` in `~/.claude/projects/-home-brian-people-Brian-sillytavern-deploy--worktrees-implement-tavern-laws5000/`.

---

# Phase 2: post-mitigation re-investigation (2026-05-22 evening)

## Symptom continued

After the Phase 1 rtk mitigation (04:57Z), stalls persisted. Two were observed inside the Phase 2 session itself (`1119a896…`): one at 05:25:26 on a `cc-search-chats | python3` pipeline that errored with a Python KeyError, and one at 05:26:20 on a clean successful `tail | python3 -c …` retry. Critically, the second stall had `is_error=False` — so the Phase 1 framing of "rtk-mangled output content confuses the model" could not be the whole story.

## Refined signature

Stalls correlate strongly with PreToolUse approver decisions of **`no-opinion`** — the case where no rule fires, the cache misses, the decision dict stays `None`, and `run_hook` exits 0 with no stdout. This is distinct from `allow` (rule fired with explicit decision) and `deny` (rule explicitly blocked).

## Evidence (n=10 across 5 projects)

A Sonnet subagent scan of all `~/.claude/projects/*/*.jsonl` files modified at or after 2026-05-22T04:57Z (the rtk-mitigation timestamp). Across 12 sessions:

| Group | Total turns | Stalls | Stall rate |
|---|---|---|---|
| `allow` decision | 24 | 0 | 0% |
| `no-opinion` decision | 10 | 10 | **100%** |
| `deny` decision | 0 | 0 | n/a |

The correlation holds across all 5 projects involved (`approver-rtk`, `brian-ed3d-plugins`, `sillytavern-deploy`, `morning-assistant`, `brian-ed3d-plugins-crash-recovery`) — not project-specific.

Lookup methodology: the subagent's first pass used the tool_result timestamp to query approver logs and found "absent" entries for several stalls. Switching to the **PreToolUse dispatch timestamp** resolved all 10 stalls to logged `no-opinion` entries. Long-running commands (a 20-minute `uv run`, a 3-minute font enumeration) had wide gaps between dispatch and result, hence the lookup-window bug. Fixed before reporting.

## Refined causal chain

Phase 1's "rtk → mangled output → model confusion → stall" was incomplete. The corrected understanding:

1. rtk rewrites Bash commands (e.g. `find` → `rtk find`, `tail file` → `rtk read file --tail-lines N`).
2. The rewritten command has a different pipe signature than the approver's whitelists expect (e.g. `rtk|jq|find` instead of `find`).
3. The approver finds no matching rule and no cached signature.
4. `run_hook` returns silently (no JSON to stdout).
5. The harness… does something with that silence that breaks the tool_result → model_response cycle.
6. Tool runs, result returns, model produces nothing, Stop fires.

Step 5 mechanism remains speculative — only the harness team knows for sure. But the correlation gives us a clean place to intervene: eliminate the silence.

This reframes Phase 1's findings: the rtk `exclude_commands` mitigation worked partially because it reduced the number of commands rtk transformed into approver-unknown shapes. Stalls dropped (the original observation of 8 stalls in 1.7 days became less frequent) but didn't vanish, because any Bash pipeline involving a non-whitelisted leading (python3, awk, fc-list, custom binaries) still produces no-opinion → silence → stall.

## Intervention

**Modified `~/.claude/hooks/approver/approver.py:274-285`** (inside `run_hook`):

```python
if decision is None and tool == "Bash" and sig is not None:
    decision = {
        "name": "fallback_ask",
        "decision": "ask",
        "reason": "approver had no opinion; deferring to user",
    }
```

Narrow scope chosen deliberately:
- **`tool == "Bash"`** — non-Bash tools (Edit, Write, Read) keep their silent fallthrough so `acceptEdits` UX is preserved. The stall pattern was Bash-only in the dataset.
- **`sig is not None`** — Bash with a dangerous leading (`rm`, `sudo`, `ssh`, `bash`, `xargs`, etc.) keeps its silent fallthrough so `settings.json` hard-deny rules apply unchanged. Emitting `ask` here would risk overriding the harness's deny with a user prompt.

Logging: previously-silent no-opinion turns now log as `decision: "ask"`, `rule: "fallback_ask"` — distinguishable from real allow/deny entries, giving future visibility into how often the fallback fires.

## Tests added

`~/.claude/hooks/approver/tests/test_hook.py`:
- `test_run_hook_emits_ask_when_no_rule_matches` — RED-then-GREEN driving the new behaviour.
- `test_pretooluse_bash_safe_leading_always_emits` (parametrised, 8 cases) — contract: any Bash with a safe leading emits a permissionDecision.
- `test_pretooluse_dangerous_bash_stays_silent` (parametrised, 6 cases) — negative border: dangerous leadings still silent.
- `test_pretooluse_non_bash_stays_silent` (parametrised, 3 cases) — negative border: Edit/Write/Read still silent.

**Suite: 406 passing** (388 prior + 1 new test + 17 new contract cases). Zero regressions.

## Evidence grade

- **Demonstrated** (one border): silent `no-opinion` returns from the approver correlate 10/10 with model stalls, across 5 projects, over the post-mitigation observation window. No `allow` decision in the dataset stalled.
- **Plausible** (not yet demonstrated): silent return *causes* stalls. The other border (removing silence eliminates stalls) is not yet shown in production. The intervention is now live; observation pending.

To upgrade to demonstrated: continue normal work, count stalls in subsequent sessions, confirm rate drops to the pre-2026-05-21 baseline (0 in 631 turn-ends across 6 days).

## Confound to flag

The correlation is between `no-opinion` and stalls. The causal claim could be either:
- **(a) Direct:** approver's silence itself breaks the harness/model response cycle.
- **(b) Indirect:** "unusual command shapes" produce both no-opinion (because they're not in the safe whitelist) and stalls (for some other reason — harness fallthrough timing, missing injected context, etc.).

These have the same observational signature on the existing dataset. The intervention distinguishes them — if (a), stalls drop to ~0; if (b), they persist at similar rates after the change. The post-fix observation IS the experiment that disambiguates.

## Phase 2 files changed

| File | Change |
|---|---|
| `~/.claude/hooks/approver/approver.py` | lines 274-285: fallback_ask block added inside `run_hook` PreToolUse branch |
| `~/.claude/hooks/approver/tests/test_hook.py` | new file: 4 tests (1 driver + 3 contract groups), 18 cases total |

The approver dir is not git-versioned. No commit is made by this Phase. Pre-change `approver.py` content remains recoverable from this session's JSONL.

## Hand-off for next agent (superseded by Phase 3 below)

The Phase 2 hand-off planned to upgrade the "no-opinion causes stalls" finding to demonstrated by post-fix observation. The observation falsified the hypothesis instead. See Phase 3.

---

# Phase 3: fallback_ask hypothesis FALSIFIED, intervention reverted (2026-05-23)

## What was tried

Across 2026-05-22T~06:30Z to 2026-05-23T~03:00Z, three iterations of the fallback_ask intervention were applied to `~/.claude/hooks/approver/approver.py`:

| Version | Condition | Behaviour change |
|---|---|---|
| Initial (wide) | `decision is None` | Every no-opinion PreToolUse emits `ask` |
| Narrowed | `decision is None and tool == "Bash" and sig is not None` | Bash-only, dangerous leadings stay silent |
| Refactored | `decision is None and tool == "Bash" and sig_reason != "dangerous"` | + bash_signature returns `(sig, reason)` tuple so parse-failed commands also trigger ask |

The refactor also added 26 tests (test_hook.py + new test_session.py assertions), bringing the suite from 388 to 414 passing.

## The falsification (n=2 post-refactor stalls on explicit-ask paths)

Two stalls observed after the third (broadest) fix was live:

| Time | Session | Approver log decision | Tool result | Outcome |
|---|---|---|---|---|
| 2026-05-23T02:23:02Z | sillytavern `5f7145aa` | `decision: "ask", rule: "fallback_ask"` (cd \| git multi-line) | is_error=False, git rm + git mv output | **stall** (17 min user-approval delay first) |
| 2026-05-23T02:23:20Z | approver-rtk `1119a896` | `decision: "ask", rule: "fallback_ask"` (printf \| python3, the live-verify) | is_error=False, JSON output | **stall** (2.5 min user-approval delay first) |

In both cases:
1. Approver emitted explicit `permissionDecision: "ask"` JSON to stdout (verified in approver log).
2. Harness prompted user.
3. User approved.
4. Tool ran successfully.
5. Tool result returned to model.
6. **Model produced zero assistant content. Stop fired. Stall.**

The Phase 2 hypothesis was "silent return from approver causes stalls." If true, the fix (eliminate silence by emitting explicit ask) should have prevented stalls. The fix did not prevent stalls. **Hypothesis falsified.**

## Wider invalidation

Post-revert run of `scripts/stall-report.py --project sillytavern-deploy --days 2` shows 16 stalls in the sillytavern worktree over the observed window, including several AFTER the various fix versions were live (`2026-05-23T02:23:02`, `03:00:22`, `03:07:01`, `03:09:44`, `03:11:16`). Critically:

- **`03:07:01` was a `TaskUpdate` tool stall, not Bash.** The approver never even fires for TaskUpdate (per `dispatch()` at `approver.py:138-139`, only Bash gets rule dispatch). So whatever mechanism is causing stalls operates at a layer that does not require the approver to be involved at all.
- Multiple stalls on `cd ... && git/sed/...` commands, on heredoc patterns, on file-rename batches. Diverse tool inputs.

## What was reverted

| File | Action |
|---|---|
| `~/.claude/hooks/approver/session.py` | `bash_signature` restored to original `str | None` return |
| `~/.claude/hooks/approver/approver.py` | `sig_reason` capture removed; fallback_ask block removed |
| `~/.claude/hooks/approver/tests/test_session.py` | Original assertions restored |
| `~/.claude/hooks/approver/tests/test_hook.py` | **Deleted** (entire file was about the falsified intervention) |

Suite back to **388 passing** (Phase 1 baseline).

## What survived

- `scripts/stall-report.py` in this worktree — observability tool that scans `~/.claude/projects/*/*.jsonl` for the verified stall signature. Useful regardless of which hypothesis is being tested. Validates against known sillytavern stalls (`5f7145aa`, `7536943f`, `65ed22e7`) before reporting.

## Hypothesis space after falsification

- **(a) Silent return from approver causes stalls** — FALSIFIED (this phase).
- **(b) "Unusual command shape" causes both no-opinion AND stalls** — promoted to leading hypothesis. Common pattern across pre-fix and post-fix stalls: commands the approver doesn't auto-classify (heredocs, multi-line continuations, complex chains, unusual leadings). Mechanism unknown — possibly the tool_result content shape itself confuses the model.
- **(c) Long approval delays degrade model state** — speculative. Both post-fix stalls had multi-minute waits.
- **(d) Mechanism is below the hook layer entirely** — newly raised by the TaskUpdate stall (no approver involvement). Likely affects how the harness streams tool_result back to the model after long pauses, or how the model handles certain tool_result content shapes regardless of which tool produced them.

## Hand-off for the next investigator

This investigation's branch on the approver layer is closed. Do NOT repeat the fallback_ask experiment — it doesn't work and the cost is increased prompts.

To restart investigation cleanly:

1. **Use `scripts/stall-report.py`** to enumerate post-mitigation stalls. Add features as needed (filter by tool, filter by error, summarise content patterns).
2. **Look at tool_result content shape, not approver behaviour.** What's in the tool_result for stalled turns vs adjacent successful turns in the same session? Length, line count, embedded code blocks, presence of multi-line content, certain delimiters.
3. **The TaskUpdate stall** (sillytavern session `5f7145aa` at 2026-05-23T03:07:01Z) is the cleanest control case — no Bash, no approver, no rtk. If we can characterise that one in detail, we may find the actual mechanism.
4. **Approval delay** as a possible factor: time between assistant tool_use event and user tool_result event. A wide gap suggests the harness held the request for user approval. Correlate gap duration with stall rate.
5. **Do not re-test the silent-vs-ask distinction.** That's done.

## Why this got documented as a dead-end

Per the project's investigation conventions: dead-ends matter as much as live leads. Future agents (and future-self) will see the n=10/10 no-opinion ↔ stall correlation in the Phase 2 data and be tempted to repeat the fallback_ask experiment. The Phase 2 correlation was real, but the *causal* direction was wrong — no-opinion didn't *cause* stalls, it *coincided with* them via a third factor (unusual command shape). This phase's revert is the corrected understanding.
