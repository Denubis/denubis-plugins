# Coherence Review: Phase 7 — Skill file and skill ↔ CLI integration

Reviewer: claude-opus-4-7[1m]
Date: 2026-05-19
Phase file: /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/crash-recovery/docs/implementation-plans/2026-05-08-crash-recovery/phase_07.md
Design plan: /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/crash-recovery/docs/design-plans/2026-05-08-crash-recovery.md
Diff range: 354fd3a..b4a0171

## Conformance

The implementation matches the design plan's architectural intent for Phase 7 closely. Spot-checks:

- **SKILL.md body structure** matches the plan's required section order (Overview → Announce → Step 1-4 → Common rationalisations → Integration). Section content matches the spec including the manual-review-first iteration order and the `[manual review]` prefix.
- **AskUserQuestion gating** for both annotation (yes/no/skip all) and prune (yes/no/show me again) is structurally present and prose-matched to the plan example.
- **CLI invocations** in SKILL.md use the prescribed hardcoded `uv run --project ~/.claude/plugins/marketplaces/denubis-plugins/...` form — matches design plan's "Existing Patterns" section about hardcoded absolute paths.
- **README sections** are present in the order Plan-Task-2 specified: Overview, Installation, Dependency, Usage, UAT scenarios (AC5.6, AC6.4), Troubleshooting. README is 105 lines (≤120 line cap).
- **bats smoke** has all six tests the plan specified, with the prescribed env-var setup and teardown.

**Drift found (Perry & Wolf 1992 sense — design unclear, implementor filled in):**

- **D1 (Low).** SKILL.md frontmatter `description` text differs from the plan's example. Plan example: "Use when checking which Claude Code sessions ended abnormally (crashed, killed, idle-disconnected) and producing ~/llm-resume.md with deterministic classification and gated prune." (200 chars). Implementation: "Use when inspecting Claude Code session state after a suspected crash or idle-kill and producing ~/llm-resume.md with deterministic classification and gated prune." (164 chars). The QA constraint codified in `docs/architecture/constraints.md` ("Plugin manifest description shape") forbids parenthetical enumerations, which the plan's example would have violated. The implementor chose a compliant alternative preserving the trigger intent (suspected crash, idle-disconnect). The plan was silent on the conflict between its own example and the QA rule — the divergence is drift, not erosion. The replacement is faithful to intent.

- **D2 (Low).** SKILL.md adds a fourth "Common rationalisations" row that the plan did not specify: "The user said skip annotations, so I'll skip prune too." This is independent-decision documentation that strengthens Step 3's gating; it does not contradict the plan and is consistent with the design's deterministic-flow stance.

- **D3 (Low).** README Status section ("v0.1.0 ships the plugin, …") is implementor-added — plan was silent on it. It accurately enumerates what is and is not shipping and is consistent with the implementation-phase boundary the rest of the doc describes.

No erosion found (no code violates design intent).

## Traceability

| Decision / AC | Code | Test | Doc | Notes |
|---|---|---|---|---|
| AC1.2 (plugin listed after install) | `.claude-plugin/marketplace.json` (Phase 1) + SKILL.md (Phase 7) | `tests/test_crash_recovery_smoke.bats::denubis-crash-recovery is listed in marketplace.json` | README "Installation" | Test is the closest automatable proxy as planned; manual `/plugin` listing remains a UAT step (deferred to Phase 8). |
| AC8.1 (README documents sibling-plugin dependency with version pin) | n/a (docs only) | None automated | README "Dependency" section | Version pin remains `<PHASE-8-VERSION>` placeholder, by design — Phase 8 substitutes the real number. The presence of a non-empty Dependency section is verifiable by `grep -q "denubis-plan-and-execute"` (the plan listed this; the bats suite does not include it). |
| DR3 / DR8 (wrapper patch is the source of liveness signal) | n/a in Phase 7 | n/a in Phase 7 | SKILL.md "Integration"; README "Dependency"; README "Status" | The doc surfaces flag that crash detection becomes operational only with Phase 8's wrapper. But the docs' description of what happens *without* the wrapper is empirically wrong (see Baked-In Assumptions B1). |
| Skill description QA contract (≤200 chars, no parenthetical enumeration, leads with "Use when") | SKILL.md frontmatter (164 chars) | `tests/test_skill_descriptions.py -k triage` | `constraints.md` "Plugin manifest description shape" row | Pass; this is automated as planned. |
| SKILL.md ↔ CLI plumbing (init/triage/regenerate/prune happy path) | SKILL.md Step 1-4 invocations | All six bats tests | SKILL.md Step 1-4; README "Usage" | Plumbing well-covered. |

