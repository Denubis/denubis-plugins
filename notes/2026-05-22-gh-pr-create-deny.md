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

## Scope of the deny

Two explicit denies in `classify_gh()`:

1. **`gh pr create`** (any flags) — original incident response.
2. **`gh api` with any write method or field flags** — closes the workaround. Covers `-X POST/PUT/PATCH/DELETE` (case-insensitive), `--method=X` long form, and `-f`/`-F`/`--field`/`--raw-field` (which auto-trigger POST in `gh api`). Rule of thumb per user: "get the human to run this".

Live verified — `gh api repos/owner/repo/pulls -X POST -f title=x -f head=br -f base=main` returns:

```
permissionDecision: deny
permissionDecisionReason: pipeline_deny: gh: gh api write (-X POST) is denied by approver — github API writes can be used to bypass the gh pr create deny (e.g. POST to /repos/*/pulls). Do NOT autonomously call the github API for writes. STOP, describe the request (repo, endpoint, method, payload) and ask the user to run it themselves. If the user explicitly authorises you to lift this deny, edit ~/.claude/hooks/approver/rules/gh.py.
```

GET still allows: `gh api repos/owner/repo/issues/1` → `permissionDecision: allow`.

Adjacent risks still NOT covered (intentionally — they aren't in `settings.json` allow, so Claude Code prompts the user naturally rather than auto-executing):

- **`gh issue create`, `gh repo create`, `gh release create`** — these write commands return no-opinion from the approver and there's no settings.json allow rule for them, so Claude Code surfaces a permission prompt. No deny needed unless they later get added to the allow list and the prompt is bypassed.
- **`gh repo fork`** — supposed to be handled by `denubis-hook-gh-fork-guard` which failed in this incident; needs its own investigation (see below) before adding redundant approver deny.

If a NEW workaround appears (e.g. a new `gh foo create` subcommand, or a `git push` to a fork), add a parallel deny rule for that specific case using the same shape as the existing blocks in `classify_gh()`.

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
