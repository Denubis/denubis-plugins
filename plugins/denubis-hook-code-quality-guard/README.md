# Code-quality guard

This `PreToolUse` guard blocks three concrete write patterns:

- JavaScript injection such as `page.evaluate()` in E2E, Playwright, or integration
  tests, where it bypasses the user interaction under test.
- `metadata.create_all()` outside Alembic version files, where it bypasses migration
  history.
- Claude Bash heredocs used through `cat`, `tee`, or their output redirection to
  author files instead of the structured Write/Edit tools. A `tee` invocation
  without a file operand, `/dev/null`, ordinary file reads, and genuine command
  output capture remain allowed.

Each denial carries the same explanation in Claude Code's model-facing
`permissionDecisionReason` and transcript-facing `systemMessage` channels. The hook does
not warn on TODOs, debugging statements, skipped tests, or other word patterns whose
meaning depends on project context.

Claude Write/Edit calls use the plugin hook manifest. Bash calls reach the same
implementation through the executable `hooks/pretooluse-bash.sh` convention and
the shared PreToolUse:Bash dispatcher. Codex `apply_patch` calls use the Codex
hook manifest; `apply_patch` is already Codex's structured file-edit boundary.
