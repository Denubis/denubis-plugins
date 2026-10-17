#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "spacy[transformers]>=3.8,<3.9",
#   "en-core-web-trf @ https://github.com/explosion/spacy-models/releases/download/en_core_web_trf-3.8.0/en_core_web_trf-3.8.0-py3-none-any.whl",
#   "en-core-web-sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl",
# ]
# ///
"""Describe the shape of a Markdown manuscript's prose.

The report is descriptive. It prints distributions (sentence length, commas per
sentence, sentences per paragraph) and lists every rhetorical shape it can see
(coordinated series, foils, stacked hedges, passives, manuscript-talk, -ing
openers) with
the sentence attached. Nothing is scored, passed, or failed: the author decides
whether each shape is licensed by a distinction in the evidence.

Thresholds are never built in. A project's register note may carry a fenced
``toml`` block tagged ``prose-shape`` (see reference_register-TEMPLATE.md); pass
it with ``--register`` and the report adds the sections those targets define.
Command-line flags override the block. Without either, only distributions and
structural shapes are reported.

The transformer pipeline depends on spacy-alignments 0.9.2, which ships no
Python 3.14 wheel (PyPI, checked 2026-10-18). Its Rust source build succeeds on
3.14 when ``PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1`` is set for the first
``uv run``; uv caches the built wheel afterwards.
"""

from __future__ import annotations

import argparse
import re
import statistics
import sys
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

DEFAULT_MODEL = "en_core_web_trf"

HEDGES = {
    "may",
    "might",
    "could",
    "perhaps",
    "possibly",
    "arguably",
    "somewhat",
    "likely",
    "suggest",
    "suggests",
    "seem",
    "seems",
    "appear",
    "appears",
}

MANUSCRIPT_TALK = re.compile(
    r"\b(this|the (?:next|final|following|previous) )?section (?:shows|explains|"
    r"describes|sets out|covers|discusses|turns|introduces|presents)\b"
    r"|\b(?:it is|it's) worth noting\b"
    r"|\bin what follows\b"
    r"|\bas (?:noted|discussed|mentioned) (?:above|earlier|below)\b"
    r"|\bthe remainder of this\b",
    re.IGNORECASE,
)

NOT_BUT = re.compile(r"\bnot\b(?:(?!\bbut\b)[^.;:?!]){1,80}?\bbut\b", re.IGNORECASE)
RATHER_THAN = re.compile(r"\brather than\b|\binstead of\b", re.IGNORECASE)
NEGATED_COPULA_OPENER = re.compile(
    r"^(?:It|This|That|These|Those|They)\s+(?:is|are|was|were)\s+not\b", re.IGNORECASE
)
COPULA_OPENER = re.compile(
    r"^(?:It|This|That|These|Those|They)\s+(?:is|are|was|were)\b", re.IGNORECASE
)
_APOSTROPHES = "'" + chr(0x2019)  # straight and curly
_LETTERS = "A-Za-z0-9" + chr(0x00C0) + "-" + chr(0x024F)  # Latin letters with accents
_WORD = re.compile(f"[{_LETTERS}]+(?:[{_APOSTROPHES}\\-][{_LETTERS}]+)*")


# --- Targets ------------------------------------------------------------------


@dataclass
class Targets:
    """Register-supplied thresholds. Every field is optional; ``None`` means the
    register names no value, and the report omits the section that needs it."""

    short_words: int | None = None
    run_words: int | None = None
    run_length: int | None = None
    long_words: int | None = None
    mean_words: float | None = None
    commas_per_sentence: float | None = None
    paragraph_sentences_min: int | None = None
    paragraph_sentences_max: int | None = None

    def any_set(self) -> bool:
        return any(getattr(self, f.name) is not None for f in fields(self))

    def merged(self, other: Targets) -> Targets:
        """Values in ``other`` override values here."""
        out = Targets()
        for f in fields(self):
            theirs = getattr(other, f.name)
            setattr(
                out, f.name, theirs if theirs is not None else getattr(self, f.name)
            )
        return out


