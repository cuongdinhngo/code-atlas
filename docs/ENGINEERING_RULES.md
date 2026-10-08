# Engineering Rules — code-atlas

The **how we build** rules, binding for humans and AI agents. Companions:
[`CONVENTION.md`](CONVENTION.md) (naming/style), [`PLAN.md`](PLAN.md) (design), and
[`LESSONS.md`](LESSONS.md), which holds the evidence, the recurrence count and the ticket sightings
behind every rule here.

When a rule and a deadline conflict, raise it — don't quietly break the rule.

A rule's closing italic line names its **handle** and the `LESSONS.md` claims it was promoted from —
the two things `/mango:promote` greps to know the class is already carried — plus its status:
`Ratified <date>` once a human has confirmed the wording, or `Provisional` while it binds and awaits
that. A rule is ratified at recurrence ≥ 2 — except **R2.4**, `Provisional` on one incident because
its second sighting would cost a disclosure.

---

## 1. Architectural boundaries (SOLID at the seams)

The only axis of change we design for is **languages**, and it is expressed through **one** seam —
the adapter contract. Everywhere else, prefer the simplest thing that works.

- **R1.1 — Zero language branches in the core.** No `if language == "php"`, or any per-language
  switch, anywhere under `code_atlas/`. Such a branch means the contract leaked; fix the contract,
  not the core. *CI grep-gates this.*
- **R1.2 — One seam only (YAGNI).** The adapter contract is the sole abstraction: no plugin
  registry, base classes, factories or DI container. **Verdict: NO registry** (019, task 156) — the
  019 core diff was empty, adapters being selected from data, and #3/#4 needed none either.
  Mechanism and evidence: PLAN §19.
- **R1.3 — Dependency direction is one-way.** The core depends on the **contract**, never on a
  concrete parser (`nikic`, Roslyn, ts-morph); adapters depend on nothing in the core. The genuine
  inversion boundary is the **JSON contract + subprocess protocol**, not a Python base class.
- **R1.4 — SRP per component.** One reason to change each: adapters *parse only* (never touch
  SQLite); `store.py` *persists and queries only*; `enrichment.py` *applies optional rule-file edges
  only*; `resolver.py` *links edges only*; `tools/` *presents only*. **Parsing code and storage code
  must never import each other.**
- **R1.5 — Substitutability (LSP).** Every adapter is interchangeable behind the contract: same
  node/edge vocabulary, same guarantees. R1.1 is the litmus test — no branch keys on which language
  it is.
- **R1.6 — Optional power via capability flags (ISP).** Richer data (e.g. Roslyn's
  `semantic_types`) is advertised as a capability the core *may* use, never a method every adapter
  must implement. The core degrades gracefully when it is absent.
- **R1.7 — Add a sibling key; never loosen a coercing reader.** When a persisted blob is read
  through an accessor that coerces types, a datum of a different shape goes on its **own** meta key
  beside it, never inside the coerced structure: widening the accessor trades a total, checkable
  contract for a conditional one, and every existing consumer inherits the looser type. *Falsifier:*
  a non-int inside the census structure, or a coercion relaxed instead of a sibling key added.
  *Ratified 2026-08-30 · `sibling-meta-non-int` (`095-C2`).*
- **R1.8 — One decision, one implementation across every consumer.** When two or more call sites
  branch on the same classifier/resolver verdict (e.g. `status == "resolved_unique"`), the branch
  lives in one shared callable they all invoke; a new subject slot reuses it rather than
  re-implementing it — duplicated copies drift and one goes wrong. *Falsifier:* two sites branching
  on the same classifier status with duplicated handling instead of a shared call.
  *Ratified 2026-08-30 · `one-rule-for-every-subject-slot` (`102-C2`).*

- **R1.9 — A single-answer classifier is not a membership test.** A classifier that returns **one**
  verdict per subject by taking the deepest or best match — `responsibility_layer` is deepest-wins —
  answers *"which category is this?"*, never *"does this belong to category X?"*: an earlier segment
  that disqualifies the subject is invisible to a predicate reading only the deepest match, so
  `tests/controllers/*` reads as an entry point and `vendor/x/lib/` as a shared library. Membership
  is an **any-segment** predicate, reused where one already exists (`layers.reading_seed_rank`)
  rather than re-derived, and the classifier itself is left alone. *Falsifier:* a bucket, seed or
  filter whose truth is `responsibility_layer(...) == <layer>`.
  *Ratified 2026-08-31 · `deepest-wins-is-not-a-membership-test` (`197-C1`, seen 130, 131, 197).*

## 2. Standard over sample

