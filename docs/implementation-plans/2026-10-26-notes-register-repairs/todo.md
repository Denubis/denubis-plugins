# Notes-directory register repairs across repositories — work queue

Rulings: ADR 0043 (the notes directory holds nothing durable that other machines rely on),
ADR 0044 (the ticket file stays in the notes directory; answered questions move to records
about their subject; decision 3 commissions the ticket-file audit). Brian, 2026-10-26:
"let's go fix those repos please. both telling and the 15."
Survey: a read-only Sonnet scan on 2026-10-26 over 213 repositories and 356 register files,
summarised in the supervision-infrastructure worklog for that day.

Repair, per repository: move any register under the notes directory into tracked `docs/`
(`docs/decisions/`, or the repository's existing register location), keep each record's
original-message resolvers, reword decision lines that direct durable material into the notes
directory, repoint citations of notes paths to the landed location or to a transcript
resolver, and index the result. Workers edit and verify; commits wait for Brian's word in each
repository. The ticket file stays in the notes directory (ADR 0044); each repair audits it
and moves any answered question or status prose into the record about its subject.

## Wave 1 — registers that direct durable material into the notes directory

- [x] `~/people/Brian/brian-ed3d-gemini-argon` (no edits; fast-forward after push): not a separate project. The worker found it is
      a stale clone of this repository (origin `Denubis/denubis-plugins`, at the 2026-10-01
      commit, 34 behind, with one stray uncommitted CLAUDE.md edit). Repair is a fast-forward
      to main after today's commits are pushed, not a hand edit; Brian decides the stray edit.
- [x] `~/people/Brian/approver` (edited, uncommitted, 2026-10-26; register only; the tree was
      otherwise clean): ADR-0078's four notes-path citations are prose; superseded ADR-0031
      kept as history. That repository tracks its notes directory (ignoring only Local Mail),
      so its notes citations were never gitignored. Its own AGENTS.md and ADR-0078 amendment
      put the ticket file at `docs/open-questions.md`, 25 tracked files including code cite it,
      and it is a live ticket file with one open question; approver keeps its own register, so
      whether ADR 0044 reaches it is Brian's call (recommendation: it does not; the notes
      directory there is tracked, so the drift ADR-0078 fixed cannot return). Round two: every
      live IGNORED/EXCHANGE citation (ADRs 0008, 0014, 0058, 0078 and the resource-budget
      follow-up) is prose; the frozen checker fell from 104 to 88 findings with nothing added. Found: the
      checker crashes on a `~other/y` example token (prompt 27), and 87 ABSENT findings in a
      5,000-line register are example paths that now block every commit touching it.
