#!/usr/bin/env python3
"""
Cross-reference audit for skill-skills upstream sync (2026-04-17).

Walks the target skill directories and verifies that every path-form or
markdown-link cross-reference resolves to a file on disk.

Convention:
    - **Path-form references** (e.g., `./foo.md`, `docs/arch/bar.md:42`)
      MUST resolve. Path form requires a `/` in the backticked string.
    - **Markdown-link references** (e.g., `[text](./foo.md)`) MUST resolve.
    - **Bare backticked filenames** (e.g., `config.py`) are treated as
      prose vocabulary and NOT audited. Authors who want audit coverage
      for a same-directory reference should write `./filename.md`.
    - **denubis-<plugin>:<name>** invocations MUST resolve to one of:
      a skill directory (`plugins/<plugin>/skills/<name>/SKILL.md`),
      an agent file (`plugins/<plugin>/agents/<name>.md`), or a command
      file (`plugins/<plugin>/commands/<name>.md`). First match wins;
      skill takes precedence when a name exists in multiple locations.

This is the H1-minimal embedded script. The forthcoming common tool (see
docs/issues.md ISSUE-01) generalises this into a proper Typer-based CLI
with target-list arguments, architecture-presence check, and JSON output.
The convention and core regex semantics are intentionally compatible.

Exit codes:
  0 — all cross-references resolve (or --dump-matches requested)
  1 — at least one broken reference (details on stderr)
  2 — target directory missing

Usage:
  python3 phase_05_cross_ref_audit.py [--repo-root PATH] [--dump-matches]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_REPO_ROOT = Path("/home/brian/people/Brian/brian-ed3d-plugins")

TARGETS = [
    "plugins/denubis-extending-claude/skills/writing-skills",
    "plugins/denubis-extending-claude/skills/writing-claude-directives",
    "plugins/denubis-extending-claude/skills/testing-skills-with-subagents",
    "plugins/denubis-extending-claude/skills/epistemic-humility",
    "plugins/denubis-plan-and-execute/skills/impl-plan-write",
]

# Cross-skill invocations: `denubis-<plugin>:<skill>` with optional backticks.
XREF_RE = re.compile(r"`?(denubis-[a-z-]+):([a-z][a-z0-9-]*)`?")

# Path-form supporting-file reference. Backticked; must contain at least one
# `/`; ends in a known file extension; optional `:N` or `:N-M` line-range
# suffix. Bare filenames without `/` are intentionally NOT matched — they
# are treated as prose vocabulary. Authors who want audit coverage for a
# same-directory reference write `./filename.ext`. Teaching-material
# placeholders should use angle brackets (`<your-service>/auth.py`) so `<`
# as first character fails this character class and the placeholder is
# not audited.
PATH_REF_RE = re.compile(
    r"`([a-zA-Z0-9_.][a-zA-Z0-9_./-]*/[a-zA-Z0-9_.-]+\.(?:md|js|dot|py|sh|txt))(?::\d+(?:-\d+)?)?`"
)

# Markdown-link form: `](path/to/file.ext)` or `](path/to/file.ext#anchor)`.
# External URLs contain `:` which is outside the char class, so they do not
# match.
LINK_REF_RE = re.compile(
    r"\]\(([a-zA-Z0-9_.][a-zA-Z0-9_./-]*\.(?:md|js|dot|py|sh|txt))(?:#[^)]*)?\)"
)

# Conditional paths — references that are deliberately optional ("if the file
# exists, use it") and should not fail the audit when absent. Kept explicit
# and tiny; new entries require a review of whether the path is truly
# conditional-by-design or just a broken reference.
CONDITIONAL_PATHS: frozenset[str] = frozenset({
    ".ed3d/implementation-plan-guidance.md",  # impl-plan-write finalization hook — optional project-local guidance
})

# Verbatim external imports — files vendored byte-for-byte from an upstream
# source (e.g. Anthropic's skill-authoring guide, imported via obra). Their
# internal example links (FORMS.md, reference/finance.md, scripts/helper.py)
# reference files in a hypothetical *consumer* skill, not this repo: they are
# the upstream's illustrative content, not denubis cross-references. Editing
# them would destroy the "imported verbatim" property the design relies on, so
# these files are skipped when WALKED. References *to* them from other skills
# are still audited normally (the file exists on disk and resolves).
# Refinement added 2026-07-07 at Phase 5 execution: the as-designed script
# walked these and reported their upstream example links as broken (25 of the
# 32 first-run failures). See phase_05.md execution note.
VENDORED_VERBATIM: frozenset[str] = frozenset({
    "anthropic-best-practices.md",  # obra-vendored Anthropic guide; its example links are the upstream's
})


def resolve_xref(plugin: str, name: str, repo_root: Path) -> Path | None:
    """Resolve a `denubis-<plugin>:<name>` reference by trying each target
    class the ecosystem uses, in order: skills/, agents/, commands/.
    First hit wins. Returns None if no target resolves.
    """
    base = repo_root / "plugins" / plugin
    candidates = (
        base / "skills" / name / "SKILL.md",
        base / "agents" / f"{name}.md",
        base / "commands" / f"{name}.md",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def resolve_path_ref(
    ref: str, md_path: Path, repo_root: Path, link_relative: bool = False
) -> Path | None:
    """Resolve a supporting-file reference to a Path if it exists, else None.

    Markdown links (`link_relative=True`) are ALWAYS relative to the
    containing file, per standard markdown semantics — a `[x](notes.md)` in
    `dir/SKILL.md` points at `dir/notes.md`. Backticked path-form references
    follow the plan convention: `./`/`../` resolve against the md file's dir,
    everything else against repo root (so a bare `docs/x.md` is repo-root-
    relative and must be written `./docs/x.md` to be file-relative).

    The `link_relative` branch was added 2026-07-07 at Phase 5 execution: the
    as-designed script resolved link-refs against repo root, so bare-sibling
    markdown links (model-tier-notes.md <-> SKILL.md) that resolve fine for a
    human were reported broken (6 of the 32 first-run failures). See
    phase_05.md execution note.
    """
    if link_relative or ref.startswith(("./", "../")):
        candidate = (md_path.parent / ref).resolve()
    else:
        candidate = (repo_root / ref).resolve()
    return candidate if candidate.exists() else None


def audit_file(
    md_path: Path, repo_root: Path, dump_matches: bool = False
) -> list[tuple[int, str, str]]:
    results: list[tuple[int, str, str]] = []
    text = md_path.read_text()
    for line_num, line in enumerate(text.splitlines(), start=1):
        for match in XREF_RE.finditer(line):
            plugin, name = match.group(1), match.group(2)
            resolved = resolve_xref(plugin, name, repo_root)
            if dump_matches:
                status = "OK" if resolved else "BROKEN"
                results.append((line_num, "xref", f"[{status}] {plugin}:{name}"))
            elif resolved is None:
                results.append((line_num, "xref", f"{plugin}:{name} unresolved"))
        for regex, kind, link_rel in (
            (PATH_REF_RE, "path-ref", False),
            (LINK_REF_RE, "link-ref", True),
        ):
            for match in regex.finditer(line):
                ref = match.group(1)
                if ref in CONDITIONAL_PATHS:
                    continue  # conditional-by-design; not a failure when absent
                resolved = resolve_path_ref(ref, md_path, repo_root, link_relative=link_rel)
                if dump_matches:
                    status = "OK" if resolved else "BROKEN"
                    results.append((line_num, kind, f"[{status}] {ref}"))
                elif resolved is None:
                    results.append((line_num, kind, f"{ref} unresolved"))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cross-reference audit for skill-skills upstream sync."
    )
    parser.add_argument(
        "--repo-root",
        default=str(DEFAULT_REPO_ROOT),
        type=Path,
        help="Repository root (default: DEFAULT_REPO_ROOT constant)",
    )
    parser.add_argument(
        "--dump-matches",
        action="store_true",
        help="Print ALL detected references (OK and BROKEN) for spot-check; exit 0",
    )
    args = parser.parse_args()
    repo_root: Path = args.repo_root

    total_failures = 0
    for target in TARGETS:
        target_dir = repo_root / target
        if not target_dir.is_dir():
            print(f"FAIL: target directory missing: {target_dir}", file=sys.stderr)
            if not args.dump_matches:
                total_failures += 1
            continue
        for md_path in sorted(target_dir.glob("**/*.md")):
            if md_path.name in VENDORED_VERBATIM:
                continue  # verbatim external import; example links are the upstream's, not denubis cross-refs
            results = audit_file(md_path, repo_root, dump_matches=args.dump_matches)
            rel = md_path.relative_to(repo_root)
            for line_num, kind, message in results:
                if args.dump_matches:
                    print(f"MATCH [{kind}] {rel}:{line_num} — {message}")
                else:
                    print(f"FAIL [{kind}] {rel}:{line_num} — {message}", file=sys.stderr)
                    total_failures += 1

    if args.dump_matches:
        print("(dump-matches mode — no PASS/FAIL evaluation)", file=sys.stderr)
        return 0
    if total_failures == 0:
        print("PASS: all cross-references and supporting-file pointers resolve.")
        return 0
    print(f"TOTAL FAILURES: {total_failures}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
