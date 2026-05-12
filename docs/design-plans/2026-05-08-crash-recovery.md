# Crash Recovery Plugin Design

**GitHub Issue:** None

## Summary

The `denubis-crash-recovery` plugin gives Claude Code users a reliable way to identify and resume sessions that ended abnormally — whether from a kernel kill, a terminal disconnect, or a process crash. When Claude exits cleanly, its session JSONL closes normally and the session is easy to find. When it does not, the JSONL goes silent mid-conversation and there is no built-in way to distinguish "this session finished" from "this session died." The plugin solves this by introducing a lightweight liveness file written by the `claude-wrapper.sh` script at session start and removed on clean exit. A surviving file after the wrapper process disappears is the signal that something went wrong.

All session state is stored in a local SQLite database. A Python CLI (`crash-recovery`) scans the liveness files, reads the tail of each session's JSONL, cross-references live PIDs, and applies a deterministic rule table to classify every known session: `live`, `hard_crash`, `borderline`, `concluded`, or `irrecoverable`. The classification result is then rendered into `~/llm-resume.md`, a markdown file containing the resume command for each affected session, the reason it was classified, and any user-supplied annotations. The markdown is always regenerated from database state — it is never edited directly — which keeps the source of truth clean and makes regeneration byte-identical given the same data.

## Definition of Done

1. **Plugin installable from the existing marketplace.** `claude plugin install denubis-crash-recovery@brian-ed3d-plugins` succeeds and `/plugin` lists it. Marketplace.json + plugin.json populated; ships under the same `brian-ed3d-plugins` git repo as a `denubis-*` sibling.

2. **`crash-recovery` Python CLI runs.** `crash-recovery --help` prints usage. Subcommands at minimum: `triage` (classify + print report), `regenerate` (rewrite `~/llm-resume.md` in place, preserving user notes), `list-live` (show currently-running claude sessions per liveness data).

3. **Triage skill produces a deterministic report.** Invoking the `denubis-crash-recovery:triage` skill calls the CLI which classifies all sessions in scope and prints a markdown report. Same input state → identical output (no LLM judgement in classification).

4. **`~/llm-resume.md` regenerates without losing user annotations.** User annotations entered via `crash-recovery note <uuid> "..."` persist in the SQLite database (`sessions.user_notes`) and are surfaced in every subsequent render of `~/llm-resume.md`. Markdown is a regenerated view of database state; direct edits to it do not persist. Path is configurable via `CRASH_RECOVERY_RESUME_PATH` (default `~/llm-resume.md`).

5. **Liveness tracked via patched claude-wrapper.** `denubis-plan-and-execute/scripts/claude-wrapper.sh` writes `~/.claude/run/<session_id>.live` on start and removes it via `trap EXIT` on clean exit. Verifiable: clean exit removes the file; `kill -9` of the wrapper leaves it. Patch lands in `denubis-plan-and-execute` with a version bump.

6. **Idle-live-session detection works end-to-end.** Start a claude session, leave idle 5+ minutes, `kill -9` the wrapper PID. Run triage. Session is flagged as a casualty despite the JSONL being stale — proving the liveness mechanism catches what JSONL-tail-only would miss.

7. **No automatic pruning of "concluded" entries.** Entries previously classified as concluded persist in the file across regenerations until either (a) the user passes an explicit `--prune` flag, or (b) the underlying JSONL has been deleted from disk.

8. **Sibling-plugin coordination documented.** README explains the dependency: denubis-crash-recovery requires the matching liveness patch in denubis-plan-and-execute (≥ documented version). Both versions bumped in the same PR.

**Explicitly OUT of scope:**
- byobu/tmux-resurrect helpers
- OOM-hardening (cgroup-bounded claudew, journalctl diagnostics)
- LLM-driven judgement on borderline cases (CLI applies deterministic rules; user annotates manually)
- Auto-pruning of stale entries

## Acceptance Criteria

### crash-recovery.AC1: Plugin installs and registers
- **crash-recovery.AC1.1 Success:** `claude plugin install denubis-crash-recovery@brian-ed3d-plugins` exits 0
- **crash-recovery.AC1.2 Success:** After install, `/plugin` lists `denubis-crash-recovery` with the version in `plugin.json`
- **crash-recovery.AC1.3 Success:** `plugin.json` and the `marketplace.json` entry both have all required fields (name, version, source, author, license) and identical version strings
- **crash-recovery.AC1.4 Failure:** Install with a malformed `plugin.json` exits non-zero with a parseable error message (no silent failure)

### crash-recovery.AC2: CLI exposes the documented surface
- **crash-recovery.AC2.1 Success:** `crash-recovery --help` prints usage listing every documented subcommand (`scan`, `render`, `triage`, `regenerate`, `list-live`, `note`, `history`, `prune`, `init`)
- **crash-recovery.AC2.2 Success:** Every subcommand accepts `--help` and prints a usage-with-flags message
- **crash-recovery.AC2.3 Success:** `crash-recovery init` creates `~/.claude/crash-recovery.db` (or path from `CRASH_RECOVERY_DB`) with the schema documented in Architecture
- **crash-recovery.AC2.4 Success:** Re-running `init` against an existing DB is a no-op (idempotent — verified by row-count and schema-hash check)
- **crash-recovery.AC2.5 Failure:** Unknown subcommand exits non-zero with an error message pointing to `--help`

### crash-recovery.AC3: Classification is deterministic
- **crash-recovery.AC3.1 Success:** Every row of the rule table classifies its fixture to the expected value (parametrised tests; one assertion per row)
- **crash-recovery.AC3.2 Success:** Same fixture filesystem state passed through `scan` + `render` twice produces byte-identical markdown
- **crash-recovery.AC3.3 Success:** Each session row records a non-empty `classification_reason` string referencing the rule that matched
- **crash-recovery.AC3.4 Failure:** A JSONL with a malformed JSON line yields classification `borderline` with reason `malformed_tail`; the CLI does not crash
- **crash-recovery.AC3.5 Edge:** An empty JSONL (zero entries) yields `borderline` with reason `empty_file`
- **crash-recovery.AC3.6 Success:** When `scan` runs against a DB containing rows whose `classifier_version` is below the current `CLASSIFIER_VERSION` constant, those rows are re-classified using the current rule table before render or prune sees them. After scan completes, no `sessions` row has a stale `classifier_version`.