_REGISTER_BLOCK = re.compile(r"```toml\s+prose-shape\s*\n(.*?)\n```", re.DOTALL)


def read_targets(register_text: str) -> Targets:
    """Read the ``toml prose-shape`` block from a register note.

    Returns empty targets when the note has no block. Raises ``ValueError`` on
    an unknown key, so a misspelt target cannot silently become "no target".
    """
    m = _REGISTER_BLOCK.search(register_text)
    if not m:
        return Targets()
    data = tomllib.loads(m.group(1))
    known = {f.name for f in fields(Targets)}
    unknown = set(data) - known
    if unknown:
        raise ValueError(
            f"unknown prose-shape key(s) {sorted(unknown)}; known: {sorted(known)}"
        )
    return Targets(**data)


# --- Markdown -------------------------------------------------------------------


@dataclass
class Section:
    heading: str
    level: int
    paragraphs: list[str] = field(default_factory=list)
    bullets: list[str] = field(default_factory=list)


_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_FENCE = re.compile(r"```.*?```", re.DOTALL)
_CITATION = re.compile(r"\s*\[(?:[^\[\]]*@[^\[\]]*)\]")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_EMPHASIS = re.compile(r"(\*\*|__|\*|_|`)")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")


def _clean_inline(text: str) -> str:
    text = _CITATION.sub("", text)
    text = _LINK.sub(r"\1", text)
    text = _EMPHASIS.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"\s+([.,;:?!])", r"\1", text)


def split_markdown(text: str, section_level: int = 2) -> list[Section]:
    """Split Markdown into sections at ``section_level`` headings.

    Comments, fenced code, headings and blockquotes are not the author's
    running prose and are dropped. Bullets are kept apart from paragraphs.
    """
    text = _COMMENT.sub("", text)
    text = _FENCE.sub("", text)
    sections: list[Section] = []
    current = Section(heading="(before first heading)", level=0)
    para: list[str] = []

    def flush() -> None:
        if para:
            current.paragraphs.append(_clean_inline(" ".join(para)))
            para.clear()

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush()
            continue
        if m := _HEADING.match(line):
            flush()
            level = len(m.group(1))
            if level <= section_level:
                if current.paragraphs or current.bullets:
                    sections.append(current)
                current = Section(heading=m.group(2), level=level)
            continue
        if line.lstrip().startswith(">"):
            flush()
            continue
        if m := _BULLET.match(line):
            flush()
            current.bullets.append(_clean_inline(m.group(1)))
            continue
        para.append(line.strip())
    flush()
    if current.paragraphs or current.bullets:
        sections.append(current)
    return sections


# --- Observations ---------------------------------------------------------------


@dataclass
class Hit:
    kind: str
    section: str
    sentence: str
    detail: str = ""


@dataclass
class Shape:
    """Distributions for a section or the whole document."""

    lengths: list[int] = field(default_factory=list)
    commas: list[int] = field(default_factory=list)
    paragraph_sentences: list[int] = field(default_factory=list)
    em_dashes: int = 0
    semicolons: int = 0
    colons: int = 0
    bullets: int = 0

    @property
    def sentences(self) -> int:
        return len(self.lengths)

    @property
    def words(self) -> int:
        return sum(self.lengths)

    @property
    def paragraphs(self) -> int:
        return len(self.paragraph_sentences)


@dataclass
class SectionShape(Shape):
    heading: str = ""
    kinds: dict[str, int] = field(default_factory=dict)


@dataclass
class Report:
    whole: Shape
    sections: list[SectionShape]
    hits: list[Hit]
    targets: Targets


def load_pipeline(model: str = DEFAULT_MODEL):
    """Load a spaCy English pipeline.

    The transformer model is the default because the dependency parse carries
    the series and opener findings; the small model is kept for quick runs.
    """
    import spacy

    return spacy.load(model, exclude=["ner", "lemmatizer"])


def _word_count(sent) -> int:
    """Words as a reader counts them; a possessive or hyphenated word is one."""
    return len(_WORD.findall(sent.text))


