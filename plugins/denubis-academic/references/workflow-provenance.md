# Workflow provenance

The literature-scout and annotated-bibliography skills credit Shawn Ross's
proposer/verifier workflows and AB+ pipeline as their methodological starting
points. This transfer uses newly written instructions and helpers integrated
with denubis-academic; it does not vendor his API clients, extraction package,
Workflow runtime, personal registers or project configuration.

Reviewed sources, 2026-09-22:

- [personal-assistant literature scout](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/commands/lit-scout.md)
  and its proposer/verifier agents: separate discovery and metadata verification.
- [map-reader-llm AB+ briefs](https://github.com/saross/map-reader-llm/blob/e10d50dd0fb50a99919b9b639b3b1de577088081/prompts/ab-plus/README.md):
  source-specific drafting, mechanical evidence checks, independent interpretation
  review, and evidence-based revision.
- [personal-assistant methodology review](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/skills/review-implementation/SKILL.md):
  study-design checks added to paper-review's existing facets.

Material changes: existing Zotero/cache ownership retained; physical pages use
one-based indices; literal matches and OCR visual checks remain distinct;
reviewers' corrections require source adjudication; no fixed worker count,
word/point quota, aggregate validity verdict, automatic import or correction
loop. The search helper preserves provider errors and raw JSON instead of
presenting a failed check as absence. Public API contracts are linked in the
search reference.
