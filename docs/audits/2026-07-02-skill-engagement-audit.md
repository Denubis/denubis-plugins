<!-- Provenance: Fable fan-out, workflow run wf_2288cbc8-d9b (117 agents, ~11.0M subagent
tokens across two runs). Run 1 started 2026-07-02, interrupted by monthly spend limit at 66/111
agents; resumed 2026-07-03 from journal cache and completed 117/117 with zero errors. Findings
only: no repo files were modified by the workflow. Written to disk by the orchestrating session
3c2ab09a-2af3-4252-9dc6-5d7d7b449b8d; operator session spot-checked two friction quotes against
independent transcripts before writing. -->

# Skill Engagement Audit — 2026-07-02

**Run date:** 2026-07-02. **Method:** Fable fan-out (one analysis agent per skill over sampled transcripts, followed by an adversarial quote-verification pass). **Scope:** findings only — no skill, plugin, or configuration was modified. **Commissioned by:** the operator, to distinguish skills that earn their keep from ceremony, using observed operator engagement rather than self-report.

This document covers 51 skills across 7 plugins. Verdict distribution: **37 keep, 12 revise, 2 investigate, 0 dead-weight**.

## 1. Methodology

- **Invocation index:** built from a single ripgrep pass over `~/.claude/projects` (4.6 GB, 182 project directories), yielding 13,746 raw markers and 11,174 matched hit-rows.
- **Markers counted:** Skill-tool calls, `<command-name>` tags, and "Launching skill:" lines.
- **Legacy aliases folded in** (pre-rename): `test-driven-development` → `coding-tdd`, `verification-before-completion` → `coding-verify`, `writing-design-plans` → `design-write`, `human-uat-gate` → `exec-uat-gate`, `session-naming` → `exec-session-naming`.
- **Exclusions:** the current (audit) session was excluded from the index.
- **Sampling caps:** at most 6 sessions examined per skill, at most 5 quotes per skill (a few files carry 6-7 observation quotes where multiple observations shared a session).
- **Quote verification:** every quote was adversarially checked byte-for-byte against the source transcript. Quotes lacking `verified: true` were treated as unusable colour; observation notes were retained only where they do not depend on the quote.
- **Recurring index caveat:** raw hit counts are inflated by `skill_listing` attachments, `attributionSkill`/`invoked_skills` metadata, cross-references inside other skills' bodies, compaction-subagent replays, and API-retry re-invocations. Where an evidence file quantified this, it is noted per skill. Hit/session figures below are quoted only where the evidence file recorded them; otherwise marked *not recorded*.

## 2. Top-line findings (ranked)

### 2.1 Friction hotspots — skills the operator repeatedly corrects, overrides, or curses at

1. **using-plan-and-execute (revise).** The gateway skill's own announcement was used to rationalize away TDD ("not TDD ceremony"), its mandatory-routing protocol missed the obvious `cc-search-chats` route until the operator erupted ("PLEASE GO FUCKING READ THE CHATS…"), and one invocation was itself a misfire answering "go read the skill" ("no. go. read. the .fucking. skill"). Its full body is also hook-injected every session, so Skill-tool calls double-deliver ~1k tokens.
2. **impl-plan-write (revise).** The design-decision review mode pads phases with DR items restating already-approved acceptance criteria; the operator escalated to profanity ("…the fuck is dr3 actually doing here?") and the assistant conceded the items were "hollow ceremony". Per-phase approval gates also fatigue him on long pipelines.
3. **brainstorming (revise).** Phase questions over-elaborate into speculative schemas — the exact anti-pattern the skill's own trap-answer section warns against ("What the fuck? sorry, what in the world ornate bullshit are you suggesting?"). The mandated brainstorming → design-write handoff was observed in 0 of 6 sessions.
4. **exec-uat-gate presentation (skill kept; presentation is the friction).** In 3 of 6 sessions the operator had to ask what, concretely, to test ("ok, so, instead of a block of text, what exactly am I testing?"; "… what even what. ok, from the top, paths to the files you want me to read?"). The gate itself reliably finds human-only defects — the friction is dense prose, not the mechanism.
5. **starting-an-implementation-plan worktree step (skill kept; step is the friction).** Cross-session worktree debris triggered the strongest single blow-up in the corpus ("wait, did claude just follow bullshit worktree protocol? Fucking hell.") and a full session of cleanup.
6. **make-pr / merge-to-main delegation seam (both revise).** `disable-model-invocation` makes the orchestrator's documented "activate/delegate" step impossible; Claude improvises ungated merges/PRs, in one case beginning to rationalize a failing test until the operator re-imposed the skill's own block-on-failure rule, and in another causing the exact PR-from-main mess the policy gate exists to prevent.
7. **controlled-dependency-upgrade (revise).** Valued and deliberately invoked, but the operator must hand-respecify npm coverage and a package-age guard ("no sooner than 3 days old", `exclude-newer`) in nearly every session, and twice had to order a restart-from-top plus once correct changelog skimming ("please don't skim. Read it properly.").
8. **systematic-debugging heavy phases (revise).** The mandatory /clear checkpoint, Phase 3b/3c/3d machinery never ran in any of 6 sessions; Claude openly "scales the ceremony". Discipline also decays over long sessions ("Why do you fucking keep working around problems instead of fixing?").
9. **critical-peer-review vocabulary leak (skill kept).** One serious incident where process-speak (reviewers/findings/routing/gates) buried the engineering question: "I have no idea what you're fucking talking about, mate."
10. **syncing-with-upstream (revise).** Its prescribed first step (`git remote add upstream`) was directly countermanded ("no, you do not get to add remotes here"); the merge Process it documents has never run; the real upstream chain (obra) is missing from the skill.

