---
name: codex-peer-review
description: Use when you want an external critical peer review of a file or directory from OpenAI's codex, with its quotes verified against the source before presenting.
user-invocable: true
---

# Codex Peer Review

## Overview

Run OpenAI's `codex` as a single external critic over a target file, shaped by the `critical-peer-review` rubric. The model is never pinned here: the script reads the top-level `model` key from your `$CODEX_HOME/config.toml` and passes it through, so the reviewer tracks whatever you have codex set to and moves with new releases without an edit. It prints the model it resolved, which is what the presentation step labels the review with. The script stages the target's git repo **minus gitignored files and binaries**, so codex can check the target's cross-references (cited code, run logs) within the repo without raw data, secrets, or PDFs in its working tree. **Context stops at the repo**: references that point outside it — cited papers, external datasets — are flagged `[unverified]`, not chased across repos. It is a **second voice**, not Claude's own — present its output source-tagged, do not adopt or merge it.

**Provenance is the spine of this skill.** Codex will sometimes produce a fluent, correctly-formatted review — GRADE matrix, severity tiers, even a faked "Verification" section — of a document it never actually read. A codex review is a *claim*, not a result, until its quotes are checked against the real target. The skill is built to catch that. Checking them makes it a *grounded* claim; whether the claims are correct is the human's judgement, not something the check settles.

## When to use

- You want a critique from a separate Codex process, kept distinct from the host agent's voice.
- You want a falsification-first review (overclaiming, evidence-grade violations, internal inconsistency) from a different model.

**When NOT to use:**
- For the host agent's own review, use `denubis-plan-and-execute:critical-peer-review` directly — this skill is specifically the *external Codex process*.
- On anything you cannot disclose to OpenAI. The disclosure surface is the target's repo **minus gitignored files** — whatever codex reads from that staging goes to OpenAI. `.gitignore` is the boundary, and it only holds if sensitive data is gitignored: if raw/participant data is *committed* (tracked), it gets staged and sent — glance at what's tracked first. Separately, `-s read-only` does not confine reads, so codex can still read its own well-known paths (`~/.codex`, `~/.ssh`); only an external sandbox (bwrap) closes that. Run on your own machine, on disclosable work, watched.

## How to run

1. **Identify the target** — the file or directory the user named. Require one; do not invent a target.

2. **Write a one-line focus note.** A specific ask is what makes the review worth running: the value lands when codex is told what to check, not when it roams the repo. Name the load-bearing claims to test, in one line — for a revised document, what the revision was meant to fix; for a fresh one, the decisions you most want a second pair of eyes on. Example: `"check the RQ2 fixes hold and that RQ1 calibration matches the prereg"`. If the user already named what worries them, use that.

   **Do not hand-build context for codex.** The script stages the surrounding repo itself (next step). Do not assemble a `context/` directory of hand-picked files, and do not write the reviewer an orientation README — that is wasted effort the staging already covers. The focus note carries everything an orientation file would, in one line.

3. **Resolve the plugin root from this loaded SKILL.md path**, ascending two directories,
   then run the script with the target and focus note. This is stable in the source tree and
   every provider cache; do not assume the caller is at this repository root. The script
   stages the target's git repo (minus gitignored files and binaries) plus the rubric into
   a throwaway `/tmp` dir, runs codex with that as its only root, and writes the review to
   `./.review/<target>.<timestamp>.REVIEW.md` (gitignored and persistent; it auto-drops a
   self-ignoring `.gitignore` so output never leaks into the repo under review). If the
   target is not in a git repo, it reviews the file alone with no context.
   ```bash
   bash "$plugin_root/skills/codex-peer-review/codex-peer-review.sh" <target> "<one-line focus note>"
   ```
   The focus note is optional and is injected as a priority hint, subordinate to the anti-fabrication grounding rules — it sharpens the review without narrowing the target's scope or relaxing the verbatim-quote requirement. The script prints the package dir, the staged target path, the focus note, the resolved model, the review path, and a ready-made smoke-check command.

   Unrecognised options and surplus positionals are fatal rather than absorbed. A tolerant parser once turned a mistyped `--includ evidence.md` into a focus note reading `--includ` and dropped the evidence silently, so the operator believed a file had been sent that never was.

