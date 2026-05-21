# Post-mortem crash report — 2026-05-20 AEST

**Author:** Manual investigation (read-only). No DB / JSONL writes.
**Algorithm seed:** `docs/design-plans/2026-05-19-post-mortem-crash-detection.md`
**Investigator window:** 2026-05-19 16:00 AEST → 2026-05-20 15:14:38 AEST.

## Crash boundary

- **Source:** `last -F` output, line 47 of the captured listing:
  > `reboot   system boot  6.8.0-117-generi Tue May 19 10:34:20 2026 - Wed May 20 15:14:38 2026 (1+04:40)`
  >
  > `reboot   system boot  6.8.0-117-generi Wed May 20 15:15:23 2026   still running`
- **Timestamp (last-known-good wtmp entry from the dead boot):** `2026-05-20 15:14:38 AEST` (= `2026-05-20 05:14:38 UTC`).
- **New boot:** `2026-05-20 15:15:23 AEST` (47 s gap; no `shutdown` row between the two `reboot` rows — canonical crash pattern in `last -F`).
- **Boundary confidence:** **HIGH (VERIFIED).** Two independent signals agree:
  1. `last -F` shows the prior boot terminus at `15:14:38` with no graceful shutdown row preceding it.
  2. Five JSONL transcripts (different `~/.claude/projects/` subdirs, unrelated workloads) all fsync'd within a 11 ms window at `15:14:32.95–.97 AEST`, exactly 5.4–6.0 s before the boundary. This is the cluster signature described in `2026-05-19-post-mortem-crash-detection.md` §"Empirical algorithm".

## Live-process cross-check

`ps -ef | grep -E 'claude|claudew'` (rtk-proxied to bypass output filtering) shows three Claude sessions currently alive, all started **after** `15:15:23` (the new boot):

| UUID                                   | Project (cwd basename)                                         | PID    | Started      |
| -------------------------------------- | -------------------------------------------------------------- | ------ | ------------ |
| `b8fd4bea-ed54-4521-b209-c8f04268ed1f` | `crash-recovery` (worktree, resumed via `claude --resume`)     | 9668   | 15:16        |
| `616ade14-341b-4bb0-80f0-ac4bb48b0e11` | `session-runner`                                               | 12100  | 15:17        |
| `f8b23e59-8268-4df8-91e2-2a174e1cea06` | `crash-recovery` (worktree, this investigation session)        | 22974  | 15:19        |

None of the 13 pre-crash candidate UUIDs below appear in `ps`; all candidates are confirmed dead.

## Candidates (HIGH confidence) — 4 sessions

All four are members of the `15:14:32.95–.97 AEST` fsync cluster (within 6 s of crash boundary, ≤11 ms spread across the cluster). Each has a `mid_*` substantive tail at the moment work stopped.

### `1db0be1f-f2bb-49aa-83fa-919e30a0c872`

- **Project:** `/home/brian/people/Brian/session-runner` (git branch `main`).
- **Last write (mtime):** `2026-05-20T15:14:32.9595 AEST`, 1 844 203 bytes (683 JSONL records).
- **Tail kind:** **mid_tool_call** — assistant emitted `Bash` tool_use; no `tool_result` was ever written.
- **Last substantive event (idx 679, `2026-05-20T04:51:23 UTC`):**
  - `assistant` (`claude-opus-4-7`), `stop_reason=tool_use`, dispatched:
    `Bash{description: "Clean preview of pick.sh output", command: "echo '=== what pick.sh actually pipes to fzf (raw rows before sort) ==='; cache=\"$HOME/.cache/tmux-agent-status\"; sessio…"}`
  - Prior assistant text: "The mangling was my test harness, not the script. Real test by sourcing pick.sh's logic in isolation:"
