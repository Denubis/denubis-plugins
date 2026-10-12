# ADR 0029 — Zotero writes go through Zotero 10's stock local API, delete means trash, and zotero-api-plus is kept only for what stock cannot do

**Status:** Accepted (2026-10-12). Design:
`docs/design-plans/2026-10-12-bibliography-0.19-scan-detection-and-zotero-crud.md`.

## Authority evidence

Original human messages in session `e65bf924-a18d-429a-881d-418e144eb062`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/`):

- `ccchat:v1:claude:e65bf924-a18d-429a-881d-418e144eb062:uuid:3bfc219f-1bc6-4c2c-bcfd-1f159b96cbf7`
  (2026-10-11T23:08Z): "ok, and yes we want to add item, we want to add item from
  other collection/library, and we want all the basic CRUD capabilities and yes, let's
  design all please."
- `ccchat:v1:claude:e65bf924-a18d-429a-881d-418e144eb062:uuid:f4364e99-f5fc-4c4f-b02d-ae3b115f517c`
  (2026-10-11T23:58Z), answering the question "stock Zotero 10 local API, or new
  zotero-api-plus endpoints, for add-to-collection, delete and create?" with the stock
  API and trash-not-erase recommended: "whatever we need that is as simple and as
  reiable as possible".
- `ccchat:v1:claude:e65bf924-a18d-429a-881d-418e144eb062:uuid:1573dc00-efe6-42bf-8950-09443090812b`
  (2026-10-12T00:17Z), on a review finding that collection `DELETE` erases: "um, yes,
  we just want to send things into trash, we never want to expunge right now", and in
  the following message, "if there's a no-trash thing then that's fine, but where
  trash exists we use it".

Resolvers:

```sh
cc-search-chats resolve ccchat:v1:claude:e65bf924-a18d-429a-881d-418e144eb062:uuid:f4364e99-f5fc-4c4f-b02d-ae3b115f517c --reference-only --json
cc-search-chats resolve ccchat:v1:claude:e65bf924-a18d-429a-881d-418e144eb062:uuid:1573dc00-efe6-42bf-8950-09443090812b --reference-only --json
```

The "where trash exists we use it" qualifier arrived mid-turn and is stored only as a
`queued_command` record (timestamp `2026-10-12T00:18:24.086Z`), which the search index
does not expose as a message. Raw-record resolver:

```sh
/usr/bin/grep -n "no-trash thing" /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--claude-worktrees-bibliography-0-19-design/e65bf924-a18d-429a-881d-418e144eb062.jsonl
```

## Context

The bibliography skill needed to file an existing item into a collection, remove an
attachment, create an item, and manage collections. zotero-api-plus 0.7.2 has no such
endpoints. Zotero 10's own local API does: `server_localAPI.js` in the installed 10.0.6
bundle implements `POST`, `PUT`, `PATCH`, and `DELETE` for items and collections, with
`If-Unmodified-Since-Version` conflict checks, behind the same server-ID and API-key
gate the skill's `zotero_auth.py` already satisfies (ADR 0002 in zotero-api-plus).
Stock `DELETE` calls `eraseTx()`, which is permanent and removes attachment storage
directories; `fromJSON` accepts `deleted: true`, which moves an item to the trash.

## Decision

1. New write helpers use the stock local API. zotero-api-plus is not extended for
   operations stock already provides; it keeps cross-library copy, fetch by identifier,
   annotations, and forced auto-export.
2. The skill never erases. For items, attachments, and collections, "delete" is
   `PATCH` with `deleted: true`; restore is the reverse, and because Zotero's
   collection restore is not recursive the helper restores listed descendants itself.
   Stock `DELETE` is never sent. Emptying the trash stays a human action in Zotero.
   Where a Zotero object type has no trash, erasure is still not performed; that
   operation is simply out of scope.
3. A write is protected by the state it depends on. Modifying an existing item or
   collection carries `If-Unmodified-Since-Version` from the read the payload was built
   from, and a 412 stops the helper rather than retrying. Creating an object or
   registering an export has no prior version; those helpers re-resolve their named
   targets at apply time and stop if a resolved key differs from the preview.

## Consequences

- The new helpers are Zotero 10 only and refuse on a server without a
  `Zotero-Server-ID` header.
- One write primitive in `zotero_local_api.py` is shared by every helper, so the
  preview-then-`--apply` shape is uniform.
- Library and collection names are resolved through zotero-api-plus
  `/api/plus/libraries`, the source `copy_item.py`, `fetch.py`, and `update_item.py`
  already use, so the new helpers require the extension to be installed even though
  their writes go to stock. Ruled 2026-10-12 during implementation planning (asked
  "Which source should `list_libraries()` read: stock Zotero, or the zotero-api-plus
  `/libraries` endpoint?", answered "api-plus"); recorded in
  `docs/implementation-plans/2026-10-12-bibliography-0.19-scan-detection-and-zotero-crud/plan.md`,
  deviation 1.
- A future Zotero release that removes stock writes invalidates this record.
