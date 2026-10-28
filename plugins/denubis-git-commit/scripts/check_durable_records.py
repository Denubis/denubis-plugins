#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = []
# [tool.ty.environment]
# python-version = "3.14"
# ///
"""Check citations and memory records before committing.

Citation heuristics are deliberately lexical, not a complete Markdown/shell parser:
inline Markdown links (including angle-wrapped or percent-encoded destinations
and one level of balanced parentheses), reference definitions,
backticked paths containing '/', and plausible bare paths count. A whole code span
that names an existing path is kept intact, including spaces, before falling back
to whitespace-delimited command tokens. Comma-separated brace sets such as
sources/{docx,pdf,email} expand into separately checked alternatives.
Bare slash tokens need ./, ../, ~/, /, a tracked repository top-level name,
an ignored-but-present top-level name, or a file extension in the last segment.
Links and code spans retain the broader rule. A single directory segment such as
people/ follows the same split: prose when bare unless that top-level name is tracked
or present and ignored, and a directory citation in a link or code span, the form
finding aids use for registers. Conventional branch prefixes are
defined once in BRANCH_PREFIXES; slash tokens using those prefixes are prose only
when they name nothing tracked or present at either relative base and do not end in
a letter-led file extension, so a moved docs/eval.py stays ABSENT while a dotted
release/1.5.0 stays prose. Tracked paths,
including deleted targets, and present ignored paths keep their citation checks.
Links may name a sibling file without a slash. Link spans and code spans are removed
before looking for bare tokens; repeated references on one line are emitted once.
Trailing prose punctuation, local #fragments, ::node, :identifier, :line[:column]
and :start-end suffixes are removed for resolution. scheme:// URLs,
SCP-style Git remotes, mailto:, ccchat:, claude:, protocol-relative URLs,
anchor-only targets, leading '-' shell options, and tokens containing glob
metacharacters '*?[]' are excluded. A placeholder token is never a citation: one
containing a $NAME or ${...} shell variable, a '…' anywhere, a path segment of three
or more dots, or an angle-bracket <...> placeholder. Each extracted token, reference
definitions included, is tested before trailing punctuation is stripped, so src/...
is a placeholder rather than a citation of src/, while src/a.md... still cites
src/a.md. Bare prose treats '<' and '>' as token boundaries (inline HTML), so an
angle placeholder never joins a bare token and the bare fragments beside it are
judged alone. Named-user '~user' paths are
external and excluded without home-directory expansion; bare '~' and '~/' paths
retain their normal expansion. A reference that fails path normalisation is
skipped with one source-located WARN on stderr. A lone '/' and a single
slash-prefixed name without a dot are not citations. Quoted slash prose can still be
reported; links/code spans deliberately keep their broader contract.
Other leading word: prefixes are stripped before resolving local paths.

References are tried from the document directory and repository root. An existing,
nonignored resolution is sufficient. Worktree and exchange segments are prohibited
even when present or tracked, with WORKTREE taking precedence over EXCHANGE and then
IGNORED/ABSENT. Absolute paths under any registered linked checkout from Git's
NUL-delimited worktree list are WORKTREE, even outside this checkout; the main
checkout is excluded from that set. Relative citations local to the current linked
checkout retain their normal checks. Outside-checkout resolutions are not repository
citations, except for registered worktrees and worktree/exchange segments.
External alternatives do not hide a defective internal relative resolution.
Both lexical and symlink-resolved paths are checked. Transcript
paths under ~/.claude/projects/ or ~/.codex/sessions/ (including absolute paths under
the home directory) are accepted lexically, without opening or statting the raw record.

Selection uses CLI locations before explicitly labelled finding aids, then conventional
defaults. Finding aids come from CLAUDE.md, or root AGENTS.md when CLAUDE.md is absent
or contains only @AGENTS.md. Every standalone @file line in the selected instruction
file is expanded one level, relative to the repository root; missing files and paths
outside the repository (including symlinks) are skipped. Default registers are
docs/architecture/decisions, docs/decisions, and .notes/decisions. A Markdown file
can serve as a one-file register; missing default registers are skipped silently.
The .notes locations and open-questions queue belong
to the main checkout; other selected paths belong to this checkout. Notes are discovered
from the filesystem, including ignored documents, excluding .notes/local-mail/. --staged
adds tracked Markdown paths from the index diff only under docs/, .notes/, or configured
register/records locations; document contents are read from the working checkout.
Default selection adds whole decision registers and the open-questions file. --all
also audits whole records locations (by default .notes and docs/architecture), plus
every tracked or nonignored untracked Markdown file directly under docs/ and
docs/decisions/. Register and records directories are recursive; these two additional
docs selections are not. Non-notes locations select tracked and nonignored untracked
Markdown; notes include ignored Markdown but exclude .notes/local-mail/.
Naming a record never selects its siblings.
One citation rule applies to every selected document. ABSENT is always advisory: it is
reported with its prefix but never affects the exit status. WORKTREE, EXCHANGE and
IGNORED block, except on Markdown blockquote lines (first non-space character '>'),
where every citation kind is advisory and keeps its prefix.
The summary counts all citations and separately counts all advisory citations as
advisory. --strict also blocks wording/ticket findings, but does not promote advisory
citation findings.
Wording and ticket checks omit fenced code, marked blockquotes, and lazy quoted
paragraph continuations. Status/progress heading detection is a case-insensitive
word heuristic (status, progress, answered, resolved, closed, completed, done, parked,
state of), so those advisory findings require human interpretation.
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote

if TYPE_CHECKING:
    from collections.abc import Iterator

DEFAULT_REGISTERS = (
    "docs/architecture/decisions",
    "docs/decisions",
    ".notes/decisions",
)
BRANCH_PREFIXES = frozenset(
    {
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
    }
)
LINK = re.compile(
    r"\[[^\]]*\]\(\s*(?:<([^>]+)>|((?:[^\s()]+|\([^()\s]*\))+))"
    r"(?:\s+[^)]*)?\)"
)
LINK_DEFINITION = re.compile(r"^ {0,3}\[[^\]]+\]:\s*(?:<([^>]+)>|(\S+))")
CODE = re.compile(r"`+([^`]+)`+")
TOKEN = re.compile(r"[^\s`<>()\"']+")
BRACE_SET = re.compile(r"\{([^{}]*,[^{}]*)\}")
FILE_EXTENSION = re.compile(r"\.[A-Za-z][A-Za-z0-9]*$")
PLACEHOLDER = re.compile(r"\$(?:\{|[A-Za-z_])|…|(?:^|/)\.{3,}(?:/|$)|<[^<>]+>")
URL_SCHEME = r"(?:[a-zA-Z][a-zA-Z0-9+.-]*://|(?:mailto|ccchat|claude):)"
SCHEME = re.compile(
    rf"^(?:{URL_SCHEME}|[A-Za-z0-9._-]+@[A-Za-z0-9._-]+:)", re.IGNORECASE
)
BARE_URL = re.compile(rf"(?<![\w/.~%-])(?:{URL_SCHEME}|//)[^\s<>`\"']+", re.IGNORECASE)
TRANSITIONAL = re.compile(
    r"\b(?:until|not\s+yet|still\s+open|still\s+to\s+be|for\s+now|"
    r"to\s+be\s+proven|currently|pending|TODO|WIP)\b",
    re.IGNORECASE,
)
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)(?:\s+#+)?\s*$")
STATUS = re.compile(
    r"\b(?:status|progress|answered|resolved|closed|completed|done|parked|state of)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Finding:
    """One observable defect in a selected record."""

    kind: str
    path: str
    line: int
    reference: str
    advisory: bool = False

    def render(self) -> str:
        """Return the CLI's line-oriented format."""
        return f"{self.kind} {self.path}:{self.line} {self.reference}"


