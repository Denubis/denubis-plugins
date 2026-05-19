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

## Documentation honesty issue (Phase 7 fallout)

`plugins/denubis-crash-recovery/README.md` (committed 2026-05-18 as `9b98add`) currently says:

> "If `denubis-plan-and-execute` is at an older version, crash-recovery still runs but degrades to JSONL-tail-only heuristics (no liveness file detection)."

This is misleading. The honest version: without the Phase 8 wrapper having run before the crash, `hard_crash` and `live` classifications cannot fire — every rule that produces them requires `liveness_present=True`. Sessions appear under "Needs investigation" with reasons like `unknown_tail_kind` or `no_liveness_dangling_tool_use`, not as recoverable crashes.

Phase 8 already plans to edit the README (to substitute `<PHASE-8-VERSION>` with the real version). The honesty pass can fold in at the same time — flag this design seed as the reason.

## Suggested path forward

1. **Brainstorm** (next session, fresh context): walk through questions 1-8 above with the user; pick an architectural shape.
2. **Design plan**: write the proper design doc once architecture is chosen.
3. **Implementation phase(s)**: probably one phase, scoped to the chosen architecture.

This seed is the starting input for step 1.

## Provenance

- Empirical algorithm extracted from the 2026-05-18/19 transcript where a peer Claude session recovered the casualty list from `~/.claude/projects/` after the crash-recovery CLI failed to surface them.
- Casualty list (for reproducibility): 5 sessions clustered at `2026-05-18 18:47:56.97…98.04` AEST, cwds spanning sillytavern-deploy/implement-tavern-laws5000, brian-ed3d-plugins/denubis-dream, session-runner, and Adela/melica (×2).
- Current crash-recovery DB state on user's machine at time of writing: 130 sessions classified `borderline` with reason `unknown_tail_kind`; zero `hard_crash`; zero `live`. Consistent with the structural gap above.
