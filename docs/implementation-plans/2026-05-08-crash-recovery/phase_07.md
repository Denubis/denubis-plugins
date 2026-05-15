# denubis-crash-recovery Implementation Plan — Phase 7: Skill file and skill ↔ CLI integration

**Goal:** Ship the user-facing `triage` skill that orchestrates `crash-recovery triage`, surfaces the report, prompts for annotations, and gates the prune flow behind an explicit user confirmation.

**Architecture:** The `triage` skill is a SKILL.md markdown file. Its body walks through: (1) invoke `crash-recovery triage` via Bash to produce a live report; (2) iterate borderline/hard_crash entries and prompt for annotations via AskUserQuestion (the user can opt to skip annotation entirely); (3) optionally run `crash-recovery prune --dry-run`, surface candidates, AskUserQuestion-gate the deletion, then invoke `--confirm` only on explicit user yes. README documents the skill workflow, the sibling-plugin dependency, and the two UAT scenarios (AC5.6 post-reboot, AC6.4 idle-kill). A bats smoke test exercises the CLI pipeline end-to-end.

**Tech Stack:** Markdown (skill body), Bash (skill-invoked commands), bats-core (smoke test).

**Scope:** Phase 7 of 8 from `docs/design-plans/2026-05-08-crash-recovery.md`.

**Codebase verified:** 2026-05-13. Skills auto-discovered from `skills/` (no plugin.json update needed per Phase 1B); existing bats tests live in repo-root `tests/`; writing-skills + writing-claude-directives sub-skills available as references during implementation.

**Phase Type:** infrastructure (the skill is markdown documentation invoking already-tested CLI; the bats test is regression coverage).

---

## Acceptance Criteria Coverage

### crash-recovery.AC1: Plugin installs and registers
- **crash-recovery.AC1.2 Success:** After install, `/plugin` lists `denubis-crash-recovery` with the version in `plugin.json`

  *Verified by Phase 7 because the plugin's marketplace registration (Phase 1 Task 3) becomes user-meaningful only after the triage skill is present — `/plugin` listing is a discoverability check that the skill is the user's reason to install. The phase test invokes `claude plugin install` against a local marketplace and asserts `denubis-crash-recovery` appears in the listing.*

### crash-recovery.AC8: Sibling-plugin coordination
- **crash-recovery.AC8.1 Success:** `plugins/denubis-crash-recovery/README.md` documents the dependency on `denubis-plan-and-execute` and the minimum required version

---

<!-- START_SUBCOMPONENT_A (tasks 1-2) -->

<!-- START_TASK_1 -->
### Task 1: `skills/triage/SKILL.md`

**Verifies:** AC1.2 (skill is discoverable post-install) — full verification via Task 3 bats test.

**Files:**
- Create: `plugins/denubis-crash-recovery/skills/triage/SKILL.md`

**Implementation:**

SKILL.md must include:

1. **Frontmatter** matching the repo's `test_skill_descriptions.py` requirements (description ≤200 chars, no scholar surnames, no parenthetical enumerations, leads with "Use when…"):

   ```yaml
   ---
   name: triage
   description: Use when checking which Claude Code sessions ended abnormally (crashed, killed, idle-disconnected) and producing ~/llm-resume.md with deterministic classification and gated prune.
   user-invocable: true
   last-reviewed: 2026-05-13
   ---
   ```

   The description must be measured with `wc -c` after writing — the QA test caps at 200 chars. Tighten if over.

2. **Body skeleton** (sections required, in order):

   - **Overview** — one paragraph: what triage does, when to invoke it (after suspected crash, before starting fresh sessions, periodically).
   - **Announce at start** — instruction: "I'm using the denubis-crash-recovery:triage skill to inspect session state."
   - **Step 1: Run triage** — invoke `uv run --project ~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery triage` via Bash; show output verbatim to the user.
   - **Step 2: Annotate borderline entries (optional)** — if the report has rows under "Ambiguous correlation", "Needs investigation", or "Idle-live killed" that the user wants to mark, use AskUserQuestion to prompt for each: "Add a note to <uuid-short> (cwd: <cwd>)? (yes/no/skip all)". If yes, prompt for text, then invoke `crash-recovery note <uuid> "<text>"`.
     - **Manual-review tag:** entries whose classification reason is `unmatched` (rendered with the `Something fucky — let's go look` warning) get a `[manual review]` tag in the prompt and are surfaced *first* in the iteration order. These are the combinations Phase 2's rule table doesn't cover; the user is the only signal for what they mean.
   - **Step 3: Prune (optional, gated)** — if there are concluded entries with vanished JSONLs, offer a prune flow:
     1. Run `crash-recovery prune --dry-run`; show output.
     2. If candidates exist, AskUserQuestion: "Delete N concluded sessions whose JSONLs are gone? This permanently removes their DB rows. (yes / no / show me again)"
     3. On "yes": run `crash-recovery prune --confirm`; show the deletion count.
     4. On "no": print "Prune skipped. You can re-run later with `crash-recovery prune --confirm`."
   - **Step 4: Regenerate the resume file** — invoke `crash-recovery regenerate`; show the resulting path.
   - **Common rationalisations** — table:
     | Rationalisation | Why it's wrong |
     |---|---|
     | "I'll prune without --dry-run, --confirm is enough" | The dry-run gate is for *you*, not the CLI — see the list before acting. |
     | "The session looks concluded, I'll add no notes" | A note is the only way to preserve a concluded entry past prune. If you care about a concluded session, add a note. |
     | "I'll skip rerun-scan and prune the stale rows anyway" | AC7.7: stale-version rows are excluded from prune. Run `scan` first. |
   - **Integration** — how this skill pairs with `denubis-plan-and-execute`'s wrapper patch (Phase 8 dependency).

