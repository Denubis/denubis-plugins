---
name: controlled-dependency-upgrade
description: Use when auditing or upgrading Python dependencies - verifies direct use, reads current release evidence, changes one dependency at a time, and reruns project gates
user-invocable: true
argument-hint: "[package or audit scope]"
---

# Controlled Dependency Upgrade

## Establish scope and baseline

Distinguish an audit request from authority to change dependencies. Resolve the project
manifest, lockfile, Python range, direct dependencies, configured package index, project
instructions, dependency rationale, and required test gates.

Use the configured package-manager cache and index exactly as provided. Do not set an
alternate cache directory or fall back to a repository, home, or temporary cache. If the
configured cache is missing, read-only, or outside the permitted filesystem, stop and ask
for the environment or sandbox configuration to be fixed.

Observe the baseline gates before changing the lock state. Record existing failures rather
than attributing them to a later upgrade.

## Audit direct dependencies

For each direct dependency in scope, inspect imports, entry points, configuration, plugins,
type-only use, build use, and runtime loading. A zero import search is not enough to call a
package unused. Name the search coverage and positive controls.

Do not upgrade a transitive package directly. Resolve it through the direct parent unless
the project deliberately pins it for a documented compatibility or security reason.

Removal is a separate behavior change. Present evidence for an apparently unused direct
dependency and ask before removing it unless the human explicitly requested removals.

## Upgrade one package

Upgrade one direct dependency at a time:

1. Resolve the installed and candidate versions.
2. Read current authoritative release notes, migration guidance, security advisories, and
   supported Python range for the versions crossed.
3. Identify affected project APIs and tests before editing.
4. Use the package manager's native locked upgrade command for that package only.
5. Inspect manifest and lockfile diffs, including unexpected transitive movement.
6. Run focused compatibility checks and every required project gate.
7. Update current code or configuration only for demonstrated incompatibilities within
   the requested upgrade; do not bundle unrelated modernization.

If a gate fails, state a causal hypothesis before changing code. If the candidate version
is incompatible or unexplained transitive changes cannot be bounded, restore only the
manifest and lock changes owned by this package attempt using a recoverable method, then
report the evidence. Preserve all pre-existing edits.

Proceed to another package only after the repository is at a verified state. Ordering is
based on dependency relationships and risk, not on creating a sequence of commits.

## Return

Report each old and new version, authoritative sources consulted, manifest and lockfile
changes, compatibility edits, and exact gate results. Identify upgrades deferred and why.

Do not commit, push, or publish. A dependency-upgrade request authorises the scoped source
and lock changes, not release or Git-history actions.
