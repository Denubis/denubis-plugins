# Codex-supervises-Claude specification, forwarded by Brian on 2026-10-24

Provenance: Astra, a Codex session on `gpt-6-astra`, wrote this specification. Brian
pasted it into the supervising Claude session on 2026-10-24 with the instruction "is the
spec from Astra. Your job here is to run supervising-codex and to get sol to do the work
and you to critically engage with sol's work" (session `3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29`).
The text below is carried verbatim. Where it conflicts with an accepted ADR, the ADR
wins and the conflict is flagged, not resolved silently. ADRs 0035 to 0041 record the
rulings made against it.

---

The plugin needs a **Codex-supervises-Opus mode**, preserving the existing safety controls. This is more than changing the executable name.

Give the plugin instance this specification:

---

Implement external **Claude Code / Opus supervision from a Codex host**, using the existing `supervising-codex` workflow as the reference. Preserve existing Codex supervision behavior.

**Roles and authority**

- Opus implements bounded tasks.
- Codex prepares briefs, reviews proposed behavior and tests, inspects changes, and independently runs verification.
- The human decides unresolved requirements, rules, scope changes, commits and publication.
- Supervisor conclusions must remain challengeable: distinguish human rulings from supervisor assertions and link assertions to evidence.
- Neither agent may approve permission dialogs on the human's behalf or treat silence as approval.

**Required driver capabilities**

Expose documented commands for:

- Starting Claude Code with an explicitly selected Opus model and supported effort setting; report the actual session identity and configuration.
- Resolving the supervised pane by stable identity, excluding the supervisor itself. Refuse ambiguous matches.
- Inspecting status and bounded recent output.
- Sending a prompt-file reference or literal message safely.
- Monitoring actionable events: review checkpoint, question, permission request, completion and process failure.
- Interrupting work, compacting context, starting a fresh session and shutting down cleanly.
- Reporting context usage where reliable information exists; report "unknown" otherwise.

Do not reuse Codex-specific title parsing, session files, hooks, commands or context thresholds without verifying their Claude equivalents.

**Safe communication**

- Before sending, verify the session identity, expected project, readiness, empty input composer and absence of a permission dialog.
- Send text literally and verify submission. If submission is uncertain, report that uncertainty rather than blindly sending it again.
- Never send an Enter or approval keystroke into an unidentified UI state.
- Surface unsupported operations explicitly.
- Use a gitignored prompt/return directory outside the notes directory. Durable decisions, questions and review reports remain in their project-owned locations.
- Do not read or stage credentials or unrelated transcripts.

**Supervision checkpoints**

Support this loop without requiring the human to shuttle messages:

1. Codex issues a bounded brief naming the task, allowed files, constraints, acceptance behavior and required evidence.
2. Opus investigates and submits its proposed contract, tests and unresolved decisions.
3. Codex reviews the actual artifacts. Once the contract is settled, Opus establishes meaningful behavioral RED.
4. Codex checks the failure evidence before releasing implementation.
5. Opus implements minimally, verifies, and submits the changed files and results.
6. Codex independently reviews and reruns relevant checks.
7. Corrections return to Opus. Dependent work starts only after Codex explicitly releases it; human acceptance remains separate.

Checkpoint messages must identify the task and submitted artifact revision or digest. A stale completion event must not release newer work. The worker must remain paused while the supervisor verifies its submission.

**Failure and restart behavior**

- Persist session/task identity, the current checkpoint, prompt identity, pending questions and review disposition.
- After either process restarts, reconcile persisted state with the actual pane and files.
- Never infer completion from a process exit, a quiet monitor, elapsed time or the word "done."
- Deduplicate notifications. Ask each human question once; retain it until answered.
- Support explicit resumption after interruption without duplicate dispatch or lost review findings.
- Monitoring must yield control to the Codex host so it can review artifacts and respond to the human. Do not claim monitoring continues after the host stops unless a separately running mechanism actually provides that behavior.

**Verification requirements**

Demonstrate:

- An actual Codex host supervising an actual Opus process through one small task.
- Behavioral RED → review → implementation → independent verification.
- A reviewer rejecting a plausible but incorrect implementation and Opus correcting it.
- Refusal to send into a busy pane, nonempty composer, permission dialog, wrong session or ambiguous target.
- Recovery from worker crash, supervisor restart, interrupted submission and stale checkpoint events.
- Questions reaching the human without being answered by either agent.
- No regression to existing Codex supervision.

Use controlled fixtures for destructive/failure scenarios, plus a live local smoke test for the real CLI and tmux integration.

**Deliverables**

- Updated skill and documented driver interface.
- Tests and exact verification results, including untested boundaries.
- A minimal project setup example.
- A clear separation between implemented capabilities and proposed future features.

**For this project:** retain the existing work, load all eight required quality skills before coding, and prohibit automatic commits, shared Google writes or Discord posts.

> Integration context only: The consuming project is /home/brian/ArsMagica/charsheet. Its remediation backlog is docs/implementation-plans/2026-10-23-seasonal-character-builder-interface/todo.md. Do not execute that backlog during plugin development. The plugin must support project-supplied briefs and constraints without hard-coding charsheet's workflow.

(Replacement paragraph supplied by Astra on 2026-10-24 and forwarded by Brian, replacing the
original "use the remediation TODO" clause. Astra: "I put a charsheet-specific instruction
into the plugin spec without identifying its repository or path. That created the
ambiguity." The eight-skills and no-commit clauses of the original sentence are retained
above because the replacement did not withdraw them.)

---

The viability test is straightforward: **I can receive a checkpoint, inspect stable artifacts, challenge the work, and resume the correct Opus session reliably—without you acting as the message relay.**
