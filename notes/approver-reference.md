# Approver reference

Snapshot of `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/reference_approver-script.md` as of 2026-05-22, included here so this worktree is self-contained for anyone picking up the approver/rtk work later. Memory file is authoritative — if it diverges, trust the memory.

---

## Approver script

A personal PreToolUse hook that intercepts Bash tool calls, classifies them via per-tool rules, and either returns `permissionDecision: "allow"` (silently approves), `"ask"` (forces a prompt with annotated reason), `"deny"` (blocks with reason surfaced as tool error), or no opinion (normal flow continues).

### Layout

```
~/.claude/hooks/approver/
  approver.py          # entry: PreToolUse + PostToolUse, pure stdlib hot path
  pipeline.py          # quote-aware pipeline split + per-component classification
                       # exports TRIVIALLY_SAFE (ls/cat/head/tail/grep/rg/...)
  session.py           # per-session approval cache, signature(), DANGEROUS_LEADINGS
  rules/sed.py         # sed_readonly classifier
  rules/awk.py         # awk_safe classifier
  tests/               # pytest tests, one file per module (107 tests, all passing)
  corpus/
    build_corpus.py    # extracts Bash calls + observed outcomes from ~/.claude/projects/*.jsonl
    corpus.jsonl       # the corpus itself (rebuild via build_corpus.py --days N)
    classify_corpus.py # runs the approver against the corpus, writes REPORT.md
    REPORT.md          # latest confusion + top rule opportunities

~/.claude/approver/    # state (separate from code)
  projects/<slug>/
    log/YYYY-MM-DD.jsonl   # rolling 14-day log per project
    session-<id>.json      # per-session approval signature cache (cap 200)
```

### QA workflow

The corpus is the "big list of naughty strings" equivalent — every Bash tool call
from the last N days of sessions, labelled with observed outcome (ran/denied/errored).
When you add a rule, rerun `classify_corpus.py` to measure the delta:

```
rtk proxy uv run --with pytest python3 ~/.claude/hooks/approver/corpus/build_corpus.py --days 30
rtk proxy uv run --with pytest python3 ~/.claude/hooks/approver/corpus/classify_corpus.py
# then look at corpus/REPORT.md for headline numbers + top rule opportunities
```

Coverage progression so far:
- 21.2% (initial: sed_readonly + awk_safe + TRIVIALLY_SAFE)
- 28.9% (after fixing `2>&1` mis-split and treating `/dev/null` as harmless)
- 40.0% (after adding `cd`, `rtk`, `cc-search-chats`, `claude-research-transcript` to TRIVIALLY_SAFE)
- 65.4% (after `git_readonly`, `uv_policy`, `find_safe`, `gh_readonly` rules; 302 tests passing)

FALSE_ALLOW count: 1 (the TRAP_DENY harness probe; settings.deny intercepted, so harmless in practice).

### Classifier signature

Rules can be `bool` (returns `(ok: bool, reason: str)` — True maps to `"allow"`,
False to no-opinion) or `tri` (returns `(decision: str|None, reason: str)`
where decision is `"allow"`, `"ask"`, `"deny"`, or `None`). The registry entry
is `(rule_name, "module:func", mode)`. Pipeline aggregation: any `deny` → deny;
any `None` → no-opinion; any `ask` → ask; else allow. Deny rules override the
session cache (the cache cannot resurrect a deny).

`<slug>` is `sha1(project_root)[:12]`. Project root detection: walk up from `cwd` looking for `.git/`, fall back to `cwd`, final fallback `$CLAUDE_PROJECT_DIR`.

### Hook registration

Global in `~/.claude/settings.json`:

- `hooks.PreToolUse` matcher `Bash`: `python3 ~/.claude/hooks/approver/approver.py`
- `hooks.PostToolUse` matcher `Bash`: same command. PostToolUse caches signatures of commands the user manually approved via Claude Code's prompt UI; subsequent PreToolUse with the same signature auto-allows via `session_cascade`.

### CLI

- `python3 ~/.claude/hooks/approver/approver.py --list-rules` — print rules + first docstring line
- `python3 ~/.claude/hooks/approver/approver.py --version`
- `python3 ~/.claude/hooks/approver/approver.py --probe` — read stdin and echo to stderr (debug)

### Adding a new rule

1. Write `rules/<tool>.py` with a classifier function returning `(ok: bool, reason: str)`.
2. Write `tests/test_<tool>.py` with safe + unsafe parametrised cases.
3. Wire into `approver.py:_dispatch_bash` by leading-token name.
4. Run `python3 -m pytest ~/.claude/hooks/approver/tests/`.
5. Live-test by triggering a real call; check `additionalContext` propagates and the log entry shows the rule firing.

### Decision flow (PreToolUse, tool == Bash)

1. Compute `bash_signature(command)` — pipeline-shape signature (e.g. `"ls|awk|head"`). Returns `None` if any component is in `DANGEROUS_LEADINGS` (rm/mv/sudo/bash/xargs/ssh/…).
2. If signature is present AND already in this session's cache → emit `session_cascade` allow.
3. Else run `classify_pipeline(command)` — every component must clear via `TRIVIALLY_SAFE` or a registered rule (`sed_readonly`, `awk_safe`). If yes → emit `pipeline_safe` allow AND cache the signature.
4. Else emit nothing → normal Claude Code permission flow.

PostToolUse (tool == Bash, response not denied): cache the signature with source `post_approval`. This is the "approval cascade" mechanism — user approves once via the prompt UI, subsequent calls with the same pipeline shape auto-allow.

### Known gaps (as of 2026-05-21)

- **No cut-and-try / three-strikes detection yet.** The log captures the data; no rule consumes it. Step 4 on the build list.
- **No tool-alias awareness.** `ruff` and `python -m ruff` and `uv run ruff` produce different signatures, so cache hits don't generalise. Step 4.
- **No `find_safe` / `xargs_safe` / `unzip_listonly` rules.** These commonly appear in safe shapes but require flag-checking; they slip through to default-prompt unless cached after manual approval.
- **No bulk audit yet.** Step 5 — use cc-search-chats to extract Bash calls from recent sessions and decide which need new rules.
- **Cold-start ~30–80ms per Bash call.** Acceptable for now; daemon if it bites.
- **claude-sync coverage gap.** `~/.claude/hooks/approver/` is not on the sync list — single-machine until either extended or copied manually.

### Resuming work

There's a self-contained resume prompt at `~/.claude/hooks/approver/RESUME.md`.
Read it before continuing — it lists current coverage, deferred items, and the
"first action" to run when picking this back up.
