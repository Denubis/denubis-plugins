"""Executable contract for the project-notes frontmatter inventory."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY = (
    REPO_ROOT
    / "plugins"
    / "denubis-project-notes"
    / "skills"
    / "scanning-project-notes"
    / "scripts"
    / "inventory.py"
)


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _inventory(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(INVENTORY), "--cwd", str(cwd)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_inventory_reads_every_frontmatter_from_shared_worktree_notes(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    worktree = tmp_path / "task-worktree"
    repository.mkdir()
    _run(["git", "init", "-b", "main"], cwd=repository)
    _run(["git", "config", "user.name", "Inventory Test"], cwd=repository)
    _run(
        ["git", "config", "user.email", "inventory@example.invalid"],
        cwd=repository,
    )
    (repository / ".gitignore").write_text(".notes/\n", encoding="utf-8")
    (repository / "tracked.txt").write_text("fixture\n", encoding="utf-8")
    _run(["git", "add", "."], cwd=repository)
    _run(["git", "commit", "-m", "fixture"], cwd=repository)

    notes = repository / ".notes"
    nested = notes / "nested"
    nested.mkdir(parents=True)
    (notes / "reference_teaching-pace.md").write_text(
        "---\n"
        "name: teaching-pace\n"
        "description: Teaching feedback that may change revision work\n"
        "type: reference\n"
        "---\n\n"
        "TEACHING_BODY_MUST_NOT_APPEAR\n",
        encoding="utf-8",
    )
    (notes / "feedback_commit-messages.md").write_text(
        "---\n"
        "name: commit-messages\n"
        "description: Historical feedback about commit subjects\n"
        "type: feedback\n"
        "---\n\n"
        "COMMIT_BODY_MUST_NOT_APPEAR\n"
        "---\n"
        "BODY_AFTER_DELIMITER_MUST_NOT_APPEAR\n",
        encoding="utf-8",
    )
    (nested / "missing-frontmatter.md").write_text(
        "MISSING_FRONTMATTER_BODY_MUST_NOT_APPEAR\n",
        encoding="utf-8",
    )
    (nested / "unterminated-frontmatter.md").write_text(
        "---\nname: broken\nMALFORMED_BODY_MUST_NOT_APPEAR\n",
        encoding="utf-8",
    )
    (nested / "invalid-frontmatter.md").write_text(
        "---\nnot-a-flat-mapping\n---\nINVALID_BODY_MUST_NOT_APPEAR\n",
        encoding="utf-8",
    )
    (notes / "reference_binary-body.md").write_bytes(
        b"---\n"
        b"name: binary-body\n"
        b"description: Valid metadata before a non-text body\n"
        b"type: reference\n"
        b"---\n"
        b"\xffBODY_MUST_NOT_BE_READ\n"
    )
    outside_note = tmp_path / "outside.md"
    outside_note.write_text(
        "---\n"
        "name: outside\n"
        "description: This metadata is not project-owned\n"
        "type: reference\n"
        "---\n",
        encoding="utf-8",
    )
    (notes / "reference_external.md").symlink_to(outside_note)
    local_mail = notes / "local-mail" / "messages"
    local_mail.mkdir(parents=True)
    (local_mail / "message.md").write_text(
        '<!-- local-mail\n{"subject": "operational"}\n-->\n'
        "LOCAL_MAIL_BODY_MUST_NOT_APPEAR\n",
        encoding="utf-8",
    )

    _run(["git", "worktree", "add", "-b", "task", str(worktree)], cwd=repository)
    worktree_cwd = worktree / "nested" / "directory"
    worktree_cwd.mkdir(parents=True)

    result = _inventory(worktree_cwd)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["repository_root"] == str(repository.resolve())
    assert payload["notes_root"] == str(notes.resolve())
    assert payload["notes_root_exists"] is True
    assert payload["notes_root_status"] == "directory"
    assert payload["markdown_count"] == 7
    assert payload["excluded_markdown_count"] == 1
    assert payload["excluded"] == [
        {"path": ".notes/local-mail", "reason": "operational-state"}
    ]
    assert [note["path"] for note in payload["notes"]] == [
        ".notes/feedback_commit-messages.md",
        ".notes/nested/invalid-frontmatter.md",
        ".notes/nested/missing-frontmatter.md",
        ".notes/nested/unterminated-frontmatter.md",
        ".notes/reference_binary-body.md",
        ".notes/reference_external.md",
        ".notes/reference_teaching-pace.md",
    ]

    by_path = {note["path"]: note for note in payload["notes"]}
    assert by_path[".notes/reference_teaching-pace.md"] == {
        "path": ".notes/reference_teaching-pace.md",
        "frontmatter_status": "present",
        "frontmatter": (
            "name: teaching-pace\n"
            "description: Teaching feedback that may change revision work\n"
            "type: reference"
        ),
    }
    assert by_path[".notes/feedback_commit-messages.md"] == {
        "path": ".notes/feedback_commit-messages.md",
        "frontmatter_status": "present",
        "frontmatter": (
            "name: commit-messages\n"
            "description: Historical feedback about commit subjects\n"
            "type: feedback"
        ),
    }
    assert by_path[".notes/nested/missing-frontmatter.md"] == {
        "path": ".notes/nested/missing-frontmatter.md",
        "frontmatter_status": "missing",
        "frontmatter": None,
    }
    assert by_path[".notes/nested/unterminated-frontmatter.md"] == {
        "path": ".notes/nested/unterminated-frontmatter.md",
        "frontmatter_status": "malformed",
        "frontmatter": None,
    }
    assert by_path[".notes/nested/invalid-frontmatter.md"] == {
        "path": ".notes/nested/invalid-frontmatter.md",
        "frontmatter_status": "malformed",
        "frontmatter": None,
    }
    assert by_path[".notes/reference_binary-body.md"] == {
        "path": ".notes/reference_binary-body.md",
        "frontmatter_status": "present",
        "frontmatter": (
            "name: binary-body\n"
            "description: Valid metadata before a non-text body\n"
            "type: reference"
        ),
    }
    assert by_path[".notes/reference_external.md"] == {
        "path": ".notes/reference_external.md",
        "frontmatter_status": "symlink",
        "frontmatter": None,
    }
    assert "BODY_MUST_NOT_APPEAR" not in result.stdout

    main_cwd = repository / "nested" / "directory"
    main_cwd.mkdir(parents=True)
    main_result = _inventory(main_cwd)
    assert main_result.returncode == 0, main_result.stderr
    main_payload = json.loads(main_result.stdout)
    assert main_payload["repository_root"] == payload["repository_root"]
    assert main_payload["notes"] == payload["notes"]


def test_inventory_reports_an_absent_notes_directory(tmp_path: Path) -> None:
    project = tmp_path / "plain-project"
    project.mkdir()

    result = _inventory(project)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "repository_root": str(project.resolve()),
        "notes_root": str((project / ".notes").resolve()),
        "notes_root_exists": False,
        "notes_root_status": "absent",
        "markdown_count": 0,
        "excluded_markdown_count": 0,
        "excluded": [],
        "notes": [],
    }


def test_inventory_does_not_follow_a_symlinked_notes_root(tmp_path: Path) -> None:
    project = tmp_path / "project"
    outside = tmp_path / "outside-notes"
    project.mkdir()
    outside.mkdir()
    (outside / "reference_external.md").write_text(
        "---\nname: external\ndescription: Outside metadata\ntype: reference\n---\n",
        encoding="utf-8",
    )
    (project / ".notes").symlink_to(outside, target_is_directory=True)

    result = _inventory(project)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["notes_root_status"] == "symlink"
    assert payload["markdown_count"] == 0
    assert payload["excluded_markdown_count"] == 0
    assert payload["notes"] == []


def test_inventory_distinguishes_an_invalid_root_and_cwd(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".notes").write_text("not a directory\n", encoding="utf-8")

    result = _inventory(project)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["notes_root_exists"] is True
    assert payload["notes_root_status"] == "not-directory"
    assert payload["markdown_count"] == 0

    missing_cwd = _inventory(tmp_path / "missing")
    assert missing_cwd.returncode == 2
    assert missing_cwd.stdout == ""
    assert "not a directory" in missing_cwd.stderr
