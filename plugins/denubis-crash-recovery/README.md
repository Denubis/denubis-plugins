# denubis-crash-recovery

Identify and resume Claude Code sessions that ended abnormally. The plugin
classifies live, crashed, borderline, concluded, and irrecoverable sessions
deterministically from local state (liveness files, JSONL tails, live PIDs),
then renders `~/llm-resume.md` containing the resume command and reason for
each affected session. The markdown is always regenerated from the SQLite
database — never edited by hand — so regeneration is byte-identical given the
same inputs.

## Installation

```bash
claude plugin install denubis-crash-recovery@brian-ed3d-plugins
```

After installation, verify with `/plugin` — `denubis-crash-recovery` must
appear with the version recorded in `plugin.json`.

## Dependency

Requires `denubis-plan-and-execute` >= `2.32.2` for the wrapper
patch that writes liveness files. Both plugins must be installed, and the
wrapper must have run before the crash, for crash detection to work.

Without the wrapper having run before the crash, `hard_crash` and `live`
classifications cannot fire — every rule producing them requires a
liveness file (see `classify.py::RULES`). Crashed sessions appear under
"Needs investigation" as `unknown_tail_kind` or `no_liveness_dangling_*`,
not as recoverable crashes. Retroactive recovery for sessions that ran
before the wrapper was installed is tracked in
`docs/design-plans/2026-05-19-post-mortem-crash-detection.md`.

## Usage — common flows

- "I think a session just crashed" — invoke the `/denubis-crash-recovery:triage`
  skill, or run `crash-recovery triage` directly. The skill walks through
  classification, optional annotation, and the gated prune flow.
- "I want to clean up the resume file" — run `crash-recovery prune --dry-run`
  to see candidates, then `crash-recovery prune --confirm` to delete.
- "I want to know what happened to session X" — run
  `crash-recovery history <uuid>` to see the classification trail.

Full subcommand reference is under `crash-recovery --help`. The database lives
at `~/.claude/crash-recovery.db` (override with `CRASH_RECOVERY_DB`). Run
`crash-recovery init` once to create the schema; the command is idempotent.

## UAT scenarios

### AC5.6 — Boot_id mismatch after reboot

This UAT verifies that crash-recovery correctly identifies sessions that cannot have
survived a reboot, regardless of whether a recycled PID happens to match the recorded
wrapper PID.

1. Start a wrapped Claude session in a known cwd:
   ```
   cd ~/some/project && claudew --resume <existing-uuid>
   ```
2. Type one or two messages so the JSONL has fresh entries; verify the liveness file
   exists: `ls ~/.claude/run/`.
3. Exit Claude cleanly (`/exit` or Ctrl-D). Verify the liveness file is gone:
   `ls ~/.claude/run/`.
4. Start the session again the same way (Step 1) and leave Claude running.
5. **Reboot the machine.** (This is the destructive step — save your work everywhere first.)
6. After reboot, run: `crash-recovery scan && crash-recovery triage`.
7. **Expected observation:** the session you had running pre-reboot appears in the
   "Probable system-crash victims" section with `classification: hard_crash` and `reason: liveness_boot_id_mismatch`.

   It's wrong if: the session is misclassified as `live`, `concluded`, or shows a different
   reason. A misclassification here means the reboot-safety mechanism didn't engage —
   investigate `current_boot_id()` (Phase 3) and the rule-table ordering in `classify.py`
   (Phase 2).

### AC6.4 — Idle session killed via SIGKILL

This UAT verifies the liveness mechanism catches what JSONL-tail-only heuristics
would miss: a session that looked concluded (clean trailing entries) but whose
wrapper was killed.

1. Start a wrapped Claude session in a known cwd:
   ```
   cd ~/some/project && claudew
   ```
2. Have one normal exchange (a message + assistant response). Verify the liveness
   file exists: `ls ~/.claude/run/`.
3. Leave the session idle for at least 5 minutes (do NOT type anything — the JSONL
   should NOT receive new entries during this window).
4. Kill the wrapper process from another terminal:
   ```
   pgrep -af claude-wrapper.sh    # find the wrapper PID
   kill -9 <wrapper-pid>
   ```
5. Confirm the liveness file PERSISTED: `ls ~/.claude/run/` — your wrapper's PID
   should still have a `.live` file.