### crash-recovery.AC4: Annotations persist via SQLite
- **crash-recovery.AC4.1 Success:** `crash-recovery note <uuid> "x"` followed by `regenerate` causes "x" to appear under that UUID in `~/llm-resume.md`
- **crash-recovery.AC4.2 Success:** `note <uuid> "y"` against a UUID with an existing note overwrites the note; the prior text is no longer in the rendered output
- **crash-recovery.AC4.3 Success:** `note <uuid> --clear` removes the note; the subsequent render omits the user-notes line for that UUID
- **crash-recovery.AC4.4 Edge:** Direct edits to `~/llm-resume.md` do NOT persist across `regenerate` (the markdown is overwritten from DB state)
- **crash-recovery.AC4.5 Failure:** `note` against a UUID not in the DB exits non-zero with a clear error and does not insert a row

### crash-recovery.AC5: Wrapper liveness lifecycle
- **crash-recovery.AC5.1 Success:** When the patched `claude-wrapper.sh` starts, `~/.claude/run/<wrapper-pid>.live` exists with key=value lines for `cwd`, `started`, `argv`, and `boot_id`
- **crash-recovery.AC5.2 Success:** Clean Claude exit (status 0) or Ctrl-C exit (status 130) causes the wrapper to remove the liveness file
- **crash-recovery.AC5.3 Success:** `kill -9` of the wrapper PID leaves the liveness file present (wrapper has no chance to remove it)
- **crash-recovery.AC5.4 Edge:** Two concurrent wrapper invocations each write distinct liveness files (PID-keyed; no collision); cleaning one does not affect the other
- **crash-recovery.AC5.5 Success:** When `claude` is killed independently of the wrapper (e.g. `kill -9 $(pgrep claude)` while the wrapper continues), the wrapper exits with non-zero status and leaves the liveness file in place. This case is missed by `trap EXIT` and is the reason exit-status inspection is required.
- **crash-recovery.AC5.6 Success:** A liveness file whose `boot_id` does not match the current `/proc/sys/kernel/random/boot_id` is classified as a casualty by `scan` regardless of whether its PID is alive (PID may have been recycled by the new boot).

### crash-recovery.AC6: Idle-live-session detection end-to-end
- **crash-recovery.AC6.1 Success:** A liveness file whose PID is no longer in `pgrep` correlates to a session UUID (via argv `--resume <uuid>` or via single-candidate mtime-window match) and is classified `hard_crash`
- **crash-recovery.AC6.2 Success:** A liveness file whose PID is still alive (verified via `kill -0`) classifies its session as `live`, never `hard_crash`
- **crash-recovery.AC6.3 Borderline:** When mtime-window correlation finds multiple candidate UUIDs, classification is `borderline` with reason `ambiguous_match` and the candidate UUID list is recorded in `state_summary`
- **crash-recovery.AC6.4 UAT:** Manually start a `claudew` from a known cwd, leave it idle for 5+ minutes (no JSONL writes), `kill -9` the wrapper PID, run `crash-recovery scan`, observe the session classified `hard_crash` despite the JSONL being stale

### crash-recovery.AC7: No automatic pruning
- **crash-recovery.AC7.1 Success:** After `regenerate`, previously-classified-concluded sessions remain present in both the DB and the rendered markdown
- **crash-recovery.AC7.2 Success:** `crash-recovery prune --dry-run` lists candidate rows but the DB row count is unchanged after the command exits
- **crash-recovery.AC7.3 Success:** `crash-recovery prune` invoked without `--confirm` refuses to delete and prints instructions on how to confirm
- **crash-recovery.AC7.4 Success:** `crash-recovery prune --confirm` deletes only rows where `classification = 'concluded' AND user_notes IS NULL AND jsonl_path` no longer exists on disk
- **crash-recovery.AC7.5 Failure:** A concluded session with a user note is NOT deleted by `prune --confirm` (note acts as preservation marker)
- **crash-recovery.AC7.6 Failure:** A concluded session whose JSONL is still on disk is NOT deleted by `prune --confirm` (filesystem-presence guard)
- **crash-recovery.AC7.7 Failure:** A session whose `classifier_version` is older than current is NOT deleted by `prune --confirm` until `scan` has re-classified it under the current rule table (prune operates only on rows reflecting current rules)

### crash-recovery.AC8: Sibling-plugin coordination
- **crash-recovery.AC8.1 Success:** `plugins/denubis-crash-recovery/README.md` documents the dependency on `denubis-plan-and-execute` and the minimum required version
- **crash-recovery.AC8.2 Success:** In the release commit, both plugins' `plugin.json` versions match the entries in `marketplace.json` (version-sync invariant from the repo's CLAUDE.md holds)
- **crash-recovery.AC8.3 Success:** The release commit adds two entries to `CHANGELOG.md`: one for `denubis-crash-recovery` first release, one for `denubis-plan-and-execute` wrapper-patch version bump

## Glossary