@dataclass(frozen=True)
class Options:
    """CLI selection of records, with conventional paths as fallbacks."""

    paths: list[str]
    registers: list[str] | None
    records: list[str] | None
    staged: bool
    strict: bool
    audit_all: bool


@dataclass(frozen=True)
class Document:
    """A record and the checkout that supplies its relative references."""

    root: Path
    path: Path
    decision: bool


def arguments() -> Options:
    """Parse repo-relative locations; repeated options replace each default set."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "paths", nargs="*", help="additional Markdown files, relative to repo root"
    )
    parser.add_argument(
        "--register", action="append", help="decision register (repeatable)"
    )
    parser.add_argument(
        "--records", action="append", help="notes/architecture location (repeatable)"
    )
    parser.add_argument(
        "--staged", action="store_true", help="also check staged Markdown paths"
    )
    parser.add_argument(
        "--strict", action="store_true", help="also fail for wording/ticket findings"
    )
    parser.add_argument(
        "--all",
        dest="audit_all",
        action="store_true",
        help="audit all records locations",
    )
    args = parser.parse_args()
    return Options(
        args.paths,
        args.register,
        args.records,
        args.staged,
        args.strict,
        args.audit_all,
    )


def finding_aid_lines(root: Path) -> Iterator[tuple[int, str]]:
    """Read root instructions and their direct, repository-contained includes."""
    instructions = root / "CLAUDE.md"
    if not instructions.is_file():
        instructions = root / "AGENTS.md"
    instructions = instructions.resolve()
    if not instructions.is_relative_to(root) or not instructions.is_file():
        return
    text = instructions.read_text(encoding="utf-8")
    if instructions.name == "CLAUDE.md" and text.strip() == "@AGENTS.md":
        instructions = (root / "AGENTS.md").resolve()
        if not instructions.is_relative_to(root) or not instructions.is_file():
            return
        text = instructions.read_text(encoding="utf-8")
    yield from prose_lines(text)
    for line in text.splitlines():
        include = re.fullmatch(r"\s*@(\S+)\s*", line)
        if include is None:
            continue
        path = (root / include[1]).resolve()
        if path.is_relative_to(root) and path.is_file():
            yield from prose_lines(path.read_text(encoding="utf-8"))


def finding_aids(root: Path) -> tuple[list[str], list[str]]:
    """Read explicit, labelled local paths, without executing project directives."""
    registers: list[str] = []
    records: list[str] = []
    targets = {
        "design decisions": registers,
        "decision register": registers,
        "architecture decisions": registers,
        "project notes": records,
        "notes": records,
        "architecture": records,
    }
    for _, line in finding_aid_lines(root):
        label, separator, _ = line.partition(":")
        if not separator:
            continue
        label = label.lstrip(" -*").casefold()
        target = targets.get(label)
        if target is not None:
            target.extend(
                path for path in references(line, root) if reference_path(path)
            )
    return registers, records


def git(root: Path, *arguments: str, accepted: tuple[int, ...] = (0,)) -> str:
    """Run Git, preserving fatal failures rather than treating them as no matches."""
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in accepted:
        raise RuntimeError(result.stderr.strip() or f"git exited {result.returncode}")
    return result.stdout


@cache
def worktree_roots(root: Path) -> tuple[Path, ...]:
    """Read Git's NUL-delimited checkout paths, with the main checkout first."""
    roots = tuple(
        Path(field.removeprefix("worktree ")).resolve()
        for field in git(root, "worktree", "list", "--porcelain", "-z").split("\0")
        if field.startswith("worktree ")
    )
    if not roots:
        raise RuntimeError("Git did not identify the main checkout")
    return roots


