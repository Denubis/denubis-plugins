---
name: defense-in-depth
description: Use when invalid or untrusted data crosses system boundaries - assigns distinct invariants to the earliest reliable owners and tests bypass paths
---

# Boundary Validation

## Purpose

Prevent an invalid state from reaching the component that cannot handle it. Defense in
depth means independent boundaries protect distinct invariants or fault sources; it does
not mean copying the same check into every layer.

## Trace and assign ownership

Trace the invalid value from producer through every consumer to the observed failure. Map
trust transitions such as request parsing, deserialization, domain construction,
persistence, external API calls, process execution, and destructive filesystem actions.

Validate untrusted data at the earliest owned boundary that can state the invariant and
return an actionable error. Use stronger structural owners when available:

- parser or schema for representation and required fields;
- domain constructor or type for business invariants;
- database constraint for persisted uniqueness and referential integrity;
- transaction boundary for state-dependent consistency;
- permission or environment guard for destructive external actions; and
- protocol adapter for an external service's contract.

Each additional check must enforce a distinct invariant, protect a bypass path, or provide
a safer failure boundary. Do not duplicate the same validation in adjacent layers without
naming the independent path that can bypass the first.

## Design the failure

Reject invalid data before partial side effects. Error output names the violated invariant
and safe identifying context without exposing secrets. Preserve lower-level causes when
they help diagnosis, but translate them at the boundary that owns the public error
contract.

For destructive operations, resolve and validate the exact target immediately before the
effect. Avoid unresolved globs, broad environment variables, and assumptions that a path
or identifier still refers to the object inspected earlier.

## Test the actual defenses

Test the ordinary valid path and each invalid class. Test the bypass path that justifies
an additional layer—for example direct domain construction that skips request parsing, or
a concurrent write that bypasses an application uniqueness check.

Where persistence owns the invariant, include a test that exercises the real constraint.
Where an external action is guarded, include a non-match control and verify that the
protected effect did not occur. A mocked intermediate function cannot establish the
boundary it replaced.

Keep the fix within the demonstrated data flow. Do not add unrelated validation or turn a
specific invalid-state bug into a framework rewrite.
