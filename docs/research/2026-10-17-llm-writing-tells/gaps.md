# Gaps and decisions before a systematic review

Scope of every statement below: the collection searched on 2026-10-17 (see `search-log.md`),
assessed at title or abstract level. "Not found" means not found in that collection by the
recorded searches. It is not a claim that the work does not exist.

## 1. Coverage gaps

### 1.1 Measurements of models released from mid-2025 onward

- The abstracts read rarely name GPT-5 or later, Claude 4.5 or Claude 5, Gemini 3 or later, or
  Llama 4 or later. The models abstracts name are mostly GPT-4o, GPT-4.1, Claude 3.5 Sonnet,
  Llama 3 and o1 (Reinhart, Russell, Chakrabarty et al., Freeburg).
- The exceptions are partial:
  - Nakajima & Mizuno (23 versions up to August 2026) measures only vocabulary and detector
    transfer.
  - Zamaraeva et al. 2026 uses "GPT models" and a 2026 arXiv corpus without saying which
    GPT models in the abstract.
  - Shan et al. and van Nuenen name current models only in search snippets, which I could not
    confirm.
- Wu et al. (evidence cutoff 1 Oct 2026) say that "comparable measurements of the newest
  releases are sparse in the retrieved set". My search agrees within its scope.
- **Not found:** a feature table (Biber-style or rhetorical) for GPT-5-era, Claude 4.5/5-era,
  Gemini 3-era or Llama 4-era output against a matched human corpus.

### 1.2 Feature-level gaps (T1)

| Wanted feature | What the collection has | What it lacks |
|---|---|---|
| Participial clauses, nominalisation | Reinhart et al. (Biber features; "noun-heavy, informationally dense" per the significance statement); Mak & Walasek (nominalisation rose in student writing); Terčon & Dobrovoljc survey (more nouns) | The participial-clause and nominalisation multipliers often attributed to Reinhart et al. are **not** in the abstracts checked. Full text is needed. No frontier-model figures. |
| Triads, rule of three, series length | Bakhshi 2026: tricolon about twice the human-expert rate (single author; models not named); Wikipedia lists "rule of three" | Only one measured study was found, after a web search, two Semantic Scholar searches and one Crossref search. No study of series length (three against four or five items). |
| Negative parallelism, contrast frames | Zamaraeva et al. 2026 ("rather than": seven times the 2019 rate in 2026 papers); Boggia 2026 (epanorthosis index: overshoot or undershoot depends on genre); Wikipedia's three subtypes | Neither study measures "not just X but also Y" separately. The Mandarin study (Peng et al., arXiv:2610.22249) was excluded by the language limit. |
| Hedging and downtoners | Sanger & Maurer (less hedging in abstracts classified as LLM-assisted); Bakhshi (twice as many *performed* hesitancy markers); Jiang & Hyland ESP (fewer hedges, from a secondary source only); Liu 2026 (hedges rise under self-training, small models) | **Contradiction, flagged:** some studies report less hedging, others more hesitancy markers. The constructs differ (hedging language, performed hesitancy, interactional metadiscourse), and so do genres and models. Full-text definitions are needed before these can be combined. |
| Punctuation (em dash, semicolon, colon) | Freeburg (em-dash rate depends on the model and resists suppression); Czuma ×2 (em-dash prevalence in medRxiv and congressional texts rose through 2025); van Nuenen (more elaborate punctuation in rewrites); Sanger & Maurer (more commas) | No measured semicolon or colon densities for frontier models. **Time and model dependence, flagged:** Wikipedia now lists em-dash overuse as "historical (2022–September 2026)" and reports suppression from GPT-5.1. The Economist (30 Jul 2026, unread; known only from reposts) reportedly found that only Claude used more em dashes than professional writers and that ChatGPT used fewer. The scholarly studies above stop at 2025 data or do not name current models. Unresolved. |
| Sentence-length variance, burstiness | Kosch et al. (CHI sentence rhythm "remained irregular"); Zheng (ICLR reviewers still reward sentence-length variability); Cao et al. (temporal, not sentence-level) | No length-normalised burstiness measure for frontier models. A NeurIPS 2026 page titled "Burstiness Was Measured Wrong, and Prompting Cannot Aim It" was seen in a search snippet but could not be identified (W18, W20). Gude et al.'s sentence-length figures were seen only in a snippet. |
| Bold-label list formatting | Zhang et al. (preference models are biased towards lists and bold); Freeburg (headers, bullets and bold can be removed by instruction); Wikipedia ("inline-header vertical lists", overuse of bold) | No measured frequency of bold-label lists in human against frontier-model prose. |
| Metadiscourse, signposting | Jiang & Hyland (metadiscourse, engagement markers, bundles; GPT-4-era ChatGPT); Lin & Liu (stance and engagement in abstracts); Alani & Jansen (rises in contribution signalling and connective phrasing in abstracts) | Nothing specific to frontier models. The ESP metadiscourse abstract was unavailable. |
| Lexical diversity | LLM below human: Terčon survey, Miletić & Falk, Dönmez. LLM above human or source: Shan (generation), van Nuenen (rewrites), Cao, Sanger & Maurer. Comparisons between models only: Gude (newer instruction-tuned models below older base models); Kendro (GPT-4.5 above older ChatGPT models, while all models differ from humans). El Attar: robust signal, direction not stated | **Contradiction, flagged.** The direction differs by measure, genre, task (generation, rewriting or editing) and model generation. Do not use it as a one-direction tell until full-text measures are compared. |

