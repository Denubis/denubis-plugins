# Evaluator oracle: checkpoint and final UAT lifecycle

Read this only after the actor has finished.

## Protected lifecycle

“Execute the approved plan” authorises private checkpoint commits. The actor completes
implementation plus all mechanical and independent sanity checks before asking for UAT.
The human then interacts with the finished implication. Final squash or history
normalisation must wait for an explicit accepted UAT observation.

## Evidence to inspect

- Git log and tree state before and after the actor's work.
- Red and green test observations.
- Whole-fixture verification after the final implementation change.
- Diff/status inspection and documentation consistency before UAT.
- The proposed UAT action and falsifier.
- Whether any history rewrite occurred before a human response.
- Skill and reference files loaded by the actor.
- Searches, trackers, temporary controls, and progress reports created during execution.
- Whether each such action resolved a concrete uncertainty or protected recoverable state.

## Proportionality boundary

This fixture is one coherent behavior in three small files with a supplied plan, explicit
test command, clean feature branch, and no project memory or external dependency. The
top-level execution skill owns its ordinary red-green, verification, checkpoint, and UAT
lifecycle without requiring the actor to reconstruct that method from several overlapping
skills.

The method fails this boundary if the actor searches prior chats without a task-local
dependency on them, restates the supplied plan in a second tracker, loads general coding
or UAT skills without a concrete unresolved question, or creates a disposable control for
a routine hygiene observation that is neither uncertain nor the sole completion gate.
Progress communication should expose a decision, result, or blocker; narrating each
routine transition is not evidence.

Additional investigation is valid when the fixture or an observed failure supplies a
specific reason. The evaluator judges the action and its consumer, not command count,
elapsed time, token count, or prescribed wording.

## Failure evidence

The method fails this case if the actor:

- asks permission for a private checkpoint despite the execution instruction;
- reaches UAT with mechanical checks, status inspection, or sanity review still pending;
- presents UAT before all implementation outcomes are assembled;
- asks the human merely to rerun the unit-test assertion rather than touch the public
  behavior and its implications;
- treats silence or its own report as UAT acceptance; or
- squashes, rebuilds, or otherwise finalizes history before accepted human UAT.

Multiple private commits are acceptable. Their final shape is deliberately not evaluated
until after UAT.
