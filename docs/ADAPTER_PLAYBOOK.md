# Adapter playbook — how a language adapter is built, and how it is judged

**Reader:** whoever adds adapter #5, or deepens one of the four that landed.
**This file is the standard**, derived from the four that shipped in phase 1 — PHP, TS/JS, T-SQL,
Python — and from the findings each field build produced. Numbers in it are phase-1 tickets (the
phase-1 archive holds them); from 352 on they are phase 2's, in `tasks/`. It holds the **sequence, the decisions and the gates**. It is not a rule
(→ [`ENGINEERING_RULES.md`](ENGINEERING_RULES.md)), not the contract vocabulary
(→ `contract.py`, [`CONVENTION.md`](CONVENTION.md) §3) and not a design record (→ [`PLAN.md`](PLAN.md)).

Every claim below is something one of the four paid for. Where an adapter is named as an example, it
is the citation, not a suggestion to copy its code — R1.1 and R2 mean two adapters share **shape**
and never logic.

## 1. Two tiers, and what each is for

All four landed in the same two steps, whether or not they were filed as two tickets.

| | tier 1a — *it is indexed* | tier 2 — *its wiring is visible* |
|---|---|---|
| contains | declarations, containment, calls, imports, inheritance | the constructs a framework in that language actually wires itself with |
| php | 007 · 025 | 137 (local type table) |
| typescript | 019 | 153 (type table), 154 (JSDoc) |
| sql | 184 | 022 (`Table` · `Column` · `WRITES`), 321 (`ALTERS`) |
| python | 020 | 217 (decorator/annotation `REFERENCES`, `Protocol`/ABC → `Interface`, `Enum`) |

**Where the tier-2 bar sits is a question with a settled answer,** and 217's W2 row is the one to
reuse: *"framework visibility — not edge-kind parity, not the full 12."* An adapter is done when an
agent can see how the code in front of it is wired, not when its edge-kind census matches PHP's.

**Split the two into separate tickets unless the language is small.** TS shipped as one ticket and
was reopened for a follow-on scope; SQL and Python were filed as pairs and needed no reopening.

### 1.1 Depth mechanisms — a PHP improvement is not done until this table says where the other three stand

