"""Resume prompts belong on disk, never in the index.

`RESUME*.md` is gitignored, so this only fires on a deliberate `git add -f`. Five
reached `main` before the rule existed; the verdict comes from `git ls-files`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_no_resume_prompt_is_tracked() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "-z", "--", "*RESUME*.md"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert not tracked, (
        "Resume prompts go stale faster than the plans they point at. Keep the "
        f"file, drop it from the index:\n  {tracked.replace(chr(0), chr(10) + '  ')}"
    )
