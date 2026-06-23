# impl-plan-write: research / test / articulate, not manufactured decisions

**Status:** Design validated in conversation 2026-06-23. Not yet fully implemented. Down-payment edits applied this session (see end). Supersedes the per-phase "Review design decisions (three-lens)" review mode.

**Scope:** `plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md`.

## The problem

The "Review design decisions per phase" mode handed the planner a fill-in scaffold for every decision (`Options considered: A/B/C`, `Counterarguments` per option, `(recommended)`, lens labels), gated only by one weak line ("a choice where alternatives existed"). Any settled fact could be dressed as a decision by inventing an alternative to reject. A real run produced DR1 to DR4 where all four were already settled by the design or an acceptance criterion (match the schema; a choice written verbatim in the design; an AC; trivial arithmetic), each wearing an invented-alternative costume and statistician jargon. Performative ceremony without substance.

## The model

### The arc (shape of the work)

An implementation plan is one arc, not a per-phase loop:

1. **What do we know.** Current state: codebase reality plus the design's settled commitments. Established empirically (see channels), once, across the whole plan.
2. **Where are we going.** The design's target end-state: every phase's deliverables and ACs, read as one whole.
3. **How we get there.** The path: phases and tasks. Elaborated in order, because Phase N builds on Phase N-1. This stays sequential (depth-first).
4. **Pull out the judgement calls.** As the path is elaborated, the points where the design is silent and no test or literature settles the choice fall out. They are the residue of elaboration, collected and surfaced as a set, never a per-phase quota.

Depth-first elaboration, breadth-first decision surfacing. One human gate over the few real calls, not eight mostly-empty per-phase gates. This replaces the three review modes.

### Three channels to settle anything (speculation is none of them)

- **Run it** (experiment): testable facts.
- **Read it** (literature): settled field knowledge, external and cited.
- **Ask it** (the human): world-state only the human holds, asked short, plain, specific, critical, and then documented. Asking is always correct provided the fact is genuinely human-held, not a dodge for something testable or readable.

The agent finds out through the right channel. It never substitutes its own vibe for any of the three.

### Three heuristics (the operational core)

- **What to test.** A command settles it now with the same answer for everyone (installs, compiles, resolves, returns X). Signature: you can state "it's wrong if [observable]" and produce that observable in seconds. If a command answers it, running it is mandatory, and cheaper than the sentence that speculates about it. Banned phrase: "one command away from confirmed."
- **What to research.** Settled knowledge a field already holds (JSONB vs table, retry semantics, when to normalise). Signature: "the right way to X" or "X vs Y" with external work that answers it. Find it and cite it; never re-derive it from gut. The literature articulates the tradeoff space externally, which feeds the next heuristic.
- **How to articulate a tradeoff.** Gate first: it is only a tradeoff if it survives testing and research. Test what is testable, research what is known, and most "decisions" collapse to one answer that you simply apply. What remains is a real fork, articulated as:
  - the choice in one plain line (X or Y);
  - each side's costs and buys, every one traced to a test result or a citation (a side resting on "feels cleaner" is vibed, not articulated; go source it);
  - the pivot: the single thing that decides it, almost always a world-state fact only the human holds ("if ratings grow their own fields then table, else JSONB; only you know the roadmap").

  Then the human picks, pivot in hand. Articulation is the agent's labour; the pick is the human's.

### The ping gate

Event-driven, not scheduled. The planner pings the human only for a genuine fork that survives test and research and whose pivot is a human-held world-state fact. Most iterations pass silently. The pinged question is sharp ("I need to know Y"), not "here are two options, thoughts?". For a fully specified design with no research surprises the apparatus collapses to broad strokes, one review, write, zero pings.

### The challengers' net is wider than the planner's

The planner surfaces literature-indicated forks proactively as it researches. The terminal challengers (Claude critical-peer-review and Codex codex-peer-review) flag any load-bearing tradeoff, whether or not the literature ever named it. The gap between the two sets is the buried decisions. A load-bearing decision is a genuine tradeoff that something downstream rests on (tradeoff times downstream reach). Table shape is canonical: no paper names JSONB-vs-table for your schema, so the planner's literature-trigger stays quiet and it gets decided silently; the challengers' wider net is what catches it. The fix for a buried load-bearing decision is usually "justify it from test or literature," not "ask the human."

Decision hotspots the challengers expect:

- **Data model** (table shapes, keys, column vs table vs JSONB)
- **Seams** (sync vs async, transaction boundaries, pure core vs imperative shell)
- **State and lifecycle** (persisted vs derived, ordering, idempotency, partial-failure behaviour)
- **External contracts** (API shapes, serialization, anything other code binds to)
- **Error strategy** (reject vs repair vs defer, where validation sits)

## The workflow

1. **Broad strokes.** "How we hit the goal, roughly," across all phases. Run the buried-decision hunt here too, aimed at foundational and data-model forks, because those are decided early and the whole plan is built on them, so catching them here is cheap.
2. **Deepen, iteration by iteration.** Refine toward full detail. At the end of each iteration: a lighter review (one of critical-peer-review or codex) on that stage, and a ping only for a research-surviving fork.
3. **Terminus.** Deepen until the tests and the UAT are specified.
4. **Full-ceremony review.** Both Claude and Codex, tasked specifically with turning up buried load-bearing decisions. Whatever they surface becomes a fork to put to the human.

## Concrete changes to impl-plan-write

**Cut:** the `Options considered` and `Counterarguments` scaffold; `(recommended)` tags; manufacturing decisions for settled design; lens names used as ritual labels.

**Keep (substance, expressed plainly):** the lenses as analysis, not performance. Popper routes each falsification to either an automated test (`test-requirements.md`) or a human-judgment UAT entry (`uat-requirements.md`); Lakatos fires only on genuine degeneration; Haraway fires only on a genuine invisible cost. The phase-6 test/UAT routing machinery must be preserved. Zero decisions and zero UAT entries are valid outcomes.

**Re-home:** the strengthened gate and the plain decision-plus-implications template (the down-payment edits below) move from the per-phase loop into the arc's "pull out the judgement calls" step.

## Down-payment edits already applied this session

In `impl-plan-write/SKILL.md`:

- Strengthened the gate (step 5) with three disqualifying filters: restatement, invented alternative, obvious default. "Zero decisions is the normal, good outcome."
- Replaced the `Options considered` / `Counterarguments` template with a plain decision plus **What it implies** plus **Where I lean**, keeping the lens lines (Popper routing always; Lakatos and Haraway only when they fire) under plain headers.
- Reframed the step-7 approval example so zero decisions reads as normal, rather than "4 decisions reviewed."

These are structure-agnostic and survive into the arc.

## Open threads

- The full arc (broad strokes, iterative deepening, woven reviews, terminal dual review) is not yet encoded; only the gate and template down-payments are in.
- Intermediate reviews are assumed lighter (one reviewer); the terminal review is both reviewers at full ceremony. Confirm when encoding.
- Lakatos grounding deferred: the 1978 *Methodology of Scientific Research Programmes* PDF in Zotero (`lakatosMethodologyScientificResearch1978`) is a scanned image with no text layer, so pymupdf4llm rendered 256 watermark-only pages. The lens names (Popper, Lakatos, Haraway) are used as labels, not yet re-grounded from source. OCR (`--allow-mocr`) could recover it if wanted.