- **Why HIGH:** REASONED-UNVERIFIED. Cluster signature (5-file 11 ms fsync cluster at crash boundary − 6 s) + VERIFIED mid_tool_call tail (Bash dispatched, no result) + active project (session-runner is one of the user's live tools).
- **Suggested action:** `crash-recovery note 1db0be1f-f2bb-49aa-83fa-919e30a0c872 "killed by 2026-05-20 15:14:38 AEST system crash (cluster member)"`

### `2f14a072-5507-4c89-9ca9-df55aedc9b96`

- **Project:** `/home/brian/people/Brian/sillytavern-deploy/.worktrees/implement-tavern-laws5000` (git branch `implement-tavern-laws5000`).
- **Last write (mtime):** `2026-05-20T15:14:32.9645 AEST`, 1 077 829 bytes (427 JSONL records).
- **Tail kind:** **mid_tool_call** — assistant dispatched a subagent via the `Agent` tool; no `tool_result` returned.
- **Last substantive event (idx 418, `2026-05-20T05:13:41 UTC` = `15:13:41 AEST`, ~57 s before crash):**
  - `assistant`, `stop_reason=tool_use`, dispatched:
    `Agent{subagent_type: "denubis-plan-and-execute:task-implementor", description: "Phase 6 fixup: Task 4 revision + new Task 4B (secrets_mutator)"}`
  - Prior text: "Dispatching task-implementor for the fixup commits."
- **Why HIGH:** REASONED-UNVERIFIED. Cluster signature + VERIFIED active subagent dispatch ~57 s before crash + active worktree project. The dispatched `task-implementor` did not get a chance to complete; whatever Phase 6 fixup commits it was meant to produce are lost unless the subagent transcript was checkpointed elsewhere.
- **Suggested action:** `crash-recovery note 2f14a072-5507-4c89-9ca9-df55aedc9b96 "killed by 2026-05-20 15:14:38 AEST crash mid-Agent dispatch (Phase 6 fixup task-implementor) — check whether task-implementor commits landed"`

### `6ec92e86-0c6f-4090-8979-71695d0760ee`

- **Project:** `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/denubis-dream` (git branch `denubis-dream`).
- **Last write (mtime):** `2026-05-20T15:14:32.9605 AEST`, 363 407 bytes (157 JSONL records).
- **Tail kind:** **mid_tool_call** — last substantive record is a `tool_result` (audit-writing subagent reported success); assistant never replied to consume it.
- **Last substantive event (idx 150, `2026-05-20T02:46:28 UTC` = `12:46:28 AEST`):**
  - `user` (tool_result wrapper) carrying:
    `"audit written for feedback_honour-prior-architectural-decisions: 5 evidence lines, 3 code-artefact entries. The origin session (cc926ca0) is present in the transcript window. Both trigger instances d…"`
  - Prior tool_result: `"audit written for feedback_absencejudgement-codes-fabricated: 5 evidence lines, 5 code-artefact entries agentId: a2c64a2cdccb0eafc"`
- **Why HIGH:** REASONED-UNVERIFIED. Cluster signature + VERIFIED tool_result with no follow-up assistant turn (the assistant was preparing to consume the second audit's tool_result when the crash hit; the mtime gap between last substantive event 12:46 and final fsync 15:14 indicates an idle/save state).
- **Suggested action:** `crash-recovery note 6ec92e86-0c6f-4090-8979-71695d0760ee "killed by 2026-05-20 15:14:38 AEST crash; was mid-audit consumption of feedback_honour-prior-architectural-decisions"`

### `28d8e6cc-9ff1-4dbe-bdb1-0defe289a03b`

- **Project:** `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/denubis-dream` (git branch `denubis-dream`).
- **Last write (mtime):** `2026-05-20T15:14:32.9595 AEST`, 1 259 738 bytes (419 JSONL records).
- **Tail kind:** **user_message_no_reply / attachment-pending** — last substantive record is a `user` message + `attachment` pair; assistant had not yet produced a response.
- **Last substantive event (idx 414, `2026-05-20T02:46:21 UTC` = `12:46:21 AEST`):**
  - `user`: "Quoting hell with the awk regex. Let me write the block to a temp script and run that. ● Write(/tmp/dream-prewindow.sh) ⎿ Wrote 81 lines to ../../../../../../../tmp/dream-prewindow.sh 1 #!/usr/bin/env bash 2 set -euo pipefail 3 …"
  - Followed by an `attachment` carrying the script content; no assistant response after.
- **Why HIGH:** REASONED-UNVERIFIED. Cluster signature + VERIFIED user submitted prompt + attachment with no assistant reply. Despite the >2 h gap between last substantive event and final fsync, the cluster co-membership with four other unrelated active sessions makes mass-kill far more plausible than four-way coincidence.
- **Suggested action:** `crash-recovery note 28d8e6cc-9ff1-4dbe-bdb1-0defe289a03b "killed by 2026-05-20 15:14:38 AEST crash; user prompt + dream-prewindow.sh attachment never received assistant reply"`

## Candidates (MEDIUM confidence) — 2 sessions

### `e924c4e3-2d08-4c62-846a-771d3c8888c7`

- **Project:** `/home/brian/people/Mark/2026-WinterSchool` (git branch `main`).
- **Last write (mtime):** `2026-05-20T15:14:32.9705 AEST`, 1 873 134 bytes (293 JSONL records).
- **Tail kind:** **clean_assistant_end** (`stop_reason=end_turn`) — assistant had concluded a turn and the session was idle awaiting next user input.
- **Last substantive event (idx 287, `2026-05-20T04:30:30 UTC` = `14:30:30 AEST`, ~44 min before crash):**
  - `assistant`, `stop_reason=end_turn`, text: "Done with the rewrite. Summary of this session's deltas: - **`tools/notebook_cells.py`** + **`tools/test_notebook_cells.py`** — clean append/insert/replace/delete API with 13 passing pytest smoke tests; `tools/__init__.py` makes the package importable. - **`pyproject.toml`** — added `pytest>=8.0` t…"
- **Why MEDIUM:** REASONED-UNVERIFIED. VERIFIED cluster membership (mtime exactly within the 5-file 11 ms cluster at crash boundary − 6 s, lining up perfectly with four other unrelated sessions known to be HIGH crash victims). VERIFIED clean tail. Per the rubric, clean_assistant_end + suspicious mtime alignment = MEDIUM. The cluster signature is strong evidence of mass-kill, but the assistant had finished its turn before the crash — so "killed" here means "the idle process was killed", not "killed mid-work".
- **Suggested action:** `crash-recovery note e924c4e3-2d08-4c62-846a-771d3c8888c7 "killed by 2026-05-20 15:14:38 AEST crash while idle-waiting after end_turn at 14:30 AEST (cluster member)"`

### `e9ec7664-5d3d-482c-b8f4-299180a420bb`

- **Project:** `/media/brian/storage/people/Adela/melica` (git branch `main`).
- **Last write (mtime):** `2026-05-20T14:37:01.8694 AEST`, 1 817 906 bytes (986 JSONL records).
- **Tail kind:** **mid_tool_call** — last substantive record is a `tool_result`; assistant never replied to consume it.
- **Last substantive event (idx 982, `2026-05-20T04:37:01 UTC` = `14:37:01 AEST`, ~37 min before crash):**
  - `user` (tool_result wrapper); assistant turn never started after this result landed.
- **Why MEDIUM:** REASONED-UNVERIFIED. VERIFIED mid_tool_call tail (anomalous — assistant should have started a turn after the tool_result). NOT a cluster member (mtime 14:37, no other files at that minute). Per the rubric, mid_* tail with mtime wider than ±60 s but within ±5 min of crash → MEDIUM; here the offset is ~37 min, which is wider still, so this could also be a session that hung mid-stream (e.g., API timeout, network blip) independent of the crash. User clarification ("some likely were waiting since last night") supports treating idle-waiting sessions as crash victims, but a hung mid-tool-call session **could** be either a network event or a crash victim — the JSONL alone cannot distinguish.
- **Suggested action:** `crash-recovery note e9ec7664-5d3d-482c-b8f4-299180a420bb "possible 2026-05-20 15:14:38 AEST crash victim (mid_tool_call ~37 min before boundary, no cluster co-occurrence — verify against memory)"`

## Candidates (LOW confidence) — for manual review — 6 sessions

These all have `clean_assistant_end` or post-substantive-attachment tails from before the crash window. The JSONL alone cannot distinguish "user normally finished and walked away" from "user left idle in a tmux pane, crash killed the process". Manual triage required.

| UUID                                   | Project (cwd basename)                         | mtime (AEST)              | Tail kind                                            |
| -------------------------------------- | ---------------------------------------------- | ------------------------- | ---------------------------------------------------- |
| `5c4ebd61-5ba6-4ca7-a53e-b5fec9e0fe07` | `INTS1301`                                     | `2026-05-19 16:16:42.818` | `clean_assistant_end` (Decomposition reply on Week 7 mindmap) |
| `f59d1a4a-631c-4ad0-935a-13bb14ffca24` | `Mark/2026-WinterSchool`                       | `2026-05-19 16:46:34.312` | post-substantive attachment (last is user attachment, no reply) |
| `85b3b673-90d6-405c-a20f-97ff2c8ddabd` | `Mark/2026-WinterSchool`                       | `2026-05-19 17:11:50.603` | `clean_assistant_end` ("repo-infra scope for this chat is done; Outstanding: 3 commits ahead of origin/main, unpushed…") |
| `fa76a6ac-fd57-4b4f-8864-e1f2252cfeda` | `Mark/2026-WinterSchool`                       | `2026-05-19 17:17:37.565` | `clean_assistant_end` ("Committed as `f412fe9`. Working tree clean.") |
| `ecffea55-7b6d-415a-af96-6c5119018ea8` | `Mark/2026-WinterSchool` (cwd actually `Mark/2025-corpus-analysis`) | `2026-05-19 17:25:11.511` | `clean_assistant_end` (rsync/archive sign-off) |
| `06ca099b-4a94-46ef-a3a4-080716c1c9d1` | `Adela/melica`                                 | `2026-05-20 12:48:55.908` | `clean_assistant_end` (verdict-question prompt awaiting user) |

User clarification context: idle sessions waiting since yesterday afternoon were likely killed by the crash. If any of these tmux panes were still open at `15:14:38 AEST`, those processes died — even though their JSONL mtimes are from when the assistant last wrote, not the crash time. The JSONL alone cannot confirm this; cross-reference against your tmux session history if available.

## Excluded as live

These three UUIDs are currently running (cross-checked against `ps -ef`); they are post-reboot sessions, not crash victims:

- `b8fd4bea-ed54-4521-b209-c8f04268ed1f` (PID 9668 — `crash-recovery` worktree, resumed)
- `616ade14-341b-4bb0-80f0-ac4bb48b0e11` (PID 12100 — `session-runner`)
- `f8b23e59-8268-4df8-91e2-2a174e1cea06` (PID 22974 — `crash-recovery` worktree, this investigation)

## Excluded as clearly concluded

**1** session in the inspection window — `50dbf3ac-dfc0-4450-bbc0-e67d698defaa` (`Mark/2026-WinterSchool`, mtime `2026-05-20 11:50:46 AEST`). Tail is an explicit handoff: assistant produced "Memory updated. Resume prompt below — paste this into the next session…" with `stop_reason=end_turn`. This is the canonical "user wrapped up, session intentionally ended" pattern, not an idle-killed victim.

(Out-of-window concluded sessions: ~1053 JSONLs across 147 project directories have mtimes before 2026-05-19 16:00 AEST and were not examined.)

## Counts

- HIGH: **4**
- MEDIUM: **2**
- LOW (manual review): **6**
- Excluded as live: **3**
- Excluded as clearly concluded (within window): **1**
- Total candidates examined in window: **13** (+ 3 live = 16 sessions touched since 2026-05-19 16:00 AEST).

## Notes on evidence discipline

Per the user's `feedback_no-unverified-capability-claims`:

- **VERIFIED** statements in this report: filesystem mtimes (from `find -printf`), JSONL record contents (read directly with `python3 -c "json.loads(line)"`), live PIDs (from `ps -ef`).
- **REASONED-UNVERIFIED** statements: every "killed by crash" attribution. The cluster signature is empirically strong (5-file 11 ms fsync window co-located with crash boundary − 6 s), but no single observable fact in any JSONL says "I was killed by a crash". The inference comes from cluster + temporal + tail.
- **SPECULATIVE** content has been kept out of the HIGH/MEDIUM bodies. The LOW-confidence section is explicitly flagged as "JSONL alone cannot distinguish"; reasoning there is REASONED-UNVERIFIED with the unknowns named.

## Method (reproducibility)

1. `last -F` → identify crash boundary (`15:14:38 AEST` — last-known-good of dead boot, no graceful `shutdown` row).
2. `find ~/.claude/projects -maxdepth 2 -name '*.jsonl' -newermt '2026-05-19 16:00:00' ! -newermt '2026-05-20 15:14:33' -printf '%TY-…\n'` → 13 candidates in window.
3. Backward-scan each JSONL with `/tmp/inspect_jsonl.py` (in this report; preserved during the investigation, not yet committed) — skips bookkeeping records (`ai-title`, `last-prompt`, `permission-mode`, `agent-name`, `agent-color`, `custom-title`) and returns the last substantive event (`user`/`assistant`/`tool_result`).
4. `ps -ef | grep -E 'claude|claudew'` → 3 live PIDs; map each to its `--session-id` or `--resume` cwd; exclude those UUIDs.
5. Classify per the rubric in the investigator brief; record the cluster signature as the load-bearing signal for HIGH.

## Open questions left for the user

- For each MEDIUM/LOW session, only the user can confirm whether the tmux pane was open at `15:14:38` and therefore whether the process actually died.
- `e9ec7664` (Adela/melica, ~37 min before crash, mid_tool_call) is the most uncertain: it could be a network-induced hang independent of the crash, or it could be a session you left idle. If you remember whether the assistant ever replied to that tool_result, that resolves it.
- `28d8e6cc` (denubis-dream, >2 h gap between last substantive and final fsync but in the cluster) is HIGH on cluster evidence alone; if you remember whether you closed that session manually before the crash, that overrides.
