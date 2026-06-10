# Human Test Plan — denubis-crash-recovery 1.0.0

Generated from test-analysis against `test-requirements.md` and `uat-requirements.md`.
Source SHA range: `deaf92a..6f9ada0` (crash-recovery branch, post-Phase-8 plus pre-merge fix + M3/M4 test additions).

## Prerequisites

- Linux machine (scan requires `/proc/sys/kernel/random/boot_id`).
- `denubis-crash-recovery` plugin installed: `claude plugin install denubis-crash-recovery@brian-ed3d-plugins`.
- `denubis-plan-and-execute` >= 2.32.2 installed (wrapper patch required for liveness).
- Automated test suite passing: `uv run pytest -q` from worktree root (expect 800 tests, 0 failures, under 5s).
- `bats tests/test_claude_wrapper_liveness.bats` passing (13/13 — requires `bats` on PATH).
- `bats tests/test_crash_recovery_smoke.bats` passing.

---

## Phase 1: Schema and plugin manifest

| Step | Action | Expected |
|------|--------|----------|
| 1.1 | Run `crash-recovery init` against a fresh directory | Exit 0; `crash-recovery.db` created; `sqlite3 $DB ".tables"` shows `classification_history`, `scan_runs`, `sessions` |
| 1.2 | Run `crash-recovery init` a second time against the same DB | Exit 0; row counts still 0 in all three tables; `PRAGMA journal_mode` returns `wal` |
| 1.3 | Run `crash-recovery wibble` | Non-zero exit; `--help` appears in stdout or stderr |
| 1.4 | Run `crash-recovery --help` | Exit 0; all nine subcommands listed: `init scan render triage regenerate note history prune list-live` |
| 1.5 | Run `crash-recovery scan --help` (repeat for each of the nine subcommands) | Exit 0 for each; no error output |

---

## Phase 2: Classification rules sanity

| Step | Action | Expected |
|------|--------|----------|
| 2.1 | Start a fresh Claude session via the wrapper (`claudew`), let it complete normally (end_turn), then run `crash-recovery scan && crash-recovery triage` | Session appears in "Recently concluded" section of `~/llm-resume.md` with classification `concluded` and a non-empty reason string |
| 2.2 | Inspect the DB: `sqlite3 $DB "SELECT classification_reason FROM sessions ORDER BY last_scanned DESC LIMIT 1"` | Non-empty string matching one of the documented reasons (e.g., `no_liveness_clean_end_turn`) |

---

## Phase 3: Liveness file lifecycle

| Step | Action | Expected |
|------|--------|----------|
| 3.1 | Start a Claude session via `claudew --resume <some-uuid>` in a worktree | `~/.claude/run/<wrapper-pid>.live` exists with four keys: `cwd=`, `started=`, `argv=`, `boot_id=` |
| 3.2 | Inspect `argv=` in the liveness file | Contains `--resume <some-uuid>` verbatim |
| 3.3 | Inspect `boot_id=` in the liveness file | Matches `cat /proc/sys/kernel/random/boot_id` |
| 3.4 | Let the session exit cleanly (exit 0) | Liveness file at `~/.claude/run/<wrapper-pid>.live` no longer exists |
| 3.5 | Real-binary argv-passthrough sanity (M4 cross-check; also covered by `M4 — user-supplied argv reaches the real claude binary intact` in `tests/test_claude_wrapper_liveness.bats`) | Start a session with `claudew --print "hello world"`, capture the wrapper PID, verify the real claude binary received `--print "hello world"` plus `--disallowedTools ...`. This is a real-binary sanity check above what the bats stub validates. |

---

## Phase 4: Scan classification paths

| Step | Action | Expected |
|------|--------|----------|
| 4.1 | Start a wrapped session, do not exit (leave it running), then from another terminal run `crash-recovery scan && crash-recovery triage` | Session appears in "Currently unfinished" section with classification `live` |
| 4.2 | SIGKILL the wrapper PID (`kill -9 <wrapper-pid>`), then run `crash-recovery scan && crash-recovery triage` | Session moves to "Idle-live killed" with `hard_crash` classification and a `liveness_dead_pid_*` reason |
| 4.3 | Run `crash-recovery scan` twice without changing filesystem state | `sqlite3 $DB "SELECT COUNT(*) FROM scan_runs"` returns 2; session row count and classifications unchanged; `classification_history` count unchanged (M4 dedup) |

---

## Phase 5: Render idempotency and note workflow

