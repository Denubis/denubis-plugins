"""Tests for denubis-notes-advisory/hooks/session-notes-advisory.py.

The hook exists because a reminder to read `.notes/` already lived in the
global CLAUDE.md and was ignored in practice. Two failures on 2026-08-08
(session ``dbfd50af``) traced to the same shape: the note existed, the scan was
skipped, and a grep that came back clean was read as proof of absence. The hook
does not repeat the exhortation. It supplies the three facts a session cannot
cheaply derive — that `.notes/` exists here, how many notes are in it, and
where this session's transcript lives — and names the skill that does the work.

What is asserted here is the contract, not the prose:

- **Worktree resolution.** `.notes/` lives at the main repo root, the parent of
  ``git rev-parse --git-common-dir``, never in a worktree. A hook that resolved
  it against the process cwd would report "no notes here" from every worktree,
  which is the absence-is-not-a-signal failure with a hook wrapped around it.
- **Silence when there is nothing to say.** A project with no `.notes/` gets no
  output at all, so the hook costs nothing in the projects it cannot help.
- **A stable attribute header.** The prose is expected to be reworded; the
  ``<notes-advisory dispatch=… notes=… dir=… transcript=…>`` header is the
  machine-readable part of the contract, so the tests key off it rather than
  pinning phrasing. Keying off phrasing would make these change-detectors that
  fire on legitimate edits. Keying off a bare ``"3"`` would be worse still — a
  digit in a pytest tmp path would satisfy it, so the assertion could pass
  without the count ever being emitted.
- **Never blocking session start.** Malformed stdin, absent stdin, and a
  non-git directory all exit 0.

Stdin is read inside ``main()`` rather than at module level. ``uv run python``
aside, ``test_hook_portability.py`` *imports* every hook under a 3.9 canary to
execute its module body; a module-level ``sys.stdin.read()`` would block that
test until its timeout instead of failing or passing.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# tests/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[1]
_HOOK_PATH = (
    _REPO_ROOT
    / "plugins"
    / "denubis-notes-advisory"
    / "hooks"
    / "session-notes-advisory.py"
)

_GIT_IDENTITY = [
    "-c",
    "user.email=test@example.invalid",
    "-c",
    "user.name=Test",
]


def _git(cwd: Path, *args: str) -> None:
    """Run a git command in ``cwd``, raising on failure."""
    subprocess.run(
        ["git", *_GIT_IDENTITY, *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        timeout=30,
    )


def _init_repo(root: Path) -> Path:
    """Create a git repo at ``root`` with one commit, so worktrees can be added."""
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "--initial-branch=main")
    (root / "README.md").write_text("seed\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-m", "seed")
    return root


def _seed_notes(root: Path, names: list[str]) -> Path:
    """Create ``root/.notes/`` holding one file per entry in ``names``."""
    notes = root / ".notes"
    notes.mkdir(parents=True, exist_ok=True)
    for name in names:
        (notes / name).write_text(
            f"---\nname: {Path(name).stem}\ndescription: seeded\n---\n",
            encoding="utf-8",
        )
    return notes


def _run(
    cwd: Path,
    payload: dict | str | None = None,
) -> tuple[int, str, dict | None]:
    """Run the hook in ``cwd`` with ``payload`` on stdin.

    ``payload`` may be a dict (encoded as JSON), a raw string (fed verbatim, for
    the malformed-input cases), or None (empty stdin).

    Returns (returncode, raw_stdout, parsed_json_or_None).
    """
    if payload is None:
        stdin = b""
    elif isinstance(payload, str):
        stdin = payload.encode()
    else:
        stdin = json.dumps(payload).encode()

    result = subprocess.run(
        [sys.executable, str(_HOOK_PATH)],
        cwd=str(cwd),
        input=stdin,
        capture_output=True,
        timeout=30,
    )
    raw = result.stdout.decode()
    parsed = json.loads(raw) if raw.strip() else None
    return result.returncode, raw, parsed


def _context(parsed: dict) -> str:
    """The additionalContext string from a parsed hook payload."""
    return parsed["hookSpecificOutput"]["additionalContext"]


def _payload(cwd: Path, source: str = "startup", **extra: object) -> dict:
    """A SessionStart stdin payload of the shape Claude Code sends."""
    base: dict = {
        "hook_event_name": "SessionStart",
        "session_id": "00000000-0000-4000-8000-000000000000",
        "transcript_path": "/home/someone/.claude/projects/x/abc.jsonl",
        "cwd": str(cwd),
        "source": source,
    }
    base.update(extra)
    return base


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A git repo with three notes at its root."""
    root = _init_repo(tmp_path / "project")
    _seed_notes(root, ["feedback_a.md", "reference_b.md", "project_c.md"])
    return root


