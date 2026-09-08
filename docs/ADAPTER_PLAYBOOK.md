# Adapter playbook — how a language adapter is built, and how it is judged

**Reader:** whoever adds adapter #5, or deepens one of the four that landed.
**This file is the standard**, derived from the four that shipped — PHP (007 · 025 · 137), TS/JS
(019 · 150 · 153), T-SQL (184 · 022), Python (020 · 217) — and from the findings each field build
produced. It holds the **sequence, the decisions and the gates**. It is not a rule
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
| sql | 184 | 022 (`Table` · `Column` · `WRITES`) |
| python | 020 | 217 (decorator/annotation `REFERENCES`, `Protocol`/ABC → `Interface`, `Enum`) |

**Where the tier-2 bar sits is a question with a settled answer,** and 217's W2 row is the one to
reuse: *"framework visibility — not edge-kind parity, not the full 12."* An adapter is done when an
agent can see how the code in front of it is wired, not when its edge-kind census matches PHP's.

**Split the two into separate tickets unless the language is small.** 019 shipped TS as one ticket,
was reopened on 2026-08-25, and carried a 150-157 follow-on scope to close; SQL and Python were filed
as pairs and needed no reopening.

## 2. The three passes every source adapter converged on

| pass | job | why it cannot merge with the next |
|---|---|---|
| 1 — member table | what each class-like in **this file** declares, and what it inherits | a method may call a method declared below it, so emission cannot be the first read |
| 2 — local type table | variable → class, from what the language writes in the file | it must be flow-sensitive; emission is not |
| 3 — visitor | nodes and **bare** edges (`target_raw` only; the resolver fills `target_qname`) | — |

PHP is the reference — `MemberTypes.php`, `TypeTable.php`, `Visitor.php` — and `types.js:3-6` records
TS as a deliberate port of it (153). SQL needs no pass 2. **Python has no pass 2 at all**, which is
[227](tasks/227_python-has-no-local-type-table-so-every-member-call-is-heuristic.md).

Two constraints on pass 2, both learned the expensive way:

- **Bind only what the language puts in the file** — `new X`, a parameter or return hint, a typed
  property, a promoted constructor parameter, a `catch` type. Never a framework's convention (R2).
- **Be forgetful.** A write the table cannot read must *re-open* the variable. A stale binding
  outliving the assignment that invalidated it is worse than no binding, because it resolves
  confidently to the wrong target.

## 3. The optional-field decisions — make each one explicitly

`NODE_FIELDS` and `EDGE_FIELDS` (`contract.py:121-144`) are mostly optional, and R1.6 says the core
degrades without them. **An adapter must still decide each one on purpose and declare it**, because
the consumer cannot tell "the code has no annotation" from "this adapter never looks".

| field | decide | consumer that goes quiet if you skip it |
|---|---|---|
| `params` | fill for every callable, with each parameter's declared type | `class_diagram.py`, `onboarding/module_facts.py` — a bare `find()` instead of `find(User $u): User` |
| `extra.type` | fill for a callable's return and a typed property | signature display; your own pass 2 |
| `modifiers` | fill for every member the language gives a visibility or a `static`/`readonly`/`final` keyword | `class_diagram.py` — the UML `+`/`-`/`#` marker. TS spells all of them and emits none |
| `args` · `arg_keys` | fill at every `CALLS`/`NEW` site — the literal **category**, never the value | `find_callers`'s argument filter (049/063) **and every `CA_INDIRECTION_RULES` edge** (`enrichment.py`), so a repo in your language gets no cross-language link |
| `confidence_tier` | leave **NULL** on a structural edge | nothing — NULL folds into `RESOLVED` (`store.py:704-709`). SQL stamping it explicitly is equivalent, not better; do not file it as a defect |
| `capabilities` | declare what you capture | this is the honesty channel and it is nearly unused: `KNOWN_CAPABILITIES` (`contract.py:185`) still holds one entry |
| `is_test` | skip | nothing reads it; `class_diagram.py:253` derives the role from the path |

**Do not answer any row of this table from memory or from reading another adapter — measure it.**
`scripts/adapter_parity_report.py` runs every registered adapter over `tests/fixtures/parity/` and
prints §7; a cell you did not measure is a cell you guessed, which is how three of them were wrong
before the generator existed. Closing the gaps §7 shows is
[231](tasks/231_params-and-args-are-emitted-by-one-adapter-each-so-a-signature-is-a-php-feature.md),
the construct three adapters answer three ways is
[232](tasks/232_the-same-construct-is-a-references-edge-in-python-and-node-extra-in-php-and-ts.md),
and the class-constant kind is
[234](tasks/234_classconst-is-a-php-only-kind-and-the-two-signals-that-would-fill-it-elsewhere-are-discarded.md).

## 4. Five gates, in order — each catches what the one before it cannot

