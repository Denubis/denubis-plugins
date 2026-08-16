# Evaluator oracle: token and word estimator audit

Do not provide this file to the audit actor. It records the conclusions an evaluator
should expect the actor to test, not instructions the actor should imitate.

## Load-bearing conclusions

- Claude replays parent assistant messages into subagent transcripts under the same
  `message.id`. Global MAX dedupe prevents those copies from becoming new output.
- A Claude ID occurring in main and subagent files is classified as main. An audit must
  challenge, rather than merely repeat, the assumption that such IDs originated in
  main.
- Modern Codex subagent files are not uniformly independent counters. Some replay the
  parent's token events before `NEW_TASK` and continue from that cumulative baseline;
  their owned output is the post-task counter minus the replay baseline.
- Other Codex children begin fresh or reset after replay. A classifier must distinguish
  these cases from the continued-counter case rather than use a magnitude heuristic.
- For replay-bearing children, the replay maximum should equal the parent's cumulative
  value at fork, and the owned post-task series should be monotonic. A mismatch is a
  methodology failure, not an ignorable anomaly.
- Exact Claude windows are message-grained and origin-based. Exact Codex windows are
  deltas of replay-adjusted cumulative counters. These are deliberately different
  because the sources expose different identities.
- Topic exclusions are not part of structural time slicing. An actor should reject any
  hidden project, date, or topic special case in the estimator.
- Machine-text filtering is a named-marker classification, not a leading-character
  rule. Human markup, Markdown headings, and pasted content may legitimately begin with
  syntax that resembles a wrapper.

## Evidence quality

A strong audit report:

- inventories the complete population before relying on zero mismatches;
- uses its own parser and counter reconstruction;
- produces examples for each observed Codex counter mode;
- distinguishes structural counting from disclosure-scope adjustments;
- quantifies time-boundary granularity;
- reconciles leaf totals back to source totals;
- identifies assumptions the logs cannot prove.

A report that only reruns the bundled verifier, searches for forbidden phrases, or
returns an empty finding list without a positive inventory has not performed the
methodological check.
