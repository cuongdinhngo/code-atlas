---
id: 226
slug: an-imported-type-name-is-never-qualified-so-no-cross-file-base-or-annotation-links
title: '`find_implementations` on a repo''s own `JobQueue` interface answers zero while six classes subclass it — `resolve_name` consults only same-file `declared` and falls back to the bare token, so 84 of 97 `EXTENDS` and 1,233 of 1,313 `REFERENCES` never link, though `note_import_alias` already sees the module and `import_target_raw` already resolves it to a path in the same pass'
phase: 1.5b
milestone: Agent-trust
status: done
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
  (`<local Python sample>`, master @ `2f996ca`) and is not reproducible from
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
<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 226 · **work_doc_mode:** embed · **Current phase:** 5 finalise — complete on disk; PR pending
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · **Type:** bug
- Run: `/mango:autorun 226` with `--no-reviewer`; challenger ON.
- Branch: `feat/226-an-imported-type-name-is-never-qualified-so-no-cross-file-base-or-annotation-links`
- Contract: `.mango/run-contract-226.txt` · RECONCILE t0: 6 declared | 4 re-run | 0 holding | 4 BROKEN | 2 UNBOUND
- Handover: push feature branch + open PR only (never merge).
- Worktree: `/home/you/.cursor/worktrees/autorun226-535892a6/code-atlas-9e4914c8946d`

## Phase 0 — refine

`PREMISE: 10 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 3 by handle | 1 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions. Ticket locks the mechanism (separate marker vs binding maps; `resolve_name` after `declared`; reuse `import_target_raw`/`module_name`; in-repo only). Acceptance bar pinned by AC1–AC5. E1/E2 name the out-of-scope edges.

**PREMISE detail.** Checked and present: `adapters/python/src/parse.py` (`note_import_alias`, `resolve_name`, `module_name`), `adapters/python/src/imports.py` (`import_target_raw`, `resolve_import`), `code_atlas/contract.py` (`FQN_EDGE_KINDS`, `CONTRACT_VERSION`), `code_atlas/tools/find_implementations.py`, `code_atlas/store.py` (`SCHEMA_VERSION`). **Ambiguous (not blocking):** private field repos named in Why/E1 (outside this checkout).

**INPUT KIND:** ticket (not epic).

**Recalled claims — advisory.**

| # | Claim | Type | Matched by | Relevant here? |
|---|---|---|---|---|
| 1 | `prove-the-guard-fails` | 2 | handle | **Yes** — AC1 R6.5 bare target before |
| 2 | `prefer-the-provable-fix` | 2 | handle | **Yes** — E1 fixture-only measurement |
| 3 | `reproduce-the-payload-not-the-story` | 2 | handle | **Yes** — `find_implementations` consumer |
| 4 | adapters area (scanner / same-file map) | 5 | area | Surfaced |
| — | `embed-mode-leaks-the-working-doc-into-the-diff` | 3 | — | **retired skipped** |

**Exposure-checker:** skipped with refine (`skip: yes`).

## Phase 1 — analysis

`PREMISE: 10 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 3 by handle | 1 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Why this exists, Scope, Acceptance criteria, Exclusions) | 4 decomposed | ROWS: C=4 R=4 G=1 AC=5`
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/N touched files under UI paths (python adapter + tests/docs)`
`BASELINE: green`
`SCOPE: M`
`TIER: full`
`RULE SECTIONS: 12 applicable — 11 by change-type | 1 by recalled handle — R1.4 (change-type) ✅ adapters parse only · R2.1 (change-type) ✅ import resolution per language filesystem rules · R2.2 (change-type) ✅ no repo/framework names · R3.1 (change-type) ✅ CONTRACT_VERSION untouched · R3.3 (change-type) ✅ bare edges; core still links · R4.2 (change-type) ✅ AC5 classification byte-stable · R5.2 (change-type) ✅ AC3 external stays unlinked · R6.1 (change-type) ✅ proving tests · R6.5 (recalled handle) ✅ AC1 red-before recorded · R6.9 (change-type) ✅ find_implementations consumer · R7.1 (change-type) ✅ split maps + resolve_name only · R7.2 (change-type) ✅ ledger row`

