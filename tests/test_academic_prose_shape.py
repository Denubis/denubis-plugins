"""Tests for plugins/denubis-academic/skills/academic-writing/prose_shape.py.

The pure core (Markdown splitting, register targets, histograms, rendering) is
tested without spaCy, the way the other heavy-dependency helpers are. The
parser-dependent findings (series, foils across sentences, -ing openers) need
spaCy with the transformer model and skip when it is not installed; the
documented command in the skill text runs them:

    PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 uv run --with pytest \\
      --with "spacy[transformers]>=3.8,<3.9" --with <en_core_web_trf wheel> \\
      pytest tests/test_academic_prose_shape.py -q
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_HELPER = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-academic"
    / "skills"
    / "academic-writing"
    / "prose_shape.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("prose_shape", _HELPER)
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves the deferred annotations through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ps = _load()


# --- Markdown handling (no parser) ----------------------------------------------


def test_comments_headings_citations_and_blockquotes_are_not_prose():
    text = (
        "# Draft\n\n## Intro\n\n<!-- a comment\nspanning lines -->\n\n"
        "> Quoted epigraph sentence here. [@key, p. 1]\n\n"
        "Real prose stays in the count [@someKey2020]. A second sentence stays.\n"
    )
    sections = ps.split_markdown(text)
    prose = " ".join(p for s in sections for p in s.paragraphs)
    assert "comment" not in prose
    assert "Intro" not in prose
    assert "epigraph" not in prose
    assert "@someKey2020" not in prose
    assert "Real prose stays in the count." in prose
    assert "A second sentence stays." in prose


def test_bullets_are_kept_separately_from_paragraph_prose():
    text = (
        "## S\n\nA paragraph sentence of prose.\n\n- a bullet item\n- another bullet\n"
    )
    [section] = ps.split_markdown(text)
    assert section.paragraphs == ["A paragraph sentence of prose."]
    assert section.bullets == ["a bullet item", "another bullet"]


def test_paragraphs_are_split_on_blank_lines_and_sections_on_the_chosen_level():
    text = (
        "## Alpha\n\nFirst paragraph line one\ncontinues here.\n\nSecond paragraph.\n\n"
        "### Alpha sub\n\nSubsection paragraph.\n\n## Beta\n\nBeta paragraph.\n"
    )
    sections = {s.heading: s for s in ps.split_markdown(text)}
    assert set(sections) == {"Alpha", "Beta"}
    assert sections["Alpha"].paragraphs == [
        "First paragraph line one continues here.",
        "Second paragraph.",
        "Subsection paragraph.",
    ]
    assert len(ps.split_markdown(text, section_level=3)) == 3


# --- Register targets (no parser) -----------------------------------------------


REGISTER = """---
name: register-x
---

# Register

## Measured shape

