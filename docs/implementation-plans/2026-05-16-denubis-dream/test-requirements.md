# Test Requirements

Map of each acceptance criterion to its verification mechanism.

**Critical context (design DR1):** denubis-dream is a pure-skill plugin with no Python module. There is no pytest/jest/etc. test suite. Verification mechanisms are:

- **Operational (op):** the AC is verified by running a Bash command and checking output. Recorded in the UAT checklist (`plugins/denubis-dream/docs/uat-checklist.md`, produced in Phase 7).
- **UAT-human (uat):** the AC requires human judgement. Recorded in `uat-requirements.md`.
- **Inspection (insp):** the AC is verified by reading the produced artefact (e.g., a file exists with specific content, a frontmatter field has the expected value).

The UAT checklist (`uat-checklist.md`) is itself authored in Phase 7 against the AC matrix below — every `op` and `insp` row here becomes a checklist step there. Until Phase 7 lands, this matrix is the authoritative coverage list.

## AC Coverage Matrix

| AC | Description (one line) | Verification | Recorded at |
|----|------------------------|--------------|-------------|
| denubis-dream.AC1.1 | plugin.json exists with name/version/license | insp | uat-checklist.md (Phase 7) |
| denubis-dream.AC1.2 | marketplace.json contains denubis-dream entry with matching version | insp | uat-checklist.md (Phase 7) |
| denubis-dream.AC1.3 | CHANGELOG.md has [denubis-dream] 0.1.0 entry | insp | uat-checklist.md (Phase 7) |
| denubis-dream.AC1.4 | `/plugin list` shows denubis-dream | op | uat-checklist.md (Phase 7) |
| denubis-dream.AC1.5 | `/dream` invocable as slash command | op + uat | uat-checklist.md + uat-requirements.md DR1-1 |
| denubis-dream.AC1.6 | Marketplace JSON validation fails on malformed entry | op | uat-checklist.md (Phase 7) |
| denubis-dream.AC2.1 | Manual mode detected; main slug resolved from cwd (strips `/.worktrees/<name>`) | op | uat-checklist.md (Phase 7) |
| denubis-dream.AC2.2 | `--autonomous` flag detected; proceeds without prompting | op | uat-checklist.md (Phase 7) |
| denubis-dream.AC2.3 | Anchored slug scan rejects suffix-collision sibling (`<main>-2`) | op | uat-checklist.md (Phase 7, fixture-based) |
| denubis-dream.AC2.4 | Anchored slug scan finds pruned-worktree slugs whose transcript dirs persist | op | uat-checklist.md (Phase 7, fixture-based) |
| denubis-dream.AC2.5 | Invoked outside any project dir: clean failure, no dated dir created | op + uat | uat-checklist.md + uat-requirements.md DR2-1 |
| denubis-dream.AC3.1 | One per-memory Sonnet subagent dispatched per live memory file | insp | uat-checklist.md (Phase 7) |
| denubis-dream.AC3.2 | Each `.audit.md` has populated `## Evidence` with `ev-NNN:` short-UUID + line-range entries | insp | uat-checklist.md (Phase 7) |
| denubis-dream.AC3.3 | Each `.audit.md` has populated `## Code-artefact flags` (hits + misses) | insp | uat-checklist.md (Phase 7) |
| denubis-dream.AC3.4 | Per-memory subagent windows transcripts since `lastAudited` (full if absent) | insp | uat-checklist.md (Phase 7, two-memory fixture) |
| denubis-dream.AC3.5 | `flagged/region-NNN.flagged.md` files written with `## Coverage` header | insp + uat | uat-checklist.md + uat-requirements.md DR3-5 |
| denubis-dream.AC3.6 | Failed per-memory subagent → memory listed in `SKIPPED.md`; no disposition added | op | uat-checklist.md (Phase 7, induced failure) |
| denubis-dream.AC3.7 | Re-invocation re-dispatches only memories missing `.audit.md`; existing not overwritten | op | uat-checklist.md (Phase 7, mtime check) |
| denubis-dream.AC3.8 | Corpus-wide subagent windows ≥ `.last-dream`; full corpus if absent | insp | uat-checklist.md (Phase 7) |
| denubis-dream.AC4.1 | Each `.audit.md` gets `## Changes` with diff-narrative hunks citing gate | insp | uat-checklist.md (Phase 7) |
| denubis-dream.AC4.2 | Each `.audit.md` gets `## Disposition` line (keep/edit/prune) | op (grep) | uat-checklist.md (Phase 7) |
| denubis-dream.AC4.3 | Proposed-state mirror `<name>.md` written; PRUNE = single `<!-- PRUNE -->` line | insp | uat-checklist.md (Phase 7) |
| denubis-dream.AC4.4 | Dated-dir `MEMORY.md` regenerated: kept+edited included, pruned omitted, flagged not yet listed | insp + uat | uat-checklist.md + uat-requirements.md DR4-3 |
| denubis-dream.AC4.5 | `--autonomous` exits cleanly after MEMORY.md regeneration | op | uat-checklist.md (Phase 7) |
| denubis-dream.AC4.6 | Re-invocation re-judges only `.audit.md` files lacking `## Disposition` | op | uat-checklist.md (Phase 7) |
| denubis-dream.AC5.1 | Walk order = mtime ascending (stalest first) | insp | uat-checklist.md (Phase 7) |
| denubis-dream.AC5.2 | Clean-`keep` memories batched ("N memories pass cleanly — y/n?") | uat | uat-requirements.md DR5-walk |
| denubis-dream.AC5.3 | Per-memory turn blockquotes `## Evidence` + `## Changes` from `.audit.md` | uat | uat-requirements.md DR5-walk |
| denubis-dream.AC5.4 | `accept` applies proposed mirror state; no live write | op (mtime) | uat-checklist.md (Phase 7) |
| denubis-dream.AC5.5 | `prune` writes `<!-- PRUNE -->` to mirror; disposition updates | insp | uat-checklist.md (Phase 7) |
| denubis-dream.AC5.6 | `edit <instr>` revises mirror; appends `## User edits` to `.audit.md` | insp + uat | uat-checklist.md + uat-requirements.md DR5-walk |
| denubis-dream.AC5.7 | Abandon + re-invoke resumes from first entry not in `decisions.log` | op | uat-checklist.md (Phase 7) |
| denubis-dream.AC5.8 | Live `memory/` mtimes unchanged after walk | op (mtime pre/post) | uat-checklist.md (Phase 7) |
| denubis-dream.AC5.9 | Each turn appends one JSONL line to `decisions.log`; quotes/newlines parse cleanly | op (jq) | uat-checklist.md (Phase 7, edge-case fixture) |
| denubis-dream.AC5.10 | Walk-end reached → finalisation summary + y/n auto-presented | uat | uat-requirements.md DR5-walk |
| denubis-dream.AC5.11 | Re-decisions append fresh lines; finalisation uses last-write-wins | op | uat-checklist.md (Phase 7) |
| denubis-dream.AC6.1 | Flagged-region walk follows existing memories, in numeric order | insp | uat-checklist.md (Phase 7) |
| denubis-dream.AC6.2 | Per-region turn quotes excerpt + why-memory-worthy; Opus drafts scaffold | uat | uat-requirements.md DR5-walk (covers same UX surface) |
| denubis-dream.AC6.3 | `accept` writes scaffold to `promoted/<name>.md` | insp | uat-checklist.md (Phase 7) |
| denubis-dream.AC6.4 | `edit <instr>` revises scaffold; user can re-accept | insp + uat | uat-checklist.md + uat-requirements.md DR5-walk |
| denubis-dream.AC6.5 | `dismiss` leaves flagged file in place; no `promoted/` entry; discarded at finalisation | op | uat-checklist.md (Phase 7) |
| denubis-dream.AC7.1 | Finalise prompts `y/n` before any live write | uat | uat-requirements.md DR5-walk (walk-end prompt) |
| denubis-dream.AC7.2 | `.tmp` + `mv` atomic per-file pattern used | op + uat | uat-checklist.md (interrupted-finalise drill) + uat-requirements.md DR6-7 |
| denubis-dream.AC7.3 | PRUNE-marked mirrors delete live `memory/<name>.md` | op | uat-checklist.md (Phase 7) |
| denubis-dream.AC7.4 | Promoted files moved into live `memory/<name>.md` atomically | op + uat | uat-checklist.md + uat-requirements.md DR6-2 |
| denubis-dream.AC7.5 | Live `MEMORY.md` replaced via atomic pattern | op | uat-checklist.md (Phase 7) |
| denubis-dream.AC7.6 | `lastAudited` bumped to today on every surviving live file | op (yq/grep) | uat-checklist.md (Phase 7) |
| denubis-dream.AC7.7 | Promote name collision → finalise aborts, no live writes, dated dir preserved | op | uat-checklist.md (Phase 7, induced collision) |
| denubis-dream.AC7.8 | User answers `n` → exit without applying; dated dir intact | op | uat-checklist.md (Phase 7) |
| denubis-dream.AC7.9 | `.last-dream` written atomically with today's ISO date before dated-dir removal | op | uat-checklist.md (Phase 7) |
| denubis-dream.AC7.10 | `find memory/ -name '*.md.tmp' -delete` runs before success report | op | uat-checklist.md (Phase 7, orphan-injection drill) |
| denubis-dream.AC8.1 | Self-check `grep -RE '(transcript [a-f0-9]+|L[0-9]+–[0-9]+)' memory/` = zero matches | op | uat-checklist.md (Phase 7) |
| denubis-dream.AC8.2 | Dated dir removed only after self-check passes | op | uat-checklist.md (Phase 7) |
| denubis-dream.AC8.3 | Self-check non-zero → abort, report `file:line`, leave dated dir intact | op + uat | uat-checklist.md + uat-requirements.md DR6-7 |
| denubis-dream.AC8.4 | `.gitignore` lists `memory.dream-*` | insp | uat-checklist.md (Phase 7) |
| denubis-dream.AC9.1 | `schedule`-invoked `/dream --autonomous` produces same dated artefact as manual | op | uat-checklist.md (Phase 7) |
| denubis-dream.AC9.2 | Cron-mode exits without prompting after MEMORY.md regeneration | op | uat-checklist.md (Phase 7) |
| denubis-dream.AC9.3 | Cron-mode with existing dated dir for today: print path + exit (no-op) | op | uat-checklist.md (Phase 7) |
| denubis-dream.AC9.4 | `docs/cron-integration.md` exists with example, cadence, troubleshooting | insp | uat-checklist.md (Phase 7) |
| denubis-dream.AC10.1 | No operations against other projects' memory dirs (main slug only) | op | uat-checklist.md (Phase 7, two-project fixture) |
| denubis-dream.AC10.2 | Version bumps sync plugin.json + marketplace.json + CHANGELOG.md in same commit | op (git) | uat-checklist.md (Phase 7) |
| denubis-dream.AC10.3 | All 10 DoD criteria pass UAT via the checklist | uat (umbrella) | uat-checklist.md (Phase 7) |

