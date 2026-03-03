# Changelog

## [denubis-git-commit] 1.1.0

Avoid command substitution injection warnings in commit commands.

**Changed:**
- Replace `git commit -m "$(cat <<'EOF'...)"` with `printf > /tmp/commit-msg.txt && git commit -F` approach
- No `$()` or backticks in the commit command, so Claude Code's injection detection doesn't trigger

## [denubis-plan-and-execute] 2.16.0

Remove workflow state machinery from statusline and all skills.

**Changed:**
- Statusline now derives all data from session JSON — no external state files, no Bash permission prompts
- Added session-level code churn (+lines/-lines) to statusline line 1
- Removed workflow breadcrumb (feature/skill/context) from statusline
- Haraway lens now conditional ("only when someone bears invisible cost") instead of mandatory on every decision
- Approval prompts must summarise what's being approved (key deliverables, AC coverage, flags raised)

**Removed:**
- `workflow-state.sh` and `workflow-state-wrapper.sh` (state writer scripts)
- `workflow-statusline.sh` (Bash duplicate of statusline renderer)
- "Workflow Status Line" sections from all 16 skills
- `~/.claude/workflow-state/` directory dependency

## [denubis-hook-branch-bg] 0.2.0

Fix colour differentiation — visible repo identity and worktree distinction.

**Changed:**
- Use `git-common-dir` instead of `--show-toplevel` so all worktrees of the same repo share a colour family
- `main`/`master` sits at the exact base colour (H=base, L=0.18, S=0.60); branches offset from it
- Branch hash offsets hue (±40°), lightness (±0.03), and saturation (±0.10)
- Lightness 0.10 → 0.18 (doubles perceptible colour range while maintaining WCAG AAA contrast)

**Fixed:**
- Worktrees appeared as unrelated colours (different `--show-toplevel` paths → different hues)
- At L=0.10 only ~3 hue groups were perceptible (brown/green/purple); now 12+ distinguishable

## [denubis-hook-branch-bg] 0.1.0

SessionStart hook for visual terminal differentiation via background colour.

**New:**
- Sets terminal background colour via OSC 11 escape sequence on session start
- Repo path controls hue (project identity), branch controls saturation (branch differentiation)
- Fixed 10% lightness for dark terminal backgrounds
- Process tree walk to find controlling TTY device, bypassing Claude Code's sandbox
- Caches nothing — deterministic colour from hash, computed each time

## [denubis-hook-rtk-rewrite] 1.0.0

Initial release as a tracked plugin (previously an unversioned file at `~/.claude/hooks/`).

**New:**
- Convention file for dispatcher auto-discovery (priority 50)
- bats test suite (33 tests)
- README with rewrite rule documentation and maintenance instructions