class TestHookExists:
    def test_hook_file_is_present(self):
        assert _HOOK_PATH.is_file(), f"hook not found at {_HOOK_PATH}"


class TestSilenceWhenNothingToSay:
    def test_repo_without_notes_emits_no_output(self, tmp_path: Path):
        root = _init_repo(tmp_path / "bare")
        code, raw, _parsed = _run(root, _payload(root))
        assert code == 0
        assert raw.strip() == ""

    def test_non_git_directory_without_notes_emits_no_output(self, tmp_path: Path):
        plain = tmp_path / "plain"
        plain.mkdir()
        code, raw, _parsed = _run(plain, _payload(plain))
        assert code == 0
        assert raw.strip() == ""


class TestFactsSupplied:
    def test_emits_valid_session_start_json(self, repo: Path):
        code, _raw, parsed = _run(repo, _payload(repo))
        assert code == 0
        assert parsed is not None
        assert parsed["hookSpecificOutput"]["hookEventName"] == "SessionStart"

    def test_reports_the_resolved_notes_directory(self, repo: Path):
        _code, _raw, parsed = _run(repo, _payload(repo))
        assert f'dir="{repo / ".notes"}"' in _context(parsed)

    def test_reports_the_true_note_count(self, repo: Path):
        _code, _raw, parsed = _run(repo, _payload(repo))
        assert 'notes="3"' in _context(parsed)

    def test_note_count_ignores_non_markdown_files(self, tmp_path: Path):
        """A stray non-note file must not inflate the count the session is told."""
        root = _init_repo(tmp_path / "mixed")
        _seed_notes(root, ["feedback_a.md", "reference_b.md"])
        (root / ".notes" / "scratch.txt").write_text("noise\n", encoding="utf-8")
        (root / ".notes" / "notes.json").write_text("{}\n", encoding="utf-8")

        _code, _raw, parsed = _run(root, _payload(root))
        assert 'notes="2"' in _context(parsed)

    def test_surfaces_the_transcript_path_from_stdin(self, repo: Path):
        transcript = "/home/someone/.claude/projects/x/deadbeef.jsonl"
        _code, _raw, parsed = _run(
            repo, _payload(repo, transcript_path=transcript)
        )
        assert f'transcript="{transcript}"' in _context(parsed)

    def test_names_the_skill_that_does_the_work(self, repo: Path):
        """The hook is a pointer. The procedure lives in the skill, so the skill
        must be named or the pointer dangles."""
        _code, _raw, parsed = _run(repo, _payload(repo))
        assert "scanning-project-notes" in _context(parsed)

    def test_non_git_directory_with_notes_is_still_served(self, tmp_path: Path):
        """Global convention: in a non-git project `.notes/` sits at the project
        root. A git-only resolver would silently skip those projects."""
        plain = tmp_path / "plain"
        plain.mkdir()
        _seed_notes(plain, ["feedback_a.md"])
        code, _raw, parsed = _run(plain, _payload(plain))
        assert code == 0
        assert parsed is not None
        assert f'dir="{plain / ".notes"}"' in _context(parsed)


