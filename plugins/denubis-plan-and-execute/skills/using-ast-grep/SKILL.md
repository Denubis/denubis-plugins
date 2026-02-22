---
name: using-ast-grep
description: Use when searching for code patterns by structure rather than text — function definitions, class hierarchies, decorator usage, import shapes, call sites with arguments. Also use for structural rewrites — renaming functions, migrating APIs, replacing patterns across a codebase. Provides decision guidance for ast-grep vs text Grep and command examples for Python and TypeScript.
user-invocable: false
---

# Using ast-grep for Structural Code Search and Rewrite

ast-grep matches code by AST structure, not text. Use it when the search target has syntactic structure. Use Grep when the target is a literal string. ast-grep can also **rewrite** matched code structurally — renaming functions, migrating API calls, replacing patterns across a codebase while preserving arguments and formatting.

## When to Use ast-grep vs Grep

| Looking for... | Use | Why |
|---|---|---|
| Text string, error message, config key | Grep | Literal match, fast |
| Function/method definition | ast-grep | `def foo` in a comment shouldn't match |
| All callers of a function | ast-grep | `foo($$$)` catches all argument variations |
| Class inheriting from X | ast-grep | Requires YAML rule — see below |
| Import pattern | ast-grep | `from $MOD import $NAME` handles all forms |
| Decorated function | ast-grep | Requires YAML rule — see below |
| String in comments or docstrings | Grep | ast-grep skips non-code nodes |
| Pattern across mixed file types | Grep | ast-grep needs a language specified |
| Variable assignment pattern | ast-grep | `$VAR = SomeClass($$$)` is structural |
| Rename function/method calls | ast-grep | `--rewrite` preserves all arguments |
| Migrate API patterns | ast-grep | Structural rewrite handles argument variations |
| Replace deprecated calls | ast-grep | YAML `fix` field for complex replacements |

**Rule of thumb:** If the target has parentheses, nesting, or argument lists, use ast-grep. If it's a name or literal string, use Grep. If you need to **change** matched code (not just find it), use ast-grep's rewrite capabilities.

## Simple Patterns (ast-grep run)

```bash
ast-grep run --pattern '<pattern>' --lang <lang> [path]
```

### Python

| Goal | Command |
|---|---|
| Function definitions | `ast-grep run -p 'def $FUNC($$$ARGS)' -l py src/` |
| Async functions | `ast-grep run -p 'async def $FUNC($$$ARGS)' -l py src/` |
| Class definitions | `ast-grep run -p 'class $NAME' -l py src/` |
| Imports from module | `ast-grep run -p 'from $MOD import $NAME' -l py src/` |
| Function calls | `ast-grep run -p 'some_function($$$ARGS)' -l py src/` |
| Method calls | `ast-grep run -p '$OBJ.method($$$ARGS)' -l py src/` |
| Assignments | `ast-grep run -p '$VAR = SomeClass($$$ARGS)' -l py src/` |

### TypeScript

| Goal | Command |
|---|---|
| Function declarations | `ast-grep run -p 'function $FUNC($$$ARGS)' -l ts src/` |
| Arrow functions | `ast-grep run -p 'const $NAME = ($$$ARGS) => $$$BODY' -l ts src/` |
| Interface definitions | `ast-grep run -p 'interface $NAME { $$$ }' -l ts src/` |
| Named imports | `ast-grep run -p 'import { $$$NAMES } from $MOD' -l ts src/` |

### Meta-variables

- `$NAME` — matches one AST node. Reuse enforces identity: `$A == $A` matches `x == x` but not `x == y`.
- `$$$ARGS` — matches zero or more nodes (variadic).
- `$_` — matches one node, non-capturing.

### Output

Add `--json` for structured output with file paths, ranges, and captured meta-variables. Add `-C 3` for context lines.

## YAML Rules (ast-grep scan)

Escalate from `run` to `scan` when you need negation, nesting, or combined conditions.

**Constraint:** `scan` rules require `kind` somewhere in the rule — `pattern` alone is rejected. Use `all:` to combine `kind` with other conditions.

### Classes with inheritance (cannot use simple patterns)

`class $NAME($BASE)` produces an ERROR node — the parenthesized base class syntax doesn't parse as a valid pattern. Use a YAML rule:

```bash
ast-grep scan --inline-rules 'id: x
language: python
rule:
  kind: class_definition
  has:
    kind: argument_list
    stopBy: end' src/
```

For a specific base class:
```bash
ast-grep scan --inline-rules 'id: x
language: python
rule:
  kind: class_definition
  has:
    kind: argument_list
    has:
      pattern: "BaseModel"
    stopBy: end' src/
```

### Decorated functions (cannot use simple patterns)

In Python's AST, decorators and function definitions are separate child nodes of a `decorated_definition` parent. Simple `run -p '@deco def func()'` does not work.

Find all decorated functions:
```bash
ast-grep scan --inline-rules 'id: x
language: python
rule:
  kind: decorated_definition' src/
```