def _conj_chains(sent) -> list[list]:
    """Coordinated series in the sentence, each as its list of conjunct heads."""
    chains = []
    for tok in sent:
        if tok.dep_ == "conj":
            continue
        if not any(c.dep_ == "conj" for c in tok.children):
            continue
        chain = [tok]
        cur = tok
        while True:
            nxt = [c for c in cur.children if c.dep_ == "conj"]
            if not nxt:
                break
            cur = nxt[0]
            chain.append(cur)
        chains.append(chain)
    return chains


def _hedges(sent) -> list[str]:
    """Distinct hedge words in the sentence; a repeated word counts once."""
    seen: dict[str, str] = {}
    for t in sent:
        if t.lower_ in HEDGES:
            seen.setdefault(t.lower_, t.text)
    return list(seen.values())


def _passives(sent) -> list[tuple[str, bool]]:
    """Passive clauses as (verb, has_agent). A passive subject marks the clause;
    an agent is a ``by`` phrase attached to the same verb."""
    out = []
    for tok in sent:
        if tok.dep_ == "nsubjpass":
            verb = tok.head
            has_agent = any(c.dep_ == "agent" for c in verb.children)
            out.append((verb.text, has_agent))
    return out


def _opener_kind(first) -> str:
    """Classify a sentence-initial -ing word.

    A gerund acting as the subject ("Using an LLM well begins...") is a
    nominalised-action opener. A participial clause ("Drawing on fieldwork,
    the authors argue...") is an adverbial lead-in. Both are reported because
    a run of either reads as a pattern, but they are different shapes.
    """
    dep = first.dep_
    if dep in {"csubj", "nsubj"} or (
        dep == "ROOT"
        and first.pos_ == "VERB"
        and any(c.dep_ == "nsubj" for c in first.children)
    ):
        return "gerund-subject-opener"
    if dep in {"advcl", "prep", "amod", "acl"} or first.head.dep_ == "advcl":
        return "participial-clause-opener"
    return "ing-opener"


def _structural_hits(sent, text: str, previous_text: str) -> list[tuple]:
    """Register-independent shapes in one sentence, as (kind, sentence, detail)."""
    found: list[tuple] = []
    if "—" in text:
        found.append(("em-dash", text, ""))
    if ";" in text:
        found.append(("semicolon", text, ""))
    for chain in _conj_chains(sent):
        items = ", ".join(t.text for t in chain)
        if len(chain) == 3:
            found.append(("triad", text, f"series of three: {items}"))
        elif len(chain) >= 4:
            found.append(("series-4plus", text, f"series of {len(chain)}: {items}"))
    if NOT_BUT.search(text):
        found.append(("foil", text, "not X but Y"))
    found.extend(("foil", text, m.group(0).lower()) for m in RATHER_THAN.finditer(text))
    if NEGATED_COPULA_OPENER.match(previous_text) and COPULA_OPENER.match(text):
        found.append(
            ("foil", f"{previous_text} {text}", "correction frame across two sentences")
        )
    hedges = _hedges(sent)
    if len(hedges) >= 2:
        found.append(("hedge-stack", text, ", ".join(hedges)))
    for verb, agent in _passives(sent):
        found.append(
            ("passive", text, f"{verb}, {'with agent' if agent else 'agentless'}")
        )
    if MANUSCRIPT_TALK.search(text):
        found.append(("manuscript-talk", text, ""))
    first = sent[0]
    if first.tag_ == "VBG":
        found.append((_opener_kind(first), text, f"{first.text} ({first.dep_})"))
    return found


def _threshold_hits(text: str, words: int, t: Targets) -> list[tuple]:
    found: list[tuple] = []
    if t.short_words is not None and words < t.short_words:
        found.append(("short-sentence", text, f"{words} words"))
    if t.long_words is not None and words > t.long_words:
        found.append(("long-sentence", text, f"{words} words"))
    return found


