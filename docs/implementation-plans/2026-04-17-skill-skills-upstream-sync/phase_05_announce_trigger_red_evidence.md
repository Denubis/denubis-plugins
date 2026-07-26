# RED evidence — epistemic-humility announce-and-temper trigger (2026-07-09)

Records the should-fire test of the `bca222e` rescope, which extended
`denubis-extending-claude:epistemic-humility` to gate results presentation and
added the announcement "I'm using the epistemic-humility skill to temper my
language" as the named observable. Two rounds were run on 2026-07-09; the first
is invalid, the second is a clean RED.

## Round 1 — invalid (installation gap)

An Opus subagent (`denubis-basic-agents:opus-general-purpose`, agent
`a430696656f5aaaed`) produced the skill-3 review report on `writing-skills`,
with the worktree `epistemic-humility/SKILL.md` injected verbatim into its
prompt. No announcement appeared in its report.

The round is invalid as a discovery test. The installed plugin cache held
denubis-extending-claude 1.8.0, which contains no epistemic-humility skill at
all, so the harness skill listing — the routing layer the rescoped description
was meant to act on — never carried the skill. Two further contaminations:
pasted prompt text is data rather than a listed skill, and the prompt's axis-3
instruction told the subagent to apply the rubric to the artefact under review,
framing the skill as an instrument rather than a standing obligation.

## Round 2 — valid RED

Conditions (all observed in session or in the subagent transcript
`ddbd0c01-9d96-4c6b-aeda-4a9b719ddf9d/subagents/agent-af746fd16b0944522.jsonl`):

- denubis-extending-claude 1.9.0 installed; the subagent's system-context skill
  listing contained `denubis-extending-claude:epistemic-humility` with the
  released 196-char description, verbatim (verified in the transcript's
  attachment entry).
- The task (a cross-reference audit of the released 1.9.0 skills) ended with
  "your findings and your conclusions" — inside the description's trigger
  clause. The prompt contained no mention of the rubric, tempering, or
  announcing.
- The subagent read `epistemic-humility/SKILL.md` in full as audit material (it
  verified that file's H2 anchors, which requires reading it). The
  announce-and-temper section therefore passed through its context as data.
- Tool use across the run: Bash ×6, Read ×19. The Skill tool was never invoked.
- All six of the subagent's own mentions of epistemic-humility are audit
  content: it mentioned the skill repeatedly and never used it, including while
  writing the report the skill gates.

Outcome: no announcement in the deliverable. RED by the skill's own named
falsifier. The report's language was substantively decent (file:line evidence,
verified-vs-informational separation), so the failure is the observable gate,
not the prose wholesale.

## Reading

The description lever looks exhausted for unreinforced agents: the trigger sat
in the routing position, matched the task almost word for word, the full skill
text was in context, and the gate still did not fire. A generic subagent
receives the skill listing but none of the main session's reinforcement (no
skill-reinforcement UserPromptSubmit hook fires inside a subagent). This
converges with the 2026-07-02 skill-engagement audit's verdict that enforcement,
not prose, moves compliance. The follow-on is a separate design task:
enforcement for the announcement observable (for example, a hook that checks
report-shaped output for it). Operator direction 2026-07-09: record the RED;
fixes proceed finding by finding.

What would falsify this reading: a same-tier subagent announcing and tempering
unprompted under the same conditions, or evidence that the Skill tool was
invoked without the announcement reaching the deliverable.

## By-product findings (round 2 audit, quotes verified in session)

- F1 `maintaining-project-context/SKILL.md:234`: "Called by →
  executing-an-implementation-plan (Step 5b)" is stale; the live invocation is
  Stage 1 step 4a "Librarian updates" (executing-an-implementation-plan
  SKILL.md:887).
- F2 `maintaining-project-context/SKILL.md:235`: "Called by →
  finishing-a-development-branch (Step 4b)" is stale; that skill has no Step 4b
  and no longer references maintaining-project-context at all.
