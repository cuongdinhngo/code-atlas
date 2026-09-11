---
id: 243
slug: the-capability-predicate-221-relies-on-is-attached-at-verbose-only
title: '`cross_language` — the census 221 and 238 use to decide whether a zero is honest — rides inside `edge_health_by_language`, which is attached at `verbose` only, so the agent that calls `get_index_status` at its default `standard` cannot read the one number that says whether the crossing in its repo is modelled at all'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [221, 238, 204, 183]
---

## Why this exists (field retro round 17)

204 built the `cross_language` row precisely so a cross-language gap would be *visible*: a link to a
callee that cannot be called counts as healthy in 183's per-language rows, and this is the row that
can see it. 221 then made it a predicate — an empty `find_callers` on a subject whose real callers
are in another language answers `relation_unmodelled` instead of `no_matches` — and 238 extended the
predicate to the confident non-zero.

All three deliver **in the response**. A field in a response cannot reach an agent that has decided
not to call, and that decision happens before any call.

The one channel that reaches the agent first is `get_index_status`, which the round-17 session called
as **tool call #1** and pasted verbatim into its retro. It called it at `standard` — the default.
`edge_health_by_language`, which carries `cross_language`, is attached only inside the `verbose`
payload (`code_atlas/tools/get_index_status.py:314`). `standard` carries `edge_health` (whole-graph),
`parse_failures`, `dirty_indexed_files` and `unconfigured_adapters` — no per-pair crossing census.

So the session read the status payload carefully enough to act on `unconfigured_adapters` and on
`server_stale_process`, and then wrote in the same retro that *"a third of the interesting behaviour
in this system is in stored procedures, and for that third the index is not in the conversation at
all"* — a conclusion the missing field is the direct answer to.

## Evidence — measured on the anchor monorepo, 2026-09-11

The census on an index holding 19,352 PHP, 3,012 SQL and 2,519 TypeScript files:

```
cross_language: {"by_tier":{"DYNAMIC":0,"HEURISTIC":0,"RESOLVED":0},"linked":0,"pairs":{},"unlinked":0}
```

Zero linked crossings, no pairs. PHP in this repo calls stored procedures constantly — one proc
measured for [242](242_params-is-stored-by-every-adapter-and-surfaced-by-one-tool-that-cannot-render-a-free-function.md)
has 0 linked inbound edges and **7 unlinked edges whose raw text names it**. That is exactly the
regression signal 204 wrote the row to carry, and it sat one `detail_level` above where the reader
was looking.

`_attach_edge_health_by_language` is also silent below two language buckets (:328-334) — correct for
a single-language graph, and not the cause here: this index has four.

## Scope

- **Attach the crossing census where the reader is.** Either move `cross_language` (not all of
  `edge_health_by_language`) to `standard`, or carry a bounded summary of it there. Decide between
  the two in the design and state the payload cost of each.
- **Consider `next_tool_suggestions` instead of, or as well as, a field.** `linked: 0` on a
  multi-language index is not a statistic, it is *an instruction about which questions this index
  cannot answer*. 061 built that list state-reactive for this shape of fact.
- **Keep 183's rows where they are.** The per-language tier mix is diagnostic and belongs at
  `verbose`; this ticket moves the one row that changes what a reader may conclude.
- **Out of scope:** improving cross-language linking itself (that is 222's line of work) and any
  change to 221/238's response-side predicates, which are correct.

## Constraints

- **061 / 223** — `standard` is the cheap path on the first call of every session; the added bytes
  must be measured and bounded. `pairs` grows with the square of the language count, so a summary
  may be the only admissible shape.
- **R5.6** — a pre-204 index has no stamp and must say it cannot tell, never `linked: 0`.
- **061** — omit when it adds nothing: a single-language index must stay byte-identical.
- **R4.2** — the value comes from the build stamp, not from a query-time scan; one scan per build is
  already 204's design and this ticket does not move it onto the answer path.

## Acceptance criteria

- `get_index_status` at `standard` on a multi-language index carries the crossing census (or its
  agreed summary), pinned by a test.
- A single-language index, and a pre-204 index, each stay unchanged — asserted.
- Added payload bytes at `standard` measured on the anchor-scale index and recorded here.
- A test asserts the `linked: 0` multi-language case produces the reader-facing signal chosen in
  design (field, suggestion, or both).

## References

Field retro round 17 (2026-09-11, maintainer-local) §0.1, §2.6, §3. Related:
[204](204_bare-name-resolution-has-no-language-predicate.md) (built the row),
[183](183_edge-health-has-no-per-language-breakdown.md) (per-language tier rows — the sibling that correctly stays at `verbose`),
[221](221_a-zero-is-modelled-when-every-caller-is-in-another-language.md) and
[238](238_the-honest-zero-predicate-is-gated-on-the-zero.md) (the two predicates that read it),
[061](061_payload-weight.md) (`next_tool_suggestions` and omit-when-empty),
[244](244_no-channel-announces-a-capability-change.md) (this ticket is the narrowest instance of
that one).

## Token usage

| Phase | Tokens |
|---|---|
| — | not yet started |
