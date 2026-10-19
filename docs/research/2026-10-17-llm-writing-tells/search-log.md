# Search log: stylistic and structural tells of current-generation LLM prose

Run date: 2026-10-17 (all times UTC). Scout: `llm-tells-scout`, following
`denubis-academic:literature-scout` 0.19.0 and its `references/search-and-verification.md`.

## Boundary as applied

- **Question.** What 2025–2026 literature says about the stylistic and structural tells of
  prose written by instruction-tuned frontier models, beyond single-word lexical markers. The
  five wanted topics are coded T1–T5 in `candidates.md`.
- **Date range.** 2024–2026, with priority on models released from mid-2025 onward. Older
  works appear only as seeds or for context.
- **Language.** English only. Non-English corpora were screened out and are listed in
  `candidates.md` under "Excluded after screening".
- **Source types.** Preprints, conference papers, journal articles, datasets, software
  registries, plus one non-scholarly catalogue (Wikipedia) that the brief requested.
  Detector benchmarks reporting only accuracy were excluded.
- **Acquisition.** Metadata and abstracts only. No Zotero, no PDF downloads, no full-text
  HTML papers. arXiv **abstract landing pages** (`arxiv.org/abs/…`) were fetched as metadata
  pages; their saved HTML is in `responses/arxiv-abs/`.
- **Budget and stopping point.** Aimed for about 20–30 ranked candidates. Stopped once
  forward citation from the seeds (Reinhart, Kobak, Geng and Trotta, Juzek and Ward, Milička,
  Neurobiber, Terčon) and backward references from three 2026 hubs (Wu et al., Zamaraeva et
  al., Boggia) stopped producing new feature-level work in English. The last such additions
  were Bakhshi 2026 (tricolon), reached through a keyword search, and Fung et al. 2026. The
  final reference sweeps added no new feature-level studies. Forward citation of the 2026
  hubs was not run, because each had at most 10 citing works on 2026-10-17 (Semantic Scholar).

## Indexes and services

| Service | Use | Availability during the run |
|---|---|---|
| Crossref REST (scout helper) | DOI metadata; title searches | Available. All requests HTTP 200, using the mailto from the per-user config file. |
| Semantic Scholar Graph (scout helper; one direct batch call using the configured key) | Forward citations, backward references, keyword search, batch abstracts | Intermittent HTTP 429. Rows `041` and `050` failed after 4 attempts each; both succeeded on retry (`061`, `058`). |
| OpenAlex `/works?filter=doi:` (anonymous) | Second registry; abstracts reconstructed from the inverted index | Available. The response warned of a shared anonymous daily budget. No API key was requested, because that needs the user's email. |
| arXiv export API (`export.arxiv.org/api/query`) | Planned batch metadata | **Unavailable**: HTTP 429 at 02:56:38 and on 5 retries ending 03:05:00. Replaced by OpenAlex, then by arXiv abstract landing pages. |
| arXiv abstract landing pages (`arxiv.org/abs/<id>`) | First-party title, authors, version history and abstract | Available. 32 pages fetched with HTTP 200, 4 seconds apart (`responses/arxiv-abs/fetch-log.txt`). |
| ACL Anthology | BibTeX and abstract for COLING 2025 and LREC 2026 items | Available. |
| NCBI E-utilities and PMC ID converter | PubMed abstract for Reinhart et al. | **Failed.** A DOI search returned no IDs; a title search returned an empty list; the PMC converter moved and then returned a null PMID; efetch returned HTTP 400. |
| PyPI JSON, CRAN, GitHub API | Tool registries | Available. `neurobiber` is not on PyPI (HTTP 404). |
| MediaWiki API (en.wikipedia.org) | Revision metadata and section wikitext for Wikipedia:Signs of AI writing | Available. The first section request failed (`badinteger` for an empty `oldid`); it was repeated against the fixed revision 1380587573. |
| WebSearch (Claude Code tool) | Discovery by web search, the stand-in for Google Scholar | Available. Each call returned one page of about 9–10 links plus a tool summary. Snippet claims were treated as leads only. |
| WebFetch (Claude Code tool) | Landing pages | Mixed. Reinhart's notebook failed with no output and was fetched with `curl` instead. A ScienceDirect page returned 403 (see disclosures). SAGE and arXiv pages succeeded. |
| Google Scholar (direct) | — | Not queried directly; WebSearch was used instead. |

## Disclosures

1. **Email in a request header.** On the second arXiv-API attempt (about 03:05), I put the
   user's email address into the `User-Agent` header (`mailto:`). The user's instructions
   forbid sending that address to services in request headers unless the user asks. The
   request was rejected with HTTP 429. The address was not used in any other ad-hoc request;
   the scout helper's Crossref calls used the mailto already configured for that purpose.
