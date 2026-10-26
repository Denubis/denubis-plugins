> Produced by the 2026-10-09 design fanout.
> Landed on 2026-10-25 under ADR 0041; exchange references rewritten, with no other change.

# 06 Authority: verification

Verifier: Fable 5.1 at high, named by Brian 2026-10-09. Artifact:
`06-authority-proposal.md` as read 2026-10-09. Rulings applied: ADRs 0011-0013.
Sources: Claude hooks and cross-session docs, Codex hooks doc and its
`permission-request.command.input.schema.json` at `rust-v0.160.1`, agy `hooks.md`,
August DR8/DR12, approver ADRs 0002-0071 as cited, its `CLAUDE.md` and frontends,
`rules/trusted_scripts.json`, verifications 05 and 07. **C** confirmed, **R** refuted,
**U** unchecked. Nothing typed; no settings, hooks.json, transcript, log or process read.

## Verdict

Identity and the message rule hold. The mandate model is refuted by ADR 0013. One safety
race (pane deny, then a late hook allow) needs a live test before any supervisor hold on
Claude.

## Claims

1. **No tool-call id at dialog time.** **C.** Claude doc: PermissionRequest receives
   `tool_name` and `tool_input` "but without `tool_use_id`"; `prompt_id` is a common
   field, "UUID identifying the user prompt currently being processed", so per prompt,
   not per request. Codex schema at `rust-v0.160.1`: eleven properties
   (`agent_id`, `agent_type`, `cwd`, `hook_event_name`, `model`, `permission_mode`,
   `session_id`, `tool_input`, `tool_name`, `transcript_path`, `turn_id`),
   `additionalProperties: false`, no request id; the proposal's "summarising fetch"
   caveat is closed. agy: `conversationId`, `stepIdx` only. Claude also puts
   `tool_use_id` on PermissionDenied and PostToolUseFailure; "only" is over-stated,
   immaterially.

2. **Timeouts 600/600/30 s, typed allow or deny.** **C.** agy hooks are "merged and
   executed sequentially" and "block the agent loop". Timeout behaviour is documented
   only for Claude ("renders no decision", "on most events").

3. **Invocation identity vs verifier 05 claim 11.** **C, two gaps.** A uuid per
   invocation does not collide. Gap (a): proposal 05's announce-once key must take this
   uuid or the second identical request is still swallowed; neither proposal says so.
   Gap (b): retiring a pane-answered row. The proposal uses `Stop`/`UserPromptSubmit`,
   which fire at turn end, so the row and held hook stay open mid-turn. ADR 0012's
   candidate `PermissionDenied` is refuted: it "only fires in auto mode: it doesn't run
   when you manually deny a permission dialog". A pane **deny** on Claude has no
   hook-observable event. A pane **allow** reaches `PostToolUse`, whose `tool_use_id` the
   request row lacks, so the match is by `(session, tool_name, tool_input)`, ambiguous
   for identical commands. T3 must cover that case and name the heuristic.

4. **"On timeout … the native dialog appears"; "Brian answers at the pane first → path
   B finds no dialog".** **R for Claude.** Beyond the field reports ADR 0012 accepted,
   the doc itself implies the prompt is up while the hook runs: the `permission_prompt`
   "timer starts when the permission prompt appears", and "If you or a PermissionRequest
   hook answer sooner, Claude Code doesn't run `permission_prompt`". The hold is a second
   answer path, never a replacement; "hold only when Brian is not focused on that pane"
   is moot on Claude. Codex: doc silent on drawing the prompt during a synchronous hook
   (**U**).

5. **The unresolved race.** **U, consequential.** No doc says what Claude does with a
   hook `allow` returned after the user answered the dialog; #79651 (via verifier 07)
   says the hook is not cancelled. Under the proposal a mandated `decide --allow` inside
   the hold, after Brian pressed No at the pane, makes intake print `allow`; the Record
   cannot refuse it because it learns of the pane deny only at turn end (3b). If Claude
   applies it, the tool runs against Brian's explicit deny. Falsifier: hold 60 s, deny at
   the pane, return `allow` at 30 s, check whether the command ran.

