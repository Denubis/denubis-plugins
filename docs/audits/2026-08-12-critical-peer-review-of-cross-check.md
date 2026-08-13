# Critical peer review of the 2026-08-12 cross-check — 2026-08-12

## Boundary

Reviewed subjects: `docs/audits/2026-08-12-cross-check-of-instruction-control-review.md`,
`docs/design-plans/2026-08-11-instruction-control-system.md`, the uncommitted working
tree above `dc89860`, and the stated goal for the next step: redo the skills and move in
the implementation-plan rewrite. Every claim below is either reproduced by a command run
on 2026-08-12 or marked as not independently verified. This document reproduces no human
instruction text; authority references are by manifest record ID and raw locator.

Working-tree state at review time: manifest SHA-256
`3ed5fdba196314f5a0aa7bd7a0a0055082fd63ea5af04279e3ba2bdcbdfe8c98`; full configured
pytest suite 1,566 passed; source verifier `ok: true`; baseline verifier `ok: false`.

## Claims that survive verification

- `TEST01` (Codex rollout line 9797) resolves through the manifest's own resolver to a
  genuine user record, and its content matches the boundary the two authoring skills cite
  it for: the prohibition on change-detection tests and the rubric-for-prose requirement.
- `REQUEST01` (line 13071) and `RETENTION01` (line 13297) resolve to genuine user
  records; the source verifier validates their bound text digests.
- `family:` metadata, the prose-derived route parser, and the universal caller test are
  gone. `docs/architecture/glossary.md` now documents the platform's actual invocation
  controls (`user-invocable`, `disable-model-invocation`) with a dated citation.
- The prose-test gate rework is real. `tests/test_test_quality.py` carries adversarial
  positive controls for the three shapes the audit showed the old detector missed
  (inline read, `all()`-nested comparison, regex probe), plus negative controls for
  program output and parsed structure, and the repository-wide check names its
  Python-test scope. `tests/test_always_on_instruction_ownership.py` was rewritten to
  parsed-structure and digest checks; the exact-heading locks are gone.
- The two deleted notes the audit pins are byte-recoverable at the cited assistant
  records (`a711c799…jsonl` lines 2439 and 4087; both are `Write` tool calls carrying
  the full note bodies).
- No tracked file outside `docs/audits/` references a retired note filename.
- The retirement of `feedback_commit-cadence.md` is sound: `denubis-git-commit:commit`
  splits by logical concern, not file count, which is the preference the note carried.
- The source `using-plan-and-execute` now owns task entry: goal and boundary statement,
  recursive decomposition of open-ended requests, and inspection of memory, feedback,
  and accepted decisions — the substance of `REQUEST01`.
- The research-note critique survives a direct spot-check: arXiv 2605.10039's
  within-session variable is the order of generated functions inside a single session
  (≈5.6% lower compliance odds per additional function), identified post-hoc, not
  conversational distance across turns. Retiring the "distance into session" claim was
  justified.
- `/home/brian/.codex/config.toml` carries an explicit `[history]`
  `persistence = "save-all"` with no byte cap, as the design requires.

## Confirmed defects

### 1. The mass note retirement has no resolving human record (Important)

The cleanup deleted every top-level file in the main repository's `.notes/` — a live,
gitignored, unversioned store — and the audit binds the whole follow-up to exactly two
records, `REQUEST01` and `RETENTION01`. Read at their sources, `REQUEST01` concerns
request-entry inspection and affirms that notes carry memory and feedback;
`RETENTION01` concerns Codex history expiry. Neither authorises emptying the store.
Under the design's own principle 6, a consequential action that relies on human
authority must point to a resolving record; this one points to records that do not
resolve to it. The dispositions may all be correct on the merits, but the authority
chain is a gap the system was built to reject. Resolution: the operator either
ratifies the cleanup now (a dated record referencing the disposition tables) or names
the record that authorised it.

Related observation: only two of the 48 deleted notes have per-note preservation pins.
The rest are recoverable only through Codex rollout archaeology, which the verified
`save-all` contract makes possible but the audit does not index.

### 2. The audit's final evidence no longer reproduces (Important)

The "Final source checks" section records manifest SHA-256 `e8b4bef0…`, baseline
verifier `ok: true` against unchanged live files, and 1,563 tests passed. Reproduced on
2026-08-12: the manifest hashes to `3ed5fdba…` (confirmed by both `sha256sum` and the
verifier), the baseline verifier returns `ok: false`, and the suite passes 1,566. The
audit's predecessor stated the rule this violates: recompute source and baseline
evidence after any further candidate edit or live settings change. The audit also
demands exactly this freezing discipline of transcript measurements (its defect 2) while
its own final section carries an unfrozen snapshot. Fix: recompute and restate the final
checks, or stamp them with the manifest digest and byte length they were computed
against so the staleness is self-announcing.

### 3. The settings candidate now changes the model outside its declared ownership (Important)

Live `~/.claude/settings.json` has `model: "opus"`; the candidate has
`model: "fable"`. The manifest's `settings_transition` declares ownership over enabled
plugins and permission entries only, so the verifier correctly reports "settings
transition changes values outside its declared ownership" and fails the baseline. The
audit's statement that the candidate preserves the live model is false against current
state. Deploying this candidate would silently switch the global default model to
Fable, which the operator's recorded model-tier ruling (this session's transcript, line
583) rejects on cost. Fix: rebuild the candidate from the current live baseline; if a
model change is ever intended, it needs its own authority record and a declared
transition entry.

