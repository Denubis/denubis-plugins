# Personae

User types, their goals, access patterns, and constraints.

## Heavy Claude Code user (single human)

**Role:** A developer/researcher who uses Claude Code as a primary work tool across many concurrent projects. Author and sole consumer of this marketplace.

**Goals:**
- Use Claude Code productively across long-running sessions in multiple projects.
- Maintain disciplined workflows (brainstorm → design → plan → execute) without losing process to fatigue or context drift.
- Catch behavioural drift before it ships bad work, using permission hooks where a
  boundary is mechanically checkable and external review or test evidence elsewhere.
- Re-use disciplined knowledge across sessions and machines by keeping markdown skills, agents, and CLAUDE.md files as the durable artefact set.

**Access patterns:**
- Invokes Claude Code via the `claudew` wrapper (`plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh`, `31e42d0`) from a fish shell, typically inside tmux/byobu so agent teams can use split panes.
- Runs many concurrent sessions, often across worktrees of the same repo (the `branch-bg` hook colours each terminal by repo + branch so they're visually distinguishable).
- Invokes commands and named skills for repeatable workflows. The current command
  surface includes `/getting-started`, `/setup`, `/flesh-it-out`, `/how-to-customize`,
  and `/estimate`; design, implementation, commit, and review entry points are skills.
- Reads and edits skill markdown directly when refining workflows.
- Works against forks of GitHub repos — the `gh-fork-guard` hook denies `gh` calls targeting any repo other than the configured fork.
- Uses `uv` for Python tooling, `git` everywhere, and `gh` for GitHub work.

**Constraints:**
- Local-only operation — no remote sync of plugin state beyond git.
- Linux desktop assumed by some components: `/proc` access (used by `branch-bg` for TTY discovery), fish shell, ghostty terminal (referenced in `branch-bg`'s keywords).
- Limited attention budget. The live pre-deployment settings still enable retired
  reminder plugins; the source candidate removes them instead of asking the operator to
  manage their repetition.

**Key scenarios:**
1. **Starting a new feature.** Invokes `starting-a-design-plan`. Its procedures gather
   context, clarify intent, write the design, challenge it, and update current
   architecture where implementation already warrants it. A design plan lands in
   `docs/design-plans/`.
2. **Running an implementation plan.** Invokes `starting-an-implementation-plan`, then
   `executing-an-implementation-plan`. The skills coordinate planning, implementation,
   review, and evidence collection; repository and test results establish completion.
3. **About to commit something risky.** The commit procedure checks whether changed
   contracts, APIs, domain structure, or agent instructions require corresponding
   `CLAUDE.md` or `AGENTS.md` updates. `gh-fork-guard` denies `gh pr create` against
   upstream. `code-quality-guard` denies file edits that match banned patterns (for
   example `create_all`, migration edits, or debug statements).
4. **Reading academic literature.** Adds a paper to Zotero. Invokes `denubis-academic:using-bibliography` to render the PDF into per-page markdown and emit page-keyed blockquotes.
5. **Generic agent dispatch.** Uses `denubis-basic-agents` (haiku/sonnet/opus general-purpose, python-developer, academic-researcher) when a fresh subagent without specific tooling is the right move; `using-generic-agents` is the selection guide.

## Persona Relationships

There is one persona. Other apparent "actors" — Claude Code itself, `claude-wrapper.sh`, MCP servers, git, gh, the terminal — are external entities in the per-plugin context diagrams, not personae. They are sources/sinks of data, not users with goals.
