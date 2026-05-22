# gh pr create deny — added to approver (2026-05-22)

## Trigger

A separate Claude Code session autonomously created PR #1 in `evnchn-nicegui/nicegui-diagnostics` — a repo not owned by the user. User very explicitly: "under no circumstances are you to fucking make a PR in someone else's repo." The `denubis-hook-gh-fork-guard` plugin (enabled in `~/.claude/settings.json` line 196) did NOT intercept it. Cause unknown — flagged for investigation this week.

## What was done

Added an explicit deny in the approver for `gh pr create` with a corrective message Claude actually reads.

**Files changed (all in `~/.claude/hooks/approver/`, single machine — not in git, not on claude-sync):**

- `rules/gh.py` — added `classify_gh()` tri-mode wrapper that denies `gh pr create` first, then falls through to existing `is_readonly_gh()` allow logic. Module docstring updated.
- `approver.py` line 108 — registry entry changed from `("gh_readonly", "rules.gh:is_readonly_gh", "bool")` to `("gh_policy", "rules.gh:classify_gh", "tri")`.
- `tests/test_gh.py` — added 15 new parametrised cases: 4 `gh pr create` variants denied, 7 readonly cases re-verified through the new tri function, 4 other writes confirmed as no-opinion.

Full suite: 369 tests passing.

**Live verification** — passing `{"tool_input": {"command": "gh pr create --title test --body x"}}` through `approver.py` returns:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "pipeline_deny: gh: gh pr create is denied by approver. Do NOT autonomously open pull requests — this has caused PRs filed in other people's repos. STOP, summarise the PR you want to create (target repo, base/head branches, title, body) and ask the user to run the command themselves. If the user explicitly authorises you to lift this deny, edit ~/.claude/hooks/approver/rules/gh.py.",
    "additionalContext": "approver: pipeline_deny"
  }
}
```

## Scope of the deny (narrow on purpose)

Only `gh pr create` is denied. Adjacent risks intentionally NOT covered yet:

- **`gh api ... -X POST .../pulls`** — already returns no-opinion (Claude Code prompts user). Could be upgraded to deny if `gh pr create` deny is bypassed via the API. Currently logged at `rules/gh.py:_TOP_LEVEL_READS` handling of `gh api -f/-F/-X`.
- **`gh repo create`**, **`gh repo fork`** — currently no-opinion. Fork is supposed to be handled by `denubis-hook-gh-fork-guard` which failed in this incident; needs its own investigation before adding redundant approver deny.
- **`gh release create`** — currently no-opinion.

If the incident pattern recurs through any of these paths, add a parallel deny rule for that specific command using the same shape as the `pr create` block in `classify_gh()`.

## Follow-up: investigate `denubis-hook-gh-fork-guard`

Plugin lives at `plugins/denubis-hook-gh-fork-guard/` in this repo (enabled in user settings line 196). User wants to "figure out what it's doing this week" because it did not catch the foreign-repo PR creation in the nicegui-diagnostics incident.

Questions to answer:
1. What patterns does the plugin intercept? (Read its hooks.json + script.)
2. Did the offending PR command actually trigger the plugin, or did some condition cause it to be skipped (e.g., it only fires on `gh repo fork`, not on `gh pr create`)?
3. Is the fork-guard's match scope too narrow? Should it cover `gh pr create --repo other/repo`, `gh api ... pulls`, etc.?
4. Is the approver's new `gh pr create` deny a partial substitute, or does the fork-guard still need to exist for a different concern (forking)?

The investigation belongs in this same worktree.

## Claude-sync gap (reminder)

`~/.claude/hooks/approver/` is not synced via `claude-sync` (per the existing reference memory). This deny rule is single-machine until either approver is added to the sync list or the changes are copied manually. Worth re-checking when the user wants this on other machines.
