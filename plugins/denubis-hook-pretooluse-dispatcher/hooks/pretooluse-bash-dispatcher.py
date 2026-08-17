#!/usr/bin/env python3
"""PreToolUse:Bash dispatcher — discover, run, and merge hooks by priority.

Port of pretooluse-bash-dispatcher.sh. Two hook sources, run in priority order:

  1. Plugin convention files: hooks/pretooluse-bash.sh in *enabled* marketplace
     plugins. Priority from a "# dispatcher-priority: N" comment in the first
     five lines (default 50).
  2. Drop directory: ~/.claude/hooks/pretooluse-bash.d/ — a numeric filename
     prefix is the priority (default 50).

Each hook receives the original stdin. Outputs merge as:

  - deny wins immediately: that hook's output is emitted verbatim, processing
    stops.
  - permissionDecision "allow": preserved if any hook sets it.
  - updatedInput: last hook's value wins.
  - additionalContext / systemMessage: concatenated across hooks.

Discovery is cached in DISPATCHER_CACHE_FILE, keyed on the size+mtime of the
convention files, the drop-dir contents, and the settings file mtime.

All paths are overridable via DISPATCHER_DROP_DIR, DISPATCHER_MARKETPLACE_DIR,
DISPATCHER_SETTINGS_FILE, and DISPATCHER_CACHE_FILE (used by the test suite).

Pass --list to print the discovered hooks and cache state.

Note on concatenation: the bash original joined additionalContext/systemMessage
with a literal "\\n\\n" (an uninterpreted escape in a double-quoted string);
this port joins with real newlines, which was the evident intent. No test
pinned the separator.
"""

from __future__ import annotations  # keep PEP 604 annotations runtime-free on <3.10

import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CONVENTION_FILE = "pretooluse-bash.sh"
DEFAULT_PRIORITY = 50

_PRIORITY_RE = re.compile(r"#\s*dispatcher-priority:\s*(\d+)")
_LEADING_DIGITS_RE = re.compile(r"^(\d+)")


def _path_env(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value) if value else default


_HOME = Path(os.environ.get("HOME", ""))
DROP_DIR = _path_env("DISPATCHER_DROP_DIR", _HOME / ".claude/hooks/pretooluse-bash.d")
MARKETPLACE_DIR = _path_env(
    "DISPATCHER_MARKETPLACE_DIR", _HOME / ".claude/plugins/marketplaces"
)
SETTINGS_FILE = _path_env("DISPATCHER_SETTINGS_FILE", _HOME / ".claude/settings.json")
CACHE_FILE = _path_env(
    "DISPATCHER_CACHE_FILE", _HOME / ".claude/hooks/.pretooluse-bash-cache"
)

_MARKETPLACE_GLOB = f"*/plugins/*/hooks/{CONVENTION_FILE}"


# ── Discovery ──────────────────────────────────────────────────────────────


def _load_settings() -> dict | None:
    # Kept as two single-exception clauses, not a tuple: this hook runs via
    # `uv run python` in the user's CWD, whose project may pin Python < 3.14.
    # A tuple except would be rewritten to PEP 758 (3.14-only) form by ruff and
    # then SyntaxError there. Do not recombine.
    try:
        text = SETTINGS_FILE.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _is_enabled(settings: dict | None, key: str) -> bool:
    if not isinstance(settings, dict):
        return False
    enabled = settings.get("enabledPlugins", {})
    return isinstance(enabled, dict) and enabled.get(key) is True


def _read_priority(conv: Path) -> int:
    """First "# dispatcher-priority: N" in the first five lines, else default."""
    try:
        with conv.open(encoding="utf-8") as handle:
            for _ in range(5):
                line = handle.readline()
                if not line:
                    break
                match = _PRIORITY_RE.search(line)
                if match:
                    return int(match.group(1))
    except OSError:
        pass
    return DEFAULT_PRIORITY