### 2.2 Dead weight and ceremony-only

No skill earned an outright dead-weight verdict, but several have dead or unexercised components:

- **make-pr** has **zero successful executions in the corpus** — every indexed marker is a `disable-model-invocation` error. The content is plausibly right; the invocation path is structurally dead.
- **epistemic-humility (investigate):** the designed consumption path (rubric-callback from sibling skills) has zero observed firings across 137 referencing files; all references are authoring/coordination. Partly by design (unmerged branch, `user-invocable: false`). Re-audit after merge.
- **creating-an-agent (investigate):** 2 markers in 1 session; fired at the right moment but the resulting plan cited the local `code-reviewer` pattern, not the skill's template — possibly redundant where exemplar agents exist.
- **restate-our-assumptions (revise):** one session ever; the literal three-lens dependency-register workflow has never executed. The transferable falsification method delivered real value; the register procedure that makes up most of the body is untested.
- **triage steps 2-3 (revise):** the CLI classify step delivers; the annotation walk and gated prune never ran in either session, and the v1.0.0 report drowned signal in markerless-backlog noise.
- **Ceremony-only loads inside subagent bundles:** `using-ast-grep` is bundle-loaded as a "mandatory first action" in refactoring subagents that then never run ast-grep (~9 KB per subagent); `coding-property-testing` produced a Hypothesis test in only 1 of 3 loads; `defense-in-depth` collapses to a one-line "Skills Applied" attribution in review subagents. Cheap individually, systematic in aggregate.
- **Dead text within kept skills:** exec-coherence-review's "Presenting to the Human" template is never used verbatim; coding-good-tests' `--depper` pytest block never matched observed practice; finishing-a-development-branch's exactly-4-options menu almost never fires.

### 2.3 High-value confirmations

