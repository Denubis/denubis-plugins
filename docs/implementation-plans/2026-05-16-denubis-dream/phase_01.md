# denubis-dream Implementation Plan — Phase 1: Plugin scaffolding

**Goal:** `/plugin list` shows `denubis-dream`; `/dream` is invocable in this repo and reaches a stub message announcing the plugin is loaded but behaviour is not yet implemented.

**Architecture:** Skill-driven Claude Code plugin under `plugins/denubis-dream/`. Two-file slash-command pattern: `commands/dream.md` aliases the `denubis-dream:dreaming` skill (matches denubis-plan-and-execute and denubis-00-getting-started precedent). No Python helpers — design DR1.

**Tech Stack:** Markdown skill files, JSON plugin manifests. No runtime dependencies.

**Scope:** Phase 1 of 7.

**Codebase verified:** 2026-05-17 (codebase-investigator confirmed: denubis-bibliography plugin.json shape, marketplace.json schema and 2.0.0 version, CHANGELOG format, `.gitignore` absence of `memory.dream-*`, plugin name uniqueness; clarified that `commands/<name>.md` alias is canonical for short slash commands).

**Phase Type:** infrastructure

---

## Acceptance Criteria Coverage

Phase 1 is infrastructure. Verification is operational per the `/dream` UAT checklist (Phase 7).

This phase implements the artefacts required for these acceptance criteria, all verified operationally:

### denubis-dream.AC1: Plugin discoverability and structure
- **denubis-dream.AC1.1 Success:** `plugins/denubis-dream/.claude-plugin/plugin.json` exists with `name: denubis-dream`, `version: 0.1.0`, `license: CC-BY-SA-4.0`.
- **denubis-dream.AC1.2 Success:** `.claude-plugin/marketplace.json` contains a `denubis-dream` entry pointing to `./plugins/denubis-dream` with matching version.
- **denubis-dream.AC1.3 Success:** `CHANGELOG.md` has a `[denubis-dream] 0.1.0` entry following the repo's changelog format.
- **denubis-dream.AC1.4 Success:** `/plugin list` (in a session opened in this repo) shows `denubis-dream`.
- **denubis-dream.AC1.5 Success:** `/dream` is invocable as a slash command in a Claude Code session opened in this repo.
- **denubis-dream.AC1.6 Failure:** Marketplace JSON validation fails if `denubis-dream` entry is malformed (missing version, wrong source path).

**Verifies: None mechanically.** Success = operational checks listed in the Phase 7 uat-checklist pass.

**DoD #9 prep:** `.gitignore` line for `memory.dream-*` lands in this phase (defence-in-depth — the dated dir is normally outside any worktree, but the line documents intent and protects against accidental inclusion if a future change moves the dated dir into the tree).

---

<!-- START_TASK_1 -->
### Task 1: Create plugin.json

**Files:**
- Create: `plugins/denubis-dream/.claude-plugin/plugin.json`

**Step 1: Create the file**

Create `plugins/denubis-dream/.claude-plugin/plugin.json` with the following content (shape mirrors `plugins/denubis-bibliography/.claude-plugin/plugin.json` exactly):

```json
{
    "name": "denubis-dream",
    "description": "Audit a project's per-project auto-memory against the historical record of Claude Code conversations. Produces a reviewable proposed-change tree without touching live memory during the audit.",
    "version": "0.1.0",
    "author": {
        "name": "Brian Ballsun-Stanton",
        "github": "denubis"
    },
    "license": "CC-BY-SA-4.0",
    "keywords": ["memory", "audit", "claude-code", "auto-memory", "dream"]
}
```

**Step 2: Verify operationally**

Run: `cat plugins/denubis-dream/.claude-plugin/plugin.json | python3 -m json.tool`
Expected: file pretty-prints without error (validates JSON syntax).

**Step 3: Commit**

Single-commit cadence — defer commit until the full Phase 1 set is in place (Task 7), per the `feedback_commit-cadence.md` memory: bundle related fixes, don't commit per-task during infrastructure scaffolding.
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Create skill skeleton

**Files:**
- Create: `plugins/denubis-dream/skills/dreaming/SKILL.md`

**Step 1: Create the file**

Create `plugins/denubis-dream/skills/dreaming/SKILL.md` with the following content. The frontmatter mirrors `plugins/denubis-bibliography/skills/using-bibliography/SKILL.md` (including `last-reviewed`).

```markdown
---
name: dreaming
description: Audit a project's per-project auto-memory against the historical record of Claude Code conversations. Produces a reviewable proposed-change tree under ~/.claude/projects/<slug>/memory.dream-YYYY-MM-DD/ without touching live memory during the audit.
user-invocable: true
last-reviewed: 2026-05-17
---

# denubis-dream

**Announce at start:** "I'm using the denubis-dream:dreaming skill."

## Scaffold status

This is the Phase 1 scaffold. The full pipeline (mode detection, slug-prefix discovery, Sonnet retrieval, Opus judgement, reconciliation walk, finalisation) lands in Phases 2-6 of the implementation plan.

When invoked at this stage, the skill announces itself, prints:

> denubis-dream:dreaming — scaffold ready, behaviour not yet implemented.

…and exits without modifying anything.

## Reference

- Design plan: `docs/design-plans/2026-05-16-denubis-dream.md`
- Implementation plan: `docs/implementation-plans/2026-05-16-denubis-dream/`
```

**Step 2: Verify operationally**

No file-level verification; full operational verification happens in Task 7.
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Create command alias stub

**Files:**
- Create: `plugins/denubis-dream/commands/dream.md`

**Step 1: Create the file**

