# External CLI Agents Design

**GitHub Issue:** None

## Summary

This design builds a new `denubis-external-agents` plugin that exposes two analyst agents — `codex-analyst` and `gemini-analyst` — which allow Claude Code to delegate analysis tasks to OpenAI Codex and Google Gemini respectively. The agents are discoverable as Task tool subagents, meaning any skill or caller can dispatch work to a different AI model in the same way it would dispatch to another Claude agent. This creates a lightweight mechanism for getting a second (or third) opinion from a model with different training, context limits, or capabilities — specifically useful for proleptic critique, hypothesis generation, and comprehension of large codebases that might exceed Claude's effective context window.

The implementation uses Claude Haiku as a thin wrapper: Haiku parses the caller's request, assembles the prompt, enforces the required safety flags, and relays the external CLI's output back verbatim. Safety is enforced at three independent levels — OS-level sandboxing (Landlock/seccomp for Codex, Podman for Gemini), tool restriction on the Haiku wrapper itself (Read and Bash only), and a prompt-level constraint that refuses to invoke either CLI without its exact safety flags. Project context is injected through a session-start hook that pre-caches CLAUDE.md and git state into per-session temp files, which the CLIs read via their native context mechanisms (AGENTS.md for Codex, GEMINI.md via environment variable for Gemini).

## Definition of Done

Create a `denubis-external-agents` plugin containing two haiku-based wrapper agents (`codex-analyst` and `gemini-analyst`) that invoke their respective CLIs in read-only sandboxed mode. Each agent's prompt engineering handles formatting the caller's request into an effective CLI prompt, enforcing safety flags, and relaying output back. Gemini agent supports web search as a capability. Both agents are discoverable via the Task tool as `denubis-external-agents:codex-analyst` and `denubis-external-agents:gemini-analyst`.

**Success criteria:**
- An agent can dispatch to either CLI tool and get a useful analytical response back
- Neither CLI tool can write files, execute arbitrary commands, or modify the codebase
- The agents work for the three stated use cases: diverse proleptic voices, hypothesis generation, and large-codebase comprehension

**Out of scope:**
- Modifying existing skills (proleptic-challenger, systematic-debugging) to auto-dispatch
- Cost tracking or rate limiting
- Automatic model selection (caller chooses which agent to use)

## Acceptance Criteria

### external-cli-agents.AC1: Codex analyst returns useful analysis
- **external-cli-agents.AC1.1 Success:** Dispatching `denubis-external-agents:codex-analyst` with an analysis prompt returns Codex's response text
- **external-cli-agents.AC1.2 Success:** Codex reads cached AGENTS.md context (CLAUDE.md + git state) during analysis
- **external-cli-agents.AC1.3 Success:** Providing `SKILL_PATH:` directive causes skill text to be prepended to the prompt
- **external-cli-agents.AC1.4 Failure:** Agent refuses to invoke Codex without `--sandbox read-only` flag

### external-cli-agents.AC2: Gemini analyst returns useful analysis
- **external-cli-agents.AC2.1 Success:** Dispatching `denubis-external-agents:gemini-analyst` with an analysis prompt returns Gemini's response text
- **external-cli-agents.AC2.2 Success:** Gemini reads cached GEMINI.md context via `GEMINI_SYSTEM_MD` env var
- **external-cli-agents.AC2.3 Success:** Providing `SKILL_PATH:` directive causes skill text to be prepended to the prompt
- **external-cli-agents.AC2.4 Success:** Gemini performs web search when query benefits from current information
- **external-cli-agents.AC2.5 Failure:** Agent refuses to invoke Gemini without `--approval-mode plan --sandbox` flags

