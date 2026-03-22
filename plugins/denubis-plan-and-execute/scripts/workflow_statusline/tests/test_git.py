"""Tests for git location and change detection module."""

from __future__ import annotations

import subprocess

import pytest

from workflow_statusline import git


@pytest.fixture
def git_repo(tmp_path):
    """Create a minimal git repo with one commit."""
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "test@test.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )
    # Create an initial commit so branch exists
    (tmp_path / "README.md").write_text("init")
    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "."], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", "init"],
        check=True,
        capture_output=True,
    )
    return tmp_path


class TestGitHelper:
    def test_git_runs_command(self, git_repo):
        result = git._git(str(git_repo), "rev-parse", "--git-dir")
        assert result == ".git"

    def test_git_raises_on_failure(self, tmp_path):
        with pytest.raises(subprocess.CalledProcessError):
            git._git(str(tmp_path), "rev-parse", "--git-dir")


class TestGitLocation:
    def test_non_git_dir_returns_basename(self, tmp_path):
        result = git.git_location(str(tmp_path))
        assert result == tmp_path.name

    def test_git_repo_on_main_returns_name_only(self, git_repo):
        # Default branch is usually "main" or "master"
        result = git.git_location(str(git_repo))
        # Should just be the directory name (no @branch for main/master)
        assert result == git_repo.name

    def test_git_repo_on_feature_branch_includes_branch(self, git_repo):
        subprocess.run(
            ["git", "-C", str(git_repo), "checkout", "-b", "feature-xyz"],
            check=True,
            capture_output=True,
        )
        result = git.git_location(str(git_repo))
        assert result == f"{git_repo.name}@feature-xyz"


class TestGitChanges:
    def test_no_changes_returns_zero(self, git_repo):
        staged, modified = git.git_changes(str(git_repo))
        assert staged == 0
        assert modified == 0

    def test_modified_file_detected(self, git_repo):
        (git_repo / "README.md").write_text("changed")
        staged, modified = git.git_changes(str(git_repo))
        assert staged == 0
        assert modified == 1

    def test_staged_file_detected(self, git_repo):
        (git_repo / "new_file.txt").write_text("new")
        subprocess.run(
            ["git", "-C", str(git_repo), "add", "new_file.txt"],
            check=True,
            capture_output=True,
        )
        staged, modified = git.git_changes(str(git_repo))
        assert staged == 1
        assert modified == 0

    def test_non_git_dir_returns_zero(self, tmp_path):
        staged, modified = git.git_changes(str(tmp_path))
        assert staged == 0
        assert modified == 0