## Gaps

Three soft gaps identified at the verification-mechanism level — see below. No AC row is unmapped: every AC1.1 through AC10.3 maps to at least one of `op`, `insp`, or `uat`. But three rows have verification mechanisms that would not catch the design's intended failure modes — the AC is technically covered, but the coverage is weaker than the AC's wording implies. The plan-validation review (`code-review-findings-plan-validation.md`) is the primary gate for catching missed ACs; this file is the safety-net cross-reference.

**Soft gaps worth naming** (every AC is mapped above; the rows below are flagged because the mechanism doesn't fully verify what the AC claims):

- **AC3.1** ("one subagent dispatched per memory") — verified by inspecting that one `.audit.md` exists per live memory after the autonomous pass. There is no direct trace of the `Task` tool invocations themselves; a buggy implementation that wrote `.audit.md` files without actually dispatching subagents would pass this inspection.
- **AC5.10** (walk-end auto-fires the y/n prompt) — covered by `uat-requirements.md` DR5-walk's "walk-end summary is wrong" failure clause, but only indirectly. A human running the walk will notice if the prompt fails to fire; no automated trigger.
- **AC7.2** (POSIX-level atomicity of `mv`) — the design's atomicity claim is a property of the kernel, not of the skill. Verification is operational only at the "interrupted finalise leaves a recoverable state" level (the Phase 7 interrupt drill), not at the syscall level.

## Notes on the "no automated tests" choice

**DR1 (Skill-driven plugin with no Python helpers)** explicitly accepts that deterministic operations — slug-prefix scan, mtime sort, atomic write, grep self-check — will not have unit-test coverage. The reasoning recorded in the design plan: every deterministic operation needed is one `Bash` line or one tool call; abstracting them into Python would not earn its weight at this stage. The precedent is `denubis-bibliography`, another skill-only plugin in the same repo.

**Consequence for this file:** there is no `tests/` directory to point at. The AC matrix above is exhaustive — if a row is not in `uat-checklist.md` (op/insp) or `uat-requirements.md` (uat), it has no verification mechanism. Phase 7's checklist is therefore load-bearing in a way it would not be in a plugin with a Python module: it is the only place an AC's pass/fail status is recorded before release.

**Consequence for reviewers:** the usual question — "does the test suite cover this AC?" — is replaced by "is this AC's UAT checklist step concrete enough that a human running it can produce an unambiguous pass/fail?". Vague steps that defer judgement back to the executor ("verify the output looks right") are unacceptable here; each step must specify the exact command, the exact expected output, and the exact failure signature. The plan-validation review applies this lens to every checklist step Phase 7 produces.

**Reevaluation trigger:** DR1 lists "tests need to be automated rather than UAT-driven" as a reevaluation trigger for the no-Python-module choice. If the UAT checklist becomes long enough or fragile enough that humans skip steps, the right move is to revisit DR1 — not to silently let the matrix above lose coverage.
