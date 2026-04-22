# Issues

Local issue tracking for `brian-ed3d-plugins`. Used in preference to GitHub issues for this repo.

## Format

Each issue is an `### ISSUE-NN: Title` section with:

- **Status:** open | in-progress | deferred | closed
- **Opened:** YYYY-MM-DD
- **Origin:** where this came from (plan name, session, observation)
- **Description:** what the issue is, in enough detail for a fresh session to pick up.
- **Proposed approach:** how to address it (may say "needs design plan").
- **Related:** files, plans, PRs, prior reviews.

Issues are numbered sequentially. Add new ones at the bottom of the Open section; move to Closed when resolved with a one-line outcome note.

---

## Open

### ISSUE-01: Promote `phase_05_cross_ref_audit.py` to common Typer-based tool with architecture coverage

- **Status:** open
- **Opened:** 2026-04-19
- **Origin:** `critical-peer-review-2026-04-18` of `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/` — H1 discussion in that plan's revision session. The in-scope revision shrank back to the regex fix in the embedded script; tool promotion was recognised as legitimately out-of-scope for the upstream sync plan.

**Description:**

The cross-reference audit currently lives as an embedded Python script in `phase_05.md` Task 1 of the skill-skills upstream sync plan — plan-specific, five hard-coded TARGETS, argparse-based. During H1 discussion we identified several structural improvements that together warrant a proper tool rather than an ever-growing embedded script:

1. **Common tool, not plan-scoped script.** The audit should be reusable across plans and periodic audits, not re-authored per plan.
2. **Typer CLI with proper help infrastructure.** Rich `--help`, repeatable target arguments, `--repo-root` with git-toplevel auto-detect, `--check-architecture` flag, `--json` output, `--verbose` / `-v` flag. `typer.Exit` for exit codes.
3. **Follow the `workflow_statusline` pattern** under `plugins/denubis-plan-and-execute/scripts/`. Structure:
   ```
   plugins/denubis-plan-and-execute/scripts/xref_audit/
   ├── pyproject.toml          # hatchling-built, typer dep, pytest dev dep
   ├── uv.lock
   ├── src/
   │   └── xref_audit/
   │       ├── __init__.py
   │       ├── __main__.py     # Typer entry point
   │       ├── audit.py        # core audit logic
   │       └── architecture.py # architecture-presence check
   └── tests/
       ├── __init__.py
       ├── test_audit.py
       └── test_architecture.py
   ```
