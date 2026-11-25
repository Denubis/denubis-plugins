# compact-nag

A Claude Code mod (a plugin built from a hooks module). When a session's context fills,
it has the session hand over: save its state, write the brief for its own compaction
summary, and only then compact.

## The problem

A conversation compacts when it reaches Claude Code's threshold, often in the middle of
work, using a generic summary. Subagents can grow very large before they reach it. What
the session knew but had not written down is lost.

## What it does

**At 40% of the context window** a note goes into the conversation, and again at each
further 5 points. It tells the session to finish the step it is on, start nothing new,
and then:

1. update its TODO list and any plan file;
2. write or update its worklog in the main repository's notes directory: what it did, the
   decisions and their evidence, open questions, the exact next step;
3. record decisions as the project's rules allow: a ruling the human has already made
   goes in the decision register, and a change that needs approval goes in as a proposal
   or an open-question ticket, not applied;
4. call `ready_to_compact` (`mcp__denubis-hook-compact-nag__ready_to_compact`).

**`ready_to_compact`** takes a `brief`, the session's own instructions for its compaction
summary, and `saved`, the paths of the handover files it updated. The tool refuses a
missing file, or one that has not changed since the first note of this cycle, and says
which. When it accepts, the main session compacts as soon as that turn ends. The
instructions are the brief, followed by a line telling the session to re-read the saved
files first. The acceptance also tells the session to end its reply by saying it is being
compacted at its own request and will carry on by itself, so nobody needs to nudge it.
For a worker in its own pane, that reply is what Claude Code's idle notice carries to the
supervising session, which otherwise reads the compaction as a pause.

**After that compaction** the mod submits a prompt, so the session carries on without
waiting for the person. The prompt tells it to re-read its saved files and take the
next step they name, or to say what it needs and stop if that step waits on the person.
It quotes the session's brief and its reply at the end of the turn in which it said it
was ready, even if the compaction ran a turn or more later. The prompt goes out 2 seconds
after the compaction, and only if no turn has begun since the compaction returned to the
mod: a message already waiting
when the compaction ends (a supervisor's, say) takes the next turn, and the session
carries on from that instead. No prompt follows a compaction that was refused, or one
the session did not ask for (`/compact`, Claude Code's own).

**Past 50%** the main session is still never compacted unless it said it is ready. Each
of its stops leaves an urgent note instead, which the session reads at its next turn.

**Subagents** get the same notes in their own conversation. The main conversation gets a
one-line notice naming the subagent, so whoever dispatched it can tell it to finish. A
mod cannot compact a subagent on request, so a subagent compacts only at Claude Code's
own threshold. If it called `ready_to_compact`, its brief is used then.

**Every compaction** of a conversation that saved a brief carries that brief. This
includes `/compact`, where the person's own text comes first, and Claude Code's automatic
compaction. A compaction that goes ahead starts a new cycle for that conversation.

**`/compact-nag`** lists each conversation's last context fill and whether it has been
nagged or is ready, with its saved files.

The mod does not change Claude Code's own compaction threshold
(`autoCompactWindow`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW`).

## Rulings

- [ADR 2026-11-10-bbs-pre-compaction-worklog-needs-no-approval](../../docs/architecture/decisions/2026-11-10-bbs-pre-compaction-worklog-needs-no-approval.md):
  a session may write its own worklog before it compacts, without asking first.
- [ADR 2026-11-10-bbs-compact-nag-leaves-engine-threshold](../../docs/architecture/decisions/2026-11-10-bbs-compact-nag-leaves-engine-threshold.md):
  no change to Claude Code's threshold, compaction only when the session is ready, and an
  urgent note at each stop past 50%.
- [ADR 2026-11-16-bbs-compact-nag-resumes-after-its-compaction](../../docs/architecture/decisions/2026-11-16-bbs-compact-nag-resumes-after-its-compaction.md):
  after its own compaction the mod starts the next turn, quoting the session's brief and
  its handover reply.
- [ADR 2026-11-24-bbs-compact-nag-compaction-is-not-a-pause](../../docs/architecture/decisions/2026-11-24-bbs-compact-nag-compaction-is-not-a-pause.md):
  a worker's handover reply says it will carry on by itself, and no resume prompt is sent
  once another turn has begun.

## Limits

- Context fill is measured after each model request: its input, cache and output tokens
  over the context window of the session's model, as `$.session.usage()` reports it. A
  subagent on a model with a different window is measured against the main session's.
- The thresholds (40, 5, 50) are constants in `hooks/register.ts`, not settings.
- Without `ready_to_compact`, the only compaction is Claude Code's own.
- The reply line is an instruction to the model: it works only as far as the session
  writes it and the supervisor heeds it.
- The resume is held back only by a turn that begins after the compaction returns to the
  mod. A waiting message whose turn begins before that, which the transcripts cannot rule
  out, still has the resume arrive after its turn, late, as in 0.1.1.
- A message queued ahead of the resume whose turn begins more than 2 seconds after the
  compaction still overtakes it.

## Tests

`claude plugin test plugins/denubis-hook-compact-nag` runs `tests/compact-nag.test.ts`
against a stand-in engine with a 1000-token window and a mocked clock. The stand-in
holds a plugin's prompt while a main turn runs or a message taken ahead of it waits, and
starts that message's turn after the compaction has returned to the mod. The wording the
mod gives the model is judged by review and live use, not by these tests.
