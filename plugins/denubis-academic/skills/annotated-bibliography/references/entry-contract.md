# Entry contract

Use this small JSON record for the working evidence, then write the readable
literature note using the project's conventions. The helper checks structure,
source identity and exact quotations; it does not certify interpretation.

```json
{
  "citekey": "exactKeyReturnedByResolver",
  "source_sha256_prefix": "0123456789abcdef",
  "coverage": "full source read, including tables and limitations",
  "summary": "What the source establishes, with its scope and limits.",
  "positioning": "How that bears on the project's actual question.",
  "points": [
    {
      "physical_page": 7,
      "quote": "Short exact span copied from pages/007.md.",
      "paraphrase": "The claim this span supports in context.",
      "relevance": "Why it supports, complicates or extends the project argument."
    }
  ]
}
```

The hash comes from the resolved paper's `meta.json`. The paper directory's name
must equal `citekey`. `physical_page` is a positive, one-based PDF page index;
it is not a printed page label. If a claim spans a page boundary, use separate
points/evidence spans and explain their relationship; do not manufacture a joined
verbatim span on one page. Keep paraphrases and quotes distinct.

```bash
PLUGIN_DIR="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:?plugin root unavailable}}"
uv run "$PLUGIN_DIR/skills/annotated-bibliography/check.py" \
  /absolute/path/source.entry.json \
  /absolute/zettelkasten/papers/exactKeyReturnedByResolver
```

Exit 0 means every nonempty quotation occurs exactly on its named page and the
record meets the mechanical contract. Exit 1 reports failures or unreadable
inputs. Empty point lists, blank quotations, stale/missing metadata and wrong
source hashes fail. Matching is case-sensitive and literal: the helper does not
normalise punctuation, hyphens, case or whitespace. Copy a shorter exact span
when extraction line breaks interrupt a longer quotation.

The JSON report exposes `matched`/`total`, failures, and
`visual_verification_required`. For OCR this flag remains true even if a human
has separately checked the PDF: the helper cannot attest that action. Keep the
visual verification record beside the entry. An input note claiming verification
cannot change the helper's result.

The readable note should show source identity, coverage, summary, positioning,
each paraphrase with its short evidence span and locator, caveats, and review
state. Use verified printed locators for publication citations when available;
otherwise label physical-page references explicitly. Retain the existing
literature-note metadata rather than turning a text-match result into a human
`verified-by` value.
