# Codex plugin compatibility matrix

Date: 2026-08-16

## Decision rule

This repository is the semantic source of truth for both Claude Code and Codex. Shared
procedures stay in one skill tree. Provider manifests, hook transports, invocation policy,
and genuinely provider-specific procedures may differ. A plugin is listed in the Codex
marketplace only when Codex can execute its current behavior without pretending that a
Claude-only command, agent definition, hook event, session store, or dispatcher exists.

`available` therefore means “installable and behaviorally supportable now,” not merely
“a manifest can be generated.” `withheld` is an explicit compatibility result, not an
unfinished bulk conversion.

## Initial marketplace

| plugin | status | semantic owner | Codex adaptation |
|---|---|---|---|
| `denubis-plan-and-execute` | available | existing shared skills | Codex manifest and per-skill invocation metadata; an explicit empty Codex hook file prevents the Claude live-session marker from being loaded |
| `denubis-academic` | available | existing shared skills | Codex manifest and per-skill invocation metadata; bibliography scripts resolve `PLUGIN_ROOT` or the Claude compatibility root |
| `denubis-git-commit` | available | existing shared skill | Codex manifest; implicit invocation disabled because committing is a consequential boundary |
| `denubis-project-notes` | available | existing shared skill | Codex manifest and invocation metadata; its external chat-search dependency remains explicit |
| `denubis-token-estimator` | available | existing shared skill and scripts | Codex manifest and invocation metadata; direct installed-script commands replace the Claude slash-command assumption |
| `denubis-hook-branch-bg` | available | existing provider-neutral Python hook | Codex manifest plus a native `SessionStart` hook using `PLUGIN_ROOT`; installation still requires normal Codex hook trust |

## Withheld from the initial marketplace

| plugin | status | reason | next honest boundary |
|---|---|---|---|
| `denubis-00-getting-started` | withheld | onboarding is composed around Claude commands, settings, and plugin setup | replace it with repository-level provider-specific installation documentation if users need a common entry point |
| `denubis-basic-agents` | withheld | its primary payload is Claude agent definitions and Claude tool syntax; a Codex plugin manifest does not translate those agents | decide whether any role is absent from Codex's built-in subagents, then write only that provider adapter |
| `denubis-crash-recovery` | withheld | it classifies Claude JSONL sessions and depends on the Claude wrapper/live-marker protocol | design Codex recovery against Codex's actual session and resume semantics rather than relabeling the Claude classifier |
| `denubis-extending-claude` | withheld | its procedures and examples create Claude plugins, agents, commands, and marketplace metadata | keep Claude-specific extension guidance here; use Codex's maintained plugin/skill creators for Codex until a small shared conceptual core is demonstrated |
| `denubis-external-agents` | withheld | the Codex paths drive or supervise another Codex process and include Ponytail-specific transport; installing them inside Codex creates recursive authority and provenance problems | keep those provider-specific capabilities outside the normal Codex marketplace and review each external-engine adapter separately |
| `denubis-hook-gh-fork-guard` | withheld | the current guard parses raw shell text, only recognizes commands beginning exactly with `gh`, and relies on the Claude dispatcher convention; it can imply safety while missing equivalent invocations | redesign around native executable/policy boundaries with bypass tests before advertising protection |
| `denubis-hook-pretooluse-dispatcher` | withheld | it compensates for Claude hook aggregation; Codex already aggregates native hooks | no Codex port; retain only while Claude needs the transport workaround |
| `denubis-research-agents` | withheld | its payload is Claude agent definitions and provider tool syntax, while Codex already supplies research and codebase workers | add a Codex adapter only if a measured missing role remains |

## Codex mechanisms retained

- repository marketplace discovery rather than a copied global skill directory;
- per-skill display metadata and implicit-invocation policy;
- native hook discovery, trust, and plugin-root environment variables;
- managed worktrees and resumable CLI sessions where the workflow actually needs them;
- preflight-before-mutation and fail-closed installation behavior.

The mirror deliberately does not retain generated duplicate skills, filler descriptions,
forced phase trackers, review-worker quotas, textual change detectors, the Claude hook
dispatcher, or a second semantic repository. Historical `brian-ed3d-plugins-codex`
content remains untouched until the initial marketplace passes human UAT.

## Acceptance boundary

Mechanical acceptance requires schema validation, repository tests, an actual local
marketplace add/install cycle, skill discovery from a fresh Codex session, and hook
enumeration without loading the Claude-only plan hook. Human UAT then touches the installed
CLI behavior and judges whether discovery, invocation, and consequences are unsurprising.
Only accepted UAT authorizes final history normalization and retirement of duplicated
shared skills from the old Codex repository.

## Mechanical evidence

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
acceptance authorises final normalization or main integration.

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
