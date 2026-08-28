---
id: 188
slug: imports-edges-are-never-linked-so-no-tool-can-walk-a-module-graph
title: '`IMPORTS` is never linked, so no tool can answer "which files import this one" for a module language — the TS adapter resolves the specifier to a real repo path and the core discards it'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [186, 019, 155]
---

## Why this exists

Found while proving **186**'s `try_instead` route. 186 wanted to route `include_graph` on a TS file to
a tool that *could* list its importers, and there is none — so 186 correctly emits a hint and no
route (R5.4 clause c). This ticket is the reason there is none.

Measured on a TS-indexed fixture graph:

```
IMPORTS rows: ('src/app.ts',      'src/models.ts',  target_qname=None, RESOLVED)
              ('src/barrel.ts',   'src/models.ts',  target_qname=None, RESOLVED)
              ('src/module_cjs.ts','src/cjs_service.js', target_qname=None, RESOLVED)
resolved IMPORTS targets: []                      # every single one is unlinked
```

`target_raw` is already a **repo-relative path that exists in `files`** — 155 taught the adapter to
resolve specifiers through `tsconfig` `baseUrl`/`paths`, and it works. The core then throws the
answer away, because nothing links `IMPORTS`:

```python
# code_atlas/resolver.py:115-132 — a path-linking branch for INCLUDES, and only INCLUDES
if kind == "INCLUDES":
    includes.append(edge)
elif kind in contract.FQN_EDGE_KINDS:      # FQN_EDGE_KINDS excludes IMPORTS (contract.py:66)
    symbols.append(edge)
```

So `IMPORTS` falls through both arms. Consequences, all measured:

- `include_graph` cannot see module dependencies at all (that is 186's confident zero).
- `find_references` on a file subject reaches only its **unlinked** arm — `relationship_not_modelled`,
  `total_count: 0`, no rows. It knows something exists and cannot name it.
- `impact` / `reachable_from` / `find_orphans` walk resolver-linked edges, so a TS module graph
  contributes **nothing** to blast radius or reachability. Every TS file looks like an island.
- 183's per-language tier mix will report TS `IMPORTS` as RESOLVED-but-unlinked, which is honest and
  useless: the tier says the adapter was sure, the link says nobody used it.

## Why it is not a one-line fix

Adding `IMPORTS` to the `INCLUDES` branch would path-resolve **PHP** `IMPORTS` too, and there
`target_raw` is a class FQN (`App\Contracts\Jsonable`), not a path — `_relative_to` would produce
nonsense and `nodes_by_qualified_names(..., kind="File")` would miss, quietly. **One edge kind is
carrying two meanings across languages**, which is the contract question, not a resolver tweak:

- either `IMPORTS` is split in the contract (a module dependency vs a symbol import) — a
  `contract_version` bump and a conformance-suite change (R3), or
- the link is attempted **both** ways and the first hit wins, with the tier recording which — cheaper,
  no bump, and it makes the resolver's behaviour depend on the shape of a string, which R5.2 dislikes.

Design must choose and record. This is exactly R1.5's substitutability question arriving late.

## Scope

1. A module-language `IMPORTS` edge whose `target_raw` names an indexed file gets `target_qname` set,
   at a tier that records how it was linked.
2. PHP's symbol-shaped `IMPORTS` is **unchanged** — no false path links, pinned by a test that would
   fail if a class FQN were path-resolved.
3. Design records the vocabulary decision (split the kind vs try both links) with the R3 impact
   stated either way.
4. `include_graph` and `find_references` are re-measured afterwards, and **186's hint-and-no-route is
   revisited**: once a tool can answer, R5.4 clause (c) says name it.

### Explicitly not in scope

- Teaching `include_graph` to read `IMPORTS` (069's territory, and 186 explicitly excluded it).
- Any adapter change — the adapter already emits the resolved path.
- `export *`, which cannot enumerate names file-at-a-time (155's recorded limit) and stays a bare
  module dependency.

## Constraints

- **R1.1** — no language branch. The discriminator must be the *shape of the edge*, never its
  language.
- **R3** — if the contract vocabulary changes, bump and update the conformance suite.
- **R4.2** — deterministic; a two-way link attempt must have a stated precedence.
- **061** — a PHP-only index is byte-identical.
- **Cost** — one bounded batch per resolve pass, like the `INCLUDES` branch it sits beside.

## Acceptance criteria

1. A TS `IMPORTS` edge naming an indexed file is linked — pinned by a test failing on today's code
   (`target_qname is None` today).
2. A PHP `IMPORTS` edge naming a class FQN is **not** path-linked, and its existing resolution is
   unchanged — pinned.
3. `include_graph`/`find_references` behaviour after the change is measured and recorded; 186's
   route decision is revisited with the new measurement.
4. `impact` over a TS seed crosses at least one module boundary — pinned, since "every TS file is an
   island" is the user-visible cost.
5. Determinism (R4.2), no language branch (R1.1), contract impact decided and recorded (R3).

## References
Found by [186](186_a-zero-answer-cannot-say-the-relation-is-unmodelled-for-this-language.md) while
verifying its `try_instead` route. `code_atlas/resolver.py:115-132` (the INCLUDES-only path branch);
`code_atlas/contract.py:66` (`FQN_EDGE_KINDS`, no `IMPORTS`); `:78`
(`UNMODELLED_REFERENCE_KINDS`). Related: [019](019_typescript-adapter.md),
[155](155_ts-module-shapes.md) (the adapter resolution this would finally consume),
[183](183_edge-health-has-no-per-language-breakdown.md).
