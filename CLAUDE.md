# denubis-plugins

Claude Code plugins for design, implementation, and development workflows.

## Working Philosophy

### HALT When Things Feel Sideways

This repo spends most of its time mid-refactor — files renamed, skills reorganised, standards in flux. When something feels incorrect, contradictory, or inconsistent, **halt and discuss** rather than work around the anomaly.

Concrete triggers:

- Repo state looks mixed (old and new conventions coexisting, orphaned files, rename mid-flight).
- A design decision contradicts the active refactor direction.
- Tool results, skill contents, or documents conflict with each other.
- About to produce a large artifact (design doc, rewrite, plan) on assumptions that may be stale.
- A reviewer, auditor, or test-analyst returns substantial findings (Critical / Important / Multiple Minor / NEEDS_REVISION). Even if the top-level summary is "APPROVED" or "no strict gaps", interrogate every level before acting — a Minor finding or a "flagged but not a gap" note may hint at a false-world-model assumption the reviewer didn't escalate. See `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/feedback_review-all-levels.md`.
- A planning decision feels skeevy, even if a subagent or prior session approved it. Surface the concern ("Why are we grepping for that?", "Is this rubric-as-text?") and re-examine before writing more.
- A batch-fix pattern emerges (multiple findings queued for implementation). Batch-fixing skips the discussion step where embedded assumptions get surfaced. Work findings one by one, discussing what each fix reveals before moving to the next.

Default: **HALT and discuss, not HALT and decide unilaterally.** Raise the discrepancy in plain language and wait for direction. When a revision is substantial, a "halt and escalate to next session" is a valid choice — rushed revisions often miss the same structural issues the original work missed.

## Conventions

### Task Invocations Use XML Syntax

When documenting Task tool invocations in skills or agent prompts, use XML-style blocks:

```
<invoke name="Task">
<parameter name="subagent_type">denubis-basic-agents:sonnet-general-purpose</parameter>
<parameter name="description">Brief description of what the subagent does</parameter>
<parameter name="prompt">
The prompt content goes here.

Can be multiple lines.
</parameter>
</invoke>
```

This format keeps the model on-rails better than fenced code blocks with plain text descriptions.

**Do not** write Task invocations as prose like "Use the Task tool with subagent_type X and prompt Y". Use the XML block format.

### Schema Constants from Authoritative Source

When a subagent prompt references a schema-level value set (a CHECK constraint's allowed values, a StrEnum's members, a tuple defining valid states), derive the list by reading the authoritative implementation file at dispatch time — not from documentation, summaries, or memory. Documentation drifts; memory hallucinates; subagents inherit whatever the orchestrator passes in.

**Authoritative sources**: the implementation file (e.g., `db.py`'s `CLASSIFICATION_VALUES`), not the design plan or architecture doc that describes it.

**Why**: a Critical in Phase 1 review of denubis-crash-recovery traced to passing composite section-key strings (`borderline+ambiguous_match`) as if they were the DB column values that the rest of the plan used (bare `borderline` + separate reason column). The CHECK constraint was schema-locked to the wrong shape until caught on re-review. The slip happened because the value list was generated from memory rather than read from `db.py`.

### Python Targets 3.14+ — Modern Syntax Is Intentional

This codebase targets Python 3.14+ (ruff `target-version = py314`). Modern syntax that does not parse on older interpreters is **deliberate, not a bug**. Do not "fix" it back, and do not flag it in review as a Python 2 relic.

Most-tripped-over case: **PEP 758 parenthesis-less `except`**. `except TypeError, ValueError, IndexError:` (no parentheses around the tuple) is valid from 3.14 and catches all three, exactly like the parenthesised form. It is used intentionally in application and skill scripts (`resolve.py`, `crash_recovery/*`, `workflow_statusline`, `token-estimator`) that run under uv in script mode or as packaged tools pinned to 3.14. It is **not** the Python 2 `except E, name:` bind form. Leave it — but **not in hooks**, see the carve-out below.

**Corollary — PEP 723 floors must match.** A script using 3.14-only syntax must declare `# requires-python = ">=3.14"`, not `>=3.11`. With a `>=3.11` floor, `uv run` may provision a 3.11–3.13 interpreter and the file dies with a `SyntaxError` before any logic runs. When you add 3.14-only syntax to a PEP 723 script, bump its `requires-python` in the same edit.

**Carve-out — hooks must stay portable to ≥3.9, not 3.14.** Hooks are invoked `uv run python "$script"` (a command, not script mode), fired from the *user's* current working directory on whatever machine has the plugin installed. Two consequences make the 3.14 doctrine actively harmful here. First, `uv run python <file>` does **not** read PEP 723 inline metadata — only `uv run <file>` (script mode) does — so a `requires-python = ">=3.14"` floor in a hook never binds, and uv hands the file to whatever `python` the user's project resolves, which may be system 3.9. Second, a colleague on stock-macOS Python 3.9 then hits a `SyntaxError` (parenthesis-less `except`) or a def-time `TypeError` (a runtime-evaluated `str | None` annotation) before any logic runs, and their Stop/PreToolUse hooks silently die. So hooks (`plugins/*/hooks/*.py`) must parse and import on 3.9+: add `from __future__ import annotations` so PEP 604 annotations stay strings, and write excepts in portable form — collapse to a common base class (`except OSError:` covers `FileNotFoundError`/`PermissionError`) or split into single-exception clauses, never a bare tuple (ruff's pyupgrade rewrites `except (A, B):` back to the 3.14-only PEP 758 form under `target-version = py314`, so the tuple is not stable). `pretooluse-bash-dispatcher.py` documents this in-file with a "Do not recombine" note; the rollout was completed across the remaining hooks on 2026-06-20.

**Why:** repeated sessions have "discovered" the parenthesis-less `except` as a syntax error, burnt time confirming it parses, and nearly reverted valid code. It parses. It is intended. Stop re-litigating it.

### Version Updates Require Marketplace and Changelog Sync

When updating a plugin's version in its `.claude-plugin/plugin.json`, you must also:

1. Update the corresponding version in `.claude-plugin/marketplace.json` at the repo root
2. Add a changelog entry to `CHANGELOG.md` at the repo root

Changelog entries go at the top (after the `# Changelog` heading) and follow the format:

```markdown
## [plugin-name] [version]

Brief description of the release.

**New:**
- New features or additions

**Changed:**
- Modifications to existing behavior

**Fixed:**
- Bug fixes
```

Only include sections that apply. Keep entries concise.
