---
id: 188
slug: imports-edges-are-never-linked-so-no-tool-can-walk-a-module-graph
title: '`IMPORTS` is never linked, so no tool can answer "which files import this one" for a module language — the TS adapter resolves the specifier to a real repo path and the core discards it'
phase: 1.5b
milestone: Agent-fit
status: done
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

## Session status

- **KEY:** 188 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended, ticket 1 of 3: 188 → 189 → 190) · envelope in `.mango/run-contract-188.txt`.
- **Branch:** `feat/188-imports-edges-are-never-linked` (off `main` at `25951d1`)
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2444 passed, 0 failed` at `25951d1` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 4 unresolved surfaced | 0 want-decision asked | 4 how-decision resolved+cited | 0 ASSUMED | skip: no`

1. Scope 3's vocabulary decision (split the kind vs try both links) → **neither**; see *The third option the ticket did not list*.
2. Scope 1's *"at a tier that records how it was linked"* → **one arm, so nothing for the tier to disambiguate**; recorded as a deviation.
3. Whether a `contract_version` bump is owed → **no**, and the reason is measurable rather than argued.
4. Scope 4's *"186's hint-and-no-route is revisited"* → **it becomes a route**, conditional on positive evidence.

Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous`
`RECALL: 3 claim(s) surfaced | 2 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=5 R=4 G=1 AC=5`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 11 applicable — 10 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ · §R1.2 (change-type) ✅ — it decided one arm over two · §R3 (change-type) ✅ · §R4.2 (change-type) ✅ · §R5.2 (change-type) ✅ · §R5.4 (change-type) ✅ · §R5.6 (change-type) ✅ · §R6.5 (recalled handle: prove-the-guard-fails) ✅ · §R6.7 (change-type) ✅ · §R7.2 (change-type) ✅ · §R7.6 (change-type) ✅`
`BASELINE: green — 2444 passed, 0 failed, 0 skipped at 25951d1 (bare pytest, Linux host)`

**Premise: every citation resolves and the ticket's diagnosis is exactly right.** Re-measured on a
fresh TS fixture index before touching anything:

```
IMPORTS rows: 14 | target_raw names an indexed file: 10 | of those, LINKED: 0
find_references('src/models.ts') -> reason=relationship_not_modelled, total_count=0, rows=0
include_graph('src/models.ts', imported_by) -> relation_unmodelled_for_language, try_instead=None
impact('src/models.ts') -> 1 row, files={'src/models.ts'}          # the island, measured
```

**Recall:** `prove-the-guard-fails` (R6.5, by handle). `_relative_to` and `relation_unmodelled_for_language`
(by symbol — the two functions this change joins).

### One thing the ticket got wrong, and it is the thing that made this cheap