### BASELINE

`.venv/bin/python -m pytest -q --tb=no` on untouched `origin/main` at **61d992a** (after php vendor + linked adapter node_modules in worktree):

```
3049 passed in 293.25s (0:04:53)
```

`Ran at dd0471af6074724f6cc67709818ef51d6414dada`. Green. No baseline exclusions.

### Clarifications (all self-resolved; j = 0)

| # | Question | Resolution | Citation |
|---|---|---|---|
| Q1 | One map overloaded vs two maps? | **Separate** `import_markers` (Protocol/ABC/Enum) and `import_bindings` (filesystem-resolved qnames) | ticket Scope 1; AC5 |
| Q2 | Measure recoverable edges on private repos? | **Fixture only** — E1; method documented | ticket E1 |
| Q3 | Relative imports? | **Same path** via `resolve_import(..., level=)` already in `imports.py` | ticket Scope 3 |

### Requirements matrix

| ID | Source | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|
| G1 | Why | Cross-file base/annotation/decorator links so tools answer non-zero | `resolve_name` same-file only today | closed |
| R1 | Scope 1 | Keep module on import map; split classification from link targets | `note_import_alias` drops module for ordinary imports | open |
| R2 | Scope 2 | `resolve_name` consults import map after `declared` | parse.py:348-353 | open |
| R3 | Scope 3 | Reuse `import_target_raw`/`resolve_import` + `module_name` | already imported | open |
| R4 | Scope 4 | Only filesystem-resolved in-repo names | AC3 | open |
| C1 | Constraints | R5.2 — external stays unlinked | AC3 | closed |
| C2 | Constraints | R3 — no CONTRACT/SCHEMA bump | AC4 | closed |
| C3 | Constraints | R4.2 — classification unchanged | AC5 | closed |
| C4 | Constraints | R6.5 — prove bare before | AC1 | closed |
| AC1 | AC | Before: three edges `target_qname` NULL | red proof on 61d992a | open |
| AC2 | AC | After: three link RESOLVED | proving test | open |
| AC3 | AC | External bare + unlinked | proving test | open |
| AC4 | AC | Versions unchanged; conformance green | assert + suite | open |
| AC5 | AC | Classification untouched (fixtures + field shape) | proving + E1 gap | open |
| E1 | Exclusions | Private-repo 893 count not in-repo | coverage-gap | closed |
| E2 | Exclusions | `import X.Y` attr + `import *` out | coverage-gap | closed |

### AC validation

| AC | Ticket value | Independently derived | Match? | Falsifiable? |
|---|---|---|---|---|
| AC1 | three edges unlinked before | reproduced: EXTENDS/REFERENCES → bare `Entity`/`audit` | Y | measurable |
| AC2 | three link RESOLVED | FQN_EDGE_KINDS + unique Class qname | Y | measurable |
| AC3 | external bare unlinked | `resolve_import` → None | Y | measurable |
| AC4 | versions unchanged | CONTRACT_VERSION=9 SCHEMA_VERSION=5 | Y | measurable |
| AC5 | classification + field 11/11/3 | fixtures measurable; field counts → E1 gap | Y / manual-check exclusion for field census | fixtures + E1 |

### Root cause

`note_import_alias` stored the bare imported leaf for ordinary `from X import Y`, and `resolve_name` never consulted imports — only same-file `declared`. Cross-file bases/annotations therefore emitted unqualified `target_raw`, and EXTENDS has no bare-name fallback, so tools returned confident zeros.

## Phase 2 — design

### Approach

Split the overloaded import map: `import_markers` keeps Protocol/ABC/Enum classification; `import_bindings` records `module_name(resolved_path).Imported` when `resolve_import` finds a file under the tree (including relative `level`). `resolve_name` returns declared → binding → bare token. No contract/schema bump; no other adapter.