def _discover_plugins() -> list[tuple[int, str, str, str]]:
    if not MARKETPLACE_DIR.is_dir():
        return []
    settings = _load_settings()
    settings_present = SETTINGS_FILE.exists()
    found = []
    for conv in sorted(MARKETPLACE_DIR.glob(_MARKETPLACE_GLOB)):
        if not (conv.is_file() and os.access(conv, os.X_OK)):
            continue
        rel = conv.relative_to(MARKETPLACE_DIR).parts
        # path layout: marketplace, then plugins, the plugin name, hooks, file
        key = f"{rel[2]}@{rel[0]}"
        if settings_present and not _is_enabled(settings, key):
            continue
        found.append((_read_priority(conv), "plugin", key, str(conv)))
    return found


def _discover_drop() -> list[tuple[int, str, str, str]]:
    if not DROP_DIR.is_dir():
        return []
    found = []
    for hook in sorted(DROP_DIR.iterdir()):
        if not (hook.is_file() and os.access(hook, os.X_OK)):
            continue
        match = _LEADING_DIGITS_RE.match(hook.name)
        priority = int(match.group(1)) if match else DEFAULT_PRIORITY
        found.append((priority, "drop", hook.name, str(hook)))
    return found


def discover_hooks() -> list[str]:
    """Return discovered hooks as "priority:source:name:path", priority-sorted."""
    entries = _discover_plugins() + _discover_drop()
    entries.sort(key=lambda entry: entry[0])  # stable: ties keep discovery order
    return [f"{prio}:{src}:{name}:{path}" for prio, src, name, path in entries]


# ── Caching ────────────────────────────────────────────────────────────────


def compute_cache_key() -> str:
    parts = []
    if MARKETPLACE_DIR.is_dir():
        for conv in sorted(MARKETPLACE_DIR.glob(_MARKETPLACE_GLOB)):
            try:
                stat = conv.stat()
            except OSError:
                continue
            parts.append(f"{conv}|{stat.st_size}|{stat.st_mtime_ns}")
    if DROP_DIR.is_dir():
        for hook in sorted(DROP_DIR.iterdir()):
            try:
                stat = hook.stat()
            except OSError:
                continue
            parts.append(f"{hook.name}|{stat.st_size}|{stat.st_mtime_ns}")
    with contextlib.suppress(OSError):
        parts.append(f"settings|{SETTINGS_FILE.stat().st_mtime_ns}")
    digest = hashlib.md5("\n".join(parts).encode(), usedforsecurity=False)
    return digest.hexdigest()


def _write_cache(key: str, entries: list[str]) -> None:
    body = "\n".join(entries)
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(f"HASH:{key}\n{body}\n", encoding="utf-8")
    except OSError:
        pass  # cache is best-effort; a write failure just means a rebuild later


def get_hook_list() -> list[str]:
    current = compute_cache_key()
    if CACHE_FILE.exists():
        try:
            lines = CACHE_FILE.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        if lines and lines[0].startswith("HASH:") and lines[0][5:] == current:
            return [line for line in lines[1:] if line]
    entries = discover_hooks()
    _write_cache(current, entries)
    return entries


# ── Dispatch ───────────────────────────────────────────────────────────────


