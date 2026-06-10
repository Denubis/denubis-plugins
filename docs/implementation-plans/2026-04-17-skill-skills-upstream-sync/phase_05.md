# Skill-Skills Upstream Sync — Phase 5: Cross-Reference Audit, Version Bump, Commit

**⚠️ EXECUTION ORDER (L3 revision):** Phase files sort lexically as `phase_01, phase_02, phase_02_5, phase_03, phase_04, phase_05, phase_06` — but the design plan requires **Phase 6 to execute BEFORE Phase 5.** Phase 5 is the terminal phase; its coherent-set commit captures Phase 6's cross-plugin changes too. **Do not execute phase_05.md until phase_06.md is complete.** Lexical sort is not the execution order.

**2026-06-10 Amendment:** Version baselines from Phase 5B (denubis-extending-claude 1.7.0, denubis-plan-and-execute 2.30.0, verified 2026-04-17) are stale — main has moved (extending-claude at 1.7.2+, 164 commits of drift at amendment time). Re-verify all version, marketplace.json, and CHANGELOG baselines at execution time, after the step-0 main merge (see RESUME-PROMPT). Phase 2.6 (model-tier refresh) is in scope for this phase's coherent-set commit and cross-reference audit. Full execution order: `phase_01 → phase_02 → phase_02_5 → phase_02_6 → phase_03 → phase_04 → phase_06 → phase_05`.

**Goal:** Close the sync as a coherent set. Run an exhaustive cross-reference audit to confirm every sub-skill invocation and every supporting-file reference resolves. Bump both affected plugins' versions in lockstep (denubis-extending-claude for Phases 1-4; denubis-plan-and-execute for Phase 6). Sync `.claude-plugin/marketplace.json` at repo root. Append `CHANGELOG.md` entries for both plugins following repo convention. Commit per the user's global commit-split preference.

**Architecture:** Terminal phase — runs after all content phases (1-4 and 6) land. Python audit script is re-runnable and checked into the plan directory for provenance. Version bumps are MINOR for both plugins (feature-level change; no breaking behaviour).

**Tech Stack:** Python 3 for audit script; markdown/JSON for manifests and CHANGELOG. No new dependencies.

**Scope:** 5 of 6 phases from `docs/design-plans/2026-04-17-skill-skills-upstream-sync.md` (Phase 6 is cross-plugin hardening of impl-plan-write; Phase 5 runs after Phase 6 so its coherent-set commit captures all deltas).

**Codebase verified:** 2026-04-17 (Phase 5B direct inspection: denubis-extending-claude at 1.7.0, denubis-plan-and-execute at 2.30.0, marketplace.json lists both with matching names, CHANGELOG uses `## [plugin-name] version` format with New/Changed/Fixed sections).

**Phase Type:** infrastructure (no new tests; operational verification via audit script + file-existence checks)

---

## Acceptance Criteria Coverage

This phase implements and tests:

### skill-skills-upstream-sync.AC5: cross-cutting — version sync, cross-reference audit, commit discipline
- **skill-skills-upstream-sync.AC5.1 Success:** `plugins/denubis-extending-claude/.claude-plugin/plugin.json` version incremented from its pre-Phase-1 value
- **skill-skills-upstream-sync.AC5.2 Success:** `.claude-plugin/marketplace.json` at repo root contains a matching version for `denubis-extending-claude`
- **skill-skills-upstream-sync.AC5.3 Success:** `CHANGELOG.md` at repo root contains a new entry under the `[denubis-extending-claude]` heading at the appropriate version, following the project's New/Changed/Fixed format
- **skill-skills-upstream-sync.AC5.4 Success:** Cross-reference audit via `phase_05_cross_ref_audit.py` (path-form convention, H1 revision 2026-04-19): every `` `denubis-<plugin>:<name>` `` invocation in the five touched skills resolves to a skill (`plugins/<plugin>/skills/<name>/SKILL.md`), agent (`plugins/<plugin>/agents/<name>.md`), or command (`plugins/<plugin>/commands/<name>.md`); every **path-form** supporting-file reference (backticked string containing `/`, optional `:N` or `:N-M` line-range suffix) resolves to a file on disk; every markdown-link reference resolves. Bare backticked filenames (no `/`) are treated as prose vocabulary and not audited. Teaching-material placeholders (angle-bracket prefix, e.g., `` `<your-service>/auth.py` ``) and conditional references enumerated in `CONDITIONAL_PATHS` are silently skipped. Pre-audit spot check via `--dump-matches` confirms the regex catches real references without flagging prose.
- **skill-skills-upstream-sync.AC5.5 Failure:** No commit uses `--no-verify`, `--amend` of a prior commit in this plan, or any forced operation (global CLAUDE.md git safety protocol)
- **skill-skills-upstream-sync.AC5.6 Edge:** Commits split per user's global preference (3+ files → 2+ commits, split by natural concern); tests and implementation for a given phase live in the same commit
- **skill-skills-upstream-sync.AC5.7 Success (extended scope for Phase 6):** `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json` version also incremented; `.claude-plugin/marketplace.json` updated in the same pass; `CHANGELOG.md` gains a second entry under the `[denubis-plan-and-execute]` heading covering Phase 6's impl-plan-write hardening
- **skill-skills-upstream-sync.AC5.8 Success (added during H3 revision; M3 revision 2026-04-19):** Frustration-signal audit executed via `cc-search-chats:search-chat` across all phase-authoring sessions within the plan's implementation window; results committed to `phase_05_frustration_audit.md` with queries, matches (session ID + timestamp + context), and joint human-review categorisation of each match. Replaces the unfalsifiable "Phase 4 IS integration evidence" claim dropped in H3 revision. Any GENUINE-FRUSTRATION matches (regardless of whether the session later course-corrected) are documented with per-phase AC-coverage-downgrade notes — M3 revision 2026-04-19 dropped the prior RESOLVED-IN-SESSION dismissal path because a methodology that requires user frustration to self-correct is methodology that failed at that point

---

## Dependencies and Sources

**Phase dependencies (execution order):**
- Phases 1, 2, 2.5, 3, 4 complete (denubis-extending-claude content changes landed)
- **Phase 6 complete** (denubis-plan-and-execute impl-plan-write hardening landed — AC5.7 scope)
- Phase 5 runs **last** so its commit set includes all deltas

**No external dependencies.** Entirely internal audit + manifest updates.

