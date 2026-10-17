---
name: register-project-author
description: Attested prose register for one author, project, and venue context
type: reference
---

# Author and project prose register

## Authority and limits

- Corpus or author decision from which this register was derived:
- Date and derivation method:
- Current venue and whether a rule belongs to the venue rather than the author:
- Evidence too narrow to support a durable rule:
- Newer author decisions that supersede older examples:

## Audience, voice, and stance

- Intended readers:
- Person and reader address:
- Epistemic hedging and attribution verbs:
- Terms, abbreviations, and explanations:

## Sentence and paragraph construction

- Typical sentence and paragraph shape:
- Signposting and connective practice:
- Tense and voice by section:
- Known model-generated drift to resist:

## Punctuation, orthography, and presentation

- Spelling and punctuation conventions:
- Numbers, units, tables, figures, and headings:
- Citation and quotation presentation:
- Literal material that blanket normalization must not touch:

## Measured shape

Optional. Targets the author has attested for this register, with the source of each
number. `prose_shape.py --register` reads the fenced block and reports against it; every
key is optional, an omitted key produces no section, and an unknown key is an error.
Delete the block rather than leave guessed values in it.

```toml prose-shape
# short_words = 12            # count sentences under this many words
# run_words = 10              # a run is consecutive sentences under this
# run_length = 3              # sentences that make a run (default 3)
# long_words = 45             # flag sentences over this
# mean_words = 22             # informational target for mean length
# commas_per_sentence = 1.0   # informational target for the mean
# paragraph_sentences_min = 2 # flag paragraphs shorter than this
# paragraph_sentences_max = 6 # flag paragraphs longer than this
```

- Source of each target (author ruling, corpus measurement, venue guidance):

## Attested exceptions

Record each departure from the portable academic-writing method positively, with its
source. Optional quantitative observations are diagnostic evidence, not phrase locks or
automatic acceptance gates.