- **R2.1** — Adapters implement the **language specification + ecosystem standards** (for PHP: full
  8.5 grammar, namespaces, PSR-4/PSR-0, traits, enums, attributes, closures, first-class callables,
  the global namespace, `include`/`require`). Nothing else.
- **R2.2** — Adapters must **never** encode a specific repo's directory names, class-naming habits,
  or framework. *CI grep-gate bans repo/framework names in adapter source.*
- **R2.3** — Sample repos drive **test coverage and performance targets only**, never adapter
  semantics. If a fact about a repo would change adapter behaviour, it belongs in the language spec
  or nowhere.
- **R2.4 — No private repo's identifiers in any tracked file**, `docs/` and fixtures included,
  where R2.2's source-only scope let them collect. Use a shape-preserving stand-in, never the real
  name. Gated by `tests/test_no_client_identifiers.py`, matching vocabulary **by digest** (a
  plaintext denylist is the disclosure); commit identities by `scripts/identity_markers.py` (340).
  *Falsifier:* a client's name in any tracked file or commit identity, or a denylist that spells
  one out. *Provisional 2026-09-23 · `de-identification-is-tree-wide` (325).*

## 3. The contract is a frozen, versioned artifact

- **R3.1** — A change to node/edge vocabulary, fields, or the qname convention requires a
  `contract_version` bump and a conformance-test update in the same change; that bump, or a
  `SCHEMA_VERSION` one, cuts a release — version plus a CHANGELOG entry flagging the rebuild
  (`tests/test_release_discipline.py`).
- **R3.2** — `contract.py` is the single source of truth for the schema. Store, indexer and tools
  import from it; they never re-declare field lists.
- **R3.3** — Adapters emit **bare** edges (targets as raw FQNs/names); cross-file linking is the
  core resolver's job. A single file can't know all targets — don't pretend it can.
- **R3.4** — Every adapter must pass `tests/contract/` before it is considered to exist. That test
  *is* the substitutability guarantee.

- **R3.5 — One version constant per document; bump the one whose shape moved.** Each version
  constant guards exactly **one** published document — `contract_version` the contract,
  `DATASET_VERSION` `manifest_dict`, `ARTIFACT_VERSION` `OnboardingArtifact.as_dict()` — and a new
  key on a shape bumps *that* shape's constant, never a neighbour's. This generalises R3.1 to the
  documents it does not name: a new key **is** a shape change, so it moves a version even when no
  vocabulary did. *Falsifier:* a bump on a constant whose document did not change, or a new key on a
  published shape with no bump.
  *Ratified 2026-08-31 · `version-the-document-that-moved` (`197-C2`, `196-C5`).*

## 4. Determinism & purity of the core

- **R4.1 — No LLM or network calls in the core.** Ever. LLM enrichment lives only in the Phase-3
  onboarding layer: *deterministic graph → LLM enrichment → presentation.* In practice that means
  **outside `code_atlas/`** — the implementers live in `onboarding_llm/`, are injected through
  Protocol seams, and are off by default. *CI grep-gated* (R6.4).
- **R4.2 — Identical input → identical output.** The same repo state produces identical rows: no
  wall-clock, randomness or set-ordering leaking into stored data. An incremental update for a state
  must equal a full rebuild of that state.
- **R4.3 — Single SQLite writer.** Concurrency is in parsing (N adapter workers), not in writing.
  WAL, indexed queries, bounded traversal in SQL — never load the whole graph into memory.

## 5. Error handling & degradation

- **R5.1** — A syntax error in one file returns `ok:false` for that file and never breaks the stream
  or the build: set `parsed_ok=0` and keep going. This holds for a bad *store write* too — a legal
  duplicate declaration is de-duped keep-first and, failing that, soft-fails that one file; it never
  aborts the build (043).
- **R5.2** — Unresolvable-but-static references are `HEURISTIC`; dynamic constructs (`$obj->$m()`,
  variable includes) are `DYNAMIC` and excluded from traversal by default. Never silently link a
  guess as `RESOLVED`. A name resolving to **one qname declared in several files** is not a guess —
  link it once at `RESOLVED` and let the `nodes` rows carry the per-file detail (046).
  **Multiplicity is not ambiguity.**
  **The tier answers one question: how sure you are of the TARGET.** The resolver skips `DYNAMIC`
  outright, so a tier chosen to carry any other distinction — how complete a statement was, which arm
  produced it — does not degrade the edge, it removes it from the graph. Carry that distinction in
  the target's node kind or a new edge kind. *Falsifier:* a `DYNAMIC` edge whose `target_raw` is a
  resolvable qname. *Ratified 2026-08-30 · `skip-dynamic-means-unlinkable` (`094-C1`, `022-C2`).*
