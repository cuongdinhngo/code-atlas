# Engineering Rules — code-atlas

The **how we build** rules. These are binding for humans and AI agents. They exist to keep the codebase
clean, testable, and cheap to extend to new languages. Companion docs:
[`CONVENTION.md`](CONVENTION.md) (naming/style) and the [build plan](PLAN.md) (design).

When a rule and a deadline conflict, raise it — don't quietly break the rule. A broken boundary here
costs a rewrite at adapter #2.

---

## 1. Architectural boundaries (SOLID at the seams)

The only axis of change we design for is **languages**. That axis is expressed through **one** seam — the
adapter contract. Everywhere else, prefer the simplest thing that works.

- **R1.1 — Zero language branches in the core.** No `if language == "php"` (or any per-language switch)
  anywhere under `code_atlas/`. Such a branch means the contract leaked; fix the contract, not the core.
  *CI grep-gates this.*
- **R1.2 — One seam only (YAGNI).** The adapter contract is the sole abstraction. Do **not** add a plugin
  registry, base classes, factories, or a DI container until adapter #2 (TS/JS) exists and proves the
  shape. Two implementations reveal the right abstraction; one implementation invents the wrong one.
- **R1.3 — Dependency direction is one-way.** Core depends on the **contract**, never on a concrete parser
  (`nikic`, Roslyn, ts-morph). Adapters depend on nothing in the core. The genuine inversion boundary is
  the **JSON contract + subprocess protocol**, not a Python base class.
- **R1.4 — SRP per component.** Each module has one reason to change:
  - adapters *parse only* (never touch SQLite),
  - `store.py` *persists/queries only*,
  - `enrichment.py` *applies optional rule-file edges only* (never owns SQL; may read a single
    already-indexed call-site line to recover string literals when `view_data` rules request it —
    task 062; never runs a language parser),
  - `resolver.py` *links edges only*,
  - `tools/` *presents only*.
  **Parsing code and storage code must never import each other.**
- **R1.5 — Substitutability (LSP).** Every adapter is interchangeable behind the contract: same node/edge
  vocabulary, same guarantees. The litmus test is R1.1 — no branch anywhere keys on which language it is.