2. **Guessed URL.** I tried a ScienceDirect PII URL for Jiang and Hyland (2025, ESP) that I
   had built rather than found in a registry. It returned HTTP 403. That URL appears in no
   deliverable and supports no claim.
3. **No independent reviewer.** No second reviewer was dispatched. The rechecks in
   `verification.md` were done by the agent that did discovery, so they are not independent.

## Web searches and page fetches (in run order)

Times are approximate, inferred from neighbouring API timestamps, because the tools do not
log them. "Page 1" means the one result page the tool returned.

| # | ~Time | Tool | Query or URL | Pages inspected | Leads kept |
|---|---|---|---|---|---|
| W1 | 02:41 | WebFetch, then curl | https://www.refsmmat.com/notebooks/llm-style.html | Full notebook page (updated 8 Jun 2026); saved as `responses/009-refsmmat-llm-style-notebook.html` | Identified the notebook's studies: Goulart, Milička, Mizumoto, Mak and Walasek, Kirilloff, Ming, plus Toney, Dawkins, Jiang and Hyland ×3, Russell (StoryScope), Liang, Leppänen, Siler, DeLuca |
| W2 | 02:48 | WebSearch (standard) | "em dash" large language models writing frequency study arXiv 2025 | Page 1 (9 links) | Czuma ×2, Kosch, Freeburg |
| W3 | 02:48 | WebSearch (standard) | "not X but Y" OR "negative parallelism" OR antithesis LLM-generated text rhetorical figure study | Page 1 (9 links) | No study measuring the construction in LLM output; practitioner pages only |
| W4 | 02:48 | WebSearch (standard) | "rule of three" OR tricolon OR triads LLM generated prose overuse study 2025 2026 | Page 1 (9 links) | No measured study; practitioner pages only |
| W5 | 02:49 | WebSearch (standard) | people who frequently use ChatGPT accurate detectors of AI-generated text expert annotators clues | Page 1 (9 links) | Russell et al. 2025 |
| W6 | 02:50 | WebSearch (standard) | Measuring AI "slop" in text taxonomy expert interviews Shaib 2025 arXiv | Page 1 (9 links) | Shaib et al. 2025 |
| W7 | 02:50 | WebSearch (standard) | Antislop framework identifying eliminating repetitive patterns language models Paech 2025 | Page 1 (10 links) | Paech et al. 2025 |
| W8 | 02:50 | WebSearch (standard) | "Idiosyncrasies in Large Language Models" Sun 2025 word choice markdown formatting classifiers | Page 1 (9 links) | Sun et al. 2025 |
| W9 | 02:51 | WebSearch (**extended**) | GPT-5 Claude Sonnet 4.5 Gemini 3 writing style stylometric comparison human text 2026 arXiv | Page 1 (8 links) | van Nuenen 2026; Shan et al. 2026; a Japanese stylometry paper (excluded); vendor blogs (not used) |
| W10 | 02:52 | WebSearch (standard) | readers prefer AI fine-tuned on authors' books over expert human writers blind evaluation Chakrabarty Ginsburg Dhillon | Page 1 (10 links) | Chakrabarty, Ginsburg and Dhillon 2025 |
| W11 | 02:52 | WebSearch (standard) | "human-authorship halo" attribution bias literary style evaluation humans AI arXiv 2510.08831 | Page 1 (10 links) | Haverals and Martin 2025; v1 title "Everyone prefers human writers, including AI" |
| W12 | 02:52 | WebSearch (standard) | survey editors reviewers perceived signs of AI-generated manuscripts "em dash" OR "overly polished" OR formulaic 2025 study | Page 1 (9 links) | Hadan et al. (arXiv 2407.12015); the Quaia editorial; the AACR corpus study (not resolved) |
| W13 | 02:53 | WebSearch (standard) | biberplus Python package Biber tagger Alkiek; MFTE multi-feature tagger of English Le Foll; pseudobibeR R package | Page 1 (10 links) | Registry pages, which were then queried directly |
| W14 | 03:50 | WebFetch | https://arxiv.org/abs/2410.16107 | Abstract page | Reinhart version history (v1 21 Oct 2024; v2 21 Aug 2025) |
| W15 | 03:51 | WebSearch (standard) | Geng Trotta "advancement" word frequency decline arXiv abstracts LLM late 2024 | Page 1 (9 links) | **No mention of "advancement" found** |
| W16 | 03:52 | WebSearch (standard) | "advancement" LLM-associated word frequency decreased 2024 2025 arXiv abstracts preprint ChatGPT-style words decline | Page 1 (9 links) | **No mention of "advancement" found**; Sanger and Maurer 2026 |
| W17 | 03:53 | WebSearch (standard) | Economist July 2026 "How to spot AI writing" em dashes Claude professional writers study | Page 1 (9 links) | Reposts and summaries only; the original Economist article was not retrieved |
| W18 | 03:53 | WebSearch (standard) | sentence length variance burstiness LLM-generated text versus human writing measured 2025 study instruction-tuned | Page 1 (9 links) | Cao et al. 2026; a NeurIPS 2026 page titled "Burstiness Was Measured Wrong, and Prompting Cannot Aim It" (not identified further) |
| W19 | 03:54 | WebSearch (standard) | journal publisher guidance editors signs of AI-generated manuscript structural features list 2025 2026 editorial | Page 1 (9 links) | The SAGE blog (June 2025) |
| W20 | 03:55 | WebSearch (standard) | "Burstiness Was Measured Wrong" prompting cannot aim it | Page 1 (9 links) | **Not found**; that lead stays unidentified |
| W21 | 03:55 | WebSearch (standard) | "Emphasizing the Commendable" homogenized transitive verb constructions machine generated peer reviews | Page 1 (9 links) | Fung et al. 2026 (LREC) |
| W22 | 03:56 | WebSearch (standard) | hedges boosters stance markers LLM-generated research articles corpus comparison 2025 GPT-4o Claude academic writing | Page 1 (9 links) | No study comparing GPT-4o and Claude; CHI study methods |
| W23 | 03:56 | WebSearch (standard) | Rudnicka 2025 chatbot distinctive writing style ChatGPT Gemini idiolect study journal | Page 1 (10 links) | A Scientific American feature only; no journal version found |
| W24 | 04:29 | WebSearch (standard) | aclanthology.org "Why Does ChatGPT "Delve" So Much" COLING 2025 Juzek Ward | Page 1 (9 links) | ACL Anthology 2025.coling-main.426 |
| W25 | 04:29 | WebFetch | ScienceDirect PII URL built by me for Jiang and Hyland (ESP) | HTTP 403 | None (see disclosure 2) |
| W26 | 04:31 | WebFetch | https://www.sagepub.com/explore-our-content/blogs/posts/sage-perspectives/2025/06/11/ai-detection-for-peer-reviewers-look-out-for-red-flags | Full blog page | SAGE red-flag list (cites no research) |
| W27 | 04:26–04:52 | curl (background, 4-second spacing) | 32 arXiv abstract landing pages | Abstract pages | Version history, author forms and abstracts (`responses/094-arxiv-abs-parsed.jsonl`) |
| W28 | 02:54–02:56 | curl | MediaWiki API: page info, section list, and wikitext for §3.1, §10.6, §12, §13.5, §13.8 at revision 1380587573 | Those sections | Wikipedia catalogue content and the sources it cites |
| W29 | 04:24–04:29 | curl | ACL Anthology `2026.lrec-1.836` (bib and landing page) and `2025.coling-main.426.bib` | Bib records and one abstract | Metadata for Fung et al. and Juzek and Ward |

