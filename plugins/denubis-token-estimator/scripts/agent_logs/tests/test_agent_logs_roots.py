"""Log roots follow CLAUDE_CONFIG_DIR and CODEX_HOME, and an explicit path wins."""

from __future__ import annotations

from denubis_agent_logs.roots import claude_projects_root, codex_sessions_root


def test_claude_root_is_the_projects_directory_under_claude_config_dir(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "alt-config"))

    assert claude_projects_root() == tmp_path / "alt-config" / "projects"


def test_claude_root_falls_back_to_home_when_config_dir_is_unset_or_empty(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)

    assert claude_projects_root() == tmp_path / ".claude" / "projects"

    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "")

    assert claude_projects_root() == tmp_path / ".claude" / "projects"


def test_claude_config_dir_beginning_with_a_tilde_resolves_under_home(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "~/.claude-ponytail")

    assert claude_projects_root() == tmp_path / ".claude-ponytail" / "projects"


def test_codex_root_is_the_sessions_directory_under_codex_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "alt-codex"))

    assert codex_sessions_root() == tmp_path / "alt-codex" / "sessions"


def test_codex_root_falls_back_to_home_when_codex_home_is_unset_or_empty(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CODEX_HOME", raising=False)

    assert codex_sessions_root() == tmp_path / ".codex" / "sessions"

    monkeypatch.setenv("CODEX_HOME", "")

    assert codex_sessions_root() == tmp_path / ".codex" / "sessions"


def test_an_explicit_root_wins_over_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "alt-config"))
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "alt-codex"))

    assert claude_projects_root(tmp_path / "chosen") == tmp_path / "chosen"
    assert codex_sessions_root(str(tmp_path / "chosen")) == tmp_path / "chosen"
