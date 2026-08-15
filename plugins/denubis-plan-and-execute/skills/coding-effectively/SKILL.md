---
name: coding-effectively
description: Use when writing or reviewing code - inspects project conventions and routes only the testing, boundary, language, and data procedures relevant to the current change
---

# Coding Effectively

## Start from the project

Read project instructions, formatter, linter, type checker, test runner, dependency
configuration, and two or three relevant implementations. Determine whether mixed patterns
are intentional boundaries or migration state before selecting one.

Read project configuration before selecting tools. Check the documented invocation and
installed executable read-only. Do not modify a tool registry merely because a tool was
discovered during a task. If a required tool is missing or cannot use its configured
cache, report that boundary rather than inventing an installation or cache location.

## Route only what applies

Load only the procedures relevant to the current change:

| Condition | Procedure |
|---|---|
| Implementing a feature, bug fix, or behavioral refactor | `coding-tdd` |
| About to claim a result | `coding-verify` |
| Business decisions are mixed with I/O | `coding-fcis` |
| Invalid or untrusted data crosses a boundary | `defense-in-depth` |
| Writing Python | `coding-python-idioms` |
| Designing or reviewing tests | `coding-good-tests` |
| Serialization, normalization, validation, or algebraic pure logic | `coding-property-testing` |
| PostgreSQL schema, queries, or transactions | `howto-develop-with-postgres` |
| Repeated primitive operation over regular bulk data | Surface a SIMD-shaped candidate using the detector below |

Do not load every coding reference for every edit. A documentation-only change does not
need Python idioms; a pure calculation does not need database guidance; a code review that
makes no edits does not need the implementation cycle.

## Notice SIMD-shaped work

While inspecting code, report `SIMD-shaped candidate: <location>` when a loop or bulk
operation has all of these observable properties:

- it applies the same primitive comparison, arithmetic operation, or transform across a
  regular sequence of bytes or numeric values;
- iterations are independent except for a simple reduction or first-match selection;
- the data is contiguous, or its existing representation exposes a contiguous buffer;
  and
- the expected input size or call frequency is known. Do not infer hotness from the loop's
  shape alone.

Name the matching properties and the evidence still missing, especially a profile and a
representative benchmark. Do not introduce vector code, a native extension, or a new
dependency on the strength of this detection. If the user chooses to investigate and
measurement shows that the candidate is hot, use that concrete code, language, compiler,
and target hardware to design SIMD guidance.

For Python, distinguish API-level bulk operations from CPU intrinsics. A loop over boxed
Python objects may justify investigating an existing bulk operation or native backend; it
is not itself a hand-written SIMD implementation target. Surface lower-level SIMD only
when the data already lives in a suitable buffer or array, or the hot loop is inside
compiled code.

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