4. **Extend target coverage to `architecture-update`.** Part of the motivation is that architecture-update's `SKILL.md` and DFD templates currently teach bare-filename cross-reference form — path-form is what the audit can validate. The tool should audit the architecture-update skill AND the architecture-update skill should teach path-form examples.
5. **New architecture-presence check.** WARN (not FAIL) when `docs/architecture/` is absent, reporting "consider `/maintain-architecture` to scaffold." WARN messages print separate from FAILs; do not affect exit code.
6. **Template updates as part of the promotion:** `architecture-update/SKILL.md` "Cross-Reference Format" section (lines ~66-71 and the "See `template-X.md`" line ~75) and `architecture-update/template-dfd-context.md` line 38 + `architecture-update/template-dfd-process.md` lines 58-59 should be converted from bare-filename to path-form examples (`docs/architecture/dfd/0-context-diagram.md`, `./template-dfd-context.md`, etc.). Other five templates were grepped clean during the H1 discussion.
7. **Skill gates for internal documentation consistency.** The tool's value compounds when it runs automatically at the right moments. A skill (e.g., `/audit-xref` or invoked transitively from an orchestrator skill) wraps the tool; Claude Code hooks invoke that skill as gates on documentation-touching operations. Proposed trigger points:
   - `PostToolUse` on `Edit` / `Write` when the touched path matches `**/SKILL.md`, `docs/**/*.md`, or known plan/design directories — run the audit, surface FAILs as `additionalContext`.
   - `Stop` — run the full audit at session end; emit `decision: "block"` with `reason` if there are unresolved FAILs in the working tree.
   - Optional pre-commit-style via `PreToolUse` on `Bash` when the command is `git commit …` — block commits that would ship broken references.
   The hooks themselves must fail cleanly: sensible exit codes, actionable messages, no stack traces to the user, no noisy false alarms. (Reference for "fails cleanly" in this repo: the existing `shortcut-detector.py` Stop hook's surfacing pattern.)

**Why deferred from skill-skills upstream sync:**

The in-scope work for that plan is the upstream sync itself (renaming/syncing five skills from obra, keeping terminology current). Promoting the audit script to a common tool + editing the architecture-update skill is legitimately orthogonal. Doing both in the revision session would have batch-fixed without the Ripple-Rule discipline that `critical-peer-review` reviewer-2026-04-18 flagged as missing from the prior revision.

**Proposed approach:**

Treat this as its own design plan via `/starting-a-design-plan`. Brainstorm → design → plan → implement.

Entry context for that session:
- Current embedded script location (post-H1 regex fix, see skill-skills upstream sync phase_05.md Task 1)
- The two regexes the H1 fix lands: `PATH_REF_RE` (requires `/`) and `LINK_REF_RE` (markdown link form)
- `workflow_statusline` directory as structural reference
- Architecture-update's current bare-filename teaching + which templates are affected
- Question to resolve in design: auto-discovery (`--all` walks `plugins/*/skills/*`) vs explicit-target-only; the in-scope-for-H1 decision was explicit-target-only, but the tool may want `--all` as a proper feature.

**Related:**

- `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05.md` — embedded script (post-H1 regex fix)
- `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/critical-peer-review-2026-04-18.md` — H1 finding that surfaced the discussion
- `plugins/denubis-plan-and-execute/skills/architecture-update/SKILL.md`
- `plugins/denubis-plan-and-execute/skills/architecture-update/template-dfd-context.md`
- `plugins/denubis-plan-and-execute/skills/architecture-update/template-dfd-process.md`
- `plugins/denubis-plan-and-execute/scripts/workflow_statusline/` — reference tool pattern
- `plugins/denubis-plan-and-execute/skills/maintain-architecture/SKILL.md` — context on the architecture-presence gap

---

### ISSUE-02: Agent teams integration design paused at Phase 2 — Zendo experiment invalidated core assumption

- **Status:** open
- **Opened:** 2026-04-19 (thread origin: 2026-03-12 Zendo experiment, captured as WIP from that date)
- **Origin:** `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/project_agent-teams-design-wip.md`; chat sessions 3734fee0, 446ec08a, 21a34e92 (all 2026-03-12).

**Description:**

The agent-teams integration design (team code-review, team proleptic-challenge, team systematic-debugging, team three-lens) was paused mid-Phase-2-Clarification for a Zendo experiment that would test whether agent teams could collaborate adversarially. The experiment ran and returned failure: inter-agent messaging produced convergence/groupthink, not adversarial collaboration. The assistant's own 2026-03-12 summary: *"Team debugging | Dangerous — exact Zendo failure | High — proven by experiment."*

The WIP memory flags the mechanism question as open: team-with-inter-agent-messaging vs parallel-subagents-with-lead-synthesis. Phases 3–6 of the design are PENDING. No subsequent session has decided to abandon or pivot.

**Proposed approach:**

Start with a one-page decision record (halt-or-pivot), not a full design plan. The pointed question: does Zendo invalidate team-with-messaging universally, or only for adversarial patterns? If universally, the four team skills should not be built. If only adversarial, parallel-subagents-with-lead-synthesis may be the right mechanism for the four proposed skills.

**Related:**

- `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/project_agent-teams-design-wip.md`
- Chat sessions 3734fee0 (Zendo experiment), 446ec08a (Zendo team), 21a34e92 (student-alpha's hypotheses)

---

### ISSUE-03: Parts 2–4 of the upstream sync programme — design sessions not yet started

- **Status:** open (blocked on ISSUE-06 for Part 2; Part 3 further blocked on ISSUE-02)
- **Opened:** 2026-04-19 (thread origin: 2026-04-17 design plan scope exclusions)
- **Origin:** `docs/design-plans/2026-04-17-skill-skills-upstream-sync.md` DoD section ("Explicitly out of scope for Part 1") + Handoff section.

**Description:**

The skill-skills upstream sync is Part 1 of a planned multi-part upstream alignment programme. The three follow-on parts are named but undefined:

- **Part 2 — Other upstream innovations beyond skill-skills.** Includes the four skill-skills deferred from Part 1 (`writing-claude-md-files`, `maintaining-project-context`, `creating-a-plugin`, `creating-an-agent`) plus any other innovations obra has produced. Part 2's design also owns the "obra upstream drift" question (one-time sync vs ongoing automation).
- **Part 3 — Critique skills / agents.** Named but undefined. Likely depends on ISSUE-02 resolving — critique patterns are exactly where Zendo failure is most dangerous.
- **Part 4 — PromptGrimoireTool / MELICA tuning.** Named but undefined; "MELICA" has no explanation in any accessible session.

**Proposed approach:**

Sequence, do NOT batch:
1. Part 1 execution (ISSUE-06) lands
2. Part 2 design via `/starting-a-design-plan`
3. Part 3 design (after ISSUE-02 resolved)
4. Part 4 via `/flesh-it-out` first (to define what it is), then design

**Related:**

- `docs/design-plans/2026-04-17-skill-skills-upstream-sync.md`
- ISSUE-02 (blocker for Part 3)
- ISSUE-06 (blocker for Part 2)

---

### ISSUE-04: "Eyeball N%" → stratified-sampling skill

- **Status:** open
- **Opened:** 2026-04-19 (thread origin: 2026-04-17 parallel-session audit during impl-plan-write brainstorming)
- **Origin:** `docs/design-plans/2026-04-17-skill-skills-upstream-sync.md` Additional Considerations, "Eyeball N%" paragraph.

**Description:**

During a 2026-04-17 parallel-session audit, a validator subagent proposed "eyeball 10%" as sample size for a 7,200-item dataset — 720 items, infeasible. A researcher subagent countered with failure-rate-driven stratified sampling (140 items at ~2%) as the defensible alternative. The design plan flagged this as a follow-up skill:

> A future small skill should (a) name the "eyeball N%" cognitive pattern when a validator proposes a percentage, (b) convert to a failure-rate-driven stratified sample size... Out of scope for this implementation plan — flagged here so the finding survives into a follow-up design session.

The pattern is well-defined; the solution is demonstrated. The main design question is which plugin (`denubis-research-agents` vs `denubis-plan-and-execute`) and which skill shape (technique-type vs reference-type per obra taxonomy).

**Proposed approach:**

Could skip a full design plan — `/flesh-it-out` + `/writing-skills` may suffice. Alternative: fold into ISSUE-03's Part 2 scope if the Part 2 design session wants to bundle small deferred skills.

**Related:**

- `docs/design-plans/2026-04-17-skill-skills-upstream-sync.md` Additional Considerations

---

### ISSUE-05: AbsenceJudgement fabricated-codes repo-wide audit

- **Status:** open
- **Opened:** 2026-04-19 (thread origin: 2026-04-17 DR4 + feedback memory)
- **Origin:** `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/feedback_absencejudgement-codes-fabricated.md`; design plan Additional Considerations ("Fabricated-codes propagation").

**Description:**

The AbsenceJudgement paper taxonomy codes (TEMP/RAND/SCOP/VIBE/FABR failure codes; MECH/MTCH/SCAF/BOUN success codes) are fabricated — not in the paper. A prior session invented them; they spread via handoff prompts. The upstream-sync plan's Phases 1 and 4 grep-audit the four touched skills specifically. A broader repo-wide audit (all `SKILL.md`, design plans, `CLAUDE.md`, memory files, plan phase files) has not been run.

**Proposed approach:**

Two paths (preference: first):
1. **Add as a check pattern within ISSUE-01's xref-audit tool.** Natural fit — "forbidden tokens that should not appear" is the inverse of "references that should resolve." When the tool is built, a `--check-forbidden-tokens` mode lists patterns (starting with the AbsenceJudgement codes) and flags any occurrence.
2. **Standalone one-off audit.** Run now, before or after Part 1 execution, as a Bash grep across the repo.

**Related:**

- `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/feedback_absencejudgement-codes-fabricated.md`
- ISSUE-01 (proposed fold target)

---

### ISSUE-06: Skill-skills upstream sync plan never executed — uncommitted on main, no feature branch, execution handoff not started

- **Status:** open (blocked on completion of second-review revision — in progress this session)
- **Opened:** 2026-04-19 (thread origin: 2026-04-18)
- **Origin:** `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/RESUME-PROMPT.md`; `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/critical-peer-review-2026-04-18.md` finding M5.

**Description:**

The skill-skills upstream sync plan has been authored, twice peer-reviewed, and once revised (second revision is in progress in the current session). All work sits in planning documents — the actual skill artefacts (`epistemic-humility`, `writing-skills` rewrite, `testing-skills-with-subagents` restructure, `writing-claude-directives` restructure, `impl-plan-write` hardening) have not been produced.

All planning work is also uncommitted on `main`. The plan's AC5.5/5.6 commit-discipline checks use `git log main..HEAD` — which returns zero if run on main itself. Execution must happen on a feature branch via `/using-git-worktrees` (this is also critical-peer-review-2026-04-18's finding M5).

**Proposed approach:**

Sequence after the current session's revision completes:
1. Create feature branch via `/using-git-worktrees`
2. Update `RESUME-PROMPT.md` to reflect second-review-resolved state + branching context
3. Invoke `/executing-an-implementation-plan`

**Related:**

- `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/RESUME-PROMPT.md`
- `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/critical-peer-review-2026-04-18.md` (M5)

---

### ISSUE-07: `/maintaining-project-context` never invoked after any completed plan

- **Status:** open (systemic gap)
- **Opened:** 2026-04-19 (thread origin: negative-results observation from 2026-04-19 thread audit)
- **Origin:** Absence evidence: no session in the project's chat history shows the skill being invoked after any of the shipped plans (`project-context-inventory`, `proleptic-reasoning-uat-gates`, `shortcut-detection-hook`, `maintain-arch-docs`, `adr-enrichment`).

**Description:**

The `/maintaining-project-context` skill (in `denubis-extending-claude`) exists to run after completed development work and keep `CLAUDE.md` / `AGENTS.md` files current. It is never invoked. `CLAUDE.md` files across the repo are potentially out-of-date relative to shipped plans.

Two sub-concerns:

1. **Workflow gap:** no skill or command explicitly calls `/maintaining-project-context` at plan close. The skill relies on the user (or an orchestrator) remembering to run it.
2. **Retroactive drift:** even if the workflow is fixed, the five shipped plans' contexts may not be reflected in current `CLAUDE.md` files.

**Proposed approach:**

Discussion before retroactive work. The pointed question: is this a discovery problem (the skill's auto-trigger description isn't matching plan-close contexts), an orchestration problem (no skill explicitly calls it), or a user-habit problem (never remembered)? The fix depends on the answer. Retroactive catch-up (one invocation per shipped plan) should only happen once the trigger problem is resolved — otherwise the gap will reproduce.

**Related:**

- `plugins/denubis-extending-claude/skills/maintaining-project-context/SKILL.md`
- All five shipped plans in `docs/implementation-plans/` (potential retroactive audit scope)

---

### ISSUE-08: "Fast test" sideline for `/commit` skill

- **Status:** open
- **Opened:** 2026-04-19 (thread origin: 2026-03-13, session 25858764)
- **Origin:** Chat session 25858764, 2026-03-13, user message: *"yes, commit should also discover and run, but only unit tests. We should have a 'fast test' sideline."*

**Description:**

During a `/commit` skill discussion on 2026-03-13, the user directed that the commit workflow should discover-and-run unit tests — not full suites — as part of commit preparation. A "fast test" sideline: prevent shipping broken unit tests without blocking on slow integration tests. The direction was acknowledged but did not land in the `/commit` skill (verified by absence of fast-test logic in `plugins/denubis-git-commit/`).

**Proposed approach:**

Likely a small edit to `plugins/denubis-git-commit/skills/commit/SKILL.md`:

- Step between "draft commit message" and "commit": discover pytest fast-test markers (convention TBD — `@pytest.mark.fast` or under-N-seconds heuristic) and run only those.
- Gate the commit on passing: surface failures as a "commit anyway?" confirmation rather than hard-block.

Warrants a brief `/design-clarify` step first: what marker convention, what timeout, does the sideline also run for non-Python repos.

**Related:**

- `plugins/denubis-git-commit/skills/commit/SKILL.md`
- Chat session 25858764 (2026-03-13)

---

### ISSUE-09: Resume-aware transcript archiving TODO (transcript-archive plugin, out-of-repo)

- **Status:** open (external plugin)
- **Opened:** 2026-04-19 (thread origin: 2026-04-08, session 59aaea81)
- **Origin:** Chat session 59aaea81, 2026-04-08, assistant message: *"Want me to handle the simple case first (fresh interactive only) and leave resume-aware archiving as a TODO?"*

**Description:**

The `transcript-archive:transcript` skill (lives in a plugin outside this repo) was designed with a scope carve-out: resume-aware archiving — handling sessions that resume from a prior session ID rather than starting fresh — was explicitly deferred as a TODO while the simple fresh-interactive case was built. Current status of the TODO is unverified; the plugin source is not in this repo.

**Proposed approach:**

Two steps:
1. Verify current state: does the transcript-archive plugin now handle resume-aware sessions? If yes, close this issue.
2. If not, fix in the plugin source (location owned by the user; not this repo).

Tracking here because the user's workflow concern crosses repo boundaries — issues tracker catches it even though the fix lands elsewhere.

**Related:**

- Chat session 59aaea81 (2026-04-08)
- `transcript-archive:transcript` skill (external source)

---

### ISSUE-10: cc-search-chats FTS5 query fragility — hyphens and apostrophes crash the CLI

- **Status:** open (upstream tool defect)
- **Opened:** 2026-04-19 (empirically verified during 2026-04-19 thread-audit execution)
- **Origin:** Direct CLI test:
  - `cc-search-chats search "resume-aware" --json` → `sqlite3.OperationalError: no such column: aware`
  - `cc-search-chats search "we don't care about" --json` → `sqlite3.OperationalError: fts5: syntax error near "'"`

**Description:**

The `cc-search-chats` CLI accepts a single query string and passes it directly to SQLite FTS5 `MATCH` without escaping or pre-processing. Consequences:

- **Hyphenated tokens** (`"resume-aware"`) are parsed as column-qualified queries (`resume:aware` style) and crash because `aware` isn't a column.
- **Apostrophes** (`"we don't care"`) break the SQL tokenizer before FTS5 even sees the query.
- **Reserved words** (`"project"` used in earlier tests) collide with column names.

This is an upstream tool defect — the CLI should quote, escape, or pre-process user input before passing to FTS5.

**Why this matters for this repo:**

1. The current skill-skills upstream sync plan's AC5.8 frustration-signal audit (Phase 5 Task 4.5) includes queries with apostrophes (e.g., `"that's wrong"`) — those queries WILL crash the CLI, not just return zero hits. This empirically reinforces the current review's M2 finding.
2. Any future in-repo skill that invokes cc-search-chats needs defensive query construction.

**Proposed approach:**

Two independent paths:
1. **Upstream fix:** patch cc-search-chats to pre-process queries (phrase-quote the whole string for FTS5, or escape special characters). User owns the tool; small fix.
2. **Downstream workarounds:**
   - Current review's M2 revision must reference this issue and prescribe the workaround pattern (one-term-per-query, executor unions results, avoid apostrophes by using alternative spellings).
   - Any future plan or skill invoking cc-search-chats documents the fragility and example-safe queries.

**Related:**

- `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/critical-peer-review-2026-04-18.md` M2 finding
- cc-search-chats CLI source (out-of-repo)

---

### ISSUE-11: Reflective session-history pass as part of finalisation

- **Status:** open
- **Opened:** 2026-04-22
- **Origin:** Migrated from GitHub issue #1 (opened 2026-02-08). Inspired by Martin Alderson's "Self-Improving CLAUDE.md Files".

**Description:**

The auto-memory system already captures per-session feedback, user, and project patterns. The remaining gap is **cross-session recurrence detection** — patterns that only become visible when you search multiple sessions for the same kind of friction (repeated corrections, recurring setup instructions, consistent user overrides of defaults, frustration signals). Currently this signal is latent in chat history and is never surfaced.

The natural home is a *reflective pass* invoked as part of finalisation — at phase boundaries or when finishing a development branch — that reviews the relevant session range for cross-session patterns and proposes CLAUDE.md or memory additions for user approval.

**Proposed approach:**

New user-invocable skill (tentatively `review-session-patterns`) in `denubis-extending-claude`:

- Uses `cc-search-chats` as a soft dependency (detect at runtime; instruct user to install if missing, do not crash).
- Two-pass: signal-search (pattern queries across N most recent sessions) → context-extraction on hits.
- Recurrence threshold: only surface patterns appearing in 2+ separate sessions. One-off corrections are noise.
- Groups findings by category (conventions, commands, gotchas, frustration markers).
- Presents proposals for user approval; never auto-writes.
- Optional invocation hook from `finishing-a-development-branch` and/or `maintaining-project-context` (only if `cc-search-chats` is available; fail gracefully otherwise).

Interaction with existing auto-memory: complementary, not redundant. Auto-memory captures signals within a session; this skill detects them across sessions.

**Related:**

- GitHub issue #1 (original, now closed as migrated)
- `cc-search-chats` plugin (out-of-repo; installed)
- `plugins/denubis-extending-claude/skills/writing-claude-md-files/SKILL.md`
- `plugins/denubis-extending-claude/skills/maintaining-project-context/SKILL.md`
- `plugins/denubis-plan-and-execute/skills/finishing-a-development-branch/SKILL.md`
- ISSUE-10 (cc-search-chats FTS5 fragility — must be resolved or worked around before this skill is reliable)

---

## Closed

*(No closed issues yet.)*
