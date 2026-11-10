# Accepted durable-record findings

Keep accepted citation findings in `docs/durable-record-exceptions.json` at the project
root and track it with the project. The checker loads this file automatically from the
current checkout, including when invoked from a subdirectory. In a linked worktree,
that checkout's list also applies to notes read from the main checkout.

Add an entry when the human has accepted an intentional reference. Record why it is
acceptable in `reason`; do not infer approval from the existence of a finding. An
existing matching entry records the acceptance, so do not ask the human to approve it
again. Remove or revise an entry when that ruling changes.

The file contains one object with an `exceptions` array. Every entry has exactly four
nonempty, single-line string fields:

| Field | Meaning |
|---|---|
| `path` | Source Markdown document, relative to the repository root, using `/` separators. Use its normalized path without a leading `./` or any `..` segments. |
| `kind` | One of `WORKTREE`, `EXCHANGE`, or `IGNORED`. |
| `reference` | Exact reference text emitted by the checker, including any locator suffix. Copy it from the finding; do not substitute its resolved filesystem path. |
| `reason` | The human's reason for accepting this reference. It can include the project's ruling reference. |

The checker matches `path`, `kind`, and `reference` literally. There are no patterns,
directory exemptions, or line numbers. One entry covers repeated occurrences of that
reference in that source document and survives line movement. The same reference in
another document, a changed reference, or a different finding kind needs its own accepted
entry. An entry whose finding no longer occurs is inert.

For example, a DVC-managed CSV may resolve through a shared cache under `.worktrees/`
while remaining a valid project data reference. A command example's `--csv-path`
argument may intentionally name that same CSV. After the human accepts those findings,
a project's list could contain the following illustrative entries (these are example
paths, not approvals for any existing project):

```json
{
  "exceptions": [
    {
      "path": "docs/decisions/0001-register.md",
      "kind": "WORKTREE",
      "reference": "data/register.csv",
      "reason": "Human accepted the DVC register; its shared cache location does not make this project data reference temporary."
    },
    {
      "path": "docs/reference/export.md",
      "kind": "WORKTREE",
      "reference": "data/register.csv",
      "reason": "Human accepted the --csv-path argument in the export command example; it intentionally names the DVC register."
    }
  ]
}
```

The second entry could match `data/register.csv` extracted from
`uv run scripts/export.py --csv-path data/register.csv` in that source document. It
does not exclude command arguments elsewhere from checking.

Accepted findings retain their original kind and reference and gain an
`[accepted: reason]` annotation. The summary includes them in `citations` and `advisory`,
and reports the number of matched findings as `accepted`. They do not block even with
`--strict`; unmatched findings retain their usual behavior. A missing file or empty
array adds no exceptions. Invalid JSON, invalid fields, duplicate entries, and an
unreadable file fail with exit status 2; fix the list before relying on the check.