- **JSONL**: JSON Lines — a text format where each line is a self-contained JSON object. Claude Code writes one JSON object per event (tool call, message, result) to a session-specific `.jsonl` file. The "tail" of this file reveals how a session ended.
- **liveness file**: A small key=value text file written by `claude-wrapper.sh` at `~/.claude/run/<pid>.live` when a wrapper process starts. Its presence after the process disappears is the signal that the session did not exit cleanly.
- **claude-wrapper.sh** (also `claudew`): A shell script that wraps the `claude` binary, used as the user's primary entry point for starting Claude Code sessions. The denubis-crash-recovery plugin patches this wrapper to write and remove liveness files.
- **SQLite**: A file-based relational database. Used here as the plugin's source of truth for session state, annotations, and scan history. Lives at `~/.claude/crash-recovery.db`.
- **WAL mode**: Write-Ahead Logging — a SQLite concurrency option that allows readers and writers to operate simultaneously without blocking each other. Used to handle two concurrent `scan` invocations safely.
- **upsert**: A database write that inserts a new row if it does not exist, or updates the existing row if it does. Used so that repeated `scan` runs are idempotent rather than accumulating duplicate rows.
- **`pgrep` / `kill -0`**: Unix utilities for inspecting running processes. `pgrep` finds PIDs by name; `kill -0` checks whether a specific PID is alive without sending an actual signal. Used to determine whether a liveness file's recorded PID is still running.
- **trap EXIT**: A shell mechanism that registers a command to run when a script exits, regardless of the exit path. Considered for liveness-file cleanup but rejected in DR8 because it cannot distinguish "wrapper exited cleanly after Claude was killed" from "wrapper exited cleanly because Claude finished normally". The wrapper uses exit-status inspection instead.
- **boot_id**: The kernel-assigned identifier read from `/proc/sys/kernel/random/boot_id`, regenerated on every system boot. Liveness files include the boot_id at write time; `scan` compares against the current boot_id to detect liveness files orphaned by a reboot.
- **classifier_version**: An integer constant in the rule table, stored on every `sessions` row and on each scan run. When the rule table changes, scan re-classifies any rows whose stored value is below the current `CLASSIFIER_VERSION`. Keeps prune and render queries operating on rules currently in force.
- **PID**: Process ID — the number the operating system assigns to a running process. Liveness files are named by PID so that concurrent sessions do not collide.
- **mtime-window correlation**: The fallback method for linking a liveness file to a session UUID when `--resume <uuid>` is not present in the wrapper's argv. The CLI looks for JSONL files in the matching project directory whose last-modified time falls within the wrapper's lifetime.
- **UUID**: Universally Unique Identifier. Claude Code assigns each session a UUID, which appears in the JSONL filename and is the key used to resume a session with `claudew --resume <uuid>`.
- **encoded-cwd**: Claude Code encodes the working directory path as part of the filesystem path under `~/.claude/projects/`, making the project directory name a mangled form of the working directory.
- **skill**: In Claude Code, a skill is a markdown file (`SKILL.md`) that provides structured instructions to Claude for a specific task. The `denubis-crash-recovery:triage` skill is a thin wrapper that invokes the CLI and surfaces its output.
- **bats**: Bash Automated Testing System — a test framework for shell scripts. Used to test the wrapper liveness lifecycle (SIGTERM vs SIGKILL behaviour).
- **uv**: A fast Python package and project manager. The plugin uses `uv run --project <path>` to invoke the Python CLI without requiring a global install.
- **idempotent**: Producing the same result regardless of how many times an operation is applied. Relevant here for `scan` (repeated runs yield identical DB state except timestamps) and `init` (re-running does not corrupt or duplicate the schema).
- **deterministic classification**: Classification that produces the same output for the same input, every time, with no randomness or external judgement. Contrasted with LLM-driven classification, which may vary between runs.
- **parametrised tests**: Tests driven by a data table where each row is an independent test case. Used to verify every row of the classification rule table against a known fixture.
- **snapshot tests**: Tests that compare program output byte-for-byte against a previously committed expected file. Used to verify that the markdown render is stable across code changes.
- **marketplace.json**: A registry file in the `brian-ed3d-plugins` repo that lists all available plugins with their metadata. Required to be in sync with each plugin's `plugin.json` whenever a version changes.
- **plugin.json**: The per-plugin manifest file under `.claude-plugin/`. Declares the plugin's name, version, author, license, and registered skills.
- **denubis-plan-and-execute**: A sibling plugin in the same repo that ships `claude-wrapper.sh`. Crash-recovery depends on a patched version of this wrapper and must be released in coordination with a version bump to that plugin.

## Architecture

SQLite database is the source of truth for all session state. The `~/llm-resume.md` markdown file is a regenerated view, never user-edited. Annotations are typed via CLI (`crash-recovery note <uuid> "..."`) and stored in a database column.

Three components produce data:

1. **Patched `claude-wrapper.sh`** (in `denubis-plan-and-execute`) writes a PID-keyed liveness file at `~/.claude/run/<wrapper-pid>.live` containing `cwd`, `started`, `argv`, and `boot_id` (from `/proc/sys/kernel/random/boot_id`). After `claude` returns, the wrapper inspects Claude's exit status: status 0 (clean) or 130 (Ctrl-C, user-initiated) removes the file; any other status (signal-death, abnormal exit) leaves it. This means a `kill -9` of Claude while the wrapper is alive — a case `trap EXIT` would silently close — preserves the liveness file. On scan, a liveness file whose `boot_id` does not match the current boot is treated as a guaranteed casualty (wrappers cannot survive reboots).

2. **JSONL tail scan** reads the last few entries of each session's `~/.claude/projects/<encoded-cwd>/<uuid>.jsonl` file to detect hard-crash signatures (trailing `tool_use` with no result, trailing `AskUserQuestion` with no reply, trailing `Agent` dispatch with no result, trailing closing assistant message).

3. **Live-PID check** uses `pgrep` and `kill -0` to determine whether the PID recorded in each liveness file is still alive.

The `crash-recovery scan` subcommand fuses these inputs into deterministic classifications stored in SQLite. Rendering is a pure function of database state — same DB, byte-identical markdown.

Liveness-to-UUID correlation is post-hoc in the CLI: argv with `--resume <uuid>` is direct match; otherwise candidate JSONLs in the matching project directory are filtered by mtime within the wrapper's lifetime, with multiple candidates flagged `ambiguous_match`.