## Citation-chaining summary

| Seed or hub | Direction | Index | Rows returned | Saved as |
|---|---|---|---|---|
| Reinhart et al. 2025 (arXiv 2410.16107) | forward | Semantic Scholar | 131 (2 pages: offsets 0 and 100) | `010`, `011` |
| Kobak et al. 2025 (arXiv 2406.07016) | forward | Semantic Scholar | 253 (3 pages: offsets 0, 100, 200), screened by a title-keyword filter, then read in full | `020`–`022` |
| Geng and Trotta 2025 (arXiv 2502.09606) | forward | Semantic Scholar | 28 | `012` |
| Juzek and Ward 2025 (arXiv 2412.11385) | forward | Semantic Scholar | 19 | `013` |
| Milička et al. (arXiv 2509.10179) | forward | Semantic Scholar | 10 | `014` |
| Neurobiber (arXiv 2502.18590) | forward | Semantic Scholar | 4 | `015` |
| Terčon and Dobrovoljc 2025 (arXiv 2510.05136) | forward | Semantic Scholar | 12 | `016` |
| Wu et al. 2026 (arXiv 2604.19139) | backward | Semantic Scholar | 54 (many non-scholarly, see `gaps.md`) | `040` |
| Zamaraeva et al. 2026 (arXiv 2610.10092) | backward | Semantic Scholar | 40 (after one 429) | `041` (failed), `061` |
| Boggia 2026 (arXiv 2607.21498) | backward | Semantic Scholar | 32 | `042` |
| Jiang and Hyland, Goulart, Mizumoto, Mak and Walasek, Kirilloff, Ming | not chained | — | — | Identity checks only; forward citation from these was not run within budget |