def repository_roots() -> tuple[Path, Path]:
    """Resolve this checkout and its main checkout via Git's common directory."""
    root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").strip()).resolve()
    common = Path(
        git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    )
    return root, worktree_roots(common)[0]


def markdown(path: Path) -> bool:
    """Recognise the two conventional Markdown extensions, case-insensitively."""
    return path.suffix.lower() in {".md", ".markdown"}


def contained_path(root: Path, value: str) -> Path:
    """Reject a selection escaping the checkout, including symlinks outside it."""
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"record path is outside repository: {value}")
    return path


def selected_documents(root: Path, main_root: Path, options: Options) -> list[Document]:
    """Always check registers/queue; add named/staged files and optional full audit."""
    aid_registers, aid_records = finding_aids(root)
    register_values = options.registers or aid_registers or list(DEFAULT_REGISTERS)
    record_values = options.records or aid_records or [".notes", "docs/architecture"]
    registers = [Path(value) for value in register_values]
    selections: dict[Path, Document] = {}
    locations = [*register_values, *(record_values if options.audit_all else [])]
    for location in dict.fromkeys(locations):
        notes = Path(location).parts[:1] == (".notes",)
        owner = main_root if notes else root
        directory = contained_path(owner, location)
        discover = filesystem_notes if notes else tracked_documents
        for document in discover(owner, directory, registers):
            selections[document.path] = document
    additional = direct_record_documents(root, registers) if options.audit_all else []
    additional.extend(
        extra_documents(
            root,
            main_root,
            registers,
            [Path(value) for value in record_values],
            options,
        )
    )
    for document in additional:
        selections.setdefault(document.path, document)
    queue = main_root / ".notes/project_open-questions.md"
    if queue.is_file():
        queue = contained_path(main_root, str(queue))
        selections.setdefault(queue, Document(main_root, queue, False))
    return sorted(selections.values(), key=lambda document: str(document.path))


