# Audit brief — token/word estimator methodology

**For a different engine (codex / gemini / another model), run locally with read access
to the logs.** Your job: falsify the counting methodology in `DESIGN.md`, which the
estimator (`scripts/estimate.py`) implements. The numbers feed an AI-use disclosure in a
*registered academic report*; a
wrong subagent/main split is a publishable error. Be adversarial. Be charitable to
intent, ruthless about correctness.

## Why this audit exists (read this first)

Two "done" nodes have already been wrong in this exact project:

- **Node 2** asserted a 26.8% Codex subagent share via "thread-lineage MAX dedup." It was
  merging a parent rollout with its independent subagents (they share the parent id via a
  replayed `session_meta`) and taking MAX — **erasing** the subagents' additive output.
  Real share: 20.7%. The prose said "group by `session_meta.id`"; that field is unique per
  file and groups nothing. The number came from a different, wrong computation than the
  words described.
- **Node 4** asserted 1,294 human turns / 103,413 words from a method that didn't
  reproduce it (the harness got 1,452 / 144,809 — a 40% gap). It has since been
  **re-derived** by signature-inspecting the live stream to 1,351 / 108,027 with a named
  machine allow-list — but that re-derivation is itself one session old and carries a
  judgment call (markdown-heading prompts kept as human). Attack it like any other claim.

**The pattern to hunt: a claim whose prose and whose computation diverge, and which is
internally self-consistent enough that re-reading it confirms nothing.** A self-test that
passes is not evidence — node 2 "passed" its own story for weeks.

## Ground rules

1. **Do not trust `scripts/verify.py`.** It encodes *our* assumptions. Re-running it reproduces
   our possibly-wrong reasoning — that is precisely how node 2 survived. Use it as a
   starting map, then write **your own independent probes** against the raw logs.
2. **Read-only.** Never modify the logs. Probes only.
3. **No internet needed.** Everything is local. If a finding needs external info you
   cannot get, set `needs_research: true` and state the question.
4. **Emit findings to the schema** at `docs/findings.schema.json` (bundled): `{voice,
   target, findings:[{id, severity, location, title, body, needs_research,
   research_question}]}`. `body` ends in a one-line "why it matters." Write to
   `findings-<engine>.json`.
5. **No padding.** One real Critical beats ten manufactured Minors.

## Data structure (so you don't rediscover it)

**Claude** — `~/.claude/projects/<munged-cwd>/*.jsonl` (main thread) and
`.../<session>/subagents/**/*.jsonl` (subagents, `isSidechain:true`). Each line is one
event. Assistant message: `{type:"assistant", message:{id, model, usage:{output_tokens}},
cwd, isSidechain}`. **Subagent transcripts replay the parent's main-thread assistant
messages under the parent's `message.id`** — the root cause of double-counting.
User turn: `{type:"user", uuid, isMeta?, toolUseResult?, message:{content}}` where
`content` is a string or a list of `{type:"text"|"tool_result", text}` blocks.

**Codex** — `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`. One file ≈ one thread.
First `session_meta.payload`: `{id, forked_from_id, source, cwd}`. `source` is a **string**
(`cli`/`exec`/`vscode`) for root threads, or a **structured object**
`{"subagent":{"thread_spawn":{parent_thread_id,…}}}` for subagents. **A subagent file
contains TWO `session_meta` records — its own first, then the parent's replayed.** Token
usage: `event_msg.payload` with `type:"token_count"` → `info.total_token_usage.output_tokens`,
**cumulative-monotonic** within a file. Human input: `response_item.payload` with
`type:"message", role:"user"` (also a duplicate `event_msg.user_message`; ignore it).

## Per-node attack surface

Each node lists its **load-bearing assumptions** and a concrete **falsifier** — the probe
that, if it returns a hit, breaks the node. Run the falsifiers.

### Node 1 — Claude output tokens (origin-based dedup)
Assumptions:
- **A1 (origin):** an id that appears in any main-thread file *originated* in main — a
  subagent's output never reaches a main file under the subagent's own `message.id`
  (replay flows parent→child only).
- **A2 (MAX):** MAX `output_tokens` over an id's occurrences = the message's true total
  (not SUM, not last-line).

Falsifiers:
- Find an id classified `main` whose occurrences are *all* inside `/subagents/` files
  except one main file that is itself a replay → would mean A1 mislabels sub as main.
  (We claim 10,148 cross-partition ids, all genuinely main-originated. Test that claim:
  for a sample, is the main-file occurrence the *generating* turn or a replay?)
- Find an id where summing distinct non-replay segments ≠ MAX → A2 wrong.

### Node 2 — Codex output tokens (per-file, subagents additive)
Assumptions:
- **A1 (additive):** each subagent rollout has an *independent* output counter (first
  value ≈ 900, far below the parent total). Its output is new work, summed as `sub`.
