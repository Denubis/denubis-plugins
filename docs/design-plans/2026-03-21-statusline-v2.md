# Statusline v2 Design

**GitHub Issue:** None

## Summary

The statusline v2 project upgrades the tmux status bar display used alongside Claude Code sessions. The existing single-file script (`workflow-statusline.py`) is refactored into a uv-managed Python package and extended with four new capabilities: a 20-character "Boss HP" context bar that uses colour to communicate which 200k-token segment of the context window is currently active, rate limit gauges with linear-regression burn rate projections that warn when the user is on track to exhaust their quota before it resets, a redesigned first line showing git location and a prominent warning when working directly on the main branch outside a worktree, and a side-effect tmux window rename so each tab reflects the active session location.

Alongside the statusline changes, a new `session-naming` skill uses a cheap Haiku subagent to generate a short, domain-specific slug from the user's opening prompt and the current git context, then renames the tmux window to that slug. A lock file mechanism lets the skill's name take precedence over the statusline's location-based rename for the rest of the session. Four existing skills (design planning, implementation planning, implementation execution, and systematic debugging) are each updated to invoke `session-naming` at the point where the task context is clearest. The work is structured as eight sequential phases, starting with package scaffolding and ending with a plugin version bump and changelog entry.

## Definition of Done

1. **Statusline v2**: `workflow-statusline.py` upgraded with: compact model display, location with red MAIN warning when on main/master and not in a worktree, git changes, agent name when present, boss HP context bar (20 chars, colour per 200k token segment with dimmed prior layer as remainder), rate limit gauges (5h + 7d) with burn-rate time-to-exhaustion estimates, cost, duration. Side-effect: `tmux rename-window` to `Cl:<location>` on each render (only when name changes).

2. **Session-naming skill**: New skill `session-naming` in the denubis-plan-and-execute plugin that spawns a Haiku subagent to read the user's initial prompt, generate a 2-4 word slug, run `tmux rename-window "Cl:<slug>"`, and prompt the user to copy-paste `/rename <slug>`.

3. **Skill integration**: Four target skills (starting-a-design-plan, starting-an-implementation-plan, executing-an-implementation-plan, systematic-debugging) invoke session-naming early in their workflow.

4. **Skill hardening**: `starting-an-implementation-plan` and `executing-an-implementation-plan` invoke `critical-peer-review` at workflow completion. `systematic-debugging` adds a mandatory context clear and reset between hypothesis generation and hypothesis testing phases.

5. **byobu keybindings**: Shift+Alt+Left/Right for tmux window reorder (already applied to `~/.byobu/keybindings.tmux`).

## Acceptance Criteria

### statusline-v2.AC1: Line 1 displays location and git context
- **statusline-v2.AC1.1 Success:** Line 1 shows location (repo@branch or worktree name) as leftmost element
- **statusline-v2.AC1.2 Success:** Git staged and modified counts shown after location
- **statusline-v2.AC1.3 Success:** Code churn (lines added/removed) shown when present
- **statusline-v2.AC1.4 Edge:** Red `✗MAIN` shown when on main/master and not in a worktree
- **statusline-v2.AC1.5 Edge:** Agent name (`agt:<name>`) shown only when `agent.name` present in session JSON

### statusline-v2.AC2: Boss HP context bar renders correctly
- **statusline-v2.AC2.1 Success:** Bar is 20 characters wide for all context window sizes
- **statusline-v2.AC2.2 Success:** Bar colour corresponds to current 200k-token segment (green→cyan→yellow→magenta→red) for 1M context
- **statusline-v2.AC2.3 Success:** Unfilled remainder renders in dimmed prior segment colour
- **statusline-v2.AC2.4 Success:** 200k context windows degrade green→yellow→red by percentage (existing behaviour preserved)

### statusline-v2.AC3: Rate limits display with burn rate projection
- **statusline-v2.AC3.1 Success:** Rate limit percentages shown for 5h and 7d windows when present
- **statusline-v2.AC3.2 Success:** Time estimate shown (time to reset or time to exhaustion)
- **statusline-v2.AC3.3 Success:** Red percentage and `!` suffix when projected to exhaust before reset
- **statusline-v2.AC3.4 Failure:** Rate limit section omitted when `rate_limits` absent from session JSON
- **statusline-v2.AC3.5 Edge:** Single data point (first render) shows percentage only, no time projection

