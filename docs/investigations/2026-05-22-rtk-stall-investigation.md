# RTK / Approver Stall Investigation

**Date:** 2026-05-22
**Sessions:**
- Phase 1: `154eb6de-9fbf-44a6-8bef-9e4bf8cf6a40` (in `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/`)
- Phase 2: `1119a896-2eff-4dda-bafe-7eec18a14525` (in `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-approver-rtk/`)
**Status:** Phase 2 closed — Phase 1's rtk hypothesis refined to "no-opinion approver decision" hypothesis; narrow intervention shipped to approver. Awaiting post-fix observation to upgrade evidence grade from plausible to demonstrated.

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

## Hand-off for next agent

If you're picking this up:

1. **Falsification observation:** check whether stalls have continued in any session modified after 2026-05-22T06:30Z (when the approver fix went live). Use the same scan methodology — JSONL stall signature + approver log cross-reference. Look for `rule: "fallback_ask"` entries paired with stop_hook_summary events (still a stall) vs paired with normal assistant response events (the fix working).
2. **If stalls persisted after fix**: hypothesis (a) falsified, look at what additionalContext content gets injected and whether `additionalContext: null` or missing affects the model.
3. **If stalls dropped to baseline**: upgrade Phase 2 finding to demonstrated, write up as a closed investigation.
4. **Separately**, the user wants an AST-walking enhancement to the approver: instead of only matching on pipe shape (leadings), inspect the actual arg shape for `python3 -c …`, `awk …`, `xargs …`, etc., and produce confident allows for benign call shapes. This is a design conversation, not yet a plan.
