# Codex critical peer review (codex-only test) — rationale & rules

Run OpenAI's `codex` (GPT-5.5) as a second, untrusting voice over something you're working
on, shaped like the repo's `critical-peer-review` agent.

**This is a TEST only.** No Claude voice, no merge, no presentation layer. Run codex in
isolation, **verify it actually reviewed your target**, then build the proper joint
(Claude + codex) review on top of what survives.

> **Scar from the first live run:** told to review pasted text, codex reviewed nothing of
> the sort. It confabulated an entire review of a file that does not exist
> (`tmp-amanda-proposal.md`), invented line citations (`:31-40`), and wrote a fake
> "Verification" section claiming it had run `find` and `git status`. The pasted target
> never entered the review. Verified after the fact: no such file by name, by content, or
> in git — pure fabrication. **The recipe is built to catch that, because it will happen
> again.**

This document is the rationale and the rules. **The live recipe is the script.**

---

## How to run it (canonical)

The runner now lives in the `denubis-external-agents:codex-peer-review` skill, not
in `docs/`:

```bash
bash plugins/denubis-external-agents/skills/codex-peer-review/codex-peer-review.sh <file-or-dir-to-review>
```

It bundles the rubric (`review-method.md`, a copy of `critical-peer-review.md`, beside
the script) and your target into one throwaway working dir, runs `codex exec -s read-only`,
writes the review to a sibling `*.REVIEW.md`, and prints the exact provenance check to run.
The prompt it feeds in is `peer-review-smoke-prompt.md` in the same skill dir. This file is
the rationale record; the skill's `SKILL.md` is the operational instruction.

---

## The rule that matters most

**A codex review is a claim, not a result, until its citations are checked against the
real target.** Codex will produce a fluent, correctly-formatted review — faked
"Verification" section and all — for a document it never read.

The durable check is mechanical: take a verbatim quote from a finding and `grep -F` it in
the target file. If it isn't there, that finding — usually the whole review — is
fabricated; discard it. This needs nothing but the review and the file, which is why it is
the canonical check.

(Codex's live *exec traces* — `exec … succeeded: <stdout>` — are real and trustworthy
while they scroll past, but `-o` does not save them, so do not build your check on them.
This is a real gap the dogfood caught in an earlier draft of this doc.)

---

## Verify EVERY run

1. **Provenance first — before believing anything.** For each finding, `grep -F` its
   verbatim quote in the target file (the script prints the exact command). One quote that
   isn't there voids the finding, and usually the whole review — that is how the first
   fabrication was caught.
2. **Network is blocked** — confirmed at the syscall level (a sandboxed `curl` fails DNS;
   a raw socket returns `Operation not permitted`). Codex cannot web-search or fetch, so
   findings cannot be silently padded from the internet. (A sandbox invariant, not a
   per-run risk.)
3. **`-o` wrote the file** — confirmed mechanism (harness write, not a sandboxed command).
   Missing/empty means something failed, never "no findings".
4. **Codex followed the rubric** vs freelancing its own shape. If it freelances, paste the
   rubric body into the prompt instead of bundling it as a file.

---

## Sandbox reality (verified — and not what "read-only" sounds like)

Verified empirically on this version: **`-s read-only` blocks writes and network but does
NOT confine reads.** Network — a sandboxed `curl` fails DNS and a raw socket returns
`Operation not permitted`. Reads — a sandboxed command read a file outside the working
root. So a codex command can read *anything on disk* — `~/.codex/config.toml` (your
context7 key), `~/.ssh`, other projects — and send it to OpenAI. `--ignore-user-config`
only stops codex *loading* that config; it does not stop a command *reading* the file.

- **For this test:** acceptable — your machine, your work, watched run, project egress
  already accepted. But the blast radius is the whole disk, so don't run it where that
  matters and don't leave it unattended.
- `--ignore-user-config` still earns its place: it drops the context7 MCP credential,
  trust levels, and hooks. A real reduction, not a confidentiality boundary.

### Two problems, one fix, for the joint build

Unconfined reads cause **both** failures seen here: codex can wander to unintended files
(the anchoring/confabulation risk) **and** read secrets (the confidentiality risk). Both
are cured by the same thing the original design doc called primary enforcement: an
**external read-confining sandbox** (bubblewrap/`bwrap`, firejail, or a container) that
bind-mounts only the staged target (+ the rubric, read-only). The joint build needs that
before any shared or unattended use. The script already bundles inputs into one dir, so
this is a drop-in wrapper, not a rewrite.

---

Inherent caveat, not a bug to fix: whatever codex genuinely reads goes to OpenAI. That is
the deal for any external-model review — disclosed, unavoidable.