Find functions with a specific decorator:
```bash
ast-grep scan --inline-rules 'id: x
language: python
rule:
  kind: decorated_definition
  has:
    kind: decorator
    has:
      pattern: "pytest.fixture"' src/
```

### Methods inside a specific class

```bash
ast-grep scan --inline-rules 'id: x
language: python
rule:
  all:
    - kind: function_definition
    - inside:
        kind: class_definition
        stopBy: end' src/
```

### Functions missing a decorator

```bash
ast-grep scan --inline-rules 'id: x
language: python
rule:
  kind: function_definition
  not:
    has:
      pattern: "@login_required"' src/
```

### Await inside loops (antipattern)

```bash
ast-grep scan --inline-rules 'id: x
language: python
rule:
  pattern: "await $EXPR"
  inside:
    kind: for_statement
    stopBy: end' src/
```

### Key relational rules

- `inside: { kind: X, stopBy: end }` — target is contained within X. Always add `stopBy: end` or it only searches one level.
- `has: { kind: X, stopBy: end }` — target contains X.
- `not: { ... }` — negation.
- `all: [...]` / `any: [...]` — boolean combinators.

## Complex Rules via Temp File

When inline YAML quoting gets unwieldy, write a temp file:

```bash
cat > /tmp/sg-rule.yaml << 'EOF'
id: find-unguarded-await
language: python
rule:
  pattern: "await $EXPR"
  inside:
    kind: for_statement
    stopBy: end
  not:
    inside:
      kind: try_statement
      stopBy: end
EOF
ast-grep scan --rule /tmp/sg-rule.yaml src/
rm /tmp/sg-rule.yaml
```

## Structural Rewrites

ast-grep can rewrite matched code, not just find it. Meta-variables captured in the pattern are substituted into the replacement, preserving arguments, formatting, and indentation.

### Simple rewrites (ast-grep run --rewrite)

```bash
ast-grep run -p '<pattern>' -r '<replacement>' -l <lang> [--update-all] <path>
```

Without `--update-all`, this is a **dry run** — shows diffs but changes nothing. Add `-U` / `--update-all` to apply changes in place.

**Do not use `--interactive` (`-i`).** It requires a TTY and panics in non-interactive shells (agent environments, CI/CD, pipes).

### Python examples

| Goal | Command |
|---|---|
| Rename function calls | `ast-grep run -p 'old_func($$$ARGS)' -r 'new_func($$$ARGS)' -l py -U src/` |
| Rename method calls | `ast-grep run -p '$OBJ.process($$$ARGS)' -r '$OBJ.execute($$$ARGS)' -l py -U src/` |
| Wrap call in another | `ast-grep run -p 'json.loads($EXPR)' -r 'safe_json_loads($EXPR)' -l py -U src/` |

### TypeScript examples

| Goal | Command |
|---|---|
| Optional chaining | `ast-grep run -p '$OBJ && $OBJ()' -r '$OBJ?.()' -l ts -U src/` |
| Rename imports | `ast-grep run -p 'import { OldName } from $MOD' -r 'import { NewName } from $MOD' -l ts -U src/` |

### YAML rules with fix field

For complex rewrites that need `kind`, relational rules, or multi-line replacements, add a `fix` field to a YAML rule:

```bash
cat > /tmp/sg-rewrite.yaml << 'EOF'
id: rename-method
language: python
rule:
  pattern: self.process($$$ARGS)
fix: self.execute($$$ARGS)
EOF
ast-grep scan --rule /tmp/sg-rewrite.yaml --update-all src/
rm /tmp/sg-rewrite.yaml
```

When `scan --inline-rules` needs a `fix`, remember the `kind` requirement still applies:

```bash
ast-grep scan --inline-rules 'id: x
language: python
rule:
  all:
    - kind: call
    - pattern: print($$$ARGS)
fix: logger.info($$$ARGS)' --update-all src/
```

### Rewrite safety

| Mode | Flag | Behaviour |
|---|---|---|
| Dry run | (default, no flag) | Shows diffs, changes nothing |
| Apply all | `--update-all` / `-U` | Rewrites files in place |
| Interactive | `--interactive` / `-i` | **Do not use** — requires TTY, panics in agents |

**Always dry-run first.** Run without `-U` to review diffs, then add `-U` to apply.

**Meta-variable identity in rewrites:** `$NAME` in the replacement refers to the same capture as `$NAME` in the pattern. `$$$ARGS` expands to all captured nodes with original formatting preserved.

## Debugging Patterns That Don't Match

1. **Check AST structure:** `ast-grep run -p '<pattern>' -l py --debug-query=ast` — shows how the pattern is parsed.
2. **Narrow scope:** Test against a single known file first, then expand.
3. **Check language:** Explicit `--lang` avoids auto-detection surprises.
4. **Try kind-based matching:** If a pattern doesn't match, the structure may not be what you expect. Use `kind:` in a YAML rule instead.

Do not use `--strictness` flags with meta-variable patterns (`$NAME`, `$$$`). Only the default `smart` mode handles meta-variables reliably. Non-default strictness modes reject patterns containing meta-variables.