| Step | Action | Expected |
|------|--------|----------|
| 5.1 | Run `crash-recovery regenerate` twice | `sha256sum ~/llm-resume.md` same both times |
| 5.2 | Hand-edit `~/llm-resume.md` (add a sentinel line), then run `crash-recovery regenerate` | Sentinel line absent; file starts with `# Claude Code session resume` |
| 5.3 | Run `crash-recovery note <uuid> "test annotation"` then `crash-recovery regenerate` | `~/llm-resume.md` contains "test annotation" under the matching UUID's section |
| 5.4 | Run `crash-recovery note <uuid> "replacement"` then `crash-recovery regenerate` | Only "replacement" appears; "test annotation" is gone |
| 5.5 | Run `crash-recovery note <uuid> --clear` then `crash-recovery regenerate` | No "Notes:" line under that UUID in `~/llm-resume.md` |
| 5.6 | Run `crash-recovery note no-such-uuid "text"` | Non-zero exit; "no session with uuid" in stderr; DB unchanged |

---

## Phase 6: Prune workflow

| Step | Action | Expected |
|------|--------|----------|
| 6.1 | Run `crash-recovery prune` (no flags) | Exit 1; `--confirm` mentioned in stderr; no rows deleted |
| 6.2 | Run `crash-recovery prune --dry-run` with at least one concluded session whose JSONL no longer exists | Exit 0; candidate UUID listed in stdout; DB unchanged |
| 6.3 | Annotate one of the candidates with `crash-recovery note <uuid> "keep"`, then run `crash-recovery prune --dry-run` again | Annotated UUID absent from the candidate list |
| 6.4 | Run `crash-recovery prune --confirm` | Exit 0; non-annotated, JSONL-absent, concluded rows deleted; annotated rows preserved; `classification_history` rows cascade-deleted for pruned sessions |

---

## Phase 7: End-to-end triage skill (real-session sanity)

This phase covers the full end-to-end path (wrapper crash → triage skill drives scan + render) against a real Claude session. The automated M3 test (`M3 — wrapper liveness format flows through scan → render to Idle-live killed` in `tests/test_claude_wrapper_liveness.bats`) pins the format chain using a synthetic crash; this phase is the real-binary sanity check above that.

| Step | Action | Expected |
|------|--------|----------|
| 7.1 | Start a Claude session via `claudew`, force a crash (kill -9 the wrapper), then invoke `/denubis-crash-recovery:triage` in a NEW Claude session | Skill calls `scan` internally; the crashed session appears in triage output under "Idle-live killed" |
| 7.2 | Follow the skill's triage prompts through annotation and the gated prune flow | At each step the skill surfaces the correct session list and applies the annotated note to the DB |
| 7.3 | After skill completes, inspect `~/llm-resume.md` | Contains the classified session under "Idle-live killed" with the annotation text if one was entered |

---

## Human verification required (from uat-requirements.md)

| Criterion | Why manual | Steps |
|-----------|------------|-------|
| Prune-gate prompt clarity (Phase 7) | Usability judgement — automated tests cannot determine if a human would understand the deletion is permanent | Follow uat-requirements.md Phase 7 entry: invoke `/denubis-crash-recovery:triage` against 5 prune candidates; walk prompts without consulting README; verify you can articulate that deletion is permanent, which rows are affected, and that annotated sessions are excluded |
| AC5.6 — Boot_id mismatch post-reboot | Real machine reboot required | Follow uat-requirements.md Phase 8 AC5.6 entry: start wrapped session, reboot machine, run `scan && triage`, confirm pre-reboot session UUID appears under "Idle-live killed" with reason `liveness_boot_id_mismatch`; verify in DB directly |
| AC6.4 — Idle SIGKILL detection | Real idle Claude session + live SIGKILL required | Follow uat-requirements.md Phase 8 AC6.4 entry: start wrapped session, have one exchange, wait 5+ min, SIGKILL wrapper, run `scan && triage`, confirm session appears under "Idle-live killed" with `liveness_dead_pid_*` reason rather than `concluded` |

---

## Traceability

