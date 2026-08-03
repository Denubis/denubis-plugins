---
name: npm-install-script-policy
description: Use when an npm install is blocked by install scripts or git dependencies - ESTRICTALLOWSCRIPTS, EALLOWSCRIPTS, Refusing to fetch, allowScripts, postinstall - or when setting npm supply-chain defaults
user-invocable: true
---

# npm install-script policy

## Overview

Install-time lifecycle scripts (`preinstall`, `install`, `postinstall`) are the
largest code-execution surface in the npm ecosystem: every `npm install` runs
scripts from every transitive dependency, as your user. This skill is the
machine's configured answer to that, the procedure for working inside it, and an
honest account of what it does not cover.

**Everything below was verified on 2026-08-03** against npm 11.17.0 and 12.0.1
with real (not `--dry-run`) installs and positive controls. Where a claim is
contested, it says so.

## The configured policy

`~/.npmrc`:

```
min-release-age=14
strict-allow-scripts=true
```

- **`min-release-age=14`** refuses versions younger than 14 days, so a
  compromised release usually gets caught and unpublished before you can install
  it. It is a *resolution-time* filter.
- **`strict-allow-scripts=true`** makes an unapproved install script a hard
  error. On npm 12 this is redundant (blocking is the default) and kept so an
  npm 11 machine or a downgrade stays protected.

**Not set, deliberately: `allow-scripts=<list>`.** A name-only entry
pre-approves every *future* release of that package, which is exactly the window
the policy exists to close. Per-project pinned approvals replace it. For a
global install or `npx`, where there is no `package.json`, pass the flag
explicitly: `npm install -g --allow-scripts=better-sqlite3`.

## When an install is blocked

### `ESTRICTALLOWSCRIPTS` — a dependency wants to run a script

Do not reach for `--dangerously-allow-all-scripts`. The procedure is: install
without executing, read what wants to run, then decide.

```fish
npm install --ignore-scripts        # installs; nothing executes
npm install-scripts ls              # what wants to run, and what it runs
```

Now **read the script before approving it**. It is on disk and has not run:

```fish
cat node_modules/<pkg>/<the-script-named-by-ls>
```

Then approve or deny, and install for real:

```fish
npm install-scripts approve esbuild @swc/core   # writes pinned pkg@version
npm install-scripts deny es5-ext                # writes name-only false
npm install
```

Approvals land in `package.json` and are committed, so they are reviewable:

```json
"allowScripts": {
  "es5-ext": false,
  "esbuild@0.28.0": true
}
```

**Approve pinned, deny name-only.** That is what the commands do by default and
the asymmetry is deliberate: a pinned approval expires when the version changes,
so an upgrade re-triggers review, while a pinned *denial* would silently
re-allow every other version.

**The command was renamed.** npm 12 is `npm install-scripts approve|deny|ls`.
npm 11 is `npm approve-scripts` / `npm deny-scripts`. A "command not found" here
usually means version drift, not a typo.

### `Refusing to fetch` — a git dependency

npm 12 refuses non-registry sources by default (`allow-git=none`). Values are
`all`, `none`, `root` only; it is **not** a package list.

`root` permits only git refs the root `package.json` declares itself, so it does
**not** help when the git dep is transitive. Check first:

```fish
rg 'git\+|github:' package-lock.json
```

If it is transitive and the project genuinely needs it, scope the exception to
that repo with a project `.npmrc` (never `~/.npmrc`), and say why in a comment:

```
allow-git=all
```

### `EALLOWSCRIPTS` — `allow-scripts` in the wrong place

npm rejects `--allow-scripts` during a project-scoped `install`/`ci`/`update`/
`rebuild`. Passing it on the command line, or via `npm_config_allow_scripts`,
triggers this. Use `package.json`'s `allowScripts` for projects.

**Contested:** whether a plain `~/.npmrc` key also triggers it. Observed on
2026-08-03: a bare `npm install` on npm 11.17.0 failed `EALLOWSCRIPTS` with the
key in `~/.npmrc` and no `npm_config_*` in the environment (re-checked with
`env | rg npm_config`, empty). An independent review could not reproduce that,
having simulated the user config via `NPM_CONFIG_USERCONFIG`, which is itself an
env var and may not behave identically. Both readings are recorded; the key is
not set either way, so nothing depends on resolving it.

## What this does NOT protect against

State these plainly rather than letting the config imply more than it delivers.