### statusline-v2.AC4: tmux window rename from statusline
- **statusline-v2.AC4.1 Success:** tmux window renamed to `Cl:<location>` on each render when name changes
- **statusline-v2.AC4.2 Success:** Rename skipped when name unchanged (no subprocess overhead)
- **statusline-v2.AC4.3 Success:** Rename suppressed when lock file exists (session-naming skill active)
- **statusline-v2.AC4.4 Failure:** Rename skipped silently outside tmux (no `TMUX` env var)

### statusline-v2.AC5: Session-naming skill produces domain-specific names
- **statusline-v2.AC5.1 Success:** Haiku subagent generates 2–4 word lowercase hyphenated slug from user prompt, skill name, and git context
- **statusline-v2.AC5.2 Success:** tmux window renamed to `Cl:<slug>`
- **statusline-v2.AC5.3 Success:** Lock file written at `/tmp/claude-statusline-tmux-lock-{session_id}`
- **statusline-v2.AC5.4 Success:** User prompted with `/rename <slug>` command to copy-paste
- **statusline-v2.AC5.5 Failure:** Skill degrades gracefully if tmux unavailable

### statusline-v2.AC6: Target skills invoke session-naming
- **statusline-v2.AC6.1 Success:** Each of 4 target skills invokes session-naming at its "context is clear" moment
- **statusline-v2.AC6.2 Success:** Existing skill behaviour unchanged apart from naming invocation
- **statusline-v2.AC6.3 Edge:** Re-invocation of session-naming overwrites lock file with new name

### statusline-v2.AC7: Implementation skills invoke critical peer review
- **statusline-v2.AC7.1 Success:** `starting-an-implementation-plan` invokes `critical-peer-review` at workflow completion
- **statusline-v2.AC7.2 Success:** `executing-an-implementation-plan` invokes `critical-peer-review` at workflow completion

### statusline-v2.AC8: Systematic debugging enforces context clear
- **statusline-v2.AC8.1 Success:** `systematic-debugging` instructs user to clear context between hypothesis generation and hypothesis testing
- **statusline-v2.AC8.2 Success:** Clear instruction follows copy-then-clear pattern (user copies command before `/clear`)

## Glossary

- **Boss HP bar**: A 20-character wide progress bar that visualises context window consumption, styled after a "boss health bar" in video games. Colour encodes which 200k-token segment is active; the unfilled remainder renders in the previous segment's colour, dimmed.
- **burn rate**: The rate at which a rate limit quota is being consumed, expressed as percentage points per unit time. Derived via linear regression over a rolling cache of usage samples.
- **byobu**: A terminal multiplexer wrapper around tmux that adds status lines, keybinding management, and configuration files such as `~/.byobu/keybindings.tmux`.
- **context window**: The maximum amount of text (measured in tokens) that a language model can hold in memory during a single conversation. Claude's models offer 200k or 1M token windows depending on the subscription tier.
- **denubis-plan-and-execute**: The plugin in this repository that hosts the statusline script, skills, and hooks for plan-and-execute workflows. The statusline package and session-naming skill both live inside it.
- **Haiku subagent**: An instance of Claude Haiku (a cheaper, faster model) spawned as a sub-task to perform a focused operation — in this case, generating a session name slug — without incurring the cost of a full Sonnet invocation.
- **lock file**: A file written to `/tmp` whose presence signals that the session-naming skill has set the tmux window name. The statusline checks for this file and defers its own rename while it exists, preventing the location-based name from overwriting the skill-assigned name.
- **rate limit**: A quota imposed on Claude.ai subscribers limiting how many tokens can be consumed within a 5-hour or 7-day rolling window. Displayed in the statusline as a percentage of the quota used.
- **session JSON**: The data Claude Code pipes to the statusline script on every conversation update. Contains fields for context usage, rate limits, cost, agent name, and other session state.
- **slug**: A short, lowercase, hyphen-separated string used as a human-readable identifier — here, a 2–4 word summary of the session's purpose, e.g. `fix-auth-timeout`.
- **tmux**: A terminal multiplexer that manages multiple terminal sessions within a single window, organised as named or numbered panes and windows. The statusline renames the current tmux window as a side-effect of each render.
- **TTL (time-to-live)**: A cache expiry duration. The git status cache uses a 5-second TTL; after that, the next render re-runs the git commands.
- **uv**: A fast Python package and project manager. The new statusline package uses `uv` (via `pyproject.toml`) to manage its dependencies and entry point, replacing the previous standalone script.
- **worktree**: A git feature that allows multiple working directories to be checked out from the same repository simultaneously. The statusline treats an active worktree as safe; the red `✗MAIN` warning is suppressed when git reports the user is in a worktree rather than the primary checkout.

