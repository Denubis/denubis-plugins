# ripgrep reference

Companion to `SKILL.md`, which carries the four silent-failure flags and the
`-h`/`-H`/`-I` triple. This file holds the rest.

**Versions measured 2026-08-07: ripgrep 14.1.0, GNU grep 3.11.** Re-run `rg --help`
before trusting a row against a different release.

## The three that error loudly

These exit 2 with a message. They cost a retry and nothing else.

| you meant | in grep | rg reads it as | error | **type this instead** |
|---|---|---|---|---|
| extended regex | `-E` | `--encoding` | `unknown encoding: <your pattern>` | nothing — rg regexes are extended already |
| align output | `-T` | `--type-not` | `unrecognized file type: <your pattern>` | nothing — rg has no equivalent |
| directory handling | `-d` | `--max-depth` | `value is not a valid number` | `--max-depth N`, or nothing to recurse fully |

## The three that differ without biting

`-P` (rg `--pcre2` / grep `--perl-regexp`), `-z` (rg `--search-zip` / grep
`--null-data`), `-U` (rg `--multiline` / grep `--binary`). All boolean, all exit 0, and
on ordinary text searches the result is usually what you wanted. Know they differ;
spend no attention on them.

For a regex that must cross line boundaries, `-U`/`--multiline` is correct, and
`--multiline-dotall` additionally lets `.` match a newline.

## Safe in both tools

`-A -B -C -F -H -V -a -b -c -e -f -i -l -m -n -o -q -v -w -x`

Twenty flags mean the same thing in both. Most invocations need only these.

## grep flags rg rejects outright

`-D` `-G` `-R` `-Z`. These error rather than misfire, which makes them harmless.

There is no recursive flag: **rg recurses by default.** `-R` and `-r` are both wrong,
and only one of them tells you.

## Defaults that shape what a search can see

`rg` skips hidden files and gitignored paths.

| | plain files | hidden | gitignored |
|---|---|---|---|
| `rg` | yes | **no** | **no** |
| `rg --hidden --no-ignore` | yes | yes | yes |
| `/usr/bin/grep -r` | yes | yes | yes |

`-u` equals `--no-ignore`; `-uu` adds `--hidden`; `-uuu` adds `--binary`.

This bites hardest on `.notes/`, which is both hidden and gitignored. Neither flag
alone reaches it. A half-corrected search still returns nothing and now carries false
confidence, so pass both or name the path explicitly.

## `grep` in the Bash tool is not GNU grep

Claude Code shims `grep` to `ugrep` in `-G` mode. Under `-i`, a `\b` immediately before
a foldable non-ASCII letter folds the letter into the escape and fails to compile — it
exits 2, and a pipeline discarding stderr then reports zero matches for a term that
occurs thousands of times. Use `rg`, or `/usr/bin/grep` when POSIX semantics matter.

`ugrep` earns its place for fuzzy matching (`-Z`) and for patterns crossing line
boundaries, subject to that `-i` breakage. Fuzzy results are leads, not proof.

## Output shape

`--json` gives structured output. `-C N` adds context lines and inflates output
severalfold depending on match density. `-M`/`--max-columns` truncates long lines.
`-t`/`--type` filters by language and is cheaper than a glob; `-g`/`--glob` handles
what `--type` cannot.
