# ADR 0034 — permission-queue leaves the plugins repository for its own private repository

**Status:** Accepted (2026-10-22). Supersedes the "start as an experiment" placement in
ADR 0030; the interaction rulings in 0030 and 0012 are unchanged. Retires ticket L4.

## Authority evidence

Original human messages in session `f30676a7-e08c-43cb-86f8-9dc704202a5a`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/`):

- `ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:bc93324d-b038-4724-9415-932203b97ff7`
  (2026-10-22T07:12Z), on why `experiments/permission-queue/` still held a parked test,
  committed evidence dumps and an uninstalled launcher: "yep, make the promotion. Not
  sure what you mean by design, it's running right now? ... do we just promote it out of
  this plugin?"
- `ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:96dd5369-5171-4fa7-8b33-21d514158a23`
  (2026-10-22T07:12Z): "yeah, go promote it to something in people/Brian/ private repo,
  and push. then fix all the symlinks"

Resolvers:

```sh
cc-search-chats resolve ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:bc93324d-b038-4724-9415-932203b97ff7 --reference-only --json
cc-search-chats resolve ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:96dd5369-5171-4fa7-8b33-21d514158a23 --reference-only --json
```

## Context

ADR 0030 placed the held-approval work under `experiments/permission-queue/` as an
experiment. By 2026-10-22 it was shipped and in daily use: about 4,000 lines of flat
modules, twelve test files in the root `tests/`, one test parked in the tool's pending
subdirectory, the 2026-10-14 live-run evidence committed beside the code, and the
`permission-queue` command on PATH as a symlink from `~/.local/bin` into the
checkout. It is a tool, not a
Claude Code plugin: it ships no skills, agents or hooks through the marketplace.

## Decision

1. permission-queue becomes its own private repository under `~/people/Brian/`, pushed
   to GitHub under the `Denubis` account like the other private tools (adopted default:
   repository name `permission-queue`, remote `git@github.com:Denubis/permission-queue.git`).
2. It carries the root lint standards of this repository (ruff, ty, complexipy at 15,
   vulture, the warn-only lint script, and the blocking pre-commit gates), per Brian's
   "same standards" ruling recorded in ADR 0032.
3. The code, its twelve test files, the parked test, the evidence directory and the
   three Markdown documents move with it. This repository keeps only the decision
   records and a pointer. `~/.local/bin/permission-queue` and any other symlink are
   repointed at the new checkout.
4. ADR 0012 and the interaction rulings in ADR 0030 continue to govern its behaviour.

## Consequences

- The flaky-test fixes made on 2026-10-22 land in the new repository, not here.
- The open tickets about permission-queue in the `project_open-questions` file in the
  notes directory (standalone viewer target, Codex two-client retry) move to the new
  repository's notes directory.
- Ticket L4 (linting the parked test as test code) is moot here; the parked test is the
  new repository's concern.
- The architecture map's permission-queue references point to the new repository.