- **A2 (no resumes):** 173 files = 173 distinct own-ids, so no same-id continuation needs
  MAX-merging.
- **A3 (classify):** first `session_meta.source` (object→sub, string→root) is the right
  label.

Falsifiers (these are the ones that bit us — run them hardest):
- Find a subagent whose **first** `output_tokens` ≈ its parent's total → the counter
  *continues* the parent (replay), so summing double-counts and the additive model is
  wrong. (We sampled ~6 and saw ≈900 starts. Check **all 71** subagents, not a sample.)
- Find two rollout files sharing a first-`session_meta.id` → a true resume we missed.
- Find a `cli`/`exec` file with `forked_from_id` pointing at another root whose counter
  continues it → a root resume that should be MAX-merged, not summed.
- Confirm `total_token_usage.output_tokens` is monotonic in every file (so MAX=final);
  find a non-monotonic file → MAX may overstate.

### Node 3 — Claude human words (machine-tag allow-list)
Assumptions:
- **A1 (complete list):** `MACHINE_TAGS` in `scripts/verify.py` names *every* machine wrapper; no
  unlisted machine tag leaks in as human; no human content is wrongly dropped.
- **A2 (no mixing):** no `type:user` entry mixes a wrapper block and a human block (so
  entry-level/​block-level filtering loses no human text).
- **A3 (markup kept):** the rule is an allow-list of machine tags, **not** "starts with
  `<`" — humans paste `<p>`/`<div>`/`<style>`.

Falsifiers:
- Histogram the leading tag of *every* `type:user` text block in main files. Any frequent
  tag not in `MACHINE_TAGS` that is clearly machine output → leak (inflates human words).
- Find a human block whose leading tag *is* in `MACHINE_TAGS` (e.g. a human typing
  `<command-name>` in prose) → false drop.
- Find an entry with both a wrapper block and a human block → A2 wrong.

### Node 4 — Codex human words  (re-derived — attack the classifications)
Now pinned at **1,351 turns / 108,027 words**. Method: root threads, `response_item`
`role:user`, drop leading marker in `{turn_aborted, skill, subagent_notification,
environment_context, user_instructions}` or `# AGENTS.md` opener; keep everything else;
**no dedup** (zero resumes + no message id => each kept message is a distinct send;
repeated `yes`/`continue` are real human turns). Assumptions to break:
- **A1 (allow-list complete):** signature-histogram *every* root-thread `role:user` text by
  leading marker, weighted by **word count**. Any high-word signature not in the machine
  list that is clearly machine → leak. Any human content whose leading marker *is* in the
  list → false drop.
- **A2 (the judgment call):** the 10 `#`-heading turns (8,625 words) are kept as human
  ("# Claude / Right. So the CMS is out…"). Read all 10. If any is a machine-injected
  template rather than Brian's prose, it should be dropped.
- **A3 (channel):** we use `response_item` `role:user` (1,769) and ignore
  `event_msg.user_message` (1,351). Confirm no human turn lives *only* in the latter.
- **A4 (kept-by-choice):** pasted agent output + terminal pastes (~4,900 words) are kept
  by the owner's explicit decision. Don't "fix" this — but report the volume so it's a
  conscious inclusion, not a hidden one.

### Node 5 — cwd attribution + reconciliation
Assumptions:
- **A1:** `ROOTS=[~/people, /media/brian/storage/people]`, longest-prefix; L1=person,
  L2=project; cwd bound to the **MAX-token occurrence** carries through dedup.
- **A2 (reconciliation):** 0 ids span >1 person; ≤2 span >1 (person,project). So person
  rollups are exact.
- **A3 (acceptance):** sum of *all* leaves — including `(unrooted)` and `(person-root)` —
  equals the node 1–4 grand totals, for tokens **and** words.

Falsifiers:
- Recompute cross-person / cross-(person,project) id counts independently. Any id crossing
  >1 person breaks exact person reconciliation.
- Build the full leaf table and sum it; assert it equals the grand totals. Any shortfall =
  a silent drop (the thing we most want to prevent).
- Stress the mapper: two `.token-estimator` files claiming overlapping prefixes; a mapper
  path that is a person dir (would swallow sibling projects).

## How to run

```bash
# the bundled harness (our arithmetic) — read it, distrust it, then go around it:
python3 scripts/verify.py            # human report
python3 scripts/verify.py --json     # machine-readable

# then your own probes against:
#   ~/.claude/projects/**/*.jsonl
#   ~/.codex/sessions/**/rollout-*.jsonl
```

Run read-only (`codex exec -s read-only --skip-git-repo-check -C <this dir>`, or your
engine's equivalent). Deliver findings in the schema. Severity by real load on the
report's correctness: a wrong main/sub split is Critical; a few-percent human-word drift
is Minor. End by stating plainly that your ordering and ours may both be wrong — the call
is the human's.
