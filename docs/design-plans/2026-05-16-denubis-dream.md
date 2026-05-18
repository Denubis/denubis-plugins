# denubis-dream Design

**GitHub Issue:** None

## Summary

`denubis-dream` is a new Claude Code plugin that audits a project's per-project auto-memory against the historical record of Claude Code conversations. Auto-memory files (small markdown documents Claude reads at session start) drift over time: facts become stale, code artefacts get renamed, and memory-worthy insights from recent conversations never get written down. The `/dream` skill addresses this by reading every live memory file, cross-referencing it against the transcript corpus for that project and all its worktrees, and producing a reviewable proposed-change tree in a scratch directory — without touching live memory during the audit.

The implementation is a pure skill-driven pipeline with no Python helpers, following the `denubis-bibliography` precedent. Sonnet subagents run in parallel to collect evidence per memory and flag transcript regions that look memory-worthy but have no corresponding memory. An Opus judgement pass then applies five evaluative gates to each memory and proposes a disposition (`keep`, `edit`, or `prune`). In manual mode the user walks the proposals interactively — reviewing blockquoted evidence, accepting or overriding each recommendation, and promoting flagged transcript regions into new memories — before a finalisation step applies the accepted changes atomically to live memory. A `--autonomous` flag allows cron-scheduled runs that produce the same audit artefact but skip the interactive walk entirely.

## Definition of Done

**Primary deliverable:** A new `denubis-dream` plugin providing the `/dream` skill that audits per-project auto-memory against worktree-aggregated transcripts and produces a reviewable proposed memory tree.

**Success criteria:**

1. **Plugin exists in this repo.** `plugins/denubis-dream/` contains `.claude-plugin/plugin.json`, with matching entries in `.claude-plugin/marketplace.json` and `CHANGELOG.md`.
2. **`/dream` is discoverable and invocable** as a slash command in a Claude Code session opened in this repo.
3. **First-run `/dream` produces `~/.claude/projects/<main-slug>/memory.dream-YYYY-MM-DD/`** containing a full proposed memory tree, and **does not modify `memory/`** during the autonomous run (live-memory mtimes unchanged).
4. **A second cron (`/dream --autonomous`) invocation while an unfinalised dream exists is a no-op** that prints the existing dated dir's path and exits. Manual `/dream` with an unfinalised dream re-opens reconciliation (criterion 6).
5. **Cron-driven `/dream` via the existing `schedule` skill** produces the same dated artefact as manual invocation, exits without prompting, and is the same no-op as (4) when blocked.
6. **Interactive `/dream` while a dream exists re-opens reconciliation in conversation**, walking memory-by-memory with transcript evidence quoted as blockquotes in chat; user can keep / prune / promote / edit each entry. Live `memory/` is not mutated during discussion.
7. **Finalising the dream applies user-adopted state to live `memory/`**, archives or removes the dated dir, and updates each surviving memory's frontmatter `metadata.lastAudited` (and any other agreed audit-state fields).
8. **No transcript UUIDs or message-range citations appear in any memory file body** after finalisation (grep-falsifiable). Audit state lives in frontmatter `metadata:` only; evidence stays in chat.
9. **`memory.dream-*/` is listed in this repo's `.gitignore`** as defence-in-depth.
10. **Memories that name code artefacts** (files, functions, schema constants, flag names, etc.) **are grep-validated against live code at audit time**; misses surface in the audit conversation as flagged items.

**Out of scope (explicit):**

- Cross-project memory operations (each project audits its own slug only).
- Modifying upstream ed3d-plugins; `denubis-dream` is denubis-only.
- Calling Anthropic's `/v1/dreams` Managed Agents API; we port the pattern locally.
- Audit of memory directories other than `~/.claude/projects/<main-slug>/memory/` (worktree slugs have no memory dir to audit).

## Acceptance Criteria

### denubis-dream.AC1: Plugin discoverability and structure
- **denubis-dream.AC1.1 Success:** `plugins/denubis-dream/.claude-plugin/plugin.json` exists with `name: denubis-dream`, `version: 0.1.0`, `license: CC-BY-SA-4.0`.
- **denubis-dream.AC1.2 Success:** `.claude-plugin/marketplace.json` contains a `denubis-dream` entry pointing to `./plugins/denubis-dream` with matching version.
- **denubis-dream.AC1.3 Success:** `CHANGELOG.md` has a `[denubis-dream] 0.1.0` entry following the repo's changelog format.
- **denubis-dream.AC1.4 Success:** `/plugin list` (in a session opened in this repo) shows `denubis-dream`.
- **denubis-dream.AC1.5 Success:** `/dream` is invocable as a slash command in a Claude Code session opened in this repo.
- **denubis-dream.AC1.6 Failure:** Marketplace JSON validation fails if `denubis-dream` entry is malformed (missing version, wrong source path).

### denubis-dream.AC2: Mode detection and discovery
- **denubis-dream.AC2.1 Success:** `/dream` (no flag) detects manual mode and resolves the main project slug from `cwd` (strips `/.worktrees/<name>` if present).
- **denubis-dream.AC2.2 Success:** `/dream --autonomous` detects autonomous mode and proceeds without prompting at any point.
- **denubis-dream.AC2.3 Success:** Anchored slug scan matches exactly `^<main>$` or `^<main>--worktrees-.+$` under `~/.claude/projects/`. A sibling directory with a suffix-collision name (e.g., `<main>-2`) is *not* included.
- **denubis-dream.AC2.4 Success:** Anchored slug scan also finds slugs of pruned worktrees whose transcript dirs still exist (the worktree was removed but `~/.claude/projects/<main>--worktrees-<name>/` persists).
- **denubis-dream.AC2.5 Failure:** Invoked outside any project directory: `/dream` reports unable to resolve main slug and exits cleanly (no dated dir created).

### denubis-dream.AC3: Evidence retrieval (Sonnet subagents)
- **denubis-dream.AC3.1 Success:** One per-memory evidence subagent (`model: claude-sonnet-4-6`) dispatched per live memory file.
- **denubis-dream.AC3.2 Success:** Each `<name>.audit.md` contains a populated `## Evidence` section with `ev-NNN:` entries citing transcript short-UUIDs and line ranges.
- **denubis-dream.AC3.3 Success:** Each `<name>.audit.md` contains a populated `## Code-artefact flags` section showing both hits (with `path:line`) and misses (with "verify or edit") for code-artefact mentions in the memory body.
- **denubis-dream.AC3.4 Success:** Per-memory subagent windows transcripts from the memory's `frontmatter.metadata.lastAudited` onward (full corpus if absent).
- **denubis-dream.AC3.5 Success:** Flagged-region subagent writes `flagged/region-NNN.flagged.md` files for memory-worthy transcript regions matching no existing memory. Each file includes a `## Coverage` header line stating the transcript-time range scanned and the bounding `.last-dream` timestamp.
- **denubis-dream.AC3.6 Failure:** Per-memory subagent failure: memory name appears in `memory.dream-DATE/SKIPPED.md`; no `## Disposition` is added to that memory in the judgement phase.
- **denubis-dream.AC3.7 Success:** Re-invoking `/dream` while some live memories lack a `.audit.md` in today's dated dir re-dispatches per-memory subagents only for the missing ones; already-collected `.audit.md` files are not overwritten.
- **denubis-dream.AC3.8 Success:** Corpus-wide flagged-region subagent reads transcripts with timestamps ≥ the value in `~/.claude/projects/<main-slug>/.last-dream`. If `.last-dream` is absent (first dream), the subagent reads the full corpus and reports the unbounded scan in its `## Coverage` header.

