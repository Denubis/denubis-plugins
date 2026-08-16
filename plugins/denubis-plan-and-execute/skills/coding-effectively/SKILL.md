---
name: coding-effectively
description: Use for direct code work when no more specific execution, debugging, or refactoring workflow already owns the method - inspects project conventions and routes only genuinely needed specialist guidance
---

# Coding Effectively

Do not add this as a second orchestration layer when an already-selected workflow owns the
implementation cycle, verification, and handoff. Use it for direct code work or when a
specific convention or boundary remains unresolved.

## Start from the project

Read project instructions, formatter, linter, type checker, test runner, dependency
configuration, and two or three relevant implementations. Determine whether mixed patterns
are intentional boundaries or migration state before selecting one.

Read project configuration before selecting tools. Check the documented invocation and
installed executable read-only. Do not modify a tool registry merely because a tool was
discovered during a task. If a required tool is missing or cannot use its configured
cache, report that boundary rather than inventing an installation or cache location.

## Route only what applies

Load a detailed procedure only when it adds a method the active workflow does not already
own:

| Condition | Procedure |
|---|---|
| Direct feature, bug-fix, or behavioral-refactor work has no active execution method | `coding-tdd` |
| Completion evidence is not already owned by the active workflow | `coding-verify` |
| Business decisions are mixed with I/O | `coding-fcis` |
| Invalid or untrusted data crosses a boundary | `defense-in-depth` |
| Python compatibility, typing, resource, or interpolation policy is material | `coding-python-idioms` |
| The test boundary or failure discrimination is non-obvious | `coding-good-tests` |
| Serialization, normalization, validation, or algebraic pure logic | `coding-property-testing` |
| PostgreSQL schema, queries, or transactions | `howto-develop-with-postgres` |

Do not load every coding reference for every edit. Familiar syntax, one ordinary
behavioral test, and a routine completion check do not each need another skill file. A
documentation-only change does not need Python idioms; a pure calculation does not need
database guidance; a code review that makes no edits does not need the implementation
cycle.

## Implementation boundaries

- Make the smallest coherent change that satisfies the named behavior.
- Extend an existing semantic owner before adding a parallel module or abstraction.
- Give every new interface a current consumer.
- Encode invalid states with types, constraints, or boundary validation where practical.
- Preserve explicit error behavior; do not swallow failures or suppress type errors.
- Avoid speculative compatibility layers, unused extension points, and unrelated cleanup.
- Keep project and language conventions unless evidence shows they are the defect.

Name files and symbols for their responsibility. Avoid generic containers such as
`utils`, `helpers`, or `common` when a more precise existing owner or name is available.
Size and complexity are investigation signals, not universal numerical gates; judge them
by cohesion, control flow, duplication, and testability.

## Evidence

Implementation state comes from the diff and repository. Correctness claims come from
tests, type checks, builds, and runtime observations that exercise the changed boundary.
A model report, review status, task label, or plausible explanation is not a substitute.
