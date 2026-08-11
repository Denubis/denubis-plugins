---
name: using-code-search
description: Use when writing or reviewing repository searches with rg or ast-grep, especially when translating grep flags, choosing text versus structural search, or interpreting a negative result
user-invocable: false
---

# Searching Code: rg and ast-grep

Two tools, one decision. `rg` matches text. `ast-grep` matches syntax. Most mistakes in
both come from typing a flag or a name that means something else than you expect.

**Versions measured 2026-08-07: ripgrep 14.1.0, GNU grep 3.11, ast-grep 0.44.1.** Flag
meanings move between releases; re-run `rg --help` before trusting a row elsewhere.

Full references: [`ripgrep.md`](ripgrep.md) and [`ast-grep.md`](ast-grep.md).

## Pick the tool

| Looking for... | Use | Why |
|---|---|---|
| Text string, error message, config key | `rg` | Literal match, fast |
| String in comments or docstrings | `rg` | ast-grep skips non-code nodes |
| Pattern across mixed file types | `rg` | ast-grep needs a language specified |
| Function/method definition | `ast-grep` | `def foo` in a comment shouldn't match |
| All callers of a function | `ast-grep` | `foo($$$)` catches all argument variations |
| Import pattern | `ast-grep` | `from $MOD import $NAME` handles all forms |
| Variable assignment pattern | `ast-grep` | `$VAR = SomeClass($$$)` is structural |
| Class inheriting from X | `ast-grep` | Requires a YAML rule |
| Decorated function | `ast-grep` | Requires a YAML rule |
| Rename function/method calls | `ast-grep` | `--rewrite` preserves all arguments |
| Migrate API patterns | `ast-grep` | Structural rewrite handles argument variations |
| Replace deprecated calls | `ast-grep` | YAML `fix` field for complex replacements |

**Rule of thumb:** parentheses, nesting, or argument lists means ast-grep. A name or
literal string means rg. Needing to *change* the matched code means ast-grep.

## The four rg flags that fail silently

`rg` is not `grep` with a faster engine. These four exit 0 and print output that looks
like a successful search.

| you meant | in grep | rg reads it as | you get | **type this instead** |
|---|---|---|---|---|
| recurse | `-r` | `--replace` | matches rewritten; next token became the pattern | nothing — rg recurses by default |
| files without a match | `-L` | `--follow` | **the opposite file set** | `--files-without-match` |
| hide filenames | `-h` | `--help` | the help text | `-I` |
| suppress error messages | `-s` | `--case-sensitive` | correct rows, wrong case behaviour | `--no-messages` |

Observed on a two-file fixture:

```
$ rg -rn 'alpha' fix/          # meant: recursive, line numbers
fix/f.txt:n beta               # got: every 'alpha' replaced with 'n'
fix/f.txt:gamma n              # exit 0. Real paths. Real content. Wrong.

$ /usr/bin/grep -rL 'alpha' fix/    $ rg -L 'alpha' fix/
fix/g.txt                           fix/f.txt:alpha beta
                                    fix/f.txt:gamma alpha
# grep -L lists files WITHOUT a match. rg -L follows symlinks and lists files WITH one.
```

`rg` has **no short flag** for `--files-without-match`. Write it long.

`-r` is the worst of the four because the output is well-formed. Nothing signals it.

## Filename control: the `-h` / `-H` / `-I` triple

The most-hit trap, because the grep reflex is `-h`.

| intent | grep | rg |
|---|---|---|
| suppress filenames | `-h` | **`-I`** |
| force filenames | `-H` | `-H` (same) |
| help | `--help` | `-h` or `--help` |

`rg -h 'pattern' path/` prints help and exits 0, so a pipeline that counts lines
reports the length of the help text.

Six further collisions, the visibility defaults, and the ugrep shim are in
[`ripgrep.md`](ripgrep.md).

## Spell it `ast-grep`, not `sg`

`sg` is ast-grep's own short name, but `/usr/bin/sg` is `newgrp`, an unrelated setgid
utility. Which one you reach depends on PATH order, and that differs between an
interactive shell, a subagent, and a hook. `ast-grep` always resolves correctly.

Patterns, YAML rules, and structural rewrites are in [`ast-grep.md`](ast-grep.md).

## Reading a result of zero

An empty result is a claim about the search, not about the repository. Before believing
it, name what the query could not reach — hidden paths, gitignored paths, untracked
files under `git grep`, a term spelled another way, a string built at runtime — and
close that gap or state the conclusion as bounded by what was actually searched.

This matters most when the empty result is about to authorise building something. The
expensive failure is not the missed match; it is the hours spent rebuilding what was
there all along.
