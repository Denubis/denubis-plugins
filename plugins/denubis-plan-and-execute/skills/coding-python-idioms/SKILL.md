---
name: coding-python-idioms
description: Use when writing Python - follows the project's supported versions and tools, keeps boundaries explicit, and rejects unsafe interpolation and type suppression
---

# Python Decisions

## Establish the project contract

Read `pyproject.toml`, lockfiles, project instructions, formatter, linter, type checker,
test runner, supported Python range, and two or three nearby modules. The repository owns
its interpreter floor and tools. Do not assume Python 3.14, `uv`, `ruff`, `ty`, pytest,
Typer, Pydantic, or a logging library merely because this skill mentions the kind of
problem they solve.

Use syntax supported by the declared floor. Prefer modern built-ins such as `list[str]`
and `X | None` only when that floor permits them. Preserve a deliberate compatibility
style in mixed-version libraries. Run tools through the project's documented invocation;
do not bypass its environment or invent a cache location.

Preserve a committed dependency graph during verification. When a uv project has a
lockfile and dependency resolution is not part of the task, run tests, formatters,
linters, type checkers, and builds with `uv run --frozen ...`; plain `uv run` may
re-resolve and rewrite `uv.lock` from user-level resolver settings. Use `--locked` when
the check must instead prove that project metadata and the lockfile agree. Use unfrozen
`uv lock`, `uv sync`, or `uv run` only when dependency metadata or resolution is an
intentional part of the change, then inspect and verify the resulting lockfile.

## Types describe the real boundary

- Type public interfaces and non-obvious internal values; let ordinary local inference
  work.
- Model meaningful alternatives with unions, enums, protocols, dataclasses, or domain
  types rather than dictionaries whose shape exists only in comments.
- Narrow untrusted or dynamically typed data at the boundary.
- Do not suppress type errors with `# type: ignore`, `cast()` used as an assertion, or a
  broader annotation. Fix the contract, add an adapter, or surface the unresolved library
  boundary.
- Do not add a compatibility annotation or abstraction without a current consumer.

## Strings do not supply escaping policy

Use the destination's structured API:

- parameterized database queries for values and an allowlisted identifier mechanism;
- argument arrays rather than a shell string for subprocesses;
- the template or DOM framework's contextual escaping for HTML; and
- structured serialization for JSON, URLs, and protocols.

An f-string interpolates immediately and is unsafe at those boundaries. A Python 3.14
t-string returns a `Template` for a separate processor; it does not itself escape HTML,
parameterize SQL, or make a shell command safe. Use a t-string only when the chosen
consumer explicitly interprets it with the required context-aware policy.

## Preserve explicit behavior

- Use context managers for resources whose cleanup must run on success and failure.
- Catch the narrow exception the boundary can handle. Preserve cause and context when
  translating errors; never use an empty catch or silently turn a failure into success.
- Avoid mutable default arguments. Use a sentinel when `None` is a valid value.
- Prefer explicit parameters to catch-all `*args` or `**kwargs` at stable interfaces.
- Keep pure decisions separate from I/O when that makes behavior testable, but do not
  create ceremony around a one-line operation.
- Do not mutate a collection while iterating unless the container contract explicitly
  supports it.
- Use the project's logging and configuration owners. A CLI script may intentionally
  print; a service should use its established observable logging boundary.

Treat metaclasses, import hooks, dynamic inheritance, runtime code evaluation, binary
deserialization, and bytecode manipulation as high-consequence mechanisms. Use them only
when a current requirement and testable consumer rule out the simpler alternative. Never
interpret or deserialize untrusted input with a mechanism capable of executing code.

## Evidence

Behavior changes use the project-native red-green-refactor cycle. Run the focused tests,
configured type checker, linter/formatter, and relevant integration check. Confirm each
command exercised the intended interpreter and project. A clean phrase search or the
absence of a type error after suppression is not evidence.