- **R5.3** — Fail loud on *config/programmer* errors (bad `CA_*`, missing adapter command); fail
  soft on *data* errors (one weird source file). Don't confuse the two.
- **R5.4 — A field the reader acts on holds one register; prose gets a sibling field.** Where a
  payload field carries a value the reader is meant to *execute* — a route, a tool name, an
  identifier — **every** value must be machine-checkable as that kind, and the *how to re-ask*
  qualifier goes in a named sibling (`try_instead` / `try_instead_hint`). One prose value makes the
  whole field ambiguous, not just itself. A route must (a) be a member of a registry **derived from
  code**, (b) never name the tool that is answering — a self-route loops for the mechanical reader
  the field exists for — and (c) be able to answer the question that caused the miss. **Where no
  registered tool can, emit the hint and no route:** naming a tool that cannot answer is worse than
  naming none. *Falsifier:* a route constant outside the registry; an emitter whose `try_instead`
  equals its own tool name; or a routed tool that returns `reason: ok` while the thing sought is
  still absent.
  *Ratified 2026-08-30 · `try-instead-tool-name` (`093-C1`) · clause (c) `route-must-answer` (`093-C4`).*
- **R5.5 — A reported value is sourced from the computation that owns the whole fact.** When a
  surface — a payload field, a signed claim line, a summary — reports a count or a caveat, read it
  from the computation owning the **entire** fact the field names, never from a producer narrower
  than the field's documented meaning. Two shapes recur: the source carries the value only at some
  **detail levels**, or computes it only for some of the **cases** the field's name covers. Both ship
  a value honest about its source and false about its subject. *Falsifier:* producers, enumerated by
  grep, covering fewer cases than the field's name or docstring claims — or a caveat present at one
  detail level and absent at another for the same underlying fact.
  *Ratified 2026-08-30 · `source-the-caveat-from-the-computation` (`100-C1`).*
- **R5.6 — Never attest past what the payload can distinguish.** When a field cannot separate two
  states a reader acts on differently — absent subject vs modelled zero, budget-cut walk vs complete —
  carry a field that separates them or emit no signed line/label for that answer; never sign a value
  the payload cannot tell apart. Prove it with a test driving both states. *Falsifier:* a count/flag identical
  across the two states with no separating field, or a test asserting only one.
  *Ratified 2026-08-30 · `do-not-attest-past-the-payloads-resolution` (`100-C4`, `087-C2`, `088-C2`).*
- **R5.7 — A repo-writing tool removes only what its own manifest recorded.** Before deleting or
  overwriting a tree, read the recorded page list and remove exactly those, refusing foreign paths
  (`..`, absolute, outside the managed subdir) rather than unlinking them — the rule that guards the
  index database guards on-disk artifacts too. *Falsifier:* a tool that rmtrees/overwrites a directory
  without consulting its manifest, destroying a hand-written or foreign file.
  *Ratified 2026-08-30 · `own-only-what-you-wrote` (`088-C1`).*
- **R5.8 — Rank inside the statement that truncates.** Wherever a page is cut — a tool payload or a
  rendered artifact — the ordering that decides which rows matter is applied in the same statement
  that applies the limit. A rank computed a layer above the cut lets page 1 hold none of the rows the
  ranking exists to surface. *Falsifier:* a paged payload whose `ORDER BY` differs from the order it
  reports ranking by. *Ratified 2026-08-30 · `rank-before-truncate` (`126-C1`).*

## 6. Testing (definition of done)

- **R6.1** — No task is done without tests. Minimum bar per area: adapter change → a fixture +
  conformance assertion; resolver/store/indexer change → an integration test asserting resolved
  rows; tool change → a test over a fixture repo.
- **R6.2 — Spec-driven fixtures, not repo-driven.** An adapter **names its construct inventory before
  its first fixture**, or the fixture is drawn from whatever repo is open (task 149). The inventories
  are **data**, not prose here: `<LANG>_R62_CASES` in `tests/contract/adapter_registry.py`, which the
  conformance keys must equal — re-listing them in this file is the drift R6.7 forbids. Two things the
  data cannot carry: a construct with **two spellings reaching the walk by different paths** needs
  both as cases (`019-C2`, `184-C3`, `022-C4`); and an adapter with **no syntax-error case** says
  why in its README.