**Gaps:**

- **T1 (Low).** AC8.1 has no automated assertion that the dependency string is *present*. The plan listed `grep -q "denubis-plan-and-execute" plugins/denubis-crash-recovery/README.md` as a verification step but did not turn it into a bats test. This is automatable and would survive into Phase 8's edits to the same file. Candidate fitness function: add a test to `tests/test_crash_recovery_smoke.bats` (or wherever the suite lands long-term) that asserts the README contains the sibling-plugin dependency line. State: this traceability concern should be a test, not a recurring review item.

- **T2 (Low).** `prune.py` exits non-zero with stderr containing "confirm" — the bats test asserts the exit code is non-zero AND stderr contains "confirm". But the SKILL.md body claims (correctly) that `prune` without `--confirm` exits with code 1. The smoke test does not pin the code-1-not-code-2 distinction, which matters because the constraints doc ("CLI exit-code contract") makes code 1 = "no data" and code 2 = "invocation rejected". The plan was silent on which value to assert. Candidate fitness function: change `[ "$status" -ne 0 ]` to `[ "$status" -eq 1 ]` to lock the contract. Low-cost; should be a test, not a review note.

- **T3 (Low).** The "manual-review-first" iteration order documented in SKILL.md Step 2 has no automated test guarding it. This is intrinsically an LLM-runtime behaviour (the skill body instructs Claude on iteration order), not a code path that could be unit-tested without an integration harness. Not automatable today; flag as a UAT concern only.

## Baked-In Assumptions

**B1 — "every session classified `concluded`" overclaim (concerning, already routed for Phase 8 fix).**

- **Design said:** silent on what happens when the wrapper is absent. The design plan says "the CLI degrades gracefully: classification falls back to JSONL-tail-only heuristics for those" (Additional Considerations / Backward compatibility, line 508) but does not assert any specific classification.
- **Implementation chose:** README (lines 25-27) and SKILL.md (line 99) both claim that without the wrapper, "every session will be classified `concluded`" / "every session is classified `concluded`". The 2026-05-18 dogfood disproved this empirically: 5 crash victims classified `borderline` with reason `unknown_tail_kind` and routed to "Needs investigation" / "Ambiguous correlation". Every `HARD_CRASH` row in `classify.py::RULES` (lines 117-164) requires `liveness_present=True`, so without liveness files `hard_crash` cannot fire; but `borderline` is the catch-all, not `concluded`.
- **Rating:** **concerning** — this is a false world-model claim in user-facing docs. The dogfood already exposed it. The Phase 7 review (code review + proleptic CA1) explicitly accepted this with the user's approval to fix in Phase 8's honesty pass. The design seed (`docs/design-plans/2026-05-19-post-mortem-crash-detection.md`) documents both sites and the honest replacement text.
- **Forward impact:** Phase 8 is now responsible for substituting the honest replacement at the same time it fills `<PHASE-8-VERSION>`. `phase_08.md:550-556` enumerates the three sites by file:line. The risk is that Phase 8's honesty pass gets deprioritised under release pressure and the false claim ships to v1.0.0. The reviewer's view: Phase 8's plan amendment is concrete enough that the risk is bounded but the human should know the docs are deliberately ship-with-a-known-defect at the Phase 7 boundary.

**B2 — Wrapper-absent classification is described as "degraded heuristics" (notable).**

