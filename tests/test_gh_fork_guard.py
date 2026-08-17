"""Tests for denubis-hook-gh-fork-guard/hooks/gh-fork-guard.py."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Load the module from its file path (no package structure)
_HOOK_PATH = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-hook-gh-fork-guard"
    / "hooks"
    / "gh-fork-guard.py"
)
_PLUGIN_ROOT = _HOOK_PATH.parents[1]
_CODEX_MANIFEST_PATH = _PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
_CODEX_HOOKS_PATH = _PLUGIN_ROOT / "hooks" / "codex-hooks.json"
_CODEX_MARKETPLACE_PATH = _PLUGIN_ROOT.parents[1] / ".agents/plugins/marketplace.json"
_spec = importlib.util.spec_from_file_location("gh_fork_guard", _HOOK_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

extract_gh_commands = _mod.extract_gh_commands
check_repo_flag = _mod.check_repo_flag
check_api_path = _mod.check_api_path
check_explicit_repo_arg = _mod.check_explicit_repo_arg
repo_is_allowed = _mod.repo_is_allowed


# ---------------------------------------------------------------------------
# repo_is_allowed
# ---------------------------------------------------------------------------
class TestRepoIsAllowed:
    @pytest.fixture(autouse=True)
    def _set_allowed(self):
        original = _mod.ALLOWED_REPO
        _mod.ALLOWED_REPO = "denubis/denubis-plugins"
        yield
        _mod.ALLOWED_REPO = original

    def test_exact_match(self):
        assert repo_is_allowed("denubis/denubis-plugins")

    def test_case_insensitive(self):
        assert repo_is_allowed("Denubis/Denubis-Plugins")

    def test_strips_git_suffix(self):
        assert repo_is_allowed("denubis/denubis-plugins.git")

    def test_strips_https_prefix(self):
        assert repo_is_allowed("https://github.com/denubis/denubis-plugins")

    def test_strips_ssh_prefix(self):
        assert repo_is_allowed("git@github.com:denubis/denubis-plugins")

    def test_strips_quotes(self):
        assert repo_is_allowed("'denubis/denubis-plugins'")
        assert repo_is_allowed('"denubis/denubis-plugins"')

    def test_different_repo_denied(self):
        assert not repo_is_allowed("upstream/other-repo")

    def test_full_url_different_repo(self):
        assert not repo_is_allowed("https://github.com/upstream/other-repo.git")


# ---------------------------------------------------------------------------
# extract_gh_commands
# ---------------------------------------------------------------------------
class TestExtractGhCommands:
    def test_single_gh_command(self):
        assert extract_gh_commands("gh pr list") == ["gh pr list"]

    def test_no_gh_command(self):
        assert extract_gh_commands("git status") == []

    def test_compound_and(self):
        cmds = extract_gh_commands("gh pr list && gh issue view 1")
        assert len(cmds) == 2

    def test_compound_pipe(self):
        cmds = extract_gh_commands("gh pr list | grep foo")
        assert cmds == ["gh pr list"]

    def test_compound_semicolon(self):
        cmds = extract_gh_commands("gh pr list ; gh issue list")
        assert len(cmds) == 2

    def test_mixed_commands(self):
        cmds = extract_gh_commands("git status && gh pr view 1")
        assert cmds == ["gh pr view 1"]


# ---------------------------------------------------------------------------
# check_repo_flag
# ---------------------------------------------------------------------------
class TestCheckRepoFlag:
    @pytest.fixture(autouse=True)
    def _set_allowed(self):
        original = _mod.ALLOWED_REPO
        _mod.ALLOWED_REPO = "denubis/denubis-plugins"
        yield
        _mod.ALLOWED_REPO = original

    def test_repo_flag_with_equals(self):
        assert check_repo_flag("gh pr list --repo=upstream/other") == "upstream/other"

    def test_repo_flag_with_space(self):
        assert check_repo_flag("gh pr list --repo upstream/other") == "upstream/other"

    def test_short_flag(self):
        assert check_repo_flag("gh pr list -R upstream/other") == "upstream/other"

    def test_allowed_repo_passes(self):
        assert check_repo_flag("gh pr list --repo denubis/denubis-plugins") is None

    def test_no_flag(self):
        assert check_repo_flag("gh pr list") is None


# ---------------------------------------------------------------------------
# check_api_path
# ---------------------------------------------------------------------------
class TestCheckApiPath:
    @pytest.fixture(autouse=True)
    def _set_allowed(self):
        original = _mod.ALLOWED_REPO
        _mod.ALLOWED_REPO = "denubis/denubis-plugins"
        yield
        _mod.ALLOWED_REPO = original

    def test_api_path_different_repo(self):
        assert check_api_path("gh api repos/upstream/other/pulls") == "upstream/other"

    def test_api_path_allowed_repo(self):
        assert check_api_path("gh api repos/denubis/denubis-plugins/pulls") is None

    def test_api_path_quoted(self):
        assert (
            check_api_path('gh api "repos/upstream/other/issues"') == "upstream/other"
        )

    def test_no_api_path(self):
        assert check_api_path("gh pr list") is None


# ---------------------------------------------------------------------------
# check_explicit_repo_arg
# ---------------------------------------------------------------------------
class TestCheckExplicitRepoArg:
    @pytest.fixture(autouse=True)
    def _set_allowed(self):
        original = _mod.ALLOWED_REPO
        _mod.ALLOWED_REPO = "denubis/denubis-plugins"
        yield
        _mod.ALLOWED_REPO = original

    def test_repo_clone_different(self):
        assert (
            check_explicit_repo_arg("gh repo clone upstream/other") == "upstream/other"
        )

    def test_repo_clone_allowed(self):
        assert check_explicit_repo_arg("gh repo clone denubis/denubis-plugins") is None

    def test_repo_view(self):
        assert (
            check_explicit_repo_arg("gh repo view upstream/other") == "upstream/other"
        )

    def test_not_a_repo_subcommand(self):
        assert check_explicit_repo_arg("gh pr list") is None


# ---------------------------------------------------------------------------
# Integration: main() via subprocess
# ---------------------------------------------------------------------------
class TestMainIntegration:
    def _run(
        self,
        input_data: dict,
        *,
        provider: str = "claude",
    ) -> tuple[int, dict | None]:
        environment = os.environ.copy()
        environment.update(
            {
                "PATH": "/usr/bin:/bin",
                "ALLOWED_GH_REPO": "denubis/denubis-plugins",
                "DENUBIS_HOOK_PROVIDER": provider,
            }
        )
        result = subprocess.run(
            [sys.executable, str(_HOOK_PATH)],
            input=json.dumps(input_data).encode(),
            capture_output=True,
            timeout=10,
            env=environment,
        )
        stdout = result.stdout.decode().strip()
        parsed = json.loads(stdout) if stdout else None
        return result.returncode, parsed

    def test_non_bash_tool_passes(self):
        rc, output = self._run({"tool_name": "Read", "tool_input": {}})
        assert rc == 0
        assert output is None

    def test_non_gh_command_passes(self):
        rc, output = self._run(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git status"},
            }
        )
        assert rc == 0
        assert output is None

    def test_allowed_repo_not_denied(self):
        """Allowed repo should not be denied — may still get advisory context."""
        rc, output = self._run(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "gh pr list --repo denubis/denubis-plugins"},
            }
        )
        assert rc == 0
        if output is not None:
            # Should not be a deny, at most advisory
            assert output["hookSpecificOutput"].get("permissionDecision") != "deny"

    def test_different_repo_denied(self):
        rc, output = self._run(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "gh pr create --repo upstream/other"},
            }
        )
        assert rc == 0
        assert output is not None
        hook_output = output["hookSpecificOutput"]
        assert hook_output["permissionDecision"] == "deny"
        reason = hook_output["permissionDecisionReason"]
        assert isinstance(reason, str) and "upstream/other" in reason
        assert output["systemMessage"] == reason

    def test_api_path_denied(self):
        rc, output = self._run(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "gh api repos/upstream/other/pulls"},
            }
        )
        assert rc == 0
        assert output is not None
        hook_output = output["hookSpecificOutput"]
        assert hook_output["permissionDecision"] == "deny"
        reason = hook_output["permissionDecisionReason"]
        assert isinstance(reason, str) and "upstream/other" in reason
        assert output["systemMessage"] == reason

    def test_codex_deny_omits_unsupported_system_message(self):
        rc, output = self._run(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "gh pr create --repo upstream/other"},
            },
            provider="codex",
        )

        assert rc == 0
        assert output is not None
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "systemMessage" not in output

    def test_repo_subcommand_advisory(self):
        """gh pr list without --repo gets advisory context."""
        rc, output = self._run(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "gh pr list"},
            }
        )
        assert rc == 0
        assert output is not None
        assert "additionalContext" in output["hookSpecificOutput"]

    def test_bad_json_exits_cleanly(self):
        result = subprocess.run(
            [sys.executable, str(_HOOK_PATH)],
            input=b"not json",
            capture_output=True,
            timeout=10,
            env={
                "PATH": "/usr/bin:/bin",
                "ALLOWED_GH_REPO": "denubis/denubis-plugins",
            },
        )
        assert result.returncode == 0
        assert result.stdout.decode().strip() == ""


class TestOutputContract:
    """Every emitted hookSpecificOutput must carry hookEventName."""

    def test_deny_carries_hook_event_name(self):
        result = _mod.deny("nope")
        assert result["hookSpecificOutput"]["hookEventName"] == "PreToolUse"

    def test_advisory_context_carries_hook_event_name(self):
        payload = json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "gh issue list"}}
        ).encode()
        result = subprocess.run(
            [sys.executable, str(_HOOK_PATH)],
            input=payload,
            capture_output=True,
            timeout=10,
            env={
                "PATH": "/usr/bin:/bin",
                "ALLOWED_GH_REPO": "denubis/denubis-plugins",
            },
        )
        assert result.returncode == 0
        out = json.loads(result.stdout.decode())
        assert out["hookSpecificOutput"]["hookEventName"] == "PreToolUse"


def test_codex_plugin_routes_bash_to_shared_guard() -> None:
    manifest = json.loads(_CODEX_MANIFEST_PATH.read_text(encoding="utf-8"))
    hooks = json.loads(_CODEX_HOOKS_PATH.read_text(encoding="utf-8"))

    assert manifest["name"] == "denubis-hook-gh-fork-guard"
    assert _PLUGIN_ROOT / manifest["hooks"] == _CODEX_HOOKS_PATH
    command = hooks["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert hooks["hooks"]["PreToolUse"][0]["matcher"] == "Bash"
    assert command == (
        'DENUBIS_HOOK_PROVIDER=codex python3 "${PLUGIN_ROOT}/hooks/gh-fork-guard.py"'
    )


def test_codex_marketplace_exposes_gh_fork_guard() -> None:
    marketplace = json.loads(_CODEX_MARKETPLACE_PATH.read_text(encoding="utf-8"))
    entries = {entry["name"]: entry for entry in marketplace["plugins"]}

    assert entries["denubis-hook-gh-fork-guard"]["source"] == {
        "source": "local",
        "path": "./plugins/denubis-hook-gh-fork-guard",
    }