Semantic Scholar's citation lists returned `total=None`, so how complete they are cannot be
measured from the response.

## Saved API responses (generated from `responses/`)

Retrieval times are taken from the helper's `retrieved_at` field where present. For saved
copies (registry pages, OpenAlex batches) the file's modification time is shown, and it is
labelled as such.

| File | Host | Query or identifier | Paging | Retrieved (UTC) | Status | Results |
|---|---|---|---|---|---|---|
| 001-cr-meta-reinhart-pnas.json | api.crossref.org | 10.1073/pnas.2422455122 |  | 2026-10-17T02:39:59.934179+00:00 | ok http=200 attempts=1 | returned=1  |
| 002-s2-meta-reinhart-arxiv.json | api.semanticscholar.org | ARXIV:2410.16107 |  | 2026-10-17T02:40:01.729419+00:00 | ok http=200 attempts=1 | returned=1  |
| 003-s2-meta-kobak-arxiv.json | api.semanticscholar.org | ARXIV:2406.07016 |  | 2026-10-17T02:40:05.704725+00:00 | ok http=200 attempts=2 | returned=1  |
| 004-s2-meta-neurobiber.json | api.semanticscholar.org | ARXIV:2502.18590 |  | 2026-10-17T02:40:07.065600+00:00 | ok http=200 attempts=1 | returned=1  |
| 005-cr-meta-kobak-sciadv.json | api.crossref.org | 10.1126/sciadv.adt3813 |  | 2026-10-17T02:40:16.939866+00:00 | ok http=200 attempts=1 | returned=1  |
| 006-s2-search-geng-trotta.json | api.semanticscholar.org | Geng Trotta ChatGPT academic writing word frequency arXiv | limit=10 offset=0 | 2026-10-17T02:40:18.880213+00:00 | ok http=200 attempts=1 | returned=3 total=3 offset=0 next=None |
| 007-s2-search-human-llm-coevolution.json | api.semanticscholar.org | Human-LLM coevolution evidence from academic writing | limit=10 offset=0 | 2026-10-17T02:40:20.722177+00:00 | ok http=200 attempts=1 | returned=10 total=954 offset=0 next=10 |
| 008-s2-search-juzek-ward.json | api.semanticscholar.org | Why does ChatGPT delve so much? Exploring the sources of lexical overrepresentation | limit=10 offset=0 | 2026-10-17T02:40:23.313393+00:00 | ok http=200 attempts=1 | returned=1 total=1 offset=0 next=None |
| 009-refsmmat-llm-style-notebook.html | file |  |  | 2026-10-17T05:10:55Z (file mtime) |  |  |
| 010-s2-cit-reinhart-p1.json | api.semanticscholar.org | ARXIV:2410.16107/citations | limit=100 offset=0 | 2026-10-17T02:42:17.063362+00:00 | ok http=200 attempts=1 | returned=100 total=None offset=0 next=100 |
| 011-s2-cit-reinhart-p2.json | api.semanticscholar.org | ARXIV:2410.16107/citations | limit=100 offset=100 | 2026-10-17T02:42:19.085134+00:00 | ok http=200 attempts=1 | returned=31 total=None offset=100 next=None |
| 012-s2-cit-geng-coevolution.json | api.semanticscholar.org | ARXIV:2502.09606/citations | limit=100 offset=0 | 2026-10-17T02:46:04.105734+00:00 | ok http=200 attempts=1 | returned=28 total=None offset=0 next=None |
| 013-s2-cit-juzek-ward.json | api.semanticscholar.org | ARXIV:2412.11385/citations | limit=100 offset=0 | 2026-10-17T02:46:05.778482+00:00 | ok http=200 attempts=1 | returned=19 total=None offset=0 next=None |
| 014-s2-cit-milicka.json | api.semanticscholar.org | ARXIV:2509.10179/citations | limit=100 offset=0 | 2026-10-17T02:46:07.248888+00:00 | ok http=200 attempts=1 | returned=10 total=None offset=0 next=None |
| 015-s2-cit-neurobiber.json | api.semanticscholar.org | ARXIV:2502.18590/citations | limit=100 offset=0 | 2026-10-17T02:46:09.007364+00:00 | ok http=200 attempts=1 | returned=4 total=None offset=0 next=None |
| 016-s2-cit-tercon.json | api.semanticscholar.org | ARXIV:2510.05136/citations | limit=100 offset=0 | 2026-10-17T02:46:10.777492+00:00 | ok http=200 attempts=1 | returned=12 total=None offset=0 next=None |
| 020-s2-cit-kobak-p1.json | api.semanticscholar.org | ARXIV:2406.07016/citations | limit=100 offset=0 | 2026-10-17T02:46:34.092462+00:00 | ok http=200 attempts=1 | returned=100 total=None offset=0 next=100 |
| 021-s2-cit-kobak-p2.json | api.semanticscholar.org | ARXIV:2406.07016/citations | limit=100 offset=100 | 2026-10-17T02:46:36.028617+00:00 | ok http=200 attempts=1 | returned=100 total=None offset=100 next=200 |
| 022-s2-cit-kobak-p3.json | api.semanticscholar.org | ARXIV:2406.07016/citations | limit=100 offset=200 | 2026-10-17T02:46:38.064008+00:00 | ok http=200 attempts=1 | returned=53 total=None offset=200 next=None |
| 030-arxiv-batch1.xml | file |  |  | 2026-10-17T03:08:14Z (file mtime) |  |  |
| 030-headers.txt | file |  |  | 2026-10-17T03:08:14Z (file mtime) |  |  |
| 031-oa-batch1.json | api.openalex.org | /works?filter=doi:10.48550%2FarXiv.2404.08627\|10.48550%2FarXiv.2502.09606\|10.48550%2FarXiv.2508.01930\|10.48550%2FarXiv.2509.10179\|10.48550%2FarXiv.2509.22996\|10.48550%2FarXiv.2604.14111\|10.48550%2FarXiv.2604.19139\ | per_page=100 | 2026-10-17T03:11:02Z (file mtime) | ok http=200 | count=12 |
| 032-oa-batch2.json | api.openalex.org | /works?filter=doi:10.48550%2FarXiv.2506.01407\|10.48550%2FarXiv.2509.09596\|10.48550%2FarXiv.2510.05136\|10.48550%2FarXiv.2602.18152\|10.48550%2FarXiv.2603.25638\|10.48550%2FarXiv.2603.27006\|10.48550%2FarXiv.2604.07565\ | per_page=100 | 2026-10-17T03:11:30Z (file mtime) | ok http=200 | count=16 |
| 033-oa-batch3.json | api.openalex.org | /works?filter=doi:10.48550%2FarXiv.2403.07183\|10.48550%2FarXiv.2407.00211\|10.48550%2FarXiv.2407.12015\|10.48550%2FarXiv.2409.11704\|10.48550%2FarXiv.2409.14509\|10.48550%2FarXiv.2501.15654\|10.48550%2FarXiv.2502.12150\ | per_page=100 | 2026-10-17T03:14:58Z (file mtime) | ok http=200 | count=19 |
| 034-oa-batch4.json | api.openalex.org | /works?filter=doi:10.1007%2Fs11192-025-05341-y\|10.1016%2Fj.acorp.2024.100106\|10.1016%2Fj.caeai.2025.100507\|10.1016%2Fj.esp.2025.03.001\|10.1016%2Fj.jslw.2024.101160\|10.1073%2Fpnas.2605754123\|10.1073%2Fpnas.262183412 | per_page=100 | 2026-10-17T03:15:34Z (file mtime) | ok http=200 | count=12 |
| 035-s2-batch-abstracts1.json | api.semanticscholar.org | batch: DOI:10.1016/j.esp.2025.03.001, DOI:10.1016/j.jslw.2024.101160, DOI:10.1007/s11192-025-05341-y, DOI:10.1073/pnas.2621834123, ARXIV:2509.09596, ARXIV:2508.01930, ARXIV:2510.13939, ARXIV:2410.16107, ARXIV:2406.07016, |  | 2026-10-17T03:27:47.619917+00:00 | ok http=200 attempts= | returned=11  |
| 036-cr-meta-10_1016_j_esp_2025_03_001.json | api.crossref.org | 10.1016/j.esp.2025.03.001 |  | 2026-10-17T03:45:20.701108+00:00 | ok http=200 attempts=1 | returned=1  |
| 036-cr-meta-10_1016_j_jslw_2024_101160.json | api.crossref.org | 10.1016/j.jslw.2024.101160 |  | 2026-10-17T03:45:21.605335+00:00 | ok http=200 attempts=1 | returned=1  |
| 037-pubmed-reinhart-abstract.txt | file |  |  | 2026-10-17T03:47:51Z (file mtime) |  |  |
| 040-s2-refs-wu-verbal-tics.json | api.semanticscholar.org | ARXIV:2604.19139/references | limit=100 offset=0 | 2026-10-17T04:13:36.456289+00:00 | ok http=200 attempts=2 | returned=54 total=None offset=0 next=None |
| 041-s2-refs-zamaraeva-antithesis.json | api.semanticscholar.org | ARXIV:2610.10092/references | limit=100 offset=0 | 2026-10-17T04:13:53.440781+00:00 | unavailable http=429 attempts=4 | returned=  |
| 042-s2-refs-boggia.json | api.semanticscholar.org | ARXIV:2607.21498/references | limit=100 offset=0 | 2026-10-17T04:13:57.428106+00:00 | ok http=200 attempts=2 | returned=32 total=None offset=0 next=None |
| 043-oa-batch5.json | api.openalex.org | /works?filter=doi:10.1002%2Fleap.2067\|10.1007%2Fs11192-026-05589-y\|10.1016%2Fj.ins.2025.122858\|10.1016%2Fj.rmal.2026.100297\|10.1038%2Fs41562-026-02550-0\|10.1038%2Fs42256-026-01178-z\|10.1111%2Fijal.70115\|10.1177%2F | per_page=100 | 2026-10-17T04:14:46Z (file mtime) | ok http=200 | count=23 |
| 050-s2-search-tricolon-large-language-models.json | api.semanticscholar.org | tricolon large language models | limit=20 offset=0 | 2026-10-17T04:16:06.937601+00:00 | unavailable http=429 attempts=4 | returned=  |
| 051-s2-search-rule-of-three-language-model-generated-t.json | api.semanticscholar.org | rule of three language model generated text | limit=20 offset=0 | 2026-10-17T04:16:08.286642+00:00 | ok http=200 attempts=1 | returned=20 total=9595 offset=0 next=20 |
| 052-s2-search-negative-parallelism-language-model-writ.json | api.semanticscholar.org | negative parallelism language model writing | limit=20 offset=0 | 2026-10-17T04:16:13.055328+00:00 | ok http=200 attempts=2 | returned=20 total=1151 offset=0 next=20 |
| 053-s2-search-not-X-but-Y-construction-language-models.json | api.semanticscholar.org | not X but Y construction language models | limit=20 offset=0 | 2026-10-17T04:16:15.616610+00:00 | ok http=200 attempts=1 | returned=20 total=215 offset=0 next=20 |
| 054-s2-search-em-dash-large-language-models.json | api.semanticscholar.org | em dash large language models | limit=20 offset=0 | 2026-10-17T04:16:17.330334+00:00 | ok http=200 attempts=1 | returned=20 total=3096 offset=0 next=20 |
| 055-s2-search-GPT-5-writing-style-linguistic-features.json | api.semanticscholar.org | GPT-5 writing style linguistic features | limit=20 offset=0 | 2026-10-17T04:16:19.754906+00:00 | ok http=200 attempts=1 | returned=20 total=2423 offset=0 next=20 |
| 056-s2-search-Claude-writing-style-stylometry-2026.json | api.semanticscholar.org | Claude writing style stylometry 2026 | limit=20 offset=0 | 2026-10-17T04:16:22.159656+00:00 | ok http=200 attempts=1 | returned=4 total=4 offset=0 next=None |
| 057-s2-search-markdown-formatting-bold-lists-LLM-respo.json | api.semanticscholar.org | markdown formatting bold lists LLM responses style | limit=20 offset=0 | 2026-10-17T04:16:25.889501+00:00 | ok http=200 attempts=2 | returned=11 total=11 offset=0 next=None |
| 058-s2-search-tricolon-retry.json | api.semanticscholar.org | tricolon large language models | limit=20 offset=0 | 2026-10-17T04:16:48.381217+00:00 | ok http=200 attempts=2 | returned=20 total=263555 offset=0 next=20 |
| 059-cr-search-tricolon.json | api.crossref.org | tricolon rule of three large language model generated text | limit=15 offset=0 | 2026-10-17T04:16:49.388134+00:00 | ok http=200 attempts=1 | returned=15 6690311 |
| 060-cr-search-negative-parallelism.json | api.crossref.org | negative parallelism antithesis large language model writing | limit=15 offset=0 | 2026-10-17T04:16:51.184211+00:00 | ok http=200 attempts=1 | returned=15 5821256 |
| 061-s2-refs-zamaraeva-antithesis-retry.json | api.semanticscholar.org | ARXIV:2610.10092/references | limit=100 offset=0 | 2026-10-17T04:16:53.610096+00:00 | ok http=200 attempts=1 | returned=40 total=None offset=0 next=None |
| 062-oa-batch6.json | api.openalex.org | /works?filter=doi:10.1093%2Fllc%2Ffqaf035\|10.48550%2FarXiv.2502.11266\|10.48550%2FarXiv.2509.15035\|10.48550%2FarXiv.2604.14513\|10.48550%2FarXiv.2604.19768\|10.48550%2FarXiv.2608.26710\|10.48550%2FarXiv.2610.01316\|10. | per_page=100 | 2026-10-17T04:24:28Z (file mtime) | ok http=200 | count=7 |
| 063-acl-anthology-2026.lrec-1.836.bib | file |  |  | 2026-10-17T04:24:29Z (file mtime) |  |  |
| 064-acl-anthology-2026.lrec-1.836-landing.html | file |  |  | 2026-10-17T05:10:55Z (file mtime) |  |  |
| 070-cr-meta-10_18653_v1_2025_findings-acl_657.json | api.crossref.org | 10.18653/v1/2025.findings-acl.657 |  | 2026-10-17T04:28:26.218886+00:00 | ok http=200 attempts=1 | returned=1  |
| 071-cr-meta-10_1075_ijcl_25151_mil.json | api.crossref.org | 10.1075/ijcl.25151.mil |  | 2026-10-17T04:28:26.912617+00:00 | ok http=200 attempts=1 | returned=1  |
| 072-cr-meta-10_18653_v1_2025_acl-long_267.json | api.crossref.org | 10.18653/v1/2025.acl-long.267 |  | 2026-10-17T04:28:27.605664+00:00 | ok http=200 attempts=1 | returned=1  |
| 073-cr-meta-10_63317_3ai7wig4fhd8.json | api.crossref.org | 10.63317/3ai7wig4fhd8 |  | 2026-10-17T04:28:28.343364+00:00 | ok http=200 attempts=1 | returned=1  |
| 074-cr-meta-10_63317_2a6746sy5cke.json | api.crossref.org | 10.63317/2a6746sy5cke |  | 2026-10-17T04:28:29.037633+00:00 | ok http=200 attempts=1 | returned=1  |
| 075-cr-meta-10_1016_j_caeai_2025_100507.json | api.crossref.org | 10.1016/j.caeai.2025.100507 |  | 2026-10-17T04:28:29.734242+00:00 | ok http=200 attempts=1 | returned=1  |
| 076-cr-meta-10_1177_07410883251328311.json | api.crossref.org | 10.1177/07410883251328311 |  | 2026-10-17T04:28:30.624854+00:00 | ok http=200 attempts=1 | returned=1  |
| 077-cr-meta-10_1093_applin_amae052.json | api.crossref.org | 10.1093/applin/amae052 |  | 2026-10-17T04:28:31.516820+00:00 | ok http=200 attempts=1 | returned=1  |
| 078-cr-meta-10_1145_3706598_3713559.json | api.crossref.org | 10.1145/3706598.3713559 |  | 2026-10-17T04:28:32.426988+00:00 | ok http=200 attempts=1 | returned=1  |
| 079-cr-meta-10_18653_v1_2025_acl-long_1308.json | api.crossref.org | 10.18653/v1/2025.acl-long.1308 |  | 2026-10-17T04:28:33.359073+00:00 | ok http=200 attempts=1 | returned=1  |
| 080-cr-meta-10_2139_ssrn_5606570.json | api.crossref.org | 10.2139/ssrn.5606570 |  | 2026-10-17T04:28:34.031520+00:00 | ok http=200 attempts=1 | returned=1  |
| 081-cr-meta-10_1073_pnas_2605754123.json | api.crossref.org | 10.1073/pnas.2605754123 |  | 2026-10-17T04:28:34.729580+00:00 | ok http=200 attempts=1 | returned=1  |
| 082-cr-meta-10_63317_4ut7ammh7z3h.json | api.crossref.org | 10.63317/4ut7ammh7z3h |  | 2026-10-17T04:28:35.651827+00:00 | ok http=200 attempts=1 | returned=1  |
| 083-cr-meta-10_18653_v1_2026_acl-long_1803.json | api.crossref.org | 10.18653/v1/2026.acl-long.1803 |  | 2026-10-17T04:28:36.339275+00:00 | ok http=200 attempts=1 | returned=1  |
| 084-cr-meta-10_1145_3806206.json | api.crossref.org | 10.1145/3806206 |  | 2026-10-17T04:28:37.063102+00:00 | ok http=200 attempts=1 | returned=1  |
| 085-cr-meta-10_3390_make8080223.json | api.crossref.org | 10.3390/make8080223 |  | 2026-10-17T04:28:38.157747+00:00 | ok http=200 attempts=1 | returned=1  |
| 086-cr-meta-10_1016_j_chbah_2024_100095.json | api.crossref.org | 10.1016/j.chbah.2024.100095 |  | 2026-10-17T04:28:38.844062+00:00 | ok http=200 attempts=1 | returned=1  |
| 087-cr-meta-10_18653_v1_2025_acl-long_443.json | api.crossref.org | 10.18653/v1/2025.acl-long.443 |  | 2026-10-17T04:28:39.734091+00:00 | ok http=200 attempts=1 | returned=1  |
| 090-cr-search-juzek-ward-coling.json | api.crossref.org | Why Does ChatGPT Delve So Much Exploring the Sources of Lexical Overrepresentation Juzek Ward | limit=5 offset=0 | 2026-10-17T04:28:51.238669+00:00 | ok http=200 attempts=1 | returned=5 45855 |
| 091-cr-search-kousha-thelwall.json | api.crossref.org | How much are LLMs changing the language of academic papers after ChatGPT multi-database full text Kousha Thelwall | limit=5 offset=0 | 2026-10-17T04:28:52.031479+00:00 | ok http=200 attempts=1 | returned=5 9365 |
| 092-cr-search-jiang-hyland-esp-abstract-check.json | api.crossref.org | Rhetorical distinctions metadiscourse essays ChatGPT students Jiang Hyland | limit=3 offset=0 | 2026-10-17T04:28:53.212906+00:00 | ok http=200 attempts=1 | returned=3 2495555 |
| 093-acl-anthology-2025.coling-main.426.bib | file |  |  | 2026-10-17T04:29:16Z (file mtime) |  |  |
| 094-arxiv-abs-parsed.jsonl | file |  |  | 2026-10-17T04:52:02Z (file mtime) |  |  |
| 095-verification-matrix.json | other |  |  | 2026-10-17T04:53:09Z (file mtime) |  |  |
| 096-verification-matrix-secondary.json | other |  |  | 2026-10-17T04:53:09Z (file mtime) |  |  |
| 100-cr-meta-10_1016_j_acorp_2024_100106.json | api.crossref.org | 10.1016/j.acorp.2024.100106 |  | 2026-10-17T05:00:26.596498+00:00 | ok http=200 attempts=1 | returned=1  |
| 101-cr-meta-10_1162_99608f92_6d5fb5ef.json | api.crossref.org | 10.1162/99608f92.6d5fb5ef |  | 2026-10-17T05:00:27.529261+00:00 | ok http=200 attempts=1 | returned=1  |
| 102-cr-meta-10_18653_v1_2024_emnlp-main_368.json | api.crossref.org | 10.18653/v1/2024.emnlp-main.368 |  | 2026-10-17T05:00:28.245838+00:00 | ok http=200 attempts=1 | returned=1  |
| 103-cr-meta-10_1007_s11192-026-05601-5.json | api.crossref.org | 10.1007/s11192-026-05601-5 |  | 2026-10-17T05:00:28.943190+00:00 | ok http=200 attempts=1 | returned=1  |
| 104-cr-meta-10_32473_flairs_39_1_141843.json | api.crossref.org | 10.32473/flairs.39.1.141843 |  | 2026-10-17T05:00:29.827884+00:00 | ok http=200 attempts=1 | returned=1  |
| 105-cr-meta-10_1007_978-3-032-19096-3_16.json | api.crossref.org | 10.1007/978-3-032-19096-3_16 |  | 2026-10-17T05:00:30.533607+00:00 | ok http=200 attempts=1 | returned=1  |
| 110-github-elenlefoll-MFTE.json | api.github.com | /repos/elenlefoll/MultiFeatureTaggerEnglish |  | 2026-10-17T05:10:55Z | None http=None attempts= | returned=  |
| cran-pseudobibeR.html | file |  |  | 2026-10-17T02:48:38Z (file mtime) |  |  |
| pypi-MFTE.json | other |  |  | 2026-10-17T02:49:15Z (file mtime) |  |  |
| pypi-biberplus.json | other |  |  | 2026-10-17T02:48:38Z (file mtime) |  |  |
| wp-info.json | other |  |  | 2026-10-17T02:49:30Z (file mtime) |  |  |
| wp-sec-10.6.json | other |  |  | 2026-10-17T02:55:26Z (file mtime) |  |  |
| wp-sec-12.json | other |  |  | 2026-10-17T02:55:27Z (file mtime) |  |  |
| wp-sec-13.5.json | other |  |  | 2026-10-17T02:55:28Z (file mtime) |  |  |
| wp-sec-13.8.json | other |  |  | 2026-10-17T02:55:29Z (file mtime) |  |  |
| wp-sec-3.1.json | other |  |  | 2026-10-17T02:55:25Z (file mtime) |  |  |
| wp-sections.json | other |  |  | 2026-10-17T02:49:30Z (file mtime) |  |  |
