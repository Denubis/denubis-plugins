# ADR 0010 — A spawned Codex has no queued-question widget, and `--spawn` takes `--cwd`

**Status:** Accepted (2026-10-08, recording rulings of 2026-09-19 and 2026-09-30).
Released as `denubis-external-agents` 0.18.0 (`--cwd`, `--question`/`--answer`) and
0.21.0 (catalogue pinning). Moved here from `.notes/project_open-questions.md` tickets
Q1, Q2 and Q3 under ADR 0008.

## Authority evidence

Original human messages:

- 2026-09-19, line 992, record `3c85292c-4d1f-492d-975d-43dc46fc343d` of
  `/home/brian/.claude/projects/-home-brian-people-Brian-breeze-narrate--worktrees-breeze-simplify/dbdf9621-e664-4a7c-b4b1-61048ba6724b.jsonl`,
  one reply covering Q1 (delivering a ruling into a pane held by the widget) and Q2
  (`--cwd`): "so, the supervisor should not *have* a question widget when codex is
  invoked from the supervising codex tool, or, worst case, multiple fucking calls to open
  it and answer if we cannot stop it from running in you=made sessions, and yes, being
  able to set cwd would be nice. the composer holds status was fixed because I ^w'd it"
- 2026-09-19, line 1245, record `ef6eb323-8fd1-4f3f-ba7d-0b9ccfc0e571` of the same
  file, after the release steps and the unproven prevention were laid out: "fuckit, for
  now, make it be able to alt , and just type in answers"
- 2026-09-30, line 1246, record `3580a9cf-ce44-48bc-a38d-2b7d5e767d7e` of
  `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/48519351-cd50-49c9-ad66-8812b026f487.jsonl`,
  answering Q3 (should `--spawn` stop the widget from existing, option (d) measured
  best): "if we can force the question widget off, that would be amazing." Followed in
  the same session by "uh, fix it if it's fixed?" while 0.157.0 was being checked.

Exact raw-record resolver:

```sh
sed -n '992p;1245p' /home/brian/.claude/projects/-home-brian-people-Brian-breeze-narrate--worktrees-breeze-simplify/dbdf9621-e664-4a7c-b4b1-61048ba6724b.jsonl
sed -n '1246p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/48519351-cd50-49c9-ad66-8812b026f487.jsonl
```

## Context

A Codex spawned by the supervisor showed the `request_user_input_async` widget because
the server-refreshed model catalogue advertised that tool. While the widget was up,
`--message` and `--approve` refused (pane title `[ ! ] Action Required`), so a human
ruling could not be delivered, and the widget expires unanswered. Separately, `--spawn`
inherited the calling pane's working directory, which can be a deleted worktree; tmux
then fell back to `$HOME` and started a `workspace-write` sandbox over the whole home
directory without warning (observed 2026-09-19).

Measured on 2026-09-19 and re-measured 2026-09-30 (codex-cli 0.154.0, then 0.159.2):
`codex debug models -c model_catalog_json=<file>` honours a pinned catalogue (exit 0,
all models retained; the same override naming a missing file fails with "No such file or
directory"), and removing only `request_user_input_async` and `send_user_message_async`
from each model's `experimental_supported_tools` leaves everything else intact.
Pinning the bundled catalogue no longer prevents anything, because the bundled file
also advertises the tool.

## Decision

- First choice: a Codex spawned by the supervisor never shows the widget. `--spawn`
  hands Codex a copy of the live catalogue with only the two question tools removed
  (option (d)), read at each spawn, `--bundled` as the fallback, spawn refused with
  neither.
- Interim and fallback: `--question` opens the widget and `--answer TEXT` types into
  it, as separate calls, for panes `--spawn` did not start.
- `--spawn` refuses a working directory that is not a directory and accepts `--cwd`.
- Option (a), leaving the widget and only explaining the refusal, is rejected.

## Consequences

- UNPROVEN as of 2026-10-08: that an interactive session honours the pinned catalogue
  and the widget never appears. `codex debug prompt-input` shows no tool list and session
  files record none, so only provoking the widget in a live spawned pane can confirm.
  `--question` / `--answer` were likewise designed against an unobserved expanded-widget
  layout. These remain to be verified on a live pane; they are not open questions for
  Brian.
- The catalogue copy freezes model metadata for the life of the pane; regenerated at
  each spawn, so staleness is bounded by pane lifetime.
