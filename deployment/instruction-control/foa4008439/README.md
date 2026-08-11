# Instruction-control deployment on `foa4008439`

This directory contains the exact global-instruction and settings candidates consumed by
the deployment. `candidate-manifest.json` binds their bytes, the changed plugin source
trees, the human-source records, and the observed live baselines.

The manifest state is `source-candidate`. It does not authorise a commit, publication, or
live write. Plugin installation must wait until the reviewed source commit is available
to the installed `denubis-plugins` marketplace.

## Preconditions

From the repository root:

```fish
uv run python deployment/instruction-control/verify_candidate.py source deployment/instruction-control/foa4008439/candidate-manifest.json --repo-root .
uv run python deployment/instruction-control/verify_candidate.py baseline deployment/instruction-control/foa4008439/candidate-manifest.json --repo-root .
scripts/pre-commit
```

Both verifier records must report `"ok": true`. The repository test runner must pass.
Any baseline change invalidates the candidate; inspect and rebuild it rather than forcing
the deployment.

The source change must then be reviewed, committed, pushed, and present in the local
marketplace checkout. Those transitions require their own explicit human authority.

## Live transition

Before changing state, create one backup directory containing:

- `/home/brian/.claude/CLAUDE.md`;
- `/home/brian/.claude/settings.json`;
- `/home/brian/.claude/plugins/installed_plugins.json`; and
- the currently selected cache trees for every plugin named under `plugin_releases`.

Then, without starting an intervening Claude session:

1. Run `claude plugin marketplace update denubis-plugins` and verify that its checkout
   contains the reviewed commit.
2. Update the five existing changed plugins named in the manifest.
3. Install `denubis-project-notes@denubis-plugins` at user scope.
4. Atomically replace the live global `CLAUDE.md` and `settings.json` with the two bound
   candidates, preserving the live files' modes.
5. Uninstall the three retired plugins at user scope with their persistent data kept.
6. Reapply the bound settings candidate after the plugin CLI finishes, because install
   and uninstall commands may rewrite that file.
7. Run the deployed verifier:

```fish
uv run python deployment/instruction-control/verify_candidate.py deployed deployment/instruction-control/foa4008439/candidate-manifest.json --repo-root .
```

The deployed verifier recomputes the global/project/settings digests, selected registry
versions, and installed cache-tree digests. A green source check is not a substitute.

## Rollback

On any failed transition or post-deployment check, restore the three backed-up live files
atomically and restore any removed cache trees before starting another Claude session.
Rerun the baseline verifier against a rollback manifest produced from those restored
files. Do not claim rollback from a settings-only restoration when the plugin registry or
selected cache path still differs.