def tracked_documents(
    root: Path, directory: Path, registers: list[Path], *, direct: bool = False
) -> list[Document]:
    """Select tracked and nonignored untracked Markdown, optionally nonrecursively."""
    documents: list[Document] = []
    for value in git(
        root,
        "ls-files",
        "-z",
        "--cached",
        "--others",
        "--exclude-standard",
        "--",
        str(directory),
    ).split("\0"):
        if value and markdown(Path(value)):
            if direct and (root / value).parent != directory:
                continue
            path = contained_path(root, value)
            decision = any(
                path.is_relative_to(root / register) for register in registers
            )
            documents.append(Document(root, path, decision))
    return documents


def direct_record_documents(root: Path, registers: list[Path]) -> list[Document]:
    """Add tracked/nonignored untracked Markdown directly under docs locations."""
    return [
        document
        for location in ("docs", "docs/decisions")
        for document in tracked_documents(root, root / location, registers, direct=True)
    ]


def filesystem_notes(
    root: Path, directory: Path, registers: list[Path]
) -> list[Document]:
    """Read main-checkout note paths regardless of ignore rules, excluding mail."""
    mail = root / ".notes/local-mail"
    paths = [directory] if directory.is_file() else directory.rglob("*")
    documents: list[Document] = []
    for path in paths:
        if not markdown(path) or path.is_relative_to(mail) or not path.is_file():
            continue
        resolved = contained_path(root, str(path))
        if not resolved.is_relative_to(mail):
            decision = any(
                resolved.is_relative_to(root / register) for register in registers
            )
            documents.append(Document(root, resolved, decision))
    return documents


