"""Regression checks for the authenticated Context7 invocation path."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS = REPO_ROOT / ".ed3d" / "tools.md"


def _tool_registry(path: Path) -> dict[str, dict[str, str]]:
    registry: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current = registry.setdefault(line.removeprefix("## "), {})
        elif current is not None and line.startswith("- "):
            key, value = line.removeprefix("- ").split(":", 1)
            current[key] = value.strip()
    return registry


def test_project_tool_registry_uses_authenticated_context7_mcp() -> None:
    context7 = _tool_registry(TOOLS)["Context7"]
    assert context7["Invocation"] == (
        "`mcp__context7__resolve_library_id`, then `mcp__context7__query_docs`"
    )
    assert context7["Prohibited"] == "`npx ctx7`"