- [x] `~/people/Phaedra/Paper` (edited, uncommitted, 2026-10-26): eight register files copied
      into `docs/decisions/` with provenance headers; the originals remain for Brian to delete
      at commit time; ADRs 0002, 0003, 0007 describe the local-mail folder and the exchange
      output in prose; AGENTS.md points at `docs/decisions/`. gitleaks over the new directory
      found nothing. Left: one notes path inside Brian's quoted words in ADR 0002 (the checker
      learns to treat quoted lines as advisory, prompt 26); ADRs 0006 and 0007 cite two
      untracked files in the repository root. Ticket file: Q1 (git init, "yes, proper init
      please") is answered and needs its own decision record; C1 is answered and landed in ADR
      0007, so it leaves the file; the "parked" heading is status wording; its description
      line and AGENTS.md line 40 still say answers sit beside questions, against ADR 0044.
      Needs Brian: does that repository's local-mail convention stand (ADR 0003 flags that
      the notes directory is never transport, and ADR 0007's review evidence lives only there)?
- [x] `~/people/Brian/sage-srm-guide`: DEFERRED by Brian on 2026-10-26 ("let's kinda just let
      sage be its own thing, there is... information protection stuff there"); revisit when the
      reviewer reports are back. Ticket Q108 in that repository's ticket file holds the open
      items. Work already done (edited, uncommitted, 2026-10-26): the guide register
      note copied to `docs/reference/guide-register.md` with provenance and ADRs 039 and 062
      linked to it; ADR 046, the register (lines 76, 103) and ADRs 024, 030 describe the ticket
      file in prose. Kept: "becomes eligible for Git tracking" in ADR 046, because that
      repository tracks its ticket file by a gitignore exception Brian approved on 7 October.
      Unchanged: ADRs 047 and 032 cite notes in INTS1302, a different, non-Git project. Its
      ticket file holds no tickets; one stale migration line could go. Needs Brian: 19 ADR
      citations into its exchange directory and 5 into its third-party `inputs/` (clearance
      rule), one of them inside a closed ticket's never-edited question; which copy of the
      guide register is authoritative, since the academic-writing skill loads only from notes;
      the docs copy still cites a notes path in another person's repository that the PII scan
      lists. The ADR 039/062 links and the new file must commit together.

## Wave 2 — registers living inside the notes directory (move into `docs/`)

- [x] `~/people/Brian/2026-promotion` (10 records copied; AGENTS.md and README repointed; no remote, no commits; two citations of its confidential gitignored sources become prose; its 575-line ticket file is almost entirely answers, audited not moved)
- [x] `~/people/Brian/localscribe` (2 records copied; public remote; its CLAUDE.md forbids private machine paths in tracked files and the record carries three session-file resolvers, for Brian; answered ticket sections 3–6 removed as already in the record; the record depends on an untracked design document that must commit with it)
- [x] `~/people/Brian/sillytavern-deploy` (merged as 0007–0012 into `docs/architecture/decisions/` with a new index; one runbook citation repointed; internal org remote; three pre-existing exchange citations in ADRs 0005/0006 and the runbook need Brian: land the draft ADR and critique or reword; CLAUDE.md:147 still says running state belongs in notes)
- [x] `~/people/Brian/tmux-codex-quota` (2 records copied; retired checkout, no remote; its ruling governs code now in this repository's statusline, so its durable home may be this register)
- [x] `~/people/Huachen/maxmyliteracy.com` (copied 2026-10-26; AGENTS.md:5 repointed; public remote on Brian's GitHub; one ABSENT pointer to a sibling project needs Brian's wording)
- [x] `~/people/Jennifer/SupervisionGuidanceNote` (copied; CLAUDE.md:30 repointed; no remote; its ticket file is mostly answered questions without resolvers, and two notes hold durable content CLAUDE.md cites)
- [x] `~/people/Jodie/BJET-Phase1-Longi-MixedMethods-RegReport` (copied; two paths put in prose; no remote; that project deliberately tracks its notes directory, so Brian confirms the move)
- [x] `~/people/Nathan/transcriber` (copied; no remote; one ABSENT resolves when worktree work lands)
- [x] `~/people/Shawn/faims.edu.au` (copied; BLOCKER for commit: it is a Jekyll site whose build publishes everything not excluded in `_config.yml`, and `docs/` is not excluded, so committing the register would publish it on faims.edu.au; Brian ruled 2026-10-26 "that's going to be specialcased and that's fine, or _docs or something" (session 3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29 line 6713); `docs/` added to the `_config.yml` exclude list, since `_docs` there is already a published collection. Organisation remote. Record 005 quotes nine other people's names inside Brian's words)
- [x] `~/people/Brian/bbs-cv-overleaf` (RDA record landed as 001 in `docs/decisions/`, index line repointed; another session is editing that tree; its empty `docs/open-questions.md` belongs in notes under ADR 0044; the "single Macquarie entry" ruling lives only in a WIP note with no record)
- [x] `~/people/Brian/cc-search-chats-plugin-python` (record landed as 0010; worklog repointed; public remote. BLOCKED in part: ADR 0009:20 and three plan lines cite two notes records that exist only on the laptop, so that register's move must be finished there or the citations reworded)
- [x] `~/people/Brian/expenses` (4 records plus index copied; AGENTS.md, README, CLAUDE.md repointed; no remote; three citations of its gitignored financial data become prose; resolvers are session-relative without ids)
- [x] `~/people/JP/philosophyofwork` (37 records copied; CLAUDE.md:255 repointed; ticket-file citations in 0002/0009 are prose; organisation remote, private. Left: three mechanism path tokens (0028:39, 0030:42, 0036:14) to put in prose, one evidence path (0004:45) for Brian; eight plan lines and pyproject.toml:51 still cite the notes register; its ticket file is entirely answered questions, Q11–Q42, with the Q33 ruling already in record 0032)
- [x] `~/people/Maryam/CollegeOfLaw` (10 records copied; AGENTS.md and README repointed; no remote, no commits yet; that project deliberately tracks its notes directory and its AGENTS.md keeps answered questions in the ticket file, both against today's rulings, for Brian; six other links still point at the originals)
- [ ] `~/people/Phaedra/Paper` (with wave 1)

## Wave 3 — citations only

- [ ] `~/people/llm/approxup` ADR 0003:108; `~/people/Brian/vuln-watch` ADR 0001:176;
      `~/people/Huachen/google-live` adr-mining and register lines;
      `~/people/Huachen/ai-lang-tool-eald-prototype` eleven Source lines;
      `~/people/Mark/2026-WinterSchool` seven lines; `~/people/Jodie/techethicsai.au` two
      lines; `~/people/Brian/PromptGrimoireTool`, `~/people/Maryam/EmperorClothes`,
      `~/people/Maryam/CollegeOfLaw` mentions to confirm as harmless.

## Ticket files

28 repositories hold the ticket file in their notes directory; two (approver, bbs-cv-overleaf)
hold an `open-questions` file under `docs/`. Each stays in the notes directory under ADR 0044; the two
`docs/` copies are audited and, if they are ticket files, moved back into the notes directory
with their answered content landed. Every ticket file is audited for answered questions.

## Checker follow-ups found by the repairs

- `--all` never selects `docs/decisions/` or an `adr-register.md` file register unless the
  repository's finding aids name them; sage-srm-guide reported a false clean (0 findings)
  until `--register docs/decisions --records docs` was passed (50 findings). Add
  `docs/decisions` and the register-file form to the defaults; re-run the survey repositories.
- sage-srm-guide: 22 exchange-directory citations and 5 citations of its gitignored
  third-party `inputs/` in ADRs. Landing or rewording each is a per-file disclosure decision
  for Brian; the worker inventories them.

- Quoted human words containing a notes or exchange path block the checker (Phaedra/Paper ADR
  0002); quoted lines become advisory for every kind (prompt 26).
- Register discovery reads tracked files only, so a freshly moved or new register is unseen
  until tracked (prompt 26).
- This repository: the plugins workers measured 30 IGNORED, 2 EXCHANGE and 30 WORKTREE
  findings across all 178 tracked `docs/` files, 56 of them in historical audits and plans
  under `docs/audits`, `docs/design-plans` and `docs/implementation-plans` that `--all` does not
  read. They block the next commit that touches each file; a deliberate tidy is its own task.

## Follow-ups in this repository

- ADR 0005 amendment (2026-10-26): the default decision register is `docs/decisions/`, not the
  notes directory. The three skills that still name the notes directory as the default register
  (`recording-project-notes`, `scanning-project-notes`, `supervising-codex`) need releases.
- gemini-argon's stale ticket file: delete or trim to Q4 when that clone is fast-forwarded.

## Open with Brian

- The word to commit in each repaired repository.
- The global instruction line naming `docs/open-questions.md` (ADR 0044 decision 4).

## Checker false positives found in wave 2 (for the checker's owner)

- `path.md:1944-1950` line ranges are not stripped (sillytavern 0009:48).
- A path containing a space is split at the space (sillytavern 0009:134).
- Brace notation `sources/{docx,pdf,email}` is read as one path (SupervisionGuidanceNote).
- A branch name such as `fix/queued-human-dialogue` reads as a path (BJET).
- A worktree path outside the checkout (`/tmp/...` linked checkout) is skipped as external
  (BJET), though it is the same defect class.
