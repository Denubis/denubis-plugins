# Test Requirements — Skill-Skills Upstream Sync

Every acceptance criterion from the design plan maps to one of:

- An **automated test** (grep-audit, structural check, Python assertion script, file-existence check)
- A **human-judgement UAT entry** in `uat-requirements.md` (referenced here by DR identifier; **NOT duplicated**)
- An **operational check** (file existence, cross-reference resolution, command exit code)
- **Integration evidence** (for Phase 4 only — the act of producing the artefact IS the evidence per design plan DoD)

Any AC mapping to NEITHER an automated test NOR a UAT entry is flagged as a **COVERAGE GAP**.

---

## Testing model for this plan

Skills in this programme are markdown documents, not runtime code. "Automated tests" here are predominantly:

- **Python assertion scripts** inlined in the phase files' verification Steps. Each script asserts structural properties (frontmatter validity, H2 ordering, presence of required strings, absence of banned strings) and prints a pass message on success.
- **Grep-audits** for verbatim phrases or banned tokens.
- **File-existence checks** via `test -f` / `test -d` / `ls`.
- **Cross-reference resolution** via the Phase 5 Task 1 audit script (`phase_05_cross_ref_audit.py`), which is itself the primary cross-reference test for the plan.

Pytest-style behaviour tests do not apply — there is no code under test beyond `phase_05_cross_ref_audit.py` and `render-graphs.js` (imported verbatim, not a denubis deliverable).

**No integration test — frustration-signal audit instead (H3 revision).** Earlier drafts claimed "Phase 4's production IS the integration evidence," treating the act of producing `writing-skills` + `epistemic-humility` using the three sub-skills as integration verification. The H3 revision dropped this as unfalsifiable (a self-attested narrative audited against self-authored commits). The replacement is AC5.8: Phase 5 Task 4.5 runs `cc-search-chats:search-chat` across all phase-authoring sessions within the plan's implementation window for user-expressed frustration signals; joint human review categorises matches and produces a verdict. DR-P4-INT-1 was deleted; see `uat-requirements.md` Phase 4 section for rationale. `phase_04_green_verification.md` now records sub-skill invocations factually, not as a coherence claim.

**The cross-reference audit script at `phase_05_cross_ref_audit.py` (Phase 5 Task 1) is itself a test.** It is the load-bearing automation for AC5.4, re-runnable, exits 0 on full pass / 1 on any failure.

---

## AC1: `writing-skills` cornerstone rewrite

### AC1.1 — SKILL.md exists with valid YAML frontmatter (name, description present)

- **Type:** Operational check + structural check
- **Test location:** `phase_04.md` Task 2 Step 3 (inline Python script)
- **What it verifies:** File exists at `plugins/denubis-extending-claude/skills/writing-skills/SKILL.md`; frontmatter parses as YAML; `name == 'writing-skills'`; `description` is a string of length > 40.
- **Run command:** Inlined in `phase_04.md` Task 2 Step 3; expected output `SKILL.md cornerstone structural checks passed (line count: N)` with N ≤ 250.

### AC1.2 — SKILL.md line count ≤ 250

- **Type:** Structural check (Python)
- **Test location:** `phase_04.md` Task 2 Step 3 (inline, same script as AC1.1)
- **What it verifies:** `len(content.splitlines()) <= 250`.
- **Run command:** `python3 -c "<inlined in phase_04.md>"`; passes iff line count ≤ 250.

### AC1.3 — SKILL.md cross-references all three sub-skills (epistemic-humility, writing-claude-directives, testing-skills-with-subagents); each resolves to an existing skill directory

- **Type:** Structural check + cross-reference audit
- **Test location:** `phase_04.md` Task 2 Step 3 (presence assertion); `phase_05.md` Task 1 + Task 4 (resolution via `phase_05_cross_ref_audit.py`)
- **What it verifies:** The three `denubis-extending-claude:<skill>` strings are present in SKILL.md (Phase 4); and each resolves to an existing `SKILL.md` under `plugins/denubis-extending-claude/skills/<skill>/` (Phase 5).
- **Run command (Phase 4):** Inlined Python in `phase_04.md` Task 2 Step 3. **Run command (Phase 5):** `python3 docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05_cross_ref_audit.py` — expected `PASS: all cross-references and supporting-file pointers resolve.`

### AC1.4 — Supporting files exist: `anthropic-best-practices.md`, `render-graphs.js`, `examples/CLAUDE_MD_TESTING.md`

- **Type:** Operational check (file existence)
- **Test location:** `phase_04.md` Task 3 Step 3 (anthropic-best-practices.md); `phase_04.md` Task 4 Step 4 (render-graphs.js + README.md); `phase_04.md` Task 5 Step 3 (examples/CLAUDE_MD_TESTING.md)
- **What it verifies:** Each file is present at its target path under `plugins/denubis-extending-claude/skills/writing-skills/`.
- **Run command:** `os.path.exists(path)` assertions inlined in each task's Python verification block; also `test -x` for render-graphs.js executability.

### AC1.5 — Obra-imported files preserve attribution

- **Type:** Grep-audit
- **Test location:** `phase_04.md` Task 3 Step 3 (anthropic-best-practices.md); `phase_04.md` Task 5 Step 3 (examples/CLAUDE_MD_TESTING.md); and for render-graphs.js byte-identicality verified in `phase_04.md` Task 4 Step 2 via `diff -q`.
- **What it verifies:** Each obra import contains `source: obra/superpowers` in its frontmatter (or equivalent attribution line for render-graphs.js preserved as-is from obra).
- **Run command:** `assert 'source: obra/superpowers' in content` — inlined in Python verification blocks for each import task.

### AC1.6 — Commit rejected if any obra-imported file lacks attribution or any cross-reference points at a non-existent skill or file

- **Type:** Cross-reference audit (negative assertion via audit script exit code)
- **Test location:** `phase_05.md` Task 1 + Task 4 (`phase_05_cross_ref_audit.py`)
- **What it verifies:** The Phase 5 audit script walks each imported file and every cross-reference in the five touched skills; exits 1 if any unresolved reference is found. The ~5 phase commits landing without a clean audit run would surface here.
- **Run command:** `python3 docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05_cross_ref_audit.py` — exit code 0 required.

### AC1.7 — `test-requirements.md` for Phase 4 documents RED evidence (static file-shape diff)