- **R6.3 — Cross-repo validation** proves "works on any repo": several varied repos index without
  crashes and with sane counts. No single repo defines "correct".
  **And where an acceptance criterion needs a judgement about a real repo — a threshold, a ranking,
  an elected group, a ratio — that judgement ships as a committed, re-runnable reporter, not an
  ad-hoc session run.** An authored fixture mirrors the assumption the code already makes, so it
  cannot exhibit the shape that breaks it, and a pinned suite can be green on both sides of a real
  defect. The reporter prints the real inputs the constant was chosen from, so the constant can be
  re-justified whenever a pin moves; `scripts/layer_report.py` and `scripts/mirror_report.py` are
  what compliance looks like. *Falsifier:* an acceptance-criterion threshold, ranking or elected
  group whose only evidence is a fixture or a session transcript, with no committed reproducer.
  *Ratified 2026-08-30 · `fixture-shape-begs-the-question` (`105-C2`).*
- **R6.4 — Guardrail tests are real tests.** The three grep-gates (R1.1 no language branches in
  core; R2.2 no repo/framework names in adapters or core; R4.1 no prompt/model id/LLM import in
  core) run in CI and fail the build, beside two commit-range scripts: R7.3 attribution and R2.4
  commit identity (`scripts/{attribution,identity}_markers.py`). R2.4's tree sweep stays pytest.
- **R6.5 — A guard ships only once it has been observed failing, and a sweep is guarded against
  emptying itself.** Every grep-gate or file sweep excludes vendored trees (`vendor/`,
  `node_modules/`), and **the exclusion needs its own test asserting the sweep is still non-empty** —
  a filter that swallows the authored files restores the 0/0 vacuity the guard existed to remove.
  **This generalises to every guard:** run it against the shape it forbids (the pre-fix code, a
  sabotaged input, an injected invalid member) and record the red run. *Falsifier:* a guard test
  whose PR claims a defect class is prevented with no recorded red run.
  **The gate itself is bound by this rule** — `scripts/gate.sh` exits **2** on a skipped check and a
  skip is never a pass; the rest is AGENTS.md *Before a PR or a push*.
  *`prove-the-guard-fails` (`093-C3`).*
- **R6.6 — Every language gets a static analyser in CI, at its strictest clean setting.** The core
  has `mypy`; the PHP adapter has **PHPStan at `level: max`**, and each later adapter brings the
  equivalent. Suppression is not how a finding is closed: no baseline file, no `@phpstan-ignore`, no
  inline `@var` override, no widened signature or cast added only to silence a rule. Either fix the
  code or argue the level down in this rule book, where the argument is reviewable. `php -l` does
  **not** satisfy this; it catches syntax, not types.
- **R6.7 — A guard that needs "every valid X" derives the set; it never lists it.** Where a test or
  a payload needs the set of all valid members — tool names, ignore-source keys, reason codes — it
  derives that set from the definition site (a module namespace, a registry, the composition that
  builds it) rather than re-typing the members. A hand-kept list is precisely what drifts when member
  N+1 arrives, and it drifts **silently**, because the guard still passes. *Falsifier:* a literal
  list of valid members inside a test or tool where a derivation was available, or a new member that
  ships without failing any guard.
  **A text sweep is not a derivation.** A guard deciding a fact about source reads the source's
  grammar (`ast.walk`, a parser); a substring or regex sweep derives from the wrong grammar and
  matches comments, docstrings and prose. *Falsifier:* a guard deciding a source fact from
  `read_text()` plus a pattern where a parse was available.
  *Ratified 2026-08-30 · `derived-not-listed-invariant` (`093-C2`, `095-C1`, `097-C1`) ·
  `read-the-syntax-not-the-text` (`187-C1`, `192-C3`).*
- **R6.8 — An AC phrased as a failure mode needs a guard that can exhibit it.** Close a "would fail
  if X" AC with a test that reaches X and is seen failing (R6.5); if the code structurally cannot
  reach X, name the different boundary the test really guards and split the claim. Run it against a
  repo/fixture that still exhibits the failure, not one a prior ticket cleaned. *Falsifier:* a
  failure-mode AC closed by a test that passes without reaching the failure, or run where it cannot
  occur. *Ratified 2026-08-30 · `ac-failure-mode-needs-the-right-guard` (`085-C2`).*
- **R6.9 — A guard asserts at the CONSUMER, not at the producer.** Where content is produced by a
  renderer, assert what the renderer produces, never the artifact's bytes: a grep over a page built
  in the browser is green by construction and cannot see the drop. **The same holds one step
  earlier — a field added for a reader is not delivered until a reader reads it:** assert the
  consumer, not the field, or the field ships populated, serialized and correct while every renderer
  still prints the old one, and guarding against this class is not immunity to it. *Falsifier:* a
  test asserting on artifact bytes for content a renderer emits, or a new field whose only
  assertions are on its own value with no consumer named.
  *Ratified 2026-08-30 · `guard-asserts-rendered-not-shipped-bytes` (`127-C1`) · widened 2026-08-31 ·
  `assert-the-consumer-not-the-field` (`198-C1`, `196-C4`, `196-C8`).*
