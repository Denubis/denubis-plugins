---
name: using-token-estimator
description: Use when measuring AI token/word usage from Claude Code or Codex logs for a disclosure, using origin dedupe, replay-aware Codex counters, exact windows, project mapping, and independent audit.
user-invocable: true
---

# Using the Token Estimator

## Outcome

Report model output tokens and human-authored input words as separate units. Split
output between root threads and subagents. Never describe tokens as equivalent to
words or use one as a proxy for the other.

The scripts read `~/.claude/projects` and `~/.codex/sessions`; they do not modify
either log store.

## Run the estimator

Resolve the provider-supplied plugin root, then invoke the report script:

```bash
PLUGIN_DIR="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:?plugin root unavailable}}"
python3 "$PLUGIN_DIR/scripts/estimate.py"                     # current project
python3 "$PLUGIN_DIR/scripts/estimate.py" --dir <path> --month
python3 "$PLUGIN_DIR/scripts/estimate.py" --dir <path> \
  --start 2026-08-11T05:37:40Z --end 2026-08-16T07:44:15Z
python3 "$PLUGIN_DIR/scripts/estimate.py" --person <name>
python3 "$PLUGIN_DIR/scripts/estimate.py" --all
python3 "$PLUGIN_DIR/scripts/estimate.py" --dir <path> --csv out.csv
```

`--start` and `--end` must be provided together as timezone-aware ISO timestamps.
They define `[start, end)` and cannot be combined with `--month`.

## Interpret output correctly

- `main_tok` is model output owned by human-steered root threads.
- `sub_tok` is model output owned by spawned subagents after replay removal.
- `human_words` counts retained human user turns after named machine-wrapper
  exclusions.

The subagent percentage describes only the model-output split. Do not combine it with
the human-word total.

## Counting rules

Claude assistant output has stable message IDs. Deduplicate globally by `message.id`,
retain maximum `output_tokens`, and classify an ID as main if it appears in any main
transcript; otherwise classify it as subagent output. For exact windows, assign the
complete retained message to its earliest main occurrence, or its earliest subagent
occurrence when it never appears in main.

Codex exposes cumulative thread counters rather than message IDs. Read the first
`session_meta`, then split child files at the first `Message Type: NEW_TASK`. Discard
pre-task replay. If post-task values continue from the replay maximum, subtract that
baseline; if they start fresh or reset, retain them unchanged. Root and replay-adjusted
child totals are additive.

Claude human turns come from main transcripts, deduplicate by UUID at their earliest
timestamp, and exclude `toolUseResult`, `isMeta`, and named wrapper tags. Codex human
turns come from root-thread `response_item` user messages and exclude named injected
markers. Do not text-deduplicate Codex turns: repeated `yes` or `continue` messages are
distinct human sends.

Machine filtering is a named allow-list in `scripts/verify.py`, never a rule such as
"drop anything starting with `<` or `#`". Human prompts may contain markup, Markdown
headings, terminal output, or pasted agent text.

## Exact windows and disclosure scope

Claude windows are message-grained at the deduplicated origin time. Codex windows are
the difference between replay-adjusted cumulative counters immediately before the two
boundaries. Human turns use their retained event time.

This is a structural time slice. If a disclosure excludes unrelated work inside the
interval, calculate and document that as a separate audited adjustment. Never add
project-, date-, or topic-specific exceptions to the estimator.

## Map directories to projects

`~/.token-estimator` declares people roots:

```toml
roots = ["/home/you/people", "/mnt/store/people"]
```

Without it, the tool scopes to the target directory. A project-local
`.token-estimator` binds current and historical paths to one canonical project:

```toml
person = "Jodie"
project = "BJET-Phase1"
paths = [
  "/home/you/people/Jodie/BJET-current",
  "/home/you/people/Jodie/old-moved-dir",
]
```

Matching uses the longest recorded-path prefix. Append new paths after a move; retain
old paths so historical log entries still resolve.

## Verify and audit

Run the live implementation checks:

```bash
python3 "$PLUGIN_DIR/scripts/verify.py"
```

Require positive population evidence: thread/file inventory, Codex counter modes,
replay/parent comparisons, monotonicity, and attribution reconciliation. An empty
defect list without those bounds is not evidence.

The verifier tests the implemented method, not the method's truth. For an independent
audit, give another engine `docs/AUDIT-BRIEF.md`, `docs/DESIGN.md`, and read-only log
access. Do not give the actor `docs/AUDIT-ORACLE.md`; use that separate file to evaluate
its report.

Do not publish adjusted totals until the structural result, every scope adjustment,
and the independent audit are all reproducible.