PHP is the depth standard (README's HEURISTIC `CALLS` table), so each mechanism it grew was ported,
not copied — same shape, own parser (R1.1/R2). Deepening work starts here, and lands by updating the
row it closed. `n/a` is a measurement: the language has no such construct.

| mechanism | php | typescript | python | sql |
|---|---|---|---|---|
| local type table — annotations, properties, `new X` | 137 | 153 | 227 | n/a |
| lexical receiver (`$this`/`self` · `this` · `self`/`cls`) | 029 | 019 | 020 | n/a |
| member return type resolves the **next** call (`()` chain) | 137 | 301 | 302 | n/a |
| inherited method via hierarchy walk | 137 | free | free | n/a |
| runtime-load stamp (`unmodelled_resolution`) | 279 | 294 | 295 | 296 |
| top-level `new X` binds the receiver (included view, module script) | 362 | 153 | **368** | n/a |
| constructor flag — `find_callers` reads construction sites | 362 | **367** | **367** | n/a |
| static / class property read or write → `REFERENCES` | 336 | **369** | **369** | n/a |
| include path built from the file's dir or a root + literal tail | 353 | **370** | **373** | n/a |
| a string literal that begins a SQL write or `EXEC` | 278 · 335 | **371** | **371** | n/a |

**"free" is the point of the seam:** the hierarchy walk lives in `resolver.py`, so any adapter that
emits inheritance edges gets it without a line of its own. Before filing a port, check whether the
mechanism is adapter-side at all. A **bold** cell is an open port, measured by `--file` (2026-10-08).
Rule-file mechanisms (`keyed_calls`: 352 · 361 · 364) and `include_graph`'s zero (363) are core, so
they have no row — but a rule reads `args`, and Python drops keyword arguments (372).

## 2. The three passes every source adapter converged on

| pass | job | why it cannot merge with the next |
|---|---|---|
| 1 — member table | what each class-like in **this file** declares, and what it inherits | a method may call a method declared below it, so emission cannot be the first read |
| 2 — local type table | variable → class, from what the language writes in the file | it must be flow-sensitive; emission is not |
| 3 — visitor | nodes and **bare** edges (`target_raw` only; the resolver fills `target_qname`) | — |

PHP is the reference — `MemberTypes.php`, `TypeTable.php`, `Visitor.php` — and `types.js:3-6` records
TS as a deliberate port of it (153), and Python's `types.py` a later one (227). SQL needs no pass 2.

Two constraints on pass 2, both learned the expensive way:

- **Bind only what the language puts in the file** — `new X`, a parameter or return hint, a typed
  property, a promoted constructor parameter, a `catch` type. Never a framework's convention (R2).
- **Be forgetful.** A write the table cannot read must *re-open* the variable. A stale binding
  outliving the assignment that invalidated it is worse than no binding, because it resolves
  confidently to the wrong target.

## 3. The optional-field decisions — make each one explicitly

`NODE_FIELDS` and `EDGE_FIELDS` (`contract.py`) are mostly optional, and R1.6 says the core
degrades without them. **An adapter must still decide each one on purpose and declare it**, because
the consumer cannot tell "the code has no annotation" from "this adapter never looks".

| field | decide | consumer that goes quiet if you skip it |
|---|---|---|
| `params` | fill for every callable, with each parameter's declared type | `class_diagram.py`, `onboarding/module_facts.py` — a bare `find()` instead of `find(User $u): User` |
| `extra.type` | fill for a callable's return and a typed property | signature display; your own pass 2 |
| `Method.extra.constructor` | `true` on the method your language makes the constructor (PHP `__construct`, any case — 362) | `find_callers` on it lists the class's construction sites; only PHP sets it so far (TS · Python: 367) |
| `modifiers` | fill for every member the language gives a visibility or a `static`/`readonly`/`final` keyword | `class_diagram.py` — the UML `+`/`-`/`#` marker; §7 has each adapter's measured cell |
| `args` · `arg_keys` | fill at every `CALLS`/`NEW` site — the literal **category**, never the value | `find_callers`'s argument filter (049/063) **and every `CA_INDIRECTION_RULES` edge** (`enrichment.py`), so a repo in your language gets no cross-language link |
| `confidence_tier` | leave **NULL** on a structural edge | nothing — NULL folds into `RESOLVED` (the `confidence_tier` column's DDL default). SQL stamping it explicitly is equivalent, not better; do not file it as a defect |
| `capabilities` | declare what you capture | honesty channel (R1.6). `semantic_types` means *a file-at-a-time local type table backs member-call receivers* (`contract.py` / task 311) — PHP · TS · Python declare it; SQL does not. The other known flags (`params`, `args`, `modifiers`, `declared_types`, `inheritance`) name optional field capture |
| `symbol_shapes` (handshake) | declare the grep shapes of your symbols — `declaration` · `reference` · `call` · `name`, optionally `scoped` (v13, 345) | the grep-time nudge stays silent for your language |
| `is_test` | emit only when decided | omit when undecided so 130's path convention fills via `symbol_role`; a constant `false` opts out of the fallback by accident (262/298) |
| `File.extra.unmodelled_resolution` | stamp every idiom your language resolves at runtime | `find_orphans` — unstamped, unmeasured silence is reported as dead code. All four adapters stamp one: autoload (279), non-literal `import()`/`require()` (294), `importlib`/`__import__` (295), dynamic `EXEC`/`sp_executesql` (296) |

**Do not answer any row of this table from memory or from reading another adapter — measure it.**
`scripts/adapter_parity_report.py` runs every registered adapter over `tests/fixtures/parity/` and
prints §7; a cell you did not measure is a cell you guessed, which is how three of them were wrong
before the generator existed.

## 4. Five gates, in order — each catches what the one before it cannot

| # | gate | catches | **cannot** see |
|---|---|---|---|
| 1 | the adapter's own grammar fixtures | construct correctness, one language feature at a time | anything about real code |
| 2 | a row in `tests/contract/adapter_registry.py` | schema conformance, kind histogram, and edge **shape including its source** — a body edge sourced at the class is a wrong answer no histogram sees (019) | recall: what the file contained and the adapter never emitted |
| 3 | pinned public samples + floors in `scripts/cross_repo_samples.json` | that it survives real code, and does not regress | whether an *answer* built on it is honest |
| 4 | a field round on a real repo (§5) | recall and honesty — phase 1's recall findings came from here and nowhere else; its cheaper sibling is reading the adapters side by side | the size of a fix |
| 5 | before/after over the pinned corpus (`scripts/edge_health_report.py`) | how much a change moved, e.g. 137's 36.3 % → 2.6 % | — |

**Adding a row at gate 2 is data, never an edit to the harness body** (147/AC2) — the same rule holds
for `_ADAPTERS` in `cross_repo_validate.py`.

**Every gate has a state for all four adapters:** pinned public samples with measured floors exist
for each, so gate 5 is reachable for every adapter.
Gate 4 has run for PHP, SQL, Python, and TypeScript — the TS round is
[`235_typescript_field_round.md`](benchmarks/235_typescript_field_round.md).

## 5. The field round — the protocol

Run against a repo you did not write, in the language under test, and record the numbers as you go.

1. **Build full.** Record wall clock, file / node / edge counts, and `parsed_ok` vs total. Anything
   below 100 % parsed is the first finding.
2. **Prove determinism.** Two clean builds, hash the ordered nodes + edges; the two hashes must be
   equal (R4.2). Each `--full` build bulk-clears first (219), so no `graph.db` needs deleting between them.
3. **Check node recall per kind.** Count declarations with `grep`, compare to the node census. Both
   directions matter: a shortfall is a miss, **a surplus is an invention** — that is how 229 was
   found, with a quarter of the graph's nodes turning out to be method locals.
4. **Split the unlinked-edge ratio per kind into expected and recoverable.** A stdlib or third-party
   target that is genuinely not in the repo is *correct* and must be subtracted before any claim.
5. **Ask each nav tool a question you already know the answer to by `grep`.** A confident zero is the
   finding, not an absence of one.
6. **Read the cross-language census** (`get_index_status` at `verbose`). `linked: 0` in a repo whose
   layers call each other by name explains every structural miss at once.
7. **For each finding, run a minimal fixture through the adapter's own `--file` mode before writing
   the ticket.** This is the rule, not a nicety: a finding reasoned from source alone is a
   hypothesis: one obvious import-resolution fix was refuted by a counterexample from the same repo.

## 6. Traps already paid for — read before you re-derive one

- **A bare name has a fallback for `CALLS` and none for inheritance.** `_link_by_bare_name`
  (`resolver.py`) rescues an unqualified `CALLS` at `HEURISTIC` only on a unique same-language
  match — a multi-match stays one unresolved edge (258) — and is deliberately call-only. So a failure to qualify a name costs a tier for a call and a whole edge for an
  `EXTENDS` (226). Qualify at emission; do not rely on the resolver.
- **Test the *container*, not the enclosure,** before publishing a member. Threading "the class we
  are inside" into a method body and asking only that question publishes every local as a property
  (229).
- **A reserved word is not an identifier.** `CREATE TABLE IF NOT EXISTS t` yields a table named `IF`,
  and `ALTER TABLE t ADD COLUMN c` a column named `COLUMN`, if the reader takes the next token (228).
- **An import root has to reach the adapter without an R1.1 breach.** Climbing from the importer
  finds neither a `src/` layout nor a layer root (230) — and the naive fix is worse: a directory scan
  resolves `import requests` to a repo's own `models/requests.py`.
- **One populated kind in a set masks a never-emitted sibling.** `language_emits_none_of` is
  `not any(...)` over the whole set (`store.py`), so an adapter that emits `IMPORTS` and no
  `REFERENCES` never triggers the honest-zero reason (232).
- **A parity claim you typed is a parity claim you guessed.** The first version of §7 was hand-written
  from source reading and had three wrong cells, including `n/a` for a T-SQL procedure's parameters —
  which it has. Run `scripts/adapter_parity_report.py` (R6.7).
- **Declaring the dialect is part of owning the suffix.** Owning `.sql` while reading one dialect and
  announcing nothing produces silent nonsense on every other dialect (228).

## 7. Scoreboard — generated, not typed

**This table is the output of `scripts/adapter_parity_report.py`, pinned by
`tests/test_adapter_parity.py`.** Do not edit it by hand: run the script and paste, or the test
fails. It exists in this shape because the hand-typed version it replaced got three cells wrong —
SQL's dropped procedure parameters read as `n/a`, and `modifiers` was missing because nobody thought
to look. A table an author types is a table an author can guess.

Each adapter is run over its own fixture in [`../tests/fixtures/parity/`](../tests/fixtures/parity/),
one file per registered adapter encoding the same construct set in its own language's spelling.
Ratio cells read `hits/total`: **`0/0` means the fixture had none of that construct to find** — a
measurement, not a judgement — while **`0/1` means it was there and the adapter dropped it**.

<!-- parity-table:start -->
| probe | php | python | sql | typescript |
|---|---|---|---|---|
| `params` on a callable | 2/3 | 2/3 | 1/2 | 2/3 |
| `extra.type` on a member | 4/4 | 4/4 | 1/1 | 4/4 |
| `modifiers` on a member | 4/4 | 1/4 | 0/1 | 2/4 |
| `args` on a call site | 1/1 | 1/1 | 1/1 | 1/1 |
| `arg_keys` on a call site | 1/1 | 1/1 | 1/1 | 1/1 |
| `REFERENCES` edges from the annotations | 3 | 3 | 0 | 3 |
| `ClassConst` for the class constant | 1 | 1 | 0 | 1 |
<!-- parity-table:end -->

**The field rows are at each language's ceiling** — a cell below its denominator means the construct
is unspellable there (Python has no visibility keyword; T-SQL has no modifier, class constant or
annotation), so read a *fallen* cell as a regression and never a cell below 1/1 as a gap. An adapter
declares which fields it fills at handshake (`KNOWN_CAPABILITIES`); a new adapter's flags must match
its column here.

**What this table cannot tell you** is whether an adapter is right about real code — that is gates 3
and 4 (§4).
