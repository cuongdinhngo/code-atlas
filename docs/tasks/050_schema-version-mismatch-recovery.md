---
id: 050
slug: schema-version-mismatch-recovery
title: A schema-version mismatch is direction-blind — one message for two opposite situations
phase: 1.5b
milestone: Robustness
status: todo
depends_on: [010, 016]
---

## Goal
`GraphStore._create_schema` (`store.py:249-261`) compares the stored `schema_version` with `!=` and
raises one message for both directions of mismatch:

```
database schema version {found!r} is not {SCHEMA_VERSION!r} — delete {path} and rebuild
(or call build_or_update_index)
```

The two directions need opposite actions:

- **Index older than the server** (`found` < `SCHEMA_VERSION`) — the index predates a schema bump.
  Rebuilding is correct, and `build_or_update_index` already does it in-band (`:41-46`).
- **Index newer than the server** (`found` > `SCHEMA_VERSION`) — the *server process* is stale: it was
  started before the upgrade, or the client was never reloaded. The index is fine. Rebuilding is not
  just unnecessary, it is destructive.

**Observed in the field, round 2 (2026-08-07).** A session against the anchor repo received
`database schema version '3' is not '2'`, read it as a corrupt index, and fell back to narrow-scope
`grep` for the rest of the session. Nothing was wrong with the index — that client's server predated
the v3 merge (task 049). Had the session followed the message's own advice, `build_or_update_index`
would have deleted an 823 MB v3 index and spent ~17 minutes writing a v2 one in its place: a silent
downgrade of shared state, on the instruction of the error text, with no confirmation step. R5.2 forbids
promoting a weaker tier; nothing today forbids overwriting a newer index with an older one.

**The diagnosis tool is the one that cannot answer.** `get_index_status` is documented "Call this
first" and is the entry point every prompt recipe opens with. It degrades gracefully when there is no
database file (`_unbuilt`, `tools/get_index_status.py:53-70`), but a schema mismatch propagates straight
out of `GraphStore(config.db_path)` at `:47`. The tool whose job is to report whether the index is
usable is the one tool that crashes when it is not — so an agent gets a stack trace where it needed a
next action, which is exactly how this ended in `grep`.

Prior art in this repo already gets the analogous case right: `incremental_update` compares
`CONTRACT_VERSION_KEY` and *degrades to a full build* rather than raising (`indexer.py:133-137`). The
schema check should be as considered as the contract check.

## Scope / Deliverables
- **Make the check directional** in `store.py`. Compare as ordered versions, not string inequality, and
  distinguish the two cases — separate exception types, or one type carrying the direction. Each case
  states the action that actually fixes it: rebuild for the older index; *restart or upgrade the server*
  for the newer one.
- **`build_or_update_index` may only auto-heal downward.** `:41-46` catches `SchemaVersionError`
  unconditionally and calls `_unlink_index` (`:73-76`). When the index is newer than the server it must
  refuse — return the mismatch and the action, delete nothing.
- **`get_index_status` answers instead of raising**, in both directions. A payload in the `_unbuilt`
  family (`indexed: false`, the two versions, the action to take) keeps the recipe working: the first
  call still tells an agent what to do next.
- **Decide the query-tool policy and record it.** The recommendation is *no auto-rebuild in query
  tools* — a `search_symbol` that silently costs ~17 minutes is worse than an error — but they should
  fail with the same structured, actionable payload rather than an exception, so an agent can recover
  without a shell. Whatever is chosen, write down why.
- **Sweep the wording.** Any doc or runbook that tells a reader to delete the index on a version error
  needs the newer-index case added (`docs/runbooks/onboarding-a-repo.md`, `README.md` §schema note).

## Constraints
- **No contract change, no schema bump (R3).** This is recovery behaviour around the existing check.
- **No migration runner (R7.4).** The index stays a derived cache; the fix is better diagnosis and a
  refusal to destroy, never an in-place upgrade path.
- **Fail loud stays (R5.3).** This ticket narrows *which* states are unrecoverable — it does not soften
  the rule. A genuinely unusable index must still fail rather than degrade quietly.
- **`get_index_status` stays cheap** — the field retro's answer to "what must not break" was this tool's
  cost. The mismatch payload must not add a query.
- **No language branch in the core (R1.1)**; determinism unchanged (R4).

## Acceptance criteria
- A store written under a *newer* schema: opening it names the stale server, and
  `build_or_update_index` leaves the file byte-identical — asserted on the file, not on the message.
- A store written under an *older* schema: the existing auto-heal path still rebuilds, unchanged.
- `get_index_status` returns a payload in both directions and raises in neither; the payload names both
  versions and the action.
- The chosen query-tool policy is implemented and has a test.
- No doc tells a reader to rebuild in the newer-index direction.
- `pytest`, `ruff`, `mypy` green.

## References
`code_atlas/store.py:163-165` (`SchemaVersionError`), `:249-261` (the direction-blind check and its
message), `:24` (`SCHEMA_VERSION`); `code_atlas/tools/build_or_update_index.py:41-46` (the
unconditional catch), `:73-76` (`_unlink_index`); `code_atlas/tools/get_index_status.py:47` (the
unguarded open), `:53-70` (`_unbuilt`, the shape to follow); `code_atlas/indexer.py:133-137` (the
contract-version check that degrades instead of raising — prior art).
Origin: field session round 2, 2026-08-07, immediately after the contract v3 / schema v3 merge
([049](049_call-site-argument-selectivity.md), PR #57). Tier rule: R5.2. No-migrations rule: R7.4.
