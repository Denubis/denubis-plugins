# Multi-agent token/word estimator — Design (v2.1, post-review, node 2 corrected)

Status: methodology reworked after critical peer review v1 falsified the v1
counting model. **v2.1 corrects node 2** — the v2 Codex method was itself wrong (it
merged additive subagent work into the parent thread; see node 2 and Retracted).
Nodes 1, 3, 4 are established empirically; node 2 is corrected and re-derived; node 5
is established with a reconciliation proof. A close external audit is pending before
implementation (`scripts/verify.py` + `docs/AUDIT-BRIEF.md`). Scaffolding (record shape, dimensions, CSV+MD output)
unchanged from v1.

## Core principle (the fix)

**Count each unit of work once, at its point of origin. A replayed copy in a child
context is not new work — but a child's own work is new and must not be erased.** The
two sources fail in opposite directions, and v1/v2 got bitten by both:

- **Claude** subagent transcripts *replay* the parent's assistant messages under the
  parent's `message.id`. Location-based counting double-counts the subagent share, so we
  dedup by message identity and classify by origin (node 1).
- **Codex** subagent rollouts do the reverse: each has its **own independent, additive**
  output counter. The danger is *merging* it into the parent and erasing it — exactly the
  v2 node-2 defect, corrected in v2.1 (node 2).

Count-once-at-origin cuts both ways: never count a replay twice, never merge away real
child work.

## Purpose

Report AI effort as two real measures — output **tokens** (machine) and human-authored
input **words** (human) — split so the proportion of output that is autonomous subagent
fan-out vs main-thread (human-steered) work is visible. Faceted person → project →
subdir → month, rollups at each level. Numbers feed an AI-use disclosure in a
registered report; a wrong split is a publishable error.

## Scope

In: **Claude Code**, **Codex**. Out: **Antigravity** (protobuf logs, no usage field).

## Record contract

```
LeafRecord = { source: "claude"|"codex", cwd: str|None, month: "YYYY-MM",
               main_tok: int, sub_tok: int, human_words: int }
```
Tokens or words, never both, per record; the core sums into leaf cells
`(person, project, subdir, month)`.

### Capability matrix (corrected — Codex DOES have subagents)

| source | main_tok | sub_tok | human_words |
|---|---|---|---|
| Claude Code | yes | yes | yes |
| Codex | yes | **yes** (thread_spawn) | yes |

## Counting methodology

### Node 1 — Claude output tokens (origin-based dedup)

- Scan `~/.claude/projects/**/*.jsonl`. Per assistant message record `message.id`,
  `output_tokens`, and whether it occurred in a main-thread file (`*/*.jsonl`, not
  under `/subagents/`) or a subagent file (`*/*/subagents/**`).
- **Dedup globally to one entry per `message.id`, MAX `output_tokens`.** Two observed
  regimes — constant (same total each line) and streaming cycles (`[1,1,191,1,1,191]`);
  MAX is the message total in both, SUM over-counts, FIRST/LAST unsafe (3 ids have max
  not on last line). The v1 "cumulative per block" story was wrong; MAX conclusion holds.
- **Classify by origin:** id present in ≥1 main file → `main_tok`; id present only in
  subagent files → `sub_tok`.
- **Justification:** a subagent's output returns to main as *text* (tool result), never
  as an assistant message carrying the subagent's `msg.id`; replay only flows parent→child.
  So "in a main file" ⟹ originated in main.
- **Evidence (point-in-time; `scripts/verify.py` is authoritative — the corpus grows live):**
  ~226,765 distinct ids; 10,148 appear in BOTH partitions. Origin-based: main ≈109.3M /
  sub ≈27.7M = **20.2%** subagent share (was 20.3% at the prior snapshot; the *ratio* is
  the load-bearing claim, the absolute counts drift up). Naive
  location-based (the v1 bug) counts the 10,148 in both buckets → 22.3%, +3.34M phantom
  subagent tokens.