- **Design said:** "JSONL-tail-only heuristics" (design plan line 508, in Additional Considerations).
- **Implementation chose:** README adopts the same "degrades to JSONL-tail-only heuristics" wording (line 26). Both the design and the implementation are repeating the same imprecise framing.
- **Rating:** **notable** — the framing presents the no-wrapper case as a different operational mode (heuristics vs precise), whereas the truth is that crashes simply cannot be classified as such at all. This is closely related to B1 and the design seed flags it as the third overclaim site (entry 3 in `2026-05-19-post-mortem-crash-detection.md:99`).
- **Forward impact:** Phase 8's honesty pass already enumerates this as a third site to fix. No additional Phase 7 action — the design seed and `phase_08.md:550-556` cover it.

**B3 — Out-of-scope design-seed commit `6639b76` (benign).**

- **Design said:** silent on capturing dogfood findings into a design seed.
- **Implementation chose:** committed a 139-line design seed for post-mortem crash detection with 8 open brainstorming questions, *before* the smoke-test commit. The plan's "Components" list for Phase 7 does not include a design-seed artefact.
- **Rating:** **benign.** This is an architectural value-add. The repo's HALT-when-sideways constraint (`constraints.md`) explicitly endorses surfacing anomalies and not working around them; the design seed is the surfacing artefact for a structural gap discovered during dogfood. The Phase 8 plan was amended to bound the seed (do NOT implement; do honesty-pass overclaims; flag at completion).
- **Forward impact:** None negative. Provides a verified empirical algorithm and a list of open questions for the next brainstorming session. The forward-fitness question for Phase 8 is just "does Phase 8 implement the honesty pass without trying to bring in post-mortem detection?" — `phase_08.md:558` explicitly forbids the latter.

**B4 — `BATS_TEST_DIRNAME` anchoring in the smoke suite (benign).**

- **Design said:** the plan's bats template anchors `$CR` to `"uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery"` (relative path) and uses `'.claude-plugin/marketplace.json'` for the marketplace listing test. This works only when bats is run from the repo root.
- **Implementation chose:** both references use `${BATS_TEST_DIRNAME}/../...`, making the suite portable across invocation cwds. Verified to pass from `/tmp` per the code-review findings file.
- **Rating:** **benign.** Goes beyond the plan and is unambiguously an improvement. Pinned by the code-review's Minor #1 finding (it was originally a finding because the relative path was a regression risk for downstream invokers; the fix anchored to BATS_TEST_DIRNAME).
- **Forward impact:** Phase 8 will add `tests/test_claude_wrapper_liveness.bats` (per `phase_08.md` Task 2). That suite already uses `$BATS_TEST_DIRNAME/../plugins/...` (line 142 of phase_08.md), so the convention is now consistent across both bats files. Positive.

**B5 — Skill body assumes Claude as the executor of the AskUserQuestion gate (benign-but-worth-noting).**

- **Design said:** "iterate borderline/hard_crash entries and prompt for annotations via AskUserQuestion (the user can opt to skip annotation entirely)" — the design plan treats AskUserQuestion as the gating tool.
- **Implementation chose:** the skill body relies on Claude to invoke AskUserQuestion at runtime. The smoke bats suite does not exercise the AskUserQuestion path (it can't — that's a Claude-runtime concern, not CLI-pipeline).
- **Rating:** **benign.** This is intrinsic to the skill architecture; it could not be otherwise. Worth surfacing because forward-fitness review of Phase 8's UAT depends on Claude's runtime behaviour matching what the skill body says, and Phase 7's automated suite cannot pin that.
- **Forward impact:** Phase 8's UAT runbooks for AC5.6 and AC6.4 are human-run scripts that do not directly exercise the annotation flow. The annotation-flow UAT is implicit ("the user invokes the skill, AskUserQuestion fires, the user replies, `note` is invoked, regenerate shows the note"). If this becomes flaky in practice it will need its own UAT runbook later — not Phase 8's scope.

**B6 — Plugin layout assumes `denubis-plugins` marketplace name in the SKILL.md invocation path (notable).**