The orchestrating skill (`denubis-crash-recovery:triage`) is a thin wrapper: invokes the CLI, surfaces the report, gates destructive actions (prune requires `--dry-run` first plus explicit confirmation). No classification logic lives in the skill.

## Data Model

**SQLite database (`~/.claude/crash-recovery.db`, override via `CRASH_RECOVERY_DB`):**

```
sessions
  uuid                  TEXT PRIMARY KEY    -- claude session UUID (NULL allowed for irrecoverable rows; see note)
  project_path          TEXT NOT NULL       -- decoded ~/.claude/projects/<encoded>/ → /home/brian/...
  cwd                   TEXT NOT NULL       -- working directory for `claudew --resume`
  jsonl_path            TEXT                -- absolute path; NULL if no JSONL ever written
  jsonl_mtime           INTEGER             -- unix epoch; for cache invalidation
  jsonl_last_ts         INTEGER             -- last-entry timestamp inside the JSONL
  classification        TEXT NOT NULL       -- enum: hard_crash | borderline | concluded | live | irrecoverable
  classification_reason TEXT                -- short machine-generated reason
  classifier_version    INTEGER NOT NULL    -- version of the rule table used; scan re-classifies stale rows
  state_summary         TEXT                -- 1-line render of the last few entries
  first_seen            INTEGER NOT NULL    -- when this plugin first indexed this session
  last_scanned          INTEGER NOT NULL    -- last `scan` that touched this row
  user_notes            TEXT                -- preserved across regen; user-owned via `crash-recovery note`

scan_runs
  id                    INTEGER PRIMARY KEY
  ts                    INTEGER NOT NULL
  live_pids             TEXT                -- JSON array of currently-live PIDs at scan time
  sessions_scanned      INTEGER
  classifier_version    INTEGER NOT NULL    -- version active during this run

classification_history
  uuid                  TEXT NOT NULL
  scan_id               INTEGER NOT NULL
  classification        TEXT NOT NULL
  reason                TEXT
  classifier_version    INTEGER NOT NULL
  PRIMARY KEY (uuid, scan_id)
```

**Liveness file format** (at `~/.claude/run/<wrapper-pid>.live`, one file per running wrapper):

```
cwd=/home/brian/foo
started=1715151234
argv=--resume db0cc58f-dc30-4195-a64a-4f25a5c19d6b
boot_id=8b2f4a3d-6c0e-4f1a-9d2b-7e3c5a8b1c4d
```

`boot_id` is read from `/proc/sys/kernel/random/boot_id` and changes on every system reboot. CLI compares against the current boot_id at scan time.

