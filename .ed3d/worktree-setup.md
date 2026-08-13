# Worktree setup

From the worktree root, install every member declared by
`pyproject.toml::tool.uv.workspace`:

```fish
uv sync --all-packages
```

Plain `uv sync` installs only the root project. Verify the shared environment and test
collection with:

```fish
uv run pytest -q
```