- **Design said:** the Existing Patterns section instructs absolute paths anchored at `~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-crash-recovery/...`.
- **Implementation chose:** matches the plan literally. So if the user installs from a renamed marketplace (e.g. a fork), the skill's CLI invocation will not resolve.
- **Rating:** **notable.** Repo convention is `denubis-` prefix and this is the canonical marketplace name; future-proofing is out of scope for v1.0.0. Worth surfacing because the user's persona description ("Local-only operation — no remote sync of plugin state beyond git") implies the marketplace path is stable, but a hostile reader would point out that any user installing this from a fork or rename will hit a runtime error in the skill, not a clear message.
- **Forward impact:** If the user (or another consumer) ever forks the marketplace under a different short name, the skill body will require a rewrite. No action for Phase 8.

## Forward Fitness

The question: will Phase 7's foundations support Phase 8's plans?

**Phase 8's bats lifecycle suite (`tests/test_claude_wrapper_liveness.bats`).** Phase 8 adds a new bats file alongside the existing one. The smoke suite uses `BATS_TEST_DIRNAME` anchoring; Phase 8's planned file (per `phase_08.md:142`) uses the same convention. The two suites will coexist with no shared fixtures. **Coheres.**

**Phase 8's `<PHASE-8-VERSION>` substitution.** Phase 7 deliberately leaves the placeholder in README. `phase_08.md:389` instructs the substitution to `2.32.2`. This is a mechanical edit; the README's structure provides a clean substitution site. **Coheres.**

**Phase 8's three-site honesty pass.** Phase 7 left the overclaims in place. `phase_08.md:550-556` enumerates the sites by file:line and provides the honest replacement text. The design seed (`docs/design-plans/2026-05-19-post-mortem-crash-detection.md:83-101`) is a second corroborating reference. **Coheres** — but only because the redundant references compensate for the deliberate ship-with-known-defect at the Phase 7 boundary. A hostile reviewer would flag: if Phase 8 implementor skips reading the design seed, the README site at line 25-27 has *two* halves of the overclaim and they need both fixing. The Phase 8 plan and the design seed both call this out explicitly.

**AC5.6 / AC6.4 UAT runbooks.** README's existing UAT runbooks (lines 46-71) are minimal — four-step numbered lists. `phase_08.md:438-501` provides much-richer runbooks with "Expected observation" lines and "It's wrong if" lines. Phase 8's plan is to *replace* the Phase 7 stubs. The README's UAT section structure is straightforward to overwrite. **Coheres** — Phase 7 explicitly stubbed these knowing Phase 8 would polish.

**README troubleshooting vs Phase 8 failure modes.** The Phase 7 README documents:
- `scan` exits with `requires Linux` (platform guard)
- `scan` exits with `does not provide reliable atomic-rename semantics` (filesystem guard)
- `scan` runs but reports 0 sessions (env-var debugging)
- Pruned a session you wanted to keep (preserves with note)
- Schema corruption (rebuild from filesystem)

