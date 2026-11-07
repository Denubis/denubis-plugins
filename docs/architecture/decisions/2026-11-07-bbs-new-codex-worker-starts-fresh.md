# ADR 2026-11-07-bbs-new-codex-worker-starts-fresh — A worker made by `new` is a new worker; it does not inherit the old worker's folder, model or effort

**Status:** Accepted (2026-11-07). Refines the Claude-drives-Codex adapter's `new` verb.

## Authority evidence

Session `d280d2b3-8069-40c1-8f99-fcd0694017d7`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d280d2b3-8069-40c1-8f99-fcd0694017d7.jsonl`):

- Line 3231, the supervisor's question (`assistant` record
  `20adae60-e36c-4f69-b7f7-1f158b862761`, 2026-11-07T06:44:45Z): "when `new` replaces a
  Codex worker, must the new worker keep the old one's folder, model and effort?"
- Line 3234, Brian's answer (`user` record `077c5ec3-27d4-4e47-a44d-dc99cac3d541`,
  2026-11-07T06:49:44Z, 17:49 Australia/Sydney): "shared local, it's fine. new worker is
  new. get sonnet on renaming." The second sentence answers this question; the first is
  recorded in ADR 2026-11-07-bbs-codex-notes-use-shared-service.

```sh
sed -n '3231p;3234p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d280d2b3-8069-40c1-8f99-fcd0694017d7.jsonl
```

The open-questions ticket it closes, raised 2026-11-07 by Codex `/root` as A2, asked: "Must `new --file F` preserve the bound
worker's cwd, model, and effort when creating its replacement thread?"

## Context

`new` comes from Brian's queued message of 2026-11-02 ("if we want a clear, we just make a
new session as you say. Just make it a single-line so we can start --new or what have you",
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f31135e5-0253-441f-8140-bdd86e8940bc.jsonl:1126`,
a `queue-operation` record). Neither that message nor ADR
2026-11-02-bbs-claude-codex-adapter-no-scraping ("Claude drives Codex through a per-client
adapter without reading its screen; a send needs no typing protection, and a clear is a
new session", on the `supervision-infrastructure` branch) said what the replacement's
settings are.

## Decision

The worker `new --file F` creates is a new worker. It does not carry over the bound
worker's working folder, model or effort.

## Consequences

- The replacement's folder, model and effort are set as for any newly dispatched worker:
  given explicitly at dispatch and verified, as Brian's global instructions require. That
  reading, and the exact parameters `new` takes, are the supervisor's and the
  implementer's, not Brian's wording.
- The adapter's thread-start parameters, model and effort checks, and tests for `new` can
  now be designed.