- **R6.10 — A test's child build gets an env with `CA_*` stripped, never `os.environ`.** A host's
  `CA_<LANG>_CMD` widens its scope past the parent's. *Falsifier:* a build spawned from `tests/`
  with `env=os.environ` or no `env=`. *Ratified 2026-10-08 · `child-build-inherits-adapter-env` (`356-C1`).*

## 7. Change discipline

- **R7.1 — Ship the smallest useful thing**; don't gold-plate before it is usable.
- **R7.2 — Keep the plan and backlog honest, cost included.** A design decision updates the
  [plan](PLAN.md); an **open** task's status updates both [`BACKLOG.md`](BACKLOG.md) and the task
  file's frontmatter. **And the spend is part of the status:** before a PR opens, the task's token
  spend goes in its working-doc cost ledger **and** in [`TOKEN_LEDGER.md`](TOKEN_LEDGER.md). A
  finished task whose cost is unrecorded reads as free, and a project that cannot say what a ticket
  cost cannot argue about where its effort goes. **A task that reaches `done` leaves BACKLOG in the
  same commit that records its spend** (218) — the ledger row carries it from then on, so the closed
  ticket is named twice, not three times (R7.6). *Falsifier:* a task at `done` with no Token-usage
  row, an open task whose two statuses disagree, or a `done` row still in BACKLOG — all guarded by
  `tests/test_backlog_bookkeeping.py`.
- **R7.3 — Small, reviewable commits** with imperative messages and no AI-attribution trailer. One
  logical change per commit.
- **R7.4 — No dead abstractions.** An interface with one implementer and no near-term second gets
  deleted; revisit when the second arrives.
- **R7.5 — Comments stay ≤ 3 lines.** Explain *what + why*, not the obvious. If it needs more, the
  code should be clearer or the explanation belongs in a doc/docstring.
- **R7.6 — A standing document is pruned by the change that adds to it.** Every file on AGENTS.md's
  **tier 1** list is read before non-trivial work, so a line added to one is charged to every future
  session, and the sum is capped by `tests/test_agent_chain_budget.py`; `PLAN.md` is tier 2 and still
  ceilinged, because a `§`-ref pulls it in. A change that adds **removes what it supersedes in the
  same commit**, and never restates what a task file, a `LESSONS.md` entry or a `benchmarks/` file
  already holds. **Session narrative is not a decision** — record the decision and the number that
  binds it, and leave the story where it happened. R7.2 keeps these documents *honest*; this one
  keeps them *readable*. *Falsifier:* a standing doc over its ceiling in
  `tests/test_doc_size_budget.py`, or a diff that appends narrative to `PLAN.md` §19 or `BACKLOG.md`
  while removing nothing it supersedes.
- **R7.7 — Revert every hunk `ruff format` rewrites outside the lines you edited;** the gate runs
  `ruff check` only. *Falsifier:* a layout-only hunk outside the change list.
  *Ratified 2026-10-08 · `formatter-rewrites-untouched-lines` (`343-C2`).*

## 8. Dependencies

- **R8.1** — Each adapter is self-contained with its own runtime/manifest (`composer.json`,
  `package.json`, `pyproject.toml`) and documents how it is launched (`CA_<LANG>_CMD`). Adapter
  deps never leak into the Python core.
- **R8.2** — Keep core dependencies minimal (FastMCP + stdlib-first). Add one only when it earns its
  place; prefer the standard library and SQLite features.
- **R8.3 — An adapter's dependencies are pinned by a committed lock file** (`composer.lock`,
  `package-lock.json`); only the resolved artifacts (`vendor/`, `node_modules/`) are ignored. A
  floating range lets two machines resolve different parser builds and emit different rows from the
  same file, which R4.2 forbids. A zero-dependency adapter commits no lock; it pins the
  *grammar* instead, refusing to run on an older runtime (Python, 217).

---

**Quick self-check before opening a PR.** Does the core have any language branch? Does an adapter
name a repo or framework? Did the contract change without a version bump + conformance update? Is
there a test, and was it seen failing? Is it the smallest change that ships value? Are the affected
docs updated — and did the change **prune what it superseded** rather than only append (R7.6)? If any
answer is wrong, fix it before review.