3. **Skill description constraint check:**

   ```bash
   wc -c plugins/denubis-crash-recovery/skills/triage/SKILL.md  # informational
   # Extract description and assert length:
   python -c "
   import re
   fm = open('plugins/denubis-crash-recovery/skills/triage/SKILL.md').read()
   m = re.search(r'^description:\s*(.+)$', fm, re.MULTILINE)
   assert m, 'no description'
   desc = m.group(1).strip()
   assert len(desc) <= 200, f'{len(desc)} > 200'
   print(f'OK: {len(desc)} chars')
   "
   ```

**Step: Run skill-description QA test**

```bash
uv run pytest tests/test_skill_descriptions.py -k triage -q
```

Expected: passes (new skill description ≤200 chars, no scholar names, no parenthetical enumeration, leads with "Use when").

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/skills/triage/SKILL.md
git commit -m "feat(crash-recovery): add triage skill body with annotation + prune gate flow"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: README documents skill usage + sibling dependency

**Verifies:** AC8.1.

**Files:**
- Modify: `plugins/denubis-crash-recovery/README.md`

**Implementation:**

Replace the Phase 1 skeleton's "TBD-PHASE-8" placeholder and add full skill documentation. Required sections (≤120 lines total, no emojis):

1. **Overview** — same as Phase 1's skeleton.
2. **Installation** — `claude plugin install denubis-crash-recovery@brian-ed3d-plugins`, then verify with `/plugin`.
3. **Dependency** — explicit text: "Requires `denubis-plan-and-execute` ≥ `<PHASE-8-VERSION>` for the wrapper patch that writes liveness files. Both plugins must be installed and at the documented versions for crash detection to work. If `denubis-plan-and-execute` is at an older version, crash-recovery still runs but degrades to JSONL-tail-only heuristics (no liveness file detection)." `<PHASE-8-VERSION>` is a placeholder Phase 8 Task fills in when the wrapper-patch version is known.
4. **Usage — common flows:**
   - "I think a session just crashed" → invoke `/denubis-crash-recovery:triage` skill (or run `crash-recovery triage` directly).
   - "I want to clean up the resume file" → `crash-recovery prune --dry-run` then `--confirm`.
   - "I want to know what happened to session X" → `crash-recovery history <uuid>`.
5. **UAT scenarios** — two short runbooks (numbered steps), one per UAT:
   - **AC5.6 (boot_id mismatch after reboot):** start a wrapped Claude session; let it run long enough that liveness file exists; reboot the machine; after reboot, run `crash-recovery scan`; assert the pre-reboot session is classified `hard_crash` with reason `liveness_boot_id_mismatch`, regardless of whether the recorded PID has been recycled.
   - **AC6.4 (idle-kill):** start a wrapped Claude session in a known cwd; leave idle 5+ minutes; `kill -9 $(pgrep -f 'claude' | head -1)` to kill the wrapper PID; run `crash-recovery scan`; assert the session is classified `hard_crash` despite a stale JSONL.
6. **Troubleshooting:**
   - "`scan` exits with `requires Linux` on macOS/BSD" → the `scan` subcommand reads `/proc/sys/kernel/random/boot_id` and is Linux-only by design. The other subcommands (`init`, `render`, `note`, `history`, `prune`, `list-live`) work cross-platform against an existing DB, but the scan/triage flow needs Linux.
   - "`scan` exits with `does not provide reliable atomic-rename semantics`" → `~/.claude/run/` is on a network or union filesystem (NFS, CIFS, sshfs, FUSE, etc.) that cannot guarantee atomic `rename(2)` for liveness-file writes. Set `CRASH_RECOVERY_RUN_DIR` to a path on a local filesystem (ext4, btrfs, xfs, zfs, tmpfs).
   - "`scan` runs but reports 0 sessions" → check `CRASH_RECOVERY_RUN_DIR` and `CRASH_RECOVERY_PROJECTS_ROOT` env vars; check `~/.claude/run/` exists and `denubis-plan-and-execute`'s wrapper has been invoked at least once after install.
   - "Pruned a session I wanted to keep" → there is no audit trail in v0.1.0 by design (the prune flow does not log deletions); preserve future sessions by adding `note <uuid>` before they get pruned.
   - "Schema corruption" → `rm ~/.claude/crash-recovery.db && crash-recovery init && crash-recovery scan` rebuilds from filesystem state.