### denubis-dream.AC4: Judgement and proposal (Opus)
- **denubis-dream.AC4.1 Success:** Each `<name>.audit.md` gets a `## Changes` section with diff-narrative hunks; each hunk cites the gate (*holds* / *correct* / *useful* / *duplicate* / *supported*) that motivated it.
- **denubis-dream.AC4.2 Success:** Each `<name>.audit.md` gets a `## Disposition` line: exactly one of `keep`, `edit`, or `prune`.
- **denubis-dream.AC4.3 Success:** Proposed-state mirror `<name>.md` written for each existing memory (a single line `<!-- PRUNE -->` for full removal).
- **denubis-dream.AC4.4 Success:** `memory.dream-DATE/MEMORY.md` regenerated to reflect proposed kept + edited entries; pruned ones omitted; flagged regions not yet listed (those join at promote-acceptance time).
- **denubis-dream.AC4.5 Success:** `--autonomous` mode exits cleanly after MEMORY.md regeneration; no reconciliation walk occurs.
- **denubis-dream.AC4.6 Success:** Re-invoking `/dream` while some `.audit.md` files lack a `## Disposition` section re-runs Opus judgement only on those (skipping already-judged ones), then regenerates `MEMORY.md` to reflect the now-complete set.

### denubis-dream.AC5: Reconciliation walk — existing memories
- **denubis-dream.AC5.1 Success:** Walk visits existing memories in `mtime` ascending order (stalest first).
- **denubis-dream.AC5.2 Success:** Memories with `keep` disposition and no code-artefact flags are batched ("N memories pass cleanly — confirm batch keep? [y/n]").
- **denubis-dream.AC5.3 Success:** Per-memory turn quotes `## Evidence` and `## Changes` from `.audit.md` as chat blockquotes; offers the recommended disposition.
- **denubis-dream.AC5.4 Success:** User verb `accept` applies the proposed mirror state (the dated-dir mirror is already correct; no live `memory/` write occurs).
- **denubis-dream.AC5.5 Success:** User verb `prune` writes `<!-- PRUNE -->` marker to the dated-dir mirror; disposition updates to `prune`.
- **denubis-dream.AC5.6 Success:** User verb `edit <instructions>` revises the dated-dir mirror per instructions; appends `## User edits` section to `.audit.md` noting the deviation from auto-recommendation.
- **denubis-dream.AC5.7 Success:** Abandoning the walk mid-stream and re-invoking `/dream` resumes from the first entry not yet present in `memory.dream-DATE/decisions.log`.
- **denubis-dream.AC5.8 Failure:** Live `memory/` file mtimes are unchanged after the walk (verified pre/post the walk; only finalisation may modify them).
- **denubis-dream.AC5.9 Success:** Every per-turn decision appends one JSON object on its own line to `memory.dream-DATE/decisions.log` (fields: `ts`, `action`, `stream`, `identifier`, `instruction`) before the next turn begins. Each line is independently parseable; instructions containing spaces, quotes, or newlines do not break parsing.
- **denubis-dream.AC5.10 Success:** Walk-end is reached when every existing memory + every flagged region has at least one entry in `decisions.log`; at walk-end Opus automatically presents the finalisation summary and `y/n` prompt.
- **denubis-dream.AC5.11 Success:** Re-decisions append fresh lines to `decisions.log`; finalisation reads the most recent line per identifier (last-write-wins per entry).

### denubis-dream.AC6: Reconciliation walk — flagged regions and promote
- **denubis-dream.AC6.1 Success:** After existing memories, walk visits `flagged/region-NNN.flagged.md` files in numeric order.
- **denubis-dream.AC6.2 Success:** Per-flagged-region turn quotes the transcript excerpt + why-memory-worthy note as blockquotes; Opus drafts a scaffold (`name`, `description`, `metadata.type`, body grounded in the excerpt).
- **denubis-dream.AC6.3 Success:** User verb `accept` writes the scaffold to `memory.dream-DATE/promoted/<name>.md`.
- **denubis-dream.AC6.4 Success:** User verb `edit <instructions>` revises the scaffold; user can re-accept the revision.
- **denubis-dream.AC6.5 Success:** User verb `dismiss` leaves the flagged file in place; no `promoted/` entry is written; the flagged file is discarded at finalisation.

### denubis-dream.AC7: Finalisation
- **denubis-dream.AC7.1 Success:** Finalise prompts for explicit user confirmation (`Apply to live memory/? [y/n]`) before any live `memory/` write. The prompt fires automatically at walk-end (AC5.10); it does not fire while un-decided entries remain.
- **denubis-dream.AC7.2 Success:** Mirror → live transfers use a `<name>.md.tmp` + `Bash mv` pattern; the `mv` rename is atomic at the POSIX syscall level (a concurrent read of `memory/<name>.md` sees either the pre-rename or post-rename content). A mid-finalisation interruption between the `.tmp` write and the `mv` may leave `.tmp` orphans in `memory/`; orphans are cleaned at the start of the next finalisation pass (AC7.10) before that pass reports success.
- **denubis-dream.AC7.3 Success:** PRUNE-marked mirrors result in deletion of the corresponding live `memory/<name>.md`.
- **denubis-dream.AC7.4 Success:** Promoted files are moved into live `memory/<name>.md` via the atomic pattern.
- **denubis-dream.AC7.5 Success:** Live `memory/MEMORY.md` is replaced from the dated-dir version via the atomic pattern.
- **denubis-dream.AC7.6 Success:** `frontmatter.metadata.lastAudited` bumped to today's date on every surviving live memory file (kept + edited + promoted).
- **denubis-dream.AC7.7 Failure:** Name collision in `promoted/` (matching an existing live memory name): finalise aborts and reports; no live writes occur; dated dir is preserved.
- **denubis-dream.AC7.8 Failure:** User rejects confirmation (`n`): finalise exits without applying; dated dir remains intact for later re-entry.
- **denubis-dream.AC7.9 Success:** After self-check passes, `~/.claude/projects/<main-slug>/.last-dream` is written (via `.tmp` + `mv`) containing the ISO date of this dream's finalisation, before the dated dir is removed. First dream creates the file; subsequent dreams overwrite it.
- **denubis-dream.AC7.10 Success:** Before reporting finalisation success, `Bash find memory/ -name '*.md.tmp' -delete` removes any `.tmp` orphans (defence against interrupted prior finalisations).

### denubis-dream.AC8: Self-check and dated-dir lifecycle
- **denubis-dream.AC8.1 Success:** Post-finalisation self-check `grep -RE '(transcript [a-f0-9]+|L[0-9]+–[0-9]+)' memory/` returns zero matches.
- **denubis-dream.AC8.2 Success:** Dated dir is removed (`rm -rf`) only after the self-check passes.
- **denubis-dream.AC8.3 Failure:** Self-check returns non-zero matches: finalise aborts, reports the offending `file:line` pairs, leaves the dated dir intact.
- **denubis-dream.AC8.4 Success:** Repo `.gitignore` lists `memory.dream-*` (defence-in-depth — the dated dir is normally outside any worktree).

### denubis-dream.AC9: Cron integration
- **denubis-dream.AC9.1 Success:** When the `schedule` skill invokes `/dream --autonomous`, the autonomous pass produces the same dated artefact (mirror + `.audit.md` + `MEMORY.md` + `flagged/`) as manual invocation.
- **denubis-dream.AC9.2 Success:** Cron-mode `/dream --autonomous` exits without prompting after `MEMORY.md` regeneration.
- **denubis-dream.AC9.3 Success:** Cron-mode `/dream --autonomous` with an existing dated dir for today: prints the path + exits (no-op; no overwrite).
- **denubis-dream.AC9.4 Success:** `plugins/denubis-dream/docs/cron-integration.md` documents how to register a cron job via the `schedule` skill (example invocation, recommended cadence, troubleshooting).

