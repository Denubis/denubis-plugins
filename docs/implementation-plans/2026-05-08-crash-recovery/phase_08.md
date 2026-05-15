# denubis-crash-recovery Implementation Plan — Phase 8: Wrapper patch in denubis-plan-and-execute and version coordination

**Goal:** Land the liveness-tracking patch in `claude-wrapper.sh`; coordinate version bumps across both plugins; document the manual UAT scenarios.

**Architecture:** The wrapper patch adds three behaviours: (1) at startup, create `~/.claude/run/` if missing and atomically write `~/.claude/run/$$.live` with `cwd`, `started`, `argv`, `boot_id`; (2) invoke Claude in foreground (already the existing pattern — no structural change); (3) after Claude returns, inspect `EXIT_CODE` — remove the liveness file iff status is 0 or 130, otherwise leave it. Version-sync: `denubis-plan-and-execute` patch-bumps 2.32.1 → 2.32.2; `denubis-crash-recovery` minor-bumps 0.1.0 → 1.0.0 (first user-ready release). Both bumps update `.claude-plugin/marketplace.json` and add `CHANGELOG.md` entries.

**Tech Stack:** Bash 4+, bats 1.10.0, POSIX file-rename semantics for atomicity.

**Scope:** Phase 8 of 8 from `docs/design-plans/2026-05-08-crash-recovery.md`. Phase 8 is intentionally last so the wrapper change — a behaviour change to a critical-path script — only lands after the rest of the plugin is proven against fixtures.

**Codebase verified:** 2026-05-13. Wrapper is structurally ready (already uses foreground invocation with `EXIT_CODE=$?` capture at line 89-90; no `exec` to replace). No preparatory-refactor needed. bats 1.10.0 installed. Current versions: denubis-plan-and-execute 2.32.1; denubis-crash-recovery 0.1.0 after Phase 1.

**Phase Type:** functionality (the wrapper patch + bats tests verify behaviour) with infrastructure-flavoured version coordination.

---

## Acceptance Criteria Coverage

### crash-recovery.AC5: Wrapper liveness lifecycle (writer side)
- **crash-recovery.AC5.1 Success (writer side):** When the patched `claude-wrapper.sh` starts, `~/.claude/run/<wrapper-pid>.live` exists with key=value lines for `cwd`, `started`, `argv`, and `boot_id`.
- **crash-recovery.AC5.2 Success:** Clean Claude exit (status 0) or Ctrl-C exit (status 130) causes the wrapper to remove the liveness file.
- **crash-recovery.AC5.3 Success:** `kill -9` of the wrapper PID leaves the liveness file present (wrapper has no chance to remove it).
- **crash-recovery.AC5.4 Edge (writer side):** Two concurrent wrapper invocations each write distinct liveness files (PID-keyed via `$$`; no collision); cleaning one does not affect the other.
- **crash-recovery.AC5.5 Success:** When `claude` is killed independently of the wrapper, the wrapper exits with non-zero status and leaves the liveness file in place.
- **crash-recovery.AC5.6 Success (UAT, post-reboot):** A liveness file whose `boot_id` does not match the current `/proc/sys/kernel/random/boot_id` is classified as a casualty by `scan` regardless of whether its PID is alive.

### crash-recovery.AC6: Idle-live-session detection end-to-end
- **crash-recovery.AC6.4 UAT:** Manually start a `claudew` from a known cwd, leave it idle for 5+ minutes (no JSONL writes), `kill -9` the wrapper PID, run `crash-recovery scan`, observe the session classified `hard_crash` despite the JSONL being stale.

### crash-recovery.AC8: Sibling-plugin coordination
- **crash-recovery.AC8.2 Success:** In the release commit, both plugins' `plugin.json` versions match the entries in `marketplace.json` (version-sync invariant from the repo's CLAUDE.md holds).
- **crash-recovery.AC8.3 Success:** The release commit adds two entries to `CHANGELOG.md`: one for `denubis-crash-recovery` first release, one for `denubis-plan-and-execute` wrapper-patch version bump.

---

<!-- START_SUBCOMPONENT_A (tasks 1-3) -->

<!-- START_TASK_1 -->
### Task 1: Patch `claude-wrapper.sh` with liveness writer + conditional cleanup

**Verifies:** AC5.1, AC5.2, AC5.3, AC5.4, AC5.5 (writer side; full verification via Task 2 bats tests).

