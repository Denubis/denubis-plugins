"""Optional agents must not revive workflow certificates or hidden mutation."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "plugins" / "denubis-plan-and-execute" / "agents"


def _agent(name: str) -> str:
    return " ".join((AGENTS / f"{name}.md").read_text(encoding="utf-8").split())


def test_no_agent_commits_or_destructively_reverts() -> None:
    for path in AGENTS.glob("*.md"):
        text = " ".join(path.read_text(encoding="utf-8").split())
        assert "git commit" not in text, path.name
        assert "git checkout -- ." not in text, path.name
        assert "git reset --hard" not in text, path.name


def test_implementors_preserve_scope_and_return_observed_evidence() -> None:
    for name in {"task-implementor", "task-bug-fixer", "refactoring-executor"}:
        text = _agent(name)
        assert "Preserve pre-existing changes" in text
        assert "Do not commit, push, publish, or deploy" in text
        assert "exact verification commands and results" in text
    assert "Verify the review finding against the cited source" in _agent("task-bug-fixer")
    assert "Do not refactor code without behavioral coverage" in _agent("refactoring-executor")


def test_review_agents_return_leads_without_files_or_status_tokens() -> None:
    for name in {"code-reviewer", "coherence-reviewer", "critical-peer-review", "dba-reviewer"}:
        text = _agent(name)
        for scar in {
            "APPROVED",
            "CHANGES REQUIRED",
            "review-wip.md",
            "findings file",
            "checkpoint file",
        }:
            assert scar not in text, name
        assert "read-only" in text.lower(), name
        assert "lead" in text.lower(), name
        assert "exact source" in text.lower(), name


def test_specialist_agents_keep_their_single_evidence_boundary() -> None:
    assert "named uncertainty" in _agent("proleptic-challenger")
    assert "Discard unsupported objections" in _agent("proleptic-challenger")
    assert "Do not ask the human" in _agent("proleptic-challenger")

    assert "Do not write a report file unless" in _agent("smell-assessor")
    assert "No numerical threshold proves" in _agent("smell-assessor")

    analyst = _agent("test-analyst")
    assert "Map each acceptance criterion" in analyst
    assert "Do not turn an automated check into a human step" in analyst
    assert "Do not write or overwrite plan files" in analyst
