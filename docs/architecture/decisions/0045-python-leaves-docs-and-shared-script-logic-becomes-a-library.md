# ADR 0045 — Python leaves `docs/`; logic shared across scripts becomes a library

**Status:** Accepted (2026-10-27). Closes ticket L5 of the lint baseline paydown
(`docs/audits/2026-10-21-lint-baseline-defects.md`, section 4). Survey:
`/tmp/docs-scripts-survey.md` was the working report; its durable findings are restated
here.

## Authority evidence

Original human messages in session `f30676a7-e08c-43cb-86f8-9dc704202a5a`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/`):

- `ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:9c03d699-c454-4f9b-8777-3dbf6a30268d`
  (2026-10-27T00:55Z), answering "Should Python under `docs/` stay in scope for ruff, ty,
  complexipy and vulture?": "um, ... that... eval shouldn't be in... please clean those up,
  search chats (with opus) and let's professionalise please"
- `ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:8bdad77d-6945-47a7-98fa-e93493c19051`
  (2026-10-27T00:56Z): "again, common features, let's just start building a proper
  library? Anything that is common should be generalised across multiple scripts. But no,
  those shouldn't be in docs, yes those should be tracked"

Resolvers:

```sh
cc-search-chats resolve ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:9c03d699-c454-4f9b-8777-3dbf6a30268d --reference-only --json
cc-search-chats resolve ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:8bdad77d-6945-47a7-98fa-e93493c19051 --reference-only --json
```

## Context

Five Python files lived under `docs/`: `branch-bg-colour-eval.py`, the three
`usage-forecast-probe` scripts and `phase_05_cross_ref_audit.py` from the 2026-04-17 plan.
An Opus xhigh survey on 2026-10-27 traced each to a model's placement choice, never a
human ruling, and found three of the five broken (the colour-eval default mode references
a hook function removed in `461970a7`; the audit's targets were renamed; `backtest.py`
divides by zero at `blend_from=168`). The survey found the real duplication across
repository scripts in one concern: reading Claude Code and Codex session logs and their
usage and quota records, written independently in six plugins with measured divergences
(the probe's first-seen deduplication undercounts output tokens by about 15% against the
token-estimator's audited maximum-per-message rule; the supervisee-offers hook encodes
project directories by replacing only `/` and `.`; the status line and the Codex
supervisor define the weekly quota record differently).

## Decision

1. No Python lives under `docs/`. The scripts stay tracked and move to the plugin or
   `scripts/` directory that owns their concern; the citing pages are updated in the same
   change. `docs` leaves `[tool.vulture] paths` once empty of Python.
2. Logic that two or more scripts share is generalised into a library rather than copied.
   The first library is `denubis-agent-logs` (import `denubis_agent_logs`), a stdlib-only
   uv workspace member at `plugins/denubis-token-estimator/scripts/agent_logs/`, owned by
   the plugin whose stated concern is read-only log analysis (adopted default from the
   survey's recommendation; the alternative, one repository-wide `denubis-common`, was
   rejected because it bundles unrelated concerns and no plugin would ship it).
3. Code enters the library when a second consumer exists or is in the same plan; logic
   with one consumer stays in its script as importable, tested functions.
4. The library carries the root lint standards per ADR 0032 and no tool tables of its own.

## Consequences

- The usage probe is rebuilt on the library with the audited deduplication rule; its
  2026-10-09 handover figures are annotated as computed under the first-seen rule.
- The branch-bg colour generator moves beside its hook, cut to its live `--emit-blocks`
  function; the retired comparison mode is not carried.
- Adoption by plugins other than the token-estimator, the ADR 0040 boundary for Codex
  quota parsing, approver pins on importing scripts, and the fate of the finished-plan
  audit script are open tickets in the project's ticket file (ADR 0044), not settled here.