6. **Mandate model vs ADR 0013.** **R as written.** 0013 "replaces the class-list and
   blanket-template readings": the grant is the supervisor's judgement against the task
   statement the mandate must carry ("A mandate without a task statement grants
   nothing"); wider implications pause and escalate to the needs-Brian list and the
   open-questions file; each decision records request, task judged against, one-line
   reason. The proposal's `approval_mandate` has `request_classes[]`, `max_decisions`,
   `used`, `cwd_root`, `expires_at` and no task statement; its DANGER test (ADR-0051, a
   delete-shaped marker) is narrower than "implications beyond what I intended"; and
   "Doing nothing is abstention" makes escalation silent. Must change: `task_statement
   not null` on the mandate; task reference and reason on `approval_decision`; an explicit
   `escalate --request ID --question` verb writing both destinations; `request_classes[]`
   stops being the grant. T5's mechanical cases survive, but "inside every rail, outside
   the task" is not mechanically testable; the audit row is the only check, and T5
   should say so.

7. **"The hash pin on the supervisor script ignores arguments, so `--approve` runs
   unprompted."** **U.** `rules/trusted_scripts.json` pins `codex_supervisor.py` by
   digest as "his standing decision about this exact build" and names `--approve` in its
   rationale, supporting the reading; I did not trace the consuming rule's argv handling.
   A bare `--approve` is the pane-key path §6 rejects (SKILL.md:216-220 **C**); unruled.

8. **Intake wraps the frontend and reads verdict, reason, DANGER.** **R in mechanism.**
   `codex_permission.permission_output` returns `None` on `ask`/no opinion and
   `codex_approver.main` prints nothing; reason and marker exist only in the classifier
   result and the log. Wrapping stdout yields nothing on exactly the requests intake
   handles; intake must call `pipeline.classify_pipeline` directly. agy frontend:
   no-opinion → `ask`, deny-on-failure, **C** in source.

9. **Codex combination; no standing grants; policy first.** **C.** "any `deny` wins";
   `allow` "proceed[s] without the approval prompt"; `updatedPermissions` "fail closed
   today"; Codex "waits for a command hook to finish". Claude: "a hook returning `allow`
   doesn't override a matching deny rule". The 5 s `hooks.json` registrations are
   verifier 07's observation.

10. **Received messages cannot decide.** **C verbatim.** "It can't approve anything: a
    message from another session never counts as your consent, so it can't answer a
    pending permission prompt on your behalf"; "Commands don't run"; "rate-limits repeated
    messages per sender, drops identical repeats arriving within a short window".

11. **Citations.** ADR-0023, ADR-0038, DR8, DR12 **C**. ADR-0071 is a fair gloss.
    ADR-0022 governs the register's editorial rule, not runtime decisions; DR12 is the
    source for grounds, and its class and consequence-bound columns are what 0013
    supersedes.

12. **Q1-Q4** are answered by ADRs 0011, 0012, 0013, 0012; drop them and cite.

## Strongest failure in Brian's environment

Claims 5 and 3b together. On Claude the dialog is up from t=0 and Brian answers there by
habit across ~20 windows; the hook lives on; the Record learns of his answer at turn end;
a supervisor's `decide --allow` inside that window reaches the vendor as a typed allow,
and nothing rules out the tool then running. Until the live test settles it, intake must
not hold a Claude hook for a supervisor mandate; holding for Brian's own surface answer
is Brian against Brian and stays.

## What survives

Per-invocation uuid identity; the four tables minus class columns, plus a task
statement; `authority.decide` as sole writer with one-decision-per-request keys; path
B's Codex guards; the message rule; policy-first ordering; surface answers through the
held hook; the §6 rejections; T1, T2, T4, T6-T8.

## Live tests needed

- Claude 2.1.295: pane deny, then hook `allow` inside the hold: does the tool run?
- Claude: identical command twice in one turn gives two invocations; subagent dialogs
  fire the hook, and with which `session_id`.
- Codex 0.160.1: prompt drawn during a synchronous hook; timeout falls to the prompt;
  `apply_patch` and MCP approvals fire the event.
- Out of my scope: `--approve` allowed regardless of argv under the pin (approver policy
  trace); `network_access = true` in Codex config.

## Questions for Brian

- With the task statement as the grant, do `expires_at`, `cwd_root` and `max_decisions`
  stay as e-stop rails? Blocks the mandate schema. Default: keep `expires_at` and
  `cwd_root`, drop `max_decisions` and `request_classes`.
- Is bare `codex_supervisor.py --approve` retired for agents once path B exists? Blocks
  what the pin authorises.
