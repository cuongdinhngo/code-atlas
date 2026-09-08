---
id: 227
slug: python-has-no-local-type-table-so-every-member-call-is-heuristic
title: 'Python is the only shipped adapter with no local type table — PHP has `TypeTable.php`/`MemberTypes.php` and TS has `types.js`, so a Python `obj.method()` stays a bare name at `HEURISTIC`: 2,899 of 4,779 `CALLS` (60.7%) on a 162-file FastAPI repo, and every `find_callers` hit came back `HEURISTIC` — while the annotation that names the receiver''s class sits in the signature the parser already walked'
phase: 1.5b
milestone: Agent-trust
status: done
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
<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 227 · **work_doc_mode:** embed · **Current phase:** 4 review → finalise
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · **Type:** enhancement
- Run: `/mango:autorun 227` with `--no-reviewer`; challenger ON
- Branch: `feat/227-python-has-no-local-type-table-so-every-member-call-is-heuristic`
- Contract: `.mango/run-contract-227.txt` · RECONCILE t0: 6 declared | 4 re-run | 0 holding | 4 BROKEN | 2 UNBOUND
- Handover: push feature branch + open PR only (never merge)
- Worktree: `/home/you/.cursor/worktrees/autorun227-fdb07743/code-atlas-9e4914c8946d`
- Depends on 226 (still todo on origin/main): same-file receivers only; cross-file FQN deferred to 226

## Phase 0 — refine

