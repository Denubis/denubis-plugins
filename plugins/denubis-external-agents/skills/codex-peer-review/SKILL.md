---
name: codex-peer-review
description: Use when you want a critical peer review of a file or directory from OpenAI's codex (GPT-5.5) as a heterogeneous second voice. Runs codex against the target using the critical-peer-review rubric, then verifies the review's quotes against the real file before presenting, so a confabulated review cannot pass as real.
user-invocable: true
---

# Codex Peer Review

## Overview

Run OpenAI's `codex` (GPT-5.5) as a single external critic over a file or directory, shaped by the `critical-peer-review` rubric. It is a **second voice**, not Claude's own — present its output source-tagged, do not adopt or merge it.

**Provenance is the spine of this skill.** Codex will sometimes produce a fluent, correctly-formatted review — GRADE matrix, severity tiers, even a faked "Verification" section — of a document it never actually read. A codex review is a *claim*, not a result, until its quotes are checked against the real target. The skill is built to catch that.

## When to use

- You want an outside, non-Claude critique of a draft, design doc, analysis, or postmortem.
- You want a falsification-first review (overclaiming, evidence-grade violations, internal inconsistency) from a different model.

**When NOT to use:**
- For Claude's own review, dispatch `denubis-plan-and-execute:critical-peer-review` directly — this skill is specifically the *external* voice.
- On anything you cannot disclose to OpenAI. Codex runs `-s read-only` (writes and network for its shell commands are blocked) but its reads are **not** confined, and whatever it reads is sent to OpenAI. Treat the run as "this content goes to OpenAI." Only run it on your own machine, on work you are willing to disclose, and watch the run.

## How to run

1. **Identify the target** — the file or directory the user named. Require one; do not invent a target.

2. **Run the script.** It bundles the rubric + the target into a throwaway working dir and runs codex against only that root:
   ```bash
   bash plugins/denubis-external-agents/skills/codex-peer-review/codex-peer-review.sh <target>
   ```
   It prints the package dir, the review path (`*.REVIEW.md`), and a ready-made smoke-check command.

3. **Provenance gate — MANDATORY, before believing or presenting anything.** See below. Do not skip it, even when the review looks impeccable. *Especially* when it looks impeccable.

4. **Present** the verified review as codex's voice (below).

## The provenance gate (non-negotiable)

A codex review enters the conversation only after its quotes are confirmed to exist in the real target.

- Take 2–3 verbatim quoted phrases from codex's findings (especially the High-severity ones) and `grep -F` each against the actual target file:
  ```bash
  grep -nF '<quoted phrase from the review>' '<the real target file>'
  ```
- **Decision rule:** a quote that is not in the target voids that finding. If the review's quotes broadly fail to match — or it cites a file or line range that does not exist — the whole review is a confabulation. **Discard it and report the confabulation. Never present fabricated findings as real.**
- Trust codex's live `exec … succeeded:` traces while they scroll past (they are harness-emitted and real), but the `-o` output file does not save them, so the durable check is the quote-grep — it needs nothing but the review and the file.
- Codex has no internet. Findings it marks `[unverified — needs external check: …]` are honest gaps, not failures; relay them as such.

## Presenting

- Label it clearly as **codex / GPT-5.5's review**, not Claude's. It is a second opinion for the human to weigh.
- Present it as-is after the provenance gate. Do not silently merge it with your own views, dedup it, re-rank its findings by what you think is "genuine," or append your own verdict on top. If you have your own take, give it separately and labelled as yours.

## Quick reference

| Step | Command / action |
|------|------------------|
| Run | `bash plugins/denubis-external-agents/skills/codex-peer-review/codex-peer-review.sh <target>` |
| Find review | path printed as `review: …REVIEW.md` |
| Verify (mandatory) | `grep -nF '<quote>' '<target file>'` for several findings |
| On quote mismatch | discard the review, report confabulation |
| Present | source-tagged as codex's voice, unmerged |

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Presenting the review without the quote-grep | Always run the provenance gate first. A polished review is not evidence it read the file. |
| Trusting the faked "Verification" section | That section is codex's prose, not proof. Only your own grep counts. |
| Merging codex's findings into your own review | Keep voices separate; present codex's as codex's. |
| Running on sensitive content | Reads go to OpenAI. Only run on disclosable work, on your machine, watched. |
| Inventing a target when none was given | Require an explicit file/dir; codex confabulates when under-specified. |
