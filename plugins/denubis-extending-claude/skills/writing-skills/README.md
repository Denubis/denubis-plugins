# writing-skills — Supporting Files Note

This skill ships with three supporting files imported from obra/superpowers (commit `6fd4507659784c351abbd2bc264c7162cfd386dc`, 2026-05-29; imported 2026-06-11). Two are reference documents; one is a dev-only CLI tool.

## `render-graphs.js` — skill-author CLI (dev-only)

**Source:** obra/superpowers/skills/writing-skills/render-graphs.js, commit `6fd4507659784c351abbd2bc264c7162cfd386dc`, imported verbatim (byte-identical) on 2026-06-11.

**Dependencies:**
- Node.js runtime (tested with Node 18+)
- `dot` binary from graphviz — install via `apt install graphviz` / `brew install graphviz` / equivalent

**Usage:**
```
./render-graphs.js <skill-directory>           # Render each dot block to a separate SVG
./render-graphs.js <skill-directory> --combine # Combine all dot blocks into one diagram
```

Extracts all ` ```dot ` code blocks from the target `SKILL.md` and renders them to SVG files alongside. Useful when preparing diagram-heavy skills for human review.

**This is skill-author tooling, not runtime.** Claude Code does not invoke it; the script is for a human author or a subagent preparing visual documentation.

## `anthropic-best-practices.md` — obra reference (verbatim import)

Anthropic-authored skill-authoring best practices, imported from obra with attribution (source commit and import date in its frontmatter). The obra body is byte-identical; the file carries a dated denubis live-docs spot-check appendix at the end. Denubis-specific guidance lives in `SKILL.md` and the sub-skills it references.

## `./examples/CLAUDE_MD_TESTING.md` — historical prompt-variant example

Imported from obra with light denubis-voice adaptation. It illustrates prompt variants,
but its model responses are observations rather than executable acceptance gates. Current
verification guidance lives in `../testing-skills-with-subagents/SKILL.md`.