**Classifier version contract:** the rule table in `crash_recovery.classify` carries an integer `CLASSIFIER_VERSION` constant. Each `scan` writes the active version to every row it upserts and to the `scan_runs` row. On subsequent scans, rows whose `classifier_version` is below the active value are re-classified before being read by render or prune. This invariant guarantees that classification queries (including prune's three-condition guard) always reflect the current rule table.

## Decision Record

### DR1: SQLite as source of truth, markdown as render
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If users want to edit the resume file directly and have changes stick. If multi-machine sync of the resume file becomes a requirement (SQLite is harder to merge than markdown).

**Decision:** We chose SQLite at `~/.claude/crash-recovery.db` as the source of truth, with `~/llm-resume.md` regenerated from DB state on every render.

**Consequences:**
- **Enables:** Deterministic regeneration without markdown parsing. User annotations are typed first-class operations. Trivial to add query/history features. No "preserve user edits" puzzle.
- **Prevents:** Ad-hoc editing of `~/llm-resume.md` (changes are overwritten on next regen). Requires CLI command to add notes.

**Alternatives considered:**
- **Per-UUID sentinel markers in single markdown file:** Rejected because parser must walk markdown and is fragile if user moves blocks between entries.
- **Sectioned single file (machine + free-form):** Rejected because notes aren't co-located with their session entries and parser still has to find the boundary.
- **Two files (machine + user):** Rejected because user has to read two files instead of one — loses the single-source-of-truth feeling.

### DR2: PID-keyed liveness files, UUID resolved post-hoc
**Status:** Accepted
**Confidence:** Medium
**Reevaluation triggers:** If correlation ambiguity (multiple candidate UUIDs in a cwd's project dir) becomes common in practice. If Claude exposes the active session UUID via an environment variable or stdout marker the wrapper could capture.

**Decision:** We chose to key the liveness file by the wrapper's PID (`~/.claude/run/<pid>.live`) and resolve to a session UUID later in the CLI scan.

**Consequences:**
- **Enables:** Wrapper writes the liveness file at startup with no race against Claude's JSONL creation. Works for new sessions and resumes alike. Simple write-once model.
- **Prevents:** Direct UUID lookup at scan time. Forces a correlation step (argv-resume vs mtime-window) in the CLI.

**Alternatives considered:**
- **UUID-keyed liveness via watch loop:** Rejected because chicken-and-egg — UUID is generated by Claude after wrapper start. Watching project dir for new JSONLs adds an inotify dependency or polling logic.
- **Update liveness file after detection:** Rejected because crash between wrapper-start and UUID-detection still leaves an unmatched liveness file.

### DR3: Patch denubis-plan-and-execute's wrapper directly
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If a third party plugin needs to add behaviour to claude-wrapper.sh, prompting a hookable wrapper architecture.

**Decision:** We chose to patch `denubis-plan-and-execute/scripts/claude-wrapper.sh` directly with the liveness logic, bumping that plugin's version alongside denubis-crash-recovery's release.

**Consequences:**
- **Enables:** Tightest path between wrapper and CLI logic; no indirection or hook discovery overhead.
- **Prevents:** Other plugins adding their own wrapper logic without coordinating with denubis-plan-and-execute. Future hookable-wrapper refactors become a separate decision.

**Alternatives considered:**
- **Hookable wrapper sourcing `~/.claude/plugins/*/wrapper-hooks/{pre,post}.sh`:** Rejected because no other plugin currently needs this; adds complexity for one consumer.
- **denubis-crash-recovery ships its own wrapper:** Rejected because the user would have to swap their fish alias, and two wrappers would coexist.

### DR4: Triage-only scope (no byobu/OOM bundling)
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If session triage proves robust and the user wants to add tmux-resurrect or OOM-hardening as siblings.

**Decision:** We chose to scope the plugin to session triage only, excluding tmux-resurrect helpers and OOM-hardening tooling discussed earlier.

**Consequences:**
- **Enables:** Smaller surface area, faster to ship, easier to reason about. Each future feature can be its own plugin.
- **Prevents:** "All-in-one crash recovery" experience. User must install and configure tmux-resurrect/OOM hardening separately if desired.

**Alternatives considered:**
- **Full denubis-crash-recovery package (triage + byobu + OOM):** Rejected as too broad for a first release; would conflate three independent concerns.
- **Triage + byobu only:** Rejected on the same grounds at smaller scale.

### DR5: Deterministic Python classification rules, no LLM in the loop
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If the rule table fails to capture meaningful borderline cases and users need narrative judgement on every run.

**Decision:** We chose deterministic Python rules (a parametrised lookup table) for session classification, with no LLM judgement during regeneration.

**Consequences:**
- **Enables:** Same input state → byte-identical output. Snapshot tests are meaningful. Rules can be unit-tested per-row. Regeneration is fast.
- **Prevents:** Nuanced "this looks like it concluded but it's borderline" judgement. The CLI can only flag `borderline` as a category — the user resolves it manually via `crash-recovery note`.

**Alternatives considered:**
- **LLM-driven classification at scan time:** Rejected because it makes regeneration non-deterministic, slow, and expensive.
- **Hybrid (rules-then-LLM-for-borderlines):** Rejected to keep the trust boundary clean — every classification has a citable rule.

### DR6: No automatic pruning
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If `~/llm-resume.md` grows too large to be useful and manual pruning becomes a chore. If the user explicitly requests prune-on-regen behaviour.

**Decision:** We chose to never automatically prune classified-concluded entries. `crash-recovery prune` only runs on explicit invocation, with `--dry-run` showing affected rows first; the skill must require explicit confirmation before destructive prune.

**Consequences:**
- **Enables:** No data loss between runs. The user owns the timing of every prune.
- **Prevents:** Self-cleaning resume file. Concluded sessions remain visible until the user acts.

**Alternatives considered:**
- **Auto-prune on regen with --no-auto-prune escape hatch:** Rejected because the user explicitly said "I'm juggling too many things; don't remove stale unless I make it clear to do so."
- **Auto-archive concluded entries to a separate section:** Rejected because the user chose SQLite-as-source-of-truth (DR1), making archiving a render concern that doesn't reduce file size meaningfully.

### DR7: Boot-aware liveness via `boot_id` in the liveness file
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If `/proc/sys/kernel/random/boot_id` becomes unreliable on the user's platform (e.g. containerised environments where `/proc` is namespaced unexpectedly).

**Decision:** We chose to include the kernel boot identifier (`/proc/sys/kernel/random/boot_id`) in every liveness file and to compare it against the current boot at scan time. Files whose `boot_id` does not match the current boot are treated as guaranteed casualties.

**Consequences:**
- **Enables:** Reboot-safety. After a system crash + reboot, stale liveness files describing PIDs that may now belong to unrelated processes cannot cause false-positive `live` classifications. The boot mismatch alone is sufficient evidence that the session is dead — no PID check needed.
- **Prevents:** Cross-boot correlation (e.g. "this session was running before reboot and is somehow still running" — physically impossible without persistence the wrapper does not provide).

**Alternatives considered:**
- **Boot-time sweep clearing `~/.claude/run/`:** Rejected because it requires either a systemd unit or a "first launch since boot" detector, both of which are extra moving parts.
- **Process start-time check via `/proc/<pid>/stat`:** Rejected because PID recycling within a single boot can produce false matches and the file is not portable across kernels.

### DR8: Conditional liveness removal by exit status (over `trap EXIT`)
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If users routinely run Claude under tools that intercept its exit status before the wrapper sees it (e.g. unusual systemd units, supervisord configurations).

**Decision:** We chose to remove the liveness file based on Claude's exit status, not via `trap EXIT`. The wrapper invokes Claude as a child, captures the exit status, and removes the liveness file only when the status is 0 (clean) or 130 (Ctrl-C, user-initiated). Any other status — including 137 (SIGKILL), 139 (SIGSEGV), or generic non-zero exits — leaves the liveness file in place.

**Consequences:**
- **Enables:** Detecting the case where Claude is killed independently of the wrapper (e.g. `kill -9 $(pgrep claude)` while the wrapper continues to live as a parent shell). A `trap EXIT` would fire on the wrapper's clean exit-after-child-death and silently remove the file.
- **Prevents:** Treating user-initiated termination (Ctrl-C, /exit) as a crash. The 130-allowlist captures Ctrl-C; clean exit captures /exit and Claude's own normal termination.

**Alternatives considered:**
- **`trap EXIT` only:** Rejected because it conflates wrapper exit with Claude exit, missing the Claude-only-kill case identified by proleptic challenge.
- **Trap on signal (SIGTERM, SIGINT) and remove there:** Rejected because the trap-based approach cannot distinguish "wrapper received SIGTERM and Claude was healthy" from "Claude crashed, wrapper noticed, exited cleanly." Exit-status inspection captures the actual signal.
- **Delete file from inside Claude on clean shutdown:** Rejected because Claude does not currently expose a hook for this and adding one couples the wrapper plugin to Claude's internals.

### DR9: Classifier version tracking via `classifier_version` column
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If rule changes prove rare enough that the version column adds noise without value. If the rule table grows to a size where bulk re-classification becomes a performance concern (use `EXPLAIN QUERY PLAN` if scan time exceeds a few seconds).

**Decision:** We chose to store an integer `classifier_version` on every `sessions` row and on every `scan_runs` row. Each scan re-classifies any rows whose stored version is older than the running CLI's `CLASSIFIER_VERSION` constant before completing.

**Consequences:**
- **Enables:** Forward-compatibility when rules evolve. Prune's three-condition guard always operates on classifications produced by the current rule table. Audit queries can join on classifier_version to reason about historical classification regimes.
- **Prevents:** Silent drift between old and new classifications stored side-by-side in the same DB. A rule change that flips a borderline session to concluded is now visible (the row's version updates) rather than masked.

**Alternatives considered:**
- **No version tracking:** Rejected because the proleptic challenge identified a real risk — prune could delete a session whose old classification said "concluded" but whose current rules would say "borderline".
- **Hash of the rule table:** Rejected as over-engineered; an integer version bumped manually with each rule change is simpler and matches typical schema-version semantics.

## Existing Patterns

Investigation of `brian-ed3d-plugins` found a direct precedent for the Python-CLI-in-a-plugin pattern: `denubis-plan-and-execute/scripts/workflow_statusline/` is a uv-managed Python package with `pyproject.toml`, `src/workflow_statusline/`, and a sibling `tests/` directory. It declares an entry point via `[project.scripts]` and is invoked from configuration as `uv run --project ~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow_statusline workflow-statusline`. denubis-crash-recovery follows this pattern: package at `plugins/denubis-crash-recovery/scripts/crash_recovery/` with the same layout and the same `uv run --project <abs-path>` invocation form. Note: the plugin directory is `denubis-crash-recovery` (matching the repo's universal `denubis-` prefix convention) while the Python package, CLI binary, AC slug, env-var prefix, and DB filename keep the bare `crash-recovery` / `crash_recovery` form for ergonomic command-line use.

Marketplace registration follows the existing `marketplace.json` schema: each plugin entry has `name`, `description`, `version`, `source` (relative path), `author`, `license`, optional `keywords`. No inter-plugin dependency declaration exists in the schema; the relationship between denubis-crash-recovery and the patched denubis-plan-and-execute wrapper is documented in the README rather than declared structurally.

Plugin layout follows the conventions seen in `denubis-plan-and-execute` and `denubis-basic-agents`: `.claude-plugin/plugin.json`, `skills/`, optional `agents/`, `hooks/`, `scripts/`, `LICENSE`, `README.md`. denubis-crash-recovery ships `.claude-plugin/`, `skills/triage/`, `scripts/crash_recovery/` (the Python package), `LICENSE`, and `README.md`. No agents or hooks are needed.

CHANGELOG entries follow the per-plugin section format `## [plugin-name] X.Y.Z` with **New:** / **Changed:** / **Fixed:** subsections — both denubis-crash-recovery's debut entry and denubis-plan-and-execute's wrapper-patch bump entry follow this format. The version-sync rule from the repo's CLAUDE.md applies: every `plugin.json` version change must update `marketplace.json` and add a CHANGELOG entry in the same commit.

Tests follow the workflow_statusline precedent: pytest tests in `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/`. The repo's top-level `pyproject.toml` currently sets `testpaths = ["tests"]`, which does NOT discover nested plugin tests. Phase 1 widens this to `testpaths = ["tests", "plugins/*/scripts/*/tests"]` so a single `uv run pytest` at the repo root picks up both root tests and plugin tests (workflow_statusline tests start running as a side-effect — acceptable). Bats tests for the wrapper patch live in the repo-root `tests/` directory alongside existing wrapper tests.

The skill ↔ CLI invocation pattern is hardcoded absolute paths, matching how workflow_statusline is configured. The skill body invokes the CLI as `uv run --project ~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery <subcommand>` (plugin directory is prefixed; CLI binary name remains bare).

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Plugin scaffold and database schema
**Goal:** Stand up the empty plugin and the SQLite schema; verify the build.

**Components:**
- `plugins/denubis-crash-recovery/.claude-plugin/plugin.json` — plugin metadata (name, version 0.1.0, author, license, keywords)
- `plugins/denubis-crash-recovery/scripts/crash_recovery/pyproject.toml` — uv-managed Python package; declares `[project.scripts]` entry `crash-recovery = "crash_recovery.__main__:main"`
- `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/` — package root with `__init__.py`, `__main__.py`, `db.py` (schema constants and connection helper)
- `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/` — pytest test layout with conftest
- `plugins/denubis-crash-recovery/README.md` — plugin overview, installation, dependency note (requires patched denubis-plan-and-execute ≥ TBD version)
- `plugins/denubis-crash-recovery/LICENSE` — CC-BY-SA-4.0 (matches sibling plugins)
- Add entry to `.claude-plugin/marketplace.json` for denubis-crash-recovery 0.1.0
- `crash-recovery init` subcommand — creates DB schema if missing, idempotent

**Dependencies:** None (first phase).

**Done when:** `uv sync --project plugins/denubis-crash-recovery/scripts/crash_recovery` succeeds, `crash-recovery --help` lists subcommands (binary name remains bare `crash-recovery`), `crash-recovery init` creates `~/.claude/crash-recovery.db` with the documented schema, and the widened `testpaths` config in repo-root `pyproject.toml` discovers tests under `plugins/*/scripts/*/tests/`. Re-running `init` is a no-op (verified by row-count and schema-hash check).
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: JSONL tail parser and classification rule table
**Goal:** Pure-function classifier from JSONL state to a classification value.

**Components:**
- `crash_recovery.jsonl` module — reads the last N entries of a JSONL file efficiently (no whole-file load), exposes a `parse_tail(path) → TailSummary` function returning the kinds of trailing entries
- `crash_recovery.classify` module — applies the deterministic rule table; `classify(tail_summary, liveness_state, pid_alive) → Classification` where `Classification` is a frozen dataclass with `value` (enum) and `reason` (string)
- Rule table data structure — declarative rows that the classifier walks; new rules added by data, not code
- Tests parametrised over the rule table, plus three failure-mode fixtures (empty JSONL, malformed JSON line, file-not-found)

**Covers ACs:** `crash-recovery.AC3.1`, `crash-recovery.AC3.2`, `crash-recovery.AC3.3` (deterministic classification + state summary line).

**Dependencies:** Phase 1 (package layout).

**Done when:** Parametrised test for every row of the rule table passes. Same JSONL state passed to `classify` twice returns identical Classification (idempotency).
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: Liveness file handling, boot awareness, and UUID correlation
**Goal:** Parse liveness files (including `boot_id`), check process-and-boot liveness, correlate to candidate session UUIDs.

**Components:**
- `crash_recovery.liveness` module — `read_liveness(path) → Liveness` parses `cwd/started/argv/boot_id` key=value lines; `current_boot_id() → str` reads `/proc/sys/kernel/random/boot_id`; `pid_alive(pid) → bool` checks via `kill -0`; `list_liveness_files(run_dir) → Iterator[Liveness]`
- `crash_recovery.correlate` module — `correlate(liveness, projects_root) → CorrelationResult` returns `direct_match(uuid)`, `mtime_match(uuid)`, `ambiguous(uuid_list)`, or `no_match`
- Tests for: argv-resume direct match; single mtime-window candidate; multiple candidates → ambiguous; zero candidates → no_match; liveness with current boot_id vs prior boot_id

**Covers ACs:** `crash-recovery.AC5.1`, `crash-recovery.AC5.4`, `crash-recovery.AC5.6`, `crash-recovery.AC6.1` (liveness file structure including boot_id, concurrent PID isolation, boot-aware classification, correlation prerequisites).

**Dependencies:** Phase 1 (package layout).

**Done when:** All correlation fixtures pass. `pid_alive` returns False for a clearly-dead PID and True for the test process's own PID. A liveness file with non-current boot_id is identifiable as such by `read_liveness` consumers.
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: `scan` subcommand
**Goal:** End-to-end pipeline that walks the filesystem, classifies, upserts SQLite rows, and re-classifies version-stale rows.

**Components:**
- `crash_recovery.scan` module — orchestrates: enumerate JSONLs in `~/.claude/projects/`, enumerate liveness files in `~/.claude/run/`, get pgrep snapshot, classify each session (writing `classifier_version` to each row), re-classify any pre-existing rows whose `classifier_version` is below current, upsert sessions table, write `scan_runs` row (with classifier_version), append `classification_history` rows
- `crash-recovery scan` CLI subcommand — wires the module to a CLI entry point; respects `CRASH_RECOVERY_DB` and `CRASH_RECOVERY_RUN_DIR`
- Concurrency safety: SQLite WAL mode, per-row upserts, scan_runs row creates the transactional boundary
- Tests: end-to-end fixture filesystem (synthetic JSONLs + synthetic liveness) → assert expected rows in DB. Scan twice → identical state (idempotency); `last_scanned` updates but `first_seen` preserves. Classifier-version-bump fixture: seed DB with rows at version N-1, run scan with version N, assert all rows now at version N with classifications recomputed.

**Covers ACs:** `crash-recovery.AC3.6`, `crash-recovery.AC4.1`, `crash-recovery.AC4.2`, `crash-recovery.AC4.3`, `crash-recovery.AC6.2` (scan correctness, idempotency, version re-classification, idle-live detection end-to-end).

**Dependencies:** Phases 1, 2, 3.

**Done when:** Fixture-driven test suite passes. Two consecutive `scan` invocations against the same fixture produce identical DB state (excluding `last_scanned` timestamps). Classifier-version-bump test passes — pre-seeded stale rows are upgraded and re-classified.
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: `render` subcommand and markdown contract
**Goal:** Pure DB-to-markdown render of `~/llm-resume.md`.

**Components:**
- `crash_recovery.render` module — `render(db_state) → str` reads from DB, formats grouped sections (currently-unfinished, idle-live-killed, recently-concluded, irrecoverable, ambiguous-match)
- Markdown contract: per-session entry shows UUID, working dir, `claudew --resume <uuid>` command, classification + reason, state-summary, user_notes (if present); sections sorted by `last_scanned` desc within each group
- `crash-recovery render` CLI — writes to file (default `~/llm-resume.md`, override via `--output` or `CRASH_RECOVERY_RESUME_PATH`)
- `crash-recovery triage` — `scan` then `render` to stdout
- `crash-recovery regenerate` — `scan` then `render` to file
- Snapshot tests: load fixture DB → render → compare against committed expected markdown byte-for-byte

**Covers ACs:** `crash-recovery.AC2.1`, `crash-recovery.AC2.2`, `crash-recovery.AC4.4`, `crash-recovery.AC7.1` (CLI invocation, deterministic render, no auto-prune behaviour visible in render).

**Dependencies:** Phase 4.

**Done when:** Snapshot test passes for at least three DB-state fixtures (empty, mixed, all-concluded). `render` against the same DB twice produces byte-identical output.
<!-- END_PHASE_5 -->

<!-- START_PHASE_6 -->
### Phase 6: `note`, `history`, `prune`, `list-live` subcommands
**Goal:** DB-side management operations.

**Components:**
- `crash_recovery.note` — set/clear `user_notes` for a session; `crash-recovery note <uuid> "<text>"` and `crash-recovery note <uuid> --clear`
- `crash_recovery.history` — read `classification_history` for a UUID; `crash-recovery history <uuid>`
- `crash_recovery.prune` — delete rows where `classification = 'concluded'` AND `user_notes IS NULL` AND `jsonl_path` does not exist on disk; `crash-recovery prune` requires `--dry-run` first to be displayed; `--confirm` flag executes
- `crash_recovery.list_live` — read liveness files, cross-reference pgrep, print currently-live sessions with cwd and pid
- Tests: note CRUD; history shows multiple snapshots after multiple scans; prune `--dry-run` is read-only and prints affected rows; prune respects all three guard conditions (must be concluded AND no note AND no JSONL on disk)

**Covers ACs:** `crash-recovery.AC2.3`, `crash-recovery.AC7.2`, `crash-recovery.AC7.3` (annotation persistence, prune guards, list-live output).

**Dependencies:** Phase 4 (DB), Phase 5 (render — `note` is verified by re-rendering and checking the note appears).

**Done when:** All four subcommand test suites pass. Prune dry-run output matches an expected fixture. Annotation persists across regeneration.
<!-- END_PHASE_6 -->

<!-- START_PHASE_7 -->
### Phase 7: Skill file and skill ↔ CLI integration
**Goal:** User-facing skill that orchestrates triage and gates destructive actions.

**Components:**
- `plugins/denubis-crash-recovery/skills/triage/SKILL.md` — invokes `crash-recovery triage` via Bash, displays output, prompts for annotations, gates prune behind explicit `--dry-run`-then-confirm
- `plugins/denubis-crash-recovery/.claude-plugin/plugin.json` updated with `skills` listing if needed (verify pattern in sibling plugins)
- bats integration test: end-to-end invocation that calls the skill's CLI command, asserts the DB has rows and the markdown render is non-empty
- README updates documenting how the skill is invoked

**Covers ACs:** `crash-recovery.AC1.2`, `crash-recovery.AC8.1` (skill registers and runs, README documents the workflow).

**Dependencies:** Phases 4, 5, 6.

**Done when:** bats test passes. Skill is discoverable via `/plugin` listing after install.
<!-- END_PHASE_7 -->

<!-- START_PHASE_8 -->
### Phase 8: Wrapper patch in denubis-plan-and-execute and version coordination
**Goal:** Land the liveness-tracking patch in the wrapper and coordinate version bumps across both plugins.

**Components:**
- `plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh` patched to: write `~/.claude/run/$$.live` with `cwd=...`, `started=...`, `argv=...`, `boot_id=$(cat /proc/sys/kernel/random/boot_id)`; replace trailing `exec` with a foreground invocation that captures Claude's exit status; remove the liveness file when exit status is 0 or 130; otherwise leave it; pass through Claude's exit status as the wrapper's exit status
- Bump `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json` version (patch increment)
- Bump `plugins/denubis-crash-recovery/.claude-plugin/plugin.json` to 1.0.0 (first user-ready release; plugin name `denubis-crash-recovery`)
- Update `marketplace.json` for both plugins
- Add two CHANGELOG entries (denubis-plan-and-execute liveness patch; denubis-crash-recovery 1.0.0 release)
- bats tests for wrapper liveness lifecycle: invoke a stub `claude` binary that exits 0 → file removed; stub that exits 130 (Ctrl-C) → file removed; stub that exits 137 (SIGKILL) → file persists; stub that exits 1 → file persists; SIGKILL the wrapper itself → file persists; verify boot_id is written and matches `/proc/sys/kernel/random/boot_id`
- Manual UAT (documented in README): start a real `claudew`, ^D it, verify no liveness file; start another, `kill -9 $(pgrep -f 'claude' | head -1)` to kill Claude only, verify the wrapper exits with non-zero and the liveness file persists; reboot the machine and verify a stale liveness file from before reboot is classified as casualty by `crash-recovery scan` regardless of any PID matching

**Covers ACs:** `crash-recovery.AC5.1` (wrapper writes file with boot_id), `crash-recovery.AC5.2` (clean/Ctrl-C exit removes), `crash-recovery.AC5.3` (kill-9 of wrapper preserves), `crash-recovery.AC5.5` (kill-9 of Claude alone preserves), `crash-recovery.AC5.6` (boot_id mismatch UAT after reboot), `crash-recovery.AC6.4` (idle-live UAT), `crash-recovery.AC8.2` (version coordination).

**Dependencies:** All prior phases. Phase 8 is intentionally last so the wrapper change — a behavioural change to a critical-path script — only lands after the rest of the plugin is proven against fixtures.

**Done when:** bats wrapper test suite passes (all five exit-status cases plus boot_id verification). Manual UAT script in README is runnable and documented. Both plugin versions, marketplace.json entries, and CHANGELOG entries are committed in the same PR.
<!-- END_PHASE_8 -->

## Additional Considerations

**Concurrency:** Two simultaneous `scan` invocations are a real risk (e.g., a triage session and a regenerate cron). SQLite WAL mode plus per-row upserts handle concurrent writes; the `scan_runs` row creates a transaction boundary so partial scans are detectable. Test for this with a fixture that races two scans.

**Backward compatibility:** Sessions that pre-date denubis-crash-recovery's installation have no liveness file. The CLI degrades gracefully: classification falls back to JSONL-tail-only heuristics for those (the methodology that worked before liveness existed). Liveness presence/absence is recorded in `sessions` as a boolean flag, so renders can flag pre-installation entries with reduced confidence.

**Future extensibility:** The classification rule table is data-driven — new rules added without code changes. If the LLM-driven judgement of borderlines becomes valuable, it can be added as a separate annotation pass that writes to `user_notes` (preserving the deterministic-classification invariant). If multi-machine sync of the resume file becomes needed, a future render mode can emit a portable JSON form alongside the markdown.

**Error handling:** Malformed JSONL lines are tolerated — the tail parser logs a warning and treats the file as `borderline` with reason `malformed_tail`. Missing project directories are tolerated — sessions with no JSONL on disk are stored as `irrecoverable`. SQLite database corruption surfaces as a fatal error from the CLI; the user can `rm ~/.claude/crash-recovery.db` and re-run `init` then `scan` to rebuild from filesystem state.

**Implementation scoping:** This design has 8 phases — the maximum for `impl-plan-write`. No further phases needed at design time; if implementation reveals a missing phase (e.g., dedicated migration tooling), it should be added as a follow-up implementation plan rather than retrofitted here.