| Acceptance Criterion | Automated test | Manual step |
|----------------------|----------------|-------------|
| AC1.1 | Marketplace listing bats proxy | 1.5 (plugin listed in `/plugin` after install) |
| AC1.2 | Marketplace listing bats proxy | 1.5 |
| AC1.3 | `test_plugin_manifest.py::test_versions_match` | — |
| AC1.4 | `test_plugin_manifest.py::test_json_load_rejects_malformed_manifest` | — |
| AC2.1 | `test_cli_help.py::test_help_lists_expected_subcommands` | 1.4 |
| AC2.2 | `test_cli_help.py` (parametrised) | 1.5 |
| AC2.3 | `test_init.py::test_init_creates_documented_schema` + CLI test | 1.1 |
| AC2.4 | `test_init.py::test_init_is_idempotent` | 1.2 |
| AC2.5 | `test_cli_help.py::test_unknown_subcommand_exits_nonzero` | 1.3 |
| AC3.1 | `test_classify.py::test_every_rule_classifies_its_fixture` | — |
| AC3.2 | `test_render.py::test_render_is_byte_identical_across_calls` + bats smoke | 5.1 |
| AC3.3 | `test_classify.py` (reason non-empty assertions) | — |
| AC3.4 | `test_classify.py::test_malformed_tail_maps_to_borderline_malformed_tail` | — |
| AC3.5 | `test_classify.py::test_empty_jsonl_maps_to_borderline_empty_file` | — |
| AC3.6 | `test_scan.py::test_scan_reclassifies_stale_classifier_version_rows` | — |
| AC4.1 | `test_note.py::test_note_set_then_regenerate_surfaces_text` | 5.3 |
| AC4.2 | `test_note.py::test_note_overwrites_existing` | 5.4 |
| AC4.3 | `test_note.py::test_note_clear_removes_note` | 5.5 |
| AC4.4 | `test_render.py::test_render_overwrites_user_edits` | 5.2 |
| AC4.5 | `test_note.py::test_note_unknown_uuid_raises...` | 5.6 |
| AC5.1 | `test_liveness.py` + bats AC5.1 | 3.1–3.3 |
| AC5.2 | `test_claude_wrapper_liveness.bats` AC5.2 tests | 3.4 |
| AC5.3 | `test_claude_wrapper_liveness.bats::AC5.3` | (reboot UAT) |
| AC5.4 | `test_liveness.py` + bats AC5.4 | — |
| AC5.5 | `test_claude_wrapper_liveness.bats` AC5.5 tests | 4.2 |
| AC5.6 (auto) | `test_scan.py::test_scan_classifies_boot_mismatch_as_hard_crash_even_if_pid_alive` | UAT Phase 8 AC5.6 |
| AC6.1 | `test_correlate.py` + `test_scan.py::test_scan_writes_expected_rows` | 4.1 |
| AC6.2 | `test_scan.py::test_scan_classifies_live_pid_as_live` | 4.1 |
| AC6.3 | `test_correlate.py::test_correlate_multiple_mtime_candidates_is_ambiguous` + `test_scan.py` | — |
| AC6.4 | — (UAT only) | UAT Phase 8 AC6.4 |
| AC7.1 | `test_render.py::test_regenerate_preserves_concluded_rows` | — |
| AC7.2 | `test_prune.py::test_prune_dry_run_is_read_only` | 6.2 |
| AC7.3 | `test_prune.py::test_prune_without_confirm_refuses` + bats smoke | 6.1 |
| AC7.4 | `test_prune.py::test_prune_confirm_deletes_matching_rows` | 6.4 |
| AC7.5 | `test_prune.py::test_prune_preserves_concluded_with_user_note` | 6.3–6.4 |
| AC7.6 | `test_prune.py::test_prune_preserves_concluded_with_extant_jsonl` | — |
| AC7.7 | `test_prune.py::test_prune_excludes_stale_classifier_version_rows` + confirm variant | — |
| AC8.1 | bats smoke `"README documents the sibling-plugin dependency (AC8.1)"` | — |
| AC8.2 | Inline Phase 8 Task 4 step 5 Python check | — |
| AC8.3 | Inline Phase 8 Task 4 step 6 grep check | — |
| Coherence M3 (writer→reader format chain) | `tests/test_claude_wrapper_liveness.bats::"M3 — wrapper liveness format flows through scan → render to Idle-live killed"` (added in `6f9ada0`) | 7.1–7.3 (real-binary sanity) |
| Coherence M4 (argv passthrough) | `tests/test_claude_wrapper_liveness.bats::"M4 — user-supplied argv reaches the real claude binary intact"` (added in `6f9ada0`) | 3.5 (real-binary sanity) |
| Prune-gate clarity (UAT) | Not automatable | UAT Phase 7 |
