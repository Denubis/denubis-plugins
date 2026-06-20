# UAT Requirements — crash-detection

Human-judgment falsification entries. Each requires the operator to USE the built thing and exercise judgment automated tests cannot capture. Most of this feature is automated (see `test-requirements.md`); the genuine human-judgment surface is whether triage recovers the operator's *real* lost work.

Quality gate: each entry states (1) what the human DOES, (2) what they're JUDGING, (3) what FAILURE looks like.

## Phase 4: Render overhaul (the user-facing surface)

### DR1/DR9: The correlation join surfaces the operator's actual crash victims, resumable

**This decision assumes:** the repaired join + the `## Probable system-crash victims` section surface the sessions the operator actually lost — keyed on identifiers (pane-title, last-substantive, last-activity, full UUID) that let them recognise each one — and the `claudew --resume <full-uuid>` line brings back the *right* session.

**To shatter it:** on the real machine, run `crash-recovery triage` (via `claudew` so a `.live` is written for the recovery session too) against the live `~/.claude/run` backlog — or after the next OOM/tmux kill. Read the `## Probable system-crash victims` section. For sessions you remember losing, judge: can you tell which is which from the pane-title / last-substantive / timestamp? Then run one of the `claudew --resume <uuid>` lines and judge whether it reopens the session you intended.

**It's wrong if:** a session you know you lost is absent from the section (still buried under "Needs investigation"); or the pane-title/last-substantive are so generic you cannot distinguish two of your sessions; or a resume line reopens the wrong session, an already-recovered one, or an empty one. (Two reasonable operators could disagree about "informative enough to recognise" — that is the judgment this entry captures.)

**Marker-tracks-live-transcript (ADR 0003 — folds in the Phase 2b proleptic residual).** The marker's `session_id` is kept on the *live* transcript by the `SessionStart` hook, which fires on `clear`/`compact`/`resume`/`startup`. Unit tests prove the hook rewrites the marker; they cannot prove Claude Code's runtime payload is what we expect on every path. Exercise both rotation paths before (or at) the next kill: (a) a session you `/clear` one or more times, and (b) a session you `claudew --resume`d. After the kill, judge that triage's crash victim is the **live** transcript you were actually working in — not the abandoned launch/pre-`/clear` transcript, and not a stale ancestor. *It's wrong if* the resume line points at the cleared/abandoned session while your live work sits under a quieter row. (The `startup` and `clear` payloads were probed during Phase 2b; `resume` was not — this UAT is where the resume path is confirmed in the real harness.)

### Operator binding requirement: all-means-all is trustworthy

**This decision assumes:** when you ask triage for the roster, the full set of your sessions for the window is present — the crash highlight is a column/section, never a filter that drops rows.

**To shatter it:** compare the rendered roster against your own memory (or `~/.byobu-sessions` panes) for a day you worked across several dirs. Judge whether *every* session you expect is present, not just the ones flagged as crashes.

**It's wrong if:** the report claims completeness but a session you know existed for that window is missing — the specific failure mode the operator called out ("when I ask for all sessions, I mean all sessions").

---

All other acceptance criteria (AC1–AC9) are automated in `test-requirements.md`. Foundational phases (1–3, 5) have no user-facing surface of their own; their correctness is proven by tests and they feed this Phase 4 surface. They route to `exec-coherence-review`, not the UAT gate.
