---
id: 227
slug: python-has-no-local-type-table-so-every-member-call-is-heuristic
title: 'Python is the only shipped adapter with no local type table — PHP has `TypeTable.php`/`MemberTypes.php` and TS has `types.js`, so a Python `obj.method()` stays a bare name at `HEURISTIC`: 2,899 of 4,779 `CALLS` (60.7%) on a 162-file FastAPI repo, and every `find_callers` hit came back `HEURISTIC` — while the annotation that names the receiver''s class sits in the signature the parser already walked'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [137, 153, 020, 226]
---

## Why this exists

137 built a local type table for PHP (`adapters/php/src/TypeTable.php`, `MemberTypes.php`) so a
member call `$obj->method()` resolves to `<Class>::method` instead of a bare, `HEURISTIC` name. 153
ported it to TypeScript (`adapters/typescript/src/types.js`) and measured the result on pinned `ky`:
**HEURISTIC 57.0% → 54.1%, 225 member calls promoted** (`TOKEN_LEDGER.md`, row 153). 020 and 217
shipped the Python adapter without one, and no ticket has said so out loud.

A field build of a 162-file FastAPI repo measures the cost: **2,899 of 4,779 `CALLS` are
`HEURISTIC` (60.7%)**, and both `find_callers` probes run against that index returned
`HEURISTIC`-only rows — correct answers the payload cannot claim to have resolved.

**Python is the cheapest of the three to promote, not the hardest.** PHP had to lean on `new X` and
docblocks; TS needed `getJSDocType` to cover `.js` at all (154). Python states the receiver's type
in the language itself, in the two places a service object comes from:

```python
def __init__(self, repo: EvidenceRepository) -> None:   # parameter annotation
    self._repo: EvidenceRepository = repo               # PEP 526 attribute annotation
```

Both are `ast` nodes the adapter already walks — `emit_function_annotation_refs` reads exactly these
annotations today (`parse.py:454-469`) and emits a `REFERENCES` edge from them. The type is being
read and then dropped for the purpose of resolving the calls on that receiver.

**The capability flag is advertised-only, so it is not the fix.** `semantic_types` is in
`KNOWN_CAPABILITIES` (`contract.py:185`) and validated as a shape (`contract.py:305-312`), but
nothing in the core consumes it — the declaration is documentation, and the promotion has to be real
before the flag means anything. Worth recording while here: **PHP announces
`'capabilities' => new stdClass()`** (`adapters/php/index.php:28`) although it has had the table
since 137, so the flag already disagrees with two of the three adapters.

## Scope

1. **A `TypeTable` for the Python adapter**, mirroring `types.js` — stdlib `ast` only, no `jedi`, no
   third-party dependency (`adapters/python/README.md`). Bindings from: parameter annotations,
   `AnnAssign` (class body and `self._x: T`), and `x = Foo()`.
2. **Flow-forgetful and file-at-a-time**, the shape 137/153 settled: fresh bindings per
   function/method, inherited by nested `def`s, and a reassignment from an unknown source *re-opens*
   the name rather than keeping a stale class.
3. **`self` / `cls` bind to the enclosing class** — the single most common receiver in this repo
   shape, and free once the table exists.
4. **A member call with a bound receiver emits `CALLS` to `<Class>::method` at `RESOLVED`**; an
   unbound receiver keeps today's bare `HEURISTIC` edge, unchanged.
5. **Announce `capabilities: {semantic_types: true}`** once the promotion is real. Already a
   `KNOWN_CAPABILITY`, so **no `CONTRACT_VERSION` bump** (R3).
6. **Add a pinned Python sample to `cross_repo_samples.json`** so the before/after is re-runnable in
   the open — the manifest pins PHP and TS only, and `edge_health_report.py` is already
   language-aware with `--only` (153 made it so). Shared with 226's E1.

**Not in scope:** cross-file class receivers beyond what 226's import map supplies — a bound name
whose class lives in another file needs that ticket's FQN, and same-file classes work without it.

## Acceptance criteria

- **AC1 (R6.5 — prove the guard fails first).** A fixture where an annotated receiver calls a method
  asserts today's bare `HEURISTIC` edge before the change, and the `RESOLVED` `<Class>::method` edge
  after. Without the red row the ticket cannot show it changed anything.
- **AC2** The promotion is **measured**, not asserted: `edge_health_report.py` before/after on the
  new Python pin, recorded as a HEURISTIC-share delta the way 153 recorded 57.0% → 54.1%.
- **AC3** Forgetfulness is proven, not claimed: a test where the receiver is reassigned from an
  unknown call asserts the later edge falls back to `HEURISTIC` rather than resolving to the class
  the name used to hold. A stale `RESOLVED` is worse than an honest `HEURISTIC` (R5.2).
- **AC4** Zero language branches in the core (R1.1) and `CONTRACT_VERSION` unchanged — this is an
  adapter emitting a better `target_qname`, nothing more.
- **AC5** Identical input yields byte-identical rows (R4.2), and every existing Python adapter
  fixture is unchanged except where a call is legitimately promoted.

## Exclusions

- **E1** No type *inference*. Only bindings the language writes down — an annotation, a constructor
  call. A receiver whose type comes from a function's return type (the fluent-chain residual 153
  recorded on TS) is the same file-at-a-time limit here, and is not a gap this ticket closes.
- **E2** The 60.7% figure is from a **local, private checkout**
  (`~/WORKSPACE/PROJECTS/1-REFERENCES/ai-hackathon`, master @ `2f996ca`, 162 files, 8,910 edges) and
  is not reproducible from this repo — which is precisely why scope 6 adds a public pin. Until that
  pin lands, quote it as a field observation with its host named, never as a repo number.

## Notes

**Ordering against [226](226_an-imported-type-name-is-never-qualified-so-no-cross-file-base-or-annotation-links.md).**
226 first. It links the type *names* — bases, annotations, decorators — and hands this ticket the
FQN for a receiver whose class is declared in another file. Run in the other order and the type
table resolves only same-file receivers, which on a layered repo (`services/` calling
`repositories/`) is the minority of exactly the calls worth promoting.
