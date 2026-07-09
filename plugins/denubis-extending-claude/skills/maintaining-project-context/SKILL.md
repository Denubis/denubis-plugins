---
name: maintaining-project-context
description: Use when completing development phases to identify and update stale CLAUDE.md or AGENTS.md files against code changes
user-invocable: false
---

# Maintaining Project Context

**REQUIRED SUB-SKILL:** Use denubis-extending-claude:writing-claude-md-files for all context file creation and updates.

## Core Principle

Context files (CLAUDE.md or AGENTS.md) document contracts and architectural intent. When code changes contracts, the documentation must update. Stale documentation is worse than no documentation.

**Trigger:** End of development phase, branch completion, or any work that changed contracts, APIs, or domain structure.

## Format Detection (MANDATORY FIRST STEP)

Before any updates, detect what format this repository uses:

```bash
# Check for AGENTS.md at root
ls -la AGENTS.md 2>/dev/null

# Check for CLAUDE.md at root
ls -la CLAUDE.md 2>/dev/null
```

| Root AGENTS.md? | Format | Action |
|-----------------|--------|--------|
| Yes | AGENTS.md-canonical | Update AGENTS.md files, create companion CLAUDE.md |
| No | CLAUDE.md-canonical | Update CLAUDE.md files directly |

**Key principle:** We use OUR format structure (Purpose, Contracts, Dependencies, Invariants, etc.) regardless of filename. AGENTS.md is just for cross-platform AI agent compatibility.

### AGENTS.md-Canonical Repos

When the repo uses AGENTS.md:

1. **Read AGENTS.md first** before making any updates
2. **Write content to AGENTS.md** using our standard structure
3. **Create companion CLAUDE.md** next to each AGENTS.md with exactly this content:

```markdown
Read @./AGENTS.md and treat its contents as if they were in CLAUDE.md
```

## When to Update Context Files

| Change Type | Update Required? | What to Update |
|-------------|------------------|----------------|
| New domain/module | Yes | Create domain context file |
| API/interface change | Yes | Contracts section |
| Architectural decision | Yes | Key Decisions section |
| Invariant change | Yes | Invariants section |
| Dependency change | Yes | Dependencies section |
| Bug fix (no contract change) | No | - |
| Refactor (same behavior) | No | - |
| Test additions | No | - |

## The Process

### Step 1: Identify What Changed

Diff against the base (branch start or phase start):

```bash
# Get changed files
git diff --name-only <base-sha> HEAD

# Get detailed changes
git diff <base-sha> HEAD --stat
```

Categorize changes:
- **Structural:** New directories, moved files
- **Contract:** Changed exports, interfaces, public APIs
- **Behavioral:** Changed invariants, guarantees
- **Internal:** Implementation details only

### Step 2: Map Changes to Context Files

For each significant change, determine which context file should document it:

| Change Location | Context File Location |
|-----------------|----------------------|
| Project-wide pattern | Root context file |
| New domain | `<domain>/` context file (create) |
| Existing domain contract | `<domain>/` context file (update) |
| Cross-domain dependency | Both affected domains |

**Hierarchy rule:** Information belongs at the lowest level where it applies. Domain-specific contracts go in domain files, not root.

**For AGENTS.md-canonical repos:** When creating new domain context files, create both `AGENTS.md` (with content) and `CLAUDE.md` (companion pointer).

### Step 3: Verify Contracts Still Hold

For each affected context file, verify:

1. **Contracts section:** Do exposes/guarantees/expects match current code?
2. **Dependencies section:** Are uses/used-by/boundary accurate?
3. **Invariants section:** Are all invariants still enforced?
4. **Key Decisions section:** Any new decisions to document?

```bash
# Find domain's public exports
grep -r "export" <domain>/index.ts

# Find domain's imports (dependencies)
grep -r "from '\.\." <domain>/
```

### Step 4: Update or Create Context Files