Phase 8's wrapper failure modes (per `phase_08.md`):
- Wrapper writes `boot_id=unknown` on non-Linux (defensive, scan-side guard)
- Wrapper does not check filesystem atomicity (writer-side; reader catches it)
- SIGKILL of wrapper itself (signal-level case the writer can't clean)

The Phase 7 README does NOT yet document:
- "Liveness file shows `boot_id=unknown`" — possible on pathological Linux configurations where `/proc/sys/kernel/random/boot_id` is unreadable. The wrapper writes `unknown` and scan classifies it as boot-mismatch. The README's "scan runs but reports 0 sessions" item is the closest pairing but doesn't catch this case.
- "Wrapper exited but no liveness file was written" — diagnostic for users hitting permission errors on `~/.claude/run/`.
- "Wrapper writes liveness file but scan never sees it" — bridging the writer/reader boundary.

**Concerning gap for Phase 8 (forward-fitness):** the Phase 8 plan's Task 4 CHANGELOG entry mentions "Linux for the `scan` subcommand" and platform guards but does not specifically update the Phase 7 README's Troubleshooting section to add wrapper-bridging diagnostics. Phase 8 Task 5 polishes the UAT runbooks but is silent on Troubleshooting additions. If Phase 8 misses this, the v1.0.0 README will document scan-side failure modes but be silent on writer-side configuration issues that a new user will hit first.

What a hostile reviewer would flag:

1. **The Phase 7 docs say crash detection becomes operational with Phase 8's wrapper.** True. But the Phase 7 README's "Status" section says "v0.1.0 ships" — implying the v0.1.0 plugin alone is shippable as a unit. It is, technically, but the user value is near-zero without Phase 8. If a user accidentally installs only v0.1.0 (the dependency is documented in README but not enforced by the marketplace schema, as the design plan notes), they'll get a "concluded for everything" misclassification (per the overclaim text). The bridging-fix Phase 8 is making in the honesty pass needs to land cleanly or v1.0.0 retains a user-confusion surface.

2. **The smoke suite verifies CLI plumbing on an empty filesystem.** The bats header explicitly says "they do NOT verify crash-detection capability — that requires liveness files." This is accurate, and the framing comment was added in response to proleptic CA2. But the smoke suite as written would pass even if `classify.py::RULES` was deleted. That's because the empty filesystem produces no rows to classify. A hostile reviewer would note: a future regression that breaks classification of *any* concrete fixture would not be caught here. Phase 8's lifecycle suite covers writer behaviour but not classify-table behaviour either. The Phase 2 pytest suite (`test_classify.py`) covers it. The forward-fitness concern is: are the pytest and bats suites partitioned cleanly enough that a regression cannot fall between them? Today, yes — `pytest -q` runs the classify tests; bats runs the CLI plumbing. The boundary is clear.

3. **The skill body assumes the user runs the skill from a directory where `uv` can find `~/.claude/plugins/marketplaces/denubis-plugins/...`.** If the marketplace directory is not present (i.e. the user has not installed the plugin via marketplace, only checked out the repo), the SKILL.md invocations will fail with a `uv run` error. The README's installation step mitigates this (`claude plugin install`) but the skill body has no fallback or self-check. This is consistent with sibling plugins (per the design plan), so it's a marketplace-wide assumption, not a Phase 7 baked-in problem. Worth surfacing but not a Phase 8 blocker.

## Situated Accountability

This is a phase that touches user-facing surfaces — SKILL.md, README — encoding assumptions about who the user is, what cognitive load they have, what platform they run on. Not pure infrastructure.

**Whose perspective shaped the choices?**

The plugin is, by its persona doc, a single-user marketplace. The user is described as a "Heavy Claude Code user" on Linux desktop, fish shell, `claudew` wrapper, tmux. The Phase 7 work explicitly serves this user: the skill body assumes the user knows what UUIDs are, what `~/.claude/projects/` contains, what "Currently unfinished" vs "Ambiguous correlation" means without further explanation. The "Common rationalisations" table is written in the user's own voice ("I'll prune without `--dry-run`, `--confirm` is enough.") — a personal interlocutor framing. This is consistent with the project's situated context (a single, expert user) but worth naming.

**Who benefits from the choices?**

- The user gets a discoverable skill that orchestrates the CLI without forcing memorisation of subcommand sequence.
- The user gets the "manual-review-first" iteration order that surfaces the worst-classified entries (`unmatched`) first — a UX choice that respects the user's attention budget (per persona: "Limited attention budget").

**Who bears costs that aren't visible in the code?**

- **macOS / BSD users.** The README's Troubleshooting section explicitly says `scan` exits with `requires Linux`. The skill body's Step 1 invokes `scan` indirectly via `triage`. On macOS, the user will see the platform guard exit and the triage report will not render. The README documents this; the skill body does not pre-check it before invoking. A non-Linux user invoking `/denubis-crash-recovery:triage` will see a CLI error message and have to read the README to understand why. This is a cost to non-Linux users invisible at the skill-body level.
- **Users without `claudew` wrapper.** Phase 8 ships the wrapper patch; Phase 7's README and SKILL.md assume the wrapper has been used. A user running `claude` directly (not through `claudew`) writes no liveness files; the docs say this degrades to "JSONL-tail-only heuristics" (which is itself an overclaim, see B1/B2). The cost: a user who reads the README expecting their direct-`claude` sessions to be detectable will find them silently misclassified.
- **Sysadmins on multi-user installs.** The persona doc says "single human user" explicitly. A sysadmin who deploys this plugin for multiple users would hit collisions on `~/.claude/run/` if any of them shared `$HOME`. The Phase 8 wrapper uses `$$` (PID) which is OS-global, so it doesn't collide *within* a single `$HOME`, but a shared-`$HOME` setup would have cross-user PID collisions. Not a Phase 7 problem, but the architecture surface is silent on multi-user safety. Out of scope for a single-user marketplace.
- **Users whose `~/.claude/` lives on a network filesystem.** Phase 7 README documents `CRASH_RECOVERY_RUN_DIR` override for this case, which is correct. But a user who hasn't set the env var will get a refusing scan with a fix instruction — readable, but assumes the user can decide where to put the run dir. For someone on a corporate-network home directory, this can be a genuine "I cannot fix this" situation.

**What's absent?**

- **A "what does each classification mean" reference in the SKILL.md or README.** Both docs use `hard_crash`, `borderline`, `concluded`, `irrecoverable`, `unmatched` as known terms. The design plan's Glossary section defines some of these terms in plain English. The user-facing artefacts don't include a glossary entry. The first-time user of v1.0.0 (the headline release) will read "Ambiguous correlation" and "Needs investigation" in the report without knowing what they mean. The user-persona is explicitly the author of the marketplace, so they know — but if the persona ever shifts (other users, or future-self months later), this absence is a friction point.
- **An assessment of the failure mode that prompted the design seed.** The dogfood discovered the structural gap on 2026-05-18. Phase 7 documented it (design seed) and bounded it (Phase 8 amendment). But the user-facing README still claims the plugin "ships the full classification pipeline" (line 100). For an honest accounting of v1.0.0's capabilities, the README could acknowledge that post-mortem detection of pre-install crashes is not implemented yet. The design seed is internal-facing; the README is user-facing.
- **Acknowledgement that the v0.1.0/v1.0.0 split is "ship the plumbing, then ship the engine".** Phase 7's "Status" section gestures at this ("at which point crash detection becomes operational end-to-end") but doesn't name the v0.1.0 state honestly. A reader could conclude v0.1.0 is partial-functionality; the truth is v0.1.0 is "non-functional for the use case the plugin describes" until Phase 8 lands.

The implementor's perspective: the engineering choice was "ship Phase 7 to keep the implementation plan moving; defer the honesty fix to Phase 8 when the docs are already being edited." This is a reasonable optimisation against tooling friction. The cost: a (transient, by Phase 8) user-facing claim is known-false in v0.1.0 and the team accepts it.

## Architecture Doc Updates

**Existing architecture docs are largely up to date through Phase 6.** Phase 7's surface (SKILL.md + README + bats) is user-facing and not a new architectural-component layer. But several specific updates are warranted:

**Update U1 (Medium — should land in Phase 7 or early Phase 8 architecture-update pass).**
File: `docs/architecture/README.md`. Section: "Plugin Contexts (14)".
Change: this file currently lists 14 plugins. Crash-recovery is not in the list. A `denubis-crash-recovery/0-context.md` should be added to mirror the pattern of `denubis-plan-and-execute/0-context.md` etc.
Rationale: the architecture docs convention (`README.md:38`) is "these docs describe what exists in the marketplace now. Future or in-development work is not represented here. When a design plan lands and becomes code, its plugin gets a context (or its existing context gets updated)." Phase 7 brings the plugin to a state where its user-facing surface is shipped. The plugin "exists in the marketplace" enough to warrant a context. The plan does not call this out; the `architecture-update` skill is normally invoked at design or implementation milestones.
**Recommendation:** add `docs/architecture/plugins/denubis-crash-recovery/0-context.md` with a Level-0 diagram showing the user → SKILL.md → CLI → SQLite/JSONL/liveness-file → markdown render flow. Include the dependency on `denubis-plan-and-execute`'s wrapper patch as an external entity. Update `architecture/README.md:5` from "(14)" to "(15)". This is more naturally a Phase 8 or post-Phase-8-Finalization task — Phase 7 alone is not the natural moment, since the plugin isn't user-functional until Phase 8 ships. Flag as "during Finalization, before v1.0.0 release."

**Update U2 (Medium — high signal/cost ratio).**
File: `docs/architecture/constraints.md`. Section: "Crash-Recovery Discipline (implemented through Phase 6)".
Change: header should flip to "Phase 7" once Phase 7 lands. Add a row pinning the SKILL.md description-shape compliance (the QA constraint is at the project level, but the crash-recovery-specific check is `tests/test_skill_descriptions.py -k triage`). Add a row pinning the bats smoke suite as the AC1.2 automated proxy.
Rationale: the constraints doc has a row for every load-bearing test from Phases 1-6. Phase 7 introduces two new pinned tests (skill-description QA + bats smoke). The existing convention is "every constraint has a verification method"; without these rows, the bats suite is invisible at the architecture-doc level.

**Update U3 (Medium — surfaces the post-mortem detection design seed).**
File: `docs/architecture/constraints.md`. Section: "Crash-Recovery Discipline".
Change: add a row called "Known limitations: post-mortem crash detection" with the requirement text "Crash victims whose sessions started before the wrapper was installed cannot be classified as `hard_crash` — `classify.py::RULES` requires `liveness_present=True` for every `HARD_CRASH` outcome. Sessions in this state are classified `BORDERLINE` with reasons like `unknown_tail_kind` or `no_liveness_dangling_*`." Reference the design seed as the planned remediation.
Rationale: the design seed (`docs/design-plans/2026-05-19-post-mortem-crash-detection.md`) is currently a planning artefact with no architecture-level pointer. The architecture doc convention is to surface decisions and limitations that shape behaviour. A future maintainer reading `constraints.md` should be able to find the limitation without digging through implementation-plan history. The design seed is the right reference; the architecture doc is the right pointer.

**Update U4 (Low — naming consistency).**
File: `docs/architecture/glossary.md`. 
Change: add a glossary entry for `triage skill` distinguishing it from the CLI subcommand `crash-recovery triage`. The glossary defines a `skill` (line 9) and has entries for `boot_id`, `pid_alive`, `parse_tail`, etc., but no top-level entry for the user-facing `denubis-crash-recovery:triage` skill body that orchestrates the CLI. With Phase 7 shipping the skill body, this is a glossary-shaped term ("a markdown file under `plugins/denubis-crash-recovery/skills/triage/SKILL.md` providing structured instructions to Claude…").

**Update U5 (Low — Phase 8 dependency clarity in personae).**
File: `docs/architecture/personae.md`.
Change: the persona doc references `claudew` as the entry point. With Phase 8 about to add wrapper-side liveness behaviour, the persona's "Access patterns" could note that `claudew` includes the crash-recovery liveness-file behaviour as of Phase 8. Not urgent — the file documents *current* state, and Phase 8's wrapper change is a Phase 8 architecture-update concern.

**No contradictions found between Phase 7's artefacts and current architecture docs** — the docs are silent on Phase 7's specifics (skill body, README, bats) rather than wrong about them.

## Findings Summary

### High (count: 0)

None. The most-concerning issue (B1, the overclaim) is already routed through the proleptic-challenge process with explicit user acceptance and Phase 8 plan amendment.

### Medium (count: 4)

- **M1 (B1 / Forward Fitness):** Phase 7 ships with a known-false claim in user-facing docs (README "every session classified `concluded`"; SKILL.md identical claim). The fix is bounded by Phase 8 amendment + design seed. **Severity Medium not High** because user has accepted with full visibility and Phase 8 plan explicitly enumerates the fix sites by file:line. Becomes High if Phase 8's honesty pass is skipped or partial.
- **M2 (Forward Fitness / Architecture Doc):** Phase 7 README's Troubleshooting section lacks entries for wrapper-bridging failure modes (boot_id=unknown on pathological Linux, wrapper-write permission errors, writer/reader bridging). Phase 8's plan does not explicitly extend Troubleshooting. Recommend Phase 8 Task 5 (UAT polish) also extend Troubleshooting with wrapper-side modes.
- **M3 (Architecture Docs U1):** No `denubis-crash-recovery/0-context.md` exists despite the plugin's user-facing surface now being shipped. Architecture docs README still says "Plugin Contexts (14)". Recommend addition during Phase 8 or Finalization.
- **M4 (Architecture Docs U2, U3):** `constraints.md`'s "Crash-Recovery Discipline" section needs Phase 7 update (header bump + 2 new rows for SKILL.md QA + bats smoke + post-mortem limitations row referencing the design seed).

### Low (count: 6)

- **L1 (D1):** SKILL.md description text differs from plan example (forced by repo QA constraint); compliant alternative preserves intent. No action.
- **L2 (D2):** SKILL.md adds a fourth "Common rationalisations" row beyond plan spec. No action — strengthens gating.
- **L3 (D3):** README adds Status section not in plan. No action — accurate.
- **L4 (T1 / B5 / B6):** Several traceability gaps and assumptions are non-automatable today and should remain as review-time considerations, not test requirements (skill runtime behaviour, marketplace path assumption, single-user persona).
- **L5 (T2):** bats `prune` test asserts non-zero exit code rather than `==1` specifically. Candidate fitness function (tighten exit-code assertion).
- **L6 (T1):** README dependency-text presence has no automated check despite the plan suggesting a `grep -q` verification step. Candidate fitness function (add to bats suite).

## Overall Assessment

**Coheres, with the explicit known-defect (B1) tracked into Phase 8 and architecture doc updates queued for Phase 8 or Finalization.**

The implementation matches the design plan's intent for Phase 7 (user-facing skill + README + smoke suite) closely. The most significant divergences — the overclaim about `concluded` classification, the design-seed commit, the BATS_TEST_DIRNAME anchoring — are all justified responses to surfaced realities (QA-rule conflict, dogfood discovery, code-review finding) and have been routed through the appropriate downstream mechanisms (Phase 8 plan amendment, design seed, fix commit). No erosion was detected; the drift items are mostly response-to-constraints decisions that preserve intent.

The traceability picture is mostly clean. AC1.2 has the closest automatable proxy (marketplace.json listing) plus skill discoverability via the QA test on SKILL.md description. AC8.1 is doc-only and not automated; a small bats addition would close that gap. Two minor fitness-function candidates (prune exit-code specificity, dependency-text presence assertion) are straightforward but were not in scope for Phase 7's bats suite.

Forward fitness for Phase 8 is **good** with one watchpoint: the honesty pass needs to land cleanly across all three enumerated sites or v1.0.0 ships with a residual false claim. The plan amendment and design seed redundancy mitigate this. Troubleshooting-section extension is a softer recommendation worth raising during Phase 8 review.

Situated accountability work surfaces several absent-stakeholder considerations (macOS users, multi-user installs, network-home users, future-self-as-other-user). The "single Heavy Claude Code user on Linux desktop" persona is the explicit design centre; the absent-stakeholder costs are acknowledged out-of-scope rather than addressed. The most user-felt absence is a "what does each classification mean" reference in the user-facing docs — the Glossary in the design plan covers it, but the README does not surface it.

Architecture doc updates are queued (M3, M4, U4, U5) — these can fold into Phase 8's architecture-update pass or the post-Phase-8 Finalization step.

**Requirements before Phase 8 begins:**
1. Phase 8 implementor must read both `phase_08.md:550-556` AND `docs/design-plans/2026-05-19-post-mortem-crash-detection.md:83-101` before editing the README and SKILL.md — neither file alone is sufficient (both halves of the README:25-27 overclaim need fixing).
2. Add the M2 troubleshooting extensions to Phase 8 Task 5's scope if possible.
3. Add M3 and M4 architecture-doc updates to Phase 8's scope or to Finalization (decision is the user's).

**Optional follow-ups (not blocking):**
- L5 and L6 fitness-function candidates can fold into Phase 8's bats work or Phase-8-Finalization test-requirements.md generation.
