"""Behavioral contract for the always-on instruction budget alarm."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = (
    REPO_ROOT
    / "plugins"
    / "denubis-hook-instruction-budget"
    / "hooks"
    / "instruction-budget.py"
)
PLUGIN_ROOT = HOOK_PATH.parents[1]


@pytest.fixture
def hook_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("instruction_budget", HOOK_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_lines(path: Path, count: int, *, width: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(("x" * width + "\n") * count, encoding="utf-8")


def test_claude_measures_global_and_project_as_one_budget(
    hook_module: ModuleType,
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    project = tmp_path / "project"
    _write_lines(home / ".claude" / "CLAUDE.md", 100)
    _write_lines(project / "CLAUDE.md", 101)

    report = hook_module.inspect_instruction_budget(
        provider="claude",
        cwd=project,
        home=home,
        project_root=project,
    )

    assert report.total_lines == 201
    assert report.total_bytes == 402
    assert [source.path for source in report.sources] == [
        home / ".claude" / "CLAUDE.md",
        project / "CLAUDE.md",
    ]
    assert report.over_line_limit is True
    assert report.over_byte_limit is False
    assert report.within_limits is False


def test_byte_limit_is_independent_of_line_limit(
    hook_module: ModuleType,
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    project = tmp_path / "project"
    source = home / ".claude" / "CLAUDE.md"
    source.parent.mkdir(parents=True)
    source.write_text("x" * 32_769, encoding="utf-8")

    report = hook_module.inspect_instruction_budget(
        provider="claude",
        cwd=project,
        home=home,
        project_root=project,
    )

    assert report.total_lines == 1
    assert report.total_bytes == 32_769
    assert report.over_line_limit is False
    assert report.over_byte_limit is True
    assert report.within_limits is False


def test_claude_counts_unscoped_rules_but_not_path_scoped_rules(
    hook_module: ModuleType,
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    project = tmp_path / "project"
    _write_lines(home / ".claude" / "CLAUDE.md", 190)
    _write_lines(home / ".claude" / "rules" / "always.md", 11)
    scoped_rule = project / ".claude" / "rules" / "python.md"
    scoped_rule.parent.mkdir(parents=True)
    scoped_rule.write_text(
        "---\npaths:\n  - '**/*.py'\n---\n" + ("ignored\n" * 100),
        encoding="utf-8",
    )

    report = hook_module.inspect_instruction_budget(
        provider="claude",
        cwd=project,
        home=home,
        project_root=project,
    )

    assert report.total_lines == 201
    assert [source.path.name for source in report.sources] == [
        "CLAUDE.md",
        "always.md",
    ]
    assert report.over_line_limit is True


def test_claude_counts_recursive_import_content(
    hook_module: ModuleType,
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    project = tmp_path / "project"
    global_instructions = home / ".claude" / "CLAUDE.md"
    global_instructions.parent.mkdir(parents=True)
    global_instructions.write_text("@shared.md\n", encoding="utf-8")
    _write_lines(global_instructions.with_name("shared.md"), 200)

    report = hook_module.inspect_instruction_budget(
        provider="claude",
        cwd=project,
        home=home,
        project_root=project,
    )

    assert report.total_lines == 201
    assert [source.path.name for source in report.sources] == [
        "CLAUDE.md",
        "shared.md",
    ]
    assert report.over_line_limit is True


def test_codex_global_load_does_not_consume_project_truncation_budget(
    hook_module: ModuleType,
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    project = tmp_path / "project"
    global_source = home / ".codex" / "AGENTS.md"
    project_source = project / "AGENTS.md"
    global_source.parent.mkdir(parents=True)
    project.mkdir()
    global_source.write_text("g" * 16_904, encoding="utf-8")
    project_source.write_text("p" * 26_302, encoding="utf-8")

    report = hook_module.inspect_instruction_budget(
        provider="codex",
        cwd=project,
        home=home,
        project_root=project,
    )

    assert report.total_bytes == 43_206
    assert report.project_bytes == 26_302
    assert report.over_byte_limit is True
    assert report.project_truncated is False


def test_codex_honors_configured_fallback_and_project_limit(
    hook_module: ModuleType,
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    config_root = home / ".codex"
    project = tmp_path / "project"
    config_root.mkdir(parents=True)
    config_root.joinpath("config.toml").write_text(
        'project_doc_max_bytes = 40000\n'
        'project_doc_fallback_filenames = ["CLAUDE.md"]\n',
        encoding="utf-8",
    )
    _write_lines(project / "CLAUDE.md", 20)

    report = hook_module.inspect_instruction_budget(
        provider="codex",
        cwd=project,
        home=home,
        project_root=project,
        config_root=config_root,
    )

    assert report.project_limit == 40_000
    assert [source.path for source in report.sources] == [project / "CLAUDE.md"]


def test_codex_reports_actual_project_chain_truncation_separately(
    hook_module: ModuleType,
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    project = tmp_path / "project"
    package = project / "package"
    _write_lines(project / "AGENTS.md", 100, width=199)
    _write_lines(package / "AGENTS.md", 100, width=129)

    report = hook_module.inspect_instruction_budget(
        provider="codex",
        cwd=package,
        home=home,
        project_root=project,
    )

    assert report.project_bytes == 33_000
    assert report.project_limit == 32_768
    assert report.project_truncated is True


def test_codex_truncation_warns_even_when_combined_policy_is_within_limits(
    hook_module: ModuleType,
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    project = tmp_path / "project"
    _write_lines(project / "AGENTS.md", 51)

    report = hook_module.inspect_instruction_budget(
        provider="codex",
        cwd=project,
        home=home,
        project_root=project,
        project_limit=100,
    )
    output = hook_module.warning_output(report)

    assert report.within_limits is True
    assert report.project_truncated is True
    assert output is not None
    assert set(output) == {"systemMessage"}
    assert "configured 100-byte loader limit" in output["systemMessage"]


def test_over_budget_hook_emits_user_warning_without_model_context(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    project = tmp_path / "project"
    _write_lines(home / ".claude" / "CLAUDE.md", 201)
    project.mkdir()
    environment = os.environ.copy()
    environment["HOME"] = str(home)

    result = subprocess.run(
        [sys.executable, str(HOOK_PATH), "--provider", "claude"],
        input=json.dumps({"hook_event_name": "SessionStart", "cwd": str(project)}),
        cwd=project,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert set(output) == {"systemMessage"}
    assert "201 lines" in output["systemMessage"]
    assert "200 lines" in output["systemMessage"]
    assert "32,768 bytes" in output["systemMessage"]


def test_within_budget_report_is_positive_and_hook_stays_silent(
    hook_module: ModuleType,
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    project = tmp_path / "project"
    _write_lines(home / ".codex" / "AGENTS.md", 20)
    _write_lines(project / "AGENTS.md", 30)

    report = hook_module.inspect_instruction_budget(
        provider="codex",
        cwd=project,
        home=home,
        project_root=project,
    )

    assert report.total_lines == 50
    assert report.total_bytes == 100
    assert report.within_limits is True
    assert hook_module.warning_output(report) is None


@pytest.mark.parametrize(
    ("provider", "manifest_directory", "root_variable"),
    [
        ("claude", ".claude-plugin", "CLAUDE_PLUGIN_ROOT"),
        ("codex", ".codex-plugin", "PLUGIN_ROOT"),
    ],
)
def test_provider_manifests_run_the_shared_alarm_only_at_startup(
    provider: str,
    manifest_directory: str,
    root_variable: str,
) -> None:
    manifest = json.loads(
        (PLUGIN_ROOT / manifest_directory / "plugin.json").read_text(encoding="utf-8")
    )
    hooks_path = PLUGIN_ROOT / manifest["hooks"]
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))["hooks"]

    assert set(hooks) == {"SessionStart"}
    assert len(hooks["SessionStart"]) == 1
    registration = hooks["SessionStart"][0]
    assert registration["matcher"] == "startup"
    assert len(registration["hooks"]) == 1
    command = registration["hooks"][0]["command"]
    assert command == (
        f'python3 "${{{root_variable}}}/hooks/instruction-budget.py" '
        f"--provider {provider}"
    )