**For updates:**
1. Read existing file first (especially for AGENTS.md)
2. Update freshness date via `date +%Y-%m-%d`
3. Update affected sections
4. Remove stale content
5. Verify under token budget (<100 lines for domain files)

**For new domains (CLAUDE.md-canonical repos):**
1. Create `<domain>/CLAUDE.md` using template from writing-claude-md-files
2. Document purpose, contracts, dependencies, invariants
3. Set freshness date

**For new domains (AGENTS.md-canonical repos):**
1. Create `<domain>/AGENTS.md` using template from writing-claude-md-files
2. Document purpose, contracts, dependencies, invariants
3. Set freshness date
4. Create companion `<domain>/CLAUDE.md`:
   ```markdown
   Read @./AGENTS.md and treat its contents as if they were in CLAUDE.md
   ```

### Step 5: Commit Documentation Updates

```bash
git add <affected CLAUDE.md files>
git commit -m "docs: update project context for <branch-name>"
```

## Decision Tree

```
Has code changed?
├─ No → Skip (nothing to update)
└─ Yes → Detect format first (AGENTS.md at root?)
    │
    └─ What changed?
        ├─ Only tests/internal details → Skip
        └─ Contracts/APIs/structure → Continue
            │
            ├─ New domain created?
            │   ├─ AGENTS.md repo → Create AGENTS.md + companion CLAUDE.md
            │   └─ CLAUDE.md repo → Create CLAUDE.md
            │
            ├─ Existing domain changed?
            │   └─ Update domain context file (read first!)
            │
            └─ Project-wide pattern changed?
                └─ Update root context file
```

## Quick Reference

**Always update when:**
- New public exports added
- Interface signatures changed
- Invariants added/removed
- Dependencies changed
- Architectural decisions made

**Never update for:**
- Internal refactoring
- Bug fixes that don't change contracts
- Test file changes
- Comment/documentation-only changes

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Updating for every change | Only update for contract changes |
| Forgetting freshness date | Always use `date +%Y-%m-%d` |
| Documenting implementation | Document contracts and intent |
| Putting domain info in root | Use domain context files for domain contracts |
| Skipping verification | Read the code, confirm contracts hold |
| Skipping format detection | Always check for AGENTS.md first |
| Writing AGENTS.md without reading | Always read existing content before updating |
| Forgetting companion CLAUDE.md | AGENTS.md repos need both files |

## Test Pseudocode Maintenance

After implementation, verify that test files exist for changed code and that test descriptions match current behaviour.

### Process

1. Identify changed source files from diff
2. For each changed file with public interfaces, check for corresponding test file
3. Flag missing test coverage as a finding (do not write tests — that's implementation work)
4. For existing tests, verify test names/descriptions still match what the code does

### When to Skip

- Changes to test files only (already covered)
- Internal refactoring with no public interface changes
- Configuration-only changes

## Permissions Cleanup

After implementation, check that `settings.json` permissions still match actual tool usage.

### Process

1. Read project's `.claude/settings.json` (or `.claude/settings.local.json`)
2. For each `allow` entry, check whether the permitted command is still used in the project
3. Flag unused permissions as candidates for removal
4. Present findings to human — do not remove permissions without approval

### When to Skip

- No settings files exist
- Changes didn't affect tool usage patterns

## Dependency Rationale

Dependency rationale maintenance is **not** handled by this skill. It requires structured Popper/Lakatos/Haraway analysis via `restate-our-assumptions`, which warrants subagent dispatch. The project-claude-librarian agent dispatches a subagent for this separately.

## Integration Points

**Called by:**
- **project-claude-librarian agent** - Uses this skill to coordinate updates
- **executing-an-implementation-plan** (Stage 1, step 4a "Librarian updates") - After all tasks complete

**Uses:**
- **writing-claude-md-files** - For actual context file creation/updates (works for both CLAUDE.md and AGENTS.md)
- **restate-our-assumptions** - For dependency rationale (dispatched separately by librarian agent)
