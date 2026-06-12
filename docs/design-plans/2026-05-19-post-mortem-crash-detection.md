# Post-mortem crash detection (design seed)

**Status:** Seed — needs brainstorming before implementation planning.
**Surfaced by:** Phase 7 dogfood attempt, 2026-05-19. After a real system crash on 2026-05-18 ~18:47 AEST killed 5 in-flight Claude sessions, the just-shipped `crash-recovery triage` reported 0 sessions in "Currently unfinished" and 0 in "Idle-live killed". The casualties were buried in the 130-row "Needs investigation" bin as `unknown_tail_kind` or `no_liveness_dangling_*`.
**Related:** `docs/design-plans/2026-05-08-crash-recovery.md` (parent design); Phase 7 SKILL.md and README; Phase 8 wrapper patch.

## Problem statement

The classifier (`plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/classify.py::RULES`) has no rule that produces `hard_crash` when `liveness_present=False`. Every `HARD_CRASH` row in the rule table requires `liveness_present=True`. Without the Phase 8 wrapper installed and having run before the crash, no liveness file exists, and the classifier is structurally incapable of identifying a crash victim *as* a crash victim — they fall through to `BORDERLINE` / `unknown_tail_kind` / `no_liveness_dangling_*` and render under "Needs investigation".

Phase 8's wrapper patch closes part of this gap going forward: once installed, every new wrapped session writes a liveness file at startup, so future crashes can be classified deterministically. But Phase 8 does **not** retroactively help sessions that died before the wrapper was installed — and that "first crash after install" scenario will keep recurring as users adopt the plugin. The headline use case ("I had a crash, find my dead sessions") is the *first* thing a new user will exercise.

## Empirical algorithm (validated 2026-05-19)

A peer Claude session recovered the casualty list using filesystem heuristics alone, no DB. The algorithm:

```
Input:  ~/.claude/projects/*/*.jsonl
        `last -Fxn 50` (or `journalctl --list-boots`)
Output: list of (uuid, cwd, last_user_msg, last_assistant_state, resume_cmd, crash_window_ts)

1. Extract abnormal-termination windows from `last`:
   - "crash" rows
   - boot-without-preceding-shutdown rows (the prior wtmp entry is the crash time)
   - sub-5-minute boots (panic loop signature)
   For each, the transition timestamp is `crash_window_ts`.

2. For each crash window, sweep [crash_window_ts - 60s, crash_window_ts + 5s]:
   a. Find JSONLs with mtime in window.
   b. If ≥2 files cluster within ±2s of each other AND within the window:
      cluster signature confirmed — these are crash victims.

3. For each clustered JSONL:
   a. Read FORWARD for the first record carrying a `cwd` field. Skip
      bookkeeping sidecars (records whose only top-level keys are things
      like agent-name, pr-link, content-types).
   b. Read BACKWARD for the last *substantive* event (user message, or
      assistant text / tool_use). Skip trailing bookkeeping entries.
   c. UUID is the filename basename without `.jsonl`.

4. Classify as hard_crash with reason
   `mtime_cluster_at_system_event_<iso8601>` and reduced-confidence text
   "heuristic: clustered fsync at <crash_time> — verify against your
   session memory".

5. Render under "Currently unfinished" (or a new section "Probable
   system-crash victims" — open question, see below).
```

## Gotchas the empirical run discovered

1. **`who -b` is wrong for anything but the most recent boot.** It returned the post-crash boot time (10:34 the next morning), not the crash time. Use `last -Fxn N` or `journalctl --list-boots` to walk the full reboot history; correlate against the suspected crash window.
2. **JSONL first/last lines may be sidecar bookkeeping** (single agent-name entry, single pr-link entry, etc.). A 500-line transcript can have a first line that is just `{"agent-name": "..."}` with no `cwd`, and a last line that is just `{"content-types": [...]}`. Robust extraction needs to scan forward to first-real-record and backward to last-substantive-event.
3. **A clean shutdown that happens to coincide with a kernel buffer flush is not a crash.** False positives need to be suppressed by correlating against `last` output — clusters not aligned with an abnormal-termination window should not be classified hard_crash.
4. **VM live-migration / suspend-resume can produce fsync jitter** that mimics a cluster. ±2s is a default, not a guarantee; the threshold may need tuning per-host or per-filesystem.

## Relationship to Phase 8 wrapper

