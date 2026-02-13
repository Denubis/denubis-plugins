---
name: controlled-dependency-upgrade
description: Use when upgrading Python dependencies, auditing unused packages, or reviewing dependency health - methodical one-at-a-time upgrade cycle with changelog review, falsifiable justification audit, and per-package commits using uv
user-invocable: true
---

# Controlled Dependency Upgrade

## Overview

Upgrade dependencies one at a time, reading the changelog before each. Never upgrade blind. Never batch. Every package gets its own test cycle and its own commit.

## Workflow Status Line

Update the breadcrumb at transitions. If the state script is not installed, skip silently.

All commands prefixed with: `~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow-state-wrapper.sh`

| Transition | `--skill` | `--context` |
|------------|-----------|-------------|
| Entry | `controlled-dependency-upgrade` | `auditing dependencies` |
| Upgrading specific package | | `upgrading: <package-name>` |
| Unjustified package removal approval | | `approve removal: <package>` |
| Missing changelog — proceed? | | `no changelog for <package> — proceed?` |
| Between packages (Claude working) | | `""` |

## When to Use

- Routine dependency maintenance
- Security advisories requiring package updates
- Before major releases (clean up dependency health)
- When `uv pip list --outdated` shows stale packages

## Prerequisites

**CLAUDE.md must document the project's test command.** If it doesn't, stop and ask the user to add it before proceeding. The skill cannot verify upgrades without a documented test suite.

Read CLAUDE.md and extract the test command before starting any work.

## Workflow

The upgrade process has two phases: **Audit** (are all packages justified?) then **Upgrade** (one at a time, tested, committed).

### Phase 1: Package Audit

Run before any upgrades. The audit is not optional, even under time pressure — upgrading a package you're about to remove wastes more time than auditing costs. If time is short, do fewer upgrades after the audit rather than skipping the audit to do more upgrades.

#### Step 1: Inventory

```bash
uv pip list
```

Cross-reference against `pyproject.toml` to separate:
- **Direct dependencies**: listed in `[project.dependencies]`, `[project.optional-dependencies]`, or `[dependency-groups]`
- **Transitive dependencies**: everything else (pulled in by direct deps)

#### Step 2: Justify Each Direct Dependency

**First, check for `docs/dependency-rationale.md`.** If it exists, read it — previous design plans may have already documented why each package exists. Use existing rationale as your starting hypothesis, then try to falsify it against the current codebase state (rationale may be stale if code has changed since the design was written).

For each direct dependency, produce a falsifiable claim:

| Package | Claim | Evidence | Falsification Attempt | Verdict |
|---------|-------|----------|----------------------|---------|
| requests | "Used for HTTP calls to external APIs" | `src/api/client.py:12`, `src/fetcher.py:34` | Searched for `import requests` and `from requests` — found in 2 files, both in active code paths | Justified |
| boto3 | "Used for S3 uploads" | `tests/test_old_upload.py:8` | Only import is in a test file. That test file tests `OldUploader` which was removed in commit abc123. | **Unjustified — remove** |

**How to assess:**
1. Search for imports: `import <pkg>` and `from <pkg>` across all Python files
2. Search for CLI usage: check `Makefile`, `pyproject.toml [tool.*]` sections, CI configs, scripts
3. Search for plugin/extension loading: check config files, entry points
4. For test-only imports: verify the tests exercise live code, not removed functionality
5. For type stubs (`types-*`): verify the parent package is still used

**Falsification means actively trying to break the claim.** Follow the evidence chain:
- "It's imported" → Where? → Is that code reachable? → Is it tested? → Do the tests pass?
- "It's a CLI tool" → Where is it invoked? → Is that invocation still in use?
- "It's a pytest plugin" → Is it in `conftest.py` or `pyproject.toml [tool.pytest]`? → Do tests actually use its features?

#### Step 3: Present Findings

Create a task list of unjustified packages. For each, present:
- The failed justification chain
- Proposed action (remove from pyproject.toml)
- Any risks of removal

