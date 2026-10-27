"""Exercise the commit plugin's CLI against real, isolated Git repositories."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "plugins/denubis-git-commit/scripts/check_durable_records.py"
)
DECISION = "docs/architecture/decisions/0001-record.md"


def git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        env={
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GIT_")
        },
        capture_output=True,
        text=True,
        check=True,
    )


def write(repository: Path, path: str, text: str, *, tracked: bool = True) -> Path:
    destination = repository / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    if tracked:
        git(repository, "add", "--", path)
    return destination


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Durable Records Test")
    git(root, "config", "user.email", "records@example.invalid")
    git(root, "config", "core.excludesFile", os.devnull)
    write(root, ".gitignore", "private/\n.worktrees/\ncodex-prompts/\n")
    write(root, "src/record.txt", "Preserved evidence.\n")
    write(root, "private/evidence.md", "Ephemeral evidence.\n", tracked=False)
    return root


def check(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        cwd=repository,
        env={
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GIT_")
        },
        text=True,
        capture_output=True,
        check=False,
    )


def findings(
    result: subprocess.CompletedProcess[str],
) -> set[tuple[str, str, int, str]]:
    parsed: set[tuple[str, str, int, str]] = set()
    lines = result.stdout.splitlines()
    assert lines and lines[-1].startswith("SUMMARY "), result.stdout + result.stderr
    for line in lines[:-1]:
        kind, location, reference = line.split(" ", 2)
        path, number = location.rsplit(":", 1)
        parsed.add((kind, path, int(number), reference))
    return parsed


def test_ignored_citation_blocks_commit(repository: Path) -> None:
    write(repository, DECISION, "Evidence: `private/evidence.md`.\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert ("IGNORED", DECISION, 1, "private/evidence.md") in findings(result)


@pytest.mark.parametrize(
    ("document", "arguments"),
    [
        (DECISION, ()),
        ("docs/decisions/0001.md", ()),
        ("rulings/0001.md", ("--register", "rulings")),
        ("rulings.md", ("--register", "rulings.md")),
    ],
)
def test_untracked_registers_are_checked(
    repository: Path, document: str, arguments: tuple[str, ...]
) -> None:
    write(repository, document, "`private/evidence.md`\n", tracked=False)
    result = check(repository, *arguments)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("IGNORED", document, 1, "private/evidence.md")}


@pytest.mark.parametrize(
    ("location", "arguments"),
    [
        ("docs/decisions", ()),
        ("memory", ("--records", "memory", "--all")),
    ],
)
def test_ignored_untracked_records_are_excluded(
    repository: Path, location: str, arguments: tuple[str, ...]
) -> None:
    ignored = f"{location}/ignored.md"
    write(repository, ".gitignore", f"private/\n{ignored}\n")
    write(repository, ignored, "`private/evidence.md`\n", tracked=False)
    control = f"{location}/visible.md"
    write(repository, control, "`missing/control.md`\n", tracked=False)
    result = check(repository, *arguments)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", control, 1, "missing/control.md")}


@pytest.mark.parametrize(
    ("reference", "kind"),
    [
        (".worktrees/task/report.md", "WORKTREE"),
        ("codex-prompts/out/report.md", "EXCHANGE"),
        ("missing/report.md", "ABSENT"),
    ],
)
def test_citation_defect_kinds(repository: Path, reference: str, kind: str) -> None:
    write(repository, DECISION, f"Evidence: `{reference}`.\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {(kind, DECISION, 1, reference)}


@pytest.mark.parametrize(
    "citation",
    ["`lost/file.md`", "[evidence](lost/file.md)", "lost/file.md"],
)
def test_each_citation_syntax(repository: Path, citation: str) -> None:
    write(repository, DECISION, f"# Decision\n\nEvidence: {citation}.\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", DECISION, 3, "lost/file.md")}


def test_nested_relative_links_and_tracked_root_paths_are_clean(
    repository: Path,
) -> None:
    write(repository, "docs/architecture/decisions/evidence.md", "# Evidence\n")
    write(repository, "docs/architecture/decisions/a file.md", "# Space\n")
    write(repository, "private/tracked.md", "# Tracked exception\n", tracked=False)
    git(repository, "add", "-f", "private/tracked.md")
    write(
        repository,
        DECISION,
        "[sibling](evidence.md)\n"
        "[root](../../../src/record.txt#evidence)\n"
        "[space](<a file.md>)\n"
        "[encoded space](a%20file.md)\n"
        "`src/record.txt:1` and `private/tracked.md`.\n",
    )
    result = check(repository)
    assert result.returncode == 0, result.stdout + result.stderr
    assert findings(result) == set()


def test_nested_relative_ignored_path_is_rejected(repository: Path) -> None:
    write(repository, DECISION, "[evidence](../../../private/evidence.md)\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("IGNORED", DECISION, 1, "../../../private/evidence.md")
    }


@pytest.mark.parametrize("syntax", ["code", "link", "bare"])
@pytest.mark.parametrize(
    "reference",
    [
        "~other/y",
        "~other/x.md",
        "~other/.worktrees/x.md",
        "~other/codex-prompts/y.md",
    ],
)
def test_named_user_paths_are_external(
    repository: Path, syntax: str, reference: str
) -> None:
    citation = {
        "code": f"`{reference}`",
        "link": f"[source]({reference})",
        "bare": reference,
    }[syntax]
    write(repository, DECISION, f"{citation}\n")
    result = check(repository)
    assert result.returncode == 0, result.stdout + result.stderr
    assert findings(result) == set()
    assert result.stderr == ""


def test_current_user_home_paths_keep_repository_checks(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(repository))
    write(repository, DECISION, "`~/x.md`\n[home](~)\n")
    missing = check(repository)
    assert missing.returncode == 1, missing.stdout + missing.stderr
    assert findings(missing) == {("ABSENT", DECISION, 1, "~/x.md")}
    write(repository, "x.md", "# Evidence\n")
    present = check(repository)
    assert present.returncode == 0, present.stdout + present.stderr
    assert findings(present) == set()
    assert present.stderr == ""


@pytest.mark.parametrize("blocking", [False, True])
def test_unreadable_reference_warns_once_and_other_references_are_checked(
    repository: Path, blocking: bool
) -> None:
    reference = "bad%00/reference.md"
    write(
        repository,
        DECISION,
        f"`{reference}` [same]({reference}) {reference}\n"
        "`src/record.txt`\n" + ("`missing/control.md`\n" if blocking else ""),
    )
    result = check(repository)
    assert result.returncode == int(blocking), result.stdout + result.stderr
    assert findings(result) == (
        {("ABSENT", DECISION, 3, "missing/control.md")} if blocking else set()
    )
    assert result.stderr == f"WARN {DECISION}:1 unreadable reference {reference}\n"


@pytest.mark.parametrize(
    "excluded",
    [
        "https://example.invalid/missing/file.md",
        "https://example.invalid/a(b/c)",
        "https://example.invalid/{a/b}",
        "[remote](//example.invalid/missing/file.md)",
        "[remote](https://example.invalid/missing/file.md)",
        "`ssh://example.invalid/missing/file.md`",
        "[anchor](#missing/anchor)",
        "`#missing/anchor`",
        "`--output=missing/file.md`",
        "--output=missing/file.md",
        "`missing/*.md`",
        "missing/?.md",
        "`missing/[ab].md`",
        "[pattern](missing/*.md)",
        "`~/.claude/projects/never-read/record.jsonl:42`",
        "`~/.codex/sessions/never-read/record.jsonl`",
        "[transcript](~/.claude/projects/never-read/record.jsonl)",
    ],
)
def test_reference_exclusions_with_a_defect_control(
    repository: Path, excluded: str
) -> None:
    write(repository, DECISION, f"{excluded}\n`missing/control.md`\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", DECISION, 2, "missing/control.md")}


@pytest.mark.parametrize("syntax", ["code", "link", "bare"])
@pytest.mark.parametrize(
    "remote",
    [
        "git@github.com:Denubis/permission-queue.git",
        "git.ops_1-test@code-host.example:team/project.git",
    ],
)
def test_scp_style_git_remotes_are_not_file_citations(
    repository: Path, syntax: str, remote: str
) -> None:
    citation = {"code": f"`{remote}`", "link": f"[remote]({remote})", "bare": remote}[
        syntax
    ]
    write(repository, DECISION, f"Remote: {citation}\n")
    result = check(repository)
    assert result.returncode == 0, result.stdout + result.stderr
    assert findings(result) == set()


@pytest.mark.parametrize(
    "document",
    [DECISION, "docs/architecture/page.md", ".notes/quote.md", "docs/plan.md"],
)
@pytest.mark.parametrize("prefix", ["> ", "  > > "])
@pytest.mark.parametrize("strict", [False, True])
def test_blockquoted_absent_citations_are_advisory_everywhere(
    repository: Path, document: str, prefix: str, strict: bool
) -> None:
    write(repository, document, f"{prefix}`missing/quoted.md`\n")
    result = check(repository, document, *(["--strict"] if strict else []))
    assert result.returncode == 0, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", document, 1, "missing/quoted.md")}
    assert "advisory=1" in result.stdout


@pytest.mark.parametrize(
    "document",
    [DECISION, "docs/architecture/page.md", ".notes/quote.md", "docs/plan.md"],
)
@pytest.mark.parametrize(
    ("reference", "kind"),
    [
        ("private/evidence.md", "IGNORED"),
        ("codex-prompts/out/report.md", "EXCHANGE"),
        (".worktrees/task/report.md", "WORKTREE"),
    ],
)
@pytest.mark.parametrize("strict", [False, True])
def test_blockquoted_ephemeral_citations_are_advisory_everywhere(
    repository: Path, document: str, reference: str, kind: str, strict: bool
) -> None:
    write(repository, document, f"  > `{reference}`\n")
    result = check(repository, document, *(["--strict"] if strict else []))
    assert result.returncode == 0, result.stdout + result.stderr
    assert findings(result) == {(kind, document, 1, reference)}
    assert "advisory=1" in result.stdout


@pytest.mark.parametrize("quoted", [False, True])
def test_register_ephemeral_citations_are_advisory_only_on_blockquote_lines(
    repository: Path, quoted: bool
) -> None:
    write(repository, ".gitignore", "private/\n.notes/\n")
    write(repository, ".notes/x.md", "Local evidence.\n", tracked=False)
    references = [
        ("IGNORED", ".notes/x.md"),
        ("EXCHANGE", "codex-prompts/out/y.md"),
        ("WORKTREE", ".worktrees/z.md"),
    ]
    prefix = "> " if quoted else ""
    write(
        repository,
        DECISION,
        "".join(f"{prefix}see {reference}\n" for _, reference in references),
    )
    result = check(repository)
    assert result.returncode == (0 if quoted else 1), result.stdout + result.stderr
    assert findings(result) == {
        (kind, DECISION, number, reference)
        for number, (kind, reference) in enumerate(references, 1)
    }
    assert f"citations=3 advisory={3 if quoted else 0} " in result.stdout


def test_quoted_advisories_do_not_hide_an_unquoted_blocker(repository: Path) -> None:
    write(
        repository,
        DECISION,
        "> `private/evidence.md`\n"
        "> `codex-prompts/out/report.md`\n"
        "> `.worktrees/task/report.md`\n"
        "`missing/blocker.md`\n",
    )
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("IGNORED", DECISION, 1, "private/evidence.md"),
        ("EXCHANGE", DECISION, 2, "codex-prompts/out/report.md"),
        ("WORKTREE", DECISION, 3, ".worktrees/task/report.md"),
        ("ABSENT", DECISION, 4, "missing/blocker.md"),
    }
    assert "citations=4 advisory=3 " in result.stdout


def test_staged_adds_markdown_outside_registers(repository: Path) -> None:
    write(repository, "docs/guides/changed.md", "`missing/staged.md`\n")
    write(
        repository,
        "docs/guides/untracked.md",
        "`missing/untracked.md`\n",
        tracked=False,
    )
    assert findings(check(repository)) == set()
    result = check(repository, "--staged")
    assert result.returncode == 0, result.stdout + result.stderr
    assert findings(result) == {
        ("ABSENT", "docs/guides/changed.md", 1, "missing/staged.md")
    }


@pytest.mark.parametrize("include_plan", [False, True])
def test_staged_omits_changelog_and_selects_docs(
    repository: Path, include_plan: bool
) -> None:
    write(repository, "CHANGELOG.md", "`private/evidence.md`\n")
    if include_plan:
        write(repository, "docs/plan.md", "`codex-prompts/out/report.md`\n")
    result = check(repository, "--staged")
    assert result.returncode == int(include_plan), result.stdout + result.stderr
    assert findings(result) == (
        {("EXCHANGE", "docs/plan.md", 1, "codex-prompts/out/report.md")}
        if include_plan
        else set()
    )


@pytest.mark.parametrize("staged", [False, True])
def test_positionally_named_changelog_is_still_checked(
    repository: Path, staged: bool
) -> None:
    write(repository, "CHANGELOG.md", "`private/evidence.md`\n`missing/report.md`\n")
    arguments = [*(["--staged"] if staged else []), "CHANGELOG.md"]
    result = check(repository, *arguments)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("IGNORED", "CHANGELOG.md", 1, "private/evidence.md"),
        ("ABSENT", "CHANGELOG.md", 2, "missing/report.md"),
    }
    write(repository, "CHANGELOG.md", "`missing/report.md`\n")
    advisory_only = check(repository, *arguments)
    assert advisory_only.returncode == 0, advisory_only.stdout + advisory_only.stderr
    assert findings(advisory_only) == {
        ("ABSENT", "CHANGELOG.md", 1, "missing/report.md")
    }


def test_staged_rename_and_deletion(repository: Path) -> None:
    write(repository, "docs/guides/old.md", "# Evidence\n")
    write(repository, "docs/guides/deleted.md", "`missing/deleted.md`\n")
    git(repository, "commit", "-m", "fixture")
    git(repository, "mv", "docs/guides/old.md", "docs/guides/new.md")
    write(repository, "docs/guides/new.md", "`missing/renamed.md`\n")
    git(repository, "rm", "docs/guides/deleted.md")
    result = check(repository, "--staged")
    assert result.returncode == 0, result.stdout + result.stderr
    assert findings(result) == {
        ("ABSENT", "docs/guides/new.md", 1, "missing/renamed.md")
    }


def test_explicit_path_adds_an_untracked_document(repository: Path) -> None:
    write(repository, "reviews/report.md", "`missing/explicit.md`\n", tracked=False)
    result = check(repository, "reviews/report.md")
    assert result.returncode == 0, result.stdout + result.stderr
    assert findings(result) == {
        ("ABSENT", "reviews/report.md", 1, "missing/explicit.md")
    }


@pytest.mark.parametrize("tracked", [False, True])
def test_locations_can_override_the_default_registers_and_records(
    repository: Path, tracked: bool
) -> None:
    write(repository, DECISION, "`missing/default.md`\n")
    write(repository, "rulings/0001.md", "`missing/ruling.md`\n", tracked=tracked)
    write(repository, "memory/record.md", "`missing/memory.md`\n", tracked=tracked)
    result = check(repository, "--register", "rulings", "--records", "memory", "--all")
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("ABSENT", "rulings/0001.md", 1, "missing/ruling.md"),
        ("ABSENT", "memory/record.md", 1, "missing/memory.md"),
    }


def test_full_audit_reaches_every_conventional_location(
    repository: Path,
) -> None:
    locations = [
        "docs/architecture/decisions/0001.md",
        ".notes/decisions/0001.md",
        ".notes/reference.md",
        "docs/architecture/topology.markdown",
    ]
    for path in locations:
        write(repository, path, "`missing/evidence.md`\n")
    write(
        repository,
        "docs/architecture/untracked.md",
        "`missing/untracked.md`\n",
        tracked=False,
    )
    result = check(repository, "--all")
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("ABSENT", path, 1, "missing/evidence.md") for path in locations
    } | {("ABSENT", "docs/architecture/untracked.md", 1, "missing/untracked.md")}


def test_linked_worktree_uses_main_checkout_notes_and_local_staged_docs(
    repository: Path, tmp_path: Path
) -> None:
    write(repository, ".notes/reference.md", "# Evidence\n")
    git(repository, "commit", "-m", "fixture")
    worktree = tmp_path / "linked"
    git(repository, "worktree", "add", "-b", "task", str(worktree))
    write(repository, ".notes/reference.md", "`private/evidence.md`\n")
    write(worktree, "docs/guides/staged.md", "`missing/local.md`\n")
    result = check(worktree, "--staged", "--all")
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("IGNORED", ".notes/reference.md", 1, "private/evidence.md"),
        ("ABSENT", "docs/guides/staged.md", 1, "missing/local.md"),
    }


def test_execution_from_nested_directory(repository: Path) -> None:
    write(repository, DECISION, "`private/evidence.md`\n")
    result = check(repository / "src")
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("IGNORED", DECISION, 1, "private/evidence.md")}


@pytest.mark.parametrize("arguments", [("--unknown",), ("missing.md",)])
def test_usage_errors_exit_two(repository: Path, arguments: tuple[str, ...]) -> None:
    result = check(repository, *arguments)
    assert result.returncode == 2
    assert result.stderr


def test_outside_git_exits_two(tmp_path: Path) -> None:
    result = check(tmp_path)
    assert result.returncode == 2
    assert "git" in result.stderr.lower()


@pytest.mark.parametrize(
    "phrase",
    [
        "until",
        "not yet",
        "still open",
        "still to be",
        "for now",
        "to be proven",
        "CURRENTLY",
        "pending",
        "TODO",
        "WIP",
    ],
)
def test_transitional_wording_is_advisory_unless_strict(
    repository: Path, phrase: str
) -> None:
    write(
        repository, DECISION, f"# Decision\n\nThe migration is {phrase} incomplete.\n"
    )
    result = check(repository)
    assert result.returncode == 0, result.stdout + result.stderr
    assert findings(result) == {("TRANSITIONAL", DECISION, 3, phrase)}
    assert check(repository, "--strict").returncode == 1


def test_transitional_matching_ignores_fences_blockquotes_and_nonregisters(
    repository: Path,
) -> None:
    write(
        repository,
        DECISION,
        "# Decision\n"
        "> Human: currently pending\n"
        "> > TODO until WIP\n\n"
        "```text\nfor now\n```\n"
        "~~~text\nnot yet\n~~~\n"
        "The decision is currently incomplete.\n",
    )
    write(repository, ".notes/evidence.md", "The report is currently pending.\n")
    result = check(repository)
    assert result.returncode == 0, result.stdout + result.stderr
    assert findings(result) == {("TRANSITIONAL", DECISION, 11, "currently")}


def test_open_questions_require_question_line_and_reject_status_sections(
    repository: Path,
) -> None:
    questions = ".notes/project_open-questions.md"
    write(
        repository,
        questions,
        "# Open questions\n"
        "### Q1 Cache location\n"
        "Which cache belongs to this project?\n"
        "### Q2 Worker permission\n"
        "The operator must decide.\n"
        "## Progress update\n"
        "### Answered tickets\n"
        "Have these been answered?\n",
    )
    result = check(repository)
    assert result.returncode == 0, result.stdout + result.stderr
    observed = findings(result)
    assert {(kind, path, line) for kind, path, line, _ in observed} == {
        ("OPEN_QUESTION", questions, 4),
        ("OPEN_QUESTION", questions, 6),
        ("OPEN_QUESTION", questions, 7),
    }
    assert check(repository, "--strict").returncode == 1


def test_question_in_code_does_not_answer_a_ticket(repository: Path) -> None:
    questions = ".notes/project_open-questions.md"
    write(
        repository,
        questions,
        "### Q1 Missing question\n"
        "```\nExample?\n```\n"
        "#### Evidence\nA log line.\n"
        "### Q2 Real question\n"
        "Question for Brian:\nMay the worker proceed?\n",
    )
    result = check(repository, "--strict")
    assert result.returncode == 1, result.stdout + result.stderr
    assert {
        line for kind, _, line, _ in findings(result) if kind == "OPEN_QUESTION"
    } == {1}


def test_open_questions_checked_even_when_gitignored(repository: Path) -> None:
    write(repository, ".gitignore", "private/\n.notes/\n")
    write(
        repository,
        ".notes/project_open-questions.md",
        "### Q1 Cache choice\nNo question.\n",
        tracked=False,
    )
    result = check(repository, "--strict")
    assert result.returncode == 1, result.stdout + result.stderr
    assert {kind for kind, _, _, _ in findings(result)} == {"OPEN_QUESTION"}


def test_claude_finding_aid_selects_a_custom_decision_register(
    repository: Path,
) -> None:
    write(
        repository,
        "CLAUDE.md",
        "## Finding aids\n\n- Design decisions: `decisions/`.\n",
    )
    write(
        repository,
        "decisions/0001.md",
        "The evidence is pending.\n`missing/finding.md`\n",
    )
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("TRANSITIONAL", "decisions/0001.md", 1, "pending"),
        ("ABSENT", "decisions/0001.md", 2, "missing/finding.md"),
    }


def test_worktree_container_does_not_taint_local_tracked_citations(
    repository: Path,
) -> None:
    write(repository, DECISION, "`src/record.txt`\n")
    git(repository, "commit", "-m", "fixture")
    worktree = repository / ".worktrees/task"
    git(repository, "worktree", "add", "-b", "task", str(worktree))
    result = check(worktree)
    assert result.returncode == 0, result.stdout + result.stderr
    assert findings(result) == set()


def test_markdown_reference_definitions_and_balanced_destinations(
    repository: Path,
) -> None:
    write(repository, "docs/architecture/decisions/file(v1).md", "# Evidence\n")
    write(
        repository,
        DECISION,
        "[evidence](file(v1).md)\n[missing evidence][source]\n\n[source]: missing.md\n",
    )
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", DECISION, 4, "missing.md")}


def test_lazy_blockquote_continuation_is_not_decision_state(repository: Path) -> None:
    write(
        repository,
        DECISION,
        "> Human: currently pending\n"
        "until tomorrow\n\n"
        "The decision is currently incomplete.\n",
    )
    result = check(repository)
    assert result.returncode == 0, result.stdout + result.stderr
    assert findings(result) == {("TRANSITIONAL", DECISION, 4, "currently")}


def test_cli_register_override_takes_precedence_over_finding_aids(
    repository: Path,
) -> None:
    write(repository, "CLAUDE.md", "- Design decisions: `old-register/`.\n")
    write(repository, "old-register/0001.md", "`missing/old.md`\n")
    write(repository, "new-register/0001.md", "`missing/new.md`\n")
    result = check(repository, "--register", "new-register")
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", "new-register/0001.md", 1, "missing/new.md")}


def test_summary_counts_each_finding_and_strict_cannot_relax_citations(
    repository: Path,
) -> None:
    write(repository, DECISION, "The decision is pending.\n`missing/report.md`\n")
    write(
        repository,
        ".notes/project_open-questions.md",
        "### Q1 Cache choice\nNo question.\n",
    )
    for arguments in [(), ("--strict",)]:
        result = check(repository, *arguments)
        assert result.returncode == 1, result.stdout + result.stderr
        counts = dict(
            field.split("=") for field in result.stdout.splitlines()[-1].split()[1:]
        )
        assert counts == {
            "citations": "1",
            "advisory": "0",
            "transitional": "1",
            "open_questions": "1",
        }


def test_git_failure_is_not_a_clean_repository(repository: Path) -> None:
    (repository / ".git/config").write_text(
        "[invalid configuration\n", encoding="utf-8"
    )
    result = check(repository)
    assert result.returncode == 2
    assert result.stderr


def test_double_separator_in_local_path_is_not_a_protocol_relative_url(
    repository: Path,
) -> None:
    write(repository, DECISION, "missing//local.md\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", DECISION, 1, "missing//local.md")}


@pytest.mark.parametrize("location", [".notes", "docs/architecture", "memory"])
@pytest.mark.parametrize("selection", ["named", "staged"])
def test_selected_record_does_not_select_its_siblings(
    repository: Path, location: str, selection: str
) -> None:
    write(repository, DECISION, "`missing/register.md`\n")
    write(repository, f"{location}/unrelated.md", "`missing/unrelated.md`\n")
    git(repository, "commit", "-m", "fixture")
    selected = f"{location}/selected.md"
    write(repository, selected, "`missing/selected.md`\n")
    arguments = [selected] if selection == "named" else ["--staged"]
    result = check(repository, "--records", location, *arguments)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("ABSENT", DECISION, 1, "missing/register.md"),
        ("ABSENT", selected, 1, "missing/selected.md"),
    }


def test_default_selects_registers_and_queue_without_unrelated_records(
    repository: Path,
) -> None:
    write(repository, DECISION, "`missing/register.md`\n")
    write(repository, ".notes/unrelated.md", "`missing/note.md`\n")
    write(repository, "docs/architecture/topology.md", "`missing/architecture.md`\n")
    questions = ".notes/project_open-questions.md"
    write(repository, questions, "### Q1 Evidence\nMay we use `private/evidence.md`?\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("ABSENT", DECISION, 1, "missing/register.md"),
        ("IGNORED", questions, 2, "private/evidence.md"),
    }


@pytest.mark.parametrize("audit_all", [False, True])
def test_globally_ignored_notes_use_filesystem_and_skip_operational_mail(
    repository: Path, tmp_path: Path, audit_all: bool
) -> None:
    excludes = tmp_path / "global-excludes"
    excludes.write_text(".notes/\n", encoding="utf-8")
    git(repository, "config", "core.excludesFile", str(excludes))
    write(
        repository, ".notes/decisions/0001.md", "`missing/ruling.md`\n", tracked=False
    )
    write(repository, ".notes/reference.md", "`missing/note.md`\n", tracked=False)
    write(
        repository,
        ".notes/local-mail/nested/envelope.md",
        "`missing/mail.md`\n",
        tracked=False,
    )
    assert git(repository, "ls-files", "--", ".notes").stdout == ""
    result = check(repository, *(["--all"] if audit_all else []))
    assert result.returncode == 1, result.stdout + result.stderr
    expected = {("ABSENT", ".notes/decisions/0001.md", 1, "missing/ruling.md")}
    if audit_all:
        expected.add(("ABSENT", ".notes/reference.md", 1, "missing/note.md"))
    assert findings(result) == expected


@pytest.mark.parametrize("selection", ["named", "all"])
def test_ignored_notes_are_read_from_main_checkout_in_linked_worktree(
    repository: Path, tmp_path: Path, selection: str
) -> None:
    excludes = tmp_path / "global-excludes"
    excludes.write_text(".notes/\n", encoding="utf-8")
    git(repository, "config", "core.excludesFile", str(excludes))
    git(repository, "commit", "-m", "fixture")
    worktree = tmp_path / "linked"
    git(repository, "worktree", "add", "-b", "task", str(worktree))
    write(repository, ".notes/reference.md", "`private/evidence.md`\n", tracked=False)
    result = check(
        worktree, *([".notes/reference.md"] if selection == "named" else ["--all"])
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("IGNORED", ".notes/reference.md", 1, "private/evidence.md")
    }


def test_citation_of_a_globally_ignored_note_remains_ignored(
    repository: Path, tmp_path: Path
) -> None:
    excludes = tmp_path / "global-excludes"
    excludes.write_text(".notes/\n", encoding="utf-8")
    git(repository, "config", "core.excludesFile", str(excludes))
    write(repository, ".notes/reference.md", "# Evidence\n", tracked=False)
    write(repository, DECISION, "[note](.notes/reference.md)\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("IGNORED", DECISION, 1, ".notes/reference.md")}


@pytest.mark.parametrize("syntax", ["code", "link", "bare"])
@pytest.mark.parametrize("node", ["test_evidence", "test_evidence[param]"])
def test_pytest_node_ids_resolve_the_file_before_the_suffix(
    repository: Path, syntax: str, node: str
) -> None:
    reference = f"src/record.txt::{node}"
    citation = {
        "code": f"`{reference}`",
        "link": f"[test]({reference})",
        "bare": reference,
    }[syntax]
    write(repository, DECISION, f"{citation}\n`missing/report.py::test_missing`\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("ABSENT", DECISION, 2, "missing/report.py::test_missing")
    }


@pytest.mark.parametrize(
    "outside", ["/proc/mounts", "~/.claude/CLAUDE.md", "~/missing-system-file.md"]
)
def test_external_paths_are_not_repository_citations(
    repository: Path, outside: str
) -> None:
    write(repository, DECISION, f"`{outside}`\n`missing/real.md`\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", DECISION, 2, "missing/real.md")}


@pytest.mark.parametrize(
    "segment,kind", [(".worktrees", "WORKTREE"), ("codex-prompts", "EXCHANGE")]
)
def test_external_paths_keep_ephemeral_segment_defects(
    repository: Path, tmp_path: Path, segment: str, kind: str
) -> None:
    external = str(tmp_path / segment / "report.md")
    write(repository, DECISION, f"[external]({external})\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {(kind, DECISION, 1, external)}


@pytest.mark.parametrize("token", ["/", "/clear", "/status", "/statusline", "/proc"])
@pytest.mark.parametrize("syntax", ["code", "link", "bare"])
def test_single_segment_commands_and_root_separator_are_not_citations(
    repository: Path, token: str, syntax: str
) -> None:
    citation = {"code": f"`{token}`", "link": f"[command]({token})", "bare": token}[
        syntax
    ]
    write(repository, DECISION, f"{citation}\n`missing/real.md`\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", DECISION, 2, "missing/real.md")}


@pytest.mark.parametrize(
    "pair", ["Astra/Fable", "i/o", "and/or", "skills/agents/commands"]
)
def test_bare_prose_pairs_are_skipped_but_quoted_paths_remain_checked(
    repository: Path, pair: str
) -> None:
    write(repository, DECISION, f"{pair}\n`{pair}`\n[reference]({pair})\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("ABSENT", DECISION, 2, pair),
        ("ABSENT", DECISION, 3, pair),
    }


@pytest.mark.parametrize(
    "reference",
    [
        "./missing/file",
        "../missing/file",
        "src/missing/noext",
        "README/missing",
        "missing/file.md",
    ],
)
def test_bare_path_signals_still_find_real_missing_paths(
    repository: Path, reference: str
) -> None:
    write(repository, "README", "Fixture\n")
    write(repository, DECISION, f"{reference}\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", DECISION, 1, reference)}


@pytest.mark.parametrize("syntax", ["code", "link", "bare"])
@pytest.mark.parametrize("exists", [False, True])
def test_symbolic_suffix_resolves_the_file(
    repository: Path, syntax: str, exists: bool
) -> None:
    reference = f"{'src' if exists else 'missing'}/record.txt:open_source"
    citation = {
        "code": f"`{reference}`",
        "link": f"[source]({reference})",
        "bare": reference,
    }[syntax]
    write(repository, DECISION, f"{citation}\n")
    result = check(repository)
    assert result.returncode == (0 if exists else 1), result.stdout + result.stderr
    assert findings(result) == (
        set() if exists else {("ABSENT", DECISION, 1, reference)}
    )


@pytest.mark.parametrize("reference", ["missing/report.md", "private/missing.md"])
def test_nonexistent_candidates_under_ignored_directories_are_absent(
    repository: Path, reference: str
) -> None:
    write(repository, ".gitignore", "private/\n.notes/\n")
    document = ".notes/decisions/0001.md"
    write(repository, document, f"`{reference}`\n", tracked=False)
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", document, 1, reference)}


@pytest.mark.parametrize("syntax", ["code", "link", "bare"])
@pytest.mark.parametrize("prefix", ["x", "word"])
@pytest.mark.parametrize(
    ("path", "kind"),
    [
        ("codex-prompts/out/report.md", "EXCHANGE"),
        (".worktrees/task/report.md", "WORKTREE"),
        ("private/evidence.md", "IGNORED"),
    ],
)
def test_unknown_scheme_prefix_does_not_hide_local_defects(
    repository: Path, syntax: str, prefix: str, path: str, kind: str
) -> None:
    reference = f"{prefix}:{path}"
    citation = {
        "code": f"`{reference}`",
        "link": f"[source]({reference})",
        "bare": reference,
    }[syntax]
    write(
        repository,
        DECISION,
        f"{citation}\nhttps://example.invalid/codex-prompts/out/report.md\n",
    )
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {(kind, DECISION, 1, reference)}


def test_untracked_directory_does_not_turn_bare_prose_into_a_path(
    repository: Path,
) -> None:
    (repository / "deployment").mkdir()
    write(repository, DECISION, "The deployment/viewer pair.\nsrc/missing/noext\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", DECISION, 2, "src/missing/noext")}


def test_bare_ignored_present_note_is_still_a_citation(repository: Path) -> None:
    write(repository, ".gitignore", "private/\n.notes/\n")
    write(repository, ".notes/evidence", "Local evidence.\n", tracked=False)
    write(repository, DECISION, ".notes/evidence\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("IGNORED", DECISION, 1, ".notes/evidence")}


@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize(
    ("reference", "kind"),
    [
        ("codex-prompts/out/report.md", "EXCHANGE"),
        (".worktrees/task/report.md", "WORKTREE"),
        ("private/evidence.md", "IGNORED"),
    ],
)
def test_staged_design_plan_absent_is_advisory_but_ephemeral_is_blocking(
    repository: Path, strict: bool, reference: str, kind: str
) -> None:
    plan = "docs/design-plans/future.md"
    write(repository, plan, f"`missing/future.md`\n`{reference}`\n")
    arguments = ["--staged", *(["--strict"] if strict else [])]
    result = check(repository, *arguments)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("ABSENT", plan, 1, "missing/future.md"),
        (kind, plan, 2, reference),
    }
    write(repository, plan, "`missing/future.md`\n")
    advisory_only = check(repository, *arguments)
    assert advisory_only.returncode == 0, advisory_only.stdout + advisory_only.stderr
    assert findings(advisory_only) == {("ABSENT", plan, 1, "missing/future.md")}


@pytest.mark.parametrize("location", [".notes", "docs/architecture", "memory"])
@pytest.mark.parametrize("selection", ["named", "staged"])
def test_selected_records_keep_absent_blocking(
    repository: Path, location: str, selection: str
) -> None:
    record = f"{location}/evidence.md"
    write(repository, record, "`missing/evidence.md`\n")
    arguments = [record] if selection == "named" else ["--staged"]
    result = check(repository, "--records", location, *arguments)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", record, 1, "missing/evidence.md")}


@pytest.mark.parametrize("suffix", ["open_source", "42", "42:7"])
def test_sibling_file_locators_are_not_mistaken_for_scheme_prefixes(
    repository: Path, suffix: str
) -> None:
    write(repository, "docs/architecture/decisions/evidence.txt", "Evidence.\n")
    write(
        repository,
        DECISION,
        f"[source](evidence.txt:{suffix})\n[missing](missing.txt:{suffix})\n",
    )
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", DECISION, 2, f"missing.txt:{suffix}")}


@pytest.mark.parametrize(
    ("reference", "kind"),
    [("word:private/evidence", "IGNORED"), ("word:src/missing/noext", "ABSENT")],
)
def test_prefixed_bare_paths_keep_tracked_and_ignored_name_signals(
    repository: Path, reference: str, kind: str
) -> None:
    write(repository, "private/evidence", "Ephemeral evidence.\n", tracked=False)
    write(repository, DECISION, f"{reference}\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {(kind, DECISION, 1, reference)}


@pytest.mark.parametrize("audit_all", [False, True])
def test_default_docs_decisions_register_is_checked(
    repository: Path, audit_all: bool
) -> None:
    register = "docs/decisions/adr-register.md"
    write(repository, register, "`private/evidence.md`\n")
    result = check(repository, *(["--all"] if audit_all else []))
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("IGNORED", register, 1, "private/evidence.md")}


def test_markdown_file_register_does_not_select_siblings(repository: Path) -> None:
    register = "docs/decisions/adr-register.md"
    write(repository, register, "Evidence is pending.\n`private/evidence.md`\n")
    write(repository, "docs/decisions/unrelated.md", "`missing/unrelated.md`\n")
    result = check(repository, "--register", register)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("TRANSITIONAL", register, 1, "pending"),
        ("IGNORED", register, 2, "private/evidence.md"),
    }


@pytest.mark.parametrize("audit_all", [False, True])
def test_missing_default_registers_are_skipped_silently(
    repository: Path, audit_all: bool
) -> None:
    write(repository, "docs/guide.md", "`src/record.txt`\n")
    result = check(repository, *(["--all"] if audit_all else []))
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert findings(result) == set()


def test_all_adds_tracked_and_untracked_markdown_directly_under_docs_and_decisions(
    repository: Path,
) -> None:
    records = ["docs/guide.markdown", "docs/decisions/adr-register.md"]
    for record in records:
        write(repository, record, "`private/evidence.md`\n")
    write(repository, "docs/nested/guide.md", "`missing/nested.md`\n")
    write(repository, "docs/decisions/nested/guide.md", "`missing/nested.md`\n")
    write(repository, "docs/data.txt", "`missing/nonmarkdown.md`\n")
    for record in ["docs/untracked.md", "docs/decisions/untracked.md"]:
        write(repository, record, "`missing/untracked.md`\n", tracked=False)
    result = check(repository, "--all", "--register", "rulings", "--records", "memory")
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("IGNORED", record, 1, "private/evidence.md") for record in records
    } | {
        ("ABSENT", record, 1, "missing/untracked.md")
        for record in ["docs/untracked.md", "docs/decisions/untracked.md"]
    }


@pytest.mark.parametrize("selection", ["named", "staged"])
def test_all_direct_records_keep_their_rules_when_also_selected(
    repository: Path, selection: str
) -> None:
    record = "docs/guide.md"
    write(repository, record, "`missing/evidence.md`\n")
    arguments = [record] if selection == "named" else ["--staged"]
    result = check(repository, "--all", *arguments)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", record, 1, "missing/evidence.md")}
    assert "advisory=0" in result.stdout


@pytest.mark.parametrize("claude", [None, "  @AGENTS.md  \n", "# Rules\n@AGENTS.md\n"])
def test_agents_finding_aids_select_registers_and_records(
    repository: Path, claude: str | None
) -> None:
    if claude is not None:
        write(repository, "CLAUDE.md", claude)
    write(
        repository,
        "AGENTS.md",
        "- Design decisions: `rulings/`.\n- Project notes: `memory/`.\n",
    )
    write(repository, "rulings/0001.md", "Evidence is pending.\n")
    write(repository, "memory/evidence.md", "`private/evidence.md`\n")
    result = check(repository, "--all")
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("TRANSITIONAL", "rulings/0001.md", 1, "pending"),
        ("IGNORED", "memory/evidence.md", 1, "private/evidence.md"),
    }


@pytest.mark.parametrize("source", ["claude", "agents", "agents-wrapper"])
def test_finding_aid_includes_are_root_relative_and_one_level(
    repository: Path, source: str
) -> None:
    primary = "CLAUDE.md" if source == "claude" else "AGENTS.md"
    if source == "agents-wrapper":
        write(repository, "CLAUDE.md", "@AGENTS.md\n")
    write(
        repository,
        primary,
        "# Rules\n  @config/finding-aids.md  \n@records.md\nOrdinary text.\n",
    )
    write(
        repository,
        "config/finding-aids.md",
        "- Decision register: `rulings/index.md`.\n@nested.md\n",
    )
    write(repository, "records.md", "- Project notes: `memory/`.\n")
    write(repository, "nested.md", "- Decision register: `unwanted/`.\n")
    write(repository, "rulings/index.md", "Evidence is pending.\n")
    write(repository, "memory/evidence.md", "`private/evidence.md`\n")
    write(repository, "unwanted/0001.md", "`missing/nested.md`\n")
    result = check(repository, "--all")
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("TRANSITIONAL", "rulings/index.md", 1, "pending"),
        ("IGNORED", "memory/evidence.md", 1, "private/evidence.md"),
    }


def test_finding_aid_includes_skip_missing_external_and_nonstandalone_paths(
    repository: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text("- Design decisions: `unwanted/`.\n", encoding="utf-8")
    (repository / "escape.md").symlink_to(outside)
    write(
        repository,
        "CLAUDE.md",
        "@missing.md\n@../outside.md\n"
        f"@{outside}\n@escape.md\n"
        "@extra.md trailing words\nInline @extra.md\n  @valid.md  \n",
    )
    write(repository, "extra.md", "- Decision register: `unwanted/`.\n")
    write(repository, "valid.md", "- Decision register: `rulings/`.\n")
    write(repository, "unwanted/0001.md", "`missing/unwanted.md`\n")
    write(repository, "rulings/0001.md", "`private/evidence.md`\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("IGNORED", "rulings/0001.md", 1, "private/evidence.md")
    }


@pytest.mark.parametrize("syntax", ["code", "link", "bare"])
def test_line_ranges_resolve_existing_files_and_keep_missing_files(
    repository: Path, syntax: str
) -> None:
    write(repository, "docs/deployment.md", "Deployment evidence.\n")
    reference = "docs/deployment.md:1944-1950"
    citation = {
        "code": f"`{reference}`",
        "link": f"[source]({reference})",
        "bare": reference,
    }[syntax]
    write(repository, DECISION, f"{citation}\n`missing/report.md:9-12`\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", DECISION, 2, "missing/report.md:9-12")}


@pytest.mark.parametrize("base", ["", "docs/architecture/decisions/"])
def test_backticked_paths_with_spaces_resolve_before_splitting(
    repository: Path, base: str
) -> None:
    reference = "references/character/Becky Bennett.json"
    write(repository, base + reference, "{}\n")
    write(repository, DECISION, f"`{reference}`\n`missing/control.md`\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", DECISION, 2, "missing/control.md")}


def test_backticked_spaced_ignored_path_and_command_fallback(
    repository: Path,
) -> None:
    reference = "private/Becky Bennett.json"
    write(repository, reference, "{}\n", tracked=False)
    write(
        repository,
        DECISION,
        f"`{reference}`\n`cat src/record.txt missing/control.md`\n",
    )
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("IGNORED", DECISION, 1, reference),
        ("ABSENT", DECISION, 2, "missing/control.md"),
    }


@pytest.mark.parametrize("syntax", ["code", "link", "bare"])
@pytest.mark.parametrize("missing", [False, True])
def test_brace_sets_report_only_failing_alternatives(
    repository: Path, syntax: str, missing: bool
) -> None:
    for directory in ("docx", "pdf", "email"):
        if directory != "email" or not missing:
            write(repository, f"sources/{directory}/evidence.txt", "Evidence.\n")
    reference = "sources/{docx,pdf,email}"
    citation = {
        "code": f"`{reference}`",
        "link": f"[source]({reference})",
        "bare": reference,
    }[syntax]
    write(repository, DECISION, f"{citation}\n")
    result = check(repository)
    assert result.returncode == int(missing), result.stdout + result.stderr
    assert findings(result) == (
        {("ABSENT", DECISION, 1, "sources/email")} if missing else set()
    )


def test_multiple_brace_sets_expand_each_path_segment(repository: Path) -> None:
    for path in ("docx/draft", "docx/final", "pdf/draft"):
        write(repository, f"sources/{path}.md", "Evidence.\n")
    write(repository, DECISION, "`sources/{docx,pdf}/{draft,final}.md`\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", DECISION, 1, "sources/pdf/final.md")}


@pytest.mark.parametrize("syntax", ["code", "link", "bare"])
@pytest.mark.parametrize(
    "prefix",
    [
        "fix",
        "feat",
        "feature",
        "chore",
        "docs",
        "refactor",
        "release",
        "hotfix",
        "test",
        "ci",
        "build",
        "perf",
        "style",
    ],
)
def test_branch_names_are_prose_with_a_missing_path_control(
    repository: Path, syntax: str, prefix: str
) -> None:
    reference = f"{prefix}/queued-human-dialogue"
    citation = {
        "code": f"`{reference}`",
        "link": f"[source]({reference})",
        "bare": reference,
    }[syntax]
    write(repository, DECISION, f"{citation}\n`feature/bugfix`\n`missing/control.md`\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", DECISION, 3, "missing/control.md")}


@pytest.mark.parametrize("base", ["", "docs/architecture/decisions/"])
def test_branch_prefixes_keep_tracked_absent_and_present_ignored_paths(
    repository: Path, base: str
) -> None:
    write(repository, base + "docs/evidence.txt", "Evidence.\n").unlink()
    write(repository, ".gitignore", "private/\nfix/\n")
    write(repository, base + "fix/evidence.md", "Ignored evidence.\n", tracked=False)
    if base:
        write(repository, ".gitignore", "private/\n**/fix/\n")
    write(repository, DECISION, "`docs/evidence.txt`\n`fix/evidence.md`\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("ABSENT", DECISION, 1, "docs/evidence.txt"),
        ("IGNORED", DECISION, 2, "fix/evidence.md"),
    }


@pytest.mark.parametrize("syntax", ["code", "link", "bare"])
@pytest.mark.parametrize("name", ["evaluation.py", "evaluation.md"])
def test_files_moved_out_of_docs_stay_absent_beside_branch_names(
    repository: Path, syntax: str, name: str
) -> None:
    moved = f"docs/{name}"
    write(repository, moved, "Evidence.\n")
    (repository / "scripts").mkdir()
    git(repository, "mv", "--", moved, f"scripts/{name}")
    citation = {
        "code": f"`{moved}`",
        "link": f"[source]({moved})",
        "bare": moved,
    }[syntax]
    write(
        repository,
        DECISION,
        f"{citation}\n`fix/queued-human-dialogue`\n`release/1.5.0`\n",
    )
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", DECISION, 1, moved)}


@pytest.mark.parametrize("syntax", ["code", "link", "bare"])
@pytest.mark.parametrize(
    "placeholder",
    [
        "$XDG_STATE_HOME/branch-bg/registry.json",
        "${CLAUDE_PLUGIN_ROOT}/hooks/missing.py",
        '"${PLUGIN_ROOT}/hooks/missing.py"',
        "src/missing-$UID/state.json",
        "src/${NAME}-cache/state.json",
        "${CLAUDE_REAL_BINARY:-src/missing/claude}",
        "…/branch-strip.sh",
        "src/…/missing.md",
        "src/missing/…",
        ".../branch-strip.sh",
        "src/.../missing.md",
        "src/missing/...",
        "cache/branch-bg-<uid>/<md5(path,title)>",
        "src/<name>/missing.md",
        "<repo>/src/missing.md",
        "plugins/<name>/hooks/",
    ],
)
def test_placeholder_tokens_are_not_citations_beside_a_missing_control(
    repository: Path, syntax: str, placeholder: str
) -> None:
    citation = {
        "code": f"`{placeholder}`",
        "link": f"[source]({placeholder})",
        "bare": placeholder,
    }[syntax]
    write(repository, DECISION, f"{citation} beside `missing/control.md`\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", DECISION, 1, "missing/control.md")}


@pytest.mark.parametrize(
    "placeholder",
    [
        "$XDG_STATE_HOME/branch-bg/registry.json",
        "…/branch-strip.sh",
        "src/missing/...",
        "src/<name>/missing.md",
    ],
)
def test_placeholder_reference_definitions_are_not_citations(
    repository: Path, placeholder: str
) -> None:
    write(repository, DECISION, f"[source]: {placeholder}\n`missing/control.md`\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", DECISION, 2, "missing/control.md")}


def test_prose_ellipsis_after_a_path_keeps_the_path_checked(repository: Path) -> None:
    write(repository, DECISION, "See src/missing.md... and ../missing/file.md\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("ABSENT", DECISION, 1, "src/missing.md"),
        ("ABSENT", DECISION, 1, "../missing/file.md"),
    }


def test_single_directory_segment_is_prose_bare_and_cited_when_quoted(
    repository: Path,
) -> None:
    write(
        repository,
        DECISION,
        "a people/ path segment\n`people/`\n[segment](people/)\n`src/`\n",
    )
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("ABSENT", DECISION, 2, "people/"),
        ("ABSENT", DECISION, 3, "people/"),
    }


@pytest.mark.parametrize("exists", [False, True])
@pytest.mark.parametrize("syntax", ["code", "link", "symlink"])
def test_registered_external_worktree_paths_are_worktree_findings(
    repository: Path, tmp_path: Path, exists: bool, syntax: str
) -> None:
    git(repository, "commit", "-m", "fixture")
    worktree = tmp_path / "jcal-transcript-exporter-repair"
    git(repository, "worktree", "add", "-b", "repair", str(worktree))
    target = "src/record.txt" if exists else "missing/report.md"
    reference = str(worktree / target)
    if syntax == "symlink":
        (repository / "linked-evidence").symlink_to(worktree, target_is_directory=True)
        reference = f"linked-evidence/{target}"
    citation = f"[source](<{reference}>)" if syntax == "link" else f"`{reference}`"
    write(repository, DECISION, f"{citation}\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("WORKTREE", DECISION, 1, reference)}


def test_worktree_paths_do_not_match_a_sibling_with_the_same_prefix(
    repository: Path, tmp_path: Path
) -> None:
    git(repository, "commit", "-m", "fixture")
    worktree = tmp_path / "linked repair"
    git(repository, "worktree", "add", "-b", "repair", str(worktree))
    outside = str(tmp_path / "linked repair-other/src/record.txt")
    reference = str(worktree / "codex-prompts/report.md")
    write(repository, DECISION, f"[outside](<{outside}>)\n[source](<{reference}>)\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("WORKTREE", DECISION, 2, reference)}


def test_absolute_main_checkout_paths_are_not_linked_worktree_citations(
    repository: Path, tmp_path: Path
) -> None:
    git(repository, "commit", "-m", "fixture")
    worktree = tmp_path / "linked"
    git(repository, "worktree", "add", "-b", "repair", str(worktree))
    write(worktree, DECISION, f"`{repository}/src/record.txt`\n`missing/control.md`\n")
    result = check(worktree)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {("ABSENT", DECISION, 2, "missing/control.md")}


@pytest.mark.parametrize("prefix", ["fix", "build"])
def test_branch_prefix_without_a_slash_still_checks_a_sibling_link(
    repository: Path, prefix: str
) -> None:
    write(repository, DECISION, f"[source]({prefix})\n`missing/control.md`\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert findings(result) == {
        ("ABSENT", DECISION, 1, prefix),
        ("ABSENT", DECISION, 2, "missing/control.md"),
    }