**Files:**
- Modify: `plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh`

**Implementation:**

The patch adds two code blocks:

**Block A — Liveness file write (insert BEFORE the existing Claude invocation, around line 86-88):**

```bash
# --- crash-recovery liveness file write (atomic) ---
CR_RUN_DIR="${CRASH_RECOVERY_RUN_DIR:-$HOME/.claude/run}"
mkdir -p "$CR_RUN_DIR"
CR_LIVE_FILE="$CR_RUN_DIR/$$.live"
CR_LIVE_TMP="$CR_RUN_DIR/$$.live.tmp"
{
    printf 'cwd=%s\n' "$PWD"
    printf 'started=%s\n' "$(date +%s)"
    printf 'argv=%s\n' "$*"
    printf 'boot_id=%s\n' "$(cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo unknown)"
} > "$CR_LIVE_TMP"
mv "$CR_LIVE_TMP" "$CR_LIVE_FILE"
# --- end crash-recovery liveness file write ---
```

Key invariants:
- `mkdir -p` is safe and idempotent; tolerates the `~/.claude/run/` directory being absent or already present.
- `CRASH_RECOVERY_RUN_DIR` env-var override exists so bats tests can point at a fixture directory.
- `$$` is the wrapper's PID; guarantees per-invocation uniqueness (AC5.4 writer side).
- `printf` (not `echo`) avoids shell-interpretation surprises in argv strings.
- `$*` (not `$@`) records the user's argv as a single space-joined string. Either `$*` or `$@` works inside double-quoted `printf %s`; `$*` is chosen for explicit single-string semantics. (Phase 3's `_extract_resume_uuid` uses `shlex.split(argv)` which would handle either form — the rationale is wrapper-side clarity, not reader-side parsing.)
- Write goes to a `.tmp` file first; `mv` is atomic (POSIX `rename(2)` semantics on the same filesystem) — Phase 3's parser never sees a half-written file.
- `cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo unknown` is defensive: on non-Linux hosts the `cat` would fail and we'd write `boot_id=unknown` rather than crashing the wrapper. This keeps the wrapper itself harmless cross-platform. The reader side (`crash-recovery scan`) does NOT rely on this fallback — it guards on `sys.platform == "linux"` and exits with code 2 before calling Phase 3's `current_boot_id()` (which would otherwise raise `FileNotFoundError` on non-Linux). So `boot_id=unknown` files exist only in pathological setups where the wrapper ran on Linux but `/proc/sys/kernel/random/boot_id` was unreadable — `scan` will see them and classify normally against the running kernel's boot_id (which definitionally won't match `"unknown"`, routing them to `liveness_boot_id_mismatch`).

**Block B — Conditional cleanup (insert immediately BEFORE `exit $EXIT_CODE` at line 121 of the on-disk wrapper):**

```bash
# --- crash-recovery liveness file cleanup ---
# DR8: remove the liveness file only on clean (0) or Ctrl-C (130) exit.
# Any other code (137 SIGKILL, 139 SIGSEGV, generic non-zero) leaves the file
# in place as evidence of an abnormal termination.
if [ "$EXIT_CODE" -eq 0 ] || [ "$EXIT_CODE" -eq 130 ]; then
    rm -f "$CR_LIVE_FILE"
fi
# --- end crash-recovery liveness file cleanup ---
```

**Why insert at line 121, not immediately after `EXIT_CODE=$?` (line 90):** the on-disk wrapper has a post-session transcript-archive block (lines 92–119) that includes a `read -r` (line 106) — it pauses for the user to press Enter before archiving. If the rm-logic ran right after line 90, the liveness file would be removed *before* the user-blocking prompt. A `kill -9` of the wrapper while it sits at the prompt would then leave no liveness file behind, masking AC5.3's signal that the wrapper was killed abnormally. Inserting just before `exit $EXIT_CODE` preserves the file across the transcript-archive prompt and only removes it once we're committed to a clean exit.

