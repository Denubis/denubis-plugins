# ADR 0046 — Installed plugins take shared libraries as commit-pinned git dependencies; the release skill owns the pin step

**Status:** Accepted (2026-10-27). Closes ticket L5c (library distribution to other
plugins). Applies the ADR 0040 route to `denubis-agent-logs` (ADR 0045) and to any later
shared library in this repository.

## Authority evidence

Original human messages in session `f30676a7-e08c-43cb-86f8-9dc704202a5a`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/`):

- `ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:058d62fb-611f-41da-b2c0-21eebef25037`
  (2026-10-27T05:18Z), on declaring the library as a dependency: "um, is there a problem
  with that as pyproject toml? or as a script header pep?"
- `ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:6441018b-d124-48e4-b13b-8e5f55baa6ee`
  (2026-10-27T05:23Z), after the answer that neither is a problem and that the only costs
  are first-run network and bumping the pinned commit: "so long as we properly have a
  skill that documents what needs to be done when we marketplace and cmomit, this is not
  an issue."

Resolvers:

```sh
cc-search-chats resolve ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:058d62fb-611f-41da-b2c0-21eebef25037 --reference-only --json
cc-search-chats resolve ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:6441018b-d124-48e4-b13b-8e5f55baa6ee --reference-only --json
```

## Context

Inside this repository every script can import every other through the uv workspace. An
installed plugin runs from its own copy under
`~/.claude/plugins/cache/denubis-plugins/<plugin>/<version>/`, with no sibling plugin
beside it, so a shared library cannot be reached by a relative path once installed. Hook
and skill scripts are PEP 723 scripts run with `uv run --script`, and already declare
their third-party dependencies in their headers. ADR 0040 chose, for the supervision
library, an installable package inside a plugin that outside consumers pin by path or git
reference.

## Decision

1. A shipped plugin that needs a shared library from this repository declares it in the
   consuming script's PEP 723 header: the distribution name in `dependencies`, and a
   `[tool.uv.sources]` entry naming this repository's public git URL, a commit (`rev`), and
   the library's `subdirectory`. Development and tests keep using the workspace.
2. Releasing a library change is incomplete until every consuming script's `rev` is moved
   to the commit that carries the change, in the same release change as the plugin version
   bump, marketplace entry and changelog line the repository contract already requires.
3. The release procedure is documented in the marketplace-maintenance skill
   (`denubis-extending-agents:maintaining-a-marketplace`) as a named step, and the commit
   skill's release path points at it. Both landed on 2026-10-27 (extending-agents 2.1.0,
   git-commit 1.5.1).
4. A vendored copy is not used.

## Amendment, 2026-10-27, after the rubric review of the skill step

The instruction-control review of the first skill text found that a single release commit
cannot pin itself, that an 8-character `rev` forces a GitHub fetch on every run and fails
offline (observed with uv 0.13.5 against this repository), that a consumer plugin whose
`rev` moves must bump its own version or installed users never receive it, and that the
commit skill carried no pointer to the step. Brian's answers, same session:

- `ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:0b57eb84-3ba9-4fdc-88fd-b1148b02a370`
  (2026-10-27T06:18Z): "um. ... yeah, two-stage is fine. Is this wise? Am I missing an
  obvious thing here?"
- `ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:e6794dd6-8039-44aa-a15d-8f65a5766f57`
  (2026-10-27T06:20Z): "yeah, no, not going to do pypi until this settles down... and...
  uh, is there a way to have a setup check bit for hooks or something so they fail-noisy?
  and yes, one library and mostly me and 2 colleagues, but yes, we should have repair as
  part of this. Session start hook?"
- `ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:ecbcfb3e-fe4d-41ba-9215-f929c5094433`
  (2026-10-27T06:31Z): "ok", to the proposal of a launcher-level failure message plus a
  check-and-repair step in the setup skill instead of a new SessionStart hook.

Decisions added:

5. A shared-library change ships in two stages: the library change lands and is pushed
   on the default branch first; a second release commit moves each consumer's `rev` to
   that published full 40-character hash and bumps each consumer plugin's version.
6. Hooks (`plugins/*/hooks/*.py`) do not take a git-pinned library. They vendor the few
   functions they need or do not adopt the library. Only tools and skills' scripts
   consume it. A SessionStart hook must keep working offline inside its timeout.
7. Publishing to PyPI is deferred until the library settles; the git pin is the interim.
8. Failure is noisy and repair is documented: each hook launcher emits a `systemMessage`
   naming the plugin and the repair command when `uv run --script` fails, and the
   getting-started plugin's `/denubis-00-getting-started:setup` command gains a
   check-and-repair step that resolves
   every installed plugin's script environments and, in this repository, compares each
   consumer's `rev` with the library's last commit. No new SessionStart hook.

## Consequences

- First resolution on a machine needs network access to GitHub; later runs use the uv
  cache, provided the pin is the full hash. A hook that cannot resolve its dependency fails in the same way as any other
  missing PEP 723 dependency.
- A stale `rev` in a consumer is a release defect. The git-form resolution from a clean
  cache is unchecked as of this record; the first cross-plugin adoption must run it and
  record the result.
- Ticket L5c closes. Tickets L5d (ADR 0040 boundary for Codex quota parsing) and L5e
  (approver pins on importing scripts) remain open.
