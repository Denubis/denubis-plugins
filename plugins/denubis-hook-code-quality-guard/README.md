# Code-quality guard

This `PreToolUse` guard blocks two concrete write patterns:

- JavaScript injection such as `page.evaluate()` in E2E, Playwright, or integration
  tests, where it bypasses the user interaction under test.
- `metadata.create_all()` outside Alembic version files, where it bypasses migration
  history.

Each denial carries the same explanation in Claude Code's model-facing
`permissionDecisionReason` and transcript-facing `systemMessage` channels. The hook does
not warn on TODOs, debugging statements, skipped tests, or other word patterns whose
meaning depends on project context.

Claude Write/Edit calls use the plugin hook manifest. Codex `apply_patch` calls use
its Codex hook manifest. No Bash hook is registered. Shell writes, including heredocs,
are judged by the host's destination
permissions and approver; this hook does not parse shell content or claim equivalent
code-quality coverage for that route.