def extra_documents(
    root: Path,
    main_root: Path,
    registers: list[Path],
    records: list[Path],
    options: Options,
) -> list[Document]:
    """Add explicitly requested files and staged additions/modifications/renames."""
    extra = list(options.paths)
    if options.staged:
        locations = [Path("docs"), Path(".notes"), *registers, *records]
        extra.extend(
            value
            for value in git(
                root, "diff", "--cached", "--name-only", "--diff-filter=ACMRT", "-z"
            ).split("\0")
            if value
            and markdown(Path(value))
            and any(
                (root / value).is_relative_to(root / location) for location in locations
            )
        )
    documents: list[Document] = []
    for value in extra:
        owner = main_root if Path(value).parts[:1] == (".notes",) else root
        path = contained_path(owner, value)
        if not markdown(path) or not path.is_file():
            raise ValueError(f"expected an existing Markdown file: {value}")
        decision = any(path.is_relative_to(owner / register) for register in registers)
        documents.append(Document(owner, path, decision))
    return documents


def bare_reference(reference: str, root: Path) -> bool:
    """Require a path prefix, repository top-level name, or final extension in prose."""
    path = reference_path(reference.rstrip(".,;!"))
    if path is None or "/" not in path or path == "/":
        return False
    top_level = root / path.split("/", 1)[0]
    return (
        path.startswith(("./", "../", "~/", "/"))
        or bool(Path(path).suffix)
        or bool(git(root, "ls-files", "-z", "--", str(top_level)))
        or (
            top_level.exists()
            and bool(git(root, "check-ignore", "--", str(top_level), accepted=(0, 1)))
        )
    )


def code_references(span: str, root: Path, directory: Path) -> list[str]:
    """Prefer an existing whole code-span path before splitting command tokens."""
    tokens = [token for token in span.split() if "/" in token]
    if len(span.split()) <= 1 or not tokens:
        return tokens
    path = reference_path(span.rstrip(".,;!"))
    if path is None or (path.startswith("~") and not path.startswith("~/")):
        return tokens
    try:
        raw = Path(path).expanduser()
        if any((base / raw).exists() for base in (root, directory)):
            return [span]
    except OSError, RuntimeError, ValueError:
        return [span]
    return tokens


def expand_braces(reference: str) -> list[str]:
    """Expand comma-separated brace alternatives, including successive segments."""
    match = BRACE_SET.search(reference)
    if match is None:
        return [reference]
    return [
        expanded
        for alternative in match[1].split(",")
        for expanded in expand_braces(
            reference[: match.start()] + alternative + reference[match.end() :]
        )
    ]


def references(line: str, root: Path, *, directory: Path | None = None) -> list[str]:
    """Extract destinations once; do not reinterpret excluded links as bare paths."""
    definition = LINK_DEFINITION.match(line)
    if definition:
        return [
            expanded
            for expanded in expand_braces(definition[1] or definition[2])
            if not PLACEHOLDER.search(expanded)
        ]
    found = [match[1] or match[2] for match in LINK.finditer(line)]
    remainder = LINK.sub(" ", line)
    for match in CODE.finditer(remainder):
        found.extend(code_references(match[1], root, directory or root))
    remainder = CODE.sub(" ", remainder)
    remainder = BARE_URL.sub(" ", remainder)
    found.extend(
        token for token in TOKEN.findall(remainder) if bare_reference(token, root)
    )
    return list(
        dict.fromkeys(
            expanded.rstrip(".,;!")
            for reference in found
            for expanded in expand_braces(reference)
            if not PLACEHOLDER.search(expanded)
        )
    )


def reference_path(reference: str) -> str | None:
    """Remove locators and exclude non-file citations before filesystem operations."""
    reference = reference.split("::", 1)[0]
    if reference.startswith(("#", "-", "//")) or SCHEME.match(reference):
        return None
    if any(character in reference for character in "*?[]"):
        return None
    path = unquote(
        re.sub(
            r":(?:\d+(?:-\d+|:\d+)?|[A-Za-z_][A-Za-z0-9_]*)$",
            "",
            reference.split("#", 1)[0],
        )
    )
    path = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", "", path, count=1)
    if not prohibited_segment(Path(path)) and (
        path == "/" or re.fullmatch(r"/[^/.]+", path)
    ):
        return None
    transcript_roots = (".claude/projects/", ".codex/sessions/")
    prefixes = tuple(
        prefix + transcript
        for prefix in ("~/", str(Path.home()) + "/")
        for transcript in transcript_roots
    )
    return None if path.startswith(prefixes) else path