4. **Staging extra evidence — `--include <path>`, repeatable.** Force-stages a path the default surface excludes: a generated diff, a cited paper, a gitignored artefact. It is deliberately not bounded by the repository or by `.gitignore`, which is exactly why it is gated.

   ```bash
   … <target> "<focus note>" --include /path/to/evidence.md --include-confirmed
   ```

   Everything before transmission is local. The script stages into `/tmp`, prints a manifest enumerating **every file** each include actually stages (a directory include discloses its whole text tree, and a name is not a manifest), and then stops for a decision. At a terminal that is a `[y/N]` prompt. Non-interactively it aborts unless `--include-confirmed` is passed, so a model composing the command line cannot disclose files by omission — the flag is the decision, and it is recorded in the command line that carried it.

   Printing alone was the earlier design, and it was a receipt rather than a control: by the time anyone read it the files were in flight, and the usual reader of that receipt is a model rather than the operator whose files are being sent.

5. **Provenance gate — MANDATORY, before believing or presenting anything.** See below. Do not skip it, even when the review looks impeccable. *Especially* when it looks impeccable.

6. **Present** the provenance-checked review as codex's voice (below).

## The provenance gate (non-negotiable)

A codex review enters the conversation only after its quotes are confirmed to exist in the real files it cites.

**What the gate does and does not establish.** It answers one question: did codex read the real files? That is provenance, and nothing more. A quote can exist verbatim while the claim built on it is false, the severity attached to it is inflated, or the finding is a false positive against a design decision codex could not see. Those remain codex's claims, to be weighed by the human, and no grep can settle them. So a review that passes this gate is *provenance-checked*, never *verified*.

- Take 2–3 verbatim quoted phrases from codex's findings (especially the High-severity ones) and `grep -F` each against the file codex attributes it to — the target, or a context file it cites:
  ```bash
  grep -nF '<quoted phrase from the review>' '<the file codex cites>'
  ```
- **Decision rule:** a quote that is not in the file it's attributed to voids that finding. If the review's quotes broadly fail to match — or it cites a file or line range that does not exist — the whole review is a confabulation. **Discard it and report the confabulation. Never present fabricated findings as real.**
- Trust codex's live `exec … succeeded:` traces while they scroll past (they are harness-emitted and real), but the `-o` output file does not save them, so the durable check is the quote-grep — it needs nothing but the review and the file.
- Codex has no internet. Findings it marks `[unverified — needs external check: …]` are honest gaps, not failures; relay them as such.

## Presenting

- Label it clearly as codex's review, not Claude's, naming the model the script reported on its `model:` line (**codex / `<model>`'s review**). Read that value off the run rather than assuming one, since it follows the operator's config and changes when they change it. It is a second opinion for the human to weigh.
- Present it as-is after the provenance gate. Do not silently merge it with your own views, dedup it, re-rank its findings by what you think is "genuine," or append your own verdict on top. If you have your own take, give it separately and labelled as yours.

## Quick reference

| Step | Command / action |
|------|------------------|
| Run | `bash "$plugin_root/skills/codex-peer-review/codex-peer-review.sh" <target> "<one-line focus note>"` |
| Find review | `./.review/<target>.<ts>.REVIEW.md` (path printed as `review: …`) |
| Verify (mandatory) | `grep -nF '<quote>' '<cited file>'` (target or context) for several findings |
| On quote mismatch | discard the review, report confabulation |
| Present | source-tagged as codex's voice, unmerged |

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Presenting the review without the quote-grep | Always run the provenance gate first. A polished review is not evidence it read the file. |
| Trusting the faked "Verification" section | That section is codex's prose, not proof. Only your own grep counts. |
| Merging codex's findings into your own review | Keep voices separate; present codex's as codex's. |
| Running on sensitive content | The repo minus gitignored goes to OpenAI. Ensure raw/sensitive data is gitignored (not committed) before running. |
| Inventing a target when none was given | Require an explicit file/dir; codex confabulates when under-specified. |
| Hand-building a `context/` dir or reviewer README | The script stages the repo for you. Pass a one-line focus note as the second argument instead; it carries the orientation in one line. |
| Running with no focus note | Codex roams the repo unfocused and returns a sprawling, low-signal review. A one-line focus note on the load-bearing claims is what makes the run worth it. |
