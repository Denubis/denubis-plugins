# Source audit — instruction-control simplification at `b33b22c`

## Boundary

This audit treats review statements as leads. A finding is retained only when the current
repository, the compared Git version, or a reproducible command demonstrates it. This
document makes no claim of human authority. The governing design and its resolvable
authority records are in
`docs/design-plans/2026-08-11-instruction-control-system.md`.

Reviewed surface:

- commit `b33b22c` and its parent;
- `deployment/instruction-control/foa4008439/`;
- current `denubis-plan-and-execute` workflow skills; and
- the uncommitted test-quality correction following `b33b22c`.

## Confirmed findings and current dispositions

### Deployment baselines were silently skipped

`deployment/instruction-control/verify_candidate.py` accepted only absolute baseline
paths. The manifest's `git:c6882d2:CLAUDE.md` binding was therefore ignored. Deployed
candidate records without `live_path` were ignored by the same control shape.

The working-tree correction resolves Git bindings, rejects unsupported relative
bindings, and rejects deployed candidates without a live target. Behavioral coverage is
in `tests/test_instruction_control_verifier.py`.

### The settings candidate had unrelated overwrites

The original candidate would have replaced the live model, output style, and date hook.
The working-tree candidate now preserves all three and binds the current live file as its
baseline. Because the candidate remains a complete replacement file, any later live
change invalidates it; the corrected verifier rejects that drift rather than silently
deploying over it. This source correction does not grant deployment authority.

### UAT collation lost useful discrimination

The parent version of
`plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md` distinguished:

- a human judgment from an automated check already covering the same claim;
- an integrated human experience from a sequence of automatable steps; and
- a genuinely judgment-dependent result from one every observer can settle from a
  disclosed deterministic boundary.

The `b33b22c` skill retained only the entry shape: what the human does, judges, and could
observe to falsify acceptance. The working tree now restores the three distinctions as a
short rubric and as review expectations. It does not restore the former duplicated
prose, stamps, or exact-wording locks.

### Internal skills have no explicit workflow caller

`requesting-code-review`, `exec-coherence-review`, and `exec-refactoring-rubric` declare
`user-invocable: false`, and no current `SKILL.md` names them as a next step. The
repository's own glossary defines non-user-invocable skills as procedures called by
other skills or agents, so the explicit caller graph is incomplete.

This did **not** demonstrate that Claude could never discover them from the skill
catalogue. Platform auto-selection and explicit workflow routing are different
mechanisms. The working tree adds explicit caller edges and a graph-derived test for
internal skills that declare a workflow family.

### Skill selection lost its continuous owner

The retired per-prompt reminder and removed SessionStart injection were both delivery
paths for skill selection. `using-plan-and-execute` still says to invoke the most
specific applicable skill, but that instruction is available only after the skill has
already been selected. The global candidate contains no equivalent task-entry invariant.

The global candidate now has one task-entry skill-selection invariant. It does not
recreate a per-turn hook, repeat the catalogue, or require ceremonial announcements.

### Exact-prose tests were change detectors

The post-`b33b22c` discipline suites asserted strings and headings from instruction files
that the same change authored. Those checks could preserve wording but could not detect
the workflow defects above.

The working-tree correction removes those tests, preserves independent structural and
configuration checks, adds an AST-based gate for raw wording assertions against source
Markdown, and places non-executable expectations in
`docs/review-rubrics/instruction-control.md`.

## Not established

- `user-invocable: false` alone does not establish that a skill is unreachable.
- Model agreement, a review verdict, or a passing exact-string assertion does not
  establish behavioral compliance.
- The source simplification is not deployable merely because repository tests pass. Live
  baseline and external-tool prerequisites are separate gates.

## Other reviewed leads

- The executor now stops before three attempts when a fix expands the failure surface or
  threatens recovery, and records deferred blockers in the current phase or existing
  project tracker.
- The unused `Phase Type` template field was removed. No current skill consumed it.
- Project finding aids now route search work to `using-code-search` and describe direct
  `.notes/` access without pointing to the intentionally uninstalled project-notes skill.
- Two records in the 2026-04-17 implementation plan falsely claimed the current executor
  blocks work on `main`; the inline Git-log guard is now stated as the actual owner.
- The `claude-sync` settings removal now has the separately resolvable `A2` authority
  record in the governing design and deployment manifest.
- Zero-entry UAT remains valid. A generic human touchpoint would not test a criterion and
  was not restored.
- Delegation remains optional. The executor surfaces verified delegated results that
  change the work, without reinstating mandatory delegation reports.

## Remaining decisions and dependencies

1. Keep `denubis-project-notes` installation in a separate candidate until cross-vendor
   exact source resolution is installed and verified. Core reminder retirement uses raw
   source locators and does not depend on PostgreSQL receipt correlation.
2. Recompute source and baseline evidence after any further candidate edit or live
   settings change. Deployment remains a separate human-authorised transition.

No deployment, installation, publication, or commit follows from this audit.
