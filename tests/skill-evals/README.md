# Skill methodological evaluations

These cases test whether an agent can apply a skill to realistic work. They are not
automated prose checks and do not produce approval certificates.

Each case separates:

- `actor.md`: the task and permitted evidence given to the acting agent;
- `fixture/`: the workspace copied to an isolated scratch directory; and
- `oracle.md`: the evaluator's criteria, which are not shown to the actor.

## Procedure

1. Copy the case fixture to a new scratch directory. Initialise Git when the case requires
   commit observations.
2. Record the exact skill paths and repository commit or file digests supplied to the
   actor.
3. Give the actor only `actor.md`, the scratch workspace, named project instructions, and
   the skills under test. Instruct it not to inspect the case directory or evaluator
   material.
4. Let the actor perform the task. Capture its filesystem changes, commands, commits, and
   final response.
5. Only after the actor finishes, read `oracle.md` and evaluate the observed consequences.
6. Report concrete deviations and evidence. A model verdict is a lead, not authority that
   the skill works in other contexts.

Run a current-skill baseline before changing a major methodological responsibility. That
baseline is RED only when the actor exhibits the failure named by the hidden oracle; an
awkward phrase or different document layout is not a failure by itself.