- **Type:** Operational check (file existence) + content presence + file-shape baseline
- **Test location:** `phase_04.md` Task 1 Step 3 (phase_04_red_evidence.md committed).
- **What it verifies:** `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_04_red_evidence.md` exists; Phase 4 is a preventive cornerstone rewrite (amended 2026-04-22 plan-amendment pass — original independent-session-failure framing reversed, mirroring Phase 2). Evidence content includes (a) the pre-rewrite `writing-skills/SKILL.md` SHA and line-count baseline, (b) current H2-shape enumeration, (c) target-shape description per Task 2 (≤250 lines, Workflow H2 sequencing three sub-skills, Supporting Files section, rubric callback), and (d) explicit "preventive, not corrective" framing (file shape is a structural observation, not a session-observable failure).
- **Run command:** `test -f docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_04_red_evidence.md` and inspection for (i) pre-rewrite SHA + line-count baseline, (ii) file-shape diff with current vs target H2 list, (iii) preventive-restructure framing statement.

---

## AC2: `testing-skills-with-subagents` restructure

### AC2.1 — RED phase section begins with conversation-precedent protocol, cross-references `cc-search-chats:search-chat`, specifies fresh-session (independent-session) fallback

- **Type:** Structural check (Python)
- **Test location:** `phase_03.md` Task 2 Step 3 (inline Python script)
- **What it verifies:** `Conversation-Precedent` string present; `cc-search-chats:search-chat` cross-reference present; `fresh-session` or `separate chat session` string present; `independent-session` gate framing present.
- **Run command:** Inlined Python assertion block in `phase_03.md` Task 2 Step 3; expected `RED conversation-precedent + Haiku edit structural checks passed`.

### AC2.2 — Synthetic multi-stressor pressure scenarios positioned as REFACTOR-phase completeness checks, not primary RED baseline

- **Type:** Structural check (Python with section boundary parsing)
- **Test location:** `phase_03.md` Task 3 Step 4 (inline Python script)
- **What it verifies:** `## REFACTOR Phase` boundary exists; `Pressure-Scenario Completeness` or `Pressure Types` string appears inside REFACTOR section, not inside RED section; the full 7-pressure table does not appear within RED.
- **Run command:** Inlined Python in `phase_03.md` Task 3 Step 4; expected `pressure-scenario demotion + obra table absorption structural checks passed`.

### AC2.3 — Model-tier guidance, "No Blaming the Model", flaky-result discipline all retained

- **Type:** Grep-audit (Python)
- **Test location:** `phase_03.md` Task 5 Step 1 (preservation audit)
- **What it verifies:** Strings `RED at production` / `tested RED with Sonnet` present; `one tier below` / `one tier down` / `test GREEN with Haiku` present; `No Blaming the Model` H3 present; core phrasing (`the skill is not clear enough` / `the skill is always the problem`) present; `flaky` and `Run it 3 times` / `three times` present.
- **Run command:** Inlined Python in `phase_03.md` Task 5 Step 1; expected `denubis-specific strengths preservation audit passed`.

### AC2.4 — Obra's multi-factor pressure-scenario format absorbed (3+ combined stressors, A/B/C forced choice, concrete options)

- **Type:** Grep-audit (Python)
- **Test location:** `phase_03.md` Task 3 Step 4 (same inline script as AC2.2)
- **What it verifies:** All seven pressure names present within REFACTOR section (`Time`, `Sunk cost`, `Authority`, `Economic`, `Exhaustion`, `Social`, `Pragmatic`); `3+` or `three or more` guidance present. Additionally, the "Key Elements of Good Scenarios" 5-item list is authored per Task 3 Step 3 (concrete options, real constraints, real file paths, make agent act, no easy outs).
- **Run command:** Inlined Python in `phase_03.md` Task 3 Step 4.

### AC2.5 — Rubric callback section present, references `epistemic-humility`

- **Type:** Structural check (Python) + cross-reference audit
- **Test location:** `phase_03.md` Task 4 Step 4 (presence + ordering); `phase_05.md` Task 1/4 (resolution)
- **What it verifies:** `## Rubric Callback` H2 exists; `denubis-extending-claude:epistemic-humility` cross-reference present; position is between `## When to Use` and `## TDD Mapping`; cross-reference resolves via Phase 5 audit.
- **Run command:** Inlined Python in `phase_03.md` Task 4 Step 4; plus `phase_05_cross_ref_audit.py`.

### AC2.6 — Haiku-no-judgement operator-empirical guidance PRESENT in `testing-skills-with-subagents/SKILL.md`; tier-test structural principle preserved (amended 2026-04-22)

- **Type:** Grep-audit (positive assertion for operator-empirical framing; positive assertion for tier-test principle)
- **Test location:** `phase_03.md` Task 2 Step 3 (inline Python)
- **What it verifies:** A passage citing `Haiku 4.5` together with a judgement term (`judgement`/`judgment`), an operator/empirical anchor, and a strong negation (`unsuitable`/`never`) is PRESENT. `weakest` tier-phrasing PRESENT. Amended 2026-04-22 plan-amendment pass — prior framing required the pre-amendment phrase "struggles with judgement" to be ABSENT; the amended framing requires the operator-empirical guidance to be PRESENT (pre-amendment phrasing may also be retained inside the reframed passage, which is fine). Operator position overrides Anthropic's 2026-04 marketing framing.
- **Run command:** Inlined Python assertion block in `phase_03.md` Task 2 Step 3.

### AC2.7 — `test-requirements.md` for Phase 3 documents RED evidence from an independent session

