"""Keep every test's git subprocesses out of the repository that launched pytest.

A commit hook runs this suite with git's repository variables exported (in a linked
worktree, ``GIT_DIR`` and ``GIT_INDEX_FILE`` among them). Tests that build a scratch
repository with ``git -C <tmp>`` still honour those variables, so on 2026-11-07 a
fixture's ``git init``, identity config and ``commit -m init`` landed in the calling
repository instead: a junk commit on the task branch, its index replaced, and
``core.bare = true`` with a ``Test`` identity in the shared config. Git names the
variables that bind a command to a repository; drop them before any test runs.
"""

import os
import subprocess


def _repository_local_git_variables() -> list[str]:
    return subprocess.run(
        ["git", "rev-parse", "--local-env-vars"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()


REPOSITORY_LOCAL_GIT_VARIABLES = _repository_local_git_variables()


def pytest_configure() -> None:
    for name in REPOSITORY_LOCAL_GIT_VARIABLES:
        os.environ.pop(name, None)
