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
  - `enrichment.py` *applies optional rule-file edges only* (never parses source; never owns SQL),
  - `resolver.py` *links edges only*,
  - `tools/` *presents only*.
  **Parsing code and storage code must never import each other.**
- **R1.5 — Substitutability (LSP).** Every adapter is interchangeable behind the contract: same node/edge
  vocabulary, same guarantees. The litmus test is R1.1 — no branch anywhere keys on which language it is.
- **R1.6 — Optional power via capability flags (ISP).** Richer data (e.g. Roslyn's `semantic_types`) is
  advertised as a capability the core *may* use, never a method all adapters must implement. The core
  degrades gracefully when a capability is absent.

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
  restores the 0/0 vacuity the guard existed to remove.
- **R6.6 — Every language gets a static analyser in CI, at its strictest clean setting.** The core has
  `mypy`; the PHP adapter has **PHPStan at `level: max`** (`adapters/php/phpstan.neon`), and each later
  adapter brings the equivalent for its language. Suppression is not how a finding is closed: no
  baseline file, no `@phpstan-ignore`, no inline `@var` override, no widened signature or cast added
  only to silence a rule. Either fix the code or argue the level down in the rule book — where the
  argument is reviewable. `php -l` does **not** satisfy this; it catches syntax, not types.

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
