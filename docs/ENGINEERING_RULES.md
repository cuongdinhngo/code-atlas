# Engineering Rules — code-atlas

The **how we build** rules, binding for humans and AI agents: they keep the codebase clean,
testable, and cheap to extend to a new language. Companions — [`CONVENTION.md`](CONVENTION.md)
(naming/style), the [build plan](PLAN.md) (design), and [`LESSONS.md`](LESSONS.md), which holds the
per-task evidence and narrative behind the rules below.

When a rule and a deadline conflict, raise it — don't quietly break the rule. A broken boundary here
costs a rewrite at adapter #2.

A rule's closing italic line is its provenance: `LESSONS.md` entry · **handle** · the tasks it has
been **seen** on (keep that list honest — `AGENT_BRIEF.md` P-rules) · `Provisional` if it binds now
but awaits ratification.

---

## 1. Architectural boundaries (SOLID at the seams)

The only axis of change we design for is **languages**, and it is expressed through **one** seam —
the adapter contract. Everywhere else, prefer the simplest thing that works.

- **R1.1 — Zero language branches in the core.** No `if language == "php"`, or any per-language
  switch, anywhere under `code_atlas/`. Such a branch means the contract leaked; fix the contract,
  not the core. *CI grep-gates this.*
- **R1.2 — One seam only (YAGNI).** The adapter contract is the sole abstraction. No plugin
  registry, base classes, factories or DI container until adapter #2 (TS/JS) exists and proves the
  shape. Two implementations reveal the right abstraction; one invents the wrong one.
- **R1.3 — Dependency direction is one-way.** The core depends on the **contract**, never on a
  concrete parser (`nikic`, Roslyn, ts-morph); adapters depend on nothing in the core. The genuine
  inversion boundary is the **JSON contract + subprocess protocol**, not a Python base class.
- **R1.4 — SRP per component.** One reason to change each: adapters *parse only* (never touch
  SQLite); `store.py` *persists and queries only*; `enrichment.py` *applies optional rule-file edges
  only* — never owns SQL, never runs a language parser, but may read a single already-indexed
  call-site line to recover string literals when `view_data` rules request it (062); `resolver.py`
  *links edges only*; `tools/` *presents only*. **Parsing code and storage code must never import
  each other.**
- **R1.5 — Substitutability (LSP).** Every adapter is interchangeable behind the contract: same
  node/edge vocabulary, same guarantees. R1.1 is the litmus test — no branch keys on which language
  it is.
- **R1.6 — Optional power via capability flags (ISP).** Richer data (e.g. Roslyn's
  `semantic_types`) is advertised as a capability the core *may* use, never a method every adapter
  must implement. The core degrades gracefully when it is absent.
- **R1.7 — Add a sibling key; never loosen a coercing reader.** When a persisted blob is read
  through an accessor that coerces types — `collection_census()` int-casts every value — a datum of
  a different shape goes on its **own** meta key beside it, never inside the coerced structure.
  Widening the accessor trades a total, checkable contract for a conditional one, and every existing
  consumer inherits the looser type. *Falsifier:* a non-int inside the census structure, or a
  coercion relaxed instead of a sibling key added — cf. `UNTRACKED_INDEXABLE_KEY` (092),
  `IGNORE_SOURCES_KEY` (095).
  *Provisional · `LESSONS.md` `095-C2` · handle `sibling-meta-non-int` · seen 092, 095.*

## 2. Standard over sample

- **R2.1** — Adapters implement the **language specification + ecosystem standards** (for PHP: full
  8.5 grammar, namespaces, PSR-4/PSR-0, traits, enums, attributes, closures, first-class callables,
  the global namespace, `include`/`require`). Nothing else.
- **R2.2** — Adapters must **never** encode a specific repo's directory names, class-naming habits,
  or framework. *CI grep-gate bans repo/framework names in adapter source.*
- **R2.3** — Sample repos (a large PHP monorepo, a Laravel app, a Symfony app, a small library)
  drive **test coverage and performance targets only**, never adapter semantics. If a fact about a
  repo would change adapter behaviour, it belongs in the language spec or nowhere.