def prohibited_segment(path: Path) -> str | None:
    """Give the specific ephemeral-directory classifications precedence."""
    if ".worktrees" in path.parts:
        return "WORKTREE"
    if "codex-prompts" in path.parts:
        return "EXCHANGE"
    return None


def registered_worktree(root: Path, candidate: Path) -> bool:
    """Match path components against linked checkouts, lexically and via symlinks."""
    resolved = candidate.resolve()
    return any(
        candidate.is_relative_to(worktree) or resolved.is_relative_to(worktree)
        for worktree in worktree_roots(root)[1:]
    )


def candidate_kind(root: Path, candidate: Path) -> str | None:
    """Check a candidate's durable location without reading the referenced file."""
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root) and registered_worktree(root, candidate):
        return "WORKTREE"
    special = prohibited_segment(
        candidate.relative_to(root, walk_up=True)
    ) or prohibited_segment(resolved.relative_to(root, walk_up=True))
    if special:
        return special
    if not resolved.is_relative_to(root):
        return "EXTERNAL"
    if not resolved.exists():
        return "ABSENT"
    ignored = git(root, "check-ignore", "--", str(resolved), accepted=(0, 1))
    return "IGNORED" if ignored else None


def untracked_branch_name(root: Path, path: str, candidates: list[Path]) -> bool:
    """Recognise conventional branch prefixes only when no candidate names a path.

    A last segment ending in a letter-led file extension names a file, not a branch,
    so docs/eval.py moved out of docs/ stays ABSENT while release/1.5.0 stays prose.
    """
    return (
        "/" in path
        and path.split("/", 1)[0] in BRANCH_PREFIXES
        and not FILE_EXTENSION.search(path)
        and not any(
            candidate.exists()
            or candidate.is_symlink()
            or git(root, "ls-files", "-z", "--", str(candidate))
            for candidate in candidates
        )
    )


def classify_reference(root: Path, document: Path, reference: str) -> str | None:
    """Try both allowed relative bases; raw transcript citations bypass all I/O."""
    path = reference_path(reference)
    if path is None:
        return None
    if path.startswith("~") and path != "~" and not path.startswith("~/"):
        return "EXTERNAL"
    raw = Path(path).expanduser()
    if raw.is_absolute() and registered_worktree(root, raw):
        return "WORKTREE"
    special = prohibited_segment(raw)
    if special:
        return special
    candidates = [root / raw, document.parent / raw]
    kinds = [
        kind
        for candidate in candidates
        if (kind := candidate_kind(root, candidate)) != "EXTERNAL"
    ]
    if (
        not kinds
        or None in kinds
        or (set(kinds) == {"ABSENT"} and untracked_branch_name(root, path, candidates))
    ):
        return None
    return next(
        kind for kind in ("WORKTREE", "EXCHANGE", "IGNORED", "ABSENT") if kind in kinds
    )


def citation_findings(root: Path, document: Path, text: str) -> list[Finding]:
    """Identify each defective path citation; ABSENT and quoted lines are advisory."""
    found: list[Finding] = []
    for number, line in enumerate(text.splitlines(), 1):
        for reference in references(line, root, directory=document.parent):
            try:
                kind = classify_reference(root, document, reference)
            except Exception:
                print(
                    f"WARN {document.relative_to(root)}:{number} "
                    f"unreadable reference {reference}",
                    file=sys.stderr,
                )
                continue
            if kind and kind != "EXTERNAL":
                found.append(
                    Finding(
                        kind,
                        str(document.relative_to(root)),
                        number,
                        reference,
                        advisory=kind == "ABSENT" or line.lstrip().startswith(">"),
                    )
                )
    return found