### denubis-dream.AC10: Cross-cutting behaviours
- **denubis-dream.AC10.1 Success:** `/dream` performs no operations against memory directories of other projects — only the resolved main slug's `memory/` is touched.
- **denubis-dream.AC10.2 Success:** Plugin version bumps follow the repo convention — `plugin.json` + `marketplace.json` + `CHANGELOG.md` synced in the same commit (per top-level `CLAUDE.md`).
- **denubis-dream.AC10.3 Success:** All 10 DoD criteria pass UAT via `plugins/denubis-dream/docs/uat-checklist.md` against either a fixture project or the live project before the plugin is declared releasable.

## Glossary

- **auto-memory**: Per-project markdown files under `~/.claude/projects/<slug>/memory/` that Claude Code reads at session start to load persistent context about a project. Each file has YAML frontmatter and a prose body.
- **MEMORY.md**: The index file inside a memory directory (both live and dated-dir) that lists all active memory entries for a project.
- **dated dir** (`memory.dream-YYYY-MM-DD/`): A scratch directory created alongside live `memory/` during the autonomous pass. Holds all audit artefacts (mirrors, `.audit.md` files, flagged regions, promoted scaffolds, `decisions.log`) and is destroyed at finalisation or preserved on abort.
- **mirror** (`<name>.md` in the dated dir): A proposed-state copy of a live memory file. During reconciliation the user's accepted dispositions are applied to the mirror; the mirror is what gets written to live `memory/` at finalisation.
- **`.audit.md`**: The per-memory verdict file produced by the autonomous pass. Contains `## Evidence`, `## Code-artefact flags`, `## Changes`, and `## Disposition` sections. Persists between the autonomous run and the reconciliation session so Opus can re-quote evidence as chat blockquotes.
- **ev-NNN**: A numbered citation line inside `## Evidence` that identifies a specific transcript excerpt (short-UUID + line range) relevant to a memory.
- **five gates**: The evaluative criteria Opus applies during judgement — *holds* (claim still applies to current project state), *correct* (factually accurate against current code), *useful* (shapes future behaviour, not noise), *duplicate* (another memory says the same), *supported* (transcript evidence exists for the claim).
- **disposition**: The outcome assigned to a memory or flagged region. Existing memories get `keep`, `edit`, or `prune`; flagged regions get `promote` or `dismiss`.
- **diff-narrative**: The format for `## Changes` content: human-readable change hunks using verbs (Removed, Edited, Reordered, Added) with the motivating gate cited in italics, rather than a unified diff or per-gate verdict table.
- **reconciliation walk**: The interactive phase of `/dream` where Opus presents each memory's evidence and proposed change to the user one at a time (or in batches for clean keeps), collects dispositions, and tracks them in `decisions.log`.
- **flagged region** (`flagged/region-NNN.flagged.md`): A transcript excerpt identified by the corpus-wide Sonnet subagent as memory-worthy but matching no existing memory. During the reconciliation walk the user can promote it into a new memory or dismiss it.
- **promote**: The user disposition for a flagged region that results in Opus drafting a memory scaffold, which the user can accept or edit, landing in `promoted/<name>.md` and ultimately in live `memory/` at finalisation.
- **`decisions.log`**: An append-only log inside the dated dir. Records one line per reconciliation turn (`<ISO-timestamp> <action> <stream> <identifier> [<instruction>]`). Used to detect walk progress, enable mid-walk resume, and determine the last-write-wins disposition at finalisation.
- **`lastAudited`** (`frontmatter.metadata.lastAudited`): A YAML frontmatter field on each memory file recording the date of the last completed audit. Used to window each per-memory subagent's transcript read (only transcripts since this date; full corpus if absent).
- **slug**: The `~/.claude/projects/` directory name Claude Code derives from a project's filesystem path by replacing `/` with `-`. Each worktree gets its own slug (`<main>--worktrees-<name>`).
- **slug-prefix scan**: The discovery step that finds the main project slug and all worktree-derived slugs (including pruned ones whose transcript dirs survive) by listing `~/.claude/projects/` and matching on the main slug as a prefix.
- **main slug**: The slug derived from the repo root (not a worktree path). All memory files live under the main slug; worktree slugs contribute transcripts but have no `memory/` of their own.
- **autonomous pass**: The pipeline phase (slug resolution → discovery → Sonnet retrieval → Opus judgement → MEMORY.md regeneration) that runs without user interaction. Triggered by both `/dream` (before the walk) and `/dream --autonomous` (which exits after this phase).
- **corpus-wide flagged-region subagent**: The single Sonnet subagent that reads the union of all discovered transcript files and surfaces memory-worthy regions not covered by any existing memory.
- **per-memory evidence subagent**: One of the parallel Sonnet subagents dispatched during the autonomous pass — one per live memory file — that windows and reads transcripts and writes `## Evidence` and `## Code-artefact flags` to that memory's `.audit.md`.
- **code-artefact flag**: An entry in the `## Code-artefact flags` section of an `.audit.md` recording whether a code artefact named in the memory body (file path, function name, schema constant, flag name) was found (`path:line`) or missed ("verify or edit") by `grep` against live code.
- **DoD self-check**: The post-finalisation `grep -RE '(transcript [a-f0-9]+|L[0-9]+–[0-9]+)' memory/` that verifies no transcript UUIDs or line-range citations leaked into live memory files. Finalisation aborts and leaves the dated dir intact if this returns matches.
- **promote-scaffold**: The draft memory body that Opus writes for a flagged region during the reconciliation walk — containing `name`, `description`, `metadata.type`, and a body grounded in the transcript excerpt — before the user accepts or edits it.
- **`schedule` skill**: An existing system-level Claude Code skill (not part of this plugin) used to register cron jobs. `denubis-dream` integrates with it by honouring the `--autonomous` flag the schedule skill passes through.
- **`denubis-bibliography`**: The existing skill-driven plugin in this repo that established the precedent for plugins with no Python helpers; `denubis-dream` follows the same directory layout.
- **SKIPPED.md**: A file written to the dated dir listing any memory names for which the per-memory Sonnet subagent failed; skipped memories are excluded from Opus judgement and surfaced at walk start.
- **atomic write**: The per-file finalisation pattern of writing to a `.tmp` file then calling `mv` to replace the live path, ensuring a concurrent reader sees either the pre-finalise or post-finalise content, never a partial write.

## Architecture

`denubis-dream` is a skill-driven Claude Code plugin under `plugins/denubis-dream/`. It registers a `/dream` slash command backed by the `denubis-dream:dreaming` skill, with no Python helpers — all deterministic operations (slug-scan, mtime sort, grep, atomic writes) are achievable via `Bash`, and all model-mediated operations (evidence retrieval, gate evaluation, reconciliation walk) are achievable via `Read`/`Write`/`Edit` plus subagent dispatch in skill text.

**Two invocation modes:**

- **Manual** (`/dream`, no flag): user in an Opus session. If no dated dir for today exists at `~/.claude/projects/<main-slug>/memory.dream-YYYY-MM-DD/`, the autonomous pass runs and the same conversation continues straight into reconciliation. If a dated dir exists, reconciliation opens immediately.
- **Cron autonomous** (`/dream --autonomous`, via the existing `schedule` skill): same autonomous pass; never enters reconciliation; no-op + path-print + exit if a dated dir exists.

**Pipeline (autonomous pass):**