class _Run:
    """Consecutive sentences under ``run_words``; closed at a longer sentence or
    a paragraph break. Inactive when the register names no run threshold."""

    def __init__(self, t: Targets) -> None:
        self.words = t.run_words
        self.length = t.run_length if t.run_length is not None else 3
        self.items: list[str] = []

    def feed(self, text: str, words: int) -> tuple | None:
        if self.words is None:
            return None
        if words < self.words:
            self.items.append(text)
            return None
        return self.close()

    def close(self) -> tuple | None:
        hit = None
        if self.words is not None and len(self.items) >= self.length:
            hit = (
                "short-run",
                " ".join(self.items),
                f"{len(self.items)} consecutive sentences under {self.words} words",
            )
        self.items = []
        return hit


def _paragraph_hit(paragraph: str, n: int, t: Targets) -> tuple | None:
    if t.paragraph_sentences_max is not None and n > t.paragraph_sentences_max:
        return ("long-paragraph", paragraph, f"{n} sentences")
    if t.paragraph_sentences_min is not None and 0 < n < t.paragraph_sentences_min:
        return ("short-paragraph", paragraph, f"{n} sentence(s)")
    return None


def _tally(acc: Shape, text: str, words: int) -> None:
    acc.lengths.append(words)
    acc.commas.append(text.count(","))
    acc.em_dashes += text.count("—")
    acc.semicolons += text.count(";")
    acc.colons += text.count(":")


def _analyse_section(
    nlp, section: Section, whole: Shape, targets: Targets
) -> tuple[SectionShape, list[Hit]]:
    row = SectionShape(heading=section.heading, bullets=len(section.bullets))
    whole.bullets += len(section.bullets)
    hits: list[Hit] = []

    def record(found: tuple | None) -> None:
        if found is None:
            return
        kind, sentence, detail = found
        hits.append(Hit(kind, section.heading, sentence, detail))
        row.kinds[kind] = row.kinds.get(kind, 0) + 1

    for paragraph in section.paragraphs:
        run = _Run(targets)
        previous_text = ""
        n_sentences = 0
        for sent in nlp(paragraph).sents:
            text = sent.text.strip()
            if not text:
                continue
            n_sentences += 1
            words = _word_count(sent)
            _tally(whole, text, words)
            _tally(row, text, words)
            for found in _structural_hits(sent, text, previous_text):
                record(found)
            for found in _threshold_hits(text, words, targets):
                record(found)
            record(run.feed(text, words))
            previous_text = text
        record(run.close())
        whole.paragraph_sentences.append(n_sentences)
        row.paragraph_sentences.append(n_sentences)
        record(_paragraph_hit(paragraph, n_sentences, targets))
    return row, hits


def analyse_sections(
    nlp, sections: list[Section], targets: Targets | None = None
) -> Report:
    targets = targets or Targets()
    whole = Shape()
    rows: list[SectionShape] = []
    hits: list[Hit] = []
    for section in sections:
        row, section_hits = _analyse_section(nlp, section, whole, targets)
        rows.append(row)
        hits.extend(section_hits)
    return Report(whole=whole, sections=rows, hits=hits, targets=targets)


# --- Reporting ------------------------------------------------------------------

LENGTH_BINS = [
    (1, 5),
    (6, 10),
    (11, 15),
    (16, 20),
    (21, 25),
    (26, 30),
    (31, 40),
    (41, None),
]
COMMA_BINS = [(0, 0), (1, 1), (2, 2), (3, 3), (4, None)]
PARAGRAPH_BINS = [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 7), (8, None)]

STRUCTURAL_KINDS = [
    "em-dash",
    "semicolon",
    "triad",
    "series-4plus",
    "foil",
    "hedge-stack",
    "passive",
    "manuscript-talk",
    "participial-clause-opener",
    "gerund-subject-opener",
    "ing-opener",
]
THRESHOLD_KINDS = [
    "short-sentence",
    "short-run",
    "long-sentence",
    "long-paragraph",
    "short-paragraph",
]


