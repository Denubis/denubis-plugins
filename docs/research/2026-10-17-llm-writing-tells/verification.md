# Metadata verification

Date: 2026-10-17 (UTC).

**This check is not independent.** No second reviewer was dispatched. The agent that ran
discovery also re-queried each candidate, so shared mistakes in my own handling would not be
caught. Independent verification is still pending.

## What was compared

For each ranked row, these fields were compared: all named authors, title,
venue/version, year or date, and identifier. The sources were:

- **arXiv landing page** (first-party record for preprints): `responses/094-arxiv-abs-parsed.jsonl`,
  parsed from `responses/arxiv-abs/*.html`;
- **OpenAlex** (`responses/03*-oa-*.json`, `043`, `062`);
- **Semantic Scholar** (citation and reference lists, searches, batch: `responses/0[0-6]*-s2-*.json`);
- **Crossref** (publisher deposits: `responses/0[0-9]*-cr-meta-*.json`, `10[0-5]-cr-meta-*.json`);
- **ACL Anthology BibTeX** (`responses/063-…lrec-1.836.bib`, `093-…coling-main.426.bib`);
- **MediaWiki API** for the Wikipedia page (`responses/wp-info.json`, `wp-sections.json`, `wp-sec-*.json`).

A script built the side-by-side matrix (`responses/095-verification-matrix.json`, ranked;
`096-…-secondary.json`, secondary). I then read every flagged disagreement myself. Spelling
variants (diacritics, hyphen characters, initials against full given names) count as
**supported**. A different person, a different title, or a different version counts as
**corrected** or **conflicting**.

Arxiv-only rows have weaker cross-checks. OpenAlex and Semantic Scholar both ingest arXiv,
so their agreement with the arXiv page is not fully independent evidence. The arXiv landing
page is treated as the authority for preprint identity.

## Coverage

| Set | Rows | Re-queried against at least one source other than the discovery hit | Bibliographic registry agreement on every field | Rows with a correction or unresolved conflict |
|---|---|---|---|---|
| Ranked | 30 | **30 / 30** | 29 / 30 (Wikipedia has no bibliographic registry; its revision was checked through the MediaWiki API) | 3 corrected (ranks 5, 7, 10); 1 version-title note not confirmed (rank 28); 1 unresolved content claim from the brief (rank 11, "advancement") |
| Secondary | 58 (S45 is a duplicate of rank 14) | 57 / 57 distinct rows were re-queried for title and authors; venue and year were also checked where Crossref was fetched (15 distinct rows) | The script found title and author agreement for 45 rows before manual review; the other 13 are resolved in the table below | 4 corrected (S9, S17, S23, S36); 3 unresolved or conflicting (S6, S11, S58) |

Fields left unchecked: for secondary rows without a Crossref record, venue, volume and pages
are as OpenAlex or Semantic Scholar returned them and were not re-verified. The Semantic
Scholar and OpenAlex citation counts in the saved responses were not cross-checked.

## Ranked rows

"Supported" means every source agrees. Where a value differs, the original and the
corrected or conflicting values are both given, with evidence.