## 3. The contract is a frozen, versioned artifact

- **R3.1** — A change to node/edge vocabulary, fields, or the qname convention requires a
  `contract_version` bump and a conformance-test update in the same change.
- **R3.2** — `contract.py` is the single source of truth for the schema. Store, indexer and tools
  import from it; they never re-declare field lists.
- **R3.3** — Adapters emit **bare** edges (targets as raw FQNs/names); cross-file linking is the
  core resolver's job. A single file can't know all targets — don't pretend it can.
- **R3.4** — Every adapter must pass `tests/contract/` before it is considered to exist. That test
  *is* the substitutability guarantee.

## 4. Determinism & purity of the core

- **R4.1 — No LLM or network calls in the core.** Ever. LLM enrichment lives only in the Phase-3
  onboarding layer, cleanly separated: *deterministic graph → LLM enrichment → presentation.* In
  practice that means **outside `code_atlas/`**: the three implementers (090 summarizer, 091 layer
  refiner, 117 prose writer) live in `onboarding_llm/`, are injected through Protocol seams, and are
  off by default. *CI grep-gates this* — no prompt text, model id or LLM import under `code_atlas/`
  (117).
- **R4.2 — Identical input → identical output.** The same repo state produces identical rows: no
  wall-clock, randomness or set-ordering leaking into stored data. An incremental update for a state
  must equal a full rebuild of that state.
- **R4.3 — Single SQLite writer.** Concurrency is in parsing (N adapter workers), not in writing.
  WAL, indexed queries, bounded traversal in SQL — never load the whole graph into memory.

## 5. Error handling & degradation

- **R5.1** — A syntax error in one file returns `ok:false` for that file and never breaks the stream
  or the build: set `parsed_ok=0` and keep going. This holds for a bad *store write* too — a
  per-file `IntegrityError` (a legal duplicate declaration: a `function_exists` guard, an
  `interface X`/`class X` pair) is de-duped keep-first by the store and, failing that, soft-fails
  that one file; it never aborts the build (043).
- **R5.2** — Unresolvable-but-static references are `HEURISTIC`; dynamic constructs (`$obj->$m()`,
  variable includes) are `DYNAMIC` and excluded from traversal by default. Never silently link a
  guess as `RESOLVED`. A name resolving to **one qname declared in several files** is not a guess —
  the edge records a `target_qname`, so the name did resolve: link it once at `RESOLVED` and let the
  `nodes` rows carry the per-file detail (046). Multiplicity is not ambiguity.
- **R5.3** — Fail loud on *config/programmer* errors (bad `CA_*`, missing adapter command); fail
  soft on *data* errors (one weird source file). Don't confuse the two.
- **R5.4 — A field the reader acts on holds one register; prose gets a sibling field.** Where a
  payload field carries a value the reader is meant to *execute* — a route, a tool name, an
  identifier — **every** value must be machine-checkable as that kind, and the *how to re-ask*
  qualifier goes in a named sibling (`try_instead` / `try_instead_hint`). One prose value makes the
  whole field ambiguous, not just itself: the reader cannot tell a route from an instruction without
  spending a call. A route must (a) be a member of a registry **derived from code**, not a hand-kept
  list, (b) never name the tool that is answering — a self-route loops for the mechanical reader the
  field exists for — and (c) be able to answer the question that caused the miss. **Where no
  registered tool can, emit the hint and no route:** naming a tool that cannot answer is worse than
  naming none, because the reader spends a call on a confident wrong answer. *Falsifier:* a route
  constant outside the registry; an emitter whose `try_instead` equals its own tool name (the
  enumeration test fails); or a routed tool that returns `reason: ok` on the subject that missed
  while the thing sought is still absent (clause (c) · handle `route-must-answer` · `LESSONS.md`
  `093-C4` · seen 093, 101, 102).
  *Provisional · `LESSONS.md` `093-C1` · handle `try-instead-tool-name` ·
  seen 092, 093, 100, 101, 102.*