## Architecture

Three components: a statusline package (Python, uv-managed), a session-naming skill (SKILL.md), and skill integration points (additions to four existing skills).

### Statusline Package

The current single-file `workflow-statusline.py` is replaced by a uv-managed Python package at `plugins/denubis-plan-and-execute/scripts/workflow_statusline/`.

```
scripts/workflow_statusline/
├─ pyproject.toml
├─ src/workflow_statusline/
│  ├─ __init__.py
│  ├─ __main__.py    # Entry: parse JSON, compose lines, print, tmux rename
│  ├─ cache.py       # Generic TTL file cache (used by git + burn rate)
│  ├─ bar.py         # Boss HP bar: 20-char, colour per 200k segment
│  ├─ tmux.py        # tmux rename-window (defers to naming skill lock)
│  ├─ git.py         # git_location() and git_changes()
│  └─ colours.py     # ANSI 16-colour constants
```

Data flow: Claude Code pipes session JSON to stdin on every conversation update (debounced 300ms). `__main__.py` parses the JSON, calls each module, composes two output lines, prints them to stdout, and fires `tmux rename-window` as a side-effect.

**Line 1** (priority left-to-right, truncate from right):
```
✗MAIN +2~3 | +156/-23              # on main, not in worktree
ed3d@feat +2~3 | +156/-23          # normal repo or worktree
ed3d@feat +2~3 | agt:reviewer      # with agent name
```

**Line 2**:
```
████████████▒▒▒▒▒▒▒▒ 60% | 5h:23% ~1h12m 7d:41% ~3d | $1.50 | 12m30s
```

### Boss HP Context Bar

20-character bar where colour represents which 200k-token segment the user is currently in. Gives absolute scale awareness even though the bar shows relative percentage.

Segment colours (each represents 200k tokens of context consumed):
- Segment 1 (0–200k): green
- Segment 2 (200k–400k): cyan
- Segment 3 (400k–600k): yellow
- Segment 4 (600k–800k): magenta
- Segment 5 (800k–1M): red

The filled portion renders in the current segment's colour. The unfilled remainder renders in the previous segment's colour, dimmed — showing what was just burned through.

For 200k context windows, the entire bar is one segment. Colours degrade green → yellow → red by percentage, matching current behaviour.

### Rate Limit Burn Rate

Cached to `/tmp/claude-statusline-rate-{session_id}`. Rolling buffer of `timestamp|used_pct` entries (max 20, appended every 30+ seconds).

Projection:
1. Linear regression over cached entries: `burn_rate = delta_pct / delta_time`
2. `time_to_exhaustion = (100 - current_pct) / burn_rate`
3. `time_to_reset = resets_at - now`
4. If exhaustion < reset → will hit limit. Show exhaustion time with `!` suffix, red percentage.
5. If sustainable → show reset time.

Display: `5h:23% ~1h12m` (sustainable) or `5h:89% ~18m!` (will exhaust).

Absent when `rate_limits` not in session JSON (non-subscriber or pre-first-response).

### tmux Rename

`tmux.py` calls `tmux rename-window` on each render when the computed name differs from the cached name at `/tmp/claude-statusline-tmux-{session_id}`.

A lock file `/tmp/claude-statusline-tmux-lock-{session_id}` suppresses statusline renames. The lock is written by the session-naming skill's Haiku subagent. While the lock exists, the statusline defers. The lock is overwritten (not deleted) when session-naming runs again.

Before any skill names the session: statusline keeps tmux tab as `Cl:<location>`.
After a skill names it: skill's name wins until another skill invocation overwrites it.

