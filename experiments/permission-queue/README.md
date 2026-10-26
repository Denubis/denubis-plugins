# permission-queue has moved

permission-queue lives in its own private repository, `~/people/Brian/permission-queue`
(remote `git@github.com:Denubis/permission-queue.git`), under ADR 0034 in
`docs/architecture/decisions/`. The code, its twelve test modules, the parked
installed-daemon test, the evidence captures, fixture and documents moved there on
2026-10-26 from this directory, working-tree versions, with the launcher installed from
that checkout. The classifier it loads from this repository
(`plugins/denubis-external-agents/scripts/codex_supervisor.py`) is reached through
`DENUBIS_PLUGINS_REPO` until the ADR 0040 package exists.