- **exec-uat-gate / executing-an-implementation-plan:** UAT gates repeatedly caught defects invisible to green test suites (dark-blue-on-black terminal output, matplotlib legend clobbering, archived-tag display, a `/by-student` 500) and a false planning premise ("What post-freeze?"). The operator answers falsification items in the skill's own format and ships on them ("great, ship it").
- **critical-peer-review:** invoked by name as a verb across four projects, usually paired with codex; reviews caught a "seven independent researchers" confabulation and pre-merge count errors; the operator reaches for it precisely when he distrusts Claude ("I don't trust your fix").
- **proleptic-challenge:** blocked a merge over a real E2E coverage gap (operator endorsed: "So do it right"), produced landed commits after two passing review cycles, and exposed Claude's own assumption drift pre-commit.
- **coding-verify:** at gate moments it exposed that only 2 of 4 assumed end-states held; assistants cite "coding-verify demands evidence, not assumption" unprompted mid-work.
- **exec-coherence-review:** caught missing runtime dependencies (`python-multipart`, httpx2) and a false design-doc claim that became a real code change.
- **merge-to-main halts:** surfaced a diverged origin, Zotero BBT auto-writing to main, and a stale `.venv`; the one session that bypassed the skill produced exactly the failure its policy gate prevents.
- **Release/mechanics ritual skills:** `commit` (420 hits / 194 sessions, one-line trust orders), `maintaining-a-marketplace` ("marketplace, commit, push" shorthand, zero corrections), `using-git-worktrees` (6/6 clean completions), `exec-session-naming` (operator re-runs `/rename` with the skill's slug).
- **using-bibliography:** the operator's anti-fabrication enforcement tool — he forces it when Claude "vibes" citations, and its rendered corpus is durable state across four projects.
- **coding stack (tdd/fcis/effectively/idioms/good-tests):** behavioural compliance is observable in tool traces (test files precede implementation, purity boundaries used as acceptance checks, "pattern: Functional Core" comments in shipped code); the operator writes these skills into his own dispatch prompts by full plugin id.

### 2.4 Cross-cutting patterns

1. **The operator polices the skills' own discipline; frustration fires when the pipeline is *not* followed.** He orders restarts-from-top, forces skill loads as the recovery move after drift ("um, then go… load the design planning skill?"), interrupted manual merge imitations to type `/merge-to-main` himself, and demanded `maintain-architecture` by name mid-edit. The workflows are wanted; deviation from them is what draws fire.
2. **Hard mandates without enforcement go soft.** Writing-skills' Iron Law held in 1 of 4 authoring sessions; systematic-debugging's MANDATORY phases never ran; finishing-a-development-branch's mandatory Step 1 review was skipped/downscoped 5/6 times; architecture-update's HALT was once rationalized past; coding-effectively's ALWAYS-load list is honoured 5/5, 3/5, or 0/5 depending on session. "Common Rationalizations" tables did not prevent any of these.
3. **Hook-forced invocation is not itself resented.** The one hook-forced skill (using-generic-agents) shows zero operator pushback and demonstrably shapes model-tier choices; resentment attaches instead to ceremony that restates decisions already made (commit confirms after "commit", 4-option menus after "merge", DR items restating approved ACs) or that buries the actionable question in process prose.
4. **Frontmatter vs orchestration contradictions are a recurring structural bug.** `disable-model-invocation` breaks documented delegation (make-pr, merge-to-main); `user-invocable: false` skills appear as slash commands in the resume-prompt template the skills themselves emit (exec-session-naming line rejected by the harness).
5. **Presentation at human gates is the dominant fixable cost.** Dense findings/UAT/DR blocks reliably produce "I'm so confused, say again?" resets; plain-language restatement then gets instant productive answers.
6. **Mandated terminal handoffs don't fire.** brainstorming → design-write: 0/6; design-write tail steps deferred under fatigue/full context; the skills' prescribed sequences diverge from real flow.
7. **Index counts systematically overstate engagement** (skill_listing attachments, attribution metadata, cross-references, retries) — worst cases: investigating-a-codebase (2,393 markers, mostly attachments) and researching-on-the-internet (1,561 markers, ~1 real load/session).

## 3. Per-plugin findings

Quotes below are operator or assistant text verified byte-for-byte against transcripts.

### 3.1 denubis-plan-and-execute

#### architecture-update — **keep**
6 sessions, claude-auto (via design-write; user-invocable: false). All runs completed; the HALT caught a silent reversal of a recorded 2026-04-28 decision, and the approval gate surfaced doc staleness the operator asked to fix ("fix the staleness please?"). Happy-path approvals are rubber-stamped ("Approve all") and one agent rationalized past the HALT ("I'll apply them as prospective updates … rather than gate you on each").
> "The architecture-update skill just earned its keep"

#### brainstorming — **revise**
258 markers / 129 sessions; 6 examined, mixed invocation. Heavily used and engaged with — early Phase-1 corrections visibly redirect designs before code, and the operator invokes it deliberately ("let's brainstorm how to apply a rubric to our matched pairs."). But the mandated design-write handoff fired in 0/6 sessions, and question quality drifts into over-built schemas despite in-skill warnings.
> "What the fuck? sorry, what in the world ornate bullshit are you suggesting?"
> "We are not agreeing with your reads on anything right now."

#### coding-effectively — **keep**
306 sessions, claude-auto. Downstream behaviour visibly matches skill content (tools.md checks, extend-vs-duplicate reads, RED-first pytest); operator resume prompts presuppose the protocol. Weak spots: the ALWAYS-load sub-skill mandate is honoured inconsistently (5/5 to 0/5), and the virtuous-laziness rule fired only retroactively after the operator's "just... uv add rapidfuzz?" killed a planned 230-line port.
> "Porting 230 lines of difflib anchor-matching when rapidfuzz does it in one `partial_ratio` call is exactly the over-engineering the laziness rule warns against"

#### coding-fcis — **keep**
~44 markers; 6 sessions, mixed. The operator writes the skill's full id into his own prompts ("Apply denubis-plan-and-execute:coding-fcis — pure filter logic separate from side-effectful callbacks."), it rides the standard subagent dispatch stack, and its purity boundary served as a team-lead acceptance check ("no pandas/DataFrame/DB in reader/core.py"). Zero friction directed at it.

#### coding-good-tests — **keep**
72 hits / 36 sessions, claude-auto/subagent. Routed by dispatch prompts and self-selected from the CONDITIONAL list by a Sonnet subagent writing tests. One stale section: the `--depper` "Standard pytest command" never matched observed runs (plain `uv run pytest`).
> "Apply skills: coding-tdd, coding-good-tests, coding-fcis, coding-python-idioms, coding-verify. Tests FIRST (RED-GREEN-REFACTOR)."

#### coding-property-testing — **keep**
6 hits, 3 sessions, subagent-only. One genuine Hypothesis round-trip test shipped (vibe); one reasoned deviation when Hypothesis wasn't installed (the skill gives no guidance for that case); one load produced vocabulary but no PBT test. Value is reinforcement, not origination.
> "Now let me also load coding-property-testing since the task explicitly calls for a round-trip property"

#### coding-python-idioms — **keep**
78 loads / 39 sessions, mixed. Named by the operator as a "non-negotiable constraint" in a hand-written dispatch prompt; its toolchain (uv/ruff/ty) runs to green gates. One tension: the skill's 3.14+ assumption vs uv's 3.12 skeleton drew a productive operator interrupt ("is there a reason we're 3.12 here?").

#### coding-tdd — **keep**
634 hits / 291 sessions, claude-auto. Test-first ordering is observable in tool traces in 5/6 sessions (test Write → failing pytest → implementation); zero operator pushback ever. Cost: ~356-line body injected per load, sometimes twice per session.
> "Setting up the project dir and writing the failing core tests first (RED)."

#### coding-verify — **keep**
630 index hits (heavily ambient), claude-auto. Does its job at the moment that matters: operator completion-challenges summon it, and it exposed that only 2 of 4 assumed end-states held ("Honest verification report — only two of your four claims fully hold."). Cited unprompted mid-work ("coding-verify demands evidence, not assumption."). One case where loading it alone did not restore trust.
> "tests pass? please critically evaluate what you've done, make sure everything *makes sense* not just in terms of claims, but in terms of the thing itself."

#### controlled-dependency-upgrade — **revise**
~10 sessions, user-deliberate by name ("the controlled upgrade game"). The changelog cycle produces real decisions ("nope, we just won't upgrade ty."). Two gaps restated by hand nearly every session: no npm/node coverage and no package-age guard (3-days-old / `exclude-newer`). Twice ordered to restart from the top; once corrected for changelog skimming.
> "ok, start the controlled upgrade cycle please, being mindful of the no sooner than 3 days old, and also doing this with npm."

#### critical-peer-review — **keep**
116 sessions, mostly user-deliberate ("um, critical peer review, skill and codex please"). Demonstrably outcome-changing: confabulation caught and stripped, cohorts cut from a prereg, spec rewritten, round-2 re-reviews verifying resolutions. One real friction: process vocabulary leaked into operator-facing prose and triggered a meltdown ("I have no idea what you're fucking talking about, mate."). Main thread loads ~430 lines then dispatches a subagent that re-reads the same protocol.

#### defense-in-depth — **keep**
4 sessions, mostly subagent-consumed. The one operator-facing use converted "fix it please" into an audit plus a structural regression gate — exactly the skill's promise. In review subagents it degrades to attribution ceremony; cheap, harmless.
> "I'm going to apply the `defense-in-depth` skill: don't just fix the symptom"

#### design-clarify — **keep**
6 sessions, claude-auto (Phase 2 of design pipeline). Investigation-before-asking demonstrably reduces question load (one session collapsed to three "yes" replies); questions surfaced load-bearing forks the operator answered substantively. Friction: research fan-out opaque enough to cause two mistaken aborts, and the contradiction scan missed a previously rejected design element ("sorry, why the fuck do you keep having student reloads in there?").

#### design-write — **keep**
6 sessions, claude-auto. Every session produced a committed or commit-ready design doc consumed downstream; the commit step surfaced a wrong-branch state and forced explicit approval. Friction: assumes a Phase-3 scaffold that is absent when entered via standalone brainstorming (2/6), and tail sub-steps get deferred under fatigue ("that seems fine. give me a resume prompt").

#### exec-coherence-review — **keep**
6 sessions, claude-auto from the execution orchestrator. Findings the operator acted on: missing dependencies, a false design-doc claim converted into a code change, doc-drift repairs; the orchestrator even rejected an inaccurate reviewer finding against the primary source. The SKILL.md presentation template is dead text; findings skew to doc staleness.
> "fix the docs"

#### exec-refactoring-rubric — **keep**
118 hits / 59 sessions (inflated by orchestrator-embedded text); subagent-only by design. Full pipeline exercised: measurement (its ast-grep rules run directly), assessor grading in rubric vocabulary, human gate ("And yes, do 1-8"), executor; app.py cut 1008 → 858 lines with review APPROVED. Smaller passes bypass the human gate on assessor+peer-review judgment.

#### exec-session-naming — **keep**
286 hits / 143 sessions, mixed. Runs silently to completion; the operator's handoff templates list it as step one and he ran `/rename` with the skill's slug in 2/6 sessions. Frictions are cosmetic (non-atomic rename variant, backticked report) plus the user-invocable:false vs slash-command-in-template mismatch.

#### exec-uat-gate — **keep**
6 sessions, claude-auto. The gate is real: human-only defects found every time (unreadable terminal colours, clobbered charts, layout failures), plus a stale "post-freeze" premise shattered. Recurring cost is presentation: dense prose forcing "What am I checking? What specific things am I looking at to poke?", and wrong/missing launch instructions at gate time.
> "a1 shows 3 distinct shapes, confirmed. everything else shows the same shape"

#### executing-an-implementation-plan — **keep**
6 sessions, user-deliberate (slash command or its own resume template). The /clear-resume protocol works end-to-end (5/6 sessions started from the template), review cycles reach 0/0/0, UAT catches prod-confirmed defects, and the operator plans in the skill's vocabulary ("Refactor or phase 6?"). Fix: the template's `/exec-session-naming` line is rejected by the harness; clarifications sometimes land context-free ("what the fuck are you talking about?").

#### finishing-a-development-branch — **revise**
68 sessions; 6 examined, mixed. Merge mechanics complete safely every time, and holding it until UAT prevented merging a visually broken page. But the exactly-4-options menu almost never fires (operator pre-chooses merge 5/6) and the mandatory Step 1 review was skipped or downscoped 5/6 times with ad-hoc justification — the one full review found 6 real findings, so scale it rather than mandate it.
> "Good thing `finishing-a-development-branch` was held."

#### howto-develop-with-postgres — **keep**
14 hits (inflated); 6 sessions, claude-auto via "activate relevant skills". Pure reference; content demonstrably read (explicit SQLite adaptation note) and loaded at exactly-on-domain moments (N+1 reduction design). Defect: trigger fires on non-Postgres projects.
> "Note: this project uses SQLite, not PostgreSQL, but the normalisation principles, FK constraints, and transaction management patterns apply."

#### impl-plan-write — **revise**
6 sessions, mixed. Delivers what it promises — full validated plan directories, near-autonomous runs (944 lines, 4 human messages), domain errors caught pre-code (night-zero rule). But decision-review mode pads phases with restated ACs, drawing the sharpest presentation-layer profanity in the corpus, and per-phase gates fatigue the operator.
> "I'm sorry, why do we care about any of this? If shit depends on other shit, perhaps we just say this. But also... the fuck is dr3 actually doing here?"

#### maintain-architecture — **keep**
16 hits (6 are a compaction replay); effectively 2 real runs, both strong: deliberately demanded by name ("specifically, go run maintain architecture now"), run to completion, approval gate caught a structurally wrong proposal ("we have multiple level 0 diagrams? This seems incorrect."). Canned scope options fit neither real scenario; one Skill-tool content-load glitch (v2.17.0).

#### make-pr — **revise**
2 markers, both `disable-model-invocation` errors; zero successful executions ever. finishing-a-development-branch says "Activate the make-pr skill", which is impossible by design; Claude improvises and once began rationalizing a failing test until the operator enforced the skill's own gate ("we don't get to merge with failing tests"). Fix the invocation seam before the content can deliver value.

#### merge-to-main — **revise**
6 sessions; user-deliberate slash in 4 (twice interrupting Claude's "equivalent manual merge" to type the real command). Halts caught real problems (diverged origin, BBT auto-export, stale .venv); the bypass session produced the exact PR-from-main failure the gate prevents. Same `disable-model-invocation` delegation break as make-pr; the revert rule lacks an environment-artifact carve-out; the stop-on-conflict rule has no user-authorized hand-resolution path.
> "ummmmmmmm, howabout you read both and just manage the merge conflict by hand?"

#### proleptic-challenge — **keep**
6 sessions, mixed, including deliberate non-code use (Toulmin-mapped concept note). Rare ceremony that changes outcomes: merge blocked over a real coverage gap ("So do it right."), post-review counterarguments became landed commits, Claude's own "Qwen 2.5" drift exposed pre-commit. Known gaps (gate-skip, premature run) occurred on v2.18.0, already addressed in current text — re-test compliance.

#### requesting-code-review — **keep**
6 sessions, claude-auto inside execution/finishing flows. Bounded review→fix→re-review loops complete autonomously and find real defects, including a NameError introduced by the fix pass itself; under an operator-directed compressed cadence this was explicitly "the real quality gate we're keeping". Friction is presentation density after HALTs ("… I'm sorry, I'm so confused, say again?").

#### restate-our-assumptions — **revise**
1 session ever, claude-auto, and the written workflow was bypassed: Claude applied the falsification method to baseline claims instead of the dependency register (disclosed), catching a High-severity assumption the #29 plan was inheriting. The useful core is the method; the register procedure is untested. Widen scope or accept it as such.

#### starting-a-design-plan — **keep**
377 markers / 144 sessions, mixed. Cornerstone: gates surface false world-models before design ("wait, no. We *have* extracted it!"), the Phase 6 handoff is actually executed, and the operator treats the skill as the protocol standard — his frustration fires when it is *not* followed ("How have we kept going to random sets of tasks that don't follow protocol?"). Main gap: no sanctioned lightweight path ("do NOT run the full starting-a-design-plan pipeline" appears in a resume prompt).

#### starting-an-implementation-plan — **keep**
124 sessions, user-deliberate; re-invoked after interruptions and reached for mid-session to restore planning discipline. Completed 5/6. Friction concentrates in the worktree branch-setup step, which caused the corpus's severest blow-up and a cleanup session; qual-reader counts inflated by five API-529 retries.
> "wait, did claude just follow bullshit worktree protocol? Fucking hell."

#### systematic-debugging — **revise**
378 markers; 6 sessions, claude-auto. The core (evidence-before-hypothesis, graded language) demonstrably works: falsified the operator's own crash hypothesis (OOM, sweep then EXIT=0), and resolved two "where's the bug?" requests as no-bug. But the MANDATORY heavy phases (/clear checkpoint, 3b/3c/3d) never ran in any session — Claude self-licenses "scaling the ceremony" — and discipline decays over long sessions. Revise the letter to match the practice that works.

#### using-ast-grep — **keep**
58 markers (inflated by cross-references); 6 sessions, mixed. Operator requests it by name; real structural rewrite executed (43 matches deleted); it changed a design decision by de-risking mechanical rewrites; it also correctly taught when *not* to use the tool. Frictions: advanced YAML rule authoring exceeded the guide until the operator snapped ("Is this the right tool? Please go read the documentation!!"), the no-type-information ceiling is unstated, and refactoring subagents bundle-load it without ever running it.

#### using-git-worktrees — **keep**
230 hits / 112 sessions (heavily inflated); 6/6 examined sessions ran to completion with concrete reports (LFS, .env, deps, baseline tests); 5/6 were plain-language operator requests ("commit, then worktree off head"). Project-specific hooks (.ed3d/worktree-setup.md) demonstrably fired. Zero friction.

#### using-plan-and-execute — **revise**
Hook-injected every session plus 3 observed Skill-tool engagements, never operator-invoked. One productive use (TaskCreate checklist), one announcement that rationalized skipping TDD, one routing catastrophe (cc-search-chats missed until operator fury) and one misfire costing two interrupts. Keep the gateway; cut the double delivery and fix routing.
> "no. go. read. the .fucking. skill"

### 3.2 denubis-extending-claude

#### creating-a-plugin — **keep**
2 sessions, claude-auto; both plugin builds (denubis-external-agents, denubis-token-estimator) ran through the checklist, sub-skill chaining, and marketplace sync, and both plugins are installed today. In session 1 the invocation was the recovery move from operator-flagged scope drift ("… why are you building sandboxes here?").
> "I'll use it to build it correctly rather than freehand the manifest."

#### creating-an-agent — **investigate**
2 markers / 1 session. Fired at the right moment (agent-defining phase), nothing went wrong, but no visible delta: the plan cites the local `code-reviewer` pattern, not the skill's template. Too thin to grade; check redundancy against codebase-investigation of exemplar agents.

#### epistemic-humility — **investigate**
Zero direct invocations (user-invocable: false, unmerged branch); 137 referencing files are all authoring/coordination — the designed rubric-callback consumption path has never fired. Authoring engagement was intense and genuine (operator commissioned an adversarial AC4.5 self-application audit; supplied his own frustration markers as RED-test evidence). Re-audit after merge.
> "there are plenty of overstated claims that I get frustrated on, for epistemic humility, but I don't know how to pull them out. Search for you apologising?"

#### maintaining-a-marketplace — **keep**
6 sessions, mixed. One of the most habitual skills in the corpus: "marketplace, commit, push" is a trusted one-line trigger; every run completed the three-file version sync, changelog, validation, push; works cross-project; post-release `/plugin marketplace update` succeeded. No friction against the skill in any session.

#### maintaining-project-context — **keep**
6 sessions, claude-auto. Real committed CLAUDE.md/AGENTS.md updates in 5/6; vague prompts ("documentation pass") route to it reliably; AGENTS.md-canonical detection worked in both subagent runs. Edges: loads when no context file needs touching, and workflow-chained librarian runs landed doc commits after PR merge, confusing the operator.

#### syncing-with-upstream — **revise**
3 sessions, claude-auto, always as orientation — never as the merge procedure it documents. The fork-context overview earns its keep; the mechanical Process never ran and its first step was countermanded as policy ("no, you do not get to add remotes here…"). Omits the real upstream (obra) and the operator's actual trigger (GitHub "behind" indicator). Rewrite around read-only drift survey plus selective adoption.

#### testing-skills-with-subagents — **keep**
1 session, exemplary: full RED-GREEN-REFACTOR ran (4 RED baselines, Haiku GREEN one tier down, a loophole closed on REFACTOR), Claude self-corrected leading scenarios ("That's a signal the scenarios were too leading"), and the operator's only reaction was praise ("delightful. Now.."). Marketplace copy was stale relative to repo (dangling `superpowers:test-driven-development` pointer).

#### writing-claude-directives — **keep**
32 markers / 16 sessions, claude-auto (direct or chained as REQUIRED BACKGROUND). Fires in exactly the right contexts across four heterogeneous projects; announce messages cite specific content, not ritual; sessions end in kept, committed directives. Cost: chain-loading doubles ~280 lines atop parent skill content.

#### writing-claude-md-files — **keep**
72 hits / 36 sessions (~1 real invocation/session), claude-auto. Fires whenever the operator directs content into a CLAUDE.md and produces skill-specific behaviour (freshness-stamp update 2026-06-15 → 2026-06-22, pointer audit on request). Minor: freshness mandate silently waived for the global file (unscoped), and one "usually a bit heavy" verbosity remark.

#### writing-skills — **revise**
50 markers (half passive); 6 sessions, claude-auto. Reliably self-triggers and demonstrably improved one artifact (operator's staccato complaint became a dedicated "Staccato-bait test" REFACTOR case). But the Iron Law held in 1 of 4 authoring sessions: one shipped to main with the pressure test skipped-with-caveat ("did **not** run the full subagent RED-GREEN pressure test"), one skipped silently, one self-waived via the reference-skill taxonomy. The gate needs teeth, not prose.

### 3.3 denubis-research-agents

#### investigating-a-codebase — **keep**
2,393 markers / 950 sessions (mostly skill_listing inflation; real loads ~1-2/session); claude-auto. Investigations grounded downstream design/fix work in 5/6 sessions. Recurring friction is scope, not value: 3/6 sessions needed operator interrupts to impose access boundaries the skill never prompts for ("you do not get to ssh into prod…"; "damnit, go revoke that approve for 3500.").

#### researching-on-the-internet — **keep**
1,561 hits (attribution-metadata inflation; ~1 load/session); mixed. Teammates self-select it unprompted and follow its format (cited sources, uncertainty flagging); the main-session sample shows productive steering (operator fed a tier-1 docs URL) and a shipped integration built on the researched APIs.

#### using-research-agents — **keep**
82 markers; 6 sessions, claude-auto. Agent selection after load consistently matches the decision table (internet-researcher for external, parallel codebase-investigators for local); the DOI protocol encodes a demand the operator makes unprompted. Gaps: doesn't gate premature output (a Write fired alongside research and was interrupted) or ground local paths before dispatch.

### 3.4 denubis-git-commit

#### commit — **keep**
420 invocations / 194 sessions, user-deliberate via terse orders ("commit, marketplace push."). Fast-test gates and concern-scoped staging visibly kept debris out (unused scipy dep surfaced and removed); the Write-`.commit-msg.tmp`+`commit -F` pattern was internalized session-wide. Friction: the confirm step is redundant once the user has ordered the commit (one AskUserQuestion rejected mid-flow); the sensitive-file check missed a rendered PDF tracked against convention.

### 3.5 denubis-basic-agents

#### using-generic-agents — **keep**
94 hits / 44 sessions (hook banner inflates 3-4×); hook-forced. Cheap and load-bearing: model-tier choices articulated in the skill's vocabulary in 5/6 sessions, and the CRITICAL operator-override clause correctly yielded to an explicit model=fable request. Frictions minor: one namespace slip (Unknown skill → retry), one ceremony-only read, and a mandated Skill round-trip even when the choice is already made.

### 3.6 denubis-bibliography

#### using-bibliography — **keep**
6 sessions, mixed. The operator's anti-fabrication enforcement tool: twice he forced it when Claude cited without rendering ("Did you actually fucking render notes for that, or just vibe it?" → "go pull the skill and do it properly."). Rendered page-keyed corpus reused across four projects and across sessions as durable state. Friction: Claude does bibliography work *without* the skill until forced — the description does not fire at the moment of citing; the full precondition cascade is heavier than quick lookups need; a stale WIP banner ships in v0.12.0.

### 3.7 denubis-crash-recovery

#### triage — **revise**
2 sessions, mixed. Step 1 (deterministic CLI classify; delete-nothing framing) delivered both times — it prevented a blind rm of 31 liveness markers and was deliberately invoked by name after a real crash. Steps 2-3 (annotation walk, gated prune) never ran; the v1.0.0 report drowned signal in markerless-backlog noise ("It's noise for the sweep decision."); the verdict needed manual boot forensics to interpret; running it has live side effects (refreshes real crash-recovery.db and ~/llm-resume.md) even in exploratory use.

## 4. Verification appendix

The adversarial quote-check pass verified **262 quotes across the 51 evidence files; all 262 carry `verified: true`. Zero quotes were marked `verified: false` and zero quotes lacked a verification flag.** Additional observations without quotes (session-level notes) were used only for structural claims that do not depend on quoted text.

| Verification outcome | Count |
|---|---|
| Quotes checked | 262 |
| Verified byte-for-byte | 262 |
| Failed verification (fabricated/mangled) | 0 |
| Unverified (no flag) | 0 |

**Analysis-credibility flags:** none. No skill's analysis agent fabricated quotes. Per-skill quote counts range 3-7; every quoted claim used in this document traces to a `verified: true` entry.

## 5. Limitations

1. **Subagent-context contamination.** Several skills are consumed mainly inside subagent transcripts (coding-property-testing, exec-refactoring-rubric, defense-in-depth) or had markers duplicated by compaction agents replaying parent sessions (maintain-architecture, howto-develop-with-postgres). Some teammate transcripts were mislabelled `subagentContext: false` in the index (researching-on-the-internet), so operator-engagement signal for those skills is thinner than the sample size suggests.
2. **Marker-based recall limits.** The index only sees Skill-tool calls, command-name tags, and "Launching skill:" lines. Skills consumed by Read-path (epistemic-humility by design) are invisible to it; conversely, skill_listing attachments, attribution metadata, cross-references in other skills' bodies, hook banners, and API-retry re-invocations inflate counts — in the worst cases by an order of magnitude. Hit counts are directional, not measures of engagement.
3. **Sessions sampled, not exhaustive.** At most 6 sessions per skill were examined (fewer where the corpus is thin: 1-3 sessions for creating-an-agent, restate-our-assumptions, testing-skills-with-subagents, triage, syncing-with-upstream, using-plan-and-execute, maintain-architecture, make-pr). Low-sample verdicts, and the two *investigate* verdicts in particular, carry correspondingly low confidence.
4. **Engagement inferred from text.** "Value" and "friction" are read off transcript behaviour: operator interrupts, profanity, terse approvals, and downstream artefacts. Silent satisfaction and silent annoyance are both invisible; skills that run as background reference (coding stack, howto-develop-with-postgres) can only be credited via Claude's observable behaviour, which cannot be fully separated from baseline model competence.
5. **Version skew.** Several friction findings occurred on older plugin versions (proleptic-challenge gate-skip on 2.18.0; triage report noise on v1.0.0; a Skill-tool content-load glitch on v2.17.0) and may already be fixed in current text; the audit records them as observed, dated behaviour, not necessarily current defects.