### Session-Naming Skill

New skill at `plugins/denubis-plan-and-execute/skills/session-naming/SKILL.md`.

Instructs the invoking agent to spawn a Haiku subagent (`denubis-basic-agents:haiku-general-purpose`) with:
- User's initial prompt (from conversation context)
- Invoking skill name
- Repo name and branch (from git)

The subagent:
1. Generates a 2–4 word lowercase hyphenated domain-specific slug
2. Runs `tmux rename-window "Cl:<slug>"` via Bash
3. Writes the lock file `/tmp/claude-statusline-tmux-lock-{session_id}`
4. Returns the slug to the parent agent

The parent agent relays: "To also rename this session, run: `/rename <slug>`"

### Skill Integration

Four target skills invoke `denubis-plan-and-execute:session-naming` at their "context is clear" moment:

| Skill | Insertion point |
|-------|----------------|
| starting-a-design-plan | After Phase 1 (Context Gathering) |
| starting-an-implementation-plan | After reading the design document |
| executing-an-implementation-plan | After reading the implementation plan |
| systematic-debugging | After Phase 1 (Observation) |

Each adds a single invocation line. The session-naming skill handles all logic.

### Skill Hardening

**Critical peer review at implementation completion:**
`starting-an-implementation-plan` and `executing-an-implementation-plan` invoke `denubis-plan-and-execute:critical-peer-review` as their final step before handing off. This subjects the implementation plan or executed code to falsification-first analysis before the user acts on it.

**Context clear in systematic debugging:**
`systematic-debugging` currently flows from hypothesis generation directly into hypothesis testing. This is problematic: the same context that generated the hypothesis also tests it, creating confirmation bias. A mandatory context clear (`/clear`) between these phases forces hypothesis testing to start fresh, re-reading the codebase without the framing of the generation phase. The skill instructs the user to copy a command, clear context, then paste — the same pattern used in design-to-implementation handoffs.

## Existing Patterns

The current `workflow-statusline.py` uses `/tmp/claude-statusline-git-cache-{dir_hash}` for caching git status with a 5-second TTL. The new package follows this same caching pattern for burn rate data and tmux name tracking.

Skills invoke sub-skills via `denubis-plan-and-execute:skill-name` syntax. The session-naming skill follows this convention and is invoked the same way.

No existing pattern exists for tmux integration or rate limit display — these are new capabilities.

The byobu keybinding addition (`~/.byobu/keybindings.tmux`) follows byobu's standard tmux configuration format, already in use for prefix key rebinding.

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Package Scaffolding
**Goal:** Replace single-file script with uv-managed package. Existing functionality preserved.

**Components:**
- `pyproject.toml` at `plugins/denubis-plan-and-execute/scripts/workflow_statusline/`
- `src/workflow_statusline/__init__.py`, `__main__.py`, `colours.py`, `cache.py`, `git.py`
- Port existing `workflow-statusline.py` logic into package modules
- Remove old `workflow-statusline.py`

**Dependencies:** None (first phase)

**Done when:** `uv run --project .../workflow_statusline workflow-statusline` produces identical output to current script when given same JSON input. Old script removed.
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Boss HP Context Bar
**Goal:** Replace current 10-char percentage-only bar with 20-char boss HP bar.

**Components:**
- `bar.py` — `boss_hp_bar(used_pct, context_window_size)` returning ANSI-coloured string
- Segment colour logic (200k boundaries, dimmed prior layer for remainder)
- Integration into `__main__.py` line 2 composition

**Dependencies:** Phase 1

**Done when:** Bar renders correctly for 200k and 1M context windows. Colour shifts at 200k boundaries. Remainder shows dimmed prior layer. Tests verify segment boundaries and colour transitions.
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: Line 1 Redesign
**Goal:** New line 1 with location priority, red MAIN warning, agent name.

**Components:**
- Updated `git.py` — `git_location()` returns location + worktree status
- `__main__.py` line 1 composition — priority ordering, conditional sections, red MAIN
- Agent name display from `agent.name` field

**Dependencies:** Phase 1

**Done when:** Line 1 shows location first, red `✗MAIN` when on main/master outside worktree, agent name when present. Conditional sections omitted when empty.
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: Rate Limit Display with Burn Rate
**Goal:** Show rate limit usage with projected time-to-exhaustion or time-to-reset.