| # | gate | catches | **cannot** see |
|---|---|---|---|
| 1 | the adapter's own grammar fixtures | construct correctness, one language feature at a time | anything about real code |
| 2 | a row in `tests/contract/adapter_registry.py` | schema conformance, kind histogram, and edge **shape including its source** — a body edge sourced at the class is a wrong answer no histogram sees (019) | recall: what the file contained and the adapter never emitted |
| 3 | pinned public samples + floors in `scripts/cross_repo_samples.json` | that it survives real code, and does not regress | whether an *answer* built on it is honest |
| 4 | a field round on a real repo (§5) | recall and honesty — **every finding 221-230 came from here and nowhere else**; 231 and 232 came from the cheaper sibling of this gate, reading the four adapters side by side | the size of a fix |
| 5 | before/after over the pinned corpus (`scripts/edge_health_report.py`) | how much a change moved, e.g. 137's 36.3 % → 2.6 % | — |

**Adding a row at gate 2 is data, never an edit to the harness body** (147/AC2) — the same rule holds
for `_ADAPTERS` in `cross_repo_validate.py`.

**The current state of these gates is the standard's own indictment.** Gates 1-2 are complete for all
four. Gate 3 exists for PHP and TS only, so gate 5 is impossible for Python and SQL — that is
[233](tasks/233_python-and-sql-have-no-pinned-public-sample-so-no-change-to-either-can-be-shown-to-move-anything.md).
Gate 4 has run for PHP, SQL and Python, and **never for TS**.

## 5. The field round — the protocol that produced 221-230

Run against a repo you did not write, in the language under test, and record the numbers as you go.

1. **Build full.** Record wall clock, file / node / edge counts, and `parsed_ok` vs total. Anything
   below 100 % parsed is the first finding.
2. **Prove determinism.** Two clean builds, hash the ordered nodes + edges; the two hashes must be
   equal (R4.2). Delete `graph.db` between them — a rebuild over a populated one is a different
   measurement (219).
3. **Check node recall per kind.** Count declarations with `grep`, compare to the node census. Both
   directions matter: a shortfall is a miss, **a surplus is an invention** — that is how 229 was
   found, with a quarter of the graph's nodes turning out to be method locals.
4. **Split the unlinked-edge ratio per kind into expected and recoverable.** A stdlib or third-party
   target that is genuinely not in the repo is *correct* and must be subtracted before any claim.
   226 and 230 are what survived that subtraction.
5. **Ask each nav tool a question you already know the answer to by `grep`.** A confident zero is the
   finding, not an absence of one. 221 and 226 are both this step.
6. **Read the cross-language census** (`get_index_status` at `verbose`). `linked: 0` in a repo whose
   layers call each other by name explains every structural miss at once (221).
7. **For each finding, run a minimal fixture through the adapter's own `--file` mode before writing
   the ticket.** This is the rule, not a nicety: a finding reasoned from source alone is a
   hypothesis. 230's Notes carry the case for it — the obvious fix for its import resolution was
   refuted by a counterexample from the same repo, and the ticket had to be written so it could not
   be implemented as a directory scan.

## 6. Traps already paid for — read before you re-derive one

- **A bare name has a fallback for `CALLS` and none for inheritance.** `_link_by_bare_name`
  (`resolver.py:316-329`) rescues an unqualified `CALLS` at `HEURISTIC` and is deliberately
  call-only. So a failure to qualify a name costs a tier for a call and a whole edge for an
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
  `not any(...)` over the whole set (`store.py:857`), so an adapter that emits `IMPORTS` and no
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

**Since 231 the five field rows are at each language's ceiling, not its shortfall** — a cell below
its denominator now means the construct is unspellable there (Python has no visibility keyword;
T-SQL has no modifier at all, which is why its handshake declares `modifiers: false`), so read a
*fallen* cell as a regression and never a cell below 1/1 as a gap. **The last two shortfalls closed
together:** [232](tasks/232_the-same-construct-is-a-references-edge-in-python-and-node-extra-in-php-and-ts.md)
filled the `REFERENCES` row and
[234](tasks/234_classconst-is-a-php-only-kind-and-the-two-signals-that-would-fill-it-elsewhere-are-discarded.md)
the `ClassConst` row, php · python · typescript each; `sql` stays 0 on both — T-SQL has neither an
annotation to read nor a class constant to name, which is a measurement, not a gap.
**234 also moved the two member denominators** (`_members` reads `Method`/`Property`/`Column`, so a
constant reclassified out of `Property` leaves that population): python and TS `extra.type` read 4/4
where they read 5/5 and 4/5, and TS `modifiers` 2/4 where it read 3/5. Those are the same members
counted under a corrected kind — not the fallen cell this paragraph tells you to read as a regression.
An adapter declares which fields it fills at handshake (`KNOWN_CAPABILITIES`); declaring one it
cannot fill is the defect 231 removed, so a new adapter's flags must match its column here.

**What this table cannot tell you** is whether an adapter is right about real code — that is gates 3
and 4, whose state §4 records: pinned samples exist for `php`, `typescript`, `python`, and `sql`
([233](tasks/233_python-and-sql-have-no-pinned-public-sample-so-no-change-to-either-can-be-shown-to-move-anything.md)),
and a field round has never been run for `typescript`
([235](tasks/235_the-typescript-adapter-has-never-been-asked-a-question-in-the-field.md)).