**Current state (Phase 5B):**
- `denubis-extending-claude/.claude-plugin/plugin.json` version: `1.7.0` → bump to **1.8.0**
- `denubis-plan-and-execute/.claude-plugin/plugin.json` version: `2.30.0` → bump to **2.31.0**
- `.claude-plugin/marketplace.json` at repo root: contains entries for both plugins with name + description + (presumably) version
- `CHANGELOG.md` at repo root: `## [plugin-name] version` format; entries prepended at top (newest first)

---

<!-- START_TASK_1 -->
### Task 1: Write cross-reference audit script

**Verifies:** skill-skills-upstream-sync.AC5.4 (audit mechanism exists)

**Files:**
- Create: `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05_cross_ref_audit.py`

**Convention (H1 revision 2026-04-19 — path-form):** The audit recognises three classes of reference:

1. **Cross-skill invocation:** `` `denubis-<plugin>:<name>` ``. Resolves against `plugins/<plugin>/skills/<name>/SKILL.md`, then `plugins/<plugin>/agents/<name>.md`, then `plugins/<plugin>/commands/<name>.md` — first hit wins. Covers skills, agents, and commands uniformly so cross-plugin references to e.g. `denubis-basic-agents:sonnet-general-purpose` (an agent) or `denubis-plan-and-execute:flesh-it-out` (a command) resolve.
2. **Path-form backticked reference:** backticked string containing at least one `/` and ending in a known extension (`md|js|dot|py|sh|txt`), optional `:N` or `:N-M` line-range suffix. Examples: `` `./model-tier-notes.md` ``, `` `docs/architecture/dfd/0-context-diagram.md` ``, `` `src/foo.py:42-58` ``. Relative paths (`./`, `../`) resolve against the md file's directory; all others resolve against repo root.
3. **Markdown-link reference:** `[text](path/to/file.md)` with optional `#anchor`. External URLs do not match (the `:` in `http://` falls outside the path character class).

**Bare backticked filenames** (e.g., `` `config.py` ``, `` `foo.md` `` — no `/`) are treated as prose vocabulary and **not audited**. Authors who want audit coverage for a same-directory reference write `./filename.md`.

**Teaching-material placeholders** use an angle-bracket prefix (e.g., `` `<your-service>/auth.py` ``). The `<` character is outside the path character class, so placeholders do not match the path-form regex and are not audited. Phase 6 Task ND (see phase_06.md) rewrites impl-plan-write's existing illustrative inline paths to this convention.

**Conditional references** (deliberately optional paths — "use this file if it exists") are enumerated in the script's `CONDITIONAL_PATHS` frozenset. Currently one entry (`.ed3d/implementation-plan-guidance.md`). The audit silently skips matches listed there; absence is not a failure.

**Compatibility with ISSUE-01:** The regex semantics and resolution behaviour in this embedded script are intentionally compatible with the forthcoming common Typer-based tool (see `docs/issues.md` ISSUE-01). When the tool lands, this embedded script will be retired and the plan's Task 1 updated to invoke the tool.

**Step 1: Author the Python audit script**

Create a self-contained Python 3 script that:

1. Enumerates the five denubis touched skills: `writing-skills`, `writing-claude-directives`, `testing-skills-with-subagents`, `epistemic-humility`, `impl-plan-write`.
2. For each skill's `SKILL.md` and every peer `.md` supporting file, scans for the three reference classes above.
3. Resolves each cross-skill invocation by trying skills/, then agents/, then commands/ (first hit wins).
4. Resolves each path-form or markdown-link reference against the md file's directory (for `./`/`../`) or repo root.
5. Skips any match whose captured string is in `CONDITIONAL_PATHS`.
6. Outputs `FAIL` lines to stderr for any unresolved reference; single `PASS` line to stdout on success.
7. Supports `--dump-matches` mode for pre-audit spot-checking: prints every detected reference with `[OK]`/`[BROKEN]` status, exit 0 regardless.
8. Exit code 0 on full pass (or `--dump-matches`), 1 on any failure, 2 on missing target directory.

**Complete script body:**