The ticket says adding `IMPORTS` to the `INCLUDES` branch *"would path-resolve PHP `IMPORTS` too"* —
true — but it also assumes the two kinds can share one key derivation. **They cannot, and not because
of language:** `INCLUDES.target_raw` is written *relative to the including file* (`_relative_to` joins
it onto the includer's directory), while a resolved module specifier is **already repo-relative**.
`_relative_to('tests/…/reexport_barrel.ts', 'tests/…/widgets.ts')` doubles the prefix and misses. So
the arm needed a per-kind key from the start — which is what turned the contract question into a
declaration.

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | the adapter resolves the specifier and the core discards it | link it; the graph decides | measurement above | open |
| R1 | Scope 1 | a module `IMPORTS` naming an indexed file gets `target_qname`, at a tier recording how | linked; **one arm, so the tier is unchanged** | `_path_key` | open |
| R2 | Scope 2 | PHP's symbol-shaped `IMPORTS` unchanged, pinned | a miss, not a guard | proving test | open |
| R3 | Scope 3 | record the vocabulary decision with the R3 impact | **third option: no split, no both-ways** | see design | open |
| R4 | Scope 4 | re-measure the two tools; revisit 186's no-route | route added on positive evidence | proving test ×3 | open |
| AC1 | AC 1 | a TS `IMPORTS` naming an indexed file is linked — fails today | Falsifiable: `target_qname is None` today | red run 2 | open |
| AC2 | AC 2 | a PHP class-FQN `IMPORTS` is not path-linked | Falsifiable: all rows bare | proving test | open |
| AC3 | AC 3 | the two tools re-measured; 186's decision revisited | Falsifiable: reason + route + rows | proving test ×3 | open |
| AC4 | AC 4 | `impact` over a TS seed crosses a module boundary | Falsifiable: >1 file **and** depth ≥ 2 | proving test | open |
| AC5 | AC 5 | R4.2 · R1.1 · contract impact decided | Falsifiable: seeded graph + repeat + grep-gates | proving test ×4 | open |
| C1 | Constraint | R1.1 — the discriminator is the edge's shape, never its language | **sharpened: the GRAPH, not the shape** | — | binding |
| C2 | Constraint | R3 — bump if the vocabulary changes | no kind, no field ⇒ no bump, measured | — | binding |
| C3 | Constraint | R4.2 — a two-way attempt needs a stated precedence | one arm ⇒ no precedence to state | — | binding |
| C4 | Constraint | 061 — a PHP-only index is byte-identical | every PHP `IMPORTS` still bare | — | binding |
| C5 | Constraint | cost — one bounded batch, like the arm it sits beside | the same `nodes_by_qualified_names` call | — | binding |

### Root cause (taxonomy: integration)

**A producer answered and no consumer read the answer.** 155 resolved the specifier against the real
filesystem and stamped it `RESOLVED`; `resolver.py` had one path-linking arm hard-coded to the string
`"INCLUDES"`, and `FQN_EDGE_KINDS` — the opt-in list the other arm reads — never mentioned `IMPORTS`.
The edge fell between two arms that between them cover every other kind. Nothing failed loudly:
183's per-language census reported these rows as `RESOLVED`, which was true about the adapter's
confidence and silent about whether anybody used it.

### Blast radius

- `contract.py`: `PATH_TARGET_BASIS` + derived `PATH_EDGE_KINDS`; `IMPORTS` joins `IMPACT_KIND_WEIGHTS`.
- `resolver.py`: the arm is keyed on `PATH_EDGE_KINDS`, its key comes from `_path_key`, and the
  disjointness assert is now set-level.
- `coverage.py`: `relation_carried_by` — the positive of 186's verdict, and deliberately not its negation.
- `nav_result.py` / `include_graph.py`: one new route + hint; 186's no-route branch kept for the
  language that carries neither kind.
- `find_references.py`: docstring only — its behaviour changes because the graph did.
- **Four tools gain module edges without an edit** (`impact`, `reachable_from`, `find_orphans`,
  `explain_path`) because they all walk `contract.IMPACT_KINDS`.

## Phase 2 — design

### The third option the ticket did not list

The ticket offered two: split the kind (a `contract_version` bump + conformance change, R3) or attempt
both links with the first hit winning (*"makes the resolver's behaviour depend on the shape of a
string, which R5.2 dislikes"*). **Both are rejected, and the reason each fails names the third
option.**

*Splitting the kind* requires the TS adapter to emit the new kind — and *"any adapter change"* is
explicitly out of scope on this ticket, because the adapter is already correct. A vocabulary split
would be the core asking the producer to restate an answer it has already given.

*Attempting both ways* is rejected on **R1.2/YAGNI**, not on taste: only one module adapter exists and
it emits repo-relative, so a second arm would be a code path no test could exercise honestly — and
R6.5 says a guard ships only once observed failing. If adapter #3 emits a relative specifier, it adds
its own basis value to `PATH_TARGET_BASIS`, which is one line and one test.

**The third option: the contract DECLARES the basis, and the GRAPH is the discriminator.**

```python
PATH_TARGET_BASIS = {"INCLUDES": "includer-relative", "IMPORTS": "repo-relative"}
PATH_EDGE_KINDS = tuple(PATH_TARGET_BASIS)          # derived, never listed twice (R6.7)
```

`_path_key` reads the declaration and produces one lookup key; the existing
`nodes_by_qualified_names(..., kind="File", limit=2)` call decides. **This is what keeps R5.2:** the
resolver never asks *"does this string look like a path?"* — a question that needs a per-language
notion of shape. It asks *"does the graph hold a file by this name?"*, which needs none, and a miss is
evidence rather than a guess. A PHP `use A\B\C` misses; an unresolvable `./logger` misses; both stay
bare and both keep feeding `relationship_not_modelled` as honest off-graph evidence.

### Why no `contract_version` bump — measured, not argued

R3.1's literal trigger does not fire: no kind, field or qname convention moved. The one that *could*
is 129's **mechanism** trigger, which is what earned v8 — *"an index built before and updated after
would answer from bare names for untouched files and qualified ones for changed files."* It does not
fire here, and the reason is checkable: `delta_scope` sets
`scoped_kinds = tuple(sorted(FQN_EDGE_KINDS))`, `IMPORTS` is not in it, and
`iter_unresolved_edges` streams every **unscoped** kind on any resolve pass. So an incremental update
after this change links `IMPORTS` from files the delta never named — no mixed era. Pinned by
`test_an_incremental_links_imports_from_files_the_delta_never_names`, which clears the links, touches
**one** file, updates, and asserts the untouched files' imports came back.

### Scope 1's tier clause — a recorded deviation

Scope 1 asks for *"a tier that records how it was linked"*. With one arm there is nothing to
disambiguate: the link kept `INCLUDES`' rule, `_weaker_tier(incoming, "RESOLVED")`, so the tier still
carries the **adapter's** confidence and never upgrades it (R5.2). Introducing a fourth tier value
would be a contract change with no consumer (R1.2). Recorded here rather than silently dropped (P3).

### 186's no-route becomes a route — and only on positive evidence

186 emitted a hint and no route **on a measurement**, and wrote the trigger into its own test:
*"if this answers, the route becomes the honest thing to emit."* It now answers, so R5.4 clause (c)
says name it. But `relation_unmodelled_for_language(kinds=INCLUDES)` firing does not imply the
language emits `IMPORTS` — a language emitting neither would be routed to a tool that answers zero,
which is the failure clause (c) exists to prevent. So the route needs the **positive** question, and
that is not the negation of the existing helper: `relation_unmodelled_for_language` answers `False`
where the index cannot say, which is right for withholding a zero and wrong for naming a route.
`relation_carried_by` answers `False` on **both** silences. Two branches, two pinned cases.

### `IMPORTS` joins the impact weights at `INCLUDES`' 0.8

AC4 is unreachable without it — `impact`/`reachable_from`/`find_orphans`/`explain_path` all walk
`contract.IMPACT_KINDS`. A module dependency **is** a file-level dependency, so it takes the
file-level weight: lower would rank a real module edge below a same-file call, higher would outrank a
direct caller. Pinned as an equality against `INCLUDES` rather than as the literal, so the two move
together. Additive for PHP (no PHP `IMPORTS` is ever linked, so 061 holds byte-exactly).

### Rejected

- **Splitting the kind** — needs an adapter change, explicitly out of scope, and restates an answer
  the adapter already gave (R3 cost for no new information).
- **Both-ways link with precedence** — R1.2/YAGNI: an unexercised arm for a hypothetical adapter.
- **Sniffing `target_raw`'s shape** (`'/' in raw`, a suffix check) — needs a per-language notion of
  shape in the core, which is R1.1 wearing a disguise, and R5.2 rejects a decision not sourced from
  the computation.
- **Teaching `include_graph` to read `IMPORTS`** — 069's territory, and 186 excluded it. The route is
  the honest answer while that is unbuilt.
- **A `contract_version` bump for safety** — it would force every index to rebuild for a mechanism
  that was measured not to bite, and would need both adapters' announced versions moved.

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 2 recorded | 2 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **Exclusion 1 (residual, not a gap):** `include_graph` still answers `[]` for a module language.
  The route makes that navigable; it does not make `include_graph` read `IMPORTS`. Expiry: **069**.
- **Exclusion 2 (coverage gap, AC4 is input-shape-dependent):** *"impact crosses a module boundary"*
  is proven on the spec-driven TS fixture corpus, whose 2-hop chain (`consumer → barrel → models`) I
  did not author for this ticket but which is still authored fixtures, not a real repo. The linking
  itself is shape-independent (a raw either names an indexed file or it does not), so what is
  unproven at real scale is the **depth** claim, not the link. Expiry: the next field retro round —
  `impact` over a TS seed on the anchor repo, the same measurement round 12 ran for PHP.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| `PATH_TARGET_BASIS` declares the basis; `PATH_EDGE_KINDS` derived from it | implemented-as-approved |
| `_path_key` reads the declaration; the graph lookup is the discriminator | implemented-as-approved |
| One arm, no both-ways precedence (R1.2) | implemented-as-approved |
| PHP symbol-shaped `IMPORTS` stays bare as a **miss**, not a guard | implemented-as-approved |
| `IMPORTS` at `INCLUDES`' impact weight | implemented-as-approved |
| Route named only on positive evidence (`relation_carried_by`) | implemented-as-approved |
| No `contract_version` bump, justified by a test not an argument | implemented-as-approved |
| Set-level disjointness assert replaces the string one | implemented-as-approved |

**One correction during execute, and the R1.1 gate caught it.** The first `PATH_TARGET_BASIS` comment
illustrated `includer-relative` with `require './x.php'`. `tests/test_core_is_language_agnostic.py`
failed on `contract.py names ['php']` — an example is still a language name in the core. Reworded to
describe the basis without naming anything.

### Red runs (R6.5)

1. **New tests, pre-change core (whole diff stashed):** collection error on the new constants — real,
   but weak evidence, so it is not the run this ticket rests on.
2. **`resolver.py` reverted only, everything else in place — six behavioural failures**, each on the
   exact shape 188 forbids:
   - `an IMPORTS naming an indexed file must be linked, bare: [10 rows]`
   - `find_references` → `assert 'relationship_not_modelled' == 'ok'`
   - `include_graph` → **`a named route that answers zero is worse than no route`** — the route's
     honesty is load-bearing, not decorative
   - `impact never left the seed's own file: {'src/models.ts'}`
   - the seeded graph → `assert None == 'pkg/b.mod'`
   - the incremental → every import from an untouched file still bare
3. **186's own test flipped red as predicted** (`assert 'try_instead' not in payload`), which is AC3
   arriving as a test failure rather than as a claim.

### Empirical outputs

| Measure | Before | After |
|---|---|---|
| TS `IMPORTS` naming an indexed file | 10 | 10 |
| …of those, linked | **0** | **10** |
| …unresolvable specifiers, linked | 0 | **0** (unchanged — nothing invented) |
| PHP `IMPORTS` linked | 0 | **0** (061 exact) |
| `find_references('src/models.ts')` | `relationship_not_modelled`, 0 rows | `ok`, **3 rows** |
| `include_graph(imported_by)` | hint, no route | hint + `try_instead: find_references` |
| `impact('src/models.ts')` | 1 row, 1 file (itself) | **5 rows, 5 files, max depth 2** |

**Verification coverage:** 5 AC, all 5 covered — 16 new tests in one file, plus one existing 186
test rewritten because 188 falsified its measurement. No AC left to a claim.

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** `2444 passed / 0 failed` at `25951d1` →
`2459 passed / 0 failed`. ruff + mypy green. `scripts/gate.sh` → `GATE GREEN — all 15 checks passed`.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 3 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 2 type-2 claim(s) with seen >= 2 | 2 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

- `prove-the-guard-fails` (R6.5) gains 188 → 23. `route-must-answer` (R5.4's falsifier) gains 188 → 4:
  this is the first time the rule's *other* direction fired — a route that became answerable.
- **New:** `188-C1` (type-2, `link-on-the-graph-not-on-the-string`). seen=1.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived. Self-checks: the
ticket's two offered options both rejected with the reason each fails naming the third; a premise in
the ticket corrected by reading `_relative_to` before implementing (the two path kinds cannot share a
key, and not because of language); the no-bump verdict converted from an argument into a test; the
route gated on positive evidence rather than on the negation of an existing helper; an R1.1 violation
found by the repo's own grep gate and fixed; six behavioural red failures; and the residual —
`include_graph` still returns `[]` — recorded as an exclusion with 069 as its expiry.
