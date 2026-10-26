> Produced on 2026-10-09 by the reviewing Codex session.
> Moved from `.notes` on 2026-10-26 under ADR 0043; links rewritten, with no other change.

# Cross-provider messaging draft: critical review

Review and recording date: 2026-10-09. Author: the reviewing Codex session.

This records the review requested by Brian and his subsequent instruction to save it
with details. Brian then invoked `epistemic-humility` and added:

> also, we don't want ever more epicycles. Make sure we have evidence to collect or confirm around problems

That instruction governs how to use this note: collect discriminating evidence before
adding machinery. The findings are review input, not accepted architectural decisions,
implementation authorization, or six new requirements to build.

## Artifact and evidence boundary

The reviewed artifact is
[00-cross-provider-messaging-design.md](00-cross-provider-messaging-design.md),
marked Draft, 2026-10-09. Its SHA-256 at recording was:

`f95f9c9a1639ab2053d140c5bd763102568af17980c37c1479a262d6a37748cd`

Line numbers below refer to that version. The file is in a gitignored directory;
these references depend on retaining that directory. The hash identifies the reviewed
bytes but does not preserve them. If the hash changes, re-read the relevant section
before carrying a finding forward.

Evidence grades used here:

- **Observed in the artifact:** text, schema, or test definition read directly in the
  draft or another named local document. This does not mean runtime reproduction.
- **Reported:** a previous proposal or verification describes a vendor observation or
  documentation claim. This review did not independently reproduce that observation.
- **Inferred:** a failure scenario follows from the stated mechanism under named
  conditions. It remains a candidate until a discriminating check establishes those
  conditions or the specification itself settles the issue.

The review read the draft, all seven verification reports, relevant proposal sections,
the brief, the open tickets, the August properties, and relevant ADRs. It also opened
the October raw records cited for ADRs 0011–0020. This was not exhaustive verification
of every authority reference: the brief's unlocated quotations and the original human
sources for the August properties were not recovered. Raw line 1033 cited in the draft
is a queue-operation record rather than a normal user-message record; this review does
not use it as independent proof of an architectural ruling.

No scratch sessions, database connections, vendor probes, or executable fault-injection
tests were run. External documentation and runtime claims in previous verifications
remain reported evidence here. The review does not establish that the implementation
has any of these bugs. The draft itself says phase 0 has not run.

## How to act without adding epicycles

For each finding, first inspect whether the existing implementation, vendor contract,
or proposed test already resolves it. Then run the smallest authorized check that can
distinguish failure from success. Preserve the input, event order, relevant record rows,
and observable effect. A test that only counts rows is insufficient when the claim is
about which command ran or which body reached a model.

Do not pre-emptively add a broker, service, reconciliation loop, event ledger, or new
policy layer on the strength of this note. Prefer, in order: withdraw a refuted finding;
clarify an underspecified existing mechanism; strengthen one existing test; disable or
remove an unsafe fallback; add a mechanism only when the remaining demonstrated
failure requires it. These are review recommendations, not newly adopted architecture.

The scratch-session permission and M15 remain prerequisites where the draft requires
them. This note grants neither. Reading sources and specifying fixtures can proceed
without those live actions. Each evidence check below is proposed, not completed.

## F1 — Approval occurrence identity is lost at the pane boundary

**Priority:** high if the pane fallback is retained. **Grade:** observed matching rules;
inferred misapplication scenario.

**Sources:** draft lines 164–176 and 350–359; acceptance AC9 and tests T25/T28;
[authority proposal](06-authority-proposal.md),
section 2.4; [authority verification](06-authority-verification.md),
claims 1 and 3.

The draft gives each hook invocation a unique request ID. Its pane fallback checks
whether the displayed command equals the request's command. Its PostToolUse retirement
uses session, agent, tool, and input hash, choosing the oldest open request. These
identify identical content but do not, by themselves, identify the dialog occurrence.
The proposal had an additional “exactly one open request” guard that the synthesis
does not explicitly retain. That guard could refuse some ambiguous cases; its presence
and coverage should be checked before declaring the fallback defective.

**Candidate sequence:** request A is denied at the pane; its row remains open until
retirement evidence arrives; identical request B appears. Applying A's decision by
matching command text could act on B. An execution event for B could likewise retire
A under oldest-first matching. This depends on overlapping stale state being possible;
the review did not reproduce that overlap on either vendor.

**Evidence to collect:** extend T25/T28 to capture A's hook ID, the pane denial, B's hook
ID, both request lifecycles, and the exact command execution. Attempt A's application
while B is displayed. Include a control in which a correctly bound current request
does apply, so a permanently refusing adapter cannot appear correct.