`PREMISE: 9 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions. Ticket pins AC1–AC5, E1–E2, mirror of 137/153. **INPUT KIND:** ticket.

**PREMISE.** Present: TypeTable.php, MemberTypes.php, types.js, adapters/python/README.md, parse.py, contract.py, adapters/php/index.php, edge_health_report.py, cross_repo_samples.json. Ambiguous (not blocking): private FastAPI field path (E2).

**Recalled (advisory):** `prove-the-guard-fails` (R6.5).

## Phase 1 — analysis

`PREMISE: 9 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists, Scope, Acceptance criteria, Exclusions, Notes) | 5 decomposed | ROWS: C=3 R=6 G=1 AC=5`
`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/N touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`
`RULE SECTIONS: 7 applicable — 6 by change-type | 1 by recalled handle — R1.1 (change-type) ✅ adapter-only · R2 (change-type) ✅ language-spec bindings · R3 (change-type) ✅ no CONTRACT_VERSION bump · R4.2 (change-type) ✅ deterministic · R5.2 (change-type) ✅ forgetful reopen · R6.5 (recalled handle) ✅ red-first fixture · R7.2 (change-type) ✅ ledger`

### BASELINE

```
Ran at 36aef1b6a6231e95c3085eab34c37c13a1ee4ab6
$ PYTHONPATH=. pytest tests/test_python_adapter_nodes.py tests/contract/test_adapter_conformance.py -q --tb=no -k python
```

No baseline exclusions. DoD is delta-green vs origin/main.

### Clarifications (j = 0)

| # | Question | Resolution | Citation |
|---|---|---|---|
| Q1 | Public Python pin which repo? | **pallets/flask** @ `d318b68` | Scope 6; 233 candidates |
| Q2 | `Foo()` vs any call — how bind without `new`? | Only when callee ∈ same-file Class/Enum/Interface set | R5.2; TS uses `new` |

### Requirements matrix

| ID | Source | Interpretation | Status |
|---|---|---|---|
| G1 | Why | Python member calls stay HEURISTIC without a local type table | closed |
| R1 | Scope 1 | TypeTable module (stdlib ast) | closed |
| R2 | Scope 2 | Flow-forgetful, file-at-a-time | closed |
| R3 | Scope 3 | self/cls + self props | closed |
| R4 | Scope 4 | Bound receiver → RESOLVED Class::method | closed |
| R5 | Scope 5 | Announce semantic_types | closed |
| R6 | Scope 6 | Pin Python sample in cross_repo_samples.json | closed |
| C1 | Notes/deps | Same-file without 226 | closed |
| C2 | E1 | No inference / return-type chains | closed |
| C3 | E2 | Field 60.7% is private observation | closed |
| AC1 | AC | Red-first HEURISTIC→RESOLVED fixture | closed |
| AC2 | AC | Measured HEURISTIC delta on pin | closed |
| AC3 | AC | Forgetfulness proven | closed |
| AC4 | AC | R1.1 + CONTRACT_VERSION unchanged | closed |
| AC5 | AC | Fixtures unchanged except legitimate promotions | closed |

### AC validation

| AC | Ticket | Derived | Match |
|---|---|---|---|
| AC1 | red then green | registry was HEURISTIC; store test RESOLVED after | ✅ |
| AC2 | measured delta | flask CALLS HEURISTIC 83.9%→82.2% (5908→5709, −199) | ✅ |
| AC3 | forgetful | test_reassignment_from_unknown_reopens_receiver | ✅ |
| AC4 | no core / no bump | CONTRACT_VERSION=9; adapter-only | ✅ |
| AC5 | fixtures | call_method promoted; others unchanged | ✅ |

## Phase 2 — design

### Approach

1. `adapters/python/src/types.py` mirroring types.js.
2. Thread locals_/self_props through parse.py; promote member CALLS when bound.
3. Announce semantic_types; pin flask; wire _ADAPTERS + workflow CA_PYTHON_CMD.
4. Proving tests + forgetfulness + conformance registry update.

### Rejected alternatives

| Alternative | Why rejected |
|---|---|
| jedi / type checker | Ticket forbids; R2 |
| Bind every Name() call as constructor | Breaks forgetfulness |
| Wait for 226 | Ticket allows same-file now |

### Change list

| # | Change | Paths | Ph2 covered by | k/N |
|---|---|---|---|---|
| 1 | types.py | adapters/python/src/types.py | R1,R2,AC3 | 3/3 |
| 2 | Wire parse walk | adapters/python/src/parse.py | R2–R4,AC1,AC3,AC5 | 6/6 |
| 3 | Announce capability | adapters/python/index.py | R5 | 1/1 |
| 4 | Tests + registry | tests/…, adapter_registry.py | AC1,AC3,AC5 | 3/3 |
| 5 | flask pin + harness | cross_repo_*, workflow | R6,AC2 | 2/2 |
| 6 | Docs + bookkeeping | README, BACKLOG, TOKEN_LEDGER, task | R7.2 | 1/1 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**H1 `prove-the-guard-fails`** — traced: pre-change HEURISTIC bare hook; post RESOLVED Child::hook.

### Proving test

`pytest tests/test_python_semantic_types.py tests/contract/test_adapter_conformance.py -k python -q`

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`
`VERIFICATION PLAN: no ❌`

Coverage-gap: AC2 on public flask (not private FastAPI E2); expiry: when 233 lands more pins.

## Phase 3 — execute

Implemented #1–#6.

### Measurement (AC2)

flask @ d318b683471101618febed18996405ad26462110: CALLS HEURISTIC **83.9% → 82.2%** (5908 → 5709, **−199**).

### Verification sweep

```
Ran at 36aef1b6a6231e95c3085eab34c37c13a1ee4ab6
$ PYTHONPATH=. pytest tests/test_python_semantic_types.py tests/test_cross_repo_workflow_installs_every_adapter.py tests/contract/test_adapter_conformance.py -k python -q
focused suites green
```

`diff ⊆ approved list`. CONTRACT_VERSION=9.

## Phase 4 — review

`Reviewed at 36aef1b6a6231e95c3085eab34c37c13a1ee4ab6`
Reviewer: **waived** (`--no-reviewer`). Challenger: ON (ticket-blind).

### Challenger (ticket-blind)

Reconstructed from raw ticket + diff only: TypeTable; promote annotated/Foo() member calls; forgetful; announce semantic_types; pin+measure; no contract bump.

Verdict: **requirements MET**. Partial only: cross-file awaits 226 (ticket Not in scope). No blocking findings.

`GATE 4: clean (challenger LGTM; reviewer waived — disclosed)`