1. **Discovery.** Resolve the main project slug from `cwd`. Scan `~/.claude/projects/` and include only slugs matching the exact regex `^<main>$` or `^<main>--worktrees-.+$` (catches pruned worktrees; rejects unrelated projects whose slugs happen to share a prefix).
2. **Sonnet retrieval** (parallel subagents via `Task` with `model: claude-sonnet-4-6`):
   - One **per-memory evidence subagent** per live `memory/*.md`. Reads transcripts in discovered slugs from the memory's `frontmatter.metadata.lastAudited` onward (full corpus if absent); writes the `## Evidence` and `## Code-artefact flags` sections of `memory.dream-YYYY-MM-DD/<name>.audit.md`.
   - One **corpus-wide flagged-region subagent**. Reads the union corpus *bounded by `.last-dream`* — only transcripts with timestamps ≥ the recorded last-finalisation timestamp; full corpus if `.last-dream` is absent (first dream). Surfaces memory-worthy transcript regions that match no existing memory; writes one `flagged/region-NNN.flagged.md` per find (excerpt + why-memory-worthy note + a `## Coverage` header line stating which transcript-time range was scanned, so under-coverage is visible to the user during reconciliation). All existing memories are in scope for the "matches no existing memory" check.
3. **Opus judgement** (current session, sequential): reads each `.audit.md`, applies the five gates (*holds*, *correct*, *useful*, *duplicate*, *supported*), appends `## Changes` (diff-narrative hunks with cited gate) and `## Disposition` (`keep` / `edit` / `prune`), and writes the proposed-state mirror `memory.dream-YYYY-MM-DD/<name>.md`. Regenerates a proposed `memory.dream-YYYY-MM-DD/MEMORY.md` index.
4. **Mode-dependent tail:** manual continues into the reconciliation walk; autonomous exits.

**Reconciliation walk** (manual mode, or `/dream` re-invocation when dated dir exists):

Opus walks existing memories by `mtime` ascending (stalest first). Memories with `keep` disposition and no code-artefact flags are batched ("12 memories pass cleanly — confirm batch keep? [y/n]"); other memories walked individually with blockquoted evidence + recommended change. User dispositions for existing memories: **keep / edit / prune** (writes update dated-dir mirror only — never live `memory/` during the walk). After existing memories, Opus walks `flagged/` regions; for each, Opus drafts a scaffold (`name`, `description`, `metadata.type`, body grounded in the excerpt); user dispositions for flagged regions: **promote (with optional edit instruction) / dismiss**. Promotes land in `memory.dream-YYYY-MM-DD/promoted/<name>.md`.

