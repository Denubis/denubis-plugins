---
name: codex-peer-review
description: Use when you want an external critical peer review of a file or directory from OpenAI's codex (GPT-5.5), with its quotes verified against the source before presenting.
user-invocable: true
---

# Codex Peer Review

## Overview

Run OpenAI's `codex` (GPT-5.5) as a single external critic over a target file, shaped by the `critical-peer-review` rubric. The script stages the target's git repo **minus gitignored files and binaries**, so codex can check the target's cross-references (cited code, run logs) within the repo without raw data, secrets, or PDFs in its working tree. **Context stops at the repo**: references that point outside it — cited papers, external datasets — are flagged `[unverified]`, not chased across repos. It is a **second voice**, not Claude's own — present its output source-tagged, do not adopt or merge it.

**Provenance is the spine of this skill.** Codex will sometimes produce a fluent, correctly-formatted review — GRADE matrix, severity tiers, even a faked "Verification" section — of a document it never actually read. A codex review is a *claim*, not a result, until its quotes are checked against the real target. The skill is built to catch that.

## When to use

- You want an outside, non-Claude critique of a draft, design doc, analysis, or postmortem.
- You want a falsification-first review (overclaiming, evidence-grade violations, internal inconsistency) from a different model.

**When NOT to use:**
- For Claude's own review, dispatch `denubis-plan-and-execute:critical-peer-review` directly — this skill is specifically the *external* voice.
- On anything you cannot disclose to OpenAI. The disclosure surface is the target's repo **minus gitignored files** — whatever codex reads from that staging goes to OpenAI. `.gitignore` is the boundary, and it only holds if sensitive data is gitignored: if raw/participant data is *committed* (tracked), it gets staged and sent — glance at what's tracked first. Separately, `-s read-only` does not confine reads, so codex can still read its own well-known paths (`~/.codex`, `~/.ssh`); only an external sandbox (bwrap) closes that. Run on your own machine, on disclosable work, watched.

## How to run

1. **Identify the target** — the file or directory the user named. Require one; do not invent a target.

2. **Run the script.** It stages the target's git repo (minus gitignored files) plus the rubric into a throwaway `/tmp` dir, runs codex with that as its only root, and writes the review to `./.review/<target>.<timestamp>.REVIEW.md` (gitignored and persistent; it auto-drops a self-ignoring `.gitignore` so output never leaks into the repo under review). If the target is not in a git repo, it reviews the file alone with no context.
   ```bash
   bash plugins/denubis-external-agents/skills/codex-peer-review/codex-peer-review.sh <target>
   ```
   It prints the package dir, the staged target path, the review path, and a ready-made smoke-check command.

3. **Provenance gate — MANDATORY, before believing or presenting anything.** See below. Do not skip it, even when the review looks impeccable. *Especially* when it looks impeccable.

4. **Present** the verified review as codex's voice (below).

## The provenance gate (non-negotiable)

A codex review enters the conversation only after its quotes are confirmed to exist in the real files it cites.

- Take 2–3 verbatim quoted phrases from codex's findings (especially the High-severity ones) and `grep -F` each against the file codex attributes it to — the target, or a context file it cites:
  ```bash
  grep -nF '<quoted phrase from the review>' '<the file codex cites>'
  ```
- **Decision rule:** a quote that is not in the file it's attributed to voids that finding. If the review's quotes broadly fail to match — or it cites a file or line range that does not exist — the whole review is a confabulation. **Discard it and report the confabulation. Never present fabricated findings as real.**
- Trust codex's live `exec … succeeded:` traces while they scroll past (they are harness-emitted and real), but the `-o` output file does not save them, so the durable check is the quote-grep — it needs nothing but the review and the file.
- Codex has no internet. Findings it marks `[unverified — needs external check: …]` are honest gaps, not failures; relay them as such.

## Presenting

- Label it clearly as **codex / GPT-5.5's review**, not Claude's. It is a second opinion for the human to weigh.
- Present it as-is after the provenance gate. Do not silently merge it with your own views, dedup it, re-rank its findings by what you think is "genuine," or append your own verdict on top. If you have your own take, give it separately and labelled as yours.

## Quick reference

| Step | Command / action |
|------|------------------|
| Run | `bash plugins/denubis-external-agents/skills/codex-peer-review/codex-peer-review.sh <target>` |
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