- **Type:** Operational check (file existence) + content presence + independent-session provenance
- **Test location:** `phase_03.md` Task 1 Step 4 (phase_03_red_evidence.md committed)
- **What it verifies:** `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_03_red_evidence.md` exists on disk with the RED evidence structure (source, session reference, SKILL.md SHA tested against, observed failure, direct quote(s), deficiency-location analysis, how Phase 3 addresses). Source must be a session that is NOT the implementing executor — either a cc-search-chats transcript or a user-run fresh-session transcript. cc-search-chats queries are FTS5-safe single-term (2026-04-22 plan-amendment pass: ISSUE-10 constraints applied, mirroring M2's Phase 5 treatment). Phase 3 remains corrective (Phase 2 and Phase 4 went to static-evidence RED in the same amendment pass; Phase 3 did not) — the skill's target methodology is explicitly transcript-sourcing, so transcripts are expected to land.
- **Run command:** `test -f docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_03_red_evidence.md` and inspection for independent-session provenance.

---

## AC3: `writing-claude-directives` restructure

### AC3.1 — SKILL.md does not contain an Opus 4.5 "Think Sensitivity" section

- **Type:** Grep-audit (negative assertion, Python)
- **Test location:** `phase_02.md` Task 2 Step 5 (inline Python)
- **What it verifies:** Strings `Opus 4.5`, `Think Sensitivity`, `Think' Sensitivity` all ABSENT from SKILL.md.
- **Run command:** Inlined Python in `phase_02.md` Task 2 Step 5; expected `SKILL.md structural checks passed`.

### AC3.2 — `model-tier-notes.md` exists with separate Opus 4.7 / Sonnet 4.6 / Haiku 4.5 sections; each has ≥1 citation URL to 2026 Anthropic documentation

- **Type:** Structural check (Python) + URL presence grep
- **Test location:** `phase_02.md` Task 3 Step 3 (inline Python)
- **What it verifies:** Dated-header string present; `2026-04-17` present; three H2 sections `## Opus 4.7`, `## Sonnet 4.6`, `## Haiku 4.5` present; the three canonical `anthropic.com/news/claude-*-4-*` URLs present; `xhigh` effort-level mention present (DR5); retirement of old Haiku-judgement claim documented; model IDs `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001` all present.
- **Run command:** Inlined Python in `phase_02.md` Task 3 Step 3; expected `model-tier-notes.md structural checks passed`.

### AC3.3 — No `persuasion-principles.md` file imported into `writing-claude-directives/`

- **Type:** Operational check (file-absence via `os.path.exists`)
- **Test location:** `phase_02.md` Task 2 Step 5 verification script (updated 2026-04-17 — see framing correction below)
- **What it verifies:** `plugins/denubis-extending-claude/skills/writing-claude-directives/persuasion-principles.md` does NOT exist on disk — the file-absence claim is enforced directly, not inferred from content-grep of another file
- **Run command:** Inlined Python in Task 2 Step 5: `assert not os.path.exists(persuasion_path)`

**Framing correction (2026-04-17):** The initial test-analyst report described AC3.3 as "covered-in-practice by AC3.4's Cialdini/Meincke grep + Phase 5 cross-reference audit." That framing was circular (AC3.4's grep was itself named by the user as what should be expunged — "Why are you grepping for that?") and rested on a false assumption: that a content-grep-for-banned-strings in SKILL.md can substitute for file-absence verification of a different file. AC3.3 now has a direct `os.path.exists` check, and AC3.4's content-grep has been removed entirely.

### AC3.4 — SKILL.md contains no Cialdini/Meincke/persuasion-principles section

- **Type:** Structural consequence of AC3.3
- **Test location:** No direct test — AC3.4 follows from AC3.3 by construction
- **What it verifies:** If the persuasion-principles.md source file does not exist (AC3.3), authoring a section in SKILL.md that cites it would be nonsensical. AC3.4 is therefore not defended against via content-grep but via AC3.3's file-absence check.
- **Run command:** None (structural consequence of AC3.3)

**Framing correction (2026-04-17):** Previously enforced by `for banned in ['Cialdini', 'Meincke', 'persuasion principles']: assert banned not in content`. That content-grep was removed because (a) it asserted absence by repeatedly naming the forbidden strings in the verification code, which undermines the "expunge" decision; (b) the user's question "Why are you grepping for that?" surfaced the smell; (c) if the source file does not exist (AC3.3), a citing section is structurally implausible and does not need separate defending. Absence-by-construction replaces absence-by-content-grep.

### AC3.5 — `graphviz-conventions.dot` reconciled against obra's version; reconciliation documented

- **Type:** Operational check (byte-identicality via `diff -q`) + grep-audit for attribution line
- **Test location:** `phase_02.md` Task 4 Steps 1 + 3 (reconciliation verify + attribution grep)
- **What it verifies:** `diff -q /tmp/superpowers-obra/skills/writing-skills/graphviz-conventions.dot <denubis-copy>` produces no output (byte-identical except attribution comment, which is non-semantic); `grep -c 'obra/superpowers'` returns ≥ 1. Commit message documents the no-op reconciliation.
- **Run command:** `diff -q ...`; `grep -c 'obra/superpowers' plugins/denubis-extending-claude/skills/writing-claude-directives/graphviz-conventions.dot`.

### AC3.6 — Rubric callback section present, references `epistemic-humility`

- **Type:** Grep-audit (Python) + cross-reference audit
- **Test location:** `phase_02.md` Task 2 Step 5 (inline Python); `phase_05.md` Task 1/4 (resolution)
- **What it verifies:** `epistemic-humility` string present; `denubis-extending-claude:epistemic-humility` cross-reference present with correct format; cross-reference resolves under Phase 5 audit.
- **Run command:** Inlined Python in `phase_02.md` Task 2 Step 5; plus `phase_05_cross_ref_audit.py`.

### AC3.7 — No claim cites Opus 4.5 or Sonnet 4.5 as current (both superseded); every model-specific claim has explicit current model-version anchor (H6 revision: scope extended to supporting files)

- **Type:** Grep-audit (partial automation) + UAT-in-`uat-requirements.md`
- **Test location (automatable part):** `phase_02.md` Task 2 Step 5 (Opus 4.5 absence in SKILL.md) + `phase_02.md` Task 3 Step 3 (per-model H2 anchors in `model-tier-notes.md`) + `phase_02.md` Task 3.5 Step 3 (`Opus 4.5` / `Sonnet 4.5` / `Claude 4.5+` absent from `long-running-state-patterns.md`, `Opus 4.7` / `Sonnet 4.6` present, `Haiku 4.5` preserved)
- **Test location (non-automatable part):** UAT entry `DR-P2-DR3` in `uat-requirements.md` covers whether the updated aggressive-language guidance actually changes authoring behaviour (broader but adjacent verification).
- **What it verifies:** `Opus 4.5` and `Sonnet 4.5` ABSENT across restructured SKILL.md, `model-tier-notes.md`, AND `long-running-state-patterns.md`; `Opus 4.7` + `Sonnet 4.6` + `Haiku 4.5` PRESENT as the current model anchors; supporting files have dated headers + source URLs.
- **Run command:** Inlined Python in `phase_02.md` Task 2 Step 5 + Task 3 Step 3 + Task 3.5 Step 3.

### AC3.8 — `test-requirements.md` for Phase 2 documents RED evidence (static code-smell inventory) and the Anthropic PDF consumption

- **Type:** Operational check (file existence) + content presence + system-card cross-verification narrative in phase_02_red_evidence.md and implicitly in model-tier-notes.md authoring
- **Test location:** `phase_02.md` Task 1 Step 4 (phase_02_red_evidence.md); `phase_02.md` Task 3 Step 2 (system-card PDF consumption)
- **What it verifies:** `phase_02_red_evidence.md` exists; Phase 2 is a preventive restructure (amended 2026-04-22 plan-amendment pass — original independent-session-failure framing reversed). Evidence content includes (a) the Phase 2B investigator code-smell inventory (SKILL.md line 215-220 stale Opus 4.5 section, lines 69/96/99/237 generic 4.x anchors, long-running-state-patterns.md stale 4.5 anchors) with file-SHA anchors and (b) the 2026-04-22 independent-session search record (FTS5-safe queries, projects covered, 0 qualifying transcripts found). System-card PDF was consumed during authoring (`pdftotext` or `Read` tool with `pages` parameter invoked per Step 2) and no claim in `model-tier-notes.md` contradicts the system card.
- **Run command:** `test -f docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_02_red_evidence.md` and inspection for (i) code-smell inventory with file-SHA anchors, (ii) independent-session search record with FTS5-safe query list and 0-result finding; system-card consumption recorded as inspection step during Task 3 execution.

---

## AC4: `epistemic-humility` reference skill

### AC4.1 — SKILL.md exists with reference-type frontmatter (description keyed to scope-assessment triggers)

- **Type:** Operational check + structural check (Python, YAML)
- **Test location:** `phase_01.md` Task 1 Step 3 (inline Python)
- **What it verifies:** File starts with `---\n`; frontmatter parses; `name == 'epistemic-humility'`; `description` is a string of length > 60; `user-invocable is False`.
- **Run command:** Inlined Python in `phase_01.md` Task 1 Step 3; expected `frontmatter OK`.

### AC4.2 — Rubric has four sections: Scope, Observability, Process, Failure-pattern screen

- **Type:** Structural check (Python, H2 ordering)
- **Test location:** `phase_01.md` Task 1 Step 4 (inline Python)
- **What it verifies:** The four rubric H2s are present AND appear in the design-locked order (`## Scope` → `## Observability` → `## Process` → `## Failure-pattern screen`).
- **Run command:** Inlined Python in `phase_01.md` Task 1 Step 4; expected `rubric sections present and in order`.

### AC4.3 — Every cited claim is attributable to `AbsenceJudgement.tex` or a named secondary source

- **Type:** Grep-audit (Python) on citations file
- **Test location:** `phase_01.md` Task 2 Step 2 (line-number references) + Task 2 Step 3 (verbatim phrases)
- **What it verifies:** Required line-number refs from AbsenceJudgement.tex (`203`, `252`, `794`, `785`, `789`, `801`, `810`, `819`, `868`, `261`) all present in `absencejudgement-citations.md`; required verbatim phrases (`bounded, auditable, and reversible`; `scope/confabulation`; `stamp-collecting without evaluation`; `vibes-based operation`; `mechanical, bounded, low-judgement`; `heavy scaffolding`; `technoscholasticism`; `Can I solve the problem I have set`) all present.
- **Run command:** Two inlined Python blocks in `phase_01.md` Task 2 Steps 2 and 3; expected `all required line references present` and `all required verbatim phrases present`.

### AC4.4 — No TEMP/RAND/SCOP/VIBE/FABR/MECH/MTCH/SCAF/BOUN mentions outside explicit rejection context

- **Type:** Word-boundary grep-audit
- **Test location:** `phase_01.md` Task 4 Step 1
- **What it verifies:** For each of the nine codes, `grep -Hn -w <code>` across the whole skill directory reports either zero hits or hits only within SKILL.md's "Note on fabricated taxonomy" section. Any hit in `absencejudgement-citations.md` or `self-application.md` is a DR4 violation requiring rewrite.
- **Run command:** `for code in TEMP RAND SCOP VIBE FABR MECH MTCH SCAF BOUN; do grep -Hn -w "$code" plugins/denubis-extending-claude/skills/epistemic-humility/ -r || echo "  (zero hits)"; done` — inlined in `phase_01.md` Task 4 Step 1. Manual review of any hit for rejection-context.

### AC4.5 — Rubric self-application walk-through exists; surfaced vulnerabilities acknowledged by user (H4 revision: not pass/fail)

- **Type:** Structural check (Python) + **UAT entry** `DR-AC4.5` in `uat-requirements.md` for the vulnerability-review step
- **Test location (structural):** `phase_01.md` Task 3 Step 2 (inline Python) — asserts four H2s present and at least one `honesty` / `tautology` / `vulnerab` marker present in `self-application.md`. **Test location (judgement):** UAT entry `DR-AC4.5 — Self-application walk-through and vulnerability acknowledgement` in `uat-requirements.md`.
- **What it verifies (automated part):** `self-application.md` contains the four rubric H2s and at least one named reflective vulnerability (string-level proxy — zero named vulnerabilities means the walk-through didn't probe).
- **What it verifies (UAT part):** The walk-through genuinely probes the rubric vs rubber-stamps it; any surfaced vulnerability was raised to the user and acknowledged (or explicitly routed to remediation) before GREEN was committed. The H4 revision makes clear this is a walk-through commitment + vulnerability-surfacing requirement, NOT a pass/fail gate. Retrospective backstop: Phase 5 Task 4.5 frustration-signal audit (AC5.8) would catch rationalised walk-throughs where vulnerabilities didn't surface at the time but the user's frustration did later.
- **Run command (automated):** Inlined Python in `phase_01.md` Task 3 Step 2; expected `self-application walk-through structurally valid`. **UAT:** human judgement per entry.

---

## AC5: cross-cutting — version sync, cross-reference audit, commit discipline

### AC5.1 — `denubis-extending-claude/.claude-plugin/plugin.json` version incremented

- **Type:** Structural check (Python, JSON parse)
- **Test location:** `phase_05.md` Task 2 Step 4 (inline Python)
- **What it verifies:** `plugin.json['version'] == '1.8.0'` (the target bump from 1.7.0).
- **Run command:** Inlined Python in `phase_05.md` Task 2 Step 4; expected `denubis-extending-claude 1.8.0 triad synchronised`.

### AC5.2 — `.claude-plugin/marketplace.json` at repo root contains matching version for `denubis-extending-claude`

- **Type:** Structural check (Python, JSON parse)
- **Test location:** `phase_05.md` Task 2 Step 4 (same inline Python as AC5.1)
- **What it verifies:** Marketplace `denubis-extending-claude` entry has `version == '1.8.0'`, matching plugin.json.
- **Run command:** Same inlined Python in `phase_05.md` Task 2 Step 4.

### AC5.3 — `CHANGELOG.md` contains new entry under `[denubis-extending-claude]` heading at the appropriate version

- **Type:** Grep-audit (Python)
- **Test location:** `phase_05.md` Task 2 Step 4 (same inline Python as AC5.1/5.2)
- **What it verifies:** `## [denubis-extending-claude] 1.8.0` heading present in CHANGELOG.md; entry follows the New/Changed/Fixed format per CLAUDE.md convention.
- **Run command:** Same inlined Python in `phase_05.md` Task 2 Step 4.

### AC5.4 — Cross-reference audit: every cross-skill invocation and path-form supporting-file reference resolves

- **Type:** Cross-reference audit (dedicated Python script — **the primary test for the plan**)
- **Test location:** `phase_05.md` Task 1 (script authored + `--dump-matches` pre-audit spot check, Steps 1-3) + `phase_05.md` Task 4 (final re-run)
- **What it verifies** (path-form convention, H1 revision 2026-04-19): `phase_05_cross_ref_audit.py` walks all five sync-touched skills and checks three reference classes:
  1. **Cross-skill invocations** — `` `denubis-<plugin>:<name>` `` — resolve via `resolve_xref`, which tries `plugins/<plugin>/skills/<name>/SKILL.md`, then `plugins/<plugin>/agents/<name>.md`, then `plugins/<plugin>/commands/<name>.md` (first hit wins). This covers skills, agents, and commands uniformly.
  2. **Path-form supporting-file references** — backticked string containing at least one `/` (e.g., `` `./model-tier-notes.md` ``, `` `docs/architecture/dfd/0-context.md` ``, `` `src/foo.py:42-58` ``) with optional `:N` or `:N-M` line-range suffix. Relative paths (`./`, `../`) resolve against the md file's directory; all others against repo root.
  3. **Markdown-link references** — `[text](path/to/file.md)` with optional `#anchor`.

  Bare backticked filenames (e.g., `` `config.py` `` — no `/`) are treated as prose vocabulary and **not audited** — this is the path-form convention that dropped the illustrative-filename false-positive class in H1 revision. Teaching-material placeholders use angle-bracket prefix (`` `<your-service>/auth.py` ``) so `<` as first char fails the character class and the placeholder is not audited. Conditional references (deliberately optional paths — "if file exists, use it") are enumerated in the script's `CONDITIONAL_PATHS` frozenset and silently skipped. Exit codes: 0 full pass, 1 broken references, 2 missing target directory.

- **Pre-audit command** (Task 1 Step 2): `python3 docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05_cross_ref_audit.py --dump-matches` — expected list of `MATCH [kind] path:line — [OK|BROKEN] <reference>` lines; zero entries for prose-vocabulary (bare) backticked filenames; every legitimate cross-reference appears `[OK]`.
- **Run command** (Task 1 Step 3 + Task 4 final re-run): `python3 docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05_cross_ref_audit.py` — expected `PASS: all cross-references and supporting-file pointers resolve.`

### AC5.5 — No commit uses `--no-verify`, `--amend` of prior plan commit, or any forced operation

- **Type:** Operational check (manual git log inspection with heuristic)
- **Test location:** `phase_05.md` Task 4 Step 2 (preceded by branch-discipline guard — M5 revision 2026-04-19)
- **What it verifies:** `git log --oneline main..HEAD` shows ≥ 31 commits with no evidence of amend (no duplicate short-SHAs across reflog vs log) and no forced operations. `--no-verify` is not recorded in git but is a discipline check enforced at commit time. (Count reconciled during H6 revision 2026-04-19: Phase 5 gained Task 4.5 frustration-signal audit in H3 revision (+1); Phase 6 gained Task 6 illustrative-path rewrite in H1 revision (+1). Prior ≥27/≥28 claims were stale.) **Branch-discipline precondition (M5 revision 2026-04-19):** Task 4 Step 2 runs a guard first that halts if `git branch --show-current` returns `main`, `master`, or empty — `git log main..HEAD` would otherwise silently return zero commits on main and falsely pass AC5.5/5.6 against an empty set. `denubis-plan-and-execute:executing-an-implementation-plan` already blocks execution on main at the plan-entry point; the inline guard is the local belt-and-braces at the point the count is actually taken.
- **Run command:** Branch-discipline guard (see `phase_05.md` Task 4 Step 2); then `git log --oneline main..HEAD | head -40`; `git log --oneline main..HEAD | wc -l`; `git reflog origin/main` (if applicable). Manual discipline inspection.

### AC5.6 — Commits split per user's global preference (3+ files → 2+ commits by natural concern); tests and implementation for a given phase share commits

- **Type:** Operational check (manual git log inspection)
- **Test location:** `phase_05.md` Task 4 Step 2 (manual verification checklist; preceded by branch-discipline guard — M5 revision 2026-04-19)
- **What it verifies:** Commit history matches the per-phase commit counts documented in Phase 5's DoD: Phase 1 (3+), Phase 2 (5+), Phase 2.5 (1+ per smell), Phase 3 (5+), Phase 4 (6+), Phase 5 (5 — includes Task 4.5 frustration-signal audit), Phase 6 (6+ — includes Task 6 illustrative-path rewrite) → **≥ 31 total**. No giant single commit mixing unrelated files. Same M5 branch-discipline guard applies — if the guard trips, execution halts before the count is read.
- **Run command:** Branch-discipline guard (see `phase_05.md` Task 4 Step 2); then `git log --oneline main..HEAD`; manual inspection against the Phase 5 Task 4 Step 2 checklist.

### AC5.7 — `denubis-plan-and-execute` version bump + marketplace.json + CHANGELOG.md entry (extended scope for Phase 6)

- **Type:** Structural check (Python, JSON parse + grep)
- **Test location:** `phase_05.md` Task 3 Step 4 (inline Python)
- **What it verifies:** `plugin.json['version'] == '2.31.0'` (bumped from 2.30.0); marketplace.json `denubis-plan-and-execute` entry has matching `version == '2.31.0'`; CHANGELOG.md contains `## [denubis-plan-and-execute] 2.31.0` heading; newest-first ordering preserved — 2.31.0 entry appears before the denubis-extending-claude 1.8.0 entry (cross-plugin) AND before the existing denubis-plan-and-execute 2.30.0 entry (same-plugin, L3 revision 2026-04-19).
- **Run command:** Inlined Python in `phase_05.md` Task 3 Step 4; expected `denubis-plan-and-execute 2.31.0 triad synchronised`.

### AC5.8 — Frustration-signal audit executed across all phase-authoring sessions (added during H3 revision)

- **Type:** Automatable query + file-existence (automatable portion) + joint human-review categorisation (routed to UAT entry `DR-P5-FRUST-1`)
- **Test location:** `phase_05.md` Task 4.5 (all Steps 1-5)
- **What it verifies (automatable portion):**
  - `phase_05_frustration_audit.md` exists at the plan directory
  - File records the time-window start/end timestamps (Step 1 output)
  - File records each frustration-signal query run and its match count (Step 2 output)
  - File records each match with session ID, timestamp, and ±5 messages of surrounding context (Step 2 output)
  - File records a category for each match: GENUINE-FRUSTRATION / TECHNICAL-DISAGREEMENT / QUOTED-ILLUSTRATIVE (Step 3 output; M3 revision 2026-04-19 dropped the prior RESOLVED-IN-SESSION category — frustration is the signal regardless of whether the session later self-corrected)
  - File records the fatigue-floor state: if the match list exceeded 30, the sitting-cutoff timestamps and resume timestamps are logged (Step 3 guardrail 1, Meta-M7 revision 2026-04-19)
  - File records the calibration-check outcome: the three-per-category blinded sample list, the reviewer's recategorisation of each sample, the disagreement count, and whether the calibration passed (≤1 disagreement) or failed (>1) (Step 3 guardrail 2, Meta-M7 revision 2026-04-19)
  - File records a verdict: audit-passes OR audit-flags OR audit-flags-calibration-failed (Step 4 output)
  - If verdict is audit-flags, each flagged match has a per-phase AC-coverage-downgrade note (Step 4 output)
- **Run command:** `test -f docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05_frustration_audit.md` + inspection for the seven sub-items above.
- **What is NOT automatable:** The category assigned to each match (see UAT entry `DR-P5-FRUST-1`).
- **Re-runnability:** The cc-search-chats queries are deterministic; a later reviewer can re-run them against the same time window and compare matches. The verdict step depends on human judgement; if the user re-categorises, the verdict may change.

---

## AC6: `impl-plan-write` anti-smuggling hardening (cross-plugin)

### AC6.1 — DR template mandates `**What's automatable:**` / `**What's NOT automatable:**` lines before falsification block

- **Type:** Grep-audit (Python)
- **Test location:** `phase_06.md` Task 2 Step 3 (inline Python)
- **What it verifies:** Strings `What's automatable` AND `What's NOT automatable` both present in `impl-plan-write/SKILL.md`.
- **Run command:** Inlined Python in `phase_06.md` Task 2 Step 3; expected `Task 2 structural checks passed`.

### AC6.2 — `UAT Requirements Collation` section (SKILL.md line 1285) gains audit step (dedicated subagent runs three anti-smuggling tests before file is written)

- **Type:** Grep-audit (Python)
- **Test location:** `phase_06.md` Task 4 Step 3 (inline Python)
- **What it verifies:** Strings `Collation audit`, `denubis-basic-agents:sonnet-general-purpose`, `Second defensive layer` all present in `impl-plan-write/SKILL.md`.
- **Run command:** Inlined Python in `phase_06.md` Task 4 Step 3; expected `Task 4 structural checks passed`.

### AC6.3 — Template change accompanied by worked example: smuggled entry refused + adapted genuine entry shown

- **Type:** Grep-audit (Python)
- **Test location:** `phase_06.md` Task 2 Step 3 (same inline Python as AC6.1)
- **What it verifies:** Strings `Smuggled entry (REJECT)`, `Genuine UAT entry (ACCEPT)`, `Zero-UAT output` all present in `impl-plan-write/SKILL.md`.
- **Run command:** Inlined Python in `phase_06.md` Task 2 Step 3.

### AC6.4 — CUT during M2 revision (2026-04-18)

Earlier drafts of AC6.4 specified a forward-enforcement audit script (`audit-uat-template-compliance.sh`) that was supposed to walk post-Phase-6 plan directories and check each `uat-requirements.md` for the gate-form template lines. Critical peer review (M2) flagged the mechanism as rubric-as-text: the script lived as a fenced bash block inside `impl-plan-write/SKILL.md`, was never extracted to disk, and "coverage" was `grep -q 'audit-uat-template-compliance'` against the SKILL.md — the script's *name* being mentioned, not the script running.

The M2 revision cut AC6.4 entirely rather than promote it to real enforcement (which would have required a repo-level script + hook wiring + a CI step, none of which were in scope). Forward-template compliance for future plans now rests on the in-loop gates that DO have forcing-function discipline:

- **AC6.1** — template mandate in `impl-plan-write`'s DR workflow (structural: template change lives in the skill that future planners use)
- **AC6.2** — collation audit at the UAT Requirements Collation section (SKILL.md line 1285) runs every entry through the three anti-smuggling tests via a dedicated subagent before `uat-requirements.md` is written
- **AC6.8** — Finalization existence gate prevents silent-skip of UAT collation

Plans that bypass `impl-plan-write` entirely (e.g., hand-authored plans that don't use the skill) are out of scope — no gate can enforce a skill's template on authors who don't use the skill.

### AC6.5 — `uat-requirements.md` in this plan retroactively audited against the three anti-smuggling tests

- **Type:** **UAT-adjacent audit via dedicated subagent** + operational check (file existence)
- **Test location:** `phase_06.md` Task 5 (dispatch Sonnet subagent, write `uat-audit-2026-04-17.md`)
- **What it verifies:** `uat-audit-2026-04-17.md` exists in plan directory with per-entry Decomposition / Reduction / Disagreement scores; any FAIL entries are rewritten in place in `uat-requirements.md` with `<!-- PROVENANCE: rewritten 2026-04-17 ... -->` HTML comments.
- **Run command:** `test -f docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/uat-audit-2026-04-17.md`; subagent dispatch recorded in Task 5 Step 1. No single-line script — audit is agent-mediated by design.

### AC6.6 — Per-phase ND pre-presentation self-audit inserted before AskUserQuestion (step 6.5)

- **Type:** Structural check (Python)
- **Test location:** `phase_06.md` Task 3 Step 3 (inline Python)
- **What it verifies** (M6 revision 2026-04-18: reframed from "authoring-time rejection gate" to "pre-presentation self-audit" — the structural anti-smuggling gate is now Task 4 Collation audit, not this step 6.5 self-audit): Strings `Pre-presentation self-audit`, `Decomposition test`, `Reduction test`, `Disagreement test` all present in `impl-plan-write/SKILL.md`; positional check that `audit_pos < step7_pos`; reference to the Task 4 collation audit present (case-insensitive `collation audit` or literal `UAT Requirements Collation`), establishing the self-audit's structural backstop.
- **Run command:** Inlined Python in `phase_06.md` Task 3 Step 3; expected `Task 3 structural checks passed`.

### AC6.7 — Three-lens table amended: "no UAT entry" is first-class output

- **Type:** Grep-audit (Python)
- **Test location:** `phase_06.md` Task 1 Step 3 (inline Python)
- **What it verifies:** Strings `Zero UAT entries is a first-class valid outcome` AND `no UAT entry` both present in `impl-plan-write/SKILL.md`.
- **Run command:** Inlined Python in `phase_06.md` Task 1 Step 3; expected `three-lens table amendment verified`.

### AC6.8 — Finalization DoD requires `uat-requirements.md` to exist at PLAN_DIR

- **Type:** Grep-audit (Python)
- **Test location:** `phase_06.md` Task 4 Step 3 (same inline Python as AC6.2)
- **What it verifies:** Strings `Finalization cannot complete until`, `uat-requirements.md`, `No human-judgment UAT entries` (minimal-form template) all present in `impl-plan-write/SKILL.md`.
- **Run command:** Inlined Python in `phase_06.md` Task 4 Step 3.

---

## Phase 2.5: preparatory-refactor

Phase 2.5 has `Verifies: None` — it is a preparatory refactor enabling Phase 3. Its success criterion (behaviour preservation across structural split) is verified by Phase 3's ability to execute its tasks without tripping on monolithic-section surgery.

**Coverage approach:** Phase 2.5's Done-when conditions (H3 subsections extracted; verbatim blocks byte-identical; no content added or removed) are verified via:

- **Grep-audit** for preserved denubis-specific blocks (model-tier, No Blaming the Model, flaky-result discipline) — same checks as AC2.3, which Phase 3 Task 5 Step 1 runs.
- **Diff comparison** against pre-Phase-2.5 baseline — Phase 2.5's DoD notes this as an optional sanity check (`phase_03.md` Task 5 Step 2).
- **Pipeline checkpoint file** `phase_02_5_smell_checkpoint.md` exists with smell-assessor + critical-peer-review sections (operational file-existence check per phase_02_5.md DoD).

No ACs map directly to Phase 2.5 — by design, this is preparatory refactoring, not new functionality. **Not a coverage gap** because the design plan explicitly sets `Verifies: None` for this phase.

---

## Phase 4: no integration test — frustration-signal audit replaces the integration-evidence claim (H3 revision)

**Framing dropped during H3 revision.** Earlier drafts claimed "Phase 4's production IS the integration evidence" — extrapolated from the brainstorming-time direction that today is a refactoring day, not integration-test day. The extrapolation was unfalsifiable: the written narrative could be perfect while the lived authoring skipped the methodology; the commit history shares an author with the narrative, so "commits should tell the same story as the GREEN file" is a self-attested claim.

**What Phase 4 actually produces:**

1. `phase_04_green_verification.md` exists (Phase 4 Task 6 Step 4) with a closing "Sub-skill Invocations" section naming which Phase 1-3 outputs were exercised and how. This is a factual record of invocations, not a claim of integration-evidence coherence.
2. The rubric (Phase 1) was applied during Phase 4 authoring (Task 6 Step 3 rubric self-application documented).

**What replaces the unfalsifiable claim:** Phase 5 Task 4.5 — the **frustration-signal audit** (AC5.8). Runs `cc-search-chats:search-chat` across all phase-authoring sessions within the plan's implementation window, collects matches on user-expressed frustration signals, and produces a joint human-review categorisation. Falsifiable, re-runnable, and grounded in the user's interaction transcript (an independent record the executor cannot self-author). See AC5.8 test entries below for the automatable portion; UAT entry `DR-P5-FRUST-1` in `uat-requirements.md` covers the human-judgement categorisation step.

**Deleted:** UAT entry `DR-P4-INT-1` (see `uat-requirements.md` Phase 4 section for the deletion rationale).

---

## The cross-reference audit script: role and provenance

**`docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05_cross_ref_audit.py`** is the load-bearing automation for this plan's cross-reference correctness. It:

- Enumerates the five sync-touched skills (`writing-skills`, `writing-claude-directives`, `testing-skills-with-subagents`, `epistemic-humility`, `impl-plan-write`)
- Regexes every `denubis-<plugin>:<skill>` invocation across every `.md` file in each skill
- Verifies each invocation resolves to an existing `SKILL.md` at `plugins/<plugin>/skills/<skill>/SKILL.md`
- Regexes every `` `*.md/js/dot/py/sh/txt` `` filename reference in backticks and verifies it exists in the same skill directory (or is a known exempt generic filename, or is an obra-internal filename listed in `OBRA_SKIP`)
- Exits 0 on full pass, 1 on any failure

Its role as a test:

- Primary verification for **AC5.4** (cross-reference audit)
- Supporting verification for **AC1.3** (cross-references to three sub-skills resolve), **AC1.6** (commits with unresolved references would fail this audit), **AC2.5** and **AC3.6** (rubric-callback cross-references resolve)
- Re-runnable throughout development and after any edit to any of the five skills

---

## Coverage summary

| AC | Type | Covered by | Status |
|---|---|---|---|
| AC1.1 | structural-check | phase_04.md T2 S3 | covered |
| AC1.2 | structural-check | phase_04.md T2 S3 | covered |
| AC1.3 | structural-check + cross-ref audit | phase_04.md T2 S3 + phase_05_cross_ref_audit.py | covered |
| AC1.4 | file-existence | phase_04.md T3/T4/T5 | covered |
| AC1.5 | grep-audit | phase_04.md T3 S3, T5 S3; T4 S2 diff | covered |
| AC1.6 | cross-ref audit (negative) | phase_05_cross_ref_audit.py | covered |
| AC1.7 | file-existence | phase_04.md T1 S4 | covered |
| AC2.1 | structural-check | phase_03.md T2 S3 | covered |
| AC2.2 | structural-check | phase_03.md T3 S4 | covered |
| AC2.3 | grep-audit | phase_03.md T5 S1 | covered |
| AC2.4 | grep-audit | phase_03.md T3 S4 | covered |
| AC2.5 | structural-check + cross-ref audit | phase_03.md T4 S4 + phase_05_cross_ref_audit.py | covered |
| AC2.6 | grep-audit | phase_03.md T2 S3 | covered |
| AC2.7 | file-existence | phase_03.md T1 S4 | covered |
| AC3.1 | grep-audit | phase_02.md T2 S5 | covered |
| AC3.2 | structural-check + grep-audit | phase_02.md T3 S3 | covered |
| AC3.3 | file-absence (`os.path.exists`) | phase_02.md T2 S5 (updated 2026-04-17) | covered (direct check; prior "covered-in-practice" framing was circular — see per-AC note) |
| AC3.4 | structural consequence of AC3.3 | none (content-grep removed 2026-04-17) | covered (by construction — see per-AC note) |
| AC3.5 | operational (diff + grep) | phase_02.md T4 S1/S3 | covered |
| AC3.6 | grep-audit + cross-ref audit | phase_02.md T2 S5 + phase_05_cross_ref_audit.py | covered |
| AC3.7 | grep-audit + UAT adjacent | phase_02.md T2 S5 + T3 S3 + T3.5 S3 + uat-requirements.md DR-P2-DR3 | covered (H6 revision: scope extended to supporting files — SKILL.md + model-tier-notes.md + long-running-state-patterns.md) |
| AC3.8 | file-existence + narrative | phase_02.md T1 S4 + T3 S2 | covered |
| AC4.1 | structural-check | phase_01.md T1 S3 | covered |
| AC4.2 | structural-check | phase_01.md T1 S4 | covered |
| AC4.3 | grep-audit | phase_01.md T2 S2/S3 | covered |
| AC4.4 | grep-audit | phase_01.md T4 S1 | covered |
| AC4.5 | structural-check + UAT | phase_01.md T3 S2 + uat-requirements.md DR-AC4.5 | covered |
| AC5.1 | structural-check | phase_05.md T2 S4 | covered |
| AC5.2 | structural-check | phase_05.md T2 S4 | covered |
| AC5.3 | grep-audit | phase_05.md T2 S4 | covered |
| AC5.4 | cross-ref audit script | phase_05_cross_ref_audit.py | covered |
| AC5.5 | operational (git log inspection) | phase_05.md T4 S2 | covered |
| AC5.6 | operational (git log inspection) | phase_05.md T4 S2 | covered |
| AC5.7 | structural-check + grep-audit | phase_05.md T3 S4 | covered |
| AC5.8 | cc-search-chats query + file-existence + UAT | phase_05.md T4.5 + uat-requirements.md DR-P5-FRUST-1 | covered (added during H3 revision; replaces deleted DR-P4-INT-1 which attempted to audit an unfalsifiable integration-evidence claim) |
| AC6.1 | grep-audit | phase_06.md T2 S3 | covered |
| AC6.2 | grep-audit | phase_06.md T4 S3 | covered |
| AC6.3 | grep-audit | phase_06.md T2 S3 | covered |
| AC6.4 | — | — | CUT during M2 revision (2026-04-18) — forward-template compliance rests on AC6.1 + AC6.2 + AC6.8 instead; see per-AC note above |
| AC6.5 | subagent audit + file-existence | phase_06.md T5 | covered |
| AC6.6 | structural-check | phase_06.md T3 S3 | covered |
| AC6.7 | grep-audit | phase_06.md T1 S3 | covered |
| AC6.8 | grep-audit | phase_06.md T4 S3 | covered |

**Total ACs:** 43 (AC1: 7 + AC2: 7 + AC3: 8 + AC4: 5 + AC5: 8 + AC6: 7; Phase 2.5 has no ACs by design; AC5.8 added during H3 revision; AC6.4 cut during M2 revision — AC6.4 number retained as cut-marker, not reused).

**Fully covered by automated tests:** 37
**Covered by UAT entry (in uat-requirements.md):** UAT entries — `DR-AC4.5`, `DR-P1-DR1`, `DR-P1-DR2`, `DR-P1-DR4`, `DR-P2-DR8`, `DR-P2-DR3`, `DR-P3-DR7`, `DR-P5-FRUST-1` support AC4.5, AC3.7 (adjacent), and AC5.8 (frustration-signal audit categorisation). Not duplicated here. DR-P4-INT-1 was DELETED during H3 revision as unauditable-by-design; the deletion rationale lives in `uat-requirements.md` Phase 4 section, and its replacement is AC5.8 / DR-P5-FRUST-1.
**Framing corrections (2026-04-17, post-test-analyst):**

- **AC3.3** — prior framing of "covered-in-practice by AC3.4's grep" was circular and rested on a false assumption that content-grep in SKILL.md could substitute for file-absence of a different file. **Now covered by direct `os.path.exists` check in phase_02.md Task 2 Step 5.** The content-grep formerly used for AC3.4 was itself what the user named as requiring expunging.
- **AC3.4** — prior framing as an independent grep-audit was coherent but produced the anti-pattern of asserting absence by repeatedly naming the forbidden strings in verification code. **Now treated as a structural consequence of AC3.3** — if the source file does not exist, a section citing it is implausible. The content-grep has been removed.
- **AC6.4** — CUT during M2 revision (2026-04-18). The earlier "runnable bash audit script" framing was itself rubric-as-text: the script was embedded as a fenced code block inside `impl-plan-write/SKILL.md`, never extracted, never run, and coverage was just `grep -q` for the script's name. Rather than promote it to real enforcement (repo-level script + hook + CI wiring — all out of scope), the AC was cut. Forward-template compliance now rests on AC6.1 (template mandate) + AC6.2 (collation audit) + AC6.8 (Finalization existence).

**Strict coverage gaps:** None. Every AC maps to EITHER an automated test (operational check / structural assertion / runnable script) OR a UAT entry. The framing corrections above resolved the two "flagged" items via direct checks rather than rubric-as-text workarounds.

**Methodological note:** The initial test-analyst report accepted framings for AC3.3 and AC6.4 that propagated circular reasoning and the rubric-vs-gate confusion respectively. Both were surfaced by the user's intervention (the "expunge persuasion-principles" direction plus the "all levels of results must be discussed" guidance now saved to memory at `feedback_review-all-levels.md`). Future test-requirements generation should interrogate "flagged but not a gap" entries for false-assumption content before accepting them.
