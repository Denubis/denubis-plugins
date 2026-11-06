# ADR 0050 — Hooks-only plugins carry the `hook-` infix

**Status:** Adopted default (2026-10-24), not a human ruling. The dispatcher (team-lead)
settled it from repository evidence and told the human, who has not ruled on it. Applied
in `b329741`. Recorded first in the untracked `.notes/decisions/0004`; moved here
2026-10-25.

## Authority evidence

Repository evidence selected the decision. At `4d08ee0`, the parent of `b329741`, five
tracked plugins had hooks as their only component, and all five carry the infix:
`denubis-hook-branch-bg`, `denubis-hook-code-quality-guard`, `denubis-hook-gh-fork-guard`,
`denubis-hook-instruction-budget`, and `denubis-hook-pretooluse-dispatcher`. Observed
2026-10-25 by listing each tracked plugin's top-level component directories (`skills`,
`agents`, `commands`, `hooks`, `output-styles`, `bin`, MCP configuration) at that
commit; every other plugin there has skills.

```sh
git ls-tree -d --name-only 4d08ee0 plugins/
git ls-tree -r --name-only 4d08ee0 plugins/ | cut -d/ -f2,3 | sort -u
```

Records in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/e159b867-7a1e-4e2a-a524-058f6b7e72b6.jsonl`
show that the human was told and what followed. None of them is a human ruling on the
name.

- Line 938, dispatcher (assistant record), record
  `2fe501a7-874d-4be4-8a2e-459c186411c2` (2026-10-24T05:46:08.297Z), telling the human:
  "The naming ticket is recorded as settled from repository evidence, with one
  correction: five hooks-only plugins carry the infix, not six, since one folder is an
  untracked leftover."
- Line 1034, human-pasted command output, record `ee33a4d8-ddb8-4072-bba6-13f7ff9946b5`
  (2026-10-24T22:58:22.243Z): the human's push of `b329741` and the install of
  `denubis-hook-quiet-agents@denubis-plugins` and
  `denubis-hook-agent-notice-log@denubis-plugins`.
- Line 1116, plugin-submitted message (stored with role `user`, written by the plugin,
  not the human), record `6ef9c339-c826-45ac-a547-4feb462cb837`
  (2026-10-24T22:59:30.069Z): the installed plugin running under the name
  `denubis-hook-quiet-agents`.

Exact raw-record resolver:

```sh
sed -n '938p;1034p;1116p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/e159b867-7a1e-4e2a-a524-058f6b7e72b6.jsonl
```

## Context

The question as recorded: name the two mod plugins `denubis-quiet-agents` and
`denubis-agent-notice-log`, or `denubis-hook-quiet-agents` and
`denubis-hook-agent-notice-log`?

## Decision

`denubis-hook-*`. Every tracked hooks-only plugin carried the infix: five of five, after
the dispatcher's correction that one of the six folders first counted is an untracked
leftover.

## Consequences

- Applied to `plugins/denubis-hook-quiet-agents`, `plugins/denubis-hook-agent-notice-log`,
  their marketplace entries, and quiet-agents' `$.state` owner.
- The ticket left the open-questions file because the work it blocked, the commit
  `b329741`, is done. Renaming now would change the install identifier for every
  installer, so a human override should come with a migration.
