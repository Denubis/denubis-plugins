# Codex plugin compatibility matrix

Date: 2026-08-16

## Decision rule

This repository is the semantic source of truth for Claude Code, Codex, and Antigravity.
Shared procedures stay in one skill tree. Provider manifests, hook transports, invocation
policy, and genuinely provider-specific procedures may differ. A plugin is listed in the Codex
marketplace only when Codex can execute its current behavior without pretending that a
Claude-only command, agent definition, hook event, session store, or dispatcher exists.

`available` therefore means “installable and behaviorally supportable now,” not merely
“a manifest can be generated.” Where a provider lacks a transport, the gap is named at
that transport boundary rather than hiding or copying a shared skill.

## Complete shared skill surface

The marketplace exposes all 58 skills from all 11 active skill-bearing Claude plugins.
No skill is withheld or copied. Claude agent names are treated as implementations of
functional roles; Codex and Antigravity use their native delegation surfaces. Skills that
operate on Claude-specific state remain available from other hosts because the subject of
the operation is Claude, not because the host is being misidentified.

| plugin group | status | provider adaptation |
|---|---|---|
| Plan, academic, Git, notes, and estimator | available | Existing shared procedures plus Codex invocation metadata and Antigravity root manifests |
| Getting started and extending Claude | available | Claude-specific subject matter remains callable from any host; provider metadata is transport only |
| Basic and research agents | available | One functional-role procedure maps to each provider's native subagent surface; unavailable delegation falls back honestly to the host session |
| Crash recovery | available | The shared skill resolves the active installed plugin root, while the implementation intentionally inspects Claude session state |
| External agents | available, explicit-only where consequential | Helper paths resolve from the loaded skill; same-model Codex supervision is labelled process separation rather than independent-model review |

## Hook transports

| plugin | Claude | Codex | Antigravity |
|---|---|---|---|
| `denubis-hook-branch-bg` | native `SessionStart` | native `SessionStart` | not claimed |
| `denubis-hook-code-quality-guard` | `PreToolUse` Write/Edit | native `PreToolUse` `apply_patch`, normalized by the shared script | not claimed: no documented equivalent blocking pre-tool contract |
| `denubis-hook-gh-fork-guard` | Claude Bash dispatcher | native `PreToolUse:Bash`, same implementation | not claimed: no documented equivalent blocking pre-tool contract |
| `denubis-hook-pretooluse-dispatcher` | required transport workaround | absent by design; Codex aggregates hooks natively | absent by design |

## Codex mechanisms retained

- repository marketplace discovery rather than a copied global skill directory;
- per-skill display metadata and implicit-invocation policy;
- native hook discovery, trust, and plugin-root environment variables;
- managed worktrees and resumable CLI sessions where the workflow actually needs them;
- preflight-before-mutation and fail-closed installation behavior.

The mirror deliberately does not retain generated duplicate skills, filler descriptions,
forced phase trackers, review-worker quotas, textual change detectors, the Claude hook
dispatcher, or a second semantic repository. The old Codex repository's retirement state
is retained below as historical evidence rather than used as a second source.

## Acceptance boundary

Mechanical acceptance requires schema validation, repository tests, an actual local
marketplace add/install cycle, skill discovery from a fresh Codex session, and hook
enumeration without loading the Claude-only plan hook. Human UAT then touches the installed
CLI behavior and judges whether discovery, invocation, and consequences are unsurprising.
Only accepted UAT authorizes final history normalization and retirement of duplicated
shared skills from the old Codex repository.

## Historical mechanical evidence for the six-plugin candidate

The following evidence describes the superseded initial candidate. It does not validate
the complete 58-skill candidate documented above; fresh runtime UAT remains required.

The installation candidate was exercised with `codex-cli 0.145.0`:

- Codex added this worktree as marketplace `denubis-plugins` and resolved exactly the six
  listed local plugin sources. It replaced a stale marketplace pointer whose only entry
  was the discarded, uninstalled `denubis-local-mail` prototype.
