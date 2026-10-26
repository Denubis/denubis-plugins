# Supervision infrastructure — worklog

Companion to `todo.md`. One entry per dispatch or ruling, newest first.

## 2026-10-26

- Brian asked whether his global instruction (a ticket file under `docs/`) or ADRs 0005 and
  0008 govern; a first reading moved the ticket file into `docs/` (Sol, prompt 23). Brian then
  corrected the premise: an unanswered question is situational and belongs in notes, and the
  defect to fix is answered questions sitting in a ticket file. Recorded as ADR 0044; the move
  reversed (prompt 24); ADRs 0005, 0008 and 0010 restored from the last commit. He also asked
  for a survey of every decision register under his home directory for directions into the
  notes directory. Sonnet survey (read-only, 213 repositories, 356 register files): five
  repositories carry DIRECTION lines (this one, a stale clone of this repository, approver's
  register, Phaedra/Paper's local-mail ADRs, sage-srm-guide's ADR 046 and register), about
  forty CITATION lines across eleven more, fifteen registers live inside a notes directory,
  and the ticket file sits in the notes directory in 28 repositories and under `docs/` in two.
  Coverage limits: registers nested deeper than three levels or named other than `decisions`
  were not seen; classifications rest on trimmed line text. Repairs are per-repository work
  tracked in `docs/implementation-plans/2026-10-26-notes-register-repairs/todo.md`.
- Commits landed: hook migration (ADR 0038, seven plugins), ADR 0033, the landed 2026-10-09
  documents with every citation repair, the permission-queue flaky-test fix. The commit-skill
  release and ADRs 0034 to 0044 wait on Sol's tidy of the new records (prompt 22) and the
  ticket-file move (prompt 23). Found during staging: the checker never saw the new ADRs
  because register discovery uses `git ls-files`, and it selected staged `CHANGELOG.md` and
  `CLAUDE.md` outside the ruled scope; Sol narrowed `--staged` to `docs/`, notes and
  configured locations (prompt 21) and reworded four architecture-page rows (prompt 20).
- Brian ruled on the notes directory (ADR 0043: nothing durable other machines rely on; no citation
  exemption). Prompt 18 (Sol) verified: the messaging critical review moved into
  `docs/design-plans/2026-10-09-cross-provider-messaging/critical-review.md` with thirteen
  links rewritten; ADRs 0005, 0008, 0010 reworded to describe the queue's location without a
  path token; ADR 0015 bug-report path dropped; ADR 0028 cites the moved review. Default
  checker: one finding left, a false positive on a tracked file with a `:symbol` suffix, which
  Sol diagnosed (suffix not stripped, then a nonexistent `.notes`-relative candidate wrongly
  reported `IGNORED`).
- Prompt 19 (Sol, fresh session): fix that and three more checker defects (scheme-prefix
  hole, `exists()` on untracked directories, scope of the full rule per ADR 0042 decision 1
  so `ABSENT` is advisory outside registers, notes and architecture pages), and rewrite the
  five worktree-path citations in the frozen 2026-10-09 documents as prose, so the landed
  documents commit cleanly.
- Prompt 19 verified: full suite 2452 passed, 14 skipped; ruff, format, ty, complexipy clean
  on the checker and its tests; a probe document showed an exchange-prefixed token flagged EXCHANGE,
  a nonexistent path in the notes directory ABSENT, an untracked-directory prose token advisory, the
  `:symbol` suffix accepted, a worktree path WORKTREE. Default run exit 0; the seventeen
  landed documents exit 0 with 36 advisory ABSENT. Sol also rewrote five worktree-path and
  eight references to the notes directory in the frozen documents as prose on the supervisor's say-so.
  Brian then: "those references and frozen things should be justified by my words. Not just
  vibing on shit." Audit: the rules for the exchange and notes directories rest on his words (ADRs
  0041, 0042, 0043) for ADRs; extending the blocking rule to notes and architecture pages
  (ADR 0042 decision 1 wording), to staged design plans (prompt 15), and editing frozen
  design documents to satisfy it (prompts 17 and 19) are supervisor extensions with no
  ruling behind them. Raised to Brian as one question before any commit.
- Brian: "argh, ok we need to tidy up!" on the unfinished ADR 0034 move, and "please go
  manage that". Opus xhigh worker `pq-move-opus` dispatched to move permission-queue into the
  private repository without committing, repointing the symlink, or deleting from this repo;
  cutover is Brian's call. Peer session brian-ed3d-plugins-5c handed over its facts (flaky
  fix in the working tree travels with the code; two tickets migrate; ADRs 0033/0034 are its
  and fold into my commits) and agreed not to restart its worker.
- C1 of the design review decided by the supervisor on the conservative side: the direct,
  service-less driving path stays supported and the daemon is an optional layer. This
  preserves the spec's "no regression" line and ADR 0040's colleague requirement and
  contradicts no ruling. Brian may veto; design corrections to Sol follow prompt 19.

## 2026-10-25

