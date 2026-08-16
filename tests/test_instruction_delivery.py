"""Repository contracts for always-on instruction delivery.

The inventory comes from the marketplace and each listed plugin's ``hooks.json``.
The PreToolUse assertion is a positive control: a clean result is meaningful only if
the same traversal finds a known active hook boundary.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
PROJECT_NOTES_ROOT = REPO_ROOT / "plugins" / "denubis-project-notes"
PLAN_HOOKS = (
    REPO_ROOT
    / "plugins"
    / "denubis-plan-and-execute"
    / "hooks"
    / "claude-hooks.json"
)


def _claude_hooks_path(plugin_root: Path) -> Path:
    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return plugin_root / manifest.get("hooks", "hooks/hooks.json")


def _marketplace_hook_events() -> set[tuple[str, str]]:
    marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    events: set[tuple[str, str]] = set()

    for plugin in marketplace["plugins"]:
        source = plugin["source"]
        plugin_root = REPO_ROOT / source.removeprefix("./")
        hooks_path = _claude_hooks_path(plugin_root)
        if not hooks_path.is_file():
            continue
        hooks = json.loads(hooks_path.read_text(encoding="utf-8"))["hooks"]
        events.update((plugin["name"], event) for event in hooks)

    return events


def test_hook_inventory_reaches_a_known_mechanical_boundary() -> None:
    """Positive control: marketplace traversal reaches the Bash dispatcher."""
    assert (
        "denubis-hook-pretooluse-dispatcher",
        "PreToolUse",
    ) in _marketplace_hook_events()


def test_no_marketplace_plugin_runs_on_every_user_prompt() -> None:
    """UserPromptSubmit is not an action boundary for this marketplace."""
    offenders = sorted(
        plugin
        for plugin, event in _marketplace_hook_events()
        if event == "UserPromptSubmit"
    )

    assert not offenders, (
        "generic per-prompt delivery has no reliable action boundary; "
        f"retire or relocate these hooks: {offenders}"
    )


def test_no_marketplace_plugin_reminds_after_git_review() -> None:
    """A read-only git command is not the commit-preparation boundary."""
    assert (
        "denubis-hook-claudemd-reminder",
        "PostToolUse",
    ) not in _marketplace_hook_events()


def test_notes_retrieval_does_not_run_at_session_start() -> None:
    """Project-memory retrieval starts from a task, not an empty session."""
    assert (
        "denubis-notes-advisory",
        "SessionStart",
    ) not in _marketplace_hook_events()


def test_project_notes_retrieval_is_direct_main_agent_work() -> None:
    """The plugin exposes one skill without hook or agent machinery."""

    assert not (PROJECT_NOTES_ROOT / "hooks").exists()
    assert not (PROJECT_NOTES_ROOT / "agents").exists()
    assert (PROJECT_NOTES_ROOT / ".claude-plugin" / "plugin.json").is_file()
    assert (
        PROJECT_NOTES_ROOT / "skills" / "scanning-project-notes" / "SKILL.md"
    ).is_file()


def test_session_start_keeps_side_effects_without_generic_workflow_context() -> None:
    events = _marketplace_hook_events()
    plan_hooks = json.loads(PLAN_HOOKS.read_text(encoding="utf-8"))["hooks"]
    session_commands = [
        hook["command"]
        for registration in plan_hooks["SessionStart"]
        for hook in registration["hooks"]
    ]

    assert ("denubis-basic-agents", "SessionStart") not in events
    assert session_commands == [
        'python3 "${CLAUDE_PLUGIN_ROOT}/hooks/update-live-marker.py"'
    ]
