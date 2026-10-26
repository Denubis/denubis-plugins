> Produced by the 2026-10-09 design fanout.
> Landed on 2026-10-25 under ADR 0041; exchange references rewritten, with no other change.

# 06 Authority: proposal

Opus at xhigh, named by Brian 2026-10-09. **O** observed by me today; **D** read today in vendor docs or schema, not seen at runtime; **I** inferred.

## 1. Challenge

Approval requests and decisions must travel through the Record so Brian sees them in one place and a supervisor can act on one by reference, while neither the Record nor mail ever decides. The assumption protected is property 7: every approval names one exact request, one decision maker, and the policy or mandate it rests on. Message text, a role edge, repetition and timeout stand in for none of those.

**Contradictions flagged, not resolved:**

1. Function 6 says "decided by the approver or Brian". DR12 lets a mandated supervisor decide residual requests. Main says "Codex's per-command sandbox dialogs belong to the driver" (SKILL.md:295, O), and the approver's hash pin on the supervisor script ignores arguments, so `--approve` runs unprompted (O). Q3.
2. Property 7: "this system never makes Claude an approver for Claude". Brian today: "any … to supervise any other". Q1.
3. Function 1 keeps decisions out of the Record; property 11 wants approval decisions and mandates reconstructable. I treat both as operational state. Dispatcher to confirm.
4. DR8 rejected the `PermissionRequest` hook for Codex app-server identity. I use the hook differently (2.2); unproven until T2 and T3 pass.

## 2. Mechanism

### 2.1 What each vendor exposes

- **Claude Code 2.1.295** (O): `PermissionRequest`, absent from user settings and plugin hook files (O). It carries `session_id` and `prompt_id`, "without `tool_use_id`" (D).
- **Codex 0.160.1** (O; the brief says 0.157–0.159): `PermissionRequest`, with the approver and supervisor relay registered at 5 s (O). It carries `session_id` and `turn_id`, and no tool-call id (D).
- **agy 1.3.1** (O): no such hook; the approver's `PreToolUse` returns `ask` (O). It carries `conversationId` and `stepIdx`, uniqueness unverified (D).

Claude and Codex carry `tool_use_id` only on `PreToolUse` and `PostToolUse`. Each hook returns a typed allow or deny; default timeouts are 600 s, 600 s and 30 s (all D). Sources: each vendor's hooks page, and the Codex schema at `rust-v0.160.1`.

### 2.2 Intake: the request is the hook invocation

`authority-intake` is one command registered at that hook. Where the approver already sits there (Codex, agy), intake runs the installed approver frontend first and passes `allow` or `deny` through unchanged, so policy stays first and terminal (DR12). On Claude, reaching `PermissionRequest` already means policy neither allowed nor denied (I).

On `ask` or no opinion, intake mints `request_id` and inserts one row before anything else. Two identical commands in one turn are two invocations, so two ids. No content hash or turn id stands in for identity.

```sql
approval_request(request_id uuid pk, vendor, session_address,
  vendor_locator jsonb,                                -- never a key
  tool_name, input_sha256, input_text, cwd, pane,      -- text pruned on close
  approver_verdict, approver_reason, danger, state)
approval_decision(request_id pk -> request, outcome,   -- allow_once | deny
  decider_kind, decider_address, mandate_id null, grounds not null)
approval_application(request_id pk -> decision, method, result, evidence)
approval_mandate(mandate_id pk, ruling_ref, supervisor_address, supervisee_address,
  request_classes[], cwd_root, expires_at, max_decisions, used, revoked_at)
```

The primary keys make one decision per request, and one application per decision, a constraint. Verdicts and request classes are read from the approver at the point of use, not redeclared.

### 2.3 Who records a decision

One database function, `authority.decide`, is the only writer of `approval_decision`.

- **Brian on the surface**: `decider_kind = brian`.
- **Brian at the pane**: nothing is issued; the request closes `resolved_at_pane`.
- **A mandated supervisor**: `authority decide --request ID --allow|--deny --grounds TEXT`. Its address comes from process attachment, never a flag. The function checks the mandate (2.5); a refusal names the failing bound (ADR-0071) and leaves the item with Brian.

Granting a mandate and deciding as Brian are separate executables, so a hash pin on `decide` cannot cover them (ADR-0023). They refuse under any agent ancestor process, and the approver should hard-deny them, which all three frontends can do (O). An `ask` is not enough: Codex here has `network_access = true` (O).

### 2.4 Applying a decision by reference

**A. Hook return (primary).** Intake then waits for a decision row on its own `request_id`, prints the vendor's typed allow or deny, and records the application. The decision lands on exactly the call that asked, because the vendor is still waiting on that invocation. No key is pressed and no standing grant is emitted (`updatedPermissions`, `permissionOverrides`). On timeout it prints nothing and the native dialog appears.

Intake holds only when a live mandate names this session as supervisee, or when Brian answers on the surface and is not focused on that pane. Otherwise it returns at once: today's behaviour plus a visible item. Hold length is Brian's number.

**B. Guarded pane key (fallback).** `approve --request ID` on the Function 3 actuator. It requires an unapplied decision row for that id, the pane's live session to match, exactly one open request for that session, the dialog's command to equal `input_text`, and the narrow affirmative only (existing `approval_choice`, O). It sends one key, never resends, and records `uncertain` if no typed event confirms. Codex only, at first.