- `codex plugin add` installed and enabled all six plugins in the normal Codex plugin
  cache. The installed plan plugin retained Claude's explicit-only frontmatter where
  relevant and accepted the native `hooks` manifest field.
- A fresh ephemeral read-only Codex process, without being told the skill name, selected
  `denubis-plan-and-execute:executing-an-implementation-plan`, opened its `SKILL.md` from
  the installed plugin cache, and returned the required checkpoint → complete mechanical
  and sanity checks → explicit human UAT → normalization order.
- `claude plugin validate --strict` passed all six source plugins after provider hook
  registrations were split. This protects the existing Claude installation path.
- The repository suite passed `1530` tests in `5.43s`, including marketplace resolution,
  metadata constraints, explicit-only consequential skills, dual-provider hook isolation,
  installed-root execution for both provider environments, and the existing hook and
  skill behavior suites. `git diff --check` was clean.

The bundled plugin-creator validator passed the four plugins without hooks. It rejects the
`hooks` field and Claude's `disable-model-invocation: true`, despite the installed Codex
runtime accepting and installing both. For this candidate the runtime ingestion and fresh
process are the higher-authority evidence; the validator discrepancy remains a tooling
compatibility fact to recheck after a Codex upgrade.

After updated `main` was merged into the private candidate, the integrated source became
plan-and-execute 4.1.1. `uv run --all-packages pytest -q` passed 1,541 tests; the Codex and
Claude Ponytail suites passed 52 and 42 cases; ShellCheck passed; Claude strict validation
passed all six marketplace plugins; and the bundled Codex validator passed the four
plugins without hooks. The worktree is not registered as a marketplace. The final local
install and fresh-session UAT are intentionally deferred until the accepted tree is
available at the canonical checkout.

That mechanical evidence established the initial candidate. Hook trust succeeded, but
implication-level workflow UAT later failed as recorded below. The old-mirror cleanup was
performed after an invalid acceptance and remains isolated rather than integrated.

## Human UAT attempts and retirement state

The first disposable CLI run was later invalidated: Codex had silently loaded a stale
pre-rewrite plugin cache. Its apparent acceptance is not evidence for this candidate.

A second disposable run loaded the exact installed
`denubis-plan-and-execute/4.0.1/.../executing-an-implementation-plan/SKILL.md`. It proved
the intended lifecycle mechanically: the actor preserved the default greeting, added and
documented uppercase behavior, created one private feature checkpoint, completed checks,
and stopped before merge or history rewrite. Brian's interaction with the finished CLI
confirmed the feature behavior but rejected the workflow as disproportionate. The actor
had automatically invoked project-memory retrieval, searched unrelated prior chats,
loaded six overlapping workflow skills, created a duplicate plan tracker, repeatedly
narrated routine transitions, and manufactured a disposable defect for a secondary Git
hygiene observation.

The integrated correction is versioned as `denubis-plan-and-execute` 4.1.1 and
`denubis-project-notes` 0.1.1. Fresh installed-runtime UAT remains open. No current human
acceptance authorises final normalization, installation, or publication.

The 37 global `~/.agents/skills` links into `brian-ed3d-plugins-codex` and its 21,538-line
copied skill tree were removed after the invalid first acceptance. Cleanup commit
`0884ad3` remains isolated on its own branch. The old repository now owns Ponytail and
Gemini-specific adapter infrastructure only; existing uncommitted Ponytail work,
`.ed3d/`, and resume prompts were preserved. Its 35 Ponytail tests, Markdown lint, Gemini
extension validation, and diff check passed after retirement.

Gemini's current documented boundary supports `gemini skills link <path>` for an
individual skill, but the extension documentation does not promise that an extension can
package external symlink targets. The adapter therefore documents explicit, reviewed
canonical skill links instead of creating another bulk mirror.

The four existing canonical commits remain distinct coherent outcomes—lifecycle, coding
and architecture guidance, remaining shared guidance, and Codex delivery. The current
proportionality correction is a failed-UAT fix round and must fold into its owning outcomes
only after fresh human acceptance.
