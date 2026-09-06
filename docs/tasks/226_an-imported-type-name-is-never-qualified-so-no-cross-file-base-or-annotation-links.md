---
id: 226
slug: an-imported-type-name-is-never-qualified-so-no-cross-file-base-or-annotation-links
title: '`find_implementations` on a repo''s own `JobQueue` interface answers zero while six classes subclass it — `resolve_name` consults only same-file `declared` and falls back to the bare token, so 84 of 97 `EXTENDS` and 1,233 of 1,313 `REFERENCES` never link, though `note_import_alias` already sees the module and `import_target_raw` already resolves it to a path in the same pass'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [020, 217, 204, 155]
---

## Why this exists

A field build of a 162-file FastAPI/clean-architecture repo parsed perfectly — 162/162 `parsed_ok`,
1,934 nodes, and node recall exact against the source (909 `def` → 724 Function + 185 Method; 120
`class` → 106 Class + 11 Interface + 3 Enum). **The nodes are all there and the relationships
between them are not.** 3,468 of 8,910 edges link (38.9%), and the two edge kinds that carry
*"what is this a kind of"* are almost entirely dark:

| Kind | Total | Unlinked | Why |
|---|---|---|---|
| `EXTENDS` | 97 | 84 | base class imported from another file |
| `REFERENCES` | 1,313 | 1,233 | annotation / decorator naming an imported type |
| `IMPLEMENTS` | 11 | 11 | **correct** — every target is stdlib `ABC`/`Protocol`, which has no node |
| `IMPORTS` | 890 | 441 | **correct** — the unlinked rest are stdlib and third-party |

**One cause, and it is not ambiguity.** `resolve_name` (`parse.py:348-353`) looks a name up in
`declared` — same-file symbols only — and otherwise returns the token exactly as written. So
`class User(Entity)` emits `target_raw: "Entity"`, and the core's FQN resolver has nothing to match.
Of the unlinked edges, **893 name exactly one in-repo node by short name** (32 `EXTENDS`, 497
`REFERENCES`, 364 `CALLS`) against **one** ambiguous. There is no guess to make: the import
statement in the same file already says which module the name came from.

**The module is already read, twice, in the same pass.** `note_import_alias` (`parse.py:237-246`)
receives `module` and stores `import_aliases[local] = imported` — the bare leaf, the module argument
dropped on the floor for every name that is not a `Protocol`/`ABC`/`Enum` marker. And `emit_imports`
(`parse.py:489`) hands that same module to `import_target_raw`, which resolves it against the
filesystem through `imports.py` and produces the repo-relative path the `IMPORTS` edge links on. The
adapter therefore already computes, per file, the exact fact the type reference needs, and throws it
away before the reference is emitted.

**Why `CALLS` looked healthier than `EXTENDS`, and why that is misleading.** `find_callers` on this
index answers correctly — but every hit came back `HEURISTIC`, because the resolver's bare-name
fallback (`resolver.py:193`, `_link_by_bare_name`) rescues a call the adapter left unqualified. **`EXTENDS` has no such
fallback**, so an unqualified base is not a downgraded answer, it is a *zero*: `find_implementations`
on `…job_queue.JobQueue` returns `no_matches` while `ArqJobQueue` and five test stubs subclass it,
and `impact` on `…entities.user.User` returns only `User` itself against 88 references to it. The
fallback has been masking how little of the Python graph is actually resolved.

**Confirmed at 7.5x the scale, on a second private repo.** A 1,209-file AWS Lambda codebase
(1,173 Python files, 1,100 classes — node recall exact) reproduces the same shape and makes the
consequence unambiguous: `EXTENDS` is **835 of 859 unlinked (97.2 %)** and `REFERENCES` **3,346 of
3,497 (95.7 %)**. Every one of the 24 that *do* link is same-file, all in one `exceptions.py`. Of
the 835, **413 name exactly one in-repo class and 0 are ambiguous**; the other 422 are genuinely
external (`BaseModel`, `unittest.TestCase`, `Exception`, `str`, `Enum`) and must stay unlinked.

`find_implementations` on that index, against `grep` for the same base class:

