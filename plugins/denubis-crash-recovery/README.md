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

### AC5.6 — boot_id mismatch after reboot

1. Start a wrapped Claude Code session via `denubis-plan-and-execute` and let
   it run long enough that a liveness file is written under `~/.claude/run/`.
2. Reboot the machine.
3. After reboot, run `crash-recovery scan`.
4. Assert the pre-reboot session is classified `hard_crash` with reason
   `liveness_boot_id_mismatch`, regardless of whether the recorded PID has
   been recycled.

### AC6.4 — idle-kill of a wrapper process

1. Start a wrapped Claude Code session in a known cwd and leave it idle for
   five or more minutes.
2. Find the wrapper PID and kill it ungracefully:

   ```bash
   kill -9 $(pgrep -f 'claude' | head -1)
   ```

3. Run `crash-recovery scan`.
4. Assert the session is classified `hard_crash` despite a stale JSONL whose
   tail might otherwise look idle-concluded.

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
- **Pruned a session you wanted to keep.** There is no audit trail in v0.1.0
  by design — the prune flow does not log deletions. Preserve future sessions
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

v0.1.0 ships the plugin, the SQLite schema, the full classification pipeline
(`init`, `scan`, `classify`, `render`, `note`, `history`, `prune`,
`list-live`, `regenerate`, `triage`), and the user-facing triage skill. The
wrapper-patch dependency on `denubis-plan-and-execute` lands in Phase 8 of
the implementation plan, at which point crash detection becomes operational
end-to-end.