**Update `docs/dependency-rationale.md`** with audit findings:
- For justified packages without an existing entry: add one (with today's date and evidence found)
- For justified packages with a stale entry: update the claim/evidence and add `**Last reviewed:** YYYY-MM-DD`
- For unjustified packages: note removal in the entry (or remove the entry entirely after the package is removed)

This keeps the rationale file current. Future audits and the restate-our-assumptions skill depend on it.

**Wait for user approval before removing anything.** Then remove unjustified packages, run the test suite, and commit:

```bash
# After user approves removals
uv remove <package>
uv sync
# Run test suite from CLAUDE.md
git add pyproject.toml uv.lock docs/dependency-rationale.md
git commit -m "chore: remove unused dependency <package>

Justification chain failed: <brief explanation>"
```

### Phase 2: Controlled Upgrades

#### Step 1: Identify Outdated Packages

```bash
uv pip list --outdated
```

Filter to **direct dependencies only**. Transitive dependencies get upgraded through their parents — never upgrade a transitive dependency directly.

#### Step 2: Sort by Risk

Primary sort: **semver bump size** (smallest first)
- Patch bumps (1.2.3 → 1.2.4): first
- Minor bumps (1.2.0 → 1.3.0): second
- Major bumps (1.0.0 → 2.0.0): last

Within each semver tier, order is not critical. Use TaskCreate to track every package individually — one task per package, updated as you go:

```
- [ ] package-a (1.2.3 → 1.2.4) — patch
- [ ] package-b (1.0.0 → 1.1.0) — minor
- [ ] package-c (2.0.0 → 3.0.0) — major
```

#### Step 3: Per-Package Upgrade Loop

For **each** package, in order:

**3a. Read the changelog.**

```bash
gh release list -R <owner>/<repo> --limit 10
gh release view <tag> -R <owner>/<repo>
```

If the package isn't on GitHub or has no releases, check PyPI release history or the package's CHANGELOG/HISTORY file. No blind upgrades — if you can't find a changelog, tell the user and ask whether to proceed.

**3b. Assess impact against our code.**

Cross-reference changelog entries with our actual usage:
- Use `grep`/`ast-grep` to find where we use affected APIs
- Check if deprecated features are ones we call
- Check if bug fixes address issues we've encountered

**3c. Classify the upgrade.**

| Classification | Meaning | Action |
|---------------|---------|--------|
| No-op | Changes are internal/build-only, nothing we use | Upgrade, minimal review |
| Bugfix | Fixes something that may affect us | Upgrade, note the fix |
| New feature | Adds capability we might want | Upgrade, document if relevant |
| Breaking change | Removes/changes API we use | Upgrade requires code changes — assess effort, discuss with user |

**3d. Upgrade.**

```bash
uv lock --upgrade-package <package> && uv sync
```

**Do not use `uv add`.** `uv lock --upgrade-package` upgrades within existing constraints. `uv add` modifies `pyproject.toml` version specifiers, which is a separate decision.

**3e. Run the test suite.**

Run the test command documented in CLAUDE.md. The full suite, not a subset.

**3f. Handle the result.**

If tests **pass**:
```bash
git add uv.lock docs/dependency-rationale.md
git commit -m "chore: upgrade <package> <old> → <new>

<classification>: <one-line summary of what changed>
Files using this package: <list>
Changelog reviewed: <link or tag>"
```

If tests **fail**:
1. Investigate the failure — is it a genuine breaking change or a flaky test?
2. If fixable: fix the code, include the fix in the same commit
3. If not fixable or too risky: revert and note it

```bash
uv lock --upgrade-package <package>@<old-version> && uv sync
```

Mark the package as "reverted" in the task list with the reason.

**3g. Note documentation updates.**

If the changelog mentions:
- New capabilities relevant to us → note for later
- Deprecation warnings for APIs we use → create a follow-up task
- Behaviour changes → verify our code handles the new behaviour

#### Step 4: Summary

After all packages are processed, report:
- Packages upgraded successfully (with classifications)
- Packages reverted (with reasons)
- Packages removed in audit (with failed justifications)
- Follow-up tasks (deprecation migrations, new features to evaluate)

## Key Principles

| Principle | Rationale |
|-----------|-----------|
| One package, one test cycle | Isolates failures. If something breaks, you know exactly what caused it. |
| Read the changelog first | Changelogs tell you the real risk. Semver is a rough signal; the changelog is the truth. |
| Transitive deps via parent only | Directly upgrading transitive deps creates version conflicts and breaks the dependency resolver's contract. |
| Test command from CLAUDE.md | Projects without documented test suites cannot verify upgrades. Fix the docs first. |
| Falsifiable audit claims | "We use X" must be backed by evidence and actively challenged. Dead packages accumulate silently. |
| One commit per package | Each upgrade is independently revertable. `git bisect` works. History is clear. |

## Red Flags — STOP

If you find yourself reasoning any of these, you're rationalising:
- "These three patches are safe, I'll batch them" → No. One at a time.
- "I know what this package does, I don't need the changelog" → Read it anyway.
- "The tests are slow, I'll run them at the end" → Run them every time.
- "This transitive dep is outdated, I'll just bump it directly" → Upgrade the parent.
- "I'll check for unused packages later" → Audit first. Don't upgrade dead weight.
- "We're short on time, skip the audit" → Do fewer upgrades instead. The audit is faster than upgrading packages you'll remove.
- "CLAUDE.md doesn't have a test command but I know it's pytest" → Stop. Document it first.
