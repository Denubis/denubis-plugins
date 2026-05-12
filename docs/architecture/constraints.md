# Quality Constraints

Measurable limits on the behaviour of `brian-ed3d-plugins` and the disciplines its plugins encode. Each constraint has a requirement and a verification method.

## Repository Integrity

| Constraint | Requirement | Verification |
|------------|-------------|-------------|
| Version sync | Every change to a plugin's `plugin.json` version must appear in the matching entry in `.claude-plugin/marketplace.json` AND a `CHANGELOG.md` entry must be added in the same commit. | Manual review at commit time; codified in `CLAUDE.md` (`b9bed28`). Automated test: see top-level `tests/` (referenced by `pyproject.toml`'s testpaths). |
| Per-plugin scope | Each plugin holds responsibility for one concern. Hook-only plugins ship only hooks; skill bundles ship only skills/agents/commands. Mixed plugins (notably `denubis-plan-and-execute`) are exceptions justified by their orchestration role. | Directory-listing review per release. |
| HALT on anomaly | When repo state appears mid-refactor, contradictory, or sideways — including mixed conventions, orphaned files, contradictions between docs, or reviewer findings at any level — halt and discuss rather than work around it. | Codified in `CLAUDE.md` (`b9bed28`). Surfaced in the `using-plan-and-execute` skill body and reinforced by reviewer agents at phase transitions. |
| Version bumps after the feature works | Do not bump `plugin.json` / `marketplace.json` / `CHANGELOG.md` on every WIP commit — bump once when the feature is verified working. | Per the user's standing feedback; observable via `git log -- <plugin>/.claude-plugin/plugin.json`. |
| Honouring prior architectural decisions | When the user signals "don't we already…" or "I thought we…", that signal is authoritative; research-agent outputs and prior session work are inputs, not conclusions. | Per the user's standing feedback; reinforced by `proleptic-challenger` at phase transitions. |

## Tool-Call Discipline (enforced by hooks)

| Constraint | Requirement | Verification |
|------------|-------------|-------------|
| Fork isolation | `gh` CLI commands targeting any repo other than the user's fork are denied. The allowed repo is set via `ALLOWED_GH_REPO` or inferred from `git remote get-url origin`. | `denubis-hook-gh-fork-guard`'s `gh-fork-guard.py` (`f62e8a6`) running under the `pretooluse-bash` dispatcher at priority 10. |
| Token economy | Commands matching the RTK rewrite catalogue (git, gh, file ops, JS/TS tooling, Docker, Python tooling, etc.) are transparently rewritten to `rtk <cmd>` to reduce token output. | `denubis-hook-rtk-rewrite`'s `pretooluse-bash.sh` (`c580ff0`) running under the dispatcher at priority 50. |
| Banned-pattern writes | File writes/edits that match patterns the user has banned (e2e JS injection, `create_all`, migration edits, debug statements, easy-mode shortcuts, spec weakening) are denied or warned at `PreToolUse:Write|Edit`. | `denubis-plan-and-execute/hooks/code-quality-guard.py` (`9bac7ed`) with 5s timeout. |
| Stop-time shortcut detection | When the assistant's last message contains a shortcut phrase (e.g. "let me try a different approach", "for simplicity"), the `Stop` hook blocks the turn so the user can interrogate before the model abandons an approach. | `denubis-hook-shortcut-detection`'s `shortcut-detector.py` (`22d2148`), keyed per-session via a lockfile under `/tmp/shortcut-detector/`. |

## Process Discipline (encoded by skills)

| Constraint | Requirement | Verification |
|------------|-------------|-------------|
| Brainstorming before coding | New features go through `denubis-plan-and-execute:starting-a-design-plan` (brainstorm → clarify → write → proleptic-challenge → architecture-update) before any code change. | Skill bodies; reinforced by `using-plan-and-execute` injected at every `SessionStart`. |
| TDD on implementation | Every feature/bugfix writes a test first (red-green-refactor); never delete failing tests to pass. | `coding-tdd` skill body; `task-implementor` agent enforces TDD. |
| Multi-agent review | Major work passes through `code-reviewer`, `coherence-reviewer`, `critical-peer-review`, and `test-analyst` agents before merge. | Skill `requesting-code-review` + the agent set in `denubis-plan-and-execute/agents/`. |
| Single bundled review pass | At most one fix-then-re-review cycle per phase before halting for user direction. | `requesting-code-review` skill body (per commit `9f7fab9` — *"bound code-review loop to one cycle, then HALT"*). |
| Plugin manifest description shape | Every plugin's `plugin.json` description is QA-tested for shape (length, content). | Top-level `tests/` directory test (per commit `8498518` — *"enforce and apply skill description shape"*). |

## Crash-Recovery Discipline (planned)

These constraints govern the `crash-recovery` plugin currently in design. They are not yet enforced by code. Each cites the design plan as its source of authority until implementation lands.

| Constraint | Requirement | Verification |
|------------|-------------|-------------|
| Deterministic classification | Given a fixed SQLite database state, `crash-recovery render` produces byte-identical markdown output. No LLM judgement participates in classification — every classification value is produced by a parametrised rule table. | Snapshot tests planned at `plugins/crash-recovery/scripts/crash_recovery/tests/` (`docs/design-plans/2026-05-08-crash-recovery.md`, `86cdfab`). |
| Idempotent scan | Repeated `crash-recovery scan` invocations against an unchanged filesystem state produce identical DB rows (`last_scanned` timestamp aside). `first_seen` is preserved across upserts; no duplicate `classification_history` rows accumulate. | Fixture-driven test in the scan module (`docs/design-plans/2026-05-08-crash-recovery.md`, `86cdfab`). |
| Boot-aware liveness | A liveness file whose `boot_id` does not match `/proc/sys/kernel/random/boot_id` is classified as a casualty regardless of whether its PID is currently alive. This prevents post-reboot PID-recycling false positives. | Manual UAT in Phase 8: reboot the machine, confirm `crash-recovery scan` classifies stale liveness files as `hard_crash` (`docs/design-plans/2026-05-08-crash-recovery.md`, `86cdfab`). |
| No auto-prune | `crash-recovery prune` only deletes rows when invoked with `--confirm` AND a three-condition guard holds: classification is `concluded` AND `user_notes IS NULL` AND `jsonl_path` is no longer on disk. Re-running triage never silently removes entries. | Per-condition test fixture; user's standing directive to never auto-prune (`docs/design-plans/2026-05-08-crash-recovery.md`, `86cdfab`). |
| Classifier version forward-compat | Each scan stamps the current `CLASSIFIER_VERSION` onto every row it touches. When the rule table changes, scan re-classifies version-stale rows before render or prune queries see them. Prune therefore always operates against rules currently in force. | Fixture: seed DB at version N-1, run scan with version N, assert all rows upgraded (`docs/design-plans/2026-05-08-crash-recovery.md`, `86cdfab`). |

## Constraint History

| Date | Constraint | Change | Reason |
|------|------------|--------|--------|
| 2026-05-11 | — | Initial bootstrap of `docs/architecture/constraints.md`. | Document the current state of repo conventions and hook-enforced disciplines. |
| 2026-05-12 | Crash-Recovery Discipline (planned) | Added prospective constraints for crash-recovery: deterministic classification, idempotent scan, boot-aware liveness, no auto-prune, classifier version forward-compat. | Track the design-plan-stage constraints so reviewers and implementers see the contract before code lands (`docs/design-plans/2026-05-08-crash-recovery.md`, `86cdfab`). |
