"""Git lifecycle skills perform the requested action without hidden side effects."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "denubis-plan-and-execute" / "skills"


def _skill(name: str) -> str:
    return " ".join((SKILLS / name / "SKILL.md").read_text(encoding="utf-8").split())


def test_branch_finishing_routes_without_review_or_destructive_menu() -> None:
    text = _skill("finishing-a-development-branch")

    for scar in {
        "Announce at start",
        "Full-Branch Code Review",
        "Present exactly these 4 options",
        "Discard this work",
        "Worktree Cleanup",
        "Common Mistakes",
        "Red Flags",
    }:
        assert scar not in text
    assert "Inspect branch status and verification evidence" in text
    assert "ask one pointed question" in text
    assert "denubis-plan-and-execute:make-pr" in text
    assert "denubis-plan-and-execute:merge-to-main" in text
    assert "Do not delete a branch or worktree" in text


def test_make_pr_limits_remote_authority_to_push_and_pr() -> None:
    text = _skill("make-pr")

    for scar in {
        "Announce at start",
        "git rebase",
        "git stash",
        "gh issue edit",
        "fallback to pytest",
        "Common Mistakes",
        "Red Flags",
    }:
        assert scar not in text
    assert "Invoking this skill authorises pushing the current feature branch and creating one pull request" in text
    assert "Require a clean working tree" in text
    assert "If the branch is behind or diverged" in text
    assert "Run every discovered required gate" in text
    assert "Do not mutate issue labels" in text


def test_merge_limits_authority_to_verified_local_integration() -> None:
    text = _skill("merge-to-main")

    for scar in {
        "Announce at start",
        "git rebase",
        "gh issue edit",
        "Delete feature branch",
        "Worktree cleanup",
        "Common Mistakes",
        "Red Flags",
    }:
        assert scar not in text
    assert "Invoking this skill authorises one local merge" in text
    assert "Require clean working trees" in text
    assert "Run the required gates before the merge" in text
    assert "Run them again after the merge" in text
    assert "Do not delete the feature branch or worktree" in text


def test_worktree_creation_has_no_hidden_metadata_or_setup_mutation() -> None:
    text = _skill("using-git-worktrees")

    for scar in {
        "Announce at start",
        "gh issue view",
        "Ensure `.worktreeinclude` Exists",
        "Common Mistakes",
        "Red Flags",
    }:
        assert scar not in text
    assert "Derive the branch and directory name directly" in text
    assert "verify that the parent directory is ignored" in text
    assert "Use the configured package-manager caches exactly as provided" in text
    assert "Report the exact worktree path" in text
    assert "Do not remove an existing worktree" in text


def test_dependency_upgrade_does_not_grant_commit_authority() -> None:
    text = _skill("controlled-dependency-upgrade")

    for scar in {"git commit", "TaskCreate", "Red Flags"}:
        assert scar not in text
    assert "Upgrade one direct dependency at a time" in text
    assert "Use the configured package-manager cache" in text
    assert "Observe the baseline gates before changing the lock state" in text
    assert "Do not commit, push, or publish" in text
