# Changelog

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