- Prompt 17 (citation repairs) verified. Sol stopped twice on counts the prompt got wrong
  (sixteen source files for fifteen; twelve note links for eleven); both were supervisor
  miscounts, corrected, and Sol was told the filesystem governs over prompt counts. Landed
  `docs/design-plans/2026-10-09-cross-provider-messaging/` (fifteen fanout documents plus
  `BRIEF.md`): byte-identical to the originals apart from the provenance header and the
  exchange-link rewrites, checked with `diff`; no `codex-prompts` reference remains; the
  repository's gitleaks hook passes over the directory. ADR 0007, 0009 and 0011 edits
  match the prompt; the critical-review note has no exchange links left; Sol's temporary
  tickets are gone from the open-questions file. Default-mode checker: no ABSENT, EXCHANGE
  or WORKTREE finding; nine `.notes` IGNORED findings remain pending Brian's ruling.
  Consequence found during verification: the checker exits 1 for citation defects in any
  selected document, and the commit skill selects staged Markdown, so staging the landed
  historical documents fails the gate on their own 2026-10-09 citations (about 30 ABSENT
  and 5 WORKTREE, listed in Sol's notes). The prompt deliberately forbade editing those
  documents beyond the exchange links. Queued as a question for Brian in `todo.md`.
  claude-sync push found blocked by the dirty approver checkout; recorded in `todo.md`.
- Opus xhigh review of the stage-2 design returned NEEDS REVISION: 1 Critical, 12 Important,
  9 Minor. Supervisor verified the Critical and nine of the Important findings against the
  design text, `codex_supervisor.py` and the Claude Code hooks and cross-session-messaging
  pages (fetched 2026-10-25); the rest are labelled asserted. Staged with verification notes
  in the exchange directory on 2026-10-25. Halted on C1 (the design
  retires the direct Codex path at P2 while the service arrives at P3, and never without the
  private daemon), which conflicts with the spec's "no regression" and ADR 0040's colleague
  requirement; raised to Brian with a recommendation before any correction prompt.

## 2026-10-24

- Prompt 14 verified: 2406 tests pass, strict plugin validation passes, ruff and format
  clean on every hook; `tests/test_hook_portability.py` replaced by
  `tests/test_hook_uv_script_contract.py` (floor read from pyproject, registration form
  asserted, missing-uv path run in a real shell, teeth tests). Supervisor re-ran a
  migrated registration under `UV_PYTHON=3.9` (ran) and with uv off PATH (one line, exit
  1). Remaining limits: no macOS execution; Codex non-blocking exit code inferred from
  source, not observed. The vulnerability-watch ticket and its worktree disappeared from
  the open-questions file and the worktree directory at 15:39, before Sol's fresh session; Sol's
  notes record only its own H2 removal, so this is attributed to that other session.
- Prompt 16 (stage-2 design) dispatched on a fresh session.
- Prompt 14 (hook migration) in progress. Two supervisor rulings under ADR 0038: launchers
  carry `--python '>=3.14'` because an explicit `UV_PYTHON` overrides the PEP 723 floor
  (observed, uv 0.13.4; a `.python-version` does not); one fixed missing-`uv` preflight
  form per registration, exit 1. At 15:31 the Codex plugin cache
  (`~/.codex/plugins/cache/denubis-plugins/`) was refreshed from the working tree, so the
  uncommitted bumped versions were installed and the old version directories removed;
  Sol's running session still pointed its hooks there and was blocked. Forced a fresh
  session; files intact on disk. Codex `config.toml` pins `trusted_hash` per hook entry,
  so the changed `codex-hooks.json` files may need Brian to re-trust them.
- Prompt 15 (corrections to the checker) verified: default selection narrowed to staged
  or named documents plus whole decision registers plus the open-questions file, `--all`
  for the full audit; notes selected from the filesystem because the notes directory is ignored by
  the global gitignore; extraction no longer flags slash commands, prose pairs, node ids
  or paths outside the repository. Default run on this repo: two stale ADR paths (0007
  `thread-writer-locks/`, 0009 `tests/test_codex_supervisor_reminders.py`), the ADR 0011
  exchange citation, one worktree citation in the vuln-watch ticket, ten `.notes`
  citations pending Brian's exemption ruling. Full suite 2375 passed; one
  permission-queue daemon UI test failed in the full run and passed twice alone, files
  untouched by this work. Script digest `6400b3a8…` awaiting Brian's pin.
- Prompt 13 dispatched to Sol (fresh session `01a16bb3-…`, pane `%237`): commit-skill
  durable-record checks, ADR 0042. Two scope questions answered by the supervisor under
  the existing repository contract: both provider manifests move to 1.5.0; the bare
  `plugins/denubis-git-commit/plugin.json` is the Antigravity packaging manifest, read by
  `tests/test_antigravity_plugins.py` and `install_antigravity_plugins.sh`, and is left
  alone.
- Prompt 14 drafted (hook launcher migration, ADR 0038), queued behind 13.
- Rulings recorded: ADRs 0038 (hooks via `uv run --script` at 3.14), 0039 (per-instance
  supervision, own window, plural panes, no persisted bindings, no re-arming monitors, one
  Postgres-backed service), 0040 (library here as an installable package, daemon in the
  private repository, dependency one way), 0041 (exchange is the Record, telemetry from
  hooks, AskUserQuestion denied, question lifecycle), 0042 (citation and memory checks in
  the commit skill). Design decision D3 withdrawn; D1, D2, D4, D5 resolved.
- Astra's specification landed at `docs/design-plans/2026-10-24-claude-supervision-spec.md`;
  ADRs 0035 to 0039 repointed to it. Transitional wording removed from the day's ADRs and
  from the CLAUDE.md hook rule.
- Stage-1 design (Sol, prompts 11 and 12) verified; superseded in part by the rulings
  above and awaiting revision (todo item 3).
