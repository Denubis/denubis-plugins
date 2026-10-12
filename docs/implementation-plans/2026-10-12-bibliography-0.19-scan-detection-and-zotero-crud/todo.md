# Pending work

Plan: `plan.md` in this directory. Each outcome is done when its verification block
passes and its evidence is in `worklog.md`.

## Outcome E: auto-export registration
- [ ] Red: `register_export.py` cases (`bbt_collection_path` numeric absolute form reaches the RPC stub, preview no RPC, `--expect-version` rejected, missing flag usage error, accepted/not accepted by returned key, E2a, E2b, no-mtime-change, content satisfied/not)
- [ ] Green: `register_export.py` (injected clock)
- [ ] Docs: `zotero-writes.md`, `notes-and-bibliographies.md`, `SKILL.md` row, `troubleshooting.md` rows; regex update
- [ ] Verification block E; checkpoint commit

## Outcome F: release 0.19.0
- [ ] Final `SKILL.md` pass (preconditions, front door, write-boundary table, completion evidence; ≤ 500 lines)
- [ ] Bounded inspection: every documented flag and preview line exists in the helper (`--help` plus format strings), recorded per helper
- [ ] `docs/architecture/plugins/denubis-academic/0-context.md` update
- [ ] Version 0.19.0 in both `plugin.json` manifests (Claude and Codex), `marketplace.json`, `CHANGELOG.md` entry
- [ ] Verification block F (full suite, ruff check and format, `git diff --check`); checkpoint commit

## Human UAT (after F)
- [ ] Steps 1–8 in `plan.md` "Human UAT"; record each result in `worklog.md`
- [ ] After acceptance: normalise checkpoints per outcome, rerun F gates