### 1.3 Marker decay (T2)

- **Word-level decay is documented** at abstract level:
  - Geng & Trotta: "delve" fell after early 2024.
  - Mak & Walasek: markers fell in 2025.
  - Thelwall & Kousha: some terms fell from 2024 to 2025.
  - Nakajima & Mizuno: vocabulary turns over between model versions.
  - Wikipedia gives vocabulary lists by model era.
- **Prevalence studies still show rises.** Holzwarth et al. (89% of papers by the end of
  2025), Siler (57% in 2025) and Kousha & Thelwall report increases. This fits "specific
  words fade, overall LLM influence grows", but the studies use different word lists, so
  their results are not commensurable.
- **The brief's seed is unverified.** The claim that Geng and Trotta report "advancement"
  declining in late 2024 was not found in their 2024 or 2025 abstracts or in two targeted web
  searches. It may be in the full text (not read) or attributed to the wrong paper.
- **Not found:** longitudinal tracking of structural tells (antithesis, triads, participial
  clauses) across successive model releases from GPT-5 onward. Zamaraeva et al. compares only
  2019 with 2026. Gude et al. compares two generations of models.

### 1.4 Perception and blind testing (T3)

- Blind or semi-blind designs found:
  - Russell et al. 2025: expert LLM users were accurate on GPT-4o, Claude and o1 text.
  - Chakrabarty, Ginsburg & Dhillon 2025: blind expert readers penalise the quirks of
    prompted models, and fine-tuning removes them.
  - Haverals & Martin 2025: authorship labels reverse how readers judge identical features.
  - Zamaraeva et al. 2026: annotators blind to source rarely agree on which uses are
    "annoying".
  - Hadan et al. 2024: reviewers could not reliably discriminate.
- Perception without blind validation: Georgiou 2026 (professors), Miletić & Falk (experts
  rate LLM-improved text as more understandable), the SAGE blog, and Wikipedia.
- **Not found:** a 2025–2026 blind test of editors or reviewers on manuscripts written with
  frontier models, or a test of whether named structural tells (em dash, triads, antithesis)
  still predict authorship once readers are blinded.

### 1.5 Tooling (T4)

- Found: Biber-feature tooling (pseudobibeR on CRAN; biberplus and MFTE ports on PyPI; the
  Perl MFTE repository; Neurobiber), corpora (AI-Brown/AI-Koditex, LAMP, Russell et al.'s
  annotations), and phrase-level tools (Antislop, the Juzek et al. metrics).
- Not checked: how the taggers compare. Neurobiber's abstract says it is faster than "existing
  open source systems", and the brief says it compares Biber taggers. Accuracy against Biber
  or MAT is unverified at abstract level. The distribution channel for Neurobiber was not
  found (it is not on PyPI).
- **Not found:** an open detector or feature extractor for antithesis or correction frames,
  tricolon, or bold-label lists. Bakhshi's and Boggia's pipelines are described, but no code
  URL appears in their abstracts.

### 1.6 Academic manuscripts, peer review, and guidance (T5)

- Peer-review text: Fung et al. (homogenised verb–object constructions), Liang et al. 2024,
  Abdulhai et al. 2026, and Zheng 2026.