**Components:**
- `cache.py` — extended with rate limit history cache (rolling buffer, 30s interval, max 20 entries)
- New burn rate projection logic in `__main__.py` or dedicated module
- Line 2 integration: `5h:X% ~time` format with red/`!` for unsustainable pace

**Dependencies:** Phase 1

**Done when:** Rate limits display when present in session JSON, omitted when absent. Burn rate projection shows time estimate. Red + `!` when projected to exhaust before reset. Tests verify projection math and edge cases (no data, single entry, absent field).
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: tmux Integration
**Goal:** Statusline sets tmux window title as side-effect, with lock file deference.

**Components:**
- `tmux.py` — `maybe_rename(session_id, name)` checks cache, calls `tmux rename-window` only on change
- Lock file check: if `/tmp/claude-statusline-tmux-lock-{session_id}` exists, skip rename
- Integration into `__main__.py` as final step after printing

**Dependencies:** Phase 1

**Done when:** tmux window renamed to `Cl:<location>` on render. Name only updated when changed. Lock file suppresses rename. Tests verify caching and lock behaviour.
<!-- END_PHASE_5 -->

<!-- START_PHASE_6 -->
### Phase 6: Session-Naming Skill
**Goal:** New skill that spawns Haiku subagent for domain-specific session naming.

**Components:**
- `plugins/denubis-plan-and-execute/skills/session-naming/SKILL.md`
- Skill instructions: extract context, spawn Haiku, tmux rename, write lock file, return slug
- Lock file write at `/tmp/claude-statusline-tmux-lock-{session_id}`

**Dependencies:** Phase 5 (lock file convention)

**Done when:** Skill can be invoked, Haiku subagent generates appropriate slug, tmux window renamed, user prompted with `/rename` command.
<!-- END_PHASE_6 -->

<!-- START_PHASE_7 -->
### Phase 7: Skill Integration and Hardening
**Goal:** Four target skills invoke session-naming. Implementation skills gain critical peer review. Systematic debugging gains context clear between hypothesis phases.

**Components:**
- `skills/starting-a-design-plan/SKILL.md` — add session-naming invocation after Phase 1
- `skills/starting-an-implementation-plan/SKILL.md` — add session-naming invocation after reading design doc; add `critical-peer-review` invocation at workflow completion
- `skills/executing-an-implementation-plan/SKILL.md` — add session-naming invocation after reading impl plan; add `critical-peer-review` invocation at workflow completion
- `skills/systematic-debugging/SKILL.md` — add session-naming invocation after Phase 1; add mandatory context clear and reset between hypothesis generation and hypothesis testing phases

**Dependencies:** Phase 6

**Done when:** Each target skill invokes session-naming at the specified point. Implementation plan and execution skills invoke critical-peer-review at completion. Systematic debugging enforces context clear between hypothesis generation and testing. Existing skill behaviour otherwise unaffected.
<!-- END_PHASE_7 -->

<!-- START_PHASE_8 -->
### Phase 8: Plugin Release
**Goal:** Version bump and marketplace sync.

**Components:**
- `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json` — version bump
- `.claude-plugin/marketplace.json` — sync version
- `CHANGELOG.md` — add release entry
- Update statusline docs at `plugins/denubis-plan-and-execute/docs/workflow-status-line.md`

**Dependencies:** All previous phases

**Done when:** Version synced across plugin.json, marketplace.json, and CHANGELOG.md. Docs reflect new statusline features.
<!-- END_PHASE_8 -->

## Additional Considerations

**Settings migration:** Users with existing `statusLine` config pointing to `workflow-statusline.py` need to update their command path. The old script is removed. The plugin docs should include migration instructions.

**Statusline performance:** The script runs on every conversation update. The burn rate cache write (every 30s) and tmux rename check (cached) add minimal overhead. Git caching remains at 5-second TTL. No network calls.

**`rate_limits` absence:** The field is only present for Claude.ai subscribers after the first API response. All rate limit display logic gracefully handles absence — the section is simply omitted from line 2.

**tmux availability:** `tmux rename-window` fails silently outside tmux. The `TMUX` environment variable is checked before attempting rename.
