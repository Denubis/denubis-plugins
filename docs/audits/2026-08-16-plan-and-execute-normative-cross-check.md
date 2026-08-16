# Plan-and-execute normative cross-check — 2026-08-16

## Question

Does the living `denubis-plan-and-execute` plugin implement the project's current
normative rules, or does it preserve older examples and workflow architecture that should
not be copied into the Codex marketplace?

## Evidence inspected

The cross-check read:

- all 34 current `SKILL.md` files;
- all 10 bundled agent definitions;
- the plugin README, architecture context, coding-effectively design note, hooks, and
  active support files;
- all repository tests that inspect skills, instructions, manifests, and hook behavior;
- the 2026-07-02 engagement audit and the untracked 2026-08-13 refactor critique;
- the recent instruction-simplification history; and
- the current Codex mirror where it bears on provider transport.

Searches located provider terms, phase vocabulary, support-file references, and tests
that read prose. A search result was not treated as a finding until the surrounding
instruction and its consumer were read. Support-file reachability was checked across the
complete active skill and agent tree; known referenced files provided the positive
control.

The isolated worktree baseline is green:

```text
uv sync --all-packages
uv run pytest -q
1579 passed in 6.41s
```

Current library claims were checked against current documentation where the audit found
version-sensitive assertions:

- [Python 3.14 template strings](https://docs.python.org/3.14/library/string.templatelib.html)
- [Hypothesis pytest fixture limitations](https://hypothesis.readthedocs.io/en/latest/reference/api.html)
- [PostgreSQL partial indexes](https://www.postgresql.org/docs/current/indexes-partial.html)
- [PostgreSQL constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)
- [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)

## Conclusion

The August simplification substantially improved the orchestration and review skills, but
the plugin is not yet a safe canonical payload for Codex. The newer normative rules are
better than every existing example. Several living skills still preserve older phase
architecture, unsafe universal coding policy, disclosed-answer “tests,” and unused support
material. Packaging the tree unchanged would make those defects harder to remove.

The correction should preserve the evidence disciplines that survived simplification,
then remove or replace the remaining ceremony and invalid technical claims before adding
Codex manifests.

## Findings requiring correction

### 1. Planning still makes one file architecture compulsory

`impl-plan-write`, `starting-an-implementation-plan`, and
`executing-an-implementation-plan` require every design to become numbered phase files,
`flow-boundaries.md`, `test-requirements.md`, and `uat-requirements.md`. Task markers and
phase headers are mandatory even when the work has one outcome.

This is not just presentation. It changes the work:

- decomposition follows delivery chronology instead of protected decisions;
- a boundary-flow artifact is always created, including to say that it does not apply;
- the executor closes and reviews phases as workflow state;
- UAT entries attach to phases instead of the finished implications; and
- `starting-an-implementation-plan` still requires a “phase type” that the plan writer no
  longer produces.

The useful obligations are acceptance ownership, dependency order, current consumers,
positive verification signals, and durable resumability. They do not require this fixed
file set. Implementation plans should contain the smallest set of coherent outcomes the
design needs, with tests and human judgment next to the claims they own.

### 2. Execution contradicts the agreed commit and UAT lifecycle

The current execution skill says a plan does not authorise commits and performs UAT while
closing individual phases. The accepted lifecycle says:

- executing the approved plan authorises private checkpoint commits;
- fix and review rounds fold into their owning outcomes;
- agents finish all mechanical and independent sanity checks before human UAT;
- UAT touches the implications of the finished result; and
- final history normalisation occurs only after accepted UAT and must preserve the
  accepted tree exactly.

This contract belongs in plan writing, execution, branch finishing, the commit skill, and
the architecture description. It should not be left as a separate design note that the
actual executor contradicts.

### 3. The shipped skill evaluations disclose the answers

The four files beside `systematic-debugging` are not tests of method:

- `test-academic.md` asks the actor to quote rules from the skill itself;
- the pressure prompts state the required process before offering leading A/B/C choices;
- no separate evaluator owns the expected consequences or failure criteria; and
- `CREATION-LOG.md` declares that all tests passed without a reproducible invocation,
  captured output, or hidden oracle.

They are also unreachable from the current skill. Retire them from the runtime package.
New methodological evaluations must give an actor a realistic task and the skill under
test while keeping the evaluator's answer key in another file. The evaluator observes
actions and consequences rather than chosen wording.

`testing-skills-with-subagents` partially fixes the old approach by using rubrics, but it
still conflates two roles: a reviewer judging prose and an actor attempting to follow a
method. It must explicitly define the actor/evaluator split and prohibit showing the
oracle to the actor.

### 4. `coding-python-idioms` contains unsafe universal policy

The skill assumes Python 3.14, mandates `uv run`, prefers particular optional libraries,
allows a scheduled `# type: ignore`, and presents style preferences as language rules.
This conflicts with project-first adaptation and the hard prohibition on suppressing type
errors.

Its t-string guidance is dangerous. A t-string yields a `Template` whose interpolations
an application-specific processor can inspect; it does not parameterise SQL, escape HTML,
or quote shell arguments by itself. A driver must explicitly support and safely process
that template. Parameterised driver APIs and argument-vector process APIs remain the safe
default.

The skill should become a concise project-version and configured-tool decision procedure.
Version- or library-specific examples belong in current references only when the active
project uses them.

### 5. `howto-develop-with-postgres` mixes defects with house taste

The 614-line skill hard-codes a database architecture rather than teaching the agent to
derive one from current invariants and workloads. Examples of substantive problems:

- a conditional `UNIQUE` example uses constraint syntax PostgreSQL does not support;
  conditional uniqueness is implemented with a partial unique index;
- the `TX_` prefix is imposed as a universal API convention and the example's optional
  session construction obscures ownership and cleanup;
- “single operation needs no transaction” confuses statement atomicity with transaction
  boundaries;
- ULID-as-UUID is required by default and described as preventing enumeration attacks,
  although identifier opacity is not an authorization boundary;
- every table is told to have an ID and timestamps despite the skill's own reference and
  join-table exceptions;
- every foreign-key, `WHERE`, `JOIN`, and `ORDER BY` column is told to receive an index,
  ignoring workload, selectivity, write cost, and index order; and
- Serializable is prescribed categorically for money and inventory without making
  whole-transaction retry part of the contract.

PostgreSQL does not automatically index referencing foreign-key columns and often benefits
from those indexes, but the decision still depends on deletes, updates, joins, workload,
and existing composite indexes. Serializable detects anomalies by aborting transactions;
the application must retry the complete operation.

Replace the skill with a bounded schema/query/transaction review procedure. Put durable
project-specific conventions in the project that owns them, not in a universal PostgreSQL
skill.

### 6. `coding-good-tests` and `coding-property-testing` are tutorials, not selectors

`coding-good-tests` embeds a “standard” pytest command requiring optional plugins even
though project-native commands own invocation. It says both “never mock internal code”
and “always mock external boundaries,” then recommends wrappers and real integration
components. Filesystems, databases, clocks, and third-party clients require decisions
based on the boundary and failure being tested, not ownership slogans.

The existing rejection of prose change detectors is correct and should remain. It needs
the actor/oracle methodological rule added.

`coding-property-testing` makes `@example` universal, supplies ad hoc development/CI/nightly
settings, and demonstrates a function-scoped database fixture under `@given` without
warning that pytest creates that fixture once for the whole Hypothesis test rather than
once per generated example. Hypothesis reports that pattern through a health check because
state can leak between examples.

Keep the property-selection rules and strategy principles. Move optional API examples to
a current reference or remove them when ordinary Hypothesis documentation is the better
owner.

### 7. Ambient SIMD detection is an unrelated announcement policy

`coding-effectively` now requires every coding session to announce a SIMD-shaped candidate
when a loop matches structural properties, even before profiling establishes value. This
is a narrow optimization heuristic embedded in the universal coding entry skill and is
likely to become the repeated announcement tic the normative rules reject.

SIMD investigation belongs in an explicitly requested performance/profiling procedure or
a project whose workload demonstrates the need. It should not remain ambient routing.

### 8. Architecture maintenance duplicates procedure and over-specifies provenance

`maintain-architecture` invokes `architecture-update`, and both repeat the same
implemented-first mapping, predicted-flow comparison, exact-source requirements, and
living-document rules. The split no longer protects a distinct authority or side-effect
boundary because the main agent performs and verifies both operations.

The insistence that every human-derived decision carry a provider-specific exact message
locator and resolver also appears across design, UAT, architecture, and challenge skills.
Durable rationale and attributable evidence matter, but a private transcript offset is not
a portable semantic contract and can become impossible after provider migration. Exact
locators remain appropriate when a named decision or audit depends on them; they should
not be mandatory metadata for every ordinary instruction.

Merge the architecture workflow around current implemented truth, claim ownership, source
evidence, and durable ADRs. Keep diagrams and tables only when they clarify relationships.

### 9. The code-quality hook is a phrase detector with the wrong Codex boundary

`code-quality-guard.py` scans new text for selected word and call patterns. Several warnings
are heuristics whose success condition is simply that a phrase was absent. Its Claude
`Write`/`Edit` input extraction does not observe Codex `apply_patch` input. Porting it would
preserve a change detector and still fail to guard Codex edits.

Retire it rather than translating it. Keep real project constraints in linters, types,
tests, database constraints, or focused runtime hooks that independently observe the
protected effect.

### 10. Twenty-two runtime support artifacts have no active consumer

The full skill/agent reference scan found no active inbound reference for:

- seven architecture templates;
- five critical-review checklists;
- four ast-grep smell rules;
- `make-pr/testing-guidance-format.md`; and
- the five systematic-debugging creation/test artifacts.

The current design and historical implementation plans mention some filenames, but no
living skill or agent loads them. The refactoring rule files also have no executable test
or dispatcher. Remove them from the runtime tree unless a current consumer is introduced
for a demonstrated reason.

### 11. Agent files duplicate semantic procedures

The bundled reviewer, challenger, implementor, and fixer agents are now concise, but many
repeat the corresponding skill's method. This creates a second semantic owner inside the
same plugin before Codex is even considered.

Keep provider-specific agent files as thin role and authority adapters. The canonical
skill or shared behavioral contract should own review, debugging, TDD, and evidence rules.
Codex metadata and worker briefs should adapt transport without copying the procedure
again.

### 12. Living descriptions are already stale

The README and architecture still state that the human separately owns every commit,
describe per-phase execution and UAT, advertise the code-quality hook, and bind current
components to historical commit IDs. The architecture manifest version is also behind the
plugin manifest.

Living documentation should describe the corrected runtime after implementation. Commit
IDs and correction narratives belong in history or a bounded audit, not in current
component descriptions.

## Material worth preserving

The cross-check does not support a wholesale rewrite. These current mechanisms are
compact, coherent, and aligned with the normative rules:

- `coding-tdd`, `coding-verify`, `coding-fcis`, and `defense-in-depth`;
- the causal evidence loop in `systematic-debugging` (without its stale test artifacts);
- `requesting-code-review`, `critical-peer-review`, `proleptic-challenge`, and
  `restate-our-assumptions` as bounded falsification procedures;
- `exec-refactoring-rubric` after its orphaned structural-rule files are removed;
- `using-code-search` and its two referenced measured-behavior references;
- `using-git-worktrees`, `make-pr`, and `merge-to-main` as explicit side-effect owners;
- the core UAT distinction between automatable facts and irreducible human judgment; and
- direct execution with optional delegation, source verification, positive controls, and
  preservation of pre-existing work.

`exec-coherence-review` may remain as a targeted design-conformance tool, but it should not
depend on mandatory phase or predicted-flow artifacts. `exec-session-naming` may remain an
explicit convenience; the design, planning, execution, and debugging skills should not
all require it as a ritual first step.

## Proposed correction outcomes

### Outcome 1: lifecycle and methodology

- Replace fixed phase artifacts with coherent outcome planning.
- Implement the agreed checkpoint, final-UAT, and post-UAT normalization lifecycle.
- Put actor instructions and hidden evaluator oracles in separate files.
- Retire the disclosed-answer systematic-debugging artifacts.
- Update `testing-skills-with-subagents` and `coding-good-tests` to share the same test
  development rule.

### Outcome 2: coding and architecture truth

- Replace the Python, PostgreSQL, general testing, and property-testing tutorials with
  concise decision procedures and current references where necessary.
- Remove ambient SIMD announcements and the textual code-quality hook.
- Consolidate architecture maintenance and remove unreachable support artifacts.
- Thin agent definitions to provider roles rather than duplicated methods.
- Bring README and living architecture to current truth.

### Outcome 3: Codex delivery

- Add intentional `agents/openai.yaml` metadata and implicit-invocation policy.
- Add Codex manifests, hook adapters only where behavior is valid, and the repository
  marketplace.
- Verify installed behavior from fresh Codex sessions.
- Obtain implication-level human UAT.
- Only after accepted UAT, normalize the private history and retire the duplicated shared
  skill mirror in `brian-ed3d-plugins-codex`.

These are outcome boundaries, not a target commit count. Private checkpoints inside them
may be frequent and will be folded after UAT.

## Pre-change methodological observations

The evaluation cases live under `tests/skill-evals/plan-and-execute/`. In each case the
acting brief and evaluator oracle are separate; the acting agent received only its brief,
fresh fixture, and named current skills.

### Outcome planning

The actor converted one independently usable greeting option into a mandatory directory
containing `phase_01.md`, `flow-boundaries.md`, `test-requirements.md`, and
`uat-requirements.md`. The outcome itself stayed coherent, but three artifacts had no
consumer outside the fixed plan format. This fails the oracle's chronology and compulsory
paperwork boundaries while providing the expected positive control: the baseline test ran
and the fixture remained unimplemented.

### Methodological test design

The actor correctly rejected phrase matching and included a permitted deletion control,
but wrote one `review-rubric.md` containing both each scenario and its expected
consequence. It provided no separate actor briefs and hidden evaluator oracle, so a future
acting agent would be shown the answers it was meant to discover. This fails the
information-separation boundary even though its filesystem observations would otherwise
be consequential.

### Checkpoint and UAT lifecycle

The pre-change executor implemented the complete fixture and produced two passing tests,
but left every owned file uncommitted after the direct instruction to execute the approved
plan. That is the predicted consequence of the old rule that a plan cannot grant commit
authority. The run did not normalize history, so the pre-UAT rewrite guard remained
intact. The actor report and full artifact inspection are recorded with the post-change
rerun results.

## Post-change methodological observations

### Outcome planning

The first rerun produced one outcome file rather than a mandatory phase directory, but
still proposed an exact README phrase search as a documentation check. The evaluator—not
the actor—caught that as another change detector. After the planning method was corrected
to require a real documentation consumer or bounded semantic inspection, a fresh actor
again produced one outcome file and verified the README by executing its Python example
and inspecting the affected section in context. The baseline remained red and no
implementation was performed.

### Methodological test design

The rerun produced two actor-only assessments and a separate evaluator oracle. The actor
files described observable filesystem procedures without disclosing their expected
answers. The oracle distinguished an authorized deletion from a source-tree non-match and
required a positive control before treating absence as evidence. This satisfies both the
information boundary and the consequential-observation boundary.

### Checkpoint and UAT lifecycle

The rerun started from commit `7e271ba`, observed two tests with the uppercase case red,
implemented the complete outcome, and created private checkpoint `2eac346`. The resulting
tree was `1d51adb`; both tests and direct default/uppercase sanity calls passed, an invalid
positional call raised `TypeError`, `git diff --check` was clean, and the branch had no
tracked changes. The actor reported an untracked Python cache instead of hiding it.

No history normalization occurred. The final gate asked a human to run and touch both
modes and judge whether the option and documentation were unsurprising; it also named
specific falsifiers. That places implication-level UAT after mechanical and sanity checks
while preserving the checkpoint history until human acceptance.

### Installed-runtime proportionality failure

The original checkpoint/UAT actor brief named four overlapping skills, and its evaluator
oracle judged lifecycle correctness without asking whether each additional procedure,
search, tracker, or progress report had a consumer. It therefore established the commit
and UAT order but could not detect orchestration overhead.

A fresh Codex CLI run from the installed `4.0.1` cache exposed that missing boundary on a
three-file greeting fixture. The actor correctly implemented one outcome, created one
private checkpoint, ran mechanical and consumer checks, and stopped before normalization.
It also invoked project-memory retrieval solely because a file edit was about to happen,
performed broad and then scoped prior-chat searches with no task-local dependency, loaded
six overlapping workflow skills, restated the supplied plan in another tracker, narrated
routine transitions, and created a disposable whitespace defect to validate a secondary
`git diff --check` observation. Brian rejected the workflow even though the greeting
behavior itself passed.

The actor brief now supplies only the top-level execution skill. Its separate evaluator
oracle inspects loaded skill files, searches, trackers, temporary controls, and progress
reports, and asks whether each resolved a concrete uncertainty or protected recoverable
state. It deliberately does not use command, token, elapsed-time, or wording quotas. A
fresh actor run against the source correction produced one private outcome checkpoint,
used the supplied plan as its only tracker, and reported no project-memory or prior-chat
search, additional workflow skill, or disposable hygiene control. The independent
evaluator found no oracle failure in the Git tree, reflog, implementation, tests, or
documentation. It also bounded the result correctly: ephemeral skill loads, searches,
trackers, and narration are not recoverable from repository state. The installed Codex
transcript therefore remains the decisive evidence for those proportionality boundaries.
