# Phase 2: Update Marketplace and Changelog

## Overview

Register the new plugin in the marketplace and add changelog entry.

## Tasks

### Task 2A: Update marketplace.json

Add the new plugin entry to `.claude-plugin/marketplace.json`:

```json
{
  "name": "denubis-hook-shortcut-detection",
  "version": "1.0.0",
  "description": "Stop hook that detects shortcut phrases and blocks until user approves approach changes.",
  "path": "plugins/denubis-hook-shortcut-detection/hooks"
}
```

**Verification:** File is valid JSON and contains the new entry.

### Task 2B: Update CHANGELOG.md

Add entry at the top (after `# Changelog` heading):

```markdown
## [denubis-hook-shortcut-detection] 1.0.0

Initial release of shortcut detection hook.

**New:**
- Stop hook that reads Claude's transcript for shortcut phrases
- Detects high-signal phrases: "let me try a different approach", "simpler approach", "for simplicity", etc.
- Detects medium-signal phrases: "instead of", "easier to", "more efficient", etc.
- Blocks response and requires Claude to explain the problem, what was tried, and ask for explicit approval
```

**Verification:** CHANGELOG.md has the new entry at the top.

## Phase Completion Criteria

- [ ] marketplace.json updated with new plugin
- [ ] CHANGELOG.md has new version entry
- [ ] Both files are syntactically valid