def _run_one(path: str, stdin_bytes: bytes) -> str | None:
    try:
        proc = subprocess.run(
            [path],
            input=stdin_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return None
    out = proc.stdout.decode("utf-8", "replace").strip()
    return out or None


def _append(final: dict, field: str, value: object) -> None:
    if not value:
        return
    final[field] = value if not final[field] else f"{final[field]}\n\n{value}"


def _merge_hook_output(out: str, final: dict) -> bool:
    """Merge one hook's stdout into ``final``. Return True on deny (stop)."""
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return False
    if not isinstance(data, dict):
        return False
    hook_output = data.get("hookSpecificOutput") or {}
    if not isinstance(hook_output, dict):
        return False
    decision = hook_output.get("permissionDecision")
    if decision == "deny":
        final["deny_output"] = out
        return True
    if decision == "allow":
        final["decision"] = "allow"
        reason = hook_output.get("permissionDecisionReason")
        if reason:
            final["reason"] = reason
    updated = hook_output.get("updatedInput")
    if updated is not None:
        final["updated"] = updated
    _append(final, "context", hook_output.get("additionalContext"))
    _append(final, "system", data.get("systemMessage"))
    return False


def run_hooks(hook_list: list[str], stdin_bytes: bytes) -> dict:
    final = {
        "decision": "",
        "reason": "",
        "updated": None,
        "context": "",
        "system": "",
        "deny_output": None,
    }
    for line in hook_list:
        parts = line.split(":", 3)
        if len(parts) != 4:
            continue
        path = parts[3]
        candidate = Path(path)
        if not (candidate.is_file() and os.access(candidate, os.X_OK)):
            continue
        out = _run_one(path, stdin_bytes)
        if out is None:
            continue
        if _merge_hook_output(out, final):
            break
    return final


def build_output(final: dict) -> dict:
    hook_output: dict = {}
    if final["decision"]:
        hook_output["permissionDecision"] = final["decision"]
        if final["reason"]:
            hook_output["permissionDecisionReason"] = final["reason"]
    if final["updated"] is not None:
        hook_output["updatedInput"] = final["updated"]
    if final["context"]:
        hook_output["additionalContext"] = final["context"]
    # Claude Code validates hookSpecificOutput.hookEventName on EVERY
    # response, not only permission decisions — a context-only annotation
    # without it is rejected ("missing required field hookEventName").
    if hook_output:
        hook_output["hookEventName"] = "PreToolUse"
    output = {"hookSpecificOutput": hook_output}
    if final["system"]:
        output["systemMessage"] = final["system"]
    return output


def normalize_deny_output(out: str) -> str:
    """Give every deny both model-facing and transcript-facing reasons."""
    try:
        data = json.loads(out)
    except (json.JSONDecodeError, TypeError):
        return out
    if not isinstance(data, dict):
        return out

    hook_output = data.get("hookSpecificOutput")
    if not isinstance(hook_output, dict):
        return out

    hook_output["hookEventName"] = "PreToolUse"
    reason = hook_output.get("permissionDecisionReason")
    if not isinstance(reason, str) or not reason:
        candidates = (
            data.get("systemMessage"),
            hook_output.pop("systemMessage", None),
        )
        reason = next(
            (
                candidate
                for candidate in candidates
                if isinstance(candidate, str) and candidate
            ),
            "A PreToolUse hook denied this tool call without providing a reason.",
        )
        hook_output["permissionDecisionReason"] = reason
    if not isinstance(data.get("systemMessage"), str) or not data["systemMessage"]:
        data["systemMessage"] = reason
    return json.dumps(data)


# ── Diagnostics ────────────────────────────────────────────────────────────


def _print_list() -> None:
    print("Discovered hooks (execution order):")
    hook_list = get_hook_list()
    if not hook_list:
        print("  (none)")
    for line in hook_list:
        parts = line.split(":", 3)
        if len(parts) != 4:
            continue
        priority, source, name, path = parts
        print(f"  [{int(priority):02d}] {source}:{name}")
        print(f"       {path}")
    print()
    print("Sources:")
    print(f"  Marketplace: {MARKETPLACE_DIR}")
    print(f"  Drop dir:    {DROP_DIR}")
    print(f"  Settings:    {SETTINGS_FILE}")
    print(f"  Convention:  hooks/{CONVENTION_FILE}")
    print()
    if CACHE_FILE.exists():
        print(f"Cache: {CACHE_FILE}")
        try:
            lines = CACHE_FILE.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        first = lines[0] if lines else ""
        print(f"  Key: {first}")
    else:
        print("Cache: not yet created")


# ── Entry point ────────────────────────────────────────────────────────────


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] == "--list":
        _print_list()
        return 0

    hook_list = get_hook_list()
    if not hook_list:
        return 0

    final = run_hooks(hook_list, sys.stdin.buffer.read())
    if final["deny_output"] is not None:
        print(normalize_deny_output(final["deny_output"]))
        return 0
    if not (
        final["decision"]
        or final["updated"] is not None
        or final["context"]
        or final["system"]
    ):
        return 0
    print(json.dumps(build_output(final)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