### Rejected alternatives

| Alternative | Why rejected |
|---|---|
| Overload one map with module-qualified names for markers too | Ticket Scope 1 / AC5 — interface detection would break |
| Core bare-name fallback for EXTENDS | Ticket Not-in-scope / 204 owns predicate; would be HEURISTIC not RESOLVED |
| jedi / type-checker resolution | YAGNI; filesystem arithmetic already exists in `imports.py` |

### Assumptions

| Assumption | Tag |
|---|---|
| `resolve_import` + `module_name` already correct for absolute and relative | verified — used by IMPORTS edges today |
| Unique in-repo Class qname links at RESOLVED via existing resolver | verified — FQN_EDGE_KINDS includes EXTENDS/REFERENCES |

### Change list

| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | Split markers/bindings; `resolve_name` consults bindings | `adapters/python/src/parse.py` | all Python EXTENDS/REFERENCES/CALLS Name targets; protocol/enum classification | R1–R4,C1–C4,AC2–AC5,G1 | 12/12 |
| 2 | Exclude proving package from R6.2 inventory collision | `tests/contract/adapter_registry.py` | python excluded_fixtures set only | AC4 inventory hygiene | 1/1 |
| 3 | Proving fixtures + tests AC1–AC5 + find_implementations | `tests/fixtures/python/cross_file_import/` + `tests/test_python_cross_file_import_links.py` | existing python conformance cases untouched | AC1–AC5,E1 | 6/6 |
| 4 | Docs/bookkeeping: BACKLOG, TOKEN_LEDGER, task status | `docs/` | none beyond bookkeeping | R7.2,E2 | 2/2 |

### HANDLES (recalled type-2 — command + result)

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**H1 `prove-the-guard-fails`** — traced.

```
Ran at dd0471af6074724f6cc67709818ef51d6414dada
$ adapters/python/index.py --file …/user.py | filter EXTENDS/REFERENCES
EXTENDS …User -> Entity
REFERENCES …User::save -> Entity
REFERENCES …Decorated -> marker
```

Folded: AC1 red-before recorded; AC2 asserts RESOLVED after.

**H2 `prefer-the-provable-fix`** — traced.

```
Ran at dd0471af6074724f6cc67709818ef51d6414dada
$ rg -n 'E1|cross_repo_samples|private' docs/tasks/226_*.md | head -5
```

Folded: fixture-only proving; E1 exclusion for private corpus.

**H3 `reproduce-the-payload-not-the-story`** — traced.

```
Ran at dd0471af6074724f6cc67709818ef51d6414dada
$ rg -n 'find_implementations|EXTENDS' code_atlas/tools/find_implementations.py | head -8
46:        ``EXTENDS``/``IMPLEMENTS`` are resolver-linked, so empty here is a genuine zero
```

Folded: `test_find_implementations_sees_cross_file_subclass` asserts consumer payload.

### Coverage-gap exclusions

| Item | Risk tier | Why deferred | Follow-up | expiry | seen |
|---|---|---|---|---|---|
| Private-repo recoverable-edge census (893 / field AC5 11/11/3) | medium | E1 — local private checkouts; not in this repo; `cross_repo_samples` has no Python pin | Add a Python sample to `cross_repo_samples.json` (shared with 227) and re-measure | `when cross_repo_samples.json pins a Python sample repo` | (first) |
| `import X.Y` attribute use + `from X import *` | low | E2 — needs module symbol table / attribute fold; out of ticket Scope | Follow-up ticket after 227 local type table | `when a ticket owns star-import or import-then-attr qualification` | (first) |

