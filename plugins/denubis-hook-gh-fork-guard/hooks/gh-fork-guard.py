#!/usr/bin/env python3
"""
PreToolUse hook that blocks gh CLI commands targeting repos other than the user's fork.

Prevents Claude from accidentally creating issues, PRs, or other actions on
upstream repositories when working in a forked codebase.

Policy: DENY any gh command that explicitly or implicitly targets a repo
other than the allowed one. The allowed repo is determined by:
1. ALLOWED_GH_REPO environment variable (if set), otherwise
2. git remote get-url origin (parsed to owner/repo form)
If neither is available, the hook does nothing.

Detection covers:
- --repo / -R flags with a non-fork owner/repo
- gh api paths containing repos/OWNER/REPO where OWNER/REPO is not the fork
- gh repo clone/fork/view with explicit non-fork targets
"""

from __future__ import annotations  # keep PEP 604 annotations runtime-free on <3.10

import json
import os
import re
import subprocess
import sys


def get_allowed_repo() -> str | None:
    """Get the allowed repo from env var or git remote origin."""
    env_repo = os.environ.get("ALLOWED_GH_REPO")
    if env_repo:
        return env_repo

    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            url = re.sub(r"\.git$", "", url)
            url = re.sub(r"^https?://github\.com/", "", url)
            url = re.sub(r"^git@github\.com:", "", url)
            if "/" in url:
                return url
    except Exception:  # noqa: S110 (best-effort: no remote → nothing to guard)
        pass

    return None


ALLOWED_REPO = get_allowed_repo()

# gh subcommands that interact with a specific repo
REPO_SUBCOMMANDS = {
    "issue",
    "pr",
    "release",
    "run",
    "workflow",
    "label",
    "milestone",
    "project",
    "variable",
    "secret",
    "cache",
    "ruleset",
    "deploy-key",
}


def extract_gh_commands(command: str) -> list[str]:
    """Extract individual gh commands from a compound shell command."""
    # Split on shell operators to find individual commands
    # This handles: cmd1 && cmd2, cmd1 || cmd2, cmd1 ; cmd2, cmd1 | cmd2
    parts = re.split(r"\s*(?:&&|\|\||[;|])\s*", command)
    gh_commands = []
    for raw_part in parts:
        part = raw_part.strip()
        if re.match(r"^gh\s+", part):
            gh_commands.append(part)
    return gh_commands


def check_repo_flag(command: str) -> str | None:
    """Check --repo or -R flag value. Returns the repo if non-allowed, else None."""
    # Match --repo=VALUE or --repo VALUE
    match = re.search(r"--repo[= ](\S+)", command)
    if match:
        repo = match.group(1)
        if not repo_is_allowed(repo):
            return repo

    # Match -R VALUE (but not -R as part of a longer flag)
    match = re.search(r"(?:^|\s)-R\s+(\S+)", command)
    if match:
        repo = match.group(1)
        if not repo_is_allowed(repo):
            return repo

    return None


def check_api_path(command: str) -> str | None:
    """Check gh api paths for non-fork repo references."""
    # Match: gh api repos/OWNER/REPO/...
    match = re.search(r"gh\s+api\s+(?:\"([^\"]+)\"|'([^']+)'|(\S+))", command)
    if match:
        path = match.group(1) or match.group(2) or match.group(3)
        repo_match = re.match(r"repos/([^/]+/[^/]+)", path)
        if repo_match:
            repo = repo_match.group(1)
            if not repo_is_allowed(repo):
                return repo
    return None


def check_explicit_repo_arg(command: str) -> str | None:
    """Check for explicit owner/repo as a positional argument to repo subcommands."""
    # gh repo clone OWNER/REPO, gh repo view OWNER/REPO, etc.
    match = re.search(r"gh\s+repo\s+\w+\s+(\S+)", command)
    if match:
        arg = match.group(1)
        if "/" in arg and not arg.startswith("-") and not repo_is_allowed(arg):
            return arg
    return None


def repo_is_allowed(repo: str) -> bool:
    """Check if a repo string matches the allowed fork."""
    # Normalize: strip quotes, .git suffix, URL prefixes
    repo = repo.strip("'\"")
    repo = re.sub(r"\.git$", "", repo)
    repo = re.sub(r"^https?://github\.com/", "", repo)
    repo = re.sub(r"^git@github\.com:", "", repo)

    # Compare case-insensitively
    return repo.lower() == ALLOWED_REPO.lower()


def deny(reason: str) -> dict:
    """Build a deny response."""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }
    if os.environ.get("DENUBIS_HOOK_PROVIDER") != "codex":
        output["systemMessage"] = reason
    return output


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    if ALLOWED_REPO is None:
        # No env var and not in a git repo with a remote — nothing to protect.
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    gh_commands = extract_gh_commands(command)
    if not gh_commands:
        sys.exit(0)

    # First pass: check ALL commands for deny-worthy violations.
    # A single bad command in a compound expression blocks the entire thing.
    for gh_cmd in gh_commands:
        # Check --repo / -R flags
        bad_repo = check_repo_flag(gh_cmd)
        if bad_repo:
            print(
                json.dumps(
                    deny(
                        f"BLOCKED: gh command targets '{bad_repo}' which is"
                        f" not the allowed fork '{ALLOWED_REPO}'."
                        f" You may ONLY interact with {ALLOWED_REPO}. "
                        f"Use --repo {ALLOWED_REPO} or remove the --repo flag."
                    )
                )
            )
            sys.exit(0)

        # Check gh api paths
        bad_repo = check_api_path(gh_cmd)
        if bad_repo:
            print(
                json.dumps(
                    deny(
                        f"BLOCKED: gh api targets '{bad_repo}' which is not the"
                        f" allowed fork '{ALLOWED_REPO}'. Rewrite the API path to use "
                        f"repos/{ALLOWED_REPO}/... instead."
                    )
                )
            )
            sys.exit(0)

        # Check explicit repo arguments to gh repo subcommands
        bad_repo = check_explicit_repo_arg(gh_cmd)
        if bad_repo:
            print(
                json.dumps(
                    deny(
                        f"BLOCKED: gh command targets '{bad_repo}' which is not the"
                        f" allowed fork '{ALLOWED_REPO}'. You may ONLY interact with"
                        f" {ALLOWED_REPO}."
                    )
                )
            )
            sys.exit(0)

    # Second pass: no violations found. Emit advisory context if any
    # repo-interacting commands are present without explicit --repo.
    for gh_cmd in gh_commands:
        tokens = gh_cmd.split()
        if len(tokens) >= 2 and tokens[1] in REPO_SUBCOMMANDS:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": (
                        f"FORK POLICY: This gh command will use the default repo. "
                        f"Verify that `gh repo set-default` points to {ALLOWED_REPO}. "
                        f"You may ONLY interact with {ALLOWED_REPO}, never upstream."
                    ),
                }
            }
            print(json.dumps(output))
            sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
