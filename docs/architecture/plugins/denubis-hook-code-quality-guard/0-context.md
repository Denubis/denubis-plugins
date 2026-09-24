# denubis-hook-code-quality-guard — Context

## Boundary

This plugin owns two `PreToolUse` refusals whose violation is observable in the
proposed tool payload:

- JavaScript injection through `page.evaluate`, `ui.run_javascript`, script tags,
  or init scripts inside E2E, Playwright, or integration tests;
- `metadata.create_all` outside an Alembic version file.

It does not infer intent from TODOs, debug statements, skip markers, or similar
words. Shell writes, including heredocs, belong to the host destination policy and
approver. This hook does not inspect their content. Project-native tests, linters,
types, constraints, and review own contextual judgments.

```mermaid
flowchart LR
    Host[Agent host]
    Structured[Write, Edit, or apply_patch]
    Guard[code-quality-guard.py]
    Files[Project files]

    Host --> Structured --> Guard
    Guard -->|allow: no output| Files
    Guard -->|deny: model-facing reason| Host
```

## Contract

Claude Write/Edit uses `hooks/hooks.json`. This plugin registers no Bash adapter;
shell authoring is outside its boundary.
Codex `apply_patch` uses `hooks/codex-hooks.json`.

The implementation reads the proposed tool payload from stdin. Malformed input,
unrelated tools, and unmatched writes pass silently. A Claude denial exits 2 and
returns the same explanation in
`hookSpecificOutput.permissionDecisionReason` and top-level `systemMessage`.
Codex returns the model-facing structured denial with exit 0, as required by its
hook boundary.

The hook targets Python 3.9 independently of the repository application's Python
floor. `pyproject.toml` gives every `plugins/*/hooks/*.py` file that formatter
target, and the hook-portability test imports each hook under the floor
interpreter.

## Sources

- Claude Write/Edit registration: `plugins/denubis-hook-code-quality-guard/hooks/hooks.json`
- Codex registration: `plugins/denubis-hook-code-quality-guard/hooks/codex-hooks.json`
- Policy and output: `plugins/denubis-hook-code-quality-guard/hooks/code-quality-guard.py`
- Behavioral checks: `tests/test_code_quality_guard.py`
- Runtime-floor check: `tests/test_hook_portability.py`
