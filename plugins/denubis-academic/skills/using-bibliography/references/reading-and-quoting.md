# Reading and quoting

Render once on the orchestrator side, then give each reader one paper's Markdown
path. Do not make parallel readers each resolve or extract the same source.

```bash
PLUGIN_DIR="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:?plugin root unavailable}}"
BIB="${PLUGIN_DIR}/skills/using-bibliography"
uv run "$BIB/resolve.py" --citekey <exact-key>
```

## Dispatch gate

For each paper:

1. Resolve by the exact citekey wherever possible.
2. Accept only `rendered`; put `no-pdf`, `pdf-unknown`, render failures, and
   `needs-ocr-escalation` on a visible “could not prepare” list.
3. Prove `full.md` is non-empty and read `meta.json`.
4. Label the reader input `clean text layer` when `ocr` is false, or `OCR
   locator—exact quotes require source-PDF verification` when it is true.
5. Dispatch one reader with the deterministic `full.md` path and the paper's
   bounded brief.

The citekey is the handle for the render directory, Pandoc citation, literature
note, and reader result. Never construct it from author/title/year.

## Reader prompt

Interpolate the citekey, path, render note, and brief:

```text
<role>
Read one paper from the user's curated Zotero corpus to answer the bounded brief.
The orchestrator has already resolved and rendered it.
</role>

<inputs>
- citekey: {{CITEKEY}}
- rendered text: {{FULLMD_PATH}}
- render note: {{RENDER_NOTE}}
- brief: {{BRIEF}}
</inputs>

<method>
Read the supplied full.md and, when checking a passage, its sibling
pages/NNN.md. Attribute a page using the nearest preceding <!-- page:N -->
marker. Do not resolve, fetch, re-render, or search for another copy.
</method>

<source_fidelity>
If the render note says clean text layer, copy quotations verbatim from the
matching page Markdown. If it says OCR locator, use the Markdown to locate and
summarise the passage, but label every verbatim candidate “needs visual PDF
verification”; do not claim its exact wording is verified. The orchestrator or
human owns that visual check against the source PDF.
</source_fidelity>

<output>
## {{CITEKEY}} — one-line description

### Findings
- finding in your own words [physical p. N]

### Candidate quotations
> exact text copied from page Markdown

[@{{CITEKEY}}, p. N]

Verification: clean-render match | needs visual PDF verification

### Gaps and caveats
- what the brief requested but the paper did not establish
- extraction defects or uncertainties
</output>
```

Readers normally receive only rendered Markdown, which keeps PDF extraction and
the rest of the corpus out of their context. That restriction must not be used
to overclaim OCR fidelity: the reader returns a candidate and the orchestrator
performs or requests the source-PDF check.

## Locate a quotation in rendered pages

Use a distinctive literal substring:

```bash
uv run "$BIB/blockquote.py" \
  "<zettelkasten-root>/papers/<citekey>/pages" \
  "<citekey>" "<verbatim substring>"
```

Exit `0` emits every matching page-keyed blockquote. Exit `2` prints `NO MATCH`.
Try a shorter faithful substring and account for whitespace or Unicode hyphen
normalisation; never repair a mismatch by inventing source wording.

The helper checks rendered Markdown only. For `ocr: true`, append a
“needs visual PDF verification” marker until the matching physical page has
been inspected. If visual inspection cannot establish the exact wording, quote
nothing; paraphrase with an explicit caveat instead.

## Verification record

For each quotation retain:

- exact Zotero citekey;
- physical attachment page;
- exact page-Markdown match;
- `meta.json` renderer and OCR flag;
- when OCR is true, who visually checked the PDF and whether wording matched.

Page markers describe physical file pages, not the page number printed on the
paper. Use the physical page for bundled annotation tools; adapt citation style
to the venue only after the source claim is secured.