### external-cli-agents.AC3: Session hooks manage context lifecycle
- **external-cli-agents.AC3.1 Success:** SessionStart creates temp dir with AGENTS.md containing CLAUDE.md content
- **external-cli-agents.AC3.2 Success:** SessionStart creates temp dir with GEMINI.md containing CLAUDE.md content
- **external-cli-agents.AC3.3 Success:** Existing project AGENTS.md/GEMINI.md contents are appended to cached copies
- **external-cli-agents.AC3.4 Success:** Git context (diff stats, changed files, recent commits) is appended to both cached files
- **external-cli-agents.AC3.5 Success:** `EXTERNAL_AGENTS_TEMP` env var is available in session Bash calls
- **external-cli-agents.AC3.6 Success:** SessionEnd removes the temp directory

### external-cli-agents.AC4: Safety constraints hold
- **external-cli-agents.AC4.1 Success:** Codex operates in OS-level read-only sandbox (Landlock/seccomp)
- **external-cli-agents.AC4.2 Success:** Gemini operates in Podman container with plan (read-only) mode
- **external-cli-agents.AC4.3 Failure:** Neither CLI can create, modify, or delete files in the project
- **external-cli-agents.AC4.4 Edge:** Haiku wrapper has only Read and Bash tools — no Edit, Write, or other tools

## Glossary

- **Haiku**: Claude Haiku, the fastest and cheapest Claude model. Used here as a thin wrapper agent rather than for substantive reasoning.
- **Codex**: OpenAI's Codex CLI tool (`codex` command), a locally-installed agentic coding assistant backed by OpenAI models.
- **Gemini CLI**: Google's `gemini` command-line tool, a locally-installed agentic assistant backed by Google Gemini models.
- **Task tool**: A Claude Code built-in tool that dispatches work to a named subagent, identified by `plugin-name:agent-name`.
- **Subagent**: An agent definition (YAML frontmatter + markdown system prompt) invokable via the Task tool. Lives under a plugin's `agents/` directory.
- **SessionStart / SessionEnd hooks**: Claude Code hook events that fire at the beginning and end of a session. Used here to create and destroy the per-session temp directory.
- **CLAUDE_ENV_FILE**: A Claude Code mechanism for persisting environment variables across Bash tool calls within a session.
- **AGENTS.md**: The context file that the Codex CLI reads from its working root directory. Analogous to CLAUDE.md for Claude Code.
- **GEMINI_SYSTEM_MD**: An environment variable that overrides the Gemini CLI's default system prompt with a specified markdown file.
- **`--approval-mode plan`**: A Gemini CLI flag that restricts the model to read-only analysis.
- **`-s read-only` (Codex)**: A Codex CLI flag that activates its OS-level sandbox (Landlock + seccomp on Linux), preventing file writes and arbitrary command execution.
- **Landlock / seccomp**: Linux kernel security mechanisms. Landlock restricts filesystem access; seccomp restricts system calls. Together they form Codex's OS-level sandbox.
- **Podman**: A container runtime (similar to Docker) used by the Gemini CLI's `--sandbox` flag to isolate the model's process.
- **Proleptic**: Anticipatory critique — raising objections before they materialise. One of the three target use cases.
- **SKILL_PATH directive**: A caller convention: prepending `SKILL_PATH: /path/to/skill.md` to a prompt causes the wrapper agent to read that skill file and include its contents in the prompt sent to the external CLI.

## Architecture

Two thin haiku-based wrapper agents invoke external AI CLIs (OpenAI Codex, Google Gemini) in read-only sandboxed mode. A session-start hook pre-caches project context; a session-end hook cleans up.

**Context delivery:** The hook copies CLAUDE.md into the session temp directory as `AGENTS.md` (for Codex) and `GEMINI.md` (for Gemini). If the project already has AGENTS.md or GEMINI.md, their contents are appended to the copies. Git context (diff stats, changed files, recent commits) is also appended. The CLIs read these files via their native context mechanisms.

**Agent invocation flow:**
```
Caller dispatches via Task tool
    ↓
Haiku wrapper agent (Read, Bash tools only)
    ├─ Reads cached context from $EXTERNAL_AGENTS_TEMP/
    ├─ Reads skill file if SKILL_PATH: directive present
    ├─ Builds prompt: skill text + caller's analysis request
    └─ Runs CLI via Bash (single call), returns stdout verbatim
```

