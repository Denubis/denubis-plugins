# Pending work

Plan: `plan.md` in this directory. Each outcome is done when its verification block
passes and its evidence is in `worklog.md`.

## Outcome F: release 0.19.0
- [ ] Final `SKILL.md` pass (preconditions, front door, write-boundary table, completion evidence; ≤ 500 lines)
- [ ] Bounded inspection: every documented flag and preview line exists in the helper (`--help` plus format strings), recorded per helper
- [ ] `docs/architecture/plugins/denubis-academic/0-context.md` update
- [ ] Version 0.19.0 in both `plugin.json` manifests (Claude and Codex), `marketplace.json`, `CHANGELOG.md` entry
- [ ] Verification block F (full suite, ruff check and format, `git diff --check`); checkpoint commit

## Human UAT (after F)
- [ ] Steps 1–8 in `plan.md` "Human UAT"; record each result in `worklog.md`
- [ ] After acceptance: normalise checkpoints per outcome, rerun F gates
