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
