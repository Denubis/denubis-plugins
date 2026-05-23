# fallback_ask for no-opinion PreToolUse — DEAD END (2026-05-22 / reverted 2026-05-23)

> **Outcome: hypothesis falsified, intervention reverted.** See `docs/investigations/2026-05-22-rtk-stall-investigation.md` Phase 3 for the falsification evidence. Two post-fix stalls (sillytavern `5f7145aa` at 02:23:02Z and approver-rtk `1119a896` at 02:23:20Z) occurred on commands where the approver explicitly emitted `permissionDecision: "ask"` — silence was not the mechanism.
>
> The approver code, tests, and `bash_signature` API have been restored to their pre-fix state. The text below is preserved as a record of what was tried and why it failed, so the next investigator does not repeat the experiment.

---

## Original intent (2026-05-22)

## Trigger

Stalls persisted after Phase 1's rtk `exclude_commands` mitigation. Phase 2 investigation (this session, `1119a896-…`) discovered that **10/10 post-mitigation stalls across 5 projects correlated with PreToolUse approver decisions of `no-opinion`** — the case where `run_hook` exits 0 with no JSON on stdout. Zero allow-decided turns stalled. See `docs/investigations/2026-05-22-rtk-stall-investigation.md` Phase 2 for the full evidence chain.

Mechanism (speculative): when the hook is silent, the harness's fallthrough permission flow does something that breaks the tool_result → model_response cycle. Eliminating the silence eliminates the path.

## What was done

Added a fallback ask inside `run_hook`'s PreToolUse branch so the hook always emits JSON for Bash commands with safe leadings:

```python
if decision is None and tool == "Bash" and sig is not None:
    decision = {
        "name": "fallback_ask",
        "decision": "ask",
        "reason": "approver had no opinion; deferring to user",
    }
```

**Files changed (all in `~/.claude/hooks/approver/`, single machine — not in git, not on claude-sync):**

- `approver.py` lines 274-285 — fallback block added inside `run_hook` PreToolUse branch, AFTER the existing cache-write check and BEFORE the elif PostToolUse.
- `tests/test_hook.py` — new file: 4 tests (1 driver + 3 contract groups), 18 cases total. Covers: positive case (safe-leading Bash with no rule → ask), positive case (safe-leading Bash with rule → allow), negative case (dangerous-leading Bash → still silent), negative case (Edit/Write/Read → still silent).

Full suite: **406 tests passing** (388 prior + 1 new driver test + 17 new contract cases). Zero regressions.

## Scope chosen deliberately

Two scope guards, both important:

| Guard | Purpose | Effect |
|---|---|---|
| `tool == "Bash"` | Preserve `acceptEdits` UX. Stall pattern was Bash-only. | Edit, Write, Read keep their silent fallthrough — no new prompts on file edits. |
| `sig is not None` | Preserve `settings.json` hard-deny rules. | `rm`, `sudo`, `ssh`, `xargs`, `bash -c`, etc. stay silent so settings.json's deny list applies unchanged. Emitting `ask` here would risk overriding deny with a user prompt. |

Both negative borders are explicit tests in `test_hook.py`.

## Live verification

Pre-fix payload (no rule, would have been silent):

```bash
echo '{"session_id":"v","cwd":"/tmp","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"frobnicate --foo"}}' | python3 ~/.claude/hooks/approver/approver.py
```

Now returns:

```json
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": "approver had no opinion; deferring to user"}}
```

Existing allow path unchanged:

```bash
echo '{"session_id":"v","cwd":"/tmp","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"ls -la"}}' | python3 ~/.claude/hooks/approver/approver.py
```

Returns the existing pipeline_safe allow JSON with `additionalContext: "approver: pipeline_safe"` exactly as before.

## Logging change

Previously-silent no-opinion turns now log as:
```json
{"decision": "ask", "rule": "fallback_ask", "reason": "approver had no opinion; deferring to user", ...}
```

Distinguishable from rule-driven `ask` decisions (e.g. `uv_policy`'s ask cases) and from real allow/deny entries. Gives future visibility into how often the fallback fires, which is useful for sizing the gap that future rule additions (e.g. an AST-based python3 classifier) would close.

## Falsification path (Phase 3 of systematic-debugging)

The current evidence grade is **plausible** for "silent return causes stalls" — one border shown (no-opinion correlates 10/10), other border not yet shown (removal eliminates stalls). To upgrade to demonstrated:

1. Work normally for a few sessions covering varied Bash patterns (including python3 inline, awk inline, custom binaries, complex pipes).
2. Scan post-fix session JSONLs (mtime >= 2026-05-22T07:00Z) for the stall signature.
3. Cross-reference any stalls against approver log entries — `fallback_ask` entries paired with stop_hook_summary would falsify the hypothesis; clean turns paired with `fallback_ask` would corroborate it.

If stalls drop to the pre-2026-05-21 baseline (0 in 631 turns / 6 days), upgrade to demonstrated. If they persist at similar rate, investigate the *content* of injected context rather than its presence.

## Adjacent follow-up

The user wants an AST-walking enhancement to the approver so that `awk|python3` etc. get classified by their actual program shape, not just their pipe leading. Design conversation started in the Phase 2 session, not yet a plan. Loose-granularity fingerprinting agreed:

- Python `-c`: parse with stdlib `ast`, hash `{imports, call_targets, attr_chains}`, reject dangerous imports/calls outright.
- Bash args: use `bashlex` or similar, walk command nodes, check redirects/substitutions/leading-and-args.

`xargs` is a particularly motivating case — currently a dangerous leading (correctly: `xargs rm`/`xargs sh` would be bad), but `xargs grep -l <pattern>` is benign and currently has to be approved every session. An args-aware classifier would unlock that.

This is the natural sequel to the fallback_ask intervention: the fallback eliminates stalls but adds prompts. AST-walking reduces the prompts without re-introducing silence.

## Claude-sync gap (reminder)

`~/.claude/hooks/approver/` is not synced via `claude-sync`. This fallback_ask change is single-machine until the approver dir is added to sync or copied manually. The fix WILL be needed on any machine using the approver — without it, stalls return.