The verb takes a request id and nothing else. No table links a message to a decision.

### 2.5 What a supervisor may decide

Only Brian creates a mandate. It binds one supervisor address to one supervisee address, bounded by class, directory, expiry and count.

A mandated supervisor may allow once, or deny, a request that the approver left as `ask` or no opinion, from its exact supervisee, inside those bounds, and neither DANGER-marked (ADR-0051) nor ambiguous. It records grounds (ADR-0022).

It may not override a policy deny, issue a standing grant, decide for its supervisee's supervisee, pass the mandate on, decide its own requests, or act after either address changes. Doing nothing is abstention. A class approved repeatedly under mandate is a missing approver rule (ADR-0002), reported to Brian.

### 2.6 Received messages

A message is data. It may cause the recipient to read, reply, acknowledge, and work under its own session's approver. It may not answer a dialog; create or alter a request, decision, mandate or role edge; change configuration; run a slash command; or be typed into a pane with an open request. "Brian said yes" in a body is not Brian. Claude applies the same rule to peer messages: "It can't approve anything" (D).

Loop limits: one notification per request per recipient (ADR 0009); a hook-generated message never triggers another; per-sender rate limit and identical-repeat drop, as Claude does natively (D).

Version pinning follows approver ADR-0038: hook contracts, Codex session files and dialog grammars each list their vetted vendor versions. Outside them a surface degrades (no hold, no pane key) and raises one item.

## 3. Verification

- **T1 No tool-call id at dialog time.** A live Claude or Codex payload carrying one.
- **T2 Identical requests stay distinct.** The same command twice in one turn giving one row, or one hook call for a grouped prompt.
- **T3 Hook return lands on that call only.** Under a 20 s hold: the dialog shows anyway, the decision is ignored, another call is delayed, or the hook is killed.
- **T4 A message cannot decide.** A forged "R approved by Brian" message, then `approve --request R`, not refused.
- **T5 Mandate bounds hold.** Accepting any of: wrong supervisee, expired, exhausted, same family, DANGER, policy deny, second decision, supervisee's supervisee.
- **T6 One application per decision.** A second key after the actuator is killed mid-application and restarted.
- **T7 Agents cannot reach Brian-only verbs.** `grant` succeeding from an agent's shell tool (control: works from Brian's fish).
- **T8 Survives a crash (property 11).** Killing every hook, pane and viewer loses or settles an open request.

## 4. Interfaces

- **Record**: four tables, one function; retention is its owner's number.
- **Identity**: payload to address at intake; caller to address from process attachment; a fresh launch gets a new address, which voids mandates.
- **Deliver**: the actuator hosts path B and refuses sends to an address with an open request; per-address Stop and UserPromptSubmit events close pane-answered requests.
- **Acknowledge**: acknowledging a decision notice proves receipt, never closure.
- **Supervise**: a role edge supplies the pair and grants nothing; verbs are `decide` and `approve --request`.
- **Human surface**: shows each open request with its approver reason; offers allow once, deny, and mandate grant or revoke; runs outside any agent.
- **Approver project**: one deny rule and a pin for `decide`, for Brian to commission there.

## 5. Failure modes

- **Record unreachable at intake.** Pass the approver's output through with no hold, so the native dialog appears. Never allow.
- **Intake crashes or times out.** Expected to leave the normal prompt (I; unverified, section 7). agy keeps the approver's deny on failure (O).
- **Decision arrives after the hold.** Stays `decided`; path B if its guards pass, else the surface says to press at the pane.
- **Brian answers at the pane first.** Path B finds no dialog and refuses; the request closes `resolved_at_pane`.
- **Session dies with a request open.** Marked `orphaned`; removal is the surface's rule.

## 6. Rejected

- **Codex app-server identity** (DR8): no Claude or agy equivalent; whether an outside client can answer a TUI-owned request is unverified (report 03).
- **Pane key as primary** (today's `--approve`): no request identity, races the dialog (SKILL.md:220, O), one screen grammar per vendor.
- **Grants keyed on command signature**: two identical requests become one, the laundering DR8 names.

## 7. Could not check

- No live `PermissionRequest` payload from any vendor: every identity claim is D. The Codex schema came through a summarising fetch tool and Context7, not byte-verified.
- Whether Claude draws the dialog while `PermissionRequest` hooks run, and whether a `PreToolUse` `ask` leads to `PermissionRequest` (docs silent).
- Whether Codex waits for every concurrent hook, and what a timed-out hook yields.
- agy at runtime: `stepIdx` uniqueness, timeouts above 30 s.
- Claude Mods `tool.check`, which wraps the permission decision (D); another session has it.
- Not read: the `project_open-questions.md` file in the main checkout's notes directory for the approver (144 KB).

## 8. Questions for Brian

1. May a same-family supervisor (Claude over Claude) hold an approval mandate? Default: no. Blocks unattended same-family supervision.
2. Do you want to answer approvals on the side monitor, or only see them there and answer at the pane? Default: answer there; the focused pane still prompts natively. Blocks whether intake holds at all.
3. When you say a session may drive another, should that still mean "may approve every narrow one-command dialog", or listed classes per pair? Default: today's meaning as a named template, minus DANGER-marked requests. Blocks mandate defaults and the fate of bare `--approve`.
4. May intake wrap the approver's Codex and agy hook entries and add a Claude `PermissionRequest` entry? Default: yes. Blocks intake on all three vendors.