### Node 2 — Codex output tokens (per-file, subagents additive)

- Scan `~/.codex/sessions/**/rollout-*.jsonl`. **One rollout file = one Codex thread.**
- Per file, read the **first `session_meta` record** as the thread's own identity
  (`id`, `source`); take **MAX `output_tokens`** (from `event_msg.token_count` →
  `info.total_token_usage.output_tokens`) over the file. The counter is
  cumulative-monotonic, so MAX is the thread's final total.
- **Classify by the first `session_meta.source`:** a structured
  `{"subagent": {"thread_spawn": …}}` object → `sub_tok`; a string (`cli`/`exec`/`vscode`)
  → `main_tok`.
- **No lineage merging.** A subagent rollout embeds the parent's `session_meta` as a
  *replayed second record* and points at the parent via `forked_from_id` /
  `parent_thread_id` — but its **output counter is independent and additive** (first
  `output_tokens` ≈ 900, climbing to the subagent's own total, *not* starting at the
  parent's running total). Subagent output is genuine new work. The v2 method merged
  parent + subagents that shared the parent id and took MAX, **deleting** that work.
- **Resumes:** none in this corpus — 173 files = 173 distinct own-ids, so there is no
  same-id continuation to dedup. IF a future corpus has a true resume (a `cli` file whose
  `forked_from_id` points at another `cli` thread and whose counter *continues* the
  parent total, or a repeated own-id), MAX-merge those same-kind continuations only —
  never a subagent.
- **Evidence:** 173 files = 102 root (99 `cli` + 2 `exec` + 1 `vscode`) + 71 subagent.
  main **6,284,838** / sub **1,641,596** = **20.7%** subagent share. The thread the v2
  doc cited as proof of replay, `019cd741-0604` = `[112566, 112912, 115439]`, is in fact
  a parent (115,439) plus **two independent subagents** (112,566 and 112,912) that each
  produced ~112k of real output — additive, not a replay.
- **The correctness here is the classification, not the total.** Per-file sum *always*
  equals the grand total (arithmetic, not validation); what makes 20.7% right is that
  every file is counted once and labelled by its true origin. That rests entirely on the
  additive-subagent assumption below.
- **Load-bearing assumption (corrected-pending-audit, not final):** each subagent rollout's
  output counter is *independent* — it counts only the subagent's own generation, which on
  return becomes the parent's *input*, never the parent's output, so separate threads cannot
  double-count in output. Empirically every one of the 71 subagents starts fresh (first
  `output_tokens` < 2000, far below parent totals). `scripts/verify.py` checks all 71, and
  the external audit re-tests it. A subagent whose counter *continued* the parent total
  would break this and inflate `sub`.

### Node 3 — Claude human words

- **Main-thread files only** (subagent "user" turns are the orchestrator's machine
  Task prompt, verified: "Simplify code changed in Phase 4… Working directory:…").
- Per `type:user` entry: drop if `toolUseResult` key present or `isMeta:true`.
- Count words of text blocks whose leading tag is **not** in the machine-wrapper
  allow-list: `system-reminder, command-name, command-message, command-args,
  command-stdout, command-stderr, local-command-stdout, local-command-stderr,
  local-command-caveat, task-notification, teammate-message, bash-input, bash-stdout,
  bash-stderr, user-prompt-submit-hook`.
- **Critical rule:** exclusion is a *specific allow-list of machine tags*, NOT
  "starts with `<`". Humans paste markup — `<p>`, `<div>`, `<style>` observed as
  genuine human content; blanket leading-`<` exclusion would delete them.
- Dedup human turns by `uuid` (safety belt; replay doesn't reach main files).
- **Evidence (point-in-time; `scripts/verify.py` recomputes):** machine wrappers
  `task-notification` ~951, `command-name` ~762, `command-message` ~251,
  `local-command-stdout/stderr` ~220, `teammate-message` 50, `system-reminder` 6.
  **0** entries mix a wrapper block with a human block → entry-level filtering loses no
  human text. ≈22,049 plain human blocks ≈1.59M human words (vs v1's 2-project
  under-sample of 3,698). Reproduces from the written rule (unlike node 4); absolute
  counts drift up with the corpus.

### Node 4 — Codex human words (re-derived from the live stream)

- **Channel:** root threads only; `response_item` with `payload.type=="message"`,
  `role=="user"`. Ignore `event_msg.user_message` (a partial duplicate, 1,351 vs 1,769);
  exclude `role=="developer"`.
- **Machine allow-list (named markers, NOT "starts with `<`/`#`"):** drop a turn whose
  leading marker is in `{turn_aborted, skill, subagent_notification, environment_context,
  user_instructions}`, or which starts with the `# AGENTS.md` session-opener. Each was
  confirmed machine by inspecting content: `turn_aborted` = interrupt boilerplate,
  `skill` = injected SKILL.md, `subagent_notification` = subagent JSON status,
  `environment_context`/`# AGENTS.md` = injected context.
- **Keep, as human:** plain prose; **markdown-heading prompts** (`# Claude …`, `#
  Architecture Bootstrap …` — Brian's own multi-AI priming prompts, *not* machine); pasted
  agent output (`●…`) and terminal pastes (owner's explicit choice). The `#`-heading case
  is the node-3 trap restated: exclusion is a named set, never a leading-character rule.
- **No dedup.** The corpus has zero resumes and `response_item` carries no message id, so
  each kept user message is a distinct human send. Earlier text-set dedup was justified by
  "count replays once" — but with no replays it only *destroyed* real repeated turns
  (`yes` ×16, `continue`, `ok` across a thread). Dropped.
- **Two undercounting risks checked and cleared:** (a) `# AGENTS.md` messages end in
  `</INSTRUCTIONS>`/`</environment_context>` (no human prompt appended), and **0 of 102**
  root threads are left with zero human turns — so wholesale-dropping them loses no human
  text; (b) the repeated-send issue above, fixed by removing dedup.
- **Evidence (point-in-time; `scripts/verify.py` reproduces):** machine dropped —
  `# AGENTS.md` 110, `turn_aborted` 188, `subagent_notification` 71, `environment_context`
  35, `skill` 14. Result **1,351 human turns / 108,027 words**. (Supersedes the prior
  unreproducible 1,294 / 103,413.)
- **For audit:** the one judgment call is keeping the 10 markdown-heading prompts as human
  (8,625 words) — verify all 10 are Brian's prose, not a machine template (the "You are one
  of three AI systems…" opener reads closest to a template). Pasted content kept by owner's
  choice is ~4,900 words; flagged, not hidden.

### Node 5 — cwd attribution + mapper (established, with reconciliation proof)

- **Default derivation.** `ROOTS = [~/people, /media/brian/storage/people]`, longest-prefix
  match on the *recorded* `cwd` string:
  - ≥2 segments → `person`=L1, `project`=L2, `subdir`=remainder (`—` if none).
  - 1 segment → `person`=L1, `project`=`(person-root)` (real: `Lise` 12,103 msgs,
    `Helle-Aarhus` 1,053, `Brian` 1).
  - no root prefix → `person`=`(unrooted)`, `project`=`<full cwd>` (`~`/home,
    `/tmp/exec-*`, `morning-assistant`).
- **Worktrees need no special case** (user: "worktrees are part of the project").
  `.worktrees/<branch>` is just the `subdir` remainder and rolls up to the project
  automatically. The dominant pattern (PromptGrimoireTool alone has ~30) is handled by
  the generic rule.
- **Mapper** (`.token-estimator` TOML in project dirs): a canonical `person`/`project`
  plus a `paths` list (current **and** historical strings). Longest-prefix string match
  on the *recorded* cwd, applied **before** default derivation; `subdir` = remainder
  after the matched path. Pure-string-on-historical-cwd is load-bearing: the logs already
  recorded the old paths, so a dir shuffle (Jodie) can't retroactively change them and the
  mapper rescues them without touching disk. This — not a third root — is the declared fix
  for the `people/people` typo (user's call); 0 logged cwds hit it today.
- **Attribution binds to the deduplicated unit.** Each Claude `message.id` carries its
  cwd from the occurrence the dedup keeps (the MAX-token line; lexicographic tie-break),
  so attribution rides *through* dedup — never "attribute every occurrence then dedup,"
  which would re-introduce the double-count.
- **Reconciliation proof (the "up and down" guarantee):** of 226,660 Claude ids,
  **0 span more than one person** and only **2 span more than one `(person, project)`**
  (both within one person, worktree vs root). So person-grain rollups reconcile *exactly*;
  project-grain to within 2 ids in 226k; the grand total is exact by construction (every
  id's tokens land in exactly one cell). Codex cwd is stable per thread (173 threads, 1
  cwd each).
- **Acceptance test (implementation must demonstrate):** the sum of every leaf cell —
  *including* `(unrooted)` and `(person-root)` — equals the node 1–4 grand totals, for
  tokens **and** words. Report-scoped views (e.g. people-roots only) are subsets that must
  show the dropped residual, never silently omit it.

## Outputs

- `estimate.csv` — tidy leaf grain, one row per `(source, person, project, subdir,
  month)`, columns `main_tok, sub_tok, human_words`; blank (not 0) where a source
  can't produce a bucket.
- `estimate.md` — pre-rolled tables (per person→project with month rows + TOTAL,
  per-person summary).
- Terminal summary — grand totals, subagent share of output tokens, human input
  words, scoped to `--person` / `--project` filters.

## Architecture (as built)

```
scripts/verify.py   # single source of truth: node 1-5 rules + the audit harness  (read-only)
scripts/mapper.py   # reads .token-estimator mappers (directory rollup)
scripts/estimate.py # report engine: per-project / --person / --all, --month, --csv
```
`estimate.py` imports `verify.py` so the report and the audit share one implementation of
every rule. People-roots come from `~/.token-estimator` (else the local dir).

## Testing

The discipline is **reproducibility, not fixtures**: `scripts/verify.py` re-derives every
headline number from the live logs and asserts the structural invariants (no Codex resumes,
subagents additive across all of them, person-grain reconciliation), printing point-in-time
counts separately because they drift as logs grow. This is what node 2 lacked — its prose
said group by `session_meta.id`; its number came from a different, wrong grouping, and
nothing re-derived it. `docs/AUDIT-BRIEF.md` hands the assumptions to an external engine to
falsify independently.

## Retracted (do not reintroduce)

- **v2 node 2 (the big one):** "thread-lineage MAX dedup — group Codex rollouts by
  `session_meta.id` and take MAX." Wrong twice over: `session_meta.id` is unique per file
  (no grouping happens), and the *intended* grouping merged parent + subagent rollouts
  (which share the parent id via a replayed second `session_meta`) and took MAX, **erasing
  additive subagent output.** The cited proof `019cd741-0604 = [112566,112912,115439]` is
  a parent plus two independent subagents, not one replayed thread. Real share 20.7%, not
  26.8%.
- **From v1:** "Codex has no subagents" (41% are); the `3.62×` ratio and `msg_01Wtbf…`
  citation (unreproducible); the "cumulative per block" dedup story (two regimes); the
  2-project human-word counts presented as corpus-wide; the named-wrapper list as
  "complete."

## Open items

- **Close external audit pending** (`scripts/verify.py` + `docs/AUDIT-BRIEF.md`) before implementation — nodes 1, 3, 4 have
  not had the falsification that just overturned node 2.
- Node 2 subagent counter-independence is empirical; audit re-tests it.
- Codex true-resume handling is specified but untriggered (0 resumes in corpus).
- Pasted content counts as human input words (user's explicit choice).