Create `plugins/denubis-dream/commands/dream.md`. Pattern mirrors `plugins/denubis-plan-and-execute/commands/starting-a-design-plan.md` (single-line command-routing layer).

```markdown
---
description: Audit per-project auto-memory against the historical record of Claude Code conversations
---

Use your Skill tool to engage the `denubis-dream:dreaming` skill. Follow it exactly as written.
```

**Step 2: Verify operationally**

No file-level verification; routing verified in Task 7.
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Register in marketplace.json

**Files:**
- Modify: `.claude-plugin/marketplace.json`

**Step 1: Add the entry**

Locate the `plugins` array in `.claude-plugin/marketplace.json` (top-level marketplace version stays at `2.0.0` — do NOT bump). Add this entry alphabetically (or at the end if alphabetical ordering is not enforced — check the current file's pattern first). Use the exact shape used by other denubis entries (e.g., `denubis-bibliography` at lines 191-207 of the current marketplace.json):

```json
{
  "name": "denubis-dream",
  "description": "Audit a project's per-project auto-memory against the historical record of Claude Code conversations. Produces a reviewable proposed-change tree without touching live memory during the audit.",
  "version": "0.1.0",
  "source": "./plugins/denubis-dream",
  "author": {"name": "Brian Ballsun-Stanton", "github": "denubis"},
  "license": "CC-BY-SA-4.0",
  "keywords": ["memory", "audit", "claude-code", "auto-memory", "dream"]
}
```

**Step 2: Verify operationally**

Run: `cat .claude-plugin/marketplace.json | python3 -m json.tool > /dev/null`
Expected: validates without error.

Run: `python3 -c "import json; m = json.load(open('.claude-plugin/marketplace.json')); names = [p['name'] for p in m['plugins']]; assert 'denubis-dream' in names; assert m['version'] == '2.0.0'; print('OK')"`
Expected: prints `OK`.
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: Add CHANGELOG entry

**Files:**
- Modify: `CHANGELOG.md`

**Step 1: Prepend the new entry**

Open `CHANGELOG.md`. The current top entry (under the `# Changelog` heading) is `## [bibliography] 0.2.3`. Insert a new section above that entry, immediately under the changelog heading line, matching the repo convention (`## [plugin-name] version` + `**New:**` subsection):

```markdown
## [denubis-dream] 0.1.0

Initial scaffolding for the denubis-dream auto-memory audit plugin. Skill skeleton and `/dream` slash-command alias only; the full audit pipeline lands in subsequent phases.

**New:**
- Plugin manifest at `plugins/denubis-dream/.claude-plugin/plugin.json`.
- `denubis-dream:dreaming` skill skeleton with `user-invocable: true` frontmatter.
- `/dream` command alias routing to the `dreaming` skill.
- Marketplace registration at `.claude-plugin/marketplace.json`.
- `.gitignore` entry for `memory.dream-*` (defence-in-depth; see design DoD #9).
```

**Step 2: Verify**

Run: `head -20 CHANGELOG.md`
Expected: the `[denubis-dream] 0.1.0` heading appears immediately after the `# Changelog` heading.
<!-- END_TASK_5 -->

<!-- START_TASK_6 -->
### Task 6: Update .gitignore

**Files:**
- Modify: `.gitignore`

**Step 1: Add the line**

Open `.gitignore`. Group the new line with the existing transient-directory entries (`.serena/`, `.venv/`, etc.). The current shape (per investigator):

```
.worktrees/
.claude/settings.local.json
.serena/
.venv/
__pycache__/
*.pyc
```

Insert `memory.dream-*` after `.serena/` so it lives with the other transient/scratch directories:

```
.worktrees/
.claude/settings.local.json
.serena/
memory.dream-*
.venv/
__pycache__/
*.pyc
```

**Step 2: Verify**

Run: `grep -q '^memory\.dream-\*$' .gitignore && echo "OK" || echo "MISSING"`
Expected: prints `OK`.
<!-- END_TASK_6 -->

<!-- START_TASK_7 -->
### Task 7: Operational verification + single commit

**Step 1: Verify plugin discoverability**

In a session opened in this repo (a fresh `claude` invocation here, or a `/plugin list` in the current session), confirm `denubis-dream` appears in the listed plugins.

**Step 2: Verify `/dream` routes to the skill**

In the same session, type `/dream` and confirm the skill announces itself and prints the scaffold-status message ("denubis-dream:dreaming — scaffold ready, behaviour not yet implemented") without raising errors.

**If either check fails:** halt and surface the failure mode to the user. Common failure modes: (a) marketplace.json malformed (JSON parse error in Claude Code's load), (b) command alias content mis-formatted (slash command not registered), (c) skill frontmatter missing `user-invocable: true` (skill not exposed), (d) name collision (the investigator confirmed clean — but re-check if a fresh upstream sync happened mid-task).

**Step 3: Single commit for the full Phase 1 set**

Stage all Phase 1 deliverables in one commit per `feedback_commit-cadence.md` — bundle related fixes; no per-task commits during scaffolding.

```bash
git add plugins/denubis-dream/ \
        .claude-plugin/marketplace.json \
        CHANGELOG.md \
        .gitignore
git status   # sanity-check: only the expected files are staged
git commit -m "feat(dream): scaffold denubis-dream 0.1.0 plugin

Adds the plugin manifest, skill skeleton, /dream command alias,
marketplace registration, CHANGELOG entry, and the memory.dream-*
gitignore line. Pipeline behaviour lands in subsequent phases per
docs/implementation-plans/2026-05-16-denubis-dream/."
```

**Step 4: Confirm clean tree post-commit**

Run: `git status`
Expected: `nothing to commit, working tree clean`.
<!-- END_TASK_7 -->
