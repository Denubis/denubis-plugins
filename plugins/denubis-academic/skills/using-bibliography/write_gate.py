"""The preview/apply gate every Zotero write helper shares (0.19).

Design of 2026-10-12, Contracts 2 and 3: no flag means preview, `--apply`
means write, and apply refuses when the state the preview showed is no longer
what Zotero holds. What carries that state differs by operation class:

  modify    an existing item or collection: `--expect-version N`, the version
            the preview read; the write itself carries If-Unmodified-Since-Version
  create    a new item or collection: `--expect-collection KEY`,
            `--expect-parent KEY`, `--expect-library ID`, the keys the preview
            resolved by name; apply re-resolves and compares
  register  a BBT auto-export: `--expect-collection KEY`

There is no universal `--expect-version`; it exists only in the modify class.
The preview prints the complete apply command so the user copies it rather
than reconstructing it. The final line separates `accepted` (Zotero or BBT
took the request) from `verified` (the effect was read back); a helper that
cannot verify says so and exits non-zero. It never prints a bare success.
"""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    import argparse
    from collections.abc import Iterable

OperationClass = Literal["modify", "create", "register"]

# Expected-state flags per class, in the order the apply command prints them.
EXPECTATIONS: dict[str, tuple[str, ...]] = {
    "modify": ("--expect-version",),
    "create": ("--expect-collection", "--expect-parent", "--expect-library"),
    "register": ("--expect-collection",),
}

_HELP = {
    "--expect-version": "the object version the preview showed; apply refuses "
    "with `changed since preview` if Zotero now holds another",
    "--expect-collection": "the collection key the preview resolved; apply "
    "re-resolves the name and refuses with `target changed` on a difference",
    "--expect-parent": "the parent collection key the preview resolved",
    "--expect-library": "the zotero-api-plus libraryID the preview resolved",
}


def _dest(flag: str) -> str:
    return flag.lstrip("-").replace("-", "_")


def _state_name(flag: str) -> str:
    return flag.removeprefix("--expect-")


def add_gate_arguments(
    parser: argparse.ArgumentParser, *classes: OperationClass
) -> None:
    """Add `--apply` and the expected-state flags of the given classes.

    A helper with verbs of more than one class (collection.py) passes them
    all and rejects the foreign ones per verb with foreign_expectations.
    """
    parser.add_argument(
        "--apply",
        action="store_true",
        help="perform the previewed write. Without it nothing is written.",
    )
    seen: list[str] = []
    for cls in classes:
        for flag in EXPECTATIONS[cls]:
            if flag in seen:
                continue
            seen.append(flag)
            kwargs: dict = {"help": _HELP[flag]}
            if flag == "--expect-version":
                kwargs["type"] = int
                kwargs["metavar"] = "N"
            else:
                kwargs["metavar"] = "KEY" if flag != "--expect-library" else "ID"
            parser.add_argument(flag, **kwargs)


def foreign_expectations(args: argparse.Namespace, cls: OperationClass) -> list[str]:
    """Expected-state flags that were passed but belong to another class.

    A create or register verb never takes `--expect-version` (there is no
    prior version to protect); a modify verb never takes the create keys.
    """
    own = set(EXPECTATIONS[cls])
    return [
        flag
        for other, flags in EXPECTATIONS.items()
        if other != cls
        for flag in flags
        if flag not in own and getattr(args, _dest(flag), None) is not None
    ]


def missing_expectations(
    args: argparse.Namespace, required: Iterable[str]
) -> list[str]:
    """The required expected-state flags an `--apply` run did not pass.

    Empty for a preview. The caller decides what is required: a create
    without a named parent does not need `--expect-parent`.
    """
    if not getattr(args, "apply", False):
        return []
    return [flag for flag in required if getattr(args, _dest(flag), None) is None]


def expected_from_args(args: argparse.Namespace, cls: OperationClass) -> dict:
    """The expected state the flags carry, keyed by state name (`version`,
    `collection`, `parent`, `library`); absent flags are omitted."""
    out = {}
    for flag in EXPECTATIONS[cls]:
        value = getattr(args, _dest(flag), None)
        if value is not None:
            out[_state_name(flag)] = value
    return out


def state_refusal(expected: dict, current: dict) -> str | None:
    """The refusal text when `current` differs from `expected`, else None.

    Values are compared as strings so a version typed on the command line
    equals the integer Zotero returns. Only keys present in `expected` are
    compared; the first difference is reported.
    """
    for name, want in expected.items():
        have = current.get(name)
        if str(have) != str(want):
            if name == "version":
                return f"changed since preview: version is {have}, expected {want}"
            return f"target changed: {name} is {have}, expected {want}"
    return None


def format_apply_command(argv: list[str], expected: dict) -> str:
    """The exact command that applies the previewed change.

    Repeats the invocation (any earlier `--apply` or `--expect-*` dropped),
    then `--apply` and one `--expect-<state> value` per expected state, in
    `expected`'s order. Quoted for a POSIX shell.
    """
    kept: list[str] = []
    skip_next = False
    for arg in argv:
        if skip_next:
            skip_next = False
            continue
        if arg == "--apply":
            continue
        if arg.startswith("--expect-"):
            skip_next = "=" not in arg
            continue
        kept.append(arg)
    tail = ["--apply"]
    for name, value in expected.items():
        tail += [f"--expect-{name}", str(value)]
    return "uv run " + shlex.join([*kept, *tail])


def report(
    *, accepted: bool, verified: bool | None, reason: str | None = None
) -> tuple[str, int]:
    """The helper's final line and exit code (0 only for accepted AND verified).

    accepted and verified          -> `accepted; verified`, 0
    accepted, not verified         -> `accepted; not verified: <reason>`, 1
    not accepted                   -> `not accepted: <reason>`, 1
    """
    if accepted and verified:
        return "accepted; verified", 0
    if accepted:
        return f"accepted; not verified: {reason or 'effect not observed'}", 1
    return f"not accepted: {reason or 'request refused'}", 1