def unquoted_lines(text: str) -> Iterator[tuple[int, str]]:
    """Omit quotations and lazy paragraph continuations up to a block boundary."""
    quoted = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith(">"):
            quoted = True
            continue
        if (
            quoted
            and line.strip()
            and not HEADING.match(line)
            and not FENCE.match(line)
        ):
            continue
        quoted = False
        yield number, line


def prose_lines(text: str) -> Iterator[tuple[int, str]]:
    """Keep source line numbers while excluding fences and human quotations."""
    fence = ""
    for number, line in unquoted_lines(text):
        marker = FENCE.match(line)
        if fence:
            if (
                marker
                and marker[1][0] == fence[0]
                and len(marker[1]) >= len(fence)
                and not marker[2].strip()
            ):
                fence = ""
        elif marker:
            fence = marker[1]
        else:
            yield number, line


def transitional_findings(path: str, text: str) -> list[Finding]:
    """List wording for review, preserving the phrase as written."""
    return [
        Finding("TRANSITIONAL", path, number, match[0])
        for number, line in prose_lines(text)
        for match in TRANSITIONAL.finditer(line)
    ]


def ticket_findings(path: str, lines: list[tuple[int, str]]) -> list[Finding]:
    """Require a question in each level-three ticket, including its subsections."""
    found: list[Finding] = []
    ticket: tuple[int, str] | None = None
    question = False
    for number, line in [*lines, (0, "## End")]:
        heading = HEADING.match(line)
        if heading and len(heading[1]) <= 3:
            if ticket and not question:
                found.append(
                    Finding(
                        "OPEN_QUESTION",
                        path,
                        ticket[0],
                        f"missing question: {ticket[1]}",
                    )
                )
            ticket = (number, heading[2]) if len(heading[1]) == 3 else None
            question = False
        elif not heading and line.rstrip().endswith("?"):
            question = True
    return found


def open_question_findings(root: Path) -> list[Finding]:
    """Inspect the shared queue even when its file is not tracked."""
    relative = ".notes/project_open-questions.md"
    path = root / relative
    if not path.exists():
        return []
    contained_path(root, relative)
    lines = list(prose_lines(path.read_text(encoding="utf-8")))
    found = ticket_findings(relative, lines)
    for number, line in lines:
        heading = HEADING.match(line)
        if heading and STATUS.search(heading[2]):
            found.append(
                Finding(
                    "OPEN_QUESTION",
                    relative,
                    number,
                    f"status/progress heading: {heading[2]}",
                )
            )
    return found


def check_documents(root: Path, main_root: Path, options: Options) -> list[Finding]:
    """Read each selected record once and apply the checks appropriate to its owner."""
    found: list[Finding] = []
    for document in selected_documents(root, main_root, options):
        text = document.path.read_text(encoding="utf-8")
        found.extend(citation_findings(document.root, document.path, text))
        if document.decision:
            found.extend(
                transitional_findings(
                    str(document.path.relative_to(document.root)), text
                )
            )
    found.extend(open_question_findings(main_root))
    return found


def main() -> int:
    """Run the durable-record checks."""
    options = arguments()
    try:
        root, main_root = repository_roots()
        found = check_documents(root, main_root, options)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ERROR {error}", file=sys.stderr)
        return 2
    for finding in sorted(
        found, key=lambda item: (item.path, item.line, item.kind, item.reference)
    ):
        print(finding.render())
    transitions = sum(finding.kind == "TRANSITIONAL" for finding in found)
    questions = sum(finding.kind == "OPEN_QUESTION" for finding in found)
    citations = len(found) - transitions - questions
    advisory = sum(finding.advisory for finding in found)
    print(
        f"SUMMARY citations={citations} advisory={advisory} "
        f"transitional={transitions} "
        f"open_questions={questions}"
    )
    return int(
        bool(citations > advisory or (options.strict and (transitions or questions)))
    )


if __name__ == "__main__":
    raise SystemExit(main())