**Step: Verify**

```bash
test -f plugins/denubis-crash-recovery/README.md
grep -q "denubis-plan-and-execute" plugins/denubis-crash-recovery/README.md
grep -q "AC5.6" plugins/denubis-crash-recovery/README.md
grep -q "AC6.4" plugins/denubis-crash-recovery/README.md
wc -l plugins/denubis-crash-recovery/README.md   # ≤120 lines
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/README.md
git commit -m "docs(crash-recovery): document triage skill, sibling dependency, UAT runbooks"
```
<!-- END_TASK_2 -->

<!-- END_SUBCOMPONENT_A -->

---

<!-- START_SUBCOMPONENT_B (task 3) -->

<!-- START_TASK_3 -->
### Task 3: bats smoke test for the CLI pipeline

**Verifies:** AC1.2 indirectly (the skill's CLI invocations work in sequence); regression guard for future refactors.

**Files:**
- Create: `tests/test_crash_recovery_smoke.bats`

**Implementation:**

The bats test exercises the CLI commands the skill body invokes, end-to-end:

```bash
#!/usr/bin/env bats

setup() {
  export CRASH_RECOVERY_TEST_TMP="$(mktemp -d)"
  export CRASH_RECOVERY_DB="$CRASH_RECOVERY_TEST_TMP/x.db"
  export CRASH_RECOVERY_RUN_DIR="$CRASH_RECOVERY_TEST_TMP/run"
  export CRASH_RECOVERY_PROJECTS_ROOT="$CRASH_RECOVERY_TEST_TMP/projects"
  export CRASH_RECOVERY_RESUME_PATH="$CRASH_RECOVERY_TEST_TMP/llm-resume.md"
  mkdir -p "$CRASH_RECOVERY_RUN_DIR" "$CRASH_RECOVERY_PROJECTS_ROOT"
}

teardown() {
  rm -rf "$CRASH_RECOVERY_TEST_TMP"
}

CR="uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery"

@test "init creates the database" {
  run $CR init
  [ "$status" -eq 0 ]
  [ -f "$CRASH_RECOVERY_DB" ]
}

@test "triage on empty filesystem prints minimal render with six sections" {
  $CR init
  run $CR triage
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "Currently unfinished"
  echo "$output" | grep -q "Idle-live killed"
  echo "$output" | grep -q "Ambiguous correlation"
  echo "$output" | grep -q "Needs investigation"
  echo "$output" | grep -q "Recently concluded"
  echo "$output" | grep -q "Irrecoverable"
}

@test "regenerate writes file at CRASH_RECOVERY_RESUME_PATH" {
  $CR init
  $CR regenerate
  [ -f "$CRASH_RECOVERY_RESUME_PATH" ]
  grep -q "# Claude Code session resume" "$CRASH_RECOVERY_RESUME_PATH"
}

@test "render is byte-identical across two calls (AC3.2 smoke)" {
  $CR init
  $CR regenerate
  first_hash=$(sha256sum "$CRASH_RECOVERY_RESUME_PATH" | cut -d' ' -f1)
  $CR regenerate
  second_hash=$(sha256sum "$CRASH_RECOVERY_RESUME_PATH" | cut -d' ' -f1)
  [ "$first_hash" = "$second_hash" ]
}

@test "prune without --confirm refuses (AC7.3 smoke)" {
  $CR init
  run $CR prune
  [ "$status" -ne 0 ]
  echo "$output" | grep -q "confirm"
}

@test "denubis-crash-recovery is listed in marketplace.json" {
  python3 -c "
import json
m = json.load(open('.claude-plugin/marketplace.json'))
assert any(p['name'] == 'denubis-crash-recovery' for p in m['plugins'])
"
}
```

The last test (`marketplace.json` listing) is the closest we can get to AC1.2 in an automated test — true `claude plugin install` listing requires a live Claude Code instance.

**Step: Verify operationally**

```bash
bats tests/test_crash_recovery_smoke.bats
```

Expected: all 6 tests pass.

**Step: Commit**

```bash
git add tests/test_crash_recovery_smoke.bats
git commit -m "test(crash-recovery): add bats smoke test for end-to-end CLI pipeline"
```
<!-- END_TASK_3 -->

<!-- END_SUBCOMPONENT_B -->

---

## Phase 7 Done When

- `plugins/denubis-crash-recovery/skills/triage/SKILL.md` exists with frontmatter description ≤200 chars (verified by `tests/test_skill_descriptions.py`).
- README documents the dependency on `denubis-plan-and-execute` (AC8.1) and the two UAT runbooks for AC5.6 and AC6.4.
- bats smoke test passes.
- Repo-root `uv run pytest -q` passes (description QA test now also covers `triage`).

## Outstanding for later phases

- Phase 8: wrapper patch, version bumps (crash-recovery to 1.0.0; denubis-plan-and-execute patch increment), marketplace + CHANGELOG sync, AC5.1/AC5.2/AC5.3/AC5.5/AC5.6 writer side, AC6.4 idle-kill UAT, AC8.2/AC8.3.
