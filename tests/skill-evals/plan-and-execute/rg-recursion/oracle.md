# Evaluator oracle: ripgrep native recursion

Read this only after the actor has finished.

## Behavior under evaluation

The actor must translate the recursive-search intent into ripgrep semantics before the
command reaches an approver. Ripgrep searches directories recursively without a recursion
flag; its `-r` option means replacement.

## Evidence to inspect

- The exact emitted command and tool trace.
- Exit status 0 and the positive nested match
  `src/nested/example.txt:2:satellite`.
- Whether the command omitted standalone or bundled grep-style `-r` options.

## Acceptable variation and controls

`rg -n`, `rg --line-number`, fixed-string flags, filename controls, and explicit scope
flags may vary. The nested positive match proves recursion was exercised; `other.txt` is
a non-match control.

The method fails if the actor emits `rg -r`, bundles it as in `rg -rn`, relies on an
approver to correct the command, or reports success without the nested positive match.
