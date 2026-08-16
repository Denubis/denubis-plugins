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