| Subject | subclasses in source | tool answer |
|---|---:|---|
| `BaseTestCase` | 257 | **0**, `reason=no_matches` |
| `Entity` | 65 | **0**, `reason=no_matches` |
| `RdsRepository` | 37 | **0**, `reason=no_matches` |
| `DynamoDbTable` | 18 | **0**, `reason=no_matches` |
| `BaseOCRStrategy` | 12 | **0**, `reason=no_matches` |
| `CommonModel` | 10 | **0**, `reason=no_matches` |
| `BaseS3Bucket` | 5 | **0**, `reason=no_matches` |
| `CustomException` | 8 | 8 — the one whose subclasses share its file |

**The tool documents that zero as authoritative.** `find_implementations`' own docstring reads
*"`EXTENDS`/`IMPLEMENTS` are resolver-linked, so empty here is a genuine zero, never
`relationship_not_modelled` (065)"* (`find_implementations.py:46-47`). On Python that promise is
false, and 404 subclass relations are answered as confident zeros.

## Scope

1. **Keep the module on the import map.** `note_import_alias` records the module-qualified name for
   an ordinary `from X import Y`, instead of the bare leaf. The `Protocol`/`ABC`/`Enum` arm of that
   function is a *classification marker*, not a link target — the two uses have to be separated
   rather than one map overloaded, or interface detection breaks (AC5).
2. **`resolve_name` consults the import map after `declared`.** Same-file wins, then the import,
   then the bare token unchanged.
3. **Reuse the resolution that already runs.** The dotted module → repo-relative path step is
   `import_target_raw` + `imports.py`; the path → dotted qname step is `module_name`
   (`parse.py:58-65`). Relative imports (`from .base import Entity`) go through the same call with
   `level`, which `imports.py` already handles.
4. **Only for names the filesystem resolves inside the repo.** `from fastapi import APIRouter`
   resolves to no file under the tree, so the target stays the bare name and the edge stays
   unlinked — that unlinked edge is honest and must remain one (R5.2).

**Not in scope:** the resolver's bare-name fallback (204 owns the predicate, and this ticket
*reduces* what has to reach it); any other adapter; receiver typing for `obj.method()`, which is
[227](227_python-has-no-local-type-table-so-every-member-call-is-heuristic.md) and needs this
ticket's map for the cross-file half.

## Acceptance criteria

- **AC1 (R6.5 — prove the guard fails first).** A two-file fixture — `b.py` declares a class,
  `a.py` imports it as a base, as a parameter annotation and as a decorator — asserts
  `target_qname IS NULL` on all three against today's adapter, before the change.
- **AC2** After the change those three link, at `RESOLVED`. The tier does not move: the adapter read
  a declaration, it did not guess (R5.2).
- **AC3** A symbol imported from outside the repo keeps its bare `target_raw` and stays unlinked. No
  FQN is invented for a module the filesystem does not resolve.
- **AC4** `CONTRACT_VERSION` and `SCHEMA_VERSION` are **unchanged** and the conformance suite is
  green — `EXTENDS` and `REFERENCES` are already in `FQN_EDGE_KINDS` (`contract.py:73-75`), so this
  is existing vocabulary reaching targets that already exist (R3).
- **AC5** Classification is untouched: every existing adapter fixture stays byte-identical (R4.2),
  and on the field repo the 11 Interfaces, 11 `IMPLEMENTS` and 3 Enums are still exactly the 11
  `ABC`/`Protocol` classes and 3 `Enum` classes the source declares.

## Exclusions

- **E1** The 893-edge recoverable count is measured on a **local, private checkout**
  (`~/WORKSPACE/PROJECTS/1-REFERENCES/ai-hackathon`, master @ `2f996ca`) and is not reproducible from
  this repo. The committed artifact is AC1's fixture plus the method: build the index, then for each
  unlinked edge test whether `target_raw` matches exactly one `nodes.name` among
  `Class`/`Interface`/`Enum`/`Function`. `cross_repo_samples.json` pins **no Python sample** — the
  open re-run needs one added (shared with 227).
- **E2** `import X.Y` followed by attribute use (`X.Y.Thing`) and `from X import *` are out. The
  first needs the attribute path folded against the module map, the second needs the imported
  module's symbol table — both are more than carrying a module already in hand.

## Notes

**Why this is the first thing to fix in the Python adapter.** 020 and 217 bought the nodes and the
tier-2 vocabulary, and the field build shows both are exact. What an agent asks the graph is not
*what exists* but *what relates to what*, and on Python that half is currently answered by a
same-file lookup plus a `HEURISTIC` rescue in the store. Everything downstream — implementations,
blast radius, the class diagram, module fan-in — reads the edges this ticket links.