**Walk-state tracking via `memory.dream-YYYY-MM-DD/decisions.log`** — JSONL format, one decision per line. Each line is a JSON object with fields `ts` (ISO timestamp), `action` (`accept` / `reject` / `edit` / `prune` / `promote` / `dismiss`), `stream` (`memory` / `flagged`), `identifier` (the memory filename or region ID), `instruction` (null or the user's edit instruction string). Example: `{"ts":"2026-05-16T14:33:42Z","action":"edit","stream":"memory","identifier":"feedback_review.md","instruction":"remove paragraph about git log"}`. JSONL was chosen over a free-form line format because identifiers and instructions can contain spaces, quotes, and newlines without escaping ambiguity. Walk-end is reached when every entry (every existing memory + every flagged region) has at least one line in `decisions.log`. Last decision per identifier wins (re-decisions append; finalisation reads the most recent line per identifier). Resume from mid-walk: parse the log, compute the set of entries with at least one decision, walk continues from the first not-yet-decided entry.

**Finalisation trigger.** When walk-end is reached, Opus automatically presents the finalise summary + `y/n` prompt. If `n`, the dated dir persists; the user can re-invoke `/dream` to revisit any entry (which appends a fresh decision line). There is no "finalise now without walking everything" short-circuit — un-decided entries cannot be silently applied or silently skipped.

**Finalisation** requires explicit user confirmation. Per-file atomic writes (write to `.tmp`, then `mv`) apply mirrors to live `memory/`, replace `MEMORY.md`, move `promoted/` files into `memory/`, delete files marked `<!-- PRUNE -->`. Frontmatter `metadata.lastAudited` is bumped on every surviving live file. DoD #8 self-check: `grep -RE '(transcript [a-f0-9]+|L[0-9]+–[0-9]+)' memory/` must return zero matches before the dated dir is removed.

**Data flow boundaries:**

- **`memory/` (live).** Read during retrieval (to know what to audit), grep-checked during self-check, written only at finalisation. Never touched during autonomous pass (DoD #3).
- **`memory.dream-YYYY-MM-DD/` (dated dir).** Written during autonomous pass and during reconciliation; gitignored (DoD #9); destroyed at finalisation (DR9).
- **`~/.claude/projects/<main-slug>/.last-dream`** (small persistent artefact). One line: ISO timestamp of the most recent successful finalisation. Written at finalisation (DR14); read by the corpus-wide flagged-region subagent to bound its transcript window. Survives across dreams (the only inter-dream state outside `memory/` frontmatter).
- **Transcripts (`~/.claude/projects/<slug>/*.jsonl`).** Read-only.
- **Live worktree code.** Read-only (grep target for code-artefact flags).

## Decision Record

### DR1: Skill-driven plugin with no Python helpers
**Status:** Accepted
**Confidence:** Medium
**Reevaluation triggers:** Deterministic operations grow to where a Python module would be clearer; tests need to be automated rather than UAT-driven; subagent prompts become long enough that Python-rendered prompt templates are easier to maintain.

**Decision:** We chose to implement `/dream` as a pure skill (no Python module under `plugins/denubis-dream/`) over a hybrid skill + Python helper module.

**Consequences:**
- **Enables:** Simple plugin structure mirroring `denubis-bibliography`; no test-runner setup; fast prompt iteration; lower onboarding cost for contributors.
- **Prevents:** Unit testing of deterministic operations (slug scan, atomic write, grep extraction) without spinning up a Claude session.

**Alternatives considered:**
- **Hybrid skill + Python helper module:** Rejected because every deterministic operation needed is one `Bash` line or one tool call; abstracting them into Python would not earn its weight at this stage.

**Amendment 2026-05-18 (after Phase 2 coherence review H1):** DR1's "no Python helpers" rule is preserved. However, the rule does NOT extend to a single Bash helper file (`_lib.sh`) co-located with the skill at `plugins/denubis-dream/skills/dreaming/_lib.sh`. The Phase 2 coherence reviewer surfaced that pure-Bash skill blocks cannot share state across Bash tool calls (each tool call is a fresh subprocess), so a sourced helper is required for deterministic operations that more than one block consumes (e.g., `MAIN_SLUG`, `DATED_DIR`). The helper remains POSIX Bash — no test runner, no Python interpreter, no language-runtime dependency. This preserves DR1's actual intent ("simple plugin structure, no test-runner setup, lower onboarding cost") while removing the cross-block variable-persistence bug surface.

### DR2: Audit existing + flag deltas, no Sonnet candidate authoring
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** Flagged regions accumulate but rarely promote (suggesting they read as noise); user explicitly requests Opus to draft frontmatter for flagged regions during the autonomous pass.

**Decision:** We chose to have Sonnet audit existing memories AND flag memory-worthy transcript regions, but never author candidate frontmatter; promotion to a real memory always requires interactive user action.

**Consequences:**
- **Enables:** User retains authorship of every new memory; the autonomous pass is hands-off-safe (only writes the dated-dir scratch); cron runs cannot accidentally create new memories.
- **Prevents:** Pure-cron promotion of new memories; Sonnet "saving" the user time on writing new memories autonomously.

**Alternatives considered:**
- **Audit existing only:** Rejected because the user wants help noticing what they might have wanted to remember from transcript activity.
- **Audit existing + Sonnet authors candidates:** Rejected because authoring is a high-trust action that should stay with the user.

### DR3: Disjoint disposition vocab per stream
**Status:** Accepted (amended 2026-05-17 per implementation-plan critical-peer-review cycle 1)
**Confidence:** High
**Reevaluation triggers:** User finds the disjoint vocab confusing; cross-stream operations emerge (e.g., promoting an existing memory's type from `feedback` to `user`).

**Decision:** We chose disjoint disposition vocab — existing memories get `keep` / `prune` / `edit`; flagged regions get `promote` / `dismiss` — over unified vocab with overloaded meanings.

**Implementation-time amendment (2026-05-17, user-approved deviation):** existing-memory turns also offer a 4th verb `reject` as a meta-verb. `reject` is NOT a disposition — it's a user response that means "discard Phase 4's recommendation entirely; revert the mirror to byte-for-byte live state". Its action-outcome semantics: a no-op when the recommendation was `keep` (mirror was already at live); a revert-to-live when the recommendation was `edit` (drops Opus's revision); a don't-prune when the recommendation was `prune`. The disjoint-vocab invariant is preserved at the disposition layer (the underlying mirror state still resolves to one of `keep` / `prune` / `edit`); `reject` lives one layer above, in the reconciliation-walk user-response vocabulary. See `docs/implementation-plans/2026-05-16-denubis-dream/phase_05.md` header (deviation #2) for the rationale: without `reject`, a user wanting to discard an `edit` or `prune` recommendation would have to compose verbose `edit` instructions to undo Opus's proposed edit — `reject` provides a one-word path for that frequent case.

**Consequences:**
- **Enables:** Each disposition word means exactly one thing; reconciliation UX has unambiguous commands per stream. The `reject` meta-verb adds a one-word path for "discard the recommendation" without complicating the disposition layer.
- **Prevents:** Unifying logic across streams (one "decision" record per entry regardless of source).

**Alternatives considered:**
- **Unified vocab with overloaded meaning:** Rejected — same word meaning different things across streams creates confusion.
- **Three dispositions only (edit ad-hoc):** Rejected — `edit` is structural enough to deserve a named disposition.
- **`promote` also applies to existing memories:** Rejected — keeps `promote` specifically meaning "newly authored from a flagged region".
- **Omit `reject` entirely (implementation-time):** Rejected — forces users to type long `edit <restore original>` instructions to discard a recommendation; high-frequency user action deserves a one-word verb.
- **Rename `reject` to `revert` (implementation-time):** Rejected — `reject` reads as "I'm rejecting your recommendation"; `revert` is more programmer-y and less natural in the reconciliation-walk dialogue.

### DR4: Mirror + per-memory verdict file layout
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** Dated-dir disk usage becomes a problem at scale; `.audit.md` files become routinely ignored during walks (suggesting their content isn't carrying weight).

**Decision:** We chose the dated dir layout = parallel mirror (`<name>.md`) + per-memory verdict file (`<name>.audit.md`) + `flagged/` subdir + `promoted/` subdir, over mirror-only or single-manifest layouts.

**Consequences:**
- **Enables:** Audit reasoning persists between the autonomous run and the reconciliation session; Opus can re-quote evidence as chat blockquotes from disk.
- **Prevents:** A single-file manifest view of all proposed changes (must walk filesystem).

**Alternatives considered:**
- **Mirror + INDEX manifest only:** Rejected — loses per-memory reasoning between runs.
- **Mirror only, no manifest:** Rejected — Opus would re-derive reasoning each interactive session.

### DR5: Diff-narrative `.audit.md` shape
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** Diff-narrative becomes too verbose for memories with many small hunks; user wants per-gate verdict tables for cross-cutting analysis ("show me all `useful`-fails this dream").

**Decision:** We chose diff-narrative content for `.audit.md` (`## Evidence` → `## Code-artefact flags` → `## Changes` → `## Disposition`) where each `## Changes` hunk says WHAT to change and cites WHICH gate motivated it, over per-gate verdict blocks or holistic paragraphs.

**Consequences:**
- **Enables:** Audit output is actionable per-line; user sees changes-to-apply with their motivation; avoids meta-judgement noise.
- **Prevents:** Cross-memory analytics like "all `useful`-fails" (no structured gate-result field).

**Alternatives considered:**
- **Per-gate verdict block (5 rows always):** Rejected — verdict per gate without an attached action is meta-judgement noise; user pushback during brainstorming explicitly: "the audits should be what to change".
- **Failed-gate block only + disposition:** Rejected — still verdict-shaped, not change-shaped.
- **Holistic paragraph, gates as scaffolding:** Rejected — least falsifiable.

### DR6: Code-grep as separate flagged-item category
**Status:** Accepted
**Confidence:** Medium
**Reevaluation triggers:** Grep flags routinely lead to changes (suggesting they should auto-drive); the flag section becomes long enough to dominate reconciliation walks.

**Decision:** We chose to surface code-grep results in a separate `## Code-artefact flags` section (showing both hits and misses), not as evidence feeding `holds`/`correct` gates, over treating grep misses as gate-driving evidence.

**Consequences:**
- **Enables:** User retains judgement over what a grep miss means (intentional historical reference, renamed file, deprecated mention); both hits and misses visible for cheap verification.
- **Prevents:** Automated "this file no longer exists → prune memory" without human review.

**Alternatives considered:**
- **Grep miss = gate evidence:** Rejected — automated removal of mentions risks deleting deliberate references ("we used to use foo, now use bar").
- **Both (gate evidence + separate section):** Rejected — duplicates output, harder to reason about.

### DR7: Anchored slug-pattern scan for transcript discovery
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** User starts maintaining non-worktree checkouts of the same repo at different paths (they go undetected); the worktree slug pattern changes in Claude Code (e.g., new escaping for path separators).

**Decision:** We chose an *anchored regex* scan of `~/.claude/projects/` matching exactly `^<main>$` or `^<main>--worktrees-.+$` for transcript discovery, over an unanchored prefix scan, `git worktree list`, or a hybrid. The anchoring rejects suffix-collision slugs (e.g., `<main>-2` for an unrelated sibling project).

**Consequences:**
- **Enables:** Catches pruned-worktree transcripts (which remain after the worktree is removed); rejects unrelated suffix-collision projects; single regex in skill text; resilient to git state.
- **Prevents:** Catching non-worktree checkouts of the same repo at unrelated paths.

**Alternatives considered:**
- **Unanchored prefix scan:** Rejected after proleptic review — risks evidence poisoning from another project whose slug happens to start with the main slug.
- **`git worktree list`:** Rejected — only sees current worktrees; loses historical context from pruned ones.
- **Hybrid (git list ∪ anchored scan):** Rejected — the anchored scan is a superset of git list for practical purposes.

### DR8: Per-memory time windowing since `lastAudited`
**Status:** Accepted
**Confidence:** Medium
**Reevaluation triggers:** Cost of per-memory subagent dispatch becomes prohibitive for large memory counts; per-project simpler window becomes preferred for batching.

**Decision:** We chose per-memory windowing — each memory's evidence window starts at its own `frontmatter.metadata.lastAudited` (full corpus if absent) — over per-project or all-corpus windowing.

**Consequences:**
- **Enables:** Precision (newly-added memories get full coverage; freshly-audited ones get minimal re-read); each subagent has bounded context.
- **Prevents:** Single-pass-over-corpus efficiency (corpus may be read N times across N subagents).

**Alternatives considered:**
- **Per-project (since most-recent finalised dream):** Rejected — misses evidence for memories created after the last dream.
- **All transcripts every audit:** Rejected — wasteful.

### DR9: Finalisation removes the dated dir (not archived)
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** User wants to investigate "why did dream X edit memory Y?" months later; frontmatter starts wanting a `dreamId` field to point at archived reasoning.

**Decision:** We chose to remove `memory.dream-YYYY-MM-DD/` at finalisation, over archiving to `memory.dream-archive/` for historical replay. The only inter-dream artefact that survives finalisation is `~/.claude/projects/<main-slug>/.last-dream` (one ISO timestamp; see DR14) — needed to bound the corpus-wide flagged-region scanner.

**Consequences:**
- **Enables:** Minimal disk usage; frontmatter stays minimal (just `lastAudited`, no dream ID).
- **Prevents:** Post-hoc inspection of past audit reasoning.

**Alternatives considered:**
- **Archive to `memory.dream-archive/`:** Rejected — adds disk pressure and frontmatter complexity for a low-frequency need.
- **Opt-in archive (`--archive` flag at finalise):** Rejected — extra UX surface for a path the user said they don't need by default.

### DR10: Opus drafts promote-scaffold (vs strict no-AI-draft)
**Status:** Accepted
**Confidence:** Medium
**Reevaluation triggers:** User notices Opus drafts subtly biasing memory framing; user prefers to type bodies fresh; promote drafts get rejected so often that the draft cost isn't worth it.

**Decision:** We chose Opus-drafts-scaffold-user-accepts-or-edits for the promote workflow during reconciliation, over strict no-AI-drafting or `$EDITOR` handoff.

**Consequences:**
- **Enables:** Chat-friendly authoring; user retains final say; consistent with DR2 (autonomous Sonnet doesn't author; interactive Opus drafts only inside the user's accept/edit loop).
- **Prevents:** Pure user-typed authoring (Opus's draft does influence framing even when the user edits).

**Alternatives considered:**
- **Strict no-AI-drafting (user types body):** Rejected — heavy user-input cost per promote; loses speed advantage.
- **`$EDITOR` handoff:** Rejected — loses the chat thread; fragile across environments.

### DR11: Explicit `--autonomous` flag for mode detection
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** Schedule skill cannot reliably pass flags through; user finds a two-command split (`/dream` + `/dream-reconcile`) cleaner.

**Decision:** We chose explicit `--autonomous` flag (passed by the `schedule` skill in the cron invocation prompt) for distinguishing cron vs manual modes, over a separate slash command or environment-variable heuristic.

**Consequences:**
- **Enables:** Most explicit signal; no environmental ambiguity; user can manually invoke `/dream --autonomous` for headless behaviour without registering a cron job.
- **Prevents:** Hiding the cron behaviour from manual users (a feature, not a bug — manual users can opt into autonomous mode if they want).

**Alternatives considered:**
- **Two commands (`/dream` + `/dream-reconcile`):** Rejected — extra command surface; DoD criterion 6 implies reconciliation is the same `/dream` verb.
- **Env-var or TTY heuristic:** Rejected — fragile, misfires possible.

### DR12: Continue straight into reconciliation after autonomous (vs two-step)
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** Autonomous pass becomes long enough that the user routinely steps away before the walk would begin; reconciliation walks routinely interrupted by user wanting to inspect the dated dir first.

**Decision:** We chose to continue straight into the reconciliation walk after the manual autonomous pass completes (same Opus session), over a two-step "autonomous exits, user re-invokes to reconcile" flow.

**Consequences:**
- **Enables:** One-shot UX for manual users; mid-walk abandonment is naturally resumable by re-invocation.
- **Prevents:** Explicit inspection of the dated dir before the walk begins (user can still abort the walk, inspect, and re-invoke).

**Alternatives considered:**
- **Two-step (autonomous exits, user re-invokes):** Rejected — extra friction without clear benefit given resumability.
- **Prompt ("reconcile now or later?"):** Rejected — redundant since user can always abandon the walk and re-invoke later.

### DR13: Walk order — `mtime` ascending (stalest first)
**Status:** Accepted
**Confidence:** Medium
**Reevaluation triggers:** User finds recently-edited memories are more often the buggy ones (descending preferred); disposition-primary ordering becomes preferred to surface high-action items first.

**Decision:** We chose walk order = `mtime` ascending (oldest memories first), over `mtime` descending or disposition-primary.

**Consequences:**
- **Enables:** Stalest memories (largest evidence windows, most likely findings) walked first; mid-walk fatigue still leaves the highest-value entries covered.
- **Prevents:** Prioritising recently-touched memories where the user's mental context is freshest.

**Alternatives considered:**
- **`mtime` descending (newest first):** Rejected — recently-touched memories are likely already accurate.
- **Disposition-primary (prune → edit → keep), `mtime` ascending within:** Rejected — interleaves dispositions; loses temporal cadence the user can develop intuition for.

### DR14: Project-level `.last-dream` artefact for corpus-wide windowing
**Status:** Accepted
**Confidence:** Medium
**Reevaluation triggers:** Per-memory `lastAudited` aggregation proves sufficient and `.last-dream` becomes redundant; users want multiple historical dream timestamps not just the latest.

**Decision:** We chose a small persistent artefact `~/.claude/projects/<main-slug>/.last-dream` (one line: ISO timestamp of the most recent successful finalisation) to bound the corpus-wide flagged-region subagent's transcript window, over computing the bound from per-memory `lastAudited` aggregation or scanning the full corpus every dream.

**Consequences:**
- **Enables:** Corpus-wide subagent has a bounded scan window without ambiguity; coverage reporting (`## Coverage` header in flagged files) can cite the bound explicitly; first dream (no `.last-dream`) falls back to full corpus.
- **Prevents:** Fully stateless dream invocation — every dream reads `.last-dream` at the start of the autonomous pass; first dream is bounded only by the corpus's natural extent.

**Alternatives considered:**
- **Aggregate per-memory `lastAudited` (max across files):** Rejected — confuses "audited" with "dream-finalised". A brand-new memory has no `lastAudited` and would skew the aggregate. A memory audited but not promoted-from-dream still records its `lastAudited`, also skewing.
- **All-corpus every dream:** Rejected after proleptic review — corpus is unbounded; subagent context may silently truncate; user has no visibility into coverage.
- **Inline timestamp in `MEMORY.md`:** Rejected — pollutes the index; tightly couples corpus-windowing state to a file that has a different primary purpose.

## Existing Patterns

Investigation found `denubis-bibliography` (`plugins/denubis-bibliography/`) as the established precedent for skill-driven plugins with no Python module — same layout, all operations via `Bash`/`Read`/`Write`/`Edit`. This design follows that pattern:

- `plugins/denubis-dream/.claude-plugin/plugin.json` — plugin manifest.
- `plugins/denubis-dream/commands/dream.md` — slash-command stub that invokes the skill.
- `plugins/denubis-dream/skills/dreaming/SKILL.md` — full pipeline instructions Opus follows.

Plugin-version sync follows the repo-wide convention documented in the top-level `CLAUDE.md`: every version bump to `plugin.json` requires a sync to `.claude-plugin/marketplace.json` and a `CHANGELOG.md` entry. The "version bumps after the thing works, not during iteration" feedback in user memory applies — bump once on UAT pass, not on every WIP commit.

Skill text follows `denubis-plan-and-execute` conventions: clear section headers, explicit subagent dispatch examples in XML form (per repo `CLAUDE.md`), "Common Rationalizations — STOP" tables, and inline checklists where workflows are mandatory. Subagent prompts mirror the patterns in `denubis-research-agents` skills.

Cron integration uses the existing `schedule` skill (system-level, configured per-project by the user) — `/dream` does not own the scheduling decision; it only honours the `--autonomous` flag the schedule skill passes through.

**Divergence:** `memory.dream-*/` lives under `~/.claude/projects/<main-slug>/` (outside any git-tracked directory). The DoD-mandated `.gitignore` entry is defence-in-depth only — the dated dir is normally outside any worktree.

## Implementation Phases

7 phases. Each phase delivers a usable increment; later phases build on earlier ones. Functionality phases verify against acceptance criteria with behavioural tests (the skill exercised against a fixture memory tree + transcript dir).

<!-- START_PHASE_1 -->
### Phase 1: Plugin scaffolding
**Goal:** Plugin loads; `/dream` is registered as a slash command and prints a "scaffold ready, behaviour not yet implemented" stub.

**Components:**
- `plugins/denubis-dream/.claude-plugin/plugin.json` — name `denubis-dream`, version `0.1.0`, description, author, license `CC-BY-SA-4.0`.
- `plugins/denubis-dream/commands/dream.md` — slash-command stub that invokes `denubis-dream:dreaming` skill.
- `plugins/denubis-dream/skills/dreaming/SKILL.md` — skeleton frontmatter + announce-on-start; pipeline stubbed.
- `.claude-plugin/marketplace.json` — add `denubis-dream` entry (repo-wide marketplace version stays at `2.0.0`).
- `CHANGELOG.md` — add `[denubis-dream] 0.1.0` entry under the existing changelog format.
- `.gitignore` — add `memory.dream-*` (DoD #9).

**Dependencies:** None.

**Done when:** `/plugin list` shows `denubis-dream`; `/dream` is invocable in this repo and reaches the stub message; marketplace JSON validates against its schema; no lint errors. Infrastructure phase — verified operationally, no AC tests.
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Autonomous-pass orchestration
**Goal:** `/dream` (with or without `--autonomous`) detects its mode, resolves the main project slug, runs the slug-prefix discovery scan, creates today's dated dir if needed, and exits with a "discovery complete, retrieval/judgement not yet implemented" stub.

**Components:**
- `skills/dreaming/SKILL.md` sections:
  - `## Mode detection` — parse `--autonomous` flag from invocation.
  - `## Project slug resolution` — derive main slug from `cwd` (strip `/.worktrees/...` if present; convert `/` → `-`).
  - `## Discovery` — `Bash` scan of `~/.claude/projects/` matching the exact regex `^<main>$` or `^<main>--worktrees-.+$` (anchored; rejects unrelated suffix-collision slugs like `<main>-2`).
  - `## Dated dir creation` — `Bash mkdir -p ~/.claude/projects/<main>/memory.dream-$(date +%Y-%m-%d)/{flagged,promoted}`.
  - `## No-op detection` — if dir exists in `--autonomous` mode: print path + exit; in manual mode: jump to reconciliation entry.

**Dependencies:** Phase 1.

**Done when:** Manual `/dream` against this repo creates the expected dated dir; `/dream --autonomous` against the same exits cleanly when dir already exists. Covers `denubis-dream.AC1.*` (mode detection) and `denubis-dream.AC2.*` (discovery).
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: Sonnet retrieval subagents
**Goal:** Sonnet subagents are dispatched; per-memory `.audit.md` files are written with `## Evidence` and `## Code-artefact flags` sections; `flagged/region-NNN.flagged.md` files exist for surfaced regions.

**Components:**
- `skills/dreaming/SKILL.md` sections:
  - `## Per-memory evidence retrieval` — `Task` dispatch with `model: claude-sonnet-4-6`, one subagent per live memory, parallel.
  - `## Per-memory subagent prompt` — full prompt text: read the memory body, window transcripts since `lastAudited` (full corpus if absent), extract relevant excerpts as `ev-NNN:` lines, run `Bash grep` for any code-artefact mentions in the memory body, write the `## Evidence` and `## Code-artefact flags` sections to `<name>.audit.md`.
  - `## Flagged-region scanner` — `Task` dispatch with `model: claude-sonnet-4-6`, one subagent for the whole corpus, windowed to transcripts ≥ the timestamp in `~/.claude/projects/<main-slug>/.last-dream` (full corpus if `.last-dream` absent — first dream).
  - `## Flagged-region subagent prompt` — full prompt text: read the windowed corpus, identify regions matching no existing memory but looking memory-worthy, write `flagged/region-NNN.flagged.md` files (excerpt + why-memory-worthy note + `## Coverage` header stating the transcript-time range scanned + the bounding `.last-dream` timestamp, so user can see whether scan was complete).

**Dependencies:** Phase 2.

**Done when:** After Phase 2's discovery, `.audit.md` files exist for every live memory with both required sections populated; `flagged/region-*.flagged.md` files exist when the corpus contains memory-worthy regions. Covers `denubis-dream.AC3.*` (evidence collection).
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: Opus judgement
**Goal:** Opus reads each `.audit.md`, applies the five gates, appends `## Changes` (diff-narrative) and `## Disposition`, writes the proposed-state mirror, and regenerates `MEMORY.md`.

**Components:**
- `skills/dreaming/SKILL.md` sections:
  - `## Gate semantics` — what each of *holds*, *correct*, *useful*, *duplicate*, *supported* tests.
  - `## Diff-narrative writing` — how to append the `## Changes` section: verbs (`Removed`, `Edited`, `Reordered`, `Added`), one hunk per change, cited gate in italics, evidence reference (`ev-NNN`).
  - `## Disposition computation` — no changes → `keep`; structural edit → `edit`; whole-memory removal → `prune`.
  - `## Mirror writing` — `Write` to `memory.dream-DATE/<name>.md` with proposed body; for `prune`, the body is a single line `<!-- PRUNE -->`.
  - `## MEMORY.md regeneration` — Opus authors `memory.dream-DATE/MEMORY.md` reflecting the proposed kept + edited entries, with pruned ones omitted.
  - `## Autonomous exit` — when `--autonomous` flag is present, exit after MEMORY.md regeneration.

**Dependencies:** Phase 3.

**Done when:** After Phase 3 retrieval, mirror files and appended `.audit.md` files exist for every memory; `memory.dream-DATE/MEMORY.md` exists as proposed index; autonomous mode exits cleanly after. Covers `denubis-dream.AC4.*` (judgement & proposal).
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: Reconciliation walk
**Goal:** Manual `/dream` (or re-invocation when dated dir exists) opens the walk; existing memories walked `mtime`-ascending with per-stream dispositions; flagged regions walked with promote-scaffold workflow; mid-walk decisions persist; abandoned walks resume cleanly.

**Components:**
- `skills/dreaming/SKILL.md` sections:
  - `## Walk entry` — when manual mode + dated dir exists, jump straight to walk; when manual mode + dir just created (Phase 4 just finished), continue into walk.
  - `## Walk order` — `Bash ls -tr` for `mtime` ascending; batch `keep`-clean memories ("12 pass cleanly — confirm batch keep? [y/n]"); walk others individually.
  - `## Per-existing-memory turn` — blockquote `## Evidence` + `## Changes` from `.audit.md`; offer recommended disposition; user verbs are `accept` / `reject` / `edit <instructions>` / `prune`; update dated-dir mirror per choice.
  - `## Per-flagged-region turn` — blockquote excerpt + why-memory-worthy note; Opus drafts scaffold (`name`, `description`, `metadata.type`, body); user verbs are `accept` / `edit <instructions>` / `dismiss`; promotes land in `promoted/<name>.md`.
  - `## Decisions log` — append-only `memory.dream-DATE/decisions.log` in JSONL format. Each line is a JSON object: `{"ts": "<ISO>", "action": "<verb>", "stream": "memory"|"flagged", "identifier": "<id>", "instruction": null | "<text>"}`. Actions: `accept`/`reject`/`edit`/`prune` for memory stream; `accept`/`edit`/`dismiss` for flagged stream (the `accept` of a flagged region produces a `promote`-class outcome at finalisation). Re-decisions append fresh lines; finalisation uses the last line per identifier. JSONL chosen over a space-separated format to eliminate escaping ambiguity for instructions containing spaces, quotes, or newlines.
  - `## Mid-walk persistence` — each decision: (1) append a line to `decisions.log`, (2) update the dated-dir mirror or `promoted/` file, (3) append `## User edits` to `.audit.md` if the decision deviates from the auto-recommendation. All three writes complete before the next turn begins.
  - `## Resume detection` — on re-entry, read `decisions.log`, compute the set of decided identifiers (existing memory filenames + flagged region IDs), walk continues from the first not-yet-decided entry in `mtime`-ascending order (memories) or numeric order (regions).
  - `## Walk-end detection` — walk reaches end when every existing memory + every flagged region appears at least once in `decisions.log`. At walk-end, Opus automatically presents the finalise summary + `y/n` prompt.

**Dependencies:** Phase 4.

**Done when:** Manual `/dream` walks the dated dir produced in Phase 4; each disposition correctly updates the dated dir; promotes land in `promoted/<name>.md`; abandoning and re-invoking resumes from the next un-decided entry. Covers `denubis-dream.AC5.*` (walk) and `denubis-dream.AC6.*` (promote).
<!-- END_PHASE_5 -->

<!-- START_PHASE_6 -->
### Phase 6: Finalisation
**Goal:** Finalise applies user-adopted dated-dir state to live `memory/` atomically per-file; bumps `frontmatter.metadata.lastAudited`; rewrites live `MEMORY.md`; passes DoD #8 grep self-check; removes the dated dir.

**Components:**
- `skills/dreaming/SKILL.md` sections:
  - `## Finalise confirmation prompt` — summary ("X kept, Y edited, Z pruned, W promoted, V flagged dismissed"); explicit `y/n`.
  - `## Per-file atomic write pattern` — `Write` to `<live>/<name>.md.tmp`, `Bash mv` over live path; bump `lastAudited` to today's date during the write.
  - `## PRUNE marker handling` — delete `memory/<name>.md` for files with body `<!-- PRUNE -->`.
  - `## Promoted file move` — copy from `promoted/<name>.md` to `memory/<name>.md` via the same atomic pattern; abort + report if name collides.
  - `## MEMORY.md replacement` — atomic replace from dated-dir version.
  - `## DoD #8 self-check` — `Bash grep -RE '(transcript [a-f0-9]+|L[0-9]+–[0-9]+)' memory/`; must return zero matches. If non-zero, abort + report + leave dated dir intact.
  - `## .tmp orphan cleanup` — `Bash find memory/ -name '*.md.tmp' -delete` before declaring finalisation successful. Belt-and-braces against the case where a previous mid-finalisation interruption left orphaned temp files.
  - `## .last-dream timestamp write` — write today's ISO date to `~/.claude/projects/<main-slug>/.last-dream` via the atomic `.tmp + mv` pattern. This is the inter-dream persistence point for the corpus-wide flagged-region subagent's windowing.
  - `## Dated-dir removal` — `Bash rm -rf memory.dream-YYYY-MM-DD/` after self-check passes, `.tmp` orphans are cleaned, and `.last-dream` is written.

**Dependencies:** Phase 5.

**Done when:** After Phase 5 walk completes, finalise applies all user-adopted changes to live `memory/`; self-check returns zero matches; dated dir is removed; `lastAudited` values reflect the dream date on surviving files. Covers `denubis-dream.AC7.*` (finalise) and `denubis-dream.AC8.*` (self-check).
<!-- END_PHASE_6 -->

<!-- START_PHASE_7 -->
### Phase 7: Cron integration documentation + UAT
**Goal:** Plugin documents how to register a cron job via the `schedule` skill; manual UAT checklist exists for full-pipeline verification on a fixture project; end-to-end verification passes.

**Components:**
- `plugins/denubis-dream/docs/cron-integration.md` — how to use the `schedule` skill to call `/dream --autonomous`; example invocation; recommended cadence (e.g., weekly); troubleshooting.
- `plugins/denubis-dream/docs/uat-checklist.md` — step-by-step manual verification covering all 10 DoD criteria against either a fixture memory tree + transcript dir or the live project. Because DR1 accepts no automated unit tests for deterministic operations, this checklist explicitly covers integrity-critical edge cases that would otherwise have unit-test coverage: (1) slug-prefix scan against a fixture containing both a real worktree slug and a deliberate suffix-collision slug (`<main>-test`), confirming only the real one is included; (2) `decisions.log` parsing under edge cases — identifiers with underscores, instructions containing quotes/newlines/multi-line text; (3) atomic write verification by interrupting mid-finalisation (`Ctrl-C` after self-check, before `.last-dream` write) and confirming `memory/` is in a consistent state with `.tmp` orphans cleaned on next run; (4) mid-walk abandonment by exiting the session mid-walk and re-entering, confirming resume from the first not-yet-decided entry; (5) corpus-wide subagent coverage check by comparing the `## Coverage` header against the `.last-dream` timestamp.
- `skills/dreaming/SKILL.md` `## Cron integration` section pointing to `docs/cron-integration.md`.
- Plugin version bump to `0.2.0` (or whichever post-UAT version) — sync `plugin.json` + `marketplace.json` + `CHANGELOG.md` in the same commit per repo convention.

**Dependencies:** Phase 6.

**Done when:** `cron-integration.md` and `uat-checklist.md` exist and are reviewed; user completes UAT checklist successfully end-to-end against the live project; plugin version bumped consistently across the three files. Covers `denubis-dream.AC9.*` (cron integration) and all cross-cutting acceptance criteria.
<!-- END_PHASE_7 -->

## Additional Considerations

**Error handling.**
- *Per-memory Sonnet subagent failure:* Opus's judgement pass detects a missing `## Evidence` section in `.audit.md`, skips that memory's judgement, appends the memory name to `memory.dream-DATE/SKIPPED.md`. Reconciliation surfaces the skipped list at walk start.
- *Mid-judgement Opus crash:* dated-dir files are partial. Re-invoking `/dream` picks up where it left off — Opus iterates the dated dir, judges any `.audit.md` lacking a `## Disposition` section, skips already-judged ones.
- *Reconciliation mid-walk abandonment:* every per-turn decision persists to the dated dir; re-invocation resumes from the first un-decided entry (detected by comparing mirror content to its un-edited proposed state).
- *Finalisation partial failure:* per-file atomic writes (rename-only atomicity per AC7.2) mean partial application is consistent at the file level; un-bumped `lastAudited` values cause those memories to be re-audited on the next dream. If the interrupt landed between a `.tmp` write and its `mv`, the next finalisation pass cleans the `.tmp` orphans (AC7.10) before reporting success. Finalisation is otherwise idempotent (mirror = live on re-run is a no-op effectively), so re-entering an unfinalised dream after a partial interruption converges on the correct state.

**Corpus-wide scanner bound (first dream).** First-ever dream has no `.last-dream` to bound the corpus-wide flagged-region subagent — it reads the full corpus. This may be slow and may silently truncate if the corpus exceeds the subagent's context window; the `## Coverage` header on each flagged file reports the actual scanned range so the user can see whether coverage was complete. Subsequent dreams are bounded by the previous successful finalisation date.

**Model pinning.**
- Sonnet subagent dispatches pin `model: claude-sonnet-4-6` (current Sonnet at the date of writing).
- Opus runs in the current session (caller is expected to be Opus, per user's standing rule that judgement-grade work belongs on Opus); no model override is needed for judgement work.
- Model IDs live inline in the skill text; updates require a plugin version bump per the repo's standard convention.

**Versioning.**
- Initial release: `denubis-dream` `0.1.0`. Subsequent bumps sync `plugin.json` + `marketplace.json` + `CHANGELOG.md` in the same commit (per top-level `CLAUDE.md`).
- "Version bumps after the thing works, not during iteration" (per user feedback memory) — bump once on UAT pass at Phase 7, not on every WIP commit during Phases 1–6.

**Out-of-scope (from DoD).**
- Cross-project memory operations — each project audits its own slug only.
- Modifications to upstream `ed3d-plugins`; `denubis-dream` is denubis-only.
- Calling Anthropic's `/v1/dreams` Managed Agents API — pattern is ported locally.
- Audit of memory directories other than `~/.claude/projects/<main-slug>/memory/` (worktree slugs have no `memory/` to audit).