**Result that withdraws or narrows this finding:** an existing invariant demonstrably
retires A before B can become actionable, or the application path refuses the stale
ID while accepting the current one. Document that invariant rather than creating a
second identity system. Two distinct database rows alone do not settle the finding.

**Smallest response if confirmed:** refuse ambiguous pane application and retain exact
held-hook application where supported. Only investigate stronger dialog binding if the
fallback remains necessary. The disposition of bare `--approve` is still M11.

## F2 — The late-answer gate is narrower than its stated uncertainty

**Priority:** high before enabling competing Claude answer paths. **Grade:** observed
gate scope; runtime race reported and unverified.

**Sources:** draft lines 361–372 and T23;
[authority verification](06-authority-verification.md),
claims 4–5 and “What survives”; [ADR 0012](../../architecture/decisions/0012-approvals-answerable-from-the-surface-and-the-pane.md).

Pending T23, the draft refuses supervisor decisions on Claude but allows Brian's
surface answer through the same held-hook mechanism. It explicitly acknowledges that
a stale surface answer could override his pane denial if T23 fails. The previous
verifier endorsed this exception as “Brian against Brian”; that is an argument about
the actor, not evidence of first-answer-wins behavior.

**Evidence to collect:** use the already-planned T23: deny at the pane, then return a
late hook allow, recording whether the command executes. Exercise the surface path
that would supply that result and inspect its stale-row behavior. Retain the vendor
version and trace. No separate concurrency subsystem is justified before this test.

**Result that withdraws or narrows this finding:** the installed vendor reliably ignores
the late answer and the application retires or disables the stale surface item. Then
cite the result for both decision origins and remove the artificial distinction.

**Smallest response if unresolved or failing:** gate both origins of competing held-hook
answers, rather than treating the human-origin path as proven safe. This recommendation
does not revoke the desired two-surface behavior; it concerns when that mechanism can
claim to implement it. If all phase-0 tests are already mandatory pass gates for every
answer path, make that explicit and remove the contradictory exception in prose.

## F3 — A model-issued shell call is insufficient evidence of body receipt

**Priority:** high for the meaning of acknowledged. **Grade:** observed audit definition;
inferred false-positive case already acknowledged as possible by the draft.

**Sources:** draft lines 256–271, AC1, and T19;
[acknowledge proposal](04-acknowledge-proposal.md),
section 2; [acknowledge verification](04-acknowledge-verification.md),
claim 2.

The draft requires `read` before `ack` and proposes auditing acknowledgements against
model tool-call records. A single model-issued shell pipeline could read the body,
extract its code, acknowledge, and return only a success indicator. The model initiated
the call, but its context need never contain the body. An audit of caller provenance
alone would accept that record. This is distinct from M14: no sub-agent is needed.

**Evidence to collect:** compare a normal read-result-then-ack exchange against that
single-call pipeline. Capture the actual tool output delivered to the parent model,
the acknowledgement row, and the audit verdict. T19's hook-driven negative case is
useful but does not discriminate this case.

**Result that withdraws or narrows this finding:** the existing audit refuses the
pipeline because it establishes body-bearing output before a later acknowledgement,
or an existing command boundary prevents the pipeline. Specify that actual boundary.
Even the stronger evidence establishes delivery into context, not comprehension.

**Smallest response if confirmed:** correct the audit criterion or narrow the receipt
claim explicitly. Do not add a new receipt service merely to move the same unproven
assertion elsewhere. If auditing is retrospective, also state what consumers may rely
on before the audit; the current wording should not imply preventive enforcement.

## F4 — The ping claim and the external delivery can diverge after a crash

**Priority:** high for recovery semantics. **Grade:** observed operation ordering;
inferred crash window.

**Sources:** draft lines 239–252, “Failure and recovery” listener entry, T3 and T13;
[acknowledge proposal](04-acknowledge-proposal.md),
“Retry and give-up,” which explicitly contemplated a crash between claim and display.

`claim_ping_v1` stamps `pinged_at` before the winning channel displays the pointer.
If the process dies after commit but before output, other channels lose the claim even
though no pointer arrived. The draft's assertion that the next hook pings after a
listener failure therefore needs qualification or a recovery path. The durable body
is not lost. Some later nudges may recover attention; this finding is about the promised
initial ping and fallback behavior, not universal permanent mail loss.

**Evidence to collect:** kill the channel immediately after the claim commit and before
submission; trigger the next eligible hook and inspect its output and record state.
Use a recipient without a supervisor so a separate nudge cannot hide the result.
Separately stop the channel after submission but before recording confirmation, to
check that recovery does not repeat an uncertain external action blindly. Include a
normal successful delivery as the positive control.