Key invariants:
- The check is exit-status based, NOT signal-trap based. This is DR8: a `trap EXIT` would fire on the wrapper's clean exit-after-child-death (AC5.5), silently removing the file even though Claude was killed.
- `rm -f` tolerates the file already being absent (defensive — though it should always exist by Block A's write).
- This block is unreachable if the wrapper itself is SIGKILLed (AC5.3) — `rm` never runs, file stays. The bats test for this case asserts the file persists.
- Known limitation: the existing bats fixture exits the stub `claude` immediately, so it never exercises the transcript-archive path. AC5.3's "wrapper SIGKILLed during transcript prompt" sub-scenario is therefore not covered by automated tests; it is verified manually via the Phase 8 UAT runbook. Accepted gap for v1.0.0.

**Step: Verify operationally**

```bash
# Quick smoke test using a fake claude that exits cleanly.
cat > /tmp/fake-claude.sh <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x /tmp/fake-claude.sh

CR_RUN_DIR=/tmp/cr-test-run
mkdir -p "$CR_RUN_DIR"
rm -rf "$CR_RUN_DIR"/*

REAL_CLAUDE=/tmp/fake-claude.sh CRASH_RECOVERY_RUN_DIR="$CR_RUN_DIR" \
  plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh --print "hello"
# Liveness file should have been written AND removed (clean exit).
ls "$CR_RUN_DIR"/*.live 2>/dev/null && echo "FAIL: liveness file persisted on clean exit" || echo "OK: liveness file removed on clean exit"
rm -rf "$CR_RUN_DIR" /tmp/fake-claude.sh
```

**Step: Commit**

```bash
git add plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh
git commit -m "feat(plan-and-execute): patch claude-wrapper.sh with liveness file write + conditional cleanup"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: bats lifecycle tests for the wrapper patch

**Verifies:** crash-recovery.AC5.1, AC5.2, AC5.3, AC5.4, AC5.5 (writer side, end-to-end).

**Files:**
- Create: `tests/test_claude_wrapper_liveness.bats`

**Implementation:**

The bats file uses a stub `claude` binary on PATH (configurable via `REAL_CLAUDE` env var, matching the wrapper's existing variable). Each test sets a different exit code on the stub and asserts the file's presence/absence.

```bash
#!/usr/bin/env bats

WRAPPER="$BATS_TEST_DIRNAME/../plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh"

setup() {
  export CR_TEST_DIR="$(mktemp -d)"
  export CRASH_RECOVERY_RUN_DIR="$CR_TEST_DIR/run"
  mkdir -p "$CRASH_RECOVERY_RUN_DIR"
  # Stub claude binary: behaviour controlled by FAKE_CLAUDE_EXIT_CODE env var.
  cat > "$CR_TEST_DIR/fake-claude.sh" <<'EOF'
#!/usr/bin/env bash
exit "${FAKE_CLAUDE_EXIT_CODE:-0}"
EOF
  chmod +x "$CR_TEST_DIR/fake-claude.sh"
  export REAL_CLAUDE="$CR_TEST_DIR/fake-claude.sh"
}

teardown() {
  rm -rf "$CR_TEST_DIR"
}

@test "AC5.1 — wrapper writes liveness file with four required keys at startup" {
  # Stub claude that sleeps so we can inspect the liveness file mid-run.
  cat > "$CR_TEST_DIR/sleep-claude.sh" <<'EOF'
#!/usr/bin/env bash
sleep 2
exit 0
EOF
  chmod +x "$CR_TEST_DIR/sleep-claude.sh"
  REAL_CLAUDE="$CR_TEST_DIR/sleep-claude.sh" "$WRAPPER" --print "test" &
  wrapper_pid=$!
  sleep 0.5  # let the wrapper write the liveness file
  live_file="$CRASH_RECOVERY_RUN_DIR/$wrapper_pid.live"
  [ -f "$live_file" ]
  grep -q "^cwd=" "$live_file"
  grep -q "^started=" "$live_file"
  grep -q "^argv=" "$live_file"
  grep -q "^boot_id=" "$live_file"
  # boot_id value matches the system's current boot_id
  expected_boot_id=$(cat /proc/sys/kernel/random/boot_id)
  grep -q "^boot_id=$expected_boot_id\$" "$live_file"
  wait "$wrapper_pid"
}

@test "AC5.2 — clean exit (0) removes the liveness file" {
  FAKE_CLAUDE_EXIT_CODE=0 "$WRAPPER" --print "test"
  [ "$(ls -1 "$CRASH_RECOVERY_RUN_DIR"/*.live 2>/dev/null | wc -l)" -eq 0 ]
}

@test "AC5.2 — Ctrl-C exit (130) removes the liveness file" {
  FAKE_CLAUDE_EXIT_CODE=130 "$WRAPPER" --print "test" || true  # wrapper exits non-zero
  [ "$(ls -1 "$CRASH_RECOVERY_RUN_DIR"/*.live 2>/dev/null | wc -l)" -eq 0 ]
}

@test "AC5.5 — Claude exit 137 (SIGKILL) preserves the liveness file" {
  FAKE_CLAUDE_EXIT_CODE=137 "$WRAPPER" --print "test" || true
  [ "$(ls -1 "$CRASH_RECOVERY_RUN_DIR"/*.live 2>/dev/null | wc -l)" -eq 1 ]
}

@test "AC5.5 — Claude exit 139 (SIGSEGV) preserves the liveness file" {
  FAKE_CLAUDE_EXIT_CODE=139 "$WRAPPER" --print "test" || true
  [ "$(ls -1 "$CRASH_RECOVERY_RUN_DIR"/*.live 2>/dev/null | wc -l)" -eq 1 ]
}

@test "AC5.5 — Claude generic non-zero exit (1) preserves the liveness file" {
  FAKE_CLAUDE_EXIT_CODE=1 "$WRAPPER" --print "test" || true
  [ "$(ls -1 "$CRASH_RECOVERY_RUN_DIR"/*.live 2>/dev/null | wc -l)" -eq 1 ]
}

@test "AC5.3 — kill -9 of wrapper preserves the liveness file" {
  cat > "$CR_TEST_DIR/sleep-claude.sh" <<'EOF'
#!/usr/bin/env bash
sleep 10
exit 0
EOF
  chmod +x "$CR_TEST_DIR/sleep-claude.sh"
  REAL_CLAUDE="$CR_TEST_DIR/sleep-claude.sh" "$WRAPPER" --print "test" &
  wrapper_pid=$!
  sleep 0.5
  # Verify file exists pre-kill
  [ -f "$CRASH_RECOVERY_RUN_DIR/$wrapper_pid.live" ]
  kill -9 "$wrapper_pid"
  wait "$wrapper_pid" 2>/dev/null || true
  # File must still exist (wrapper had no chance to clean up)
  [ -f "$CRASH_RECOVERY_RUN_DIR/$wrapper_pid.live" ]
}

@test "AC5.4 — concurrent wrappers write distinct liveness files" {
  cat > "$CR_TEST_DIR/sleep-claude.sh" <<'EOF'
#!/usr/bin/env bash
sleep 2
exit 0
EOF
  chmod +x "$CR_TEST_DIR/sleep-claude.sh"
  REAL_CLAUDE="$CR_TEST_DIR/sleep-claude.sh" "$WRAPPER" --print "first" &
  pid1=$!
  REAL_CLAUDE="$CR_TEST_DIR/sleep-claude.sh" "$WRAPPER" --print "second" &
  pid2=$!
  sleep 0.5
  [ "$pid1" != "$pid2" ]
  [ -f "$CRASH_RECOVERY_RUN_DIR/$pid1.live" ]
  [ -f "$CRASH_RECOVERY_RUN_DIR/$pid2.live" ]
  wait "$pid1" "$pid2"
  # Both should be cleaned (both exited 0)
  [ "$(ls -1 "$CRASH_RECOVERY_RUN_DIR"/*.live 2>/dev/null | wc -l)" -eq 0 ]
}

@test "wrapper records user-supplied argv verbatim in the liveness file" {
  cat > "$CR_TEST_DIR/sleep-claude.sh" <<'EOF'
#!/usr/bin/env bash
sleep 2
exit 0
EOF
  chmod +x "$CR_TEST_DIR/sleep-claude.sh"
  REAL_CLAUDE="$CR_TEST_DIR/sleep-claude.sh" "$WRAPPER" --resume db0cc58f-dc30-4195-a64a-4f25a5c19d6b &
  wrapper_pid=$!
  sleep 0.5
  live_file="$CRASH_RECOVERY_RUN_DIR/$wrapper_pid.live"
  grep -q "argv=.*--resume db0cc58f-dc30-4195-a64a-4f25a5c19d6b" "$live_file"
  wait "$wrapper_pid"
}

@test "wrapper writes liveness file atomically via tempfile + mv (no .tmp residue)" {
  # Asserts no .tmp file persists at the target path under any timing.
  REAL_CLAUDE="$CR_TEST_DIR/fake-claude.sh" FAKE_CLAUDE_EXIT_CODE=0 "$WRAPPER" --print "test"
  # After completion, no .tmp leftovers
  [ "$(ls -1 "$CRASH_RECOVERY_RUN_DIR"/*.tmp 2>/dev/null | wc -l)" -eq 0 ]
}
```

**Step: Verify operationally**

```bash
bats tests/test_claude_wrapper_liveness.bats
```

Expected: all 10 tests pass.

**Step: Commit**

```bash
git add tests/test_claude_wrapper_liveness.bats
git commit -m "test(plan-and-execute): cover wrapper liveness lifecycle AC5.1-AC5.5"
```
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Bump `denubis-plan-and-execute` version + marketplace + CHANGELOG

**Verifies:** AC8.2, AC8.3 (denubis-plan-and-execute side).

**Files:**
- Modify: `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json` (version 2.32.1 → 2.32.2)
- Modify: `.claude-plugin/marketplace.json` (denubis-plan-and-execute entry: 2.32.1 → 2.32.2)
- Modify: `CHANGELOG.md` (prepend entry)

**Implementation:**

1. **plugin.json bump:** edit `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json`, change `"version": "2.32.1"` to `"version": "2.32.2"`.

2. **marketplace.json sync:** edit `.claude-plugin/marketplace.json`, find the `denubis-plan-and-execute` entry's `version` field, update to `2.32.2`.

3. **CHANGELOG entry:** prepend the following block to `CHANGELOG.md`. (Task 4, executed after this task, will prepend a `[denubis-crash-recovery] 1.0.0` entry above this one. The final order after both tasks complete will be: crash-recovery 1.0.0 first, plan-and-execute 2.32.2 below, then the prior top entry `[denubis-bibliography] 0.1.0`.):

```markdown
## [denubis-plan-and-execute] 2.32.2

Wrapper patch: claude-wrapper.sh now writes a per-PID liveness file at `~/.claude/run/<pid>.live` containing `cwd`, `started`, `argv`, and `boot_id` at startup; on clean exit (status 0) or Ctrl-C (status 130), the file is removed. Any other exit status leaves the file in place. This is the writer side of the denubis-crash-recovery plugin's session triage; install both plugins together for the full crash-recovery workflow.

**Changed:**
- `claude-wrapper.sh`: write `~/.claude/run/$$.live` at startup (atomic via temp+mv), inspect Claude's exit status post-invocation, conditionally remove the liveness file.

**Compatibility:**
- The wrapper itself runs cross-platform: on non-Linux hosts the `cat /proc/sys/kernel/random/boot_id` falls through to `echo unknown`, so the wrapper writes `boot_id=unknown` rather than crashing.
- `crash-recovery scan` (the reader side, in the `denubis-crash-recovery` plugin) is Linux-only by design — it exits with code 2 and a clear error on non-Linux platforms. The wrapper-side fallback exists so that the `denubis-plan-and-execute` plugin remains usable on macOS / BSD for the rest of its features.
- `crash-recovery scan` also refuses to run when `CRASH_RECOVERY_RUN_DIR` is on a network or union filesystem (NFS, CIFS, sshfs, FUSE-family, etc.) because the atomic-rename semantics liveness-file writes depend on are not guaranteed there. The wrapper itself does NOT make this check — it just writes the file; the reader-side guard catches the unsafe configuration before any scan-time damage.
- `CRASH_RECOVERY_RUN_DIR` env-var overrides the default `~/.claude/run/` path (used in tests, and as the workaround for users whose `$HOME` is network-mounted).

```

4. **Version-sync verification:**

```bash
python -c "
import json
pj = json.load(open('plugins/denubis-plan-and-execute/.claude-plugin/plugin.json'))
mp = json.load(open('.claude-plugin/marketplace.json'))
entry = next(p for p in mp['plugins'] if p['name'] == 'denubis-plan-and-execute')
assert pj['version'] == entry['version'] == '2.32.2', (pj['version'], entry['version'])
print('OK')
"
```

**Step: Commit**

```bash
git add plugins/denubis-plan-and-execute/.claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md
git commit -m "release(plan-and-execute): 2.32.2 — wrapper liveness patch"
```
<!-- END_TASK_3 -->

<!-- END_SUBCOMPONENT_A -->

---

<!-- START_SUBCOMPONENT_B (tasks 4-5) -->

<!-- START_TASK_4 -->
### Task 4: Bump `denubis-crash-recovery` to 1.0.0 + marketplace + CHANGELOG + README placeholder fill

**Verifies:** AC8.2, AC8.3 (denubis-crash-recovery side).

**Files:**
- Modify: `plugins/denubis-crash-recovery/.claude-plugin/plugin.json` (version 0.1.0 → 1.0.0)
- Modify: `.claude-plugin/marketplace.json` (denubis-crash-recovery entry: 0.1.0 → 1.0.0)
- Modify: `CHANGELOG.md` (prepend entry above Phase 8 Task 3's plan-and-execute entry)
- Modify: `plugins/denubis-crash-recovery/README.md` (fill in `<PHASE-8-VERSION>` placeholder with `2.32.2`)

**Implementation:**

1. **plugin.json bump:** edit `plugins/denubis-crash-recovery/.claude-plugin/plugin.json`, change `"version": "0.1.0"` to `"version": "1.0.0"`.

2. **marketplace.json sync:** edit `.claude-plugin/marketplace.json`, find the `denubis-crash-recovery` entry, update version to `1.0.0`.

3. **CHANGELOG entry:** prepend above the plan-and-execute 2.32.2 entry:

```markdown
## [denubis-crash-recovery] 1.0.0

First user-ready release. Identifies and resumes Claude Code sessions that ended abnormally (kernel kill, terminal disconnect, process crash). Combines liveness-file detection (via `denubis-plan-and-execute`'s patched wrapper, ≥2.32.2) with JSONL-tail-only heuristics; deterministic Python rule table classifies every session as `live`, `hard_crash`, `borderline`, `concluded`, or `irrecoverable`; SQLite at `~/.claude/crash-recovery.db` is the source of truth; `~/llm-resume.md` regenerates byte-identically from DB state.

**New:**
- `crash-recovery` CLI with nine subcommands: `init`, `scan`, `render`, `triage`, `regenerate`, `note`, `history`, `prune`, `list-live`.
- `denubis-crash-recovery:triage` skill orchestrates scan + annotation prompt + gated prune.
- SQLite schema: `sessions`, `scan_runs`, `classification_history` with `classifier_version` column for forward-compat re-classification.
- Deterministic rule table; one assertion per row via parametrised tests.
- Atomic resume-file write (`tempfile + os.replace`).

**Requires:**
- `denubis-plan-and-execute ≥ 2.32.2` for the wrapper patch.
- Linux for the `scan` subcommand: it reads `/proc/sys/kernel/random/boot_id` for reboot detection and exits with code 2 on non-Linux platforms. The remaining subcommands (`init`, `render`, `triage`, `note`, `history`, `prune`, `list-live`) are filesystem/DB-only and run anywhere — but `triage` invokes `scan` internally, so the practical effect is "this plugin needs Linux".

**Out of scope (future plans):**
- byobu/tmux-resurrect helpers.
- OOM-hardening for the wrapper itself.
- LLM judgement on borderline cases (deterministic rules only; user annotates manually via `crash-recovery note`).
- Automatic pruning (explicit `prune --dry-run` then `--confirm` only).
```

4. **README placeholder fill:** edit `plugins/denubis-crash-recovery/README.md`, replace every occurrence of `<PHASE-8-VERSION>` with `2.32.2`.

5. **Combined version-sync verification (covers AC8.2 for both plugins):**

```bash
python -c "
import json
mp = json.load(open('.claude-plugin/marketplace.json'))
for plugin_name, expected_version in [
    ('denubis-plan-and-execute', '2.32.2'),
    ('denubis-crash-recovery', '1.0.0'),
]:
    pj_path = f'plugins/{plugin_name}/.claude-plugin/plugin.json'
    pj = json.load(open(pj_path))
    entry = next(p for p in mp['plugins'] if p['name'] == plugin_name)
    assert pj['version'] == entry['version'] == expected_version, (plugin_name, pj['version'], entry['version'])
    print(f'OK: {plugin_name}@{expected_version}')
"
```

6. **CHANGELOG entry-count verification (covers AC8.3):**

```bash
# Verify both new entries are present and in the correct order (crash-recovery first, plan-and-execute below).
grep -n "^## \[" CHANGELOG.md | head -3
# Expected first line: ## [denubis-crash-recovery] 1.0.0
# Expected second line: ## [denubis-plan-and-execute] 2.32.2
# Expected third line: ## [denubis-bibliography] 0.1.0  (the previous top entry)
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/.claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md plugins/denubis-crash-recovery/README.md
git commit -m "release(crash-recovery): 1.0.0 — first user-ready release"
```
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: UAT runbooks (final) + completion check

**Verifies:** AC5.6 (post-reboot UAT runnable), AC6.4 (idle-kill UAT runnable).

**Files:**
- Modify: `plugins/denubis-crash-recovery/README.md` (finalise UAT runbook wording — Phase 7 stubbed these; Phase 8 polishes once wrapper behaviour is concrete)

**Implementation:**

Replace the two UAT runbook sections in README.md with polished, executable text. Each runbook is a numbered step list with **expected observation** for the human evaluator.

**AC5.6 — Post-reboot UAT:**

```markdown
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
   "Idle-live killed" section with `classification: hard_crash` and `reason: liveness_boot_id_mismatch`.

   It's wrong if: the session is misclassified as `live`, `concluded`, or shows a different
   reason. A misclassification here means the reboot-safety mechanism didn't engage —
   investigate `current_boot_id()` (Phase 3) and the rule-table ordering in `classify.py`
   (Phase 2).
```

**AC6.4 — Idle-kill UAT:**

```markdown
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
7. **Expected observation:** the session appears in "Idle-live killed" with
   `classification: hard_crash`. The JSONL's tail looks concluded (the last entry
   was a clean assistant turn), but the liveness mechanism catches that the wrapper
   never got a chance to clean up.

   It's wrong if: the session is misclassified as `concluded`. That would mean the
   classifier is relying on the JSONL tail alone and ignoring the liveness signal —
   the bug is in Phase 4's scan wiring or Phase 2's rule ordering (`live_pid_present`
   vs `hard_crash_*` rules).
```

**Step: Verify documentation**

```bash
grep -A 5 "^### AC5.6" plugins/denubis-crash-recovery/README.md
grep -A 5 "^### AC6.4" plugins/denubis-crash-recovery/README.md
```

Both must surface a "Expected observation" line.

**Step: Run full repo test suite to confirm Phases 1–8 cumulative**

```bash
uv run pytest -q
bats tests/test_claude_wrapper_liveness.bats
bats tests/test_crash_recovery_smoke.bats
```

All must pass.

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/README.md
git commit -m "docs(crash-recovery): finalise UAT runbooks for AC5.6 and AC6.4"
```
<!-- END_TASK_5 -->

<!-- END_SUBCOMPONENT_B -->

---

## Phase 8 Done When

- `plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh` writes a liveness file at startup (atomically) and conditionally removes it based on Claude's exit code.
- bats lifecycle tests pass for all 10 cases: AC5.1 four-key check; AC5.2 × 2 clean-exit paths; AC5.3 wrapper-SIGKILL; AC5.4 concurrent wrappers; AC5.5 × 3 abnormal exits; argv-verbatim recording; atomic tempfile-then-mv write.
- `denubis-plan-and-execute` bumped to 2.32.2 with marketplace + CHANGELOG.
- `denubis-crash-recovery` bumped to 1.0.0 with marketplace + CHANGELOG; README `<PHASE-8-VERSION>` filled with `2.32.2`.
- Version-sync invariant verified (AC8.2): both plugins' plugin.json + marketplace.json agree.
- CHANGELOG.md carries both new entries above the prior top entry (AC8.3).
- UAT runbooks for AC5.6 and AC6.4 are executable text in README.
- Repo-root `uv run pytest -q` passes; both bats files pass.

## End of Phase 8

This is the final implementation phase. The next steps are:
- **Finalization**: code-reviewer pass over all eight phase files (this implementation plan's tracked Finalization task).
- **Test Requirements**: generate `test-requirements.md` mapping every AC to its automated test path.
- **UAT Requirements**: collate `uat-requirements.md` from the three UAT entries produced across phases (Phase 7 prune-prompt clarity + Phase 8 AC5.6 + Phase 8 AC6.4).
- **Execution handoff**: hand the plan to `executing-an-implementation-plan` with verified absolute paths.