```toml prose-shape
short_words = 12
run_words = 10
long_words = 45
mean_words = 22
commas_per_sentence = 1.0
paragraph_sentences_max = 6
```
"""


def test_register_block_supplies_targets_and_absence_supplies_none():
    t = ps.read_targets(REGISTER)
    assert (t.short_words, t.run_words, t.long_words) == (12, 10, 45)
    assert t.mean_words == 22
    assert t.commas_per_sentence == 1.0
    assert t.paragraph_sentences_max == 6
    assert t.paragraph_sentences_min is None
    empty = ps.read_targets("# Register\n\nNo block here.\n")
    assert not empty.any_set()


def test_unknown_register_key_is_an_error_not_a_silent_default():
    with pytest.raises(ValueError, match="shrot_words"):
        ps.read_targets("```toml prose-shape\nshrot_words = 12\n```\n")


def test_flag_targets_override_register_targets():
    base = ps.Targets(short_words=12, long_words=45)
    merged = base.merged(ps.Targets(short_words=10))
    assert (merged.short_words, merged.long_words) == (10, 45)


# --- Histograms and rendering (no parser) ---------------------------------------


def test_histogram_bins_are_inclusive_with_an_open_top():
    counts = dict(ps.histogram([1, 5, 6, 10, 41, 90], ps.LENGTH_BINS))
    assert counts["1-5"] == 2
    assert counts["6-10"] == 2
    assert counts["41+"] == 2
    assert sum(counts.values()) == 6


def _report_with(targets):
    whole = ps.Shape(lengths=[8, 20, 30], commas=[0, 1, 2], paragraph_sentences=[3])
    row = ps.SectionShape(
        heading="S", lengths=[8, 20, 30], commas=[0, 1, 2], paragraph_sentences=[3]
    )
    hits = []
    if targets.short_words is not None:
        hits.append(ps.Hit("short-sentence", "S", "Eight words.", "8 words"))
        row.kinds["short-sentence"] = 1
    return ps.Report(whole=whole, sections=[row], hits=hits, targets=targets)


def test_report_without_targets_shows_distributions_and_no_threshold_columns():
    text = ps.render(_report_with(ps.Targets()), "doc")
    assert "## Sentence length" in text
    assert "## Commas per sentence" in text
    assert "## Sentences per paragraph" in text
    assert "## Sentence lengths in order" in text
    assert "<12" not in text
    assert "short-sentence" not in text
    assert "No register targets" in text


def test_report_with_targets_adds_threshold_column_and_section():
    text = ps.render(_report_with(ps.Targets(short_words=12)), "doc")
    assert "| <12 |" in text
    assert "## short-sentence (1)" in text
    assert "Eight words." in text


# --- Quote marks and acronyms (no parser) ---------------------------------------


def test_quote_marks_counts_straight_and_curly_separately():
    assert ps.quote_marks('It\'s "fine"') == (3, 0)
    assert ps.quote_marks("It\u2019s \u201cfine\u201d") == (0, 3)


def test_acronyms_report_count_first_use_and_expansion():
    sentences = [
        "A large language model (LLM) answers questions.",
        "The LLM is not a search engine.",
        "We submitted to BJET in March.",
        "The HTML comments are not prose.",
    ]
    found = ps.acronyms(sentences)
    assert found["LLM"]["count"] == 2
    assert found["LLM"]["expanded"] is True
    assert found["LLM"]["first"].startswith("A large language model")
    assert found["BJET"]["expanded"] is False
    assert found["HTML"]["expanded"] is False
    assert "A" not in found


def test_report_lists_minority_quote_form_and_unexpanded_acronyms():
    whole = ps.Shape(
        lengths=[5, 5],
        commas=[0, 0],
        paragraph_sentences=[2],
        straight_marks=1,
        curly_marks=4,
        sentences_text=["It\u2019s the LLM\u2019s turn.", "It's BJET's turn."],
    )
    hits = [
        ps.Hit("curly-mark", "S", "It\u2019s the LLM\u2019s turn."),
        ps.Hit("straight-mark", "S", "It's BJET's turn."),
    ]
    text = ps.render(
        ps.Report(whole=whole, sections=[], hits=hits, targets=ps.Targets()), "d"
    )
    assert "straight 1, curly 4" in text
    assert "- **S**: It's BJET's turn." in text
    assert (
        "It\u2019s the LLM\u2019s turn."
        not in text.split("## Quote marks")[1].split("## Acronyms")[0]
    )
    assert "| BJET | 1 | no |" in text
    assert "| LLM | 1 | no |" in text


# --- Parser-dependent findings ---------------------------------------------------


@pytest.fixture(scope="module")
def nlp():
    pytest.importorskip("spacy")
    try:
        return ps.load_pipeline()
    except OSError as exc:  # model wheel not installed in this environment
        pytest.skip(f"spaCy model unavailable: {exc}")


def analyse(nlp, text, targets=None):
    return ps.analyse_sections(nlp, ps.split_markdown(text), targets)


def test_short_sentence_total_counts_every_sentence_under_threshold(nlp):
    text = (
        "## S\n\nThis is short. "
        "This sentence, by contrast, runs comfortably past the twelve word threshold "
        "that the author set for short sentences. "
        "Another short one here.\n"
    )
    report = analyse(nlp, text, ps.Targets(short_words=12))
    hits = [h for h in report.hits if h.kind == "short-sentence"]
    assert {h.sentence for h in hits} == {"This is short.", "Another short one here."}
    assert report.whole.sentences == 3
    assert report.whole.paragraph_sentences == [3]


def test_no_threshold_means_no_threshold_hits(nlp):
    text = "## S\n\nShort one. Short two. Short three.\n"
    report = analyse(nlp, text)
    assert not any(h.kind in ps.THRESHOLD_KINDS for h in report.hits)
    assert report.whole.sentences == 3


def test_word_count_treats_possessives_and_hyphenated_words_as_one(nlp):
    curly = chr(0x2019)
    text = f"## S\n\nThe LLM{curly}s non-statistician co-author stops here.\n"
    report = analyse(nlp, text)
    assert report.whole.lengths == [6]


def test_run_of_short_sentences_is_one_hit_and_ends_at_a_paragraph(nlp):
    text = (
        "## S\n\nOne is short. Two is short. Three is short. Four is also short.\n\n"
        "Five is short. Six is short.\n"
    )
    report = analyse(nlp, text, ps.Targets(run_words=10))
    runs = [h for h in report.hits if h.kind == "short-run"]
    assert len(runs) == 1
    assert runs[0].detail.startswith("4 consecutive")


def test_paragraph_length_targets_flag_paragraphs(nlp):
    text = (
        "## S\n\nThis is one. This is two. This is three. This is four.\n\n"
        "This is five.\n"
    )
    report = analyse(
        nlp, text, ps.Targets(paragraph_sentences_min=2, paragraph_sentences_max=3)
    )
    kinds = sorted(h.kind for h in report.hits if "paragraph" in h.kind)
    assert kinds == ["long-paragraph", "short-paragraph"]
    assert report.whole.paragraph_sentences == [4, 1]


def test_triad_is_a_series_of_exactly_three_coordinated_items(nlp):
    triad = "## S\n\nI use it for lecture preparation, research, and programming.\n"
    pair = "## S\n\nI use it for research and programming.\n"
    four = "## S\n\nI use it for lectures, research, programming, and hobbies.\n"
    assert sum(h.kind == "triad" for h in analyse(nlp, triad).hits) == 1
    assert sum(h.kind == "triad" for h in analyse(nlp, pair).hits) == 0
    assert sum(h.kind == "triad" for h in analyse(nlp, four).hits) == 0
    assert sum(h.kind == "series-4plus" for h in analyse(nlp, four).hits) == 1


def test_correction_frame_across_two_sentences_is_a_foil(nlp):
    text = "## S\n\nIt is not a technical problem. It is a social one.\n"
    hits = [h for h in analyse(nlp, text).hits if h.kind == "foil"]
    assert len(hits) == 1
    assert "correction frame" in hits[0].detail


def test_rather_than_and_not_but_are_foils_and_plain_claim_is_not(nlp):
    foils = (
        "## S\n\nI read the source rather than trusting the summary. "
        "The point is not speed but accuracy in the final text.\n"
    )
    plain = "## S\n\nI read the source and then check the summary against it.\n"
    assert sum(h.kind == "foil" for h in analyse(nlp, foils).hits) == 2
    assert sum(h.kind == "foil" for h in analyse(nlp, plain).hits) == 0


def test_em_dash_and_semicolon_are_counted(nlp):
    text = "## S\n\nThe model answered — badly; the author rewrote it.\n"
    whole = analyse(nlp, text).whole
    assert whole.em_dashes == 1
    assert whole.semicolons == 1


def test_stacked_distinct_hedges_are_flagged_and_a_repeated_word_is_not(nlp):
    stacked = "## S\n\nThis may perhaps suggest that the result could possibly hold.\n"
    repeated = "## S\n\nThe LLM could be wrong, and so could you.\n"
    assert sum(h.kind == "hedge-stack" for h in analyse(nlp, stacked).hits) == 1
    assert sum(h.kind == "hedge-stack" for h in analyse(nlp, repeated).hits) == 0


def test_passives_are_found_and_agent_presence_is_told_apart(nlp):
    text = (
        "## S\n\nThe report was written by the committee. Mistakes were made. "
        "The committee wrote the report.\n"
    )
    hits = [h for h in analyse(nlp, text).hits if h.kind == "passive"]
    assert [h.sentence for h in hits] == [
        "The report was written by the committee.",
        "Mistakes were made.",
    ]
    assert "with agent" in hits[0].detail
    assert "agentless" in hits[1].detail


def test_subjectless_gerund_passive_is_found(nlp):
    text = "## S\n\nBeing challenged on our ideas forces us to think about them.\n"
    hits = [h for h in analyse(nlp, text).hits if h.kind == "passive"]
    assert len(hits) == 1
    assert "challenged" in hits[0].detail


def test_section_announcement_is_flagged(nlp):
    text = "## S\n\nThis section explains how the loop works. The loop has two parts.\n"
    hits = [h for h in analyse(nlp, text).hits if h.kind == "manuscript-talk"]
    assert len(hits) == 1
    assert hits[0].sentence.startswith("This section")


def test_gerund_subject_and_participial_clause_openers_are_told_apart(nlp):
    gerund = "## S\n\nUsing an LLM well begins before the first message is sent.\n"
    clause = (
        "## S\n\nDrawing on three decades of fieldwork, the authors argue for reuse.\n"
    )
    plain = "## S\n\nThe authors argue for reuse after three decades of fieldwork.\n"

    def kinds(text):
        return [h.kind for h in analyse(nlp, text).hits if "opener" in h.kind]

    assert kinds(gerund) == ["gerund-subject-opener"]
    assert kinds(clause) == ["participial-clause-opener"]
    assert kinds(plain) == []