- Manuscripts: Zamaraeva et al. (NLP papers), Czuma (medRxiv), Miletić & Falk (ACL
  Anthology), Kosch et al. (CHI), Sanger & Maurer (ASCE), Thelwall & Kousha (MDPI), Kobak
  and Holzwarth (PubMed and PMC), Siler, Botes, Alani & Jansen, and others.
- **Publisher guidance that names structural tells:** only the SAGE blog (June 2025). It
  lists repetitive phrasing and over-explanation, generic language, "flawless but empty"
  prose, paragraphs that all start the same way or follow a rigid pattern, and repetitive or
  generic section headers. It cites no research. COPE, ICMJE, Elsevier and Springer Nature
  guidance were not checked directly. He & Bu report that journal policies are mostly about
  disclosure.

## 2. Contradictions, flagged and unresolved

1. Lexical diversity direction (§1.2).
2. Hedging direction (§1.2).
3. Whether the em dash is still a tell, depending on time and model (§1.2).
4. Siler 2026 (PNAS) is challenged by Topaz and Bahl. Only Siler's reply (10.1073/pnas.2621834123)
   was located; the critique itself was not found.
5. The "advancement" seed (§1.3).
6. Model naming. Wu et al.'s reference list (from Semantic Scholar) includes non-scholarly
   sources titled "GPT-6 Astra. Release page…" (attributed to OpenAI), "Ask HN: Is Astra's
   writing starting to bother anyone else?", "Testing GPT-6 Astra…", "Claude Opus 5.5" and
   "Sonnet 5.5". Wikipedia's mid-2026 vocabulary list cites "ChatGPT-6 Astra for Writing Full
   Review". **"Fable" did not appear** in anything inspected. I have not inferred what model
   the user means by "Fable and Astra grade" from these sightings. That mapping is the user's
   decision (§3, item 1).

## 3. Decisions the user would need to make before a systematic review

1. **Target model set.** Which named releases count as "Fable and Astra grade", and from what
   release date? The literature names models (for example "GPT-6 Astra" in non-scholarly
   references) inconsistently, and this sets the date window and the search terms.
2. **Genre scope.** Academic manuscripts and peer reviews only, or all registers? Genre
   affects style more than source does (Rallapalli et al.), and indicators depend on context
   (El Attar et al.).
3. **Human baseline.** Corpora from before 2023 only, or contemporaneous human text? Text
   written after 2023 is contaminated by LLM assistance (Kobak, Holzwarth, Siler).
4. **Generation or editing.** Are AI-edited texts in scope? Shan et al. report different
   signatures for generation and editing, and most manuscripts involve editing.
5. **Feature inventory and measurement standard.** Which tagger (pseudobibeR, biberplus,
   Neurobiber, MFTE), which normalisation (per 1,000 words; burstiness normalised for length),
   and which definitions for hedging, antithesis and tricolon?
6. **Non-scholarly sources.** Should Wikipedia, journalism (The Economist, Washington Post),
   vendor blogs and practitioner catalogues count as evidence, or only as leads?
7. **Language scope.** Keep English only (this excludes the Mandarin "Not X, but When" study)
   or extend it?
8. **Full-text acquisition.** Approve a Zotero scout subcollection and acquisition through
   `using-bibliography`. No synthesis claim beyond the abstract can be made without it.
9. **Independent verification.** Dispatch a fresh reviewer to re-verify identity and
   relevance. This check was not independent.

## 4. Not checked

- No full texts were read; all relevance is abstract-level, and rank 20 and rows S9, S15,
  S52 and S57 are title-only.
- No abstract was available for Jiang & Hyland ESP, Goulart et al., Tao et al. 2025, Ciriello
  2026, Sourati et al. 2026 (OpenAlex), Chang 2026, or Bagdasarov & Alves 2026 (LREC).
- Not retrieved: The Economist "How to spot AI writing" (30 Jul 2026); the Washington Post
  analysis (Nov 2025, cited by Wikipedia); Rudnicka's Scientific American piece (Jul 2025);
  Leppänen et al. (listed in Reinhart's notebook, not queried).
- The arXiv API was unavailable (HTTP 429), and PubMed lookups failed.
- Forward citation was not run from Jiang & Hyland, Goulart, Mizumoto, Mak & Walasek,
  Kirilloff, Ming et al., or the 2026 hubs (each had 10 or fewer citing works).
- Citation counts were not used for ranking; the counts from Semantic Scholar and OpenAlex on
  2026-10-17 are in the saved responses.