### 4. The review rubric has no consumer (Medium)

`docs/review-rubrics/instruction-control.md` now owns the semantic expectations the
removed change-detector tests used to (badly) enforce. Nothing routes to it: no skill,
no workflow step, no finding aid — only the architecture context file and dated audits
mention it. `writing-skills` step 8 says "review the prose against its rubric" and
`testing-skills-with-subagents` says project-wide expectations belong in "a named
review rubric", but neither names this one, and the project `CLAUDE.md` finding aids do
not list it. By the design's own principle 10, text with no consumer is reference
material, not a control. Smallest fix: one finding-aid line in the project `CLAUDE.md`
and/or an explicit pointer where `requesting-code-review` or `writing-skills` tells the
reviewer what to apply.

### 5. "Integrated from a724452" claims more than the observed boundary (Medium)

`a724452` (the `impl-plan-decision-discipline` tip) carries a 1,303-line
`impl-plan-write`; HEAD carries 214 lines. What actually happened is distillation: the
decision filters (first authored in branch commit `e138cc0`) and the three UAT
distinctions (renamed Separation/Reduction/Disagreement) survive in the rewrite, and
`tests/test_skill_reference_integrity.py` is genuinely the branch's file with a 40-line
delta. But the branch's other committed mechanisms — the disclosed-oracle textual
anchor, mixed-signal SPLIT exception, per-phase self-audit, finalization existence gate,
provenance stamps — were dropped with no per-mechanism disposition. Most are ceremony
under the operator's empty-faff ruling and deserved to die; the point is that slice 6's
own instruction ("integrate as existing work … do not selectively recreate") makes the
current wording — "Final `impl-plan-write` … integrated from `a724452`" and the
definition-of-done's "integrated rather than duplicated" — an overclaim. Fix: a short
kept/renamed/dropped disposition for the branch's committed mechanisms, then state the
branch's own fate (merge, archive, or delete `impl-plan-decision-discipline`), which no
document currently does.

### 6. The no-live-write boundary sits beside performed live writes (Minor)

The audit's scope says no live write follows from it, yet the audit documents live
mutations performed during the same follow-up: the `/home/brian/.codex/config.toml`
edits (explicit `save-all`, inline-table conversion) and the `.notes/` deletions. The
sentence is technically about consequences, not contents, but a reader auditing
live-mutation discipline is misled. Fix: one paragraph listing the live actions
performed, each with its authority record — which also surfaces defect 1 honestly.

## Not independently verified

- The scoping critiques of arXiv 2607.19257, arXiv 2512.14982, and the Chroma report
  (audit defect 5) beyond the 2605.10039 spot-check above. They are consistent with the
  verified case and with the papers' abstracts as previously read, and nothing currently
  depends on them.
- The 39-of-48 versus 9-of-48 note disposition split. I verified zero dangling
  references and two preservation pins, not each note's merits.
- Ruff and shellcheck results as recorded.

## Disposition verification — 2026-08-12, later the same day

Every finding above now has a verified disposition in
`docs/audits/2026-08-12-cross-check-of-instruction-control-review.md`. Reproduced
against manifest `c8d348fdc7741cbaa19f59689fd2404a41ddf10d196c080e75c0f0d68a624a79`
(18,642 bytes):

1. Note-cleanup authority: **closed**. `NOTES01` (rollout line 11105) resolves through
   the manifest resolver to a genuine user record requesting a general notes cleanup,
   and is bound to the `project_note_cleanup` action alone.
2. Stale final evidence: **closed**. The rewritten final checks name their exact subject
   (bytes, SHA-256, timestamp) and reproduce: both verifiers return `ok: true` against
   the recorded manifest digest.
3. Settings model: **rejection accepted**. Live `settings.json` now matches the
   manifest's fable baseline exactly (6,703 bytes, `14f32d5a…`); the opus state this
   review observed was real but transient, the verifier was correctly red during it, and
   the baseline verifier is green again. The candidate preserves live; no model edit
   occurs. The flip-flop's cause remains unproven, which is acceptable because
   deployment re-verifies the baseline at transition time.
4. Rubric consumer: **closed**. The project `CLAUDE.md` finding aids now route reviews
   to `docs/review-rubrics/instruction-control.md`.
5. Implementation-plan overclaim: **closed**, beyond the requested fix. The audit states
   the integration claim was false in two ways, adds a per-mechanism reconciliation
   table (preserved / obviated / restored, including restored seam mapping, DFD
   reconciliation, ADR threshold, and UAT coverage), binds `PLAN01`–`PLAN04`, `DFD01`,
   and `UAT01`–`UAT02` as resolvable authority, addresses retained history by commit,
   and states the branch's fate: read-only evidence, retirement a separate authority.
6. Live-write disclosure: **closed**. The audit's boundary now discloses both classes of
   live write with their authority records.

The findings above remain as dated evidence of the states they observed; none is an
open defect against the current working tree.

## On the stated goal

The skill redo is in good shape. `writing-skills` and `testing-skills-with-subagents`
are grounded in a verified human record, separate mechanical checks from falsifiable
rubric entries, and kill the RED/GREEN prose theatre without abandoning verification.
The distilled `impl-plan-write` keeps the branch's decision discipline and the restored
UAT distinctions. Before declaring the implementation-plan rewrite "moved in", close
defect 5 (mechanism disposition plus branch fate). Before any deployment slice, close
defects 2 and 3 (recompute evidence, rebuild the settings candidate from current live).
Defect 1 needs an operator decision, not code.
