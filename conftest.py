# workflow_statusline is a nested project with its own pyproject.toml and deps.
# Run its tests from its own directory:
#   cd plugins/denubis-plan-and-execute/scripts/workflow_statusline && uv run pytest
collect_ignore_glob = ["plugins/*/scripts/*"]
