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
3. Prove `full.md` is non-empty and read `meta.json`: `extraction`
   (`text-layer`, `ocr`, `converted`), `forced`, and `limitations`.
4. Build the render note from the record: the extraction label and every
   limitation, verbatim. The note describes how the text was extracted; it never
   says the text may be quoted without a source check.
5. Dispatch one reader with the deterministic `full.md` path and the paper's
   bounded brief.

If the resolver advised `--force-ocr` (a text layer that looks like third-party
OCR under page-sized images), decide before dispatch whether to re-render; the
reader's duty is the same either way.

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
The rendered Markdown is a reading text and a locator, whatever the render note
says about extraction. Copy each candidate quotation verbatim from the matching
page Markdown and label it `located`. Call a quotation `verified` only if you
have opened the source page yourself (the PDF page image at that physical page,
or the snapshot or attachment for a non-PDF source) and the wording matches;
otherwise the orchestrator or human performs that check. If you opened the
page and the wording differs, the quotation is `contradicted`: say what the
page reads, and do not quote the render's wording. A passage you could not
find in the render is `unverified`. Never repair wording to make it match.
</source_fidelity>

<output>
## {{CITEKEY}} — one-line description

### Findings
- finding in your own words [physical p. N]

### Candidate quotations
> exact text copied from page Markdown

[@{{CITEKEY}}, p. N]

Verification: located | verified (source page N inspected by <who>) | contradicted (source page N inspected by <who>; it reads "...") | unverified

### Gaps and caveats
- what the brief requested but the paper did not establish
- extraction defects or uncertainties, including the render note's limitations
</output>
```

Readers normally receive only rendered Markdown, which keeps PDF extraction and
the rest of the corpus out of their context. That restriction must not be used
to overclaim fidelity: a reader without the source returns `located` candidates
and the orchestrator performs or requests the source check for each one it will
call `verified`.

## Locate a quotation in rendered pages

Use a distinctive literal substring:

```bash
uv run "$BIB/blockquote.py" \
  "<zettelkasten-root>/papers/<citekey>/pages" \
  "<citekey>" "<verbatim substring>"
```

Exit `0` emits every matching page-keyed blockquote, each ending with
`Verification: located (render match; check the source page before calling it
verified)`. Exit `2` prints `NO MATCH` and `Verification: unverified`. Try a
shorter faithful substring and account for whitespace or Unicode hyphen
normalisation; never repair a mismatch by inventing source wording.

The helper checks rendered Markdown only: a hit locates the passage. For every
quotation that will be called `verified`, open the matching physical page of
the source (the PDF page image, or the snapshot or attachment for a non-PDF
source) and compare the wording. If that inspection cannot establish the exact
wording, quote nothing; paraphrase with an explicit caveat instead.

## Verification record

For each quotation retain:

- exact Zotero citekey;
- physical attachment page;
- exact page-Markdown match;
- `meta.json` renderer, `extraction`, `forced`, and `limitations`;
- its state: `located`, `verified` or `contradicted` (who checked the source
  page, and for `contradicted` what it reads), or `unverified`.

Page markers describe physical file pages, not the page number printed on the
paper. Use the physical page for bundled annotation tools; adapt citation style
to the venue only after the source claim is secured.
