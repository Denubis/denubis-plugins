# Independent audit brief: token and word estimator

You are the audit actor. Falsify the methodology in `DESIGN.md` by inspecting the raw
Claude Code and Codex logs with your own read-only probes.

Do not run `scripts/verify.py` as your evidence. It implements the method under review.
Do not inspect `docs/AUDIT-ORACLE.md`; that file is reserved for the evaluator.

## Deliverable

Write `findings-<engine>.json` conforming to `findings.schema.json`:

```text
{voice, target, findings:[{id, severity, location, title, body,
                           needs_research, research_question}]}
```

Every finding must identify the inspected population, the probe, concrete evidence,
and why the result changes a reported total or its credibility. One real critical
finding is more useful than a padded list.

## Constraints

- Read logs only. Write probes and the final report outside the log stores.
- Use an implementation independent of `verify.py` and `estimate.py`.
- Treat negative searches as unproven until you establish which files and record types
  the probe could see.
- Report malformed and unparseable records rather than silently skipping them.
- Record the audit time because the live corpus changes.

## Audit procedure

### 1. Inventory the corpus

Independently count Claude main files, Claude subagent files, Codex rollout files,
parseable records, malformed records, root thread IDs, and subagent thread IDs. State
how each path class and record type was recognized.

### 2. Attack Claude assistant dedupe

- Group assistant records by `message.id` without using estimator code.
- Compare SUM, FIRST, LAST, and MAX behavior for repeated IDs.
- Inspect samples from IDs present in both main and subagent files. Determine whether
  the main occurrence generated the message or could itself be replayed.
- Find IDs spanning multiple people or projects and show how attribution changes under
  each plausible occurrence choice.
- Inspect timestamp ordering for cross-partition IDs. Test whether earliest-main versus
  earliest-any occurrence changes exact-window membership.

### 3. Attack Codex counter ownership

For every Codex subagent thread:

- Locate the first `Message Type: NEW_TASK` record, if present.
- Separate token events before and after that boundary.
- Resolve the parent and compute its cumulative value at the child fork time.
- Compare the child's pre-task replay maximum with that parent value.
- Determine whether post-task values continue the replay baseline, reset below it, or
  begin without replay.
- Test post-task monotonicity.

Separately inspect subagents without a task boundary, repeated own thread IDs, root
threads with lineage fields, and malformed or missing timestamps. Explain any case
where owned output cannot be distinguished from replay.

### 4. Recompute exact-window behavior

Choose at least one interval that cuts through active Claude and Codex sessions.

- For Claude, deduplicate globally and assign each complete message to the proposed
  origin timestamp. Identify messages whose later updates or replays cross either
  boundary.
- For Codex, independently form child-owned cumulative series and subtract the last
  value before each boundary.
- Confirm the start is inclusive and the end exclusive with records exactly on each
  boundary.
- Quantify the uncertainty created by message-level and counter-event granularity.

### 5. Attack human-word classification

- For Claude main user records, histogram leading tags by count and word volume. Inspect
  frequent unlisted tags and samples of listed tags. Test UUID replay ordering.
- For Codex root user messages, histogram leading markers by count and word volume.
  Inspect both retained and excluded samples.
- Check whether any human turn exists only in an ignored record channel.
- Report pasted-content volume separately; it is intentionally retained, but its size
  must remain visible.

### 6. Reconcile attribution and totals

Build an independent leaf table including unrooted and person-root activity. Sum it
back to source totals. Exercise overlapping mapper prefixes and moved paths. Any unit
that disappears or lands in more than one leaf is a finding.

### 7. State the residual uncertainty

End with:

- which assumptions survived a positive population-wide test;
- which survived only sampling;
- which could not be tested from the available logs;
- whether the estimator is suitable for publication, suitable only with caveats, or
  unsuitable.
