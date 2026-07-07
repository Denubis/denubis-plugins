# The innermost core: proposer / verifier

Date: 2026-06-25
Status: PROPOSAL — **PARTLY SUPERSEDED. Read the banner before acting on this file.**
Scope: the smallest unit we bootstrap, then use to iterate the outer lifecycle skills.

> **SUPERSEDED-IN-PART (2026-07-06).** Current truth lives in
> `RESUME-PROMPT-proposer-verifier-core.md` and `.notes/project_proposer-verifier-decisions.md`.
> Corrections to this file, so nobody acts on the stale parts:
> - **Proposer/verifier are ordinary general-purpose agents, not skills.** Any "two
>   skills" / checklist-and-rubric-in-`.notes/` framing here is dead. Enforcement is a
>   property of a *dispatch* (different model, different permissions), not a doc.
> - The bullet **"The gate is mechanical, not prose"** (below in this file) is an
>   aspirational PRINCIPLE, not a description of the shipped gate. The actual
>   `codex-peer-review` gate is honour-system prose: the suspect model hand-picks 2–3
>   quotes and greps them itself (`codex-peer-review.sh:116-118` only echoes a suggested
>   command; `SKILL.md:46,50`). Codex separately flagged this line as too broad — scope
>   it to artifact gates, human-judgment for the rest. Do not cite it as if the
>   mechanism exists.
> - The **"Panel … different models, not k samples"** bullet (k-proposers) is dead —
>   rejected as unassessed ornament.
> - **The loop, current form:** orchestrator dispatches → different model critiques
>   against intent → critique reaches the human RAW → human rules. No gate, no score.
> - The **verifier engine** section (staging harness, codex invocation, provenance-gate
>   *intent*) and the **Premise** remain valid. The Open items are largely settled or
>   recast in the resume; do not treat them as live here.

## Premise (design premise, not a proven claim)

The building model overclaims, does not reliably find its own errors, and favours its own outputs. The literature is the external evidence for treating this as a design constraint rather than a mood:

- It cannot self-correct without an external signal (Huang et al. 2024).
- It cannot locate its own reasoning errors, though it can fix them once the location is supplied externally (Tyen et al. 2024).
- An evaluator favours its own generations in proportion to how well it recognises them (Panickssery et al. 2024).

Therefore the model cannot verify its own work, and a same-model verifier is structurally compromised.

## The core, one unit of work

- **Proposer (one model): the positive leg.** Build X, demonstrate it works where intended, and leave *independently inspectable* evidence: a test that runs, a consumer a grep finds, a built thing a human can exercise. The proposer proposes freely and does not certify.
- **Verifier (a different model): the negative leg.** Ignore the proposer's claims, run and inspect the evidence directly, and design near-miss probes (same domain, wrong referent) for where X breaks or does the unwanted. Must be a different model, because a same-model verifier favours the proposer's output.
- **The positive-leg doer never does the negative leg.** This is the first split.
- **The gate is mechanical, not prose.** The verifier acts on artifacts, never on the proposer's summary of them. Where possible the gate is a hook or a receipt the proposer cannot self-attest (build-green, test-pass, a receipt file bound to the commit, written by a different process). Prose a model can rationalise past is not a gate; an excuse-catalogue invites the next excuse, so demand the artifact instead.
- **Panel, when used: different models, not k samples of one.** Model diversity is the value. Consensus passes; a split escalates to the human.
- **The human is terminal.** For "does it do what I want, and does it not do what I don't," only the human, exercising the built thing, can judge. The agent writes the bounded probe script and tells the human what to do; the human executes and judges. Everything else must already be green before this.
- **Bounded.** Retries are capped; on unresolved disagreement, HALT to the human.

## The verifier engine (calling out to a different model)

One staging harness, model-pluggable. Stage the target's repo minus gitignored files and binaries into a throwaway dir, pipe the prompt plus the rubric to the external model, capture its output, then run the provenance gate: grep the verifier's quoted phrases against the real files; a quote not in the file it is attributed to voids that finding.

- **codex (now, proven):** `codex exec -s read-only --ignore-user-config -m gpt-5.5 --ephemeral -C <staging> -o <out>`, prompt on stdin. Implemented in `plugins/denubis-external-agents/skills/codex-peer-review/codex-peer-review.sh`.
- **gemini (near-term):** the Gemini REST API (`generativelanguage…:generateContent`) is the reliable scriptable path today. `agy` (Antigravity CLI) has a headless `-p` mode but a non-TTY stdout-drop bug and no read-only confinement yet, so if used it must be wrapped in a pseudo-TTY and run inside the throwaway staging, which the harness already provides.

## Constraints carried from existing work (June 10 rubric-for-rubrics + the harness repos)

- Declare the executor. The main loop is typically Fable, subagents are Sonnet/Opus/Haiku, and over-prescription degrades Fable.
- Put enforcement in architecture (separate agents, separate tool permissions, hooks), not in per-tier prose. A mechanical gate holds regardless of which model runs.
- Readability is pass or fail. A gate whose output the human stops reading is already dead.
- Living documents carry current truth; git carries the change history (R12).

## Open (for the loop and the human to settle)

- Where the proposer/verifier boundary falls in the lifecycle: per phase, per artifact, or per gate.
- Whether the verifier designs the negative-leg probes, or the human does, or both.
- The gemini path's reliability, and whether a third Claude-subagent voice adds anything a different-model verifier does not.
- How this core relates to the in-flight `skill-skills-upstream-sync` branch and its epistemic-humility skill (collision risk on the directive skills).