def histogram(
    values: list[int], bins: list[tuple[int, int | None]]
) -> list[tuple[str, int]]:
    """Count ``values`` into inclusive bins; ``None`` as an upper bound is open."""
    out = []
    for lo, hi in bins:
        n = sum(1 for v in values if v >= lo and (hi is None or v <= hi))
        label = f"{lo}" if hi == lo else (f"{lo}+" if hi is None else f"{lo}-{hi}")
        out.append((label, n))
    return out


def _bar(n: int, total: int, width: int = 30) -> str:
    return "▓" * round(width * n / total) if total else ""


def _summary(values: list[int]) -> str:
    if not values:
        return "n=0"
    q = statistics.quantiles(values, n=4) if len(values) >= 2 else [values[0]] * 3
    return (
        f"n={len(values)}, mean {statistics.fmean(values):.1f}, "
        f"median {statistics.median(values):.0f}, sd {statistics.pstdev(values):.1f}, "
        f"quartiles {q[0]:.0f}/{q[2]:.0f}, range {min(values)}-{max(values)}"
    )


def _histogram_table(title: str, values: list[int], bins, unit: str) -> list[str]:
    out = [
        f"## {title}",
        "",
        _summary(values),
        "",
        f"| {unit} | Sentences | |",
        "|---|---|---|",
    ]
    total = len(values)
    for label, n in histogram(values, bins):
        out.append(f"| {label} | {n} | {_bar(n, total)} |")
    out.append("")
    return out


def _section_table(report: Report) -> list[str]:
    t = report.targets
    cols = [
        "Section",
        "Paras",
        "Sent.",
        "Words",
        "Mean",
        "SD",
        "Sent./para",
        "Commas/s",
    ]
    if t.short_words is not None:
        cols.append(f"<{t.short_words}")
    if t.long_words is not None:
        cols.append(f">{t.long_words}")
    cols += ["Em", "Semi", "Colon", "Triads", "Foils", "Passives", "Bullets"]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]

    def line(name: str, s: Shape, kinds: dict[str, int]) -> str:
        n = s.sentences
        cells = [
            name,
            str(s.paragraphs),
            str(n),
            str(s.words),
            f"{statistics.fmean(s.lengths):.1f}" if n else "-",
            f"{statistics.pstdev(s.lengths):.1f}" if n > 1 else "-",
            f"{statistics.fmean(s.paragraph_sentences):.1f}" if s.paragraphs else "-",
            f"{statistics.fmean(s.commas):.2f}" if n else "-",
        ]
        if t.short_words is not None:
            short = kinds.get("short-sentence", 0)
            cells.append(f"{short} ({100 * short / n:.0f}%)" if n else "0")
        if t.long_words is not None:
            cells.append(str(kinds.get("long-sentence", 0)))
        cells += [
            str(s.em_dashes),
            str(s.semicolons),
            str(s.colons),
            str(kinds.get("triad", 0)),
            str(kinds.get("foil", 0)),
            str(kinds.get("passive", 0)),
            str(s.bullets),
        ]
        return "| " + " | ".join(cells) + " |"

    all_kinds: dict[str, int] = {}
    for h in report.hits:
        all_kinds[h.kind] = all_kinds.get(h.kind, 0) + 1
    out.append(line("**Whole document**", report.whole, all_kinds))
    out.extend(line(r.heading, r, r.kinds) for r in report.sections)
    out.append("")
    return out


def _targets_lines(t: Targets) -> list[str]:
    if not t.any_set():
        return [
            "No register targets supplied, so only distributions and structural "
            "shapes are reported. Pass `--register NOTE.md` or threshold flags.",
            "",
        ]
    parts = []
    if t.mean_words is not None:
        parts.append(f"mean length about {t.mean_words:g} words")
    if t.short_words is not None:
        parts.append(f"sentences under {t.short_words} words kept sparing")
    if t.run_words is not None:
        parts.append(
            f"no run of {t.run_length if t.run_length is not None else 3} "
            f"under {t.run_words}"
        )
    if t.long_words is not None:
        parts.append(f"none over {t.long_words}")
    if t.commas_per_sentence is not None:
        parts.append(f"commas per sentence under {t.commas_per_sentence:g}")
    if t.paragraph_sentences_min is not None or t.paragraph_sentences_max is not None:
        lo = t.paragraph_sentences_min if t.paragraph_sentences_min is not None else "?"
        hi = t.paragraph_sentences_max if t.paragraph_sentences_max is not None else "?"
        parts.append(f"{lo} to {hi} sentences per paragraph")
    return ["Register targets: " + "; ".join(parts) + ".", ""]