**Fixed:**
- `uv run pytest/ruff/playwright` no longer strips the `uv run` wrapper (was invoking system tool instead of venv tool)
- `uv pip list/install/...` now rewrites to `rtk uv pip ...` (preserves uv's pip wrapper)

**New patterns:**
- `uv run ty check` / `uvx ty check`
- `bandit` / `uv run bandit` / `uvx bandit`

## [denubis-hook-pretooluse-dispatcher] 1.1.0

**New:**
- Auto-discovery of plugin hooks via `hooks/pretooluse-bash.sh` convention file
- Plugins declare priority with `# dispatcher-priority: N` comment (default 50)
- Cache with hash-based invalidation (marketplace changes, settings changes, drop dir changes)
- `--list` diagnostics flag showing discovered hooks, sources, and cache state
- Environment variable overrides for all paths (testability)

**Changed:**
- Drop directory kept for non-plugin hooks (e.g., rtk-rewrite.sh); plugin hooks no longer need symlinks

## [denubis-hook-gh-fork-guard] 1.2.0

**Changed:**
- Replaced `gh-fork-guard-wrapper.sh` with `pretooluse-bash.sh` convention file for auto-discovery
- No manual symlink required — dispatcher discovers it from the marketplace

## [denubis-plan-and-execute] 2.15.1

**Changed:**
- Phase 3c now includes Quine-Duhem awareness: falsification experiments must interrogate their own auxiliary hypotheses before concluding, and require corroboration via a different method
- Added mandatory human checkpoint when experiment and corroboration disagree
- Added subagent delegation protocol for falsification experiments
- Credit: Ben Recht, ["Devezer's Urn"](https://www.argmin.net/p/devezers-urn) for the Quine-Duhem framing

## [denubis-hook-pretooluse-dispatcher] 1.0.0

Single PreToolUse:Bash dispatcher solving Claude Code's parallel hook execution conflict.

**New:**
- Drop directory `~/.claude/hooks/pretooluse-bash.d/` for numbered hook scripts
- Sequential execution with deterministic merge: deny > updatedInput > additionalContext
- README documenting the drop directory convention and merge rules

## [denubis-plan-and-execute] 2.15.0

**New:**
- Phase 3c (Toulmin Claim Verification) in systematic-debugging skill — every factual claim in a bug analysis must be individually verified via falsification experiments before proceeding to implementation

## [denubis-hook-gh-fork-guard] 1.1.0

**Changed:**
- Removed self-registration as PreToolUse:Bash hook — now called via the pretooluse-bash dispatcher
- Added wrapper shell script for dispatcher integration

## [denubis-00-getting-started] 1.3.0

**Changed:**
- Setup now configures the PreToolUse:Bash dispatcher, drop directory, and symlinks instead of registering standalone hooks

## [denubis-00-getting-started] 1.2.0

**New:**
- RTK (Rust Token Killer) verification step in setup — checks binary, rewrite hook, and settings registration

## [denubis-hook-claudemd-reminder] 1.1.1

**Fixed:**
- Regex now matches rtk-rewritten commands (`rtk git status`, `rtk git log`)
- Use `uv run python3` for reliable Python resolution in hook context

## [denubis-hook-gh-fork-guard] 1.0.1

**Fixed:**
- Use `uv run python3` for reliable Python resolution in hook context

## [denubis-hook-shortcut-detection] 2.0.2

**Fixed:**
- Use `uv run python3` for reliable Python resolution in hook context

## [denubis-plan-and-execute] 2.14.1

**Fixed:**
- Use `uv run python3` for code-quality-guard hook invocation

## [denubis-plan-and-execute] 2.14.0

Architecture documentation maintenance system.

**New:**
- `update-architecture-docs` inner skill for detecting contradictions and proposing architecture doc changes
- `maintain-architecture` wrapper skill and `/maintain-architecture` command for standalone maintenance sessions
- Architecture doc templates (DFD context, DFD process, database, personae, glossary, constraints, state)
- `docs/architecture/` directory convention with hierarchical DFD numbering

**Changed:**
- `writing-design-plans` now invokes `update-architecture-docs` after proleptic challenge
- `dba-reviewer` and `howto-develop-with-postgres` reference `docs/architecture/database.md` instead of `docs/database.md`
- Removed "Before Commit: Database Documentation" section from `writing-design-plans` (superseded by architecture docs step)

## denubis-hook-gh-fork-guard 1.0.0

PreToolUse hook that prevents Claude from interacting with any GitHub repo other than the user's fork.

**New:**
- Hard DENY on `gh` commands with `--repo`/`-R` targeting non-fork repos
- Hard DENY on `gh api` paths referencing non-fork repos
- Hard DENY on `gh repo` subcommands with explicit non-fork targets
- Advisory context injection on repo-interacting commands without explicit `--repo`
- Configurable via `ALLOWED_GH_REPO` environment variable (defaults to `Denubis/denubis-plugins`)

## denubis-plan-and-execute 2.13.0

First-class database documentation as a living project document.

**New:**
- `docs/database.md` convention — universe of discourse, Mermaid ERDs, data flow diagrams, data dictionary with business definitions, design decisions with rationale, denormalisation register
- `writing-design-plans` creates or updates `docs/database.md` when designs involve schema work
- `dba-reviewer` validates `docs/database.md` exists and is current during reviews; gains Edit/Write tools to update it

**Changed:**
- Missing or stale `docs/database.md` is now a HALT condition in DBA review

## denubis-plan-and-execute 2.12.0

Database schema design review and subagent turn budget management.

**New:**
- `dba-reviewer` agent — opus-model schema reviewer that halts for human decisions on normalisation, key selection, constraint completeness, and PostgreSQL anti-patterns
- Parallel DBA review in `requesting-code-review` — fires alongside code-reviewer when database changes are detected; DBA HALTs take priority
- Schema Design section in `howto-develop-with-postgres` — normalisation forms (1NF-BCNF), natural vs surrogate key decision rules, constraint strategy, relationship modelling, PG type anti-patterns
- Null/empty response detection — halts and tells the human when a subagent exhausts its turn budget

**Changed:**
- All subagent invocations now have explicit `max_turns`: task-implementor (45), bug-fixer (30), code-reviewer (25), test-analyst (20), code-simplifier (20), proleptic-challenger (15), project-claude-librarian (15), dba-reviewer (15)
- "Flaky tests" treated as halt condition — the DBA agent investigates root causes rather than accepting "flaky" as an explanation

## denubis-plan-and-execute 2.11.1

Fix code-reviewer subagent returning empty output to parent.

**Fixed:**
- Code-reviewer agent exhausting turns on mandatory skill loading before producing review output
- Missing `max_turns` on code-reviewer Task invocations (now set to 25)

**Changed:**
- Skill loading in code-reviewer is now optional (max 1 turn) — key review criteria are inlined in the prompt
- Added "Output Priority" section: structured review is the primary deliverable, agent must produce it even if investigation is incomplete
- Added `uvx bandit -r .` security scan to Python project verification commands

## denubis-plan-and-execute 2.11.0

GitHub issue lifecycle tracking across the plan-and-execute workflow.

**New:**
- Design plans gain a `**GitHub Issue:**` field linking to a GitHub issue (`#123`, `org/repo#123`, or URL)
- `design-planned` label (yellow) applied when a design plan is committed
- `implementation-planned` label (blue) replaces `design-planned` when an implementation plan is created
- Labels removed when a PR is created or branch is merged
- `workflow-state.sh` gains `--issue` flag to carry the issue reference across skills
- Labels are auto-created on the repo if they don't exist

**Changed:**
- `starting-a-design-plan` Phase 1 asks for GitHub issue reference
- `writing-design-plans` applies label after commit
- `starting-an-implementation-plan` transitions label after branch setup
- `finishing-a-development-branch` removes label on merge/PR (new Step 4b)

## denubis-plan-and-execute 2.10.0

Anti-patterns, worktree enforcement, performance fix, and fence fix.

**New:**
- "I Think This Should Work" anti-pattern in systematic-debugging and executing-an-implementation-plan
- Worktree requirement precondition in executing-an-implementation-plan
- Integration section in executing-an-implementation-plan (required workflow skills)
- cc-search-chats reference in debugging Phase 1 for searching past sessions

**Fixed:**
- Session-start hook: replaced sed/awk pipeline with bash parameter substitution (no subprocess spawns)
- Writing-implementation-plans: 4-backtick fence for infrastructure task template with nested code blocks

## denubis-plan-and-execute 2.9.0

Hard gates and data flow diagrams for the design pipeline.

**New:**
- HARD-GATE in brainstorming: no implementation until design is approved
- Anti-pattern callout: "This Is Too Simple To Need A Design"
- DFD Level 0 (context diagram) and Level 1 (pipeline decomposition) in starting-a-design-plan
- DFD Process 4.0 decomposition in brainstorming skill
- EnterPlanMode interception in using-plan-and-execute: routes through starting-a-design-plan if brainstorming hasn't happened

**Changed:**
- Mermaid diagrams use `<br>` for line breaks (VSCode compatibility)

## denubis-plan-and-execute 2.8.0

Redesigned workflow status line breadcrumbs and added experimental discipline.

**Changed:**
- Status line breadcrumb: `feature ❯ step ❯ human_verb` → `feature ❯ skill_name ❯ context_phrase`
- Smart location: worktree-aware display with `@branch` when it adds information
- `workflow-state.sh`: `--step`/`--human` replaced by `--skill`/`--context`
- Skill colours by category (design=blue, planning=magenta, execution=green, defensive=yellow, gates=cyan)
- All 14 skill files updated with new `--skill`/`--context` transition tables

**New:**
- No cut-and-try discipline in systematic-debugging and executing-an-implementation-plan: state falsifiable predictions before experiments, do the reading first, pause for feedback on contradiction
- Worktree detection in statusline (compares git-common-dir to git-dir)

## denubis-plan-and-execute 2.7.0

Code quality guards as a PreToolUse hook.

**New:**
- `code-quality-guard.py` — PreToolUse hook that checks Write/Edit operations against 6 code quality rules
- Blocking checks: E2E JavaScript injection (use Playwright APIs), `metadata.create_all()` outside Alembic
- Warning checks: Alembic migration edits, debug statements in production code, shortcut/deferral patterns, test weakening (skip/xfail)

## denubis-git-commit 1.0.0

Git commit as a proper skill, so `/commit` actually works.

**New:**
- `commit` skill — analyses changes, drafts messages, splits commits by concern, matches repo style conventions

## denubis-plan-and-execute 2.6.1

**Removed:**
- `commands/commit.md` — alias to `commit-commands:commit`, which is no longer installed

## denubis-plan-and-execute 2.6.0

Workflow status line for multi-tab awareness.

**New:**
- `scripts/workflow-state.sh` — state writer that skills call at workflow transitions, keyed by working directory
- `scripts/workflow-statusline.sh` — ANSI-coloured breadcrumb renderer for Claude Code's status line
- `docs/workflow-status-line.md` — setup documentation
- 14 skill files gain `## Workflow Status Line` sections documenting their transition points

**How it works:**
- Skills write JSON state to `~/.claude/workflow-state/<hash>.json` at each transition
- Status line renders: `feature ❯ phase ❯ step ❯ human action`
- Level 4 (human action) only appears when Claude is waiting; colours escalate with effort: dim white (Approve) → cyan (Review) → yellow (Respond) → bold magenta (Think) → red bg (ENGAGE)
- Guard pattern (`[ -x ~/.claude/bin/workflow-state ] && ...`) makes it opt-in — workflows unchanged without install

## denubis-plan-and-execute 2.5.0

Three-lens design review mode for implementation planning.

**New:**
- `writing-implementation-plans` gains a third review mode: "Review design decisions per phase (three-lens analysis)"
- Applies Popper (falsification → human-testable UAT), Lakatos (only when degenerating or genuinely progressive), and Haraway (perspective, benefit, cost) to each design decision
- Separates WHAT (decisions for human judgement) from HOW (implementation tasks for subagents)
- Lens analysis is ephemeral (conversation only) — phase files remain subagent-ready

**Changed:**
- Lakatos lens fires selectively: omitted for routine choices, present only when there's evidence of degeneration or progression worth flagging
- Requirements checklist and test requirements updated for the new mode

## denubis-hook-shortcut-detection 2.0.1

Data-driven phrase tuning from transcript mining across 708 saved sessions.

**Changed:**
- Removed "instead of" from medium-signal phrases (310 hits, ~99% false positives — overwhelmingly legitimate technical explanations)
- Added "directly rather than" as high-signal phrase (2/3 real hits were genuine process-bypassing)

**Fixed:**
- Synced local plugin.json version with marketplace (was 1.1.0, should have been 2.0.0 from E-STOP rewrite)

## denubis-plan-and-execute 2.4.0

Dependency management skills and rationale documentation.

**New:**
- `controlled-dependency-upgrade` skill — methodical one-at-a-time upgrade cycle with changelog review, falsifiable package audit, and per-package commits using uv
- `restate-our-assumptions` skill — periodic philosophical audit of dependency rationale through Popper (falsification), Lakatos (research programmes), and Haraway (situated knowledge)

**Changed:**
- `writing-design-plans` now documents new dependencies in `docs/dependency-rationale.md` with falsifiable claims before committing designs

## denubis-extending-claude 1.4.0

Librarian gains dependency and test documentation responsibilities.

**Changed:**
- `project-claude-librarian` now updates `docs/dependency-rationale.md` when dependency files change during a branch
- `project-claude-librarian` now maintains `tests/test-pseudocode.md` — human-readable test logic organised by domain, updated when test files change

## denubis-hook-shortcut-detection 2.0.0

E-STOP behavior and reliable loop prevention.

**Changed:**
- Blocks now surface the detected phrase to the user for go/no-go decision instead of asking Claude to justify itself
- Replaced message-counting loop prevention with session-keyed lockfile (one detection per session, no re-trigger loops)
- Added `suppressOutput: true` to hide hook logs from chat window

**Fixed:**
- Loop prevention no longer breaks due to system-injected messages inflating user message counts

## denubis-hook-skill-reinforcement 1.1.1

**Changed:**
- Added `suppressOutput: true` to hide hook logs from chat window

## denubis-hook-claudemd-reminder 1.1.1

**Changed:**
- Added `suppressOutput: true` to hide hook logs from chat window

## denubis-basic-agents 2.0.1

**Changed:**
- Added `suppressOutput: true` to SessionStart hook

## denubis-plan-and-execute 2.3.1

**Changed:**
- Added `suppressOutput: true` to SessionStart hook

## denubis-plan-and-execute 2.3.0

Merged upstream test planning and AC traceability features.

**New:**
- `test-analyst` agent - Analyzes test coverage and suggests test strategies
- Acceptance criteria (AC) traceability in implementation plans
- AC coverage check in final code review
- Scoped AC identifiers for cross-plan uniqueness
- Verbatim task name requirement (prevents paraphrasing that loses context)
- `user-invocable: false` for sub-skills (entry points remain invocable)

**Changed:**
- `writing-design-plans` now includes test planning workflow
- `writing-implementation-plans` adds AC traceability and skill activation during investigation
- `executing-an-implementation-plan` tracks AC coverage
- `proleptic-challenger` generates only genuine objections (no forced categories)

**Philosophy:**
- Dynamic skill activation during investigation (belt-and-suspenders with hooks)
- Tests tied to acceptance criteria at design time
- Verbatim task names preserve context through compaction

**Upstream commits:** fa258cb..bd4341f from ed3dai/ed3d-plugins

## denubis-hook-shortcut-detection 1.1.0

Loop prevention to avoid blocking repeatedly when Claude explains itself.

**Fixed:**
- Hook no longer fires repeatedly when Claude re-explains after being blocked
- After blocking, skips the next assistant message (Claude's explanation)
- Re-arms after user sends a message (user stop)

## denubis-plan-and-execute 2.2.0

Python-focused coding standards for code-reviewer agent.

**New:**
- `coding-effectively` skill - Main orchestrator for coding standards
- `python-idioms` skill - Python 3.14+, t-strings, ty, security, tooling
- `functional-core-imperative-shell` skill - FCIS pattern for testability
- `defense-in-depth` skill - Validation at system boundaries
- `writing-good-tests` skill - pytest patterns, mock strategy
- `property-based-testing` skill - Hypothesis patterns
- `howto-develop-with-postgres` skill - Transactions, ACID, naming
- `docs/coding-effectively-design.md` - Design decisions document

**Changed:**
- `code-reviewer` agent now references Python-specific skills
- Removed dependency on `ed3d-house-style` plugin

## denubis-extending-claude 1.3.0

Added upstream sync skill and rename automation script.

**New:**
- `syncing-with-upstream` skill - Documents process for integrating changes from upstream ed3d-plugins
- `scripts/rename-upstream.sh` - Automates ed3d-* to denubis-* renaming after cherry-picks

## denubis-plan-and-execute 2.1.0

Proleptic reasoning and human UAT gates.

**New:**
- `proleptic-challenger` agent - Generates counterarguments at phase transitions based on Kudina, Ballsun-Stanton & Alfano (2025) proleptic reasoning framework (DOI: 10.1007/s44204-025-00247-1)
- `proleptic-challenge` skill - Documents when and how to invoke the challenger (design finalisation, between phases, during UAT)
- `human-uat-gate` skill - Presents acceptance criteria and waits for explicit human verification after code review
- `/how-to-customize` command - Documents `.ed3d/` guidance files for project-specific customisation

**Changed:**
- `writing-design-plans` now invokes proleptic challenge before committing design
- `executing-an-implementation-plan` now includes proleptic challenge between phases and UAT gate after code review
- `requesting-code-review` now leads to proleptic challenge → UAT gate flow
- `starting-a-design-plan` loads `.ed3d/design-plan-guidance.md` before clarification (if exists)
- `starting-an-implementation-plan` loads `.ed3d/implementation-plan-guidance.md` at start (if exists)
- Code reviewers now receive implementation guidance for project-specific standards (if exists)

**Philosophy:**
- Proleptic reasoning forces deliberate evaluation before phase transitions
- "Drunk tutor" framing: both proposals AND counterarguments may be flawed
- Human UAT ensures implementations meet actual needs, not just automated checks
- Guidance files enable project-specific customisation without modifying plugin code

## [denubis-hook-shortcut-detection] 1.0.0

Initial release of shortcut detection hook.

**New:**
- Stop hook that reads Claude's transcript for shortcut phrases
- Detects high-signal phrases: "let me try a different approach", "simpler approach", "for simplicity", etc.
- Detects medium-signal phrases: "instead of", "easier to", "more efficient", etc.
- Blocks response and requires Claude to explain the problem, what was tried, and ask for explicit approval

## denubis-extending-claude 1.2.0

Added transcript archiving skill with markdown output.

**New:**
- `transcript` skill - Archive conversations with IDW2025 research metadata (Three Ps: Prompt/Process/Provenance)
- `/transcript` command to invoke the skill
- **SUMMARY.md output** - Human-readable markdown summary of archived sessions
- Integrates with `claude-transcript-archive` CLI tool

**Outputs:**
- `SUMMARY.md` - Markdown summary with Three Ps, artifacts, statistics
- `index.html` - Full HTML transcript (via claude-code-transcripts)
- `session.meta.json` - Complete structured metadata
- `raw-transcript.jsonl` - Raw conversation data

## denubis-00-getting-started 1.1.0

Renamed from ed3d-00-getting-started.

**Changed:**
- Renamed plugin from `ed3d-00-getting-started` to `denubis-00-getting-started`
- Updated all references from ed3d-plugins to denubis-plugins
- Updated author and license info

## denubis-hook-skill-reinforcement 1.1.0

Renamed from ed3d-hook-skill-reinforcement.

**Changed:**
- Renamed plugin from `ed3d-hook-skill-reinforcement` to `denubis-hook-skill-reinforcement`
- Removed "EXPERIMENTAL" label (validated by practice)
- Updated author and license info

**Proleptic Review Notes:**
- Claim: Skills should be auto-invoked via hook reminders
- Objection: Adds overhead to every prompt
- Response: Small latency cost vs. quality benefit of using appropriate skills

## denubis-hook-claudemd-reminder 1.1.0

Renamed from ed3d-hook-claudemd-reminder.

**Changed:**
- Renamed plugin from `ed3d-hook-claudemd-reminder` to `denubis-hook-claudemd-reminder`
- Updated reference from `ed3d-extending-claude` to `denubis-extending-claude`
- Updated author and license info

**Proleptic Review Notes:**
- Claim: CLAUDE.md should be maintained before commits
- Objection: Adds friction to commit workflow
- Response: Documentation drift is real; small reminder cost is worth it

## [REMOVED] ed3d-playwright

Removed JavaScript/TypeScript E2E testing plugin. Not relevant to Python/SQL/LaTeX workflow.

**Removed:**
- `playwright-explorer` agent (browser automation via MCP)
- `playwright-patterns` skill (test writing patterns)
- `playwright-debugging` skill (debugging test scripts)

Same reasoning as ed3d-house-style removal: wrong ecosystem.

## denubis-extending-claude 1.1.0

Renamed from ed3d-extending-claude.

**Changed:**
- Renamed plugin from `ed3d-extending-claude` to `denubis-extending-claude`
- Updated all internal references

**Proleptic Review Notes:**
- TDD for skills validated: pressure scenarios verify behavior change
- "One excellent example" principle validated (use Python for Brian's workflow)
- project-claude-librarian useful for maintaining documentation

## denubis-plan-and-execute 2.0.0

Renamed from ed3d-plan-and-execute with significant philosophy changes.

**Changed:**
- Renamed plugin from `ed3d-plan-and-execute` to `denubis-plan-and-execute`
- **task-implementor now uses Opus** (was Haiku) - fewer mistakes, fewer review cycles
- Renamed `task-implementor-fast` to `task-implementor` (no longer optimizing for speed)
- Updated Python references (pytest, ruff instead of npm/eslint)

**New:**
- **Halt-on-non-obvious-failures policy**: If test fails in non-obvious way, STOP immediately and report. No grinding for 30 minutes working around problems.

**Proleptic Review Notes:**
- Kept "block on ALL severities" (quality over velocity)
- Three-phase workflow validated (not for simple tasks, but boundary guidance could be clearer)
- /clear between phases validated (artifacts are committed, can re-read)

## denubis-research-agents 1.1.0

Renamed from ed3d-research-agents.

**Changed:**
- Renamed plugin from `ed3d-research-agents` to `denubis-research-agents`
- Updated author and license info

**Proleptic Review Notes:**
- Design validated: response-only output prevents file pollution while design docs capture findings
- Shallow cloning (`--depth 1`) addresses performance concerns
- Sequential exploration appropriate for iterative investigation (parallelization better for independent checks)

## [REMOVED] ed3d-house-style

Removed TypeScript/React-focused house style plugin. Not relevant to Python/SQL/LaTeX workflow.

**Removed skills:**
- howto-code-in-typescript (and typebox, type-fest sub-resources)
- programming-in-react (and useEffect, react-testing sub-resources)
- coding-effectively (TypeScript-focused)
- All other Ed's opinionated standards

May create denubis-house-style with Python/SQL/LaTeX focus later.

## denubis-basic-agents 2.0.0

Renamed from ed3d-basic-agents and customized for Python/academic workflows.

**New:**
- `python-developer` agent - Sonnet-based agent with Python 3.14 idioms:
  - T-strings for security-sensitive string processing (SQL, HTML, shell)
  - Deferred annotations (no string quotes for forward references)
  - Bracketless exception handling (PEP 758)
  - Finally block discipline (PEP 765)
  - Unified compression module with zstd preference (PEP 784)
  - concurrent.interpreters for CPU-bound parallelism (PEP 734)
- `academic-researcher` agent - Opus-based agent with academic rigor (citations, argument structure, LaTeX conventions) baked in

**Changed:**
- Renamed plugin from `ed3d-basic-agents` to `denubis-basic-agents`
- Updated `using-generic-agents` skill to document domain agents alongside generic agents
- Model characterizations reframed as "heuristics, not absolute truths"
- Added explicit "when to use domain agents" guidance

**Proleptic Review Notes:**
- Addressed objection that "unprompted" agents lack domain guidance by adding domain variants
- Addressed objection that model tier hierarchy is oversimplified by reframing as heuristics
- Kept mandatory skill-checking (latency cost is small vs. quality benefit)

## ed3d-plan-and-execute 1.6.2

Fixes "Re-read skill" task dependency ordering.

**Fixed:**
- "Re-read skill" task must be re-pointed to Finalization task after granular tasks are created (was incorrectly blocked by "Create implementation plan")
- Added "After Planning: Update Dependencies" step to ensure correct task ordering

## ed3d-plan-and-execute 1.6.1

Fixes task tracking to include dependencies and absolute paths.

**Fixed:**
- Tasks now use addBlockedBy to enforce execution order (NA→NB→NC→ND, then next phase)
- Task descriptions include absolute paths for design file and output file, so tasks remain actionable after compaction

## ed3d-plan-and-execute 1.6.0

Adds granular task tracking to implementation plan writing to survive context compaction.

**New in `writing-implementation-plans`:**
- **Granular per-phase tasks:** Instead of one task per phase, now creates sub-tasks for each step:
  - Phase NA: Read [Phase Name] from design plan
  - Phase NB: Dispatch codebase-investigator to verify current state
  - Phase NC: Research external dependencies (if applicable)
  - Phase ND: Write phase file to disk
- **Finalization task:** Explicitly states "fix ALL issues including minor ones" — model cannot rationalize skipping minor issues
- **Plan validation as tracked task:** Must complete with zero issues before handoff

**New in `writing-design-plans`:**
- **Phase markers:** Design plans now require `<!-- START_PHASE_N -->` / `<!-- END_PHASE_N -->` markers around each implementation phase, enabling granular parsing

**New in `starting-an-implementation-plan`:**
- **Orchestration tasks:** Tracks Branch setup, Create implementation plan, Re-read skill, Execution handoff
- **Restore context step:** Re-reads skill before handoff to restore instructions post-compaction
- **Terminology clarification:** Renamed "Phase 1/2/3" to descriptive names (Branch Setup, Planning, Execution Handoff) to avoid confusion with implementation plan phases

**Fixed:**
- Code reviewer step was being forgotten after compaction — now tracked as explicit Finalization task
- Minor issues were being skipped — task text now makes fixing them mandatory

## ed3d-plan-and-execute 1.5.1

Updates task tracking references for compatibility with new Claude Code task system.

**Changed:**
- All references to `TodoWrite` now prefer `TaskCreate`/`TaskUpdate`/`TaskList` (the new task tools in Claude Code)
- Backwards-compatibility notes added for older Claude Code versions that still use `TodoWrite`

## ed3d-extending-claude 1.0.1

Updates task tracking references for compatibility with new Claude Code task system.

**Changed:**
- Tool tables and examples now reference `TaskCreate`/`TaskUpdate` instead of `TodoWrite`
- Backwards-compatibility notes added for older Claude Code versions

## ed3d-house-style 1.0.1

Updates task tracking references for compatibility with new Claude Code task system.

**Changed:**
- Persuasion principles documentation now references `TaskCreate`/`TaskUpdate` instead of `TodoWrite`
- Backwards-compatibility notes added for older Claude Code versions

## ed3d-plan-and-execute 1.5.0

Promotes experimental execution workflow to stable.

**Changed:**
- Execution workflow now uses just-in-time phase loading (reads one phase at a time, not all upfront)
- Code review happens once per phase instead of between every task
- TodoWrite structure: three entries per phase (Read, Execute, Code review) with absolute paths and titles
- Subagents receive phase file path and read it themselves

**Removed:**
- Experimental skill and command (merged into stable)
- Task grouping by subcomponent (plan phases now define grouping via markers)
- Task-level code review (replaced with phase-level review)

## ed3d-plan-and-execute 1.4.3

Removes misleading directive from implementation plan header.

**Fixed:**
- Removed "For Claude: REQUIRED SUB-SKILL" directive from plan header template — was being parsed by task-implementor subagent when it should only be used at the top-level orchestrator

## ed3d-plan-and-execute 1.4.2

Simplifies experimental execution workflow.

**Changed:**
- Experimental skill now reads first 10 lines (not 3) to capture Goal in header
- Subagents (task-implementor, bug-fixer) now read entire phase file instead of extracted sections
- Removed context window extraction logic — simpler approach, let subagents see full phase context

## ed3d-plan-and-execute 1.4.1

Adds experimental execution workflow and task markers. (1.4.0 was a buggy mis-push.)

**New:**
- **Task and subcomponent markers** in implementation plans: `<!-- START_TASK_N -->`, `<!-- END_TASK_N -->`, `<!-- START_SUBCOMPONENT_A (tasks 3-5) -->`, etc.
- **Experimental execution skill** (`executing-an-implementation-plan-experimental`) with just-in-time phase loading, context windows for subagents, and marker-based extraction
- **Experimental command** (`/execute-implementation-plan-experimental`) to invoke the experimental workflow

**Changed:**
- `writing-implementation-plans` now generates markers in all task templates (backwards compatible — old execution skill ignores them)

## ed3d-plan-and-execute 1.3.3

Fixes execution handoff to use absolute paths, preventing wrong-directory issues after /clear.

**Fixed:**
- Execution handoff now captures absolute paths via `git rev-parse --show-toplevel` and verifies plan directory exists before outputting command
- After `/clear`, users land in the original session directory (often repo root, not worktree) — absolute paths ensure execution happens in the correct directory regardless

**Changed:**
- `/execute-implementation-plan` command now accepts two arguments: `[absolute-plan-dir]` and `[absolute-working-dir]`
- Command verifies both paths exist and changes to working directory before engaging skill

## ed3d-plan-and-execute 1.3.2

Fixes execution handoff to pass plan directory instead of single phase file.

**Fixed:**
- Execute-implementation-plan instructions now pass the plan directory (e.g., `@docs/implementation-plans/YYYY-MM-DD-feature/`) instead of a single phase file — prevents agent from only implementing the first phase

## ed3d-plan-and-execute 1.3.1

Improves resolution of Definition of Done in design plans.

**Changed:**
- Definition of Done is now written to the design document immediately after user confirmation (Phase 3), rather than being reconstructed later during documentation (Phase 5)
- Design document file is created in Phase 3 with DoD and placeholders for Summary/Glossary
- writing-design-plans skill now appends body sections and generates only Summary/Glossary

**Fixed:**
- Corrected stale skill name references ("subagent-driven-development", "executing-plans") to "executing-an-implementation-plan"
- Reinforced that Minor issues from code review must be fixed (model was skipping them)
- Changed `/compact` to `/clear` between phases, with warning to copy next command first

## ed3d-plan-and-execute 1.3.0

Adds legibility header to design plans for human reviewers.

**New:**
- **Phase 3: Definition of Done** — New checkpoint after clarification to confirm deliverables before brainstorming
- **Legibility header** — Design plans now include Definition of Done, Summary, and Glossary sections at the top
- **Subagent extraction** — Uses fresh-context subagent to generate legibility header after writing body
- **Glossary transparency** — Subagent reports omitted "obvious" terms so user can request additions

**Changed:**
- Phases renumbered 1-6 (was 1, 2, 2b, 3, 4, 5)
- Task invocations in skills now use XML block format

## ed3d-plan-and-execute 1.2.0

Added external dependency research capabilities to implementation planning.

**Changed:**
- **writing-implementation-plans**: Added tiered external dependency research workflow. Phases involving external libraries now trigger research via `internet-researcher` (for docs/standards) with escalation to `remote-code-researcher` (for source code) when documentation is insufficient.

**New capabilities:**
- Decision framework for when to research external dependencies
- Tiered research approach: docs first, source code when needed
- External dependency findings section in phase output templates
- Updated per-phase workflow to include research step
- New rationalizations to prevent skipping external research

## ed3d-plan-and-execute 1.1.0

Corrects design plan level of detail. These changes were a missed port from the internal plugin marketplace and were intended for 1.0.0. This release represents the plugin "as intended."

**Changed:**
- **writing-design-plans**: Design plans now stay at component/module level, not task level. Contracts/interfaces can be fully specified; implementation code cannot.
- **brainstorming**: Added guidance on level of detail in Phase 3. Validates boundaries, not behavior.
- **writing-implementation-plans**: Strengthened codebase verification as source of truth. Implementation plans generate code fresh from investigation, never copy from design.
- **README**: Added "Philosophy: What Each Phase Produces" section explaining archival vs just-in-time distinction.

## ed3d-research-agents 1.1.0

Added `remote-code-researcher` agent for investigating external codebases by cloning and analyzing their source code.

**New agent:**
- `remote-code-researcher` - Answers questions about external libraries/frameworks by cloning repos to temp directories and investigating the actual source code. Combines web search (to find repos) with codebase investigation (to analyze cloned code).

## All plugins 1.0.0

Initial release of ed3d-plugins collection.