|  | Phase 8 wrapper (liveness file) | mtime-clustering (this seed) |
|---|---|---|
| Single-session crash (one process OOM'd, system stayed up) | ✓ detected | ✗ no cluster signal |
| Multi-session system crash | ✓ detected precisely | ✓ detected heuristically |
| Sessions started before wrapper install | ✗ no liveness file | ✓ catches them |
| Confidence level | deterministic | heuristic + reduced-confidence text |
| Dependencies | wrapper must be installed and have run | `last`/`journalctl` available |

The two are **complementary**, not alternatives. mtime-clustering is the answer for "the user just installed this plugin and wants to recover their previous crash" and for "the user's sessions started before the wrapper was patched in".

## Open design questions for brainstorming

1. **Where does the rule live?** Options:
   - New rows in `classify.py::RULES` (clean, but requires the classifier to know about cross-session relationships — currently it's purely per-row).
   - Separate `crash_recovery.posthoc` module that runs after `classify()` and overrides borderline → hard_crash with the new reason when the cluster signature is present.
   - A Phase 2/3-style scanner pass that writes a new column (e.g. `crash_window_id`) on detected cluster members, then a classifier rule keys off that column.
2. **Render section.** Fold the heuristic hard_crash rows into "Currently unfinished" / "Idle-live killed", or surface them in a dedicated "Probable system-crash victims" section so the reduced-confidence framing is visible at section level?
3. **Input source.** `last -F` works on most desktop Linux; `journalctl --list-boots` is the systemd-native equivalent. Should the tool prefer one, try both, or make it configurable? What about machines where neither is available (containers, sandboxes, macOS)?
4. **Cluster threshold tuning.** ±2s default; min cluster size 2; window [crash - 60s, crash + 5s]. These are guesses. Need to measure actual fsync jitter on the user's filesystems before locking them in.
5. **False-positive suppression.** Scheduled fsync (logrotate, periodic syncfs, large file writes) under load could create coincidental clusters. Should the rule require correlation with a `last`/`journalctl` abnormal-termination event, or is "cluster alone" enough to flag as borderline?
6. **Per-session API impact.** The current `classify()` is per-row. Cross-session detection means the scanner needs to compute clusters as a preprocessing step. Where in the scan pipeline does this slot in without breaking the determinism guarantees Phase 2 worked hard to establish?
7. **`history` command + `classification_history` cascade.** When a row is reclassified from borderline → hard_crash by the post-hoc pass, does that constitute a classification change that writes to `classification_history`? Or does the post-hoc pass live outside the history-tracking boundary?
8. **Resume command generation.** The other instance generated `claudew --resume <uuid>` lines. Is `claudew` a stable wrapper name, or should the render emit the unwrapped `claude --resume <uuid>` form? Should this be a render option?

## Documentation honesty (resolved in Phase 7)

The first two Phase 7 commits (`963195a` SKILL.md, `9b98add` README) contained two overclaims — both variants of the same false world model that the tool "degrades gracefully" when the wrapper is missing. The Phase 7 coherence review surfaced the second occurrence; both were fixed inline before Phase 7 closed.

The original false claims:

1. **README.md:25-27 (Dependency section):**

   > "If `denubis-plan-and-execute` is at an older version, crash-recovery still runs but degrades to JSONL-tail-only heuristics (no liveness file detection), and every session will be classified `concluded`."

   Both halves were wrong. Dangling-tail sessions are classified `borderline`, not `concluded`, and routed to "Needs investigation" / "Ambiguous correlation", not "Recently concluded".

2. **SKILL.md:99 (Integration section):**

   > "Without that wrapper patch, `scan` sees zero liveness files and every session is classified `concluded`."

   Same false claim.

The honest replacement (now in both files):

> "Without the wrapper having run before the crash, `hard_crash` and `live` classifications cannot fire — every rule producing them in `classify.py::RULES` requires `liveness_present=True`. Crashed sessions appear under 'Needs investigation' as `unknown_tail_kind` or `no_liveness_dangling_*`, not as recoverable crashes. Retroactive recovery for sessions that ran before the wrapper was installed is tracked in this design seed."

The empirical dogfood (2026-05-18 crash, 5 sessions) produced exactly this pattern.

**What remains for Phase 8:** substitute `<PHASE-8-VERSION>` in README with the real wrapper version, and extend the README Troubleshooting section with wrapper-side failure modes (Phase 7 cannot enumerate them because the writer doesn't exist yet). Both items are tracked in `phase_08.md`'s "Surfaced during Phase 7 dogfood" section.

## Suggested path forward

1. **Brainstorm** (next session, fresh context): walk through questions 1-8 above with the user; pick an architectural shape.
2. **Design plan**: write the proper design doc once architecture is chosen.
3. **Implementation phase(s)**: probably one phase, scoped to the chosen architecture.

This seed is the starting input for step 1.

## Provenance

- Empirical algorithm extracted from the 2026-05-18/19 transcript where a peer Claude session recovered the casualty list from `~/.claude/projects/` after the crash-recovery CLI failed to surface them.
- Casualty list (for reproducibility): 5 sessions clustered at `2026-05-18 18:47:56.97…98.04` AEST, cwds spanning sillytavern-deploy/implement-tavern-laws5000, brian-ed3d-plugins/denubis-dream, session-runner, and Adela/melica (×2).
- Current crash-recovery DB state on user's machine at time of writing: 130 sessions classified `borderline` with reason `unknown_tail_kind`; zero `hard_crash`; zero `live`. Consistent with the structural gap above.

## Addendum 2026-06-12 — tmux-resurrect / byobu as a post-mortem input source

A second OOM/kill on **2026-06-11 ~20:50 AEST** took out 9 sessions across 6 dirs. The
casualty list was again recovered by hand, and again the running `triage` buried them in
the 130-row `unknown_tail_kind` bin — the seed's algorithm works, it is just still unbuilt.
This run added a signal the original algorithm did not use.

**The signal.** byobu ships tmux-resurrect (plugin under `~/.byobu/tpm/plugins/`, **saves to
`~/.byobu-sessions/tmux_resurrect_<YYYYMMDDTHHMMSS>.txt` — NOT `~/.tmux/resurrect/`**).
A 2026-06-08 recovery attempt concluded "no resurrect installed" precisely because it only
checked `~/.tmux/plugins`; this is the standard miss. Continuum snapshots every ~15 min, so
there is almost always a save 0–15 min before any crash. Each `pane` line (tab-separated)
carries, in field order: `pane`, session, window, pane-idx, flags, `1`, **`:<window title>`**,
**`:<pane_current_path>`**, `1`, `<pane_current_command>`, `:<shell>`.

**What it buys, mapped to the open questions:**
- **Open Q#2 (labels / render).** Field 7 is the window title — for wrapped Claude windows
  it is the `exec-session-naming` slug prefixed `✳` (e.g. `✳ Add open-pdf endpoint to Zotero
  API plugin`). This is a human-meaningful "what was this session" label that mtime-clustering
  cannot produce. Render could show it beside the resume line.
- **Open Q#3 (input source).** A third option besides `last` / `journalctl`: the resurrect
  snapshot independently confirms *which cwds had a live `claude` pane at kill time* (filter
  panes to `✳` title or `pane_current_command`), turning the mtime cluster from "probable" to
  "corroborated". It also works where `last`/`journalctl` are unreliable (the 2026-06-11 run
  never needed `last` — pane-set ∩ mtime-cluster was sufficient).
- **False-positive suppression (Q#5).** pane∩cluster is a stronger discriminant than cluster
  alone: a coincidental fsync burst will not also have matching live `claude` panes.

**Confirms, does not replace, the cwd-join.** `correlate.py::_project_dir_for_cwd` already
reads the JSONL `cwd` field (the robust reverse map). The resurrect `pane_current_path` is the
forward map and agrees with it — useful as a cross-check, and it caught a hand-decode error:
the project dir `-home-brian-people-Brian-zendo-kdf-data` is ambiguous and naively decodes to
`zendo-kdf-data` (which does not exist) when the real cwd is `zendo-kdf/data`. Reading `cwd`
from the JSONL (as the plugin already does) is canonical; resurrect's path corroborates it.

**Gotchas observed 2026-06-11:**
- A pane having a Claude window does not mean a *resumable* session — `agy`, `ssh`, `fish`,
  `oauth2-proxy` panes coexist; filter on `✳`/`pane_current_command == claude`.
- A live Claude session may have **no** resurrect pane (here: `zendo-kdf/data`, a subdir the
  window had `cd`'d out of). So: drive the casualty list from the JSONL mtime cluster; use
  resurrect to *enrich and corroborate*, not as the sole source.
- The auto-restored post-crash tmux session has `created` == restore time and does **not**
  restart `claude`; `pgrep claude` empty + a fresh-stamped restored session is itself a
  crash tell.
- `/clear` mints a new session UUID in the same window, so one pane can leave several JSONLs
  in the kill cluster; resume the newest per cwd, or present all and let the user pick.

**Provenance.** Recovery artefact for this run: `~/llm-resume-postmortem-20260611.md`
(hand-written, kept outside the DB-managed `~/llm-resume.md`). Casualties clustered
`20:50:01.57–20:50:02.64` AEST; pre-crash snapshot `~/.byobu-sessions/tmux_resurrect_20260611T203938.txt`.

### Operator feedback 2026-06-12 — recovery-output requirements (binding)

The 2026-06-11 recovery first shipped a list of only the 7 crash-cluster sessions and
described it as "everything". The operator's correction, verbatim in intent: *"When I ask
for all sessions, I mean all sessions, not just the ones you vibe. And the starting hashes
aren't very useful."* These are hard requirements for any recovery output, manual or coded:

1. **All means all — no vibe-curation.** Enumerate **every** session in the stated window,
   not the subset the assistant judges "live" / "relevant" / "worth resuming". The operator
   decides relevance; the tool's job is the complete roster. Mark derived attributes
   (`● crash`, subagent count) as *columns*, never as a filter that drops rows. The full
   2026-06-11 set was **22** top-level sessions, not 7.
2. **State the enumeration window explicitly** ("every top-level session with activity on
   `<date>`") so scope is visible, not an implicit judgement call. Do not silently narrow it.
3. **Do not claim comprehensiveness unless the artefact is exhaustive.** "Everything is in
   the file" when the file holds a quarter of the sessions is the specific failure here.
4. **Opening message / first line is a useless identifier** — almost always `/clear`, a
   slash-command wrapper, a continuation prompt, or a tool stub. Key each row on, in order:
   the **tmux-resurrect pane title** (the `✳` `exec-session-naming` slug — the best "what was
   this"), **last substantive activity**, **last-activity timestamp**, and the **full
   resumable UUID** (never a truncated hash — the operator needs the whole UUID to resume).
5. **"Last substantive activity" extraction must skip more than `/clear`.** Observed leakage
   on 2026-06-11: trailing `<usage>…</usage>` token-accounting records, `<summary>…</summary>`
   background-command notifications, `</task-notification>` stubs, and the post-compaction
   "If you need specific details from before compaction…" boilerplate all surfaced as the
   "last message". The backward scan for the last real event must skip these bookkeeping kinds
   (extends gotcha #2 above), falling back to the last human turn or last assistant text.

Render implication for the coded feature: the "Probable system-crash victims" section (open
Q#2) is a *priority highlight*, not the whole report — the full roster must still render so
nothing is dropped.

### Operator ask 2026-06-12 — "a flag in claudew that says if I exited properly"

This flag **already exists**: it is the DR8 liveness file in
`denubis-plan-and-execute/scripts/claude-wrapper.sh`. The wrapper writes
`~/.claude/run/<PID>.live` on start (`cwd`, `started`, `argv` incl. `--resume <uuid>`,
`boot_id`) and removes it **only on exit code 0 or 130 (Ctrl-C)**; any other code (137 SIGKILL,
139 SIGSEGV, generic non-zero) leaves it as crash evidence. So "exited properly" = the `.live`
is gone; a surviving `.live` = abnormal termination. The operator's instinct is right; the
mechanism is built. The gaps below are why it does not yet *feel* built.

**Empirical landscape 2026-06-12** (`~/.claude/run`, 30 files): 3 alive (today's resumes,
incl. the already-recovered BJET `4e7fc80e` and zotero `1e32935f`), 27 dead stale markers
spanning 06-04…06-11. The flag retained every uncleanly-exited session correctly.

**The three gaps this exposes — these are the work, not a new flag:**

1. **Same-boot kills defeat `boot_id` detection.** All 30 files carry the *current* boot_id —
   the 20:50 kill was an OOM/tmux-server death, **not a reboot** (kernel never restarted). So
   "boot_id ≠ current ⇒ crash" matches **zero**, and the seed's `last`/`journalctl`
   reboot-window algorithm (steps 1–2 above) would miss it entirely. **The reliable
   same-boot crash signal is `.live`-present AND its PID is dead**, not a boot change. The
   classifier must test PID liveness of each `.live`, not (only) reboot history. boot_id stays
   useful for the *reboot* case (where PIDs are reused en masse); it is not sufficient alone.

2. **PID-liveness is PID-reuse-fragile.** A bare `kill -0 <pid>` calls a recycled PID "alive"
   and silently drops a crash victim; on 2026-06-12 this had to be rejected by reading
   `/proc/<pid>/cmdline`. The `.live` records no process start-time, so reuse cannot be
   rejected from the file alone. **Fix: stamp the process start-time into the `.live`** (e.g.
   `/proc/<pid>/stat` field 22, or `ps -o lstart=`) and require *PID alive AND start-time
   matches* to count as still-running. This is a small, testable addition to
   `claude-wrapper.sh` + `liveness.py`.

3. **No reaping, and the tool doesn't consume it.** 27 markers accumulate back to 06-04 — the
   flag rots into noise with no lifecycle. And `crash-recovery triage` renders from its SQLite
   DB without cross-referencing `~/.claude/run/*.live` at all, so the signal sits on disk
   unused. The classifier should (a) read the `.live` set, (b) classify present+PID-dead
   (start-time-checked) as `hard_crash`, and (c) reap markers once recovered/acknowledged
   (or let `prune` cover `~/.claude/run`).

**Net:** do not add a second flag. Harden the existing one (start-time stamp), then wire the
classifier to consume it for the same-boot case. This subsumes the seed's reboot-only
algorithm rather than replacing it.