def _hit_sections(report: Report, kinds: list[str]) -> list[str]:
    out = []
    for kind in kinds:
        hits = [h for h in report.hits if h.kind == kind]
        if not hits:
            continue
        out.append(f"## {kind} ({len(hits)})")
        out.append("")
        for h in hits:
            detail = f" *[{h.detail}]*" if h.detail else ""
            out.append(f"- **{h.section}**{detail}: {h.sentence}")
        out.append("")
    return out


def render(report: Report, source: str) -> str:
    out = [f"# Prose shape: {source}", ""]
    out.append(
        "Descriptive only. Each hit carries its sentence; the author decides whether "
        "the shape is licensed by a distinction in the evidence."
    )
    out.append("")
    out.extend(_targets_lines(report.targets))
    out.extend(_section_table(report))
    out.extend(
        _histogram_table("Sentence length", report.whole.lengths, LENGTH_BINS, "Words")
    )
    out.extend(
        _histogram_table(
            "Commas per sentence", report.whole.commas, COMMA_BINS, "Commas"
        )
    )
    out.extend(
        _histogram_table(
            "Sentences per paragraph",
            report.whole.paragraph_sentences,
            PARAGRAPH_BINS,
            "Sentences",
        )
    )
    out.append("## Sentence lengths in order")
    out.append("")
    for row in report.sections:
        if row.lengths:
            out.append(f"- **{row.heading}**: {' '.join(str(n) for n in row.lengths)}")
    out.append("")
    out.extend(_hit_sections(report, THRESHOLD_KINDS))
    out.extend(_hit_sections(report, STRUCTURAL_KINDS))
    return "\n".join(out)


# --- CLI ------------------------------------------------------------------------


def _flag_targets(args: argparse.Namespace) -> Targets:
    return Targets(
        short_words=args.short_words,
        run_words=args.run_words,
        run_length=args.run_length,
        long_words=args.long_words,
        mean_words=args.mean_words,
        commas_per_sentence=args.commas_per_sentence,
        paragraph_sentences_min=args.paragraph_min,
        paragraph_sentences_max=args.paragraph_max,
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", type=Path, help="Markdown manuscript")
    ap.add_argument(
        "--register", type=Path, help="register note with a toml prose-shape block"
    )
    ap.add_argument(
        "--section-level", type=int, default=2, help="heading level per row"
    )
    ap.add_argument("--output", type=Path, help="write the Markdown report here")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="spaCy pipeline name")
    for name, kind in [
        ("--short-words", int),
        ("--run-words", int),
        ("--run-length", int),
        ("--long-words", int),
        ("--mean-words", float),
        ("--commas-per-sentence", float),
        ("--paragraph-min", int),
        ("--paragraph-max", int),
    ]:
        ap.add_argument(name, type=kind, default=None, help="override the register")
    args = ap.parse_args(argv)

    targets = Targets()
    if args.register:
        try:
            targets = read_targets(args.register.read_text(encoding="utf-8"))
        except (ValueError, tomllib.TOMLDecodeError) as exc:
            print(f"register block: {exc}", file=sys.stderr)
            return 2
    targets = targets.merged(_flag_targets(args))

    text = args.path.read_text(encoding="utf-8")
    sections = split_markdown(text, args.section_level)
    nlp = load_pipeline(args.model)
    report = analyse_sections(nlp, sections, targets)
    rendered = render(report, f"{args.path} ({args.model})")
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