**CLI invocations:**
- **Codex:** `codex exec -s read-only -C "$EXTERNAL_AGENTS_TEMP" --ephemeral "$PROMPT" 2>/dev/null`
  - `-C` points working root at the temp dir (so Codex reads our AGENTS.md)
  - `-s read-only` enforces OS-level sandbox (Landlock + seccomp on Linux)
  - `--ephemeral` prevents session persistence
- **Gemini:** `GEMINI_SYSTEM_MD="$EXTERNAL_AGENTS_TEMP/GEMINI.md" gemini -p "$PROMPT" --approval-mode plan --sandbox 2>/dev/null`
  - `GEMINI_SYSTEM_MD` overrides system prompt with our cached context
  - `--approval-mode plan` is Gemini's read-only mode
  - `--sandbox` enables Podman container isolation

**Safety model — defence in depth (Layer 1 is primary):**
1. **OS-enforced sandbox (primary enforcement):** Codex uses Landlock/seccomp; Gemini uses Podman container + plan mode. Kernel-level, not honour-system. This is the only layer that prevents the external CLIs themselves from writing files.
2. **Agent tool restrictions (haiku containment):** Haiku wrapper has `Read, Bash` only — no Edit, Write, or other tools. Prevents haiku from acting outside its role, but does not constrain what the CLI processes do.
3. **Prompt-level constraints (haiku containment):** Agent system prompt forbids running CLI without exact safety flags. Same scope as Layer 2 — protects against haiku misconfiguration, not CLI escape.

**Caller protocol:**
```
SKILL_PATH: /path/to/skill/SKILL.md
---
[Analysis prompt here]
```
`SKILL_PATH:` is optional. If absent, the agent uses only cached base context.

**SKILL_PATH validation:** The agent must validate that SKILL_PATH points to a `.md` file under a known plugin directory (e.g., `plugins/*/skills/`). Reject paths to arbitrary files to prevent accidental exfiltration of credentials or private keys to external model providers.

## Existing Patterns

Investigation found no existing agents that wrap external CLI tools. All current agents invoke Claude models directly. This design introduces a new pattern: haiku as a thin CLI wrapper.

Patterns followed from existing codebase:
- **Agent file structure:** YAML frontmatter + markdown body, matching `plugins/denubis-basic-agents/agents/*.md`
- **Plugin scaffold:** `.claude-plugin/plugin.json`, `agents/` directory, LICENSE — matching existing plugin layout
- **Tool restriction:** `tools:` field in frontmatter to limit agent capabilities — pattern established by `denubis-plan-and-execute` agents (e.g., code-reviewer uses `Read, Grep, Glob, Bash`)
- **Session hooks:** SessionStart for context injection, matching `denubis-plan-and-execute` and `denubis-basic-agents` patterns
- **Temp file keying:** Session ID-based temp directory in `/tmp/`, matching pattern from `denubis-hook-shortcut-detection`

New patterns introduced:
- **SessionEnd hook** for cleanup — first use of this event type in the repo
- **CLAUDE_ENV_FILE** for persisting environment variables across Bash calls within a session
- **External CLI delegation** — haiku wrapper that shells out to non-Claude models

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Plugin Scaffold
**Goal:** Create the `denubis-external-agents` plugin structure with registration

**Components:**
- `plugins/denubis-external-agents/.claude-plugin/plugin.json` — plugin metadata
- `plugins/denubis-external-agents/LICENSE` — CC-BY-SA-4.0
- Marketplace entry in `.claude-plugin/marketplace.json`
- Changelog entry in `CHANGELOG.md`

**Dependencies:** None

**Done when:** Plugin is registered in marketplace.json, version numbers are consistent
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Session Hooks
**Goal:** Context caching at session start, cleanup at session end