- **R5.5 — A reported value is sourced from the computation that owns the whole fact.** When a
  surface — a payload field, a signed claim line, a summary — reports a count or a caveat, read it
  from the computation owning the **entire** fact the field names, never from a producer narrower
  than the field's documented meaning. Two shapes: the source carries the value only at some
  **detail levels**, or computes it only for some of the **cases** the field's name covers. Both
  ship a value honest about its source and false about its subject. *Falsifier:* producers,
  enumerated by grep, covering fewer cases than the field's name or docstring claims — or a caveat
  present at one detail level and absent at another for the same underlying fact. Measured twice:
  `CLAIM_CARRY = ("parse_failures",)` read a key carried only at `standard`/`verbose`, so the
  `minimal` line shipped without the caveat while `counts["failed"]` was 1 (100); and
  `seeds_dropped` counted only the store's budget prune while documented as naming every dropped
  seed (102).
  *Provisional · `LESSONS.md` `100-C1` · handle `source-the-caveat-from-the-computation` · seen 100,
  101, 102 · promoted by the `/mango:promote` run of 2026-08-16.*

## 6. Testing (definition of done)

- **R6.1** — No task is done without tests. Minimum bar per area: adapter change → a fixture +
  conformance assertion; resolver/store/indexer change → an integration test asserting resolved
  rows; tool change → a test over a fixture repo.
- **R6.2 — Spec-driven fixtures, not repo-driven.** PHP fixtures cover language constructs
  (namespaced, global, PSR-0 underscore, trait+conflict, enum, attributes, closures, first-class
  callable, include, static-vs-instance call, syntax error) — independent of any real repo.
- **R6.3 — Cross-repo validation** proves "works on any repo": several varied repos index without
  crashes and with sane counts. No single repo defines "correct".
  **And where an acceptance criterion needs a judgement about a real repo — a threshold, a ranking,
  an elected group, a ratio — that judgement ships as a committed, re-runnable reporter, not an
  ad-hoc session run.** An authored fixture mirrors the assumption the code already makes, so it
  cannot exhibit the shape that breaks it; a pinned suite can be green on both sides of a real
  defect. The reporter prints the real inputs the constant was chosen from, so the constant can be
  re-justified whenever a pin moves — `scripts/layer_report.py` (105) and `scripts/mirror_report.py`
  (115) are what compliance looks like. *Falsifier:* an acceptance-criterion threshold, ranking or
  elected group whose only evidence is a fixture or a session transcript, with no committed
  reproducer.
  *Provisional (awaiting ratification) · `LESSONS.md` `105-C2` · handle
  `fixture-shape-begs-the-question` · seen 084, 086, 103, 104, 105, 106, 121.*
- **R6.4 — Guardrail tests are real tests.** The three grep-gates (R1.1 no language branches in
  core; R2.2 no repo/framework names in adapters or core; R4.1 no prompt/model id/LLM import in
  core) run in CI and fail the build.
- **R6.5 — A guardrail sweep covers *authored* source only, and is guarded against emptying
  itself.** Every grep-gate or file sweep excludes vendored trees (`vendor/`, `node_modules/`): a
  dependency's own documentation is not this repo's source, and it greps a framework name. The
  exclusion needs its own test asserting the sweep is still non-empty — a filter that swallows the
  authored files restores the 0/0 vacuity the guard existed to remove. **This generalises to every
  guard, not only a sweep:** one ships only once it has been *observed failing* — run it against the
  shape it forbids (the pre-fix code, a sabotaged input, an injected invalid member) and record the
  red run. *Falsifier:* a guard test whose PR claims a defect class is prevented with no recorded
  red run — cf. the dead-route guard that scanned its own definition site (093), the delta-scope key
  set stubbed to `set()` (096), the positive-fire test that stops silence negatives passing
  vacuously (099).
  **The gate itself is bound by this rule.** `scripts/gate.sh` mirrors every CI job, and it exits
  **2 when a check was skipped** — a gate that shrank to what one machine can run has not verified
  the tree, so only `GATE GREEN` counts as green. Never read a skip as a pass, and never narrow the
  gate to make it pass; if a check cannot run here, run it where it can (Docker — README
  *Testing*) and say which host produced the result.
  *`LESSONS.md` `093-C3` · handle `prove-the-guard-fails` · seen 087, 088, 089, 093, 096, 099, 100,
  101, 121, 122, 132.*