- **R1.6 — Optional power via capability flags (ISP).** Richer data (e.g. Roslyn's `semantic_types`) is
  advertised as a capability the core *may* use, never a method all adapters must implement. The core
  degrades gracefully when a capability is absent.
- **R1.7 — A reader that coerces every value constrains what may be stored beside it; add a sibling key,
  never loosen the reader.** `PROVISIONAL (awaiting ratification)` — promoted from `LESSONS.md` `095-C2`
  (handle `sibling-meta-non-int`, seen 092, 095). When a persisted blob is read through an accessor that
  coerces types — `collection_census()` int-casts every value — a datum of a different shape goes on its
  **own** meta key beside it, never inside the coerced structure. Widening the accessor to admit the new
  shape trades a total, checkable contract for a conditional one, and every existing consumer inherits the
  looser type. *Falsifier:* a non-int value inside the census structure, or an accessor whose coercion was
  relaxed rather than a sibling key added — cf. `UNTRACKED_INDEXABLE_KEY` (092), `IGNORE_SOURCES_KEY` (095).

## 2. Standard over sample

- **R2.1** — Adapters implement the **language specification + ecosystem standards** (for PHP: full 8.5
  grammar, namespaces, PSR-4/PSR-0, traits, enums, attributes, closures, first-class callables, the global
  namespace, `include`/`require`). Nothing else.
- **R2.2** — Adapters must **never** encode a specific repo's directory names, class-naming habits, or
  framework. *CI grep-gate bans repo/framework names in adapter source.*
- **R2.3** — Sample repos (a large PHP monorepo, a Laravel app, a Symfony app, a small library) drive **test coverage
  and performance targets only** — never adapter semantics. If a fact about a repo would change adapter
  behavior, it belongs in the language spec or nowhere.

## 3. The contract is a frozen, versioned artifact

- **R3.1** — Changes to node/edge vocabulary, fields, or qname convention require a `contract_version`
  bump and an update to the conformance tests in the same change.
- **R3.2** — `contract.py` is the single source of truth for the schema. Store, indexer, and tools import
  from it; they never re-declare field lists.
- **R3.3** — Adapters emit **bare** edges (targets as raw FQNs/names); cross-file linking is the core
  resolver's job. A single file can't know all targets — don't pretend it can.
- **R3.4** — Every adapter must pass `tests/contract/` before it's considered to exist. That test *is* the
  substitutability guarantee.

## 4. Determinism & purity of the core

- **R4.1 — No LLM or network calls in the core.** Ever. LLM enrichment lives only in the Phase-2
  onboarding layer, cleanly separated: *deterministic graph → LLM enrichment → presentation.*
- **R4.2 — Identical input → identical output.** Same repo state produces identical rows. No wall-clock,
  randomness, or set-ordering leaking into stored data. Incremental update for a state must equal a full
  rebuild of that state.
- **R4.3 — Single SQLite writer.** Concurrency is in parsing (N adapter workers), not in writing. WAL,
  indexed queries, bounded traversal in SQL — never load the whole graph into memory.

## 5. Error handling & degradation

- **R5.1** — A syntax error in one file returns `ok:false` for that file and never breaks the stream or
  the build. Set `parsed_ok=0`; keep going. This holds for a bad *store write* too, not just a bad
  parse: a per-file `IntegrityError` (e.g. a legal duplicate declaration — a `function_exists` guard,
  an `interface X`/`class X` pair) is de-duped keep-first by the store and, failing that, soft-fails
  the one file — it never aborts the build (task 043).
- **R5.2** — Unresolvable-but-static references are `HEURISTIC`; dynamic constructs (`$obj->$m()`, variable
  includes) are `DYNAMIC` and excluded from traversal by default. Never silently link a guess as
  `RESOLVED`. A name that resolves to **one qname declared in several files** is not a guess — an edge
  records a `target_qname`, so the name did resolve; link it once at `RESOLVED` and let the `nodes`
  rows carry the per-file detail (task 046). Multiplicity is not ambiguity.
- **R5.3** — Fail loud on *config/programmer* errors (bad `CA_*`, missing adapter command); fail soft on
  *data* errors (one weird source file). Don't confuse the two.
- **R5.4 — A field the reader is expected to act on holds one register; prose gets a sibling field.**
  `PROVISIONAL (awaiting ratification)` — promoted from `LESSONS.md` `093-C1` (handle
  `try-instead-tool-name`, seen 092, 093, 100, 101, 102). When a payload field carries a value the reader is meant to
  *execute* — a route, a tool name, an identifier — **every** value of that field must be machine-checkable
  as that kind, and the qualifier saying *how* to re-ask goes in a named sibling (`try_instead` /
  `try_instead_hint`). One prose value makes the whole field ambiguous, not just itself: the reader cannot
  tell a route from an instruction without spending a call. Before emitting a route it must (a) be a member
  of a registry **derived from code**, not a hand-kept list, (b) not name the tool that is answering — a
  self-route loops for the mechanical reader the field exists for, and (c) be able to answer the question
  that caused the miss. **Where no registered tool can answer, emit the hint and no route:** naming a tool
  that cannot answer is worse than naming none, because the reader spends a call and gets a confident wrong
  answer. *Falsifier:* a route constant whose value is not in the registry, an emitter whose
  `try_instead` equals its own tool name — the enumeration test fails — or a route that cannot answer the
  question that caused the miss: call the routed tool on the subject that missed and it returns `reason: ok`
  while the thing the reader was looking for is still absent (clause (c), handle `route-must-answer`,
  `LESSONS.md` `093-C4`, seen 093, 101, 102).

- **R5.5 — A reported value is sourced from the computation that owns the whole fact.**
  `PROVISIONAL (awaiting ratification)` — promoted from `LESSONS.md` `100-C1` (handle
  `source-the-caveat-from-the-computation`, seen 100, 101, 102) by the `/mango:promote` run of
  2026-08-16. When a surface — a payload field, a signed claim line, a summary — reports a count or a
  caveat, read it from the computation that owns the **entire** fact the field names, never from a
  producer whose scope is narrower than the field's documented meaning. Two ways this breaks: the source
  carries the value only at some **detail levels**, or the source computes it only for some of the
  **cases** the field's name covers. Both ship a value that is honest about its source and false about
  its subject. *Falsifier:* a field whose producers, enumerated by grep, cover fewer cases than its name
  or docstring claims — or a caveat present at one detail level and absent at another for the same
  underlying fact. Measured twice: `CLAIM_CARRY = ("parse_failures",)` read the key off a payload that
  only carries it at `standard`/`verbose`, so the `minimal` line shipped without the caveat while
  `counts["failed"]` was 1 (100); and `seeds_dropped` was assigned in exactly one place — the store's
  budget prune — while documented as the field that names every dropped seed, so a subject the tool
  could not resolve was never counted at all (102).

## 6. Testing (definition of done)

- **R6.1** — No task is done without tests. Minimum bar per area:
  - adapter change → a fixture + conformance assertion,
  - resolver/store/indexer change → an integration test asserting resolved rows,
  - tool change → a test over a fixture repo.
- **R6.2 — Spec-driven fixtures, not repo-driven.** PHP fixtures cover language constructs (namespaced,
  global, PSR-0 underscore, trait+conflict, enum, attributes, closures, first-class callable, include,
  static-vs-instance call, syntax error) — independent of any real repo.
- **R6.3 — Cross-repo validation** proves "works on any repo": several varied repos index without crashes
  and with sane counts. No single repo defines "correct".
- **R6.4 — Guardrail tests are real tests.** The grep-gates (no language branches in core; no
  repo/framework names in adapters) run in CI and fail the build.
- **R6.5 — A guardrail sweep covers *authored* source only, and is guarded against emptying itself.**
  Every grep-gate or file sweep excludes vendored trees (`vendor/`, `node_modules/`) — a dependency's
  own documentation is not this repo's source, and greps a framework name inside one. The exclusion
  itself needs a test asserting the sweep is still non-empty; a filter that swallows the authored files
  restores the 0/0 vacuity the guard existed to remove. **This generalises to every guard, not only a
  sweep** (handle `prove-the-guard-fails`, `LESSONS.md` `093-C3`, seen 093, 096, 099, 100, 101): a guard ships
  only once it has been *observed failing* — run it against the shape it forbids (the pre-fix code, a
  sabotaged input, an injected invalid member) and record what failed. *Falsifier:* a guard test whose
  PR claims a defect class is prevented with no recorded red run — cf. the dead-route guard that
  scanned its own definition site (093), the delta-scope key set stubbed to `set()` (096), the
  positive-fire test that stops the silence negatives passing vacuously (099).
- **R6.6 — Every language gets a static analyser in CI, at its strictest clean setting.** The core has
  `mypy`; the PHP adapter has **PHPStan at `level: max`** (`adapters/php/phpstan.neon`), and each later
  adapter brings the equivalent for its language. Suppression is not how a finding is closed: no
  baseline file, no `@phpstan-ignore`, no inline `@var` override, no widened signature or cast added
  only to silence a rule. Either fix the code or argue the level down in the rule book — where the
  argument is reviewable. `php -l` does **not** satisfy this; it catches syntax, not types.
- **R6.7 — A guard that needs "every valid X" derives the set; it never lists it.**
  `PROVISIONAL (awaiting ratification)` — promoted from `LESSONS.md` `093-C2` + `095-C1` + `097-C1`
  (handle `derived-not-listed-invariant`, seen 093, 095, 096, 097, 099, 100, 101, 102). When a test or a payload
  needs the set of all valid members — tool names, ignore-source keys, reason codes — it derives that
  set from the definition site
  (a module namespace, a registry, the composition that builds it) rather than re-typing the members. A
  hand-kept list is precisely what drifts when member N+1 arrives, and it drifts **silently**, because the
  guard still passes. *Falsifier:* a literal list of valid members inside a test or tool where a derivation
  was available — `main.TOOL_NAMES` / `vars(module)` (093), `composed_source_names()` from
  `COMPOSED_IGNORE_FILES` (095), `contract.FQN_EDGE_KINDS` passed into the scoped scan rather than
  re-typed in `store.py` (096), one `estimate_tokens` definition site (099) — or a new member that
  ships without failing any guard.

## 7. Change discipline

- **R7.1 — Ship the smallest useful thing.** The first release is search/read/outline (task 014); don't
  gold-plate before it's usable.
- **R7.2 — Keep the plan and backlog honest.** A design decision updates the [plan](PLAN.md);
  task status updates both [`BACKLOG.md`](BACKLOG.md) and the task file's frontmatter.
- **R7.3 — Small, reviewable commits** with imperative messages; no AI-attribution trailer. One logical
  change per commit.
- **R7.4 — No dead abstractions.** If an interface has one implementer and no near-term second, delete it.
  Revisit when the second arrives.
- **R7.5 — Comments stay ≤ 3 lines.** Every code comment is at most three lines; explain *what + why*, not
  the obvious. If it needs more, the code should be clearer or the explanation belongs in a doc/docstring.

## 8. Dependencies

- **R8.1** — Each adapter is self-contained with its own runtime/manifest (`composer.json`,
  `package.json`, `.csproj`) and documents how it's launched (`CA_<LANG>_CMD`). Adapter deps never leak
  into the Python core.
- **R8.3 — An adapter's dependencies are pinned by a committed lock file** (`composer.lock`,
  `package-lock.json`, `packages.lock.json`); only the resolved artifacts (`vendor/`, `node_modules/`)
  are ignored. A floating version range lets two machines resolve different parser builds and emit
  different rows from the same file, which R4.2 forbids.
- **R8.2** — Keep core dependencies minimal (FastMCP + stdlib-first). Add a dependency only when it earns
  its place; prefer the standard library and SQLite features.

---

**Quick self-check before opening a PR:** Does the core have any language branch? Does an adapter mention
a repo or framework by name? Did the contract change without a version bump + conformance update? Is there
a test? Is it the smallest change that ships value? Are the related docs updated to match the work
(PLAN / BACKLOG + task frontmatter / CONVENTION / this file / README)? If any answer is wrong, fix it
before review.