| Rank | Key | Sources compared | Authors | Title | Venue / version | Year / date | Identifier | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | Zamaraeva et al. 2026 | arXiv, OpenAlex, S2 | supported (4; S2 drops the accent in "Santos-Rios") | supported | arXiv v1 only; no venue | 7 Oct 2026 (all) | arXiv:2610.10092 supported | — |
| 2 | Bakhshi 2026 | arXiv, OpenAlex, S2 | supported ("Asim D." / "Asim Dilawar" / "A.") | supported | arXiv v1 | 27 Mar 2026 | arXiv:2604.19768 supported | — |
| 3 | Freeburg 2026 | arXiv, OpenAlex, S2 | supported ("E. M." on arXiv and OpenAlex; "Eric Matthews" on S2) | supported | arXiv v1 | 27 Mar 2026 | arXiv:2603.27006 supported | S2 gives a fuller given name that the other two do not show; the table keeps the arXiv form. |
| 4 | Reinhart et al. 2025 | arXiv, S2, Crossref | supported (7) | supported | Crossref: PNAS 122(8), article e2422455122; arXiv journal-ref agrees | Crossref: online 18 Feb 2025, print 25 Feb 2025; arXiv v1 21 Oct 2024, v2 21 Aug 2025 | 10.1073/pnas.2422455122 and arXiv:2410.16107 supported | S2 gives year 2024 (arXiv v1). The PNAS version is dated 2025. The two are separate versions and were not merged. |
| 5 | Milička et al. | arXiv, OpenAlex, S2, Crossref | supported (3) | **corrected.** Original (arXiv, S2, Reinhart's notebook): "Benchmark of stylistic variation in LLM-generated texts". Version of record (Crossref, OpenAlex): "Benchmark of linguistic variation in LLM‑generated texts" (the hyphen is U+2011 in Crossref) | arXiv v2 (18 Sep 2025, journal-ref "International Journal of Corpus Linguistics 2026") against IJCL online first; Crossref lists no volume or pages | arXiv 2025; IJCL online 15 Sep 2026 | 10.1075/ijcl.25151.mil supported; arXiv:2509.10179 supported | The table cites the IJCL version and notes the arXiv title. S2 pairs the arXiv title with the IJCL venue and year 2025. |
| 6 | El Attar et al. 2026 | arXiv, OpenAlex, S2 | supported (arXiv orders the name "Attar, Yassir El"; family name El Attar) | supported | arXiv v1 | 2 Jun 2026 | arXiv:2606.04177 supported | — |
| 7 | Nakajima & Mizuno 2026 | arXiv, OpenAlex, S2 | supported (2) | **corrected (OpenAlex error).** OpenAlex: 'Data for "Large Language Model Turnover Undermines Screening…"'. arXiv and S2: "Large Language Model Turnover Undermines Screening for Artificial Intelligence-Assisted Scientific Writing" | arXiv v1 | 8 Oct 2026 | arXiv:2610.11599 supported | OpenAlex has merged the paper with its Zenodo data record (10.5281/zenodo.23273240 / .23273241). The arXiv title is used. |
| 8 | Rallapalli et al. 2026 | arXiv, OpenAlex, S2 | supported (7). "Chuck Loughin" on arXiv and OpenAlex; "Charles Loughin" on S2 | supported | arXiv v1 | 15 Apr 2026 | arXiv:2604.14111 supported | The arXiv name form is kept. The first S2 view showed 6 authors only because my summariser cut the list at 6; the saved response lists all 7. |
| 9 | Boggia 2026 | arXiv, OpenAlex, S2 | supported | supported | arXiv v2, 28 Jul 2026 | v1 23 Jul 2026 | arXiv:2607.21498 supported | — |
| 10 | Wu et al. 2026 | arXiv, OpenAlex, S2 | **corrected (OpenAlex error).** OpenAlex fourth author "Yufang Li"; arXiv "Liu, Bolun"; S2 "Bo-Lun Liu". The other six agree | supported | arXiv v4, 1 Oct 2026 | v1 21 Apr 2026 | arXiv:2604.19139 supported | The arXiv author list is used. |
| 11 | Geng & Trotta 2025 | arXiv, OpenAlex, S2, Crossref | supported (2) | supported | Crossref: Findings of ACL 2025, pp. 12689–12696; arXiv v2, 17 Feb 2025 | 2025. OpenAlex's 2025-01-01 is a year-only placeholder | 10.18653/v1/2025.findings-acl.657 and arXiv:2502.09606 supported | Two versions (arXiv and Findings) are distinguished. The content claim about "advancement" is unverified (see `gaps.md`). |
| 12 | Russell, Karpinska, Iyyer 2025 | arXiv, OpenAlex, Crossref | supported (3) | supported | Crossref: ACL 2025 Long, pp. 5342–5373 | 2025; arXiv v2 19 May 2025 | 10.18653/v1/2025.acl-long.267 supported | — |
| 13 | Miletić & Falk 2026 | arXiv, OpenAlex, S2, Crossref | supported (S2 drops the diacritic) | supported | Crossref: LREC 2026, pp. 1811–1830 | Crossref May 2026; OpenAlex 30 Apr 2026; arXiv 19 May 2026 | 10.63317/3ai7wig4fhd8 supported | Dates differ by source (conference date, then deposit); the year agrees. |
| 14 | Fung, Lo, Larkin 2026 | Crossref, ACL Anthology BibTeX | supported (3) | supported. Crossref leaves out the quotation marks around "Emphasizing the Commendable" that the ACL Anthology shows | LREC 2026, pp. 10664–10676 (both) | May 2026 | 10.63317/2a6746sy5cke (both); ACL Anthology 2026.lrec-1.836 | Semantic Scholar has a garbled record (author string "月. Hing-YuetFung馮慶, … Independent Researcher, William Croft, D. Nordquist", no DOI) in the Kobak citations (`022`). That record is unreliable and was not used. |
| 15 | Czuma 2026 (medRxiv) | arXiv, OpenAlex, S2 | supported | supported | arXiv v1 | 28 Jun 2026 | arXiv:2606.29540 supported | — |
| 16 | Mak & Walasek 2025 | OpenAlex, S2, Crossref | supported | supported | Crossref: Computers and Education: Artificial Intelligence 9, article 100507 | Crossref issue Dec 2025; OpenAlex 26 Nov 2025 (online) | 10.1016/j.caeai.2025.100507 supported | Matches Reinhart's notebook. |
| 17 | Thelwall & Kousha 2026 | arXiv, OpenAlex, S2 | supported ("Mike" / "Michael" / "Mike A") | supported | arXiv v1 | 8 Apr 2026 | arXiv:2604.07565 supported | — |
| 18 | Gude et al. 2026 | arXiv, OpenAlex, S2, Crossref | supported (6) | supported | Crossref: ACL 2026 Long, pp. 38900–38911 | 2026 | 10.18653/v1/2026.acl-long.1803 and arXiv:2605.06030 supported | — |
| 19 | Kobak et al. 2025 | arXiv, S2, Crossref | supported (4) | supported | Science Advances 11(27), article eadt3813 | Crossref "published-print" and "issued" 4 Jul 2025, created 2 Jul 2025; arXiv journal-ref "2 Jul 2025" | 10.1126/sciadv.adt3813 and arXiv:2406.07016 supported | Online and print dates are kept separate. S2 gives year 2024 (arXiv v1). |
| 20 | Jiang & Hyland 2025 (ESP) | OpenAlex, S2, Crossref | supported. S2 shows the first author as "Jiang Feng", with given and family names swapped; Crossref has "Feng (Kevin) Jiang" | supported | Crossref: English for Specific Purposes 79, 17–29 | Crossref print July 2025; OpenAlex 31 Mar 2025 (online) | 10.1016/j.esp.2025.03.001 supported | No abstract from any registry, so the row stays title-only. |
| 21 | Chakrabarty, Ginsburg, Dhillon 2025 | arXiv, OpenAlex, S2, Crossref | supported (3) | supported | arXiv v4 (17 Mar 2026). Crossref has SSRN "posted-content" (10.2139/ssrn.5606570), which OpenAlex labels "acceptedVersion" | arXiv v1 15 Oct 2025 | arXiv:2510.13939 and 10.2139/ssrn.5606570 supported | Versions differ in content (reader counts change between versions, per a web-search summary). The v4 abstract is the one cited. |
| 22 | Chakrabarty, Laban, Wu 2025 | arXiv, OpenAlex, S2, Crossref | supported | supported | Crossref: CHI 2025, pp. 1–33 | Crossref online 25 Apr 2025; S2 year 2024 (arXiv v1) | 10.1145/3706598.3713559 and arXiv:2409.14509 supported | — |
| 23 | Sanger & Maurer 2026 | arXiv, OpenAlex, S2 | supported | supported | arXiv v2, 16 Mar 2026 | v1 28 Jan 2026 (OpenAlex) | arXiv:2602.03864 supported | The arXiv page was fetched separately (`responses/arxiv-abs/2602.03864.html`). |
| 24 | Kosch et al. 2026 | arXiv, OpenAlex, S2 | supported | supported | arXiv v1 | 19 Sep 2026 | arXiv:2609.23090 supported | — |
| 25 | Shan, Lee, Hao 2026 | arXiv, OpenAlex | supported | supported | arXiv v2, 22 Sep 2026 | v1 28 Aug 2026 | arXiv:2608.27855 supported | No Semantic Scholar record was collected. |
| 26 | van Nuenen 2026 | arXiv, OpenAlex, S2 | supported | supported | arXiv v1 | 24 Apr 2026 | arXiv:2604.22142 supported | — |
| 27 | Zhang et al. 2025 | arXiv, OpenAlex, S2, Crossref | supported (6) | supported | Crossref: ACL 2025 Long, pp. 26940–26961 | 2025; S2 year 2024 (arXiv v1) | 10.18653/v1/2025.acl-long.1308 and arXiv:2409.11704 supported | — |
| 28 | Haverals & Martin 2025 | arXiv, OpenAlex | supported | **version note.** The v2 title (arXiv, OpenAlex) is "The human-authorship halo: attribution bias in literary style evaluation by humans and AI". The v1 title, per one web search (W11) and not seen on arXiv, was "Everyone prefers human writers, including AI" | arXiv v2, 4 Sep 2026 | v1 9 Oct 2025 | arXiv:2510.08831 supported | The v1 title was not confirmed from the arXiv v1 page. |
| 29 | Neurobiber 2025 | arXiv, S2; PyPI for biberplus | supported (4) | supported | arXiv v1 | 25 Feb 2025 | arXiv:2502.18590 supported | biberplus: PyPI 0.4.0, authors Kenan Alkiek and David Jurgens. Its home page points to github.com/davidjurgens/biberplus, which is consistent with the paper's BiberPlus. |
| 30 | Wikipedia: Signs of AI writing | MediaWiki API | n/a (collective) | supported: "Wikipedia:Signs of AI writing", page ID 75478314 | revision 1380587573 by MrPersonHumanGuy, 16 Oct 2026 17:38:05 UTC | — | https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing | The page changes daily. Content claims are tied to this revision. |

### Seed corrections

These fix bibliographic details given in the brief or in Reinhart's notebook.

| Seed as given | Corrected or observed value | Evidence |
|---|---|---|
| "Geng and Trotta preprint on 'advancement' declining in late 2024" | Identified as Geng & Trotta, "Human-LLM Coevolution: Evidence from Academic Writing", arXiv:2502.09606, later Findings of ACL 2025 (10.18653/v1/2025.findings-acl.657). The abstract names "delve" (falling) and "significant" (rising) but **not** "advancement". Their 2024 preprint (arXiv:2404.08627) abstract also does not name it. **Unresolved:** the word may appear in the full text, which was not read. | `responses/031-oa-batch1.json`, `094-arxiv-abs-parsed.jsonl`; web searches W15 and W16 |
| Milička et al. (notebook): "Benchmark of stylistic variation in LLM-generated texts", arXiv 2025 | Version of record: "Benchmark of linguistic variation in LLM‑generated texts", IJCL, online 15 Sep 2026, 10.1075/ijcl.25151.mil | `071-cr-meta-…`, `031-oa-batch1.json` |
| Ming, Hernandez & Juzek (notebook): "Identifying LLM lexical bias: A curation-free triangulated metric for preference-state learning", FLAIRS-39 | Crossref title: "Isolating LLM Lexical Bias". S2 title: "Isolating LLM Lexical Bias: A Curation-Free Triangulated Metric for Preference-Stage Learning". Both say "Isolating", and S2 says "Preference-Stage", not "preference-state". Crossref and S2 still disagree on whether the subtitle is included: **unresolved**. | `104-cr-meta-10_32473_flairs_39_1_141843.json`; `010-s2-cit-reinhart-p1.json` |
| Goulart et al. (notebook): "Goulart, L., Laı́sa Matte, M., Mendoza, A., Alvarado, L., & Velosa, I." | Registries: Larissa Goulart; Marine Laísa Matte (OpenAlex) or M. Matte (S2); Alanna Mendoza; Lee Alvarado; **Ingrid Veloso** (not "Velosa") | `034-oa-batch4.json`, `035-s2-batch-abstracts1.json` |
| Kirilloff et al. (notebook): second author "Carroll, C." | Crossref (MIT Press deposit): **Claudia Carroll**. OpenAlex: "C Jimmy Carroll". **Conflicting**; Crossref is preferred as the publisher deposit, but this was not checked against the HDSR landing page | `101-cr-meta-10_1162_99608f92_6d5fb5ef.json`; `034-oa-batch4.json` |
| Russell et al. 2026 StoryScope (notebook): four authors | Five authors: Jenna Russell; Rishanth Rajendhran; **Chau Minh Pham**; Mohit Iyyer; John Wieting | `033-oa-batch3.json`; `010-s2-cit-reinhart-p1.json` |
| Jiang & Hyland, *Written Communication* (notebook: no volume given) | 42(3), 463–492; online 30 Apr 2025 | `076-cr-meta-10_1177_07410883251328311.json` |
| Jiang & Hyland, *Applied Linguistics* 46(3), 375–391 | Supported. Online 20 Aug 2024 (Crossref); OpenAlex gives 19 Jul 2024; issue 10 Jun 2025 | `077-cr-meta-10_1093_applin_amae052.json` |
| Toney et al. 2026 ACM CSUR (notebook: no volume) | 58(12), 1–28; online 18 May 2026 (Crossref); OpenAlex gives 31 Mar 2026 | `084-cr-meta-10_1145_3806206.json` |
| Juzek & Ward, "Why does ChatGPT 'delve' so much?" | COLING 2025, pp. 6397–6411, ACL Anthology 2025.coling-main.426. The Anthology lists the first author as "Tom S. Juzek"; arXiv and S2 use "Thomas Stephan Juzek". No DOI was found | `093-acl-anthology-2025.coling-main.426.bib`; `094-…jsonl` |
| Dawkins et al. 2025 (notebook: arXiv only) | Also Findings of ACL 2025: 10.18653/v1/2025.findings-acl.695 (OpenAlex) | `033-oa-batch3.json` |

## Secondary rows: script results and manual resolution

The script compared titles and author family names after normalisation. Every row was
re-queried. Rows the script flagged:

| Row | Flag | Resolution |
|---|---|---|
| S6 Ming et al. | title mismatch | See the seed corrections above. **Unresolved**: Crossref's short title against S2's subtitled title. |
| S10 Mizumoto et al. | one source | Crossref added: Applied Corpus Linguistics 4(3), 100106, Dec 2024. Supported. |
| S11 Kirilloff et al. | one source | Crossref added. Second-author conflict as above. **Unresolved.** |
| S16 Kousha & Thelwall | one source | Crossref added: Scientometrics, online 3 Apr 2026, 10.1007/s11192-026-05601-5, no volume yet. S2 still lists only the arXiv DOI. Supported. |
| S17 Alani & Jansen | author mismatch | **Corrected (OpenAlex error).** OpenAlex: "Noor Haitham Saleem; Bernard J. Jim Jansen". Crossref (MDPI deposit) and S2: "Noor H. S. Alani; Bernard J. Jansen". |
| S22 Alghazo et al. | author mismatch | Transliteration variants (Rabab'ah / Rababah). Supported. |
| S23 Kendro et al. | title mismatch | Version difference. arXiv/S2: "Do LLMs produce texts with 'human-like' lexical diversity?". IJAL version (OpenAlex): "Do Large Language Models Produce Texts With 'Human-Like' Lexical Diversity? Evidence From Four ChatGPT Models". The published title is used. |
| S28 Abdulhai et al. | author mismatch | Initials and hyphen variants. Supported. |
| S33 Shaib et al. 2024 | one source | Crossref added: EMNLP 2024, pp. 6416–6431. Supported. |
| S34 Zamaraeva et al. 2025 | author mismatch | Hyphen-character artefact. Supported. |
| S45 | one source | Duplicate of rank 14. |
| S49 Mikros | title mismatch | Apostrophe variant; author shown as "George K." or "Georgios". Supported. |
| S58 Binz et al. | author mismatch | **Conflicting.** OpenAlex lists "Shuchen Wu" twice and leaves out "Dirk U Wulff"; S2 includes Wulff. Not resolved against arXiv; low consequence, because the row is context only. |
| S4 Juzek & Ward (LHF) | — | Crossref adds the version of record: CCIS (ECML PKDD workshops), pp. 243–259, online 1 Apr 2026, 10.1007/978-3-032-19096-3_16. S2 instead gives the OSF DOI 10.17605/OSF.IO/JY48S. These are separate versions and were not merged. |

## Limits of this verification

- Not independent; see the top of this file.
- Arxiv-only rows rest on the arXiv page plus aggregators that copy it.
- Years for conference papers come from Crossref deposits. Exact publication dates within
  2025 or 2026 are only as precise as each registry gives them.
- No row's **content** was verified. A correct identifier says nothing about what a paper
  concludes. Every relevance note in `candidates.md` rests on an abstract (or a title, where
  marked) and still needs a full-text check.