1. **A repo you do not trust.** A project `.npmrc` containing
   `dangerously-allow-all-scripts=true` defeats the user-level policy entirely.
   **Verified 2026-08-03** with a control: the same install blocks without that
   file and runs with it. Project config outranks user config for these keys, and
   the root project's own scripts run regardless. Before the first install in an
   unfamiliar repo, look: `cat .npmrc` and check `scripts` in `package.json`.
2. **A lockfile.** `min-release-age` filters *resolution*. A too-young version
   already pinned in `package-lock.json` installs cleanly, including a lockfile
   that arrived with a cloned repo or a pull request.
3. **`require()`.** Blocking install scripts does nothing about malicious code
   that runs when a build tool, test runner, or the app imports the package.
4. **Time.** Quarantine is not prevention. An attacker who stays undetected for
   14 days clears it. It also blocks genuine urgent security patches; the escape
   hatches are `--min-release-age=0` for one invocation, or
   `min-release-age-exclude`.
5. **Anything that shells out to npm.** Env vars outrank config files, so any
   tool invoking npm on your behalf can set `npm_config_*` and flip these.

## Traps

| Trap | What actually happens |
|---|---|
| `--dry-run` to test the git gate | Dry runs never fetch, so `allow-git` is never exercised and every result is meaningless. Test with real installs. |
| `approve` before installing | `ENOMATCH`. It matches *installed* packages, so `--ignore-scripts` first. |
| A permissive run "fixing" the git gate | Once the dep is cached, the gate stops firing. Clear the cache before re-testing. |
| Project `.npmrc` `allow-scripts` | **Replaces** the user list, it does not merge. |
| `package.json` `allowScripts` present | Silently overrides `.npmrc` entirely; npm warns. |
| A typo in `allow-git` | Fails **closed**. Verified: `garbage` blocks exactly like `none`. |
| Upgrading npm on this machine | Volta owns it (`~/.volta/bin/npm`). `volta install npm@12` is the native path. `npm i -g npm@12.0.1` was also verified to work and leaves `volta list npm` reporting `npm@12.0.1 (default)`. |
| `npm i -g npm@12` getting 12.0.1 | Not a bug. `min-release-age=14` is refusing the newer 12.0.2. The policy applies to npm itself. |

## Worked example

`zotero-api-plus`, 2026-08-03, npm 12.0.1. Three scripts blocked:

```
@swc/core@1.15.33 (postinstall: node postinstall.js)
es5-ext@0.10.64   (postinstall: node -e "try{require('./_postinstall')}catch(e){}" || exit 0)
esbuild@0.28.0    (postinstall: node install.js)
```

Reading `node_modules/es5-ext/_postinstall.js` before approving showed it reads
`Intl.DateTimeFormat().resolvedOptions().timeZone`, compares against 28 Russian
zones, and prints a political message. Benign protestware. But it geolocates the
machine at install time and its `try{}catch(e){}` with `|| exit 0` guarantees it
reports nothing either way, which is the shape a real payload uses. Denied. The
other two fetch platform binaries and were approved pinned. `tsc` passes with
`es5-ext` denied, so nothing needed it.

That is the whole point of the procedure: the script was readable *because* it
had been blocked first.

## Where this skill lives, and how to fix it

**Source of truth, edit here:**

```
~/people/Brian/brian-ed3d-plugins/plugins/denubis-00-getting-started/skills/npm-install-script-policy/SKILL.md
```

**What Claude actually reads at runtime** is a version-pinned copy:

```
~/.claude/plugins/cache/denubis-plugins/denubis-00-getting-started/<version>/skills/npm-install-script-policy/SKILL.md
```

**Editing the cache copy appears to work and then evaporates** on the next
version bump. The two are byte-identical when in sync, which is what makes the
mistake easy. Always edit the source.

To ship a change (this repo's `CLAUDE.md` requires all three):

1. Edit `SKILL.md` in the source path above.
2. Bump `version` in `plugins/denubis-00-getting-started/.claude-plugin/plugin.json`.
3. Update the matching version in `.claude-plugin/marketplace.json` at the repo
   root, and add a `CHANGELOG.md` entry at the top.

Then reinstall or update the plugin so the cache picks it up.

**If something here is wrong**, the failure is usually one of: npm renamed a
command between majors, a default flipped, or a claim was tested with
`--dry-run` and never actually exercised. Re-verify with a real install and a
positive control before editing, and date the correction. Every factual claim
above carries the version it was checked against, so a claim without one is a
claim someone added without testing.