`EXCLUSIONS: 2 recorded | 2 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match |
|---|---|---|---|---|
| AC1 | integration | red-before transcript + after RESOLVED | authored | ✅ |
| AC2 | integration | store edges RESOLVED | authored | ✅ |
| AC3 | integration | ExternalBase unlinked | authored | ✅ |
| AC4 | integration | version asserts + python conformance | n/a | ✅ |
| AC5 | integration | typed.py classification; field census → E1 | authored + gap | ✅ |

### Proving test

```
.venv/bin/python -m pytest tests/test_python_cross_file_import_links.py -q
```

### Rollback + porting

- **Rollback:** `git revert` / close PR unmerged.
- **Porting:** single repo (`app`).

## Phase 3 — execute

Branch `feat/226-an-imported-type-name-is-never-qualified-so-no-cross-file-base-or-annotation-links` from `origin/main` @ `61d992a`.

### Implemented (⊆ approved change list)

| # | Change | Done |
|---|---|---|
| 1 | Split markers/bindings; `resolve_name` consults bindings | ✅ `adapters/python/src/parse.py` |
| 2 | Exclude proving package from R6.2 collision | ✅ `adapter_registry.py` |
| 3 | Proving fixtures + tests AC1–AC5 + find_implementations | ✅ |
| 4 | BACKLOG / TOKEN_LEDGER / task status | ✅ |

No design deviations. AC1 negative control added after challenger partial on docstring-only red-before.

### Proving test evidence

```
Ran at dd0471af6074724f6cc67709818ef51d6414dada
$ .venv/bin/python -m pytest tests/test_python_cross_file_import_links.py -q
.......                                                                  [100%]
7 passed
```

### Verification sweep

- python conformance (`test_adapter_conformance.py -k python`) — green
- ruff/mypy on touched modules — run at finalise
- Delta-green: docker-test / full pytest at finalise

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)`. `CHALLENGER: ON`.

### Challenger (ticket-blind — raw ticket above separator + `git diff main...HEAD` only)

Independence: procedural (working-doc portion withheld). Rebuilt requirements from Scope + AC1–AC5 + E1/E2.

| Req | Verdict | Evidence |
|---|---|---|
| R1 separate marker vs binding maps | **met** | `parse.py` `import_markers` / `import_bindings` |
| R2 `resolve_name` after declared | **met** | `resolve_name` consults `import_bindings` |
| R3 reuse `resolve_import` + `module_name` | **met** | `note_import_alias` calls `resolve_import` |
| R4 in-repo only | **met** | AC3 `ExternalBase` unlinked |
| AC1 red-before | **met** | `test_ac1_unresolved_import_keeps_bare_targets` (neg control) + in-session 61d992a transcript |
| AC2 three link RESOLVED | **met** | `test_imported_base_annotation_decorator_link_resolved` |
| AC3 external bare | **met** | `test_external_import_stays_unlinked` |
| AC4 versions + conformance | **met** | `test_versions_unchanged` + python conformance green |
| AC5 classification | **met** | `test_classification_markers_untouched`; field census → E1 |
| E1 private corpus | **met** | fixture-only; exclusion recorded |
| E2 star/attr import | **met** | not implemented |
| Consumer find_implementations | **met** | `test_find_implementations_sees_cross_file_subclass` |

**Challenger verdict: PASS** — 12 met / 0 not-met / 0 can't-tell (after AC1 negative-control landing).

Round 1 had AC1 as **partial** (docstring-only red-before); accepted and fixed in-branch with `test_ac1_unresolved_import_keeps_bare_targets`.

### Scope reconcile

- File axis: `diff ⊆` approved list ✅
- Behaviour axis: approach matches ✅

`Reviewed at f00ffb61cf01e424189814eef0fb8b8fcaf321e6`

## Phase 5 — finalise

Durable lesson: none beyond reinforcing `prove-the-guard-fails` (already in LESSONS) — AC1 needed an automated negative control, not only a transcript. No new lesson entry (seen-bump deferred; promotion not proposed this run).

`LEDGER TOTAL: unmeasured · top cost driver: main-loop (host surfaces no usage block; challenger not separately metered this run)`
`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

Outward actions authorised by handover: (1) push feature branch (2) open PR. Merge NOT authorised.