**Result that withdraws or narrows this finding:** an existing claim-release or recovery
rule permits the known-unsent case to recover while preserving the uncertain case.
Alternatively, the accepted contract explicitly treats the claim as one attempt and
provides a demonstrated later recovery route. Do not describe an attempt as delivery.

**Smallest response if confirmed:** clarify the attempt/confirmation semantics and use
the existing attempt or act machinery if sufficient. A lease or outbox is not prescribed
by this review. Do not promise exactly-once external delivery merely because a database
claim has one winner.

## F5 — Identifier presence does not establish preservation of the body

**Priority:** high before enabling pruning. **Grade:** observed prune predicate;
inferred data-loss exposure under incomplete transcript content.

**Sources:** draft lines 121–134 and 205–209;
[record verification](01-record-verification.md),
claim 12; [brief](BRIEF.md), transcript
retention quotation and its accompanying interpretation.

The written pruning condition looks for each message ID in named transcripts. Pointer
messages already contain IDs. An ID's presence therefore does not prove that the body
survives there. The preceding review used a send-via-file example; that specific CLI
feature is not established by this draft and is not necessary to the narrower finding.
Truncated output, pointer-only occurrences, and the F3 case are candidates to test,
not asserted observations of the installed transcript writers.

**Evidence to collect:** give the proposed retention check controlled transcript
fixtures containing (a) the ID only, (b) the ID with a truncated or different body, and
(c) the full matching body at a resolvable occurrence. Keep all other settlement and
retention conditions equal. Also inspect one real permitted send/read exchange to
determine what each vendor actually persists. The check must retain (a) and (b) if
its justification for deletion is that the original body remains recoverable.

**Result that withdraws or narrows this finding:** the actual predicate already
validates the complete body, or a demonstrated invariant makes every qualifying
occurrence body-bearing. In that case, repair the prose and retain the relevant test.

**Smallest response if confirmed:** check the body at the retained occurrence, with
digest comparison where useful; otherwise retain the row. This need not introduce a
new archive. M12 still owns whether cited mail needs a separate file: this finding
concerns the evidence for pruning ordinary mail, not that unresolved storage policy.

## F6 — Exactly-once context advancement is underspecified

**Priority:** medium; specification gap rather than reproduced failure.
**Grade:** observed mismatch in the level of mechanism detail.

**Sources:** draft lines 105–117 and 213–224, AC2/AC3, T18/T30;
[identity proposal](02-identity-proposal.md),
enrolment rules; [acknowledge proposal](04-acknowledge-proposal.md),
Identity interface requiring one context increment per replacement.

The draft explicitly says compaction raises `ctx`; this review does not claim it
forbids that increment. However, the transactional resolution algorithm handles known
vendor sessions, including compaction, by returning their address. It does not identify
the distinct compaction occurrence used to increment once while absorbing repeated
hooks. T30 establishes event availability, not this transition's idempotence.

Missing an increment could preserve old receipt codes and suppress re-pinging;
incrementing twice could create a spurious context. Those are consequences of candidate
implementations, not observed behavior.

**Evidence to collect:** first inspect the available event payload and existing context
tracking for an occurrence identifier or monotonic position. Then exercise two genuine
compactions with replay of the first notification and a delayed old notification.
Capture `ctx`, receipt-code validity, and the resulting owed-message view after each
step. Expected behavior: one increment per genuine replacement, none for duplicates or
stale replay; an old-context code cannot acknowledge in the new context.

**Result that withdraws or narrows this finding:** an existing vendor event identity or
recorded transcript position already supplies the transition boundary. Document and
test it; do not add an independent lifecycle ledger. If no such evidence exists, leave
this as an unresolved mechanism rather than asserting that hook occurrence alone solves it.

## Relationship to existing tickets and next use

M10–M15 and the scratch-session permission remain in
the `project_open-questions.md` file in the main checkout's notes directory. This review neither answers
them nor files additional policy questions. Most findings first need artifact
clarification or evidence collection, not another ruling from Brian.

Before revising the architecture, the next reviewer or implementer should attach the
specific check result to each retained finding: source inspected, version, input/event
order, observed output, and whether the finding was confirmed, narrowed, or withdrawn.
Do not turn the six headings into six workstreams by default. Start with the existing
T23 safety experiment and the approval-correlation evidence when authorized; extend
the existing tests where possible. Receipt and pruning fixtures can share the same
body-preservation counterexamples.

No finding here certifies the rest of the design. The review's earlier phrase “six
findings survive” should be read as six concerns surviving document inspection, not six
reproduced defects. Recommendations remain conditional on the evidence described above.