```python
#!/usr/bin/env python3
"""
Cross-reference audit for skill-skills upstream sync (2026-04-17).

Walks the target skill directories and verifies that every path-form or
markdown-link cross-reference resolves to a file on disk.

Convention:
    - **Path-form references** (e.g., `./foo.md`, `docs/arch/bar.md:42`)
      MUST resolve. Path form requires a `/` in the backticked string.
    - **Markdown-link references** (e.g., `[text](./foo.md)`) MUST resolve.
    - **Bare backticked filenames** (e.g., `config.py`) are treated as
      prose vocabulary and NOT audited. Authors who want audit coverage
      for a same-directory reference should write `./filename.md`.
    - **denubis-<plugin>:<name>** invocations MUST resolve to one of:
      a skill directory (`plugins/<plugin>/skills/<name>/SKILL.md`),
      an agent file (`plugins/<plugin>/agents/<name>.md`), or a command
      file (`plugins/<plugin>/commands/<name>.md`). First match wins;
      skill takes precedence when a name exists in multiple locations.

This is the H1-minimal embedded script. The forthcoming common tool (see
docs/issues.md ISSUE-01) generalises this into a proper Typer-based CLI
with target-list arguments, architecture-presence check, and JSON output.
The convention and core regex semantics are intentionally compatible.

Exit codes:
  0 — all cross-references resolve (or --dump-matches requested)
  1 — at least one broken reference (details on stderr)
  2 — target directory missing

Usage:
  python3 phase_05_cross_ref_audit.py [--repo-root PATH] [--dump-matches]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_REPO_ROOT = Path("/home/brian/people/Brian/brian-ed3d-plugins")

TARGETS = [
    "plugins/denubis-extending-claude/skills/writing-skills",
    "plugins/denubis-extending-claude/skills/writing-claude-directives",
    "plugins/denubis-extending-claude/skills/testing-skills-with-subagents",
    "plugins/denubis-extending-claude/skills/epistemic-humility",
    "plugins/denubis-plan-and-execute/skills/impl-plan-write",
]

# Cross-skill invocations: `denubis-<plugin>:<skill>` with optional backticks.
XREF_RE = re.compile(r"`?(denubis-[a-z-]+):([a-z][a-z0-9-]*)`?")

# Path-form supporting-file reference. Backticked; must contain at least one
# `/`; ends in a known file extension; optional `:N` or `:N-M` line-range
# suffix. Bare filenames without `/` are intentionally NOT matched — they
# are treated as prose vocabulary. Authors who want audit coverage for a
# same-directory reference write `./filename.ext`. Teaching-material
# placeholders should use angle brackets (`<your-service>/auth.py`) so `<`
# as first character fails this character class and the placeholder is
# not audited.
PATH_REF_RE = re.compile(
    r"`([a-zA-Z0-9_.][a-zA-Z0-9_./-]*/[a-zA-Z0-9_.-]+\.(?:md|js|dot|py|sh|txt))(?::\d+(?:-\d+)?)?`"
)

# Markdown-link form: `](path/to/file.ext)` or `](path/to/file.ext#anchor)`.
# External URLs contain `:` which is outside the char class, so they do not
# match.
LINK_REF_RE = re.compile(
    r"\]\(([a-zA-Z0-9_.][a-zA-Z0-9_./-]*\.(?:md|js|dot|py|sh|txt))(?:#[^)]*)?\)"
)

# Conditional paths — references that are deliberately optional ("if the file
# exists, use it") and should not fail the audit when absent. Kept explicit
# and tiny; new entries require a review of whether the path is truly
# conditional-by-design or just a broken reference.
CONDITIONAL_PATHS: frozenset[str] = frozenset({
    ".ed3d/implementation-plan-guidance.md",  # impl-plan-write finalization hook — optional project-local guidance
})


def resolve_xref(plugin: str, name: str, repo_root: Path) -> Path | None:
    """Resolve a `denubis-<plugin>:<name>` reference by trying each target
    class the ecosystem uses, in order: skills/, agents/, commands/.
    First hit wins. Returns None if no target resolves.
    """
    base = repo_root / "plugins" / plugin
    candidates = (
        base / "skills" / name / "SKILL.md",
        base / "agents" / f"{name}.md",
        base / "commands" / f"{name}.md",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def resolve_path_ref(ref: str, md_path: Path, repo_root: Path) -> Path | None:
    """Resolve relative refs (`./`, `../`) against the md file's dir;
    everything else against repo root. Return Path if exists, else None.
    """
    if ref.startswith(("./", "../")):
        candidate = (md_path.parent / ref).resolve()
    else:
        candidate = (repo_root / ref).resolve()
    return candidate if candidate.exists() else None


def audit_file(
    md_path: Path, repo_root: Path, dump_matches: bool = False
) -> list[tuple[int, str, str]]:
    results: list[tuple[int, str, str]] = []
    text = md_path.read_text()
    for line_num, line in enumerate(text.splitlines(), start=1):
        for match in XREF_RE.finditer(line):
            plugin, name = match.group(1), match.group(2)
            resolved = resolve_xref(plugin, name, repo_root)
            if dump_matches:
                status = "OK" if resolved else "BROKEN"
                results.append((line_num, "xref", f"[{status}] {plugin}:{name}"))
            elif resolved is None:
                results.append((line_num, "xref", f"{plugin}:{name} unresolved"))
        for regex, kind in ((PATH_REF_RE, "path-ref"), (LINK_REF_RE, "link-ref")):
            for match in regex.finditer(line):
                ref = match.group(1)
                if ref in CONDITIONAL_PATHS:
                    continue  # conditional-by-design; not a failure when absent
                resolved = resolve_path_ref(ref, md_path, repo_root)
                if dump_matches:
                    status = "OK" if resolved else "BROKEN"
                    results.append((line_num, kind, f"[{status}] {ref}"))
                elif resolved is None:
                    results.append((line_num, kind, f"{ref} unresolved"))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cross-reference audit for skill-skills upstream sync."
    )
    parser.add_argument(
        "--repo-root",
        default=str(DEFAULT_REPO_ROOT),
        type=Path,
        help="Repository root (default: DEFAULT_REPO_ROOT constant)",
    )
    parser.add_argument(
        "--dump-matches",
        action="store_true",
        help="Print ALL detected references (OK and BROKEN) for spot-check; exit 0",
    )
    args = parser.parse_args()
    repo_root: Path = args.repo_root

    total_failures = 0
    for target in TARGETS:
        target_dir = repo_root / target
        if not target_dir.is_dir():
            print(f"FAIL: target directory missing: {target_dir}", file=sys.stderr)
            if not args.dump_matches:
                total_failures += 1
            continue
        for md_path in sorted(target_dir.glob("**/*.md")):
            results = audit_file(md_path, repo_root, dump_matches=args.dump_matches)
            rel = md_path.relative_to(repo_root)
            for line_num, kind, message in results:
                if args.dump_matches:
                    print(f"MATCH [{kind}] {rel}:{line_num} — {message}")
                else:
                    print(f"FAIL [{kind}] {rel}:{line_num} — {message}", file=sys.stderr)
                    total_failures += 1

    if args.dump_matches:
        print("(dump-matches mode — no PASS/FAIL evaluation)", file=sys.stderr)
        return 0
    if total_failures == 0:
        print("PASS: all cross-references and supporting-file pointers resolve.")
        return 0
    print(f"TOTAL FAILURES: {total_failures}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

**Step 2: Pre-audit spot check via `--dump-matches`**

Before running the real audit, dump every detected reference for manual spot-check:

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
python3 docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05_cross_ref_audit.py --dump-matches
```

Expected: a list of `MATCH [xref|path-ref|link-ref] <rel_path>:<line> — [OK|BROKEN] <reference>` lines, one per detected reference. Read the output and confirm three invariants:

- Every legitimate cross-reference (as authored in Phases 1-4 and Phase 6) appears with `[OK]`.
- No prose-vocabulary backticked filename (e.g., a literal `` `config.py` `` with no `/`) appears in the list — if one does, the regex has loosened and must be narrowed.
- Any `[BROKEN]` entry is a real broken reference, not a false positive (teaching placeholder that slipped through the angle-bracket convention, conditional path not yet added to `CONDITIONAL_PATHS`, etc.).

If a legitimate cross-reference is missing from the dump (regex too narrow), either rewrite the reference to path-form or extend the regex. If prose vocabulary appears (regex too broad), halt and narrow before Step 3.

**Step 3: Run the audit against current state**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
python3 docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05_cross_ref_audit.py
```

Expected at Phase 5 execution time (after Phases 1-4 and Phase 6 have landed): `PASS: all cross-references and supporting-file pointers resolve.`

If the audit reports FAILs, halt and surface. Common failure modes:

- A sub-skill / agent / command was renamed but one of the orchestrators didn't update its cross-reference.
- A path-form supporting-file reference points at a wrong directory (e.g., typo in `./` vs `../`).
- A markdown-link references a moved file.
- A teaching example wasn't converted to angle-bracket placeholder form during Phase 6 Task ND (illustrative-path rewrite in `impl-plan-write/SKILL.md`).

**Step 4: Commit the audit script**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05_cross_ref_audit.py
git commit -m "chore(phase-05): add cross-reference audit script for skill-skills sync

Python audit walks the five sync-touched skills (writing-skills,
writing-claude-directives, testing-skills-with-subagents,
epistemic-humility, impl-plan-write) and verifies three reference
classes resolve: cross-skill invocations (skills/agents/commands),
path-form backticked references, and markdown-link references.

Convention: path-form requires '/' in the backticked string. Bare
backticked filenames are prose vocabulary, not audited. Teaching
placeholders use angle-bracket prefix ('<your-service>/...') to opt
out of audit. Conditional references enumerated in CONDITIONAL_PATHS.

Re-runnable: python3 phase_05_cross_ref_audit.py [--repo-root PATH]
                                                 [--dump-matches]
Exit codes: 0 pass, 1 broken references, 2 missing target dir.

Regex semantics mirror the forthcoming common tool — see
docs/issues.md ISSUE-01 for the Typer-based generalisation this
embedded script will eventually migrate to.

Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md (AC5.4)
      docs/issues.md ISSUE-01"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Bump denubis-extending-claude to 1.8.0; update marketplace.json and CHANGELOG.md

**Verifies:** skill-skills-upstream-sync.AC5.1, skill-skills-upstream-sync.AC5.2, skill-skills-upstream-sync.AC5.3

**Files:**
- Modify: `plugins/denubis-extending-claude/.claude-plugin/plugin.json` (version field)
- Modify: `.claude-plugin/marketplace.json` (denubis-extending-claude entry's version field)
- Modify: `CHANGELOG.md` at repo root (prepend new entry after `# Changelog` heading)

**Step 1: Bump plugin.json version**

Edit `plugins/denubis-extending-claude/.claude-plugin/plugin.json`: change `"version": "1.7.0"` to `"version": "1.8.0"`.

**Step 2: Update marketplace.json**

Edit `.claude-plugin/marketplace.json` at repo root. Locate the `denubis-extending-claude` entry and update its version field to `1.8.0`.

**Step 3: Prepend CHANGELOG entry**

Insert at the top of `CHANGELOG.md` (after `# Changelog` heading, before the most-recent existing entry):

```markdown
## [denubis-extending-claude] 1.8.0

Skill-skills upstream sync: new `epistemic-humility` reference skill, restructure of `writing-skills` / `writing-claude-directives` / `testing-skills-with-subagents` against obra/superpowers, and establishment of the `examples/` subdirectory convention.

**New:**
- `epistemic-humility/` reference-type skill with four-section rubric (Scope / Observability / Process / Failure-pattern) sourced from AbsenceJudgement.tex (technoscholasticism, Schön 1994 p.132 four questions, Jones 2025 three conditions), with Latour 1987/1999 grounding for the Observability black-box framing. Explicit sibling supporting files `absencejudgement-citations.md` (paragraph-level verbatim quotations) and `self-application.md` (AC4.5 coherence demonstration).
- `writing-skills/anthropic-best-practices.md` imported verbatim from obra with denubis preface.
- `writing-skills/render-graphs.js` imported verbatim (Node + graphviz; skill-author tool, not runtime).
- `writing-skills/examples/CLAUDE_MD_TESTING.md` establishes the `examples/` subdirectory convention.
- `writing-skills/README.md` documents supporting-file dependencies.
- `writing-claude-directives/model-tier-notes.md` with per-model sections for Opus 4.7 / Sonnet 4.6 / Haiku 4.5 (dated header, citation URLs, system card cross-verification).

**Changed:**
- `writing-skills/SKILL.md` rewritten as thin cornerstone orchestrator (≤250 lines) sequencing three sub-skills: `epistemic-humility` (scope check) → `writing-claude-directives` (phrasing) → `testing-skills-with-subagents` (RED/GREEN/REFACTOR). Rubric callback folded into "When to Create a Skill" section. Workflow H2 makes sub-skill sequencing first-class.
- `writing-claude-directives/SKILL.md` restructured: Opus 4.5 "Think Sensitivity" section removed (superseded); per-model anchors replacing generic "Claude 4.x"; aggressive-language guidance updated to current 2026-04 Anthropic dial-back-aggressive-language framing; new "Rubric Callback" H2 cross-referencing `epistemic-humility`.
- `testing-skills-with-subagents/SKILL.md` restructured: conversation-precedent protocol (cc-search-chats:search-chat or user-run fresh chat session, independent-session gate) prepended to RED phase; synthetic pressure-scenarios demoted to REFACTOR completeness; obra's 7-pressure table absorbed; letter-vs-spirit promoted to foundational H3; meta-testing three-category framing verified and filled; Haiku-judgement passage retained and reframed with operator-empirical anchor (amended 2026-04-22 plan-amendment pass — not removed); tier-test structural principle preserved; "No Blaming the Model" and flaky-result discipline preserved byte-identical.
- `writing-claude-directives/graphviz-conventions.dot` gains obra attribution comment (content byte-identical).

**Fixed:**
- Stale Opus 4.5 "Think Sensitivity" claim in `writing-claude-directives/SKILL.md` removed (superseded by Opus 4.7 effort-level controls).
- Unsupported "Haiku struggles with judgement calls" claim in `testing-skills-with-subagents/SKILL.md` removed (not in current 2026-04 Anthropic docs).

**Explicitly NOT imported from obra:**
- `persuasion-principles.md` — denubis departs from obra on this point. Persuasion principles are compliance-induction levers that contradict the `epistemic-humility` rubric, Anthropic's current prompting guidance, and AbsenceJudgement's technoscholasticism critique. See design plan Additional Consideration *Persuasion principles do not belong in denubis skills*.
```

**Step 4: Verify the triad is synchronised**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
import json
with open('plugins/denubis-extending-claude/.claude-plugin/plugin.json') as f:
    plugin_version = json.load(f).get('version')
with open('.claude-plugin/marketplace.json') as f:
    marketplace = json.load(f)
    mp_entry = next((p for p in marketplace.get('plugins', []) if p.get('name') == 'denubis-extending-claude'), None)
    assert mp_entry is not None, 'denubis-extending-claude not found in marketplace.json'
    mp_version = mp_entry.get('version')
assert plugin_version == mp_version == '1.8.0', \
    f'version mismatch: plugin.json={plugin_version}, marketplace.json={mp_version}, expected 1.8.0'
with open('CHANGELOG.md') as f:
    changelog = f.read()
assert '## [denubis-extending-claude] 1.8.0' in changelog, 'CHANGELOG entry for 1.8.0 missing'
print('denubis-extending-claude 1.8.0 triad synchronised')
"
```
Expected: `denubis-extending-claude 1.8.0 triad synchronised`.

**Step 5: Commit as a bundle**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-extending-claude/.claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md
git commit -m "release(denubis-extending-claude): 1.8.0 — skill-skills upstream sync

- plugin.json: 1.7.0 -> 1.8.0 (MINOR; feature-level change)
- marketplace.json: version sync
- CHANGELOG.md: New / Changed / Fixed entry covering Phases 1-4

Captures deltas from skill-skills-upstream-sync Phases 1-4:
new epistemic-humility skill, restructure of three orchestrators,
obra supporting-file imports, examples/ convention established.

See CHANGELOG.md entry for full scope.
Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md"
```
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Bump denubis-plan-and-execute to 2.31.0; update marketplace.json and CHANGELOG.md (Phase 6 deltas)

**Verifies:** skill-skills-upstream-sync.AC5.7 (cross-plugin scope extension)

**Files:**
- Modify: `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json` (version field)
- Modify: `.claude-plugin/marketplace.json` (denubis-plan-and-execute entry's version field)
- Modify: `CHANGELOG.md` at repo root (prepend new entry above the denubis-extending-claude 1.8.0 entry from Task 2, since CHANGELOG is newest-first)

**Step 1: Bump plugin.json version**

Edit `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json`: change `"version": "2.30.0"` to `"version": "2.31.0"`.

**Step 2: Update marketplace.json**

Edit `.claude-plugin/marketplace.json` at repo root. Locate the `denubis-plan-and-execute` entry and update its version field to `2.31.0`.

**Step 3: Prepend CHANGELOG entry**

Insert ABOVE the `## [denubis-extending-claude] 1.8.0` entry from Task 2 (newest-first ordering):

```markdown
## [denubis-plan-and-execute] 2.31.0

Harden `impl-plan-write` against UAT smuggling: three-lens-table amendment + mandatory automatable/not-automatable template lines + per-phase pre-presentation self-audit (step 6.5, planner-side hygiene) + Task 4 Collation audit as the structural anti-smuggling gate (second defensive layer, dedicated Sonnet subagent before `uat-requirements.md` is written) + Finalization existence gate. Surfaced mid-Part-1 of the skill-skills upstream sync when applying impl-plan-write to plan that work.

**New:**
- Per-phase Task-ND pre-presentation self-audit (step 6.5): every proposed UAT entry is scored against the three anti-smuggling tests (Decomposition / Reduction / Disagreement) at planner-side BEFORE step 7 (AskUserQuestion). The self-audit does NOT block user approval — it surfaces concerns to the user so the step-7 conversation is informed. Structural anti-smuggling enforcement lives in the Task 4 Collation audit (dedicated Sonnet subagent runs every entry through the three tests before `uat-requirements.md` is written) and the Finalization existence gate.
- Mandatory `**What's automatable:**` / `**What's NOT automatable:**` lines preceding every UAT entry's falsification template. Forces the Decomposition thought at authoring time.
- `UAT Requirements Collation` section (SKILL.md line 1285) collation audit: dedicated subagent runs every entry through the three tests before `uat-requirements.md` is written. Second defensive layer behind the per-ND gate.
- Finalization existence gate on `uat-requirements.md`: Finalization cannot complete until the file exists at PLAN_DIR, even in minimal "No human-judgment UAT entries" form. Closes the silent-skip hole.
- Worked examples: smuggled-entry refusal + adapted genuine surface UAT; infrastructure phase with zero UAT entries demonstrating first-class zero-UAT output.

**Changed:**
- Three-lens table Popper row reframed from "Always — every decision gets a falsification test" to "Every decision gets a falsifiability ANALYSIS; the UAT entry is the subset where falsification genuinely requires human judgment. Zero UAT entries is a valid outcome." Addresses false-positive pattern where infrastructure phases produced mechanistically-automatable Popper entries.

**Fixed:**
- Rubric-vs-gate drift: the three anti-smuggling tests previously lived only in `exec-uat-gate` (execution time); planner-side enforcement was rubric-as-text without a forcing function. Now structurally enforced at two points — (a) the Task 4 Collation audit dispatches a dedicated Sonnet subagent to run every proposed entry through the three tests before `uat-requirements.md` is written (second defensive layer; UAT Requirements Collation section, SKILL.md line 1285); (b) the Finalization existence gate halts Finalization unless `uat-requirements.md` is on disk. Planner-side Task-ND self-audit at step 6.5 is hygienic (surfaces concerns to the user before step 7 approval), NOT structural — the user can still approve a surfaced entry; the Task 4 collation audit is what prevents smuggled entries from reaching `uat-requirements.md`.
```

**Step 4: Verify the triad**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
import json
with open('plugins/denubis-plan-and-execute/.claude-plugin/plugin.json') as f:
    plugin_version = json.load(f).get('version')
with open('.claude-plugin/marketplace.json') as f:
    marketplace = json.load(f)
    mp_entry = next((p for p in marketplace.get('plugins', []) if p.get('name') == 'denubis-plan-and-execute'), None)
    assert mp_entry is not None, 'denubis-plan-and-execute not found in marketplace.json'
    mp_version = mp_entry.get('version')
assert plugin_version == mp_version == '2.31.0', \
    f'version mismatch: plugin.json={plugin_version}, marketplace.json={mp_version}, expected 2.31.0'
with open('CHANGELOG.md') as f:
    changelog = f.read()
assert '## [denubis-plan-and-execute] 2.31.0' in changelog, 'CHANGELOG entry for 2.31.0 missing'
# Ordering check — 2.31.0 should appear before 1.8.0 (newest first, cross-plugin)
p29 = changelog.find('## [denubis-plan-and-execute] 2.31.0')
e18 = changelog.find('## [denubis-extending-claude] 1.8.0')
assert p29 < e18, 'CHANGELOG ordering wrong — plan-and-execute 2.31.0 should be before extending-claude 1.8.0 (newest first)'
# L3 revision 2026-04-19: same-plugin ordering check — 2.31.0 must precede the
# existing 2.30.0 entry for denubis-plan-and-execute. Prior check only compared
# across plugins; a regression where 2.31.0 landed below 2.30.0 would pass the
# cross-plugin check silently.
p30 = changelog.find('## [denubis-plan-and-execute] 2.30.0')
assert p30 != -1, 'existing CHANGELOG entry for denubis-plan-and-execute 2.30.0 missing (L3: baseline for same-plugin ordering check)'
assert p29 < p30, 'CHANGELOG ordering wrong — plan-and-execute 2.31.0 should be before plan-and-execute 2.30.0 (newest first, same plugin)'
print('denubis-plan-and-execute 2.31.0 triad synchronised')
"
```

**Step 5: Commit as a bundle**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-plan-and-execute/.claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md
git commit -m "release(denubis-plan-and-execute): 2.31.0 — impl-plan-write anti-smuggling hardening

- plugin.json: 2.30.0 -> 2.31.0 (MINOR; feature-level change)
- marketplace.json: version sync
- CHANGELOG.md: New / Changed / Fixed entry covering Phase 6 deltas

Captures Phase 6 of skill-skills upstream sync:
- Three-lens table amendment: 'no UAT entry' is first-class
- What's-automatable / What's-NOT-automatable template lines
- Per-phase Task-ND pre-presentation self-audit (step 6.5, planner-side
  hygiene — NOT a structural gate; user can still approve surfaced
  entries at step 7)
- Task 4 UAT Requirements Collation audit (second defensive layer —
  independent Sonnet subagent runs every entry through the three tests
  before uat-requirements.md is written; structural gate)
- Finalization existence gate on uat-requirements.md

Rationale: three anti-smuggling tests (Decomposition / Reduction /
Disagreement) previously lived only in exec-uat-gate (execution time)
and arrived too late. Phase 6 moves enforcement to authoring time.

See CHANGELOG.md entry for full scope.
Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md (Phase 6, AC6, AC5.7)"
```
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Final cross-reference audit + coherent-set verification

**Verifies:** skill-skills-upstream-sync.AC5.4 (audit passes), skill-skills-upstream-sync.AC5.5, skill-skills-upstream-sync.AC5.6

**Files:**
- No new files. Audit-only task.

**Step 1: Re-run cross-reference audit against the post-Phase-5 repo state**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
python3 docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05_cross_ref_audit.py
```
Expected: `PASS: all cross-references and supporting-file pointers resolve.` If any FAILs, halt — something landed inconsistently across the sync phases.

**Step 2: Verify git commit discipline (AC5.5, AC5.6)**

**Branch-discipline guard (M5 revision 2026-04-19).** `git log main..HEAD` silently returns zero commits when run on main itself, which would give AC5.5/5.6 a false pass against an empty result. `denubis-plan-and-execute:executing-an-implementation-plan` has a precondition that blocks execution on main, but this guard is the local belt-and-braces at the point the count is actually taken. Run first:

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
import subprocess, sys
branch = subprocess.check_output(['git', 'branch', '--show-current']).decode().strip()
assert branch not in ('main', 'master', ''), (
    f'AC5.5/5.6 cannot be run on {branch!r}: git log main..HEAD would silently return zero commits. '
    f'Halt execution and invoke denubis-plan-and-execute:using-git-worktrees to create a feature branch.'
)
print(f'branch-discipline guard passed: on {branch!r} (not main/master)')
"
```

If that passes, count commits and inspect the log:

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && git log --oneline main..HEAD 2>/dev/null | head -40
# Count commits from the sync
git log --oneline main..HEAD 2>/dev/null | wc -l
# Verify no --amend was used (no duplicate short-SHAs across commit-reflog vs log — heuristic)
# Verify no --no-verify (git log doesn't record this, but it's a discipline check)
# Verify no force-pushes landed (git reflog origin/main, if applicable)
```

Manual verification checklist (the commit history should show ≥ 31 commits total after H6 revision 2026-04-19):
- Phase 1: 3+ commits (epistemic-humility SKILL.md, absencejudgement-citations.md, self-application.md)
- Phase 2: 5+ commits (precedent, SKILL.md restructure, model-tier-notes.md, graphviz attribution, GREEN verification)
- Phase 2.5: 1+ commits per smell (from the refactoring pipeline)
- Phase 3: 5+ commits (precedent, precedent+Haiku, synthetic demotion, letter-vs-spirit+meta+rubric, audit)
- Phase 4: 6+ commits (precedent, SKILL.md, anthropic-best-practices, render-graphs+README, examples, GREEN)
- Phase 5: 5 commits (audit script, extending-claude 1.8.0, plan-and-execute 2.31.0, Task 4.5 frustration-signal audit, this final audit)
- Phase 6: 6+ commits (Task 1 three-lens amend, Task 2 template lines + worked examples, Task 3 pre-presentation self-audit step 6.5, Task 4 Finalization existence gate + Collation audit, Task 5 retroactive UAT audit file (+optional remediation commit), Task 6 illustrative-path rewrite in impl-plan-write) — lands before Phase 5 per execution-order; its commits are interspersed in the history but precede Phase 5's release commits

No `git commit --amend` of prior-plan commits. No `git push --force` or `--force-with-lease` to any public branch. No `--no-verify`.

**Step 3: Verify Definition-of-Done conditions (design plan Phase 5)**

Confirm each DoD entry:
- [ ] Four artefacts exist at their target paths (epistemic-humility, writing-claude-directives, testing-skills-with-subagents, writing-skills) plus Phase 6's impl-plan-write changes
- [ ] Each has committed RED evidence appropriate to its phase framing (amended 2026-04-22 plan-amendment pass): `phase_02_red_evidence.md` is a static code-smell inventory + the 2026-04-22 independent-session search record (Phase 2 is preventive); `phase_03_red_evidence.md` is session-transcript RED from an independent session (Phase 3 is corrective — its target methodology is transcript-sourcing); `phase_04_red_evidence.md` is a static file-shape diff with pre-rewrite SHA + line-count baseline (Phase 4 is preventive). All three files exist.
- [ ] Each passed GREEN (phase_0N_green_verification.md files exist for Phases 2, 3, 4)
- [ ] Each has a committed rubric self-application walk-through with any surfaced vulnerabilities acknowledged by user (H4 revision: walk-through + vulnerability-surfacing, not pass/fail)
- [ ] `phase_04_green_verification.md` has a "Sub-skill Invocations" section recording which Phase 1-3 outputs were exercised in Phase 4's production (factual invocation record; integration-evidence framing was dropped in H3 revision and replaced with the Task 4.5 frustration-signal audit)
- [ ] UAT audit for `uat-requirements.md` complete (per Phase 6's retroactive audit)

**Step 4: Announce completion (no commit needed — Step 4 is verification-only)**

If all checks pass, announce the sync is complete. The Finalization task (#26) is what gates the handoff to executing-an-implementation-plan.

**Consumer-tracing:** This task's output feeds the Finalization code-reviewer (Task #26) and the executing-an-implementation-plan handoff.
<!-- END_TASK_4 -->

<!-- START_TASK_4_5 -->
### Task 4.5: Frustration-signal audit (retrospective methodology-coherence check)

**Verifies:** skill-skills-upstream-sync.AC5.8

**Files:**
- Create: `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05_frustration_audit.md`

**Purpose:** Replaces the unfalsifiable "Phase 4 IS integration evidence" claim dropped during H3 revision. The original claim asserted that producing `writing-skills/SKILL.md` using the three sub-skills constituted integration evidence — but as DR-P4-INT-1 itself admitted, the written narrative could be perfect while the lived authoring skipped the methodology. This audit adds a concrete, falsifiable proxy: frustration IS observable evidence that the methodology did NOT cohere at a given point. The user's interaction transcripts across the plan's implementation window are the independent record of what actually happened — using the same `cc-search-chats:search-chat` independent-session discipline established for RED evidence sourcing in H2.

**Why this is falsifiable:** Silence does not prove methodology success, but visible frustration DOES prove methodology misalignment at that point. The audit's output is a real pass/fail verdict, not a self-attested narrative.

**Step 1: Scope the search window** (M2 revision 2026-04-19: adapted to cc-search-chats CLI limitations)

**CLI constraints** (empirically verified 2026-04-19; see `docs/issues.md` ISSUE-10): the `cc-search-chats search` CLI accepts a single literal query string passed directly to SQLite FTS5 `MATCH`. It **does not** support:

- Regex (e.g., `no,? stop` is parsed literally, not as an alternation)
- `AND`/`OR` operators in the query string
- Arbitrary start/end timestamps (only `--days N` for recency)
- Hyphens in tokens (crashes with `no such column`)
- Apostrophes (crashes with `fts5: syntax error near "'"`)

Compute the days-since-start for `--days N` and post-filter matches by timestamp:

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
# Start: first authoring commit in the plan directory
START_DATE=$(git log --reverse --format=%ai -- docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/ | head -1 | cut -d' ' -f1)
# End: the most recent commit (Phase 5 Task 4) — computed at audit time, not here
# Days-since (inclusive):
DAYS_SINCE=$(python3 -c "from datetime import date; d1=date.fromisoformat('$START_DATE'); print((date.today()-d1).days + 1)")
echo "Scoping cc-search-chats --days $DAYS_SINCE"
```

Record both `$START_DATE` and the Phase 5 Task 4 commit timestamp at the top of `phase_05_frustration_audit.md` as the audit's time window. The executor will post-filter raw cc-search-chats results by match timestamp to enforce the end-of-window bound (since `--days` only bounds the start).

**Step 2: Run frustration-signal queries via cc-search-chats:search-chat** (M2 revision 2026-04-19: one-term-per-query, no regex, no OR, no apostrophes)

Each query below is a separate `cc-search-chats search "<term>" --days $DAYS_SINCE --json` invocation. The executor collects all match lists and unions them manually (dedup by message UUID). Capture per match: session ID, message UUID, timestamp, role, user message content, plus ±5 surrounding messages via `cc-search-chats context <uuid> --depth 5 --json` (if surrounding context isn't already present in the search output).

**Safe queries** (pass FTS5 cleanly — run each):

- `mate` — Australian-English frustration signal (per `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/MEMORY.md`)
- `FFS` — frustration
- `deeply frustrating` — frustration
- `deeply frustrated` — frustration
- `no stop` — correction/redirect signal (omits the comma variant; phrase-match is close enough)
- `stop no` — same, reverse order
- `this is wrong` — correction
- `yoloed` — signals unintended/reckless action
- `oh god` — frustration exclamation
- `jesus` — frustration exclamation

**Dropped from prior query list** (would crash cc-search-chats on apostrophes — see ISSUE-10):

- `"for fuck's sake"` — dropped; `FFS` covers the frustration class
- `"that's wrong"` — dropped; `this is wrong` covers the correction class
- `"yolo'd"` — dropped; `yoloed` covers
- `"we don't"` — dropped; no clean no-apostrophe alternative captures the same reframe-needed signal. Accept this as a coverage gap; the joint review's "pick up signals I missed" clause (Step 3) catches it.

**Dropped regex-style queries**:

- `no,? stop` / `stop,? no` with comma variants — replaced by literal `no stop` / `stop no`; the comma-variant phrasing may miss some cases but avoids the regex dependency.
- `that['\u2019]s wrong` unicode-class — dropped (see above).

**Uppercase corrections**: separate mechanism — after collecting the query matches, scan user messages in the returned sessions for fully-ALL-CAPS words (single words ≥ 4 chars, not proper names). Use `cc-search-chats list --days $DAYS_SINCE --json` to enumerate sessions, then `cc-search-chats extract <session-id> --json` for content. This is manual scanning, not a query.

**Forward-fix for ISSUE-10**: when cc-search-chats is patched upstream to pre-escape queries (filed as `docs/issues.md` ISSUE-10), this Step 2 can be reverted to the richer original query set. The present restriction is an in-flight-tool-gap workaround, not the intended permanent form.

**Step 3: Joint human review — categorise each match**

Executor + user review matches together. Each match is categorised as:

- **GENUINE-FRUSTRATION:** user expressed frustration at Claude's output; the methodology failed at that point. Whether the session subsequently course-corrected is NOT a dismissal path — a methodology that requires user frustration to self-correct is a methodology that failed at that point. The subsequent correction is worth cataloguing as context but does not downgrade the match's status. (M3 revision 2026-04-19: dropped the prior RESOLVED-IN-SESSION category — frustration is the signal regardless of whether the session later fixed what triggered it.)
- **TECHNICAL-DISAGREEMENT:** user disagreed on a technical point but without frustration (e.g., "no, different approach" without emotional register).
- **QUOTED-ILLUSTRATIVE:** frustration signal appears in a quoted/illustrative context (e.g., discussing the frustration-audit itself, or quoting a prior session). False positive.

Each match's category is recorded with a 1-2 sentence justification. Where a GENUINE-FRUSTRATION match was followed by successful in-session correction, the justification may note that as observational context — but it does not change the category.

**Fatigue-floor and calibration (Meta-M7 revision 2026-04-19).** Fast-categorising a long match list risks false-dismissing genuine matches as QUOTED-ILLUSTRATIVE — especially because this plan's own review sessions discuss the frustration queries by name (`mate`, `FFS`, `yoloed`, `this is wrong`) and will themselves generate QUOTED-ILLUSTRATIVE matches when swept. To bound the fatigue risk, Step 3 has two procedural guardrails:

1. **Fatigue-floor — halt and resume at the 30-match ceiling.** If the combined match list across all queries exceeds 30 matches, do NOT categorise all of them in one sitting. Categorise the first 30, record the cutoff timestamp in `phase_05_frustration_audit.md`, and resume in a later sitting (or later day). The joint reviewer's own self-assessment ("I am still reading each match's context carefully") is the authoritative signal; when that starts slipping into "this one looks obviously illustrative, moving on", halt regardless of count.
2. **Calibration check — blind recategorisation of a random sample.** After all matches are categorised, randomly select three matches from each assigned category (so up to 9 matches total with three categories). The joint reviewer recategorises each blinded sample — the prior verdict hidden, only the match text and ±5 context visible. If the blinded recategorisation disagrees with the original on >1 of the 9, the categorisation pass is flagged as low-confidence: document the disagreement, re-run Step 3 for the whole match list with the disagreement-mode in mind, or narrow the verdict to "audit-flags (calibration failed)" per Step 4. The three-per-category threshold is small enough to be feasible on any match list ≥ 9 matches; for shorter lists, use all-matches recategorisation instead.

Both guardrails are process discipline, not category-scheme changes. They address the Meta-M7 failure mode (categoriser fatigue) without changing the categorisation rules themselves.

**Step 4: Verdict**

- If ZERO genuine-frustration matches AND calibration check passes (≤1 disagreement on the blinded sample — see Step 3 guardrail 2): audit passes. Document "no frustration signals observed across the implementation window; calibration check passed."
- If ≥1 genuine-frustration matches: audit flags methodology failure at that point, regardless of whether the session later course-corrected (M3 revision 2026-04-19). For each flagged match, document:
  - Which phase was being authored
  - Which sub-skill or sub-claim the frustration invalidates
  - Whether the affected AC coverage needs to be downgraded (note in test-requirements.md)
  - If the session course-corrected in the moment, note that as observational context — it does not remove the match from the flag count.
- If calibration check fails (>1 disagreement on the 9-sample blinded recategorisation — see Step 3 guardrail 2): audit flags as `audit-flags (calibration failed)` (Meta-M7 revision 2026-04-19). Document the specific disagreements, note that the original categorisation pass is low-confidence, and either (a) re-run Step 3 in full with the disagreement-mode in mind, or (b) leave the calibration-failed verdict standing — a downstream consumer (Finalization code-reviewer) treats calibration-failed as equivalent to ≥1 genuine-frustration match for AC coverage-downgrade purposes.

**Step 5: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05_frustration_audit.md
git commit -m "docs(phase-05): frustration-signal audit (AC5.8)

Retrospective methodology-coherence check replacing the unfalsifiable
integration-evidence claim dropped in H3 revision. Uses cc-search-chats
to scan all phase-authoring sessions within the plan's implementation
window for user-expressed frustration signals. Matches jointly reviewed
and categorised (GENUINE-FRUSTRATION / TECHNICAL-DISAGREEMENT /
QUOTED-ILLUSTRATIVE); any GENUINE-FRUSTRATION matches (regardless of
whether the session later course-corrected) documented with per-phase
AC-coverage-downgrade notes. M3 revision 2026-04-19 dropped the prior
RESOLVED-IN-SESSION dismissal path.

Refs: AC5.8; design plan Additional Consideration 'No integration test
— frustration-signal audit instead'; feedback memory 'mate' signal."
```

**Consumer-tracing:** This task's output feeds the Finalization code-reviewer and supersedes the deleted DR-P4-INT-1 UAT entry.

**Falsifiability invariant:** The audit is falsifiable because (a) cc-search-chats queries are deterministic and re-runnable, (b) frustration signals are observable surface behaviours in the transcript, and (c) the joint human-review output is inspectable. The whole pipeline is re-runnable by a later reviewer with no privileged access to the lived authoring session.
<!-- END_TASK_4_5 -->

---

## Done when (phase-level)

- [ ] `phase_05_cross_ref_audit.py` exists in the plan directory and exits 0 when run (Task 1)
- [ ] `denubis-extending-claude` triad synchronised at 1.8.0: plugin.json, marketplace.json entry, CHANGELOG.md entry (Task 2)
- [ ] `denubis-plan-and-execute` triad synchronised at 2.31.0: plugin.json, marketplace.json entry, CHANGELOG.md entry (Task 3)
- [ ] Cross-reference audit re-runs clean after both bumps; commit-discipline checks pass (no --amend, no --no-verify, no forced operations) (Task 4)
- [ ] `phase_05_frustration_audit.md` exists with time-window, queries run, match list, joint human-review categorisations, fatigue-floor log (if match list > 30), calibration-check blinded recategorisation + disagreement count, and verdict (Task 4.5 — AC5.8; fatigue-floor + calibration added during Meta-M7 revision 2026-04-19)
- [ ] Commit history shows the full sync cleanly: Phase 1 (3+) + Phase 2 (5+) + Phase 2.5 (1+ per smell) + Phase 3 (5+) + Phase 4 (6+) + Phase 6 (6+ — Tasks 1-5 plus Task 6 illustrative-path rewrite from H1 revision 2026-04-19) + Phase 5 (5 — includes Task 4.5 frustration-signal audit from H3 revision) → **≥ 31 commits** (count reconciled during H6 revision 2026-04-19)
- [ ] All prior phases' DoD conditions verified (Task 4 Step 3)
- [ ] Phase 5 UAT entry appended to `uat-requirements.md` using gate-form template

**Not in scope for Phase 5:**
- Any content changes to skills (Phases 1-4, 6 handle all content)
- Handoff to executing-an-implementation-plan (Finalization task + Re-read + Critical peer review + Execution handoff come after Phase 5)