**Components:**
- `plugins/denubis-external-agents/hooks/hooks.json` — hook event registration (SessionStart + SessionEnd)
- `plugins/denubis-external-agents/hooks/cache-context.sh` — reads CLAUDE.md, copies as AGENTS.md/GEMINI.md, appends project-specific files if present, appends git context, creates session temp dir, exports `EXTERNAL_AGENTS_TEMP` via `CLAUDE_ENV_FILE`
- `plugins/denubis-external-agents/hooks/cleanup-context.sh` — removes session temp dir on SessionEnd

**Dependencies:** Phase 1 (plugin scaffold)

**Done when:** Session start creates temp dir with populated AGENTS.md and GEMINI.md; session end removes it; `EXTERNAL_AGENTS_TEMP` is available in Bash environment
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: Codex Analyst Agent
**Goal:** Working codex-analyst agent that invokes Codex CLI in read-only mode

**Components:**
- `plugins/denubis-external-agents/agents/codex-analyst.md` — agent definition with YAML frontmatter (model: haiku, tools: Read, Bash) and system prompt covering: SKILL_PATH parsing, prompt assembly, CLI invocation with safety flags, output relay

**Dependencies:** Phase 2 (session hooks for cached context)

**Done when:** Dispatching `denubis-external-agents:codex-analyst` via Task tool invokes Codex CLI in read-only sandbox, reads cached AGENTS.md context, and returns analysis output. Agent refuses to run without safety flags.
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: Gemini Analyst Agent
**Goal:** Working gemini-analyst agent that invokes Gemini CLI in read-only sandboxed mode

**Components:**
- `plugins/denubis-external-agents/agents/gemini-analyst.md` — agent definition with YAML frontmatter (model: haiku, tools: Read, Bash) and system prompt covering: SKILL_PATH parsing, prompt assembly, CLI invocation with safety flags (GEMINI_SYSTEM_MD + plan mode + sandbox), output relay

**Dependencies:** Phase 2 (session hooks for cached context)

**Done when:** Dispatching `denubis-external-agents:gemini-analyst` via Task tool invokes Gemini CLI in plan mode with Podman sandbox, reads cached GEMINI.md context, and returns analysis output. Web search works when relevant to the query.
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: Integration Testing
**Goal:** Verify both agents work end-to-end for all three use cases

**Components:**
- Manual testing of proleptic reasoning use case (dispatch both agents with same proposal)
- Manual testing of hypothesis generation use case (dispatch with bug description)
- Manual testing of codebase comprehension (Gemini agent with architectural query)
- Verify safety: confirm neither agent can write files or execute arbitrary commands

**Dependencies:** Phases 3 and 4

**Done when:** All three use cases produce useful analytical output; safety constraints hold under both adversarial prompting AND direct sandbox verification (confirm filesystem write attempts are blocked at the OS level, not just prompt level)
<!-- END_PHASE_5 -->

## Additional Considerations

**Timeout handling:** Both CLIs can take significant time, especially Gemini with large context or web search. The Bash tool's default 2-minute timeout may be insufficient for complex analysis. Implementation should use an appropriate timeout (up to 10 minutes) for the CLI Bash calls.

**Cost awareness:** Each invocation incurs API costs on the external provider (OpenAI for Codex, Google for Gemini) plus a small haiku wrapper cost. Callers should be aware these are real API calls, not free. Gemini has a generous free tier (60 req/min, 1000/day).

**Codex `-C` behaviour:** When Codex's working root is the temp dir (via `-C`), it reads AGENTS.md from there but can still read project files anywhere on the filesystem in read-only mode. The prompt must tell Codex where the actual project lives.

**Gemini web search:** Automatic — Gemini decides whether to search based on query relevance. No flag needed to enable. This is a differentiating capability for queries that benefit from current information (e.g., "are there known vulnerabilities in this dependency?").

**Stale context within a session:** The session-start hook captures git state once. If commits happen mid-session, the cached context becomes stale. This is an accepted limitation for v1 — the context represents "project state at session start," not live state. A future enhancement could regenerate context on demand.