6. Run: `crash-recovery scan && crash-recovery triage`.
7. **Expected observation:** the session appears in "Probable system-crash victims" with
   `classification: hard_crash`. The JSONL's tail looks concluded (the last entry
   was a clean assistant turn), but the liveness mechanism catches that the wrapper
   never got a chance to clean up.

   It's wrong if: the session is misclassified as `concluded`. That would mean the
   classifier is relying on the JSONL tail alone and ignoring the liveness signal —
   the bug is in Phase 4's scan wiring or Phase 2's rule ordering (`live_pid_present`
   vs `hard_crash_*` rules).

## Troubleshooting

- **`scan` exits with `requires Linux` on macOS or BSD.** The `scan`
  subcommand reads `/proc/sys/kernel/random/boot_id` and is Linux-only by
  design. The other subcommands (`init`, `render`, `note`, `history`,
  `prune`, `list-live`) work cross-platform against an existing DB, but the
  scan and triage flows need Linux.
- **`scan` exits with `does not provide reliable atomic-rename semantics`.**
  `~/.claude/run/` is on a network or union filesystem (NFS, CIFS, sshfs,
  FUSE) that cannot guarantee atomic `rename(2)` for liveness-file writes.
  Set `CRASH_RECOVERY_RUN_DIR` to a path on a local filesystem such as ext4,
  btrfs, xfs, zfs, or tmpfs.
- **`scan` runs but reports zero sessions.** Check `CRASH_RECOVERY_RUN_DIR`
  and `CRASH_RECOVERY_PROJECTS_ROOT` env vars; check `~/.claude/run/` exists
  and that the `denubis-plan-and-execute` wrapper has been invoked at least
  once since install.
- **Pruned a session you wanted to keep.** There is no audit trail by design — the prune flow does not log deletions. Preserve future sessions
  by adding `crash-recovery note <uuid>` before they get pruned.
- **Schema corruption.** Rebuild from filesystem state:

  ```bash
  rm ~/.claude/crash-recovery.db && crash-recovery init && crash-recovery scan
  ```

### Wrapper-side failure modes (writer)

The entries above cover the reader side (`crash-recovery scan` and friends).
The wrapper in `denubis-plan-and-execute` is the writer and has its own
failure modes:

- **Liveness-file write permission errors (`~/.claude/run/` not writable by
  the user).** The wrapper's `mkdir -p` or temp-file write fails with
  `Permission denied`; no liveness file appears for the session.
  Remediation: `chown -R "$USER" ~/.claude/run/` (or delete the directory and
  let the wrapper recreate it on next launch).
- **Wrapper crashed before atomic-rename so a temp file is orphaned
  (`~/.claude/run/<pid>.live.tmp` left behind).** Symptom: stale `.tmp`
  files accumulate alongside real `.live` files; `scan` ignores them but
  they consume inodes. Remediation: `find ~/.claude/run/ -name '*.live.tmp'
  -delete` (safe to run any time; the wrapper writes the final `.live` name
  via atomic rename, so a `.tmp` file is by definition not in use).
- **Writer/reader on different filesystems (NFS-mounted home with
  local-only `/run`, or the reverse).** The wrapper writes to its
  `CRASH_RECOVERY_RUN_DIR` (default `~/.claude/run/`); `scan` reads from
  whatever `CRASH_RECOVERY_RUN_DIR` it sees at scan time. If those resolve
  to different paths, `scan` sees no liveness files. Remediation: set
  `CRASH_RECOVERY_RUN_DIR` consistently in both the wrapper's environment
  and the shell that invokes `scan` (e.g. export it from `~/.bashrc` or
  `~/.zshrc` so both inherit it).
- **`boot_id=unknown` in a liveness file written before
  `/proc/sys/kernel/random/boot_id` was readable.** Indicates the wrapper
  ran on Linux but the boot-id file was not yet present (early boot, or a
  pathological container without `/proc`). `scan` will classify such files
  as `liveness_boot_id_mismatch` against the current kernel's boot_id
  (which definitionally is not `"unknown"`), so they route to `hard_crash`.
  Remediation: usually none needed — the classification is correct
  (the wrapper could not survive a reboot anyway). If `boot_id=unknown`
  appears repeatedly on a healthy system, verify `/proc` is mounted
  (`mount | grep proc`) and that `/proc/sys/kernel/random/boot_id` is
  readable as the wrapper's user.

## Status

v1.0.0 ships the plugin, the SQLite schema, the full classification pipeline
(`init`, `scan`, `classify`, `render`, `note`, `history`, `prune`,
`list-live`, `regenerate`, `triage`), and the user-facing triage skill.
Crash detection is operational end-to-end as of 1.0.0; requires
`denubis-plan-and-execute >= 2.32.2` for the wrapper that writes liveness
files.