class TestWorktreeResolution:
    """The load-bearing case. `.notes/` lives at the main repo root."""

    def test_resolves_notes_at_main_root_when_cwd_is_a_worktree(
        self, repo: Path, tmp_path: Path
    ):
        worktree = tmp_path / "wt"
        _git(repo, "worktree", "add", str(worktree), "-b", "feature")
        assert not (worktree / ".notes").exists()

        code, _raw, parsed = _run(worktree, _payload(worktree))
        assert code == 0
        assert parsed is not None, "hook went silent inside a worktree"
        context = _context(parsed)
        assert f'dir="{repo / ".notes"}"' in context
        assert 'notes="3"' in context


class TestDispatchMarker:
    """``dispatch`` is the machine-readable half of the contract. The prose
    around it is expected to change; these assertions must not."""

    @pytest.mark.parametrize("source", ["compact", "resume", "clear", "fork"])
    def test_known_purpose_dispatches_immediately(self, repo: Path, source: str):
        """``fork`` is documented alongside the other four and was missed on the
        first pass. A session started with ``--fork-session`` inherits the
        parent's transcript, so its purpose is on record exactly as a resume's
        is; deferring there would wait for a first request that never comes."""
        _code, _raw, parsed = _run(repo, _payload(repo, source=source))
        assert 'dispatch="now"' in _context(parsed)

    def test_startup_defers_to_the_first_request(self, repo: Path):
        """At startup nothing has been asked yet, so there is no purpose to
        scan against."""
        _code, _raw, parsed = _run(repo, _payload(repo, source="startup"))
        assert 'dispatch="first-request"' in _context(parsed)

    def test_unknown_source_defers_rather_than_dispatching_blind(self, repo: Path):
        _code, _raw, parsed = _run(repo, _payload(repo, source="something-new"))
        assert 'dispatch="first-request"' in _context(parsed)

    def test_missing_source_defers(self, repo: Path):
        payload = _payload(repo)
        del payload["source"]
        _code, _raw, parsed = _run(repo, payload)
        assert 'dispatch="first-request"' in _context(parsed)


class TestOutputBudget:
    """Claude Code documents a 10,000-character limit on hook output strings.

    Documented, not observed here. The guard sits well below it so prose can
    grow without anyone having to remember the ceiling exists: a hook whose
    context is silently truncated would lose the closing advice first, which is
    the part warning against substituting a grep for the scan.
    """

    DOCUMENTED_LIMIT = 10_000
    GUARD = 4_000

    def test_context_stays_well_under_the_documented_limit(self, repo: Path):
        _code, _raw, parsed = _run(repo, _payload(repo))
        n = len(_context(parsed))
        assert n <= self.GUARD, (
            f"injected context is {n} chars against a {self.GUARD} guard "
            f"and a documented {self.DOCUMENTED_LIMIT} ceiling"
        )


class TestNeverBlocksSessionStart:
    def test_malformed_stdin_exits_zero(self, repo: Path):
        code, _raw, _parsed = _run(repo, "this is not json")
        assert code == 0

    def test_empty_stdin_exits_zero(self, repo: Path):
        code, _raw, _parsed = _run(repo, None)
        assert code == 0

    def test_json_that_is_not_an_object_exits_zero(self, repo: Path):
        code, _raw, _parsed = _run(repo, "[1, 2, 3]")
        assert code == 0

    def test_falls_back_to_process_cwd_when_payload_omits_it(self, repo: Path):
        """The harness supplies cwd, but the hook must not die without it."""
        payload = _payload(repo)
        del payload["cwd"]
        code, _raw, parsed = _run(repo, payload)
        assert code == 0
        assert parsed is not None
        assert f'dir="{repo / ".notes"}"' in _context(parsed)

    def test_absent_transcript_path_still_emits(self, repo: Path):
        payload = _payload(repo)
        del payload["transcript_path"]
        code, _raw, parsed = _run(repo, payload)
        assert code == 0
        assert parsed is not None
        assert f'dir="{repo / ".notes"}"' in _context(parsed)