- **R6.6 — Every language gets a static analyser in CI, at its strictest clean setting.** The core
  has `mypy`; the PHP adapter has **PHPStan at `level: max`** (`adapters/php/phpstan.neon`), and
  each later adapter brings the equivalent. Suppression is not how a finding is closed: no baseline
  file, no `@phpstan-ignore`, no inline `@var` override, no widened signature or cast added only to
  silence a rule. Either fix the code or argue the level down in this rule book, where the argument
  is reviewable. `php -l` does **not** satisfy this; it catches syntax, not types.
- **R6.7 — A guard that needs "every valid X" derives the set; it never lists it.** Where a test or
  a payload needs the set of all valid members — tool names, ignore-source keys, reason codes — it
  derives that set from the definition site (a module namespace, a registry, the composition that
  builds it) rather than re-typing the members. A hand-kept list is precisely what drifts when
  member N+1 arrives, and it drifts **silently**, because the guard still passes. *Falsifier:* a
  literal list of valid members inside a test or tool where a derivation was available —
  `main.TOOL_NAMES` / `vars(module)` (093), `composed_source_names()` from `COMPOSED_IGNORE_FILES`
  (095), `contract.FQN_EDGE_KINDS` passed into the scoped scan instead of re-typed in `store.py`
  (096), one `estimate_tokens` definition site (099) — or a new member that ships without failing
  any guard.
  *Provisional · `LESSONS.md` `093-C2` + `095-C1` + `097-C1` · handle `derived-not-listed-invariant`
  · seen 087, 088, 093, 095, 096, 097, 099, 100, 101, 102, 121, 122, 127, 132.*

## 7. Change discipline

- **R7.1 — Ship the smallest useful thing.** The first release is search/read/outline (014); don't
  gold-plate before it is usable.
- **R7.2 — Keep the plan and backlog honest, cost included.** A design decision updates the
  [plan](PLAN.md); task status updates both [`BACKLOG.md`](BACKLOG.md) and the task file's
  frontmatter. **And the spend is part of the status:** before a PR opens, the task's token spend
  goes in its working-doc cost ledger (`docs/tasks/NNN_slug.work.md`) **and** in the Token usage
  table in `BACKLOG.md`. No PR without it recorded in both places. A finished task whose cost is
  unrecorded reads as free, and a project that cannot say what a ticket cost cannot argue about
  where its effort goes. *Falsifier:* a task at `done` with no Token-usage row, or a spend quoted in
  one place and not the other — guarded by `tests/test_backlog_bookkeeping.py`.
- **R7.3 — Small, reviewable commits** with imperative messages and no AI-attribution trailer. One
  logical change per commit.
- **R7.4 — No dead abstractions.** An interface with one implementer and no near-term second gets
  deleted; revisit when the second arrives.
- **R7.5 — Comments stay ≤ 3 lines.** Explain *what + why*, not the obvious. If it needs more, the
  code should be clearer or the explanation belongs in a doc/docstring.

## 8. Dependencies

- **R8.1** — Each adapter is self-contained with its own runtime/manifest (`composer.json`,
  `package.json`, `.csproj`) and documents how it is launched (`CA_<LANG>_CMD`). Adapter deps never
  leak into the Python core.
- **R8.2** — Keep core dependencies minimal (FastMCP + stdlib-first). Add one only when it earns its
  place; prefer the standard library and SQLite features.
- **R8.3 — An adapter's dependencies are pinned by a committed lock file** (`composer.lock`,
  `package-lock.json`, `packages.lock.json`); only the resolved artifacts (`vendor/`,
  `node_modules/`) are ignored. A floating range lets two machines resolve different parser builds
  and emit different rows from the same file, which R4.2 forbids.

---

**Quick self-check before opening a PR:** Does the core have any language branch? Does an adapter
mention a repo or framework by name? Did the contract change without a version bump + conformance
update? Is there a test? Is it the smallest change that ships value? Are the related docs updated to
match the work (PLAN / BACKLOG + task frontmatter / CONVENTION / this file / README)? If any answer
is wrong, fix it before review.
