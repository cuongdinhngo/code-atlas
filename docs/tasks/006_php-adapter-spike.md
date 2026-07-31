---
id: 006
slug: php-adapter-spike
title: PHP adapter spike (M0)
phase: 1
milestone: M0
status: in-progress
depends_on: [002]
---

## Goal
Prove nikic/php-parser emits valid contract JSON for real PHP (§6, §7).

## Scope / Deliverables
- `adapters/php/`: `composer.json` (nikic/php-parser ^5), `index.php` (`--file` mode), `src/Visitor.php`.
- Parse with `createForNewestSupportedVersion()` (8.5) + `NameResolver` for FQNs.
- Emit contract nodes/edges for at least: a namespaced file **and** a global/underscore (PSR-0) file.

## Acceptance criteria
- `php index.php --file <namespaced>.php` and `<global-underscore>.php` each produce schema-valid JSON.
- FQNs resolved (`\Ns\Class::method`); global/underscore names handled as first-class.

## References
Plan §6, §7, §15 (M0).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Working doc — 006 PHP adapter spike

`work_doc_mode: embed` (local-file ticket) · working doc path: `docs/tasks/006_php-adapter-spike.md`
(this file, below the separator). Raw ticket stays above the separator — that separation is what keeps
the review-phase challenger blind.

---

## Phase 1 — Analysis

### Counted artifacts

```
STRUCTURE: native
SECTIONS: 4 found (Goal, Scope / Deliverables, Acceptance criteria, References) | 4 decomposed
ROWS: C=1  R=3  G=1  AC=2      (7 rows)
INVENTORY N: 2 (the two fixture files AC1 says "each" of) — per-item checklist below
CLARIFICATION: 9 raised | 6 self-resolved (cited) | 3 for human decision — all 3 RATIFIED, Gate 0 clear
BASELINE: green — 237 passed, 1 skipped (5.96 s); ruff clean; mypy clean (11 source files)
TRACK: backend — 0/N touched files under UI paths (config.track = "backend"; no UI exists)
SCOPE: M
TIER: full
```

**Baseline note (read this at review).** The 1 skip is
`tests/test_sql_confinement.py::test_no_adapter_source_reaches_into_the_core`, which skips itself while
`adapters/` holds no source (`tests/test_sql_confinement.py:51`). **This ticket is what un-skips it** —
so the post-change expectation is `0 skipped`, and a skip that *survives* means the adapter source did
not land where the guard looks. That is a baseline *change*, not baseline drift.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | Goal | "Prove nikic/php-parser emits valid contract JSON for real PHP (§6, §7)." | An M0 **spike**: de-risk the parser choice, not ship the language. "Valid" = `contract.validate() == []` **and** a non-vacuous result (see AC1 pinning). | Spike S4 — a hand-built PHP-shaped result validates clean; a planted bad kind is rejected | ✅ |
| R1 | Scope | "`adapters/php/`: `composer.json` (nikic/php-parser ^5), `index.php` (`--file` mode), `src/Visitor.php`." | Three authored files in a new self-contained adapter dir (R8.1). `--file` only; `--server` is task 007. | Dir is empty but for `adapters/ok.gitkeep`; layout fixed by CONVENTION §1 | ✅ |
| R2 | Scope | "Parse with `createForNewestSupportedVersion()` (8.5) + `NameResolver` for FQNs." | Exact factory call + the `NameResolver` visitor ahead of ours in the traverser. | Spike S2: `^5` → **v5.8.0**, `getNewestSupported()` = **80500**; S3: NameResolver resolves both fixture shapes | ✅ |
| R3 | Scope | "Emit contract nodes/edges for at least: a namespaced file **and** a global/underscore (PSR-0) file." | The floor is **breadth of file shape**, not breadth of construct — full construct coverage is 007. N = 2. | Spike S3 produced the node/edge material for both shapes | ✅ |
| AC1 | Acceptance | "`php index.php --file <namespaced>.php` and `<global-underscore>.php` each produce schema-valid JSON." | Per-item over N=2. Pinned below — bare `contract.validate()` alone passes vacuously on `ok:false`. | Spike S4 + the AC-validation table | ✅ |
| AC2 | Acceptance | "FQNs resolved (`\Ns\Class::method`); global/underscore names handled as first-class." | Two clauses, one assertion each. Exact expected qnames computed below. | Spike S3 — and it found the leading-`\` gap (F1) | ✅ |
| C1 | References | "Plan §6, §7, §15 (M0)." | §6 = the language standard, **not** any repo (R2.1–R2.3); §7 = the visitor sketch; §15 = M0, so smallest-useful (R7.1). | `docs/PLAN.md:182`, `:214`, §15 | ✅ |

### Universal inventory — AC1 "each", N = 2 (per-item, not an aggregate)

Review must confirm **every** row; a "2/2" total is not enough.

| # | Item | What must hold | Ph3/4 proven by |
|---|---|---|---|
| 1 | namespaced fixture | stdout is one JSON object; `validate() == []`; `ok is True`; `nodes` non-empty; qnames carry the namespace | *(execute)* |
| 2 | global/underscore fixture | same, and the qnames carry **no** namespace segment while keeping their underscores | *(execute)* |

### AC validation — every value re-derived independently

| AC value | Ticket says | Computed (evidence) | Falsifiable? | Verdict |
|---|---|---|---|---|
| parser constraint | `nikic/php-parser ^5` | resolves to **v5.8.0** under host PHP 8.3.6 (spike S1) | ✅ `composer show` | match |
| newest supported version | `createForNewestSupportedVersion()` **(8.5)** | `PhpVersion::getNewestSupported()->id` = **80500** (spike S2) | ✅ asserted integer | **match** |
| 8.5 grammar actually parses | implied by "(8.5)" | pipe `\|>`, `clone with`, `#[\NoDiscard]`, const attributes, asymmetric visibility, property hooks — **all 6 parse** (spike S2) | ✅ parse/throw | match |
| host runtime | PLAN §9 recommends installing PHP 8.5 CLI | host is **8.3.6** — and it does not matter: php-parser is pure PHP and parses 8.5 grammar on an 8.3 runtime (spike S2) | ✅ same probes | self-resolved, not a mismatch |
| AC1 "schema-valid JSON" | undefined term | **pinned**: `contract.validate(json.loads(stdout)) == []` **AND** `ok is True` **AND** `len(nodes) > 0`. Bare `validate()` is *not* enough — `{"path": p, "ok": false, "error": "…"}` is schema-valid, so an adapter that parses nothing would pass the AC as literally written. The Goal ("emits valid contract JSON for real PHP") is what forbids that reading. | ✅ three assertions | **strengthened** |
| AC2 namespaced qnames | `\Ns\Class::method` | `\App\Models\User`, `\App\Models\User::save`, `\App\Models\helper`, `\App\Models\User::$name`, `\App\Models\User::ROLE` — **note the leading `\`**, which NameResolver does *not* emit (finding F1) | ✅ exact strings | match, with F1 |
| AC2 global/underscore | "first-class" (vague) | **pinned**: `\Foo_Bar_Baz`, `\Foo_Bar_Baz::fetchRow`, `\foo_helper`; ≥1 `Class` node whose qname has an `_` and no namespace segment; its `EXTENDS`/`NEW` targets keep their underscores | ✅ exact strings | **pinned** |
| inventory denominator | "each" of two files | **N = 2** | ✅ counted | match |

No AC carries a bare `✅`: every one is falsifiable, and none needed a manual-check exclusion.

### Spikes (read-only, run before any design commitment)

| # | Question | Result |
|---|---|---|
| S1 | Is packagist reachable and what does `^5` resolve to? | Yes. **v5.8.0**, installs clean under PHP 8.3.6 / Composer 2.7.1 |
| S2 | Does `createForNewestSupportedVersion()` really mean 8.5, on an 8.3 host? | Yes — id **80500**, `Parser\Php8`; all six 8.4/8.5 grammar probes parse |
| S3 | What exactly does `NameResolver` hand the visitor, for both fixture shapes? | See findings F1–F7 |
| S4 | Would a plausible emitted result pass `contract.validate()`? | **Yes, zero errors** — and a planted `kind: "Klass"` is rejected (negative control) |
| S5 | What does `composer install` drop into `adapters/php/`? | 280 `.php` files under `vendor/`, and **`vendor/composer/ClassLoader.php` contains "Symfony"** — see F8 |

**F1 — NameResolver emits FQNs with *no* leading backslash.** `namespacedName` → `App\Models\User`,
`Name_FullyQualified::toString()` → `App\Models\Base`. CONVENTION §3 spells the qname `\Ns\Class`.
**The adapter must prepend `\` itself**; PLAN §7's sketch does not say so.
**F2 — global/underscore needs no special case.** `Foo_Bar_Baz` → `namespacedName` `Foo_Bar_Baz`;
`Zend_Db_Table`-shaped parents resolve fully-qualified with underscores intact. PSR-0 *path* mapping is
a resolver concern (§8.2), never a parse-time one — so "first-class" costs zero extra code.
**F3 — `namespacedName` is set on declarations only** (`Stmt_Class`, `Stmt_Function`), not on
`ClassMethod`/`Property`/`ClassConst`. Members carry a bare `Identifier`, so the adapter joins
`container::member` itself (`contract.MEMBER_SEPARATOR`).
**F4 — a `use` statement's name arrives as a plain `Name`, not `Name_FullyQualified`** (`isFQ: false`),
because it already *is* the FQN. `IMPORTS` takes `toString()` + the `\` prefix.
**F5 — an unqualified type inside a namespace resolves to the current namespace** (`Repo` →
`App\Models\Repo`). Correct PHP semantics; the resolver will leave it NULL if nothing declares it.
**F6 — an instance `MethodCall` gives only the method name** (`put`), never a receiver type. That is
exactly the `HEURISTIC` tier of R5.2/§8.2 — bare edge, `target_raw: "put"`.
**F7 — a namespaced free function is `\App\Models\helper`**, matching the `\ns\func` convention.
**F8 — the R2.2 grep-gate false-positives on Composer's own autoloader.**
`grep -rEin 'laravel|symfony|wordpress|drupal|magento' adapters/` matches
`vendor/composer/ClassLoader.php:21` ("Symfony\Component" in a docblock). The gate and the
`tests/test_sql_confinement.py` adapter sweep both scan the filesystem, so **the first `composer install`
turns a green guardrail red for a reason that has nothing to do with our source**. Both must be scoped
to *authored* adapter files. This ticket creates the collision, so this ticket fixes it.

### Clarifications

**Self-resolved (6), each cited:**
1. *Does `--file` also print the handshake line?* **No.** AC1 says the invocation "produce**s** schema-valid
   JSON" — a handshake plus a result is two JSON documents and would fail a whole-stdout `validate()`.
   The handshake belongs to `--server`, which is task 007 (`docs/CONVENTION.md:89`, `docs/PLAN.md:88`).
2. *How are `modifiers` / `params` / `extra` typed on the wire?* Native JSON structures. `store.stored()`
   canonicalises any non-scalar to sorted-key JSON before it reaches the TEXT column
   (`code_atlas/store.py:101`), so the adapter emits arrays/objects, not pre-serialised strings.
3. *Must the spike decide `is_test`?* No — it is an optional field (`contract.REQUIRED_NODE_FIELDS`) with
   a DDL default of 0 (`docs/PLAN.md:271`). Omit it; the policy (which would otherwise mean naming a test
   framework, R2.2) belongs to 007.
4. *Fixture naming.* Fixtures must **not** use `Zend_*` or any framework/repo name even in the
   underscore case — R2.2/R2.3 (`docs/ENGINEERING_RULES.md:43`) bind the *standard*, and the sample
   monorepo's `Zend/` directory is a validation sample, not a design input. Neutral names only
   (`Foo_Bar_Baz`, `Legacy_Registry`). Fixtures live in `tests/fixtures/php/` (`docs/CONVENTION.md:32`).
5. *Is `adapters/php/README.md` in scope, given the ticket lists only three files?* Yes. CONVENTION §5
   (`docs/CONVENTION.md:95`) and R8.1 both require an adapter to document its runtime and its launch in
   an adapter-local README. It gets its own matrix trace so no hunk is untraceable (LESSONS 001).
6. *Which host PHP?* 8.3.6 is fine — spike S2 proved parseable grammar is a property of php-parser, not
   of the runtime. PLAN §9's "install 8.5" is an indexing-performance recommendation, not a gate.

**For human decision (j = 3) — Gate 0, all three RATIFIED** under the session's standing
authorization ("do what is best for the project; stop asking per action"). Each is recorded with its
reasoning so a later reader can overturn it on the argument, not on the outcome.

**Q1 — Is the AC proven in CI, or only where PHP happens to be installed? → RATIFIED: prove it in CI.**
`ci.yml` gains a PHP setup + `composer install` step for `adapters/php/`, and the proving test skips
only when PHP is genuinely absent (a developer laptop). *Why:* the alternative — skip-when-absent with
a coverage-gap exclusion — makes this ticket's only proof unrunnable on the one machine that gates the
merge, which is precisely the vacuity LESSONS 002 was written about. Tasks 007, 008, 012 and 015 all
need the same step, so it is paid once here rather than four times later. *Cost:* ~10 lines of workflow.

**Q2 — `composer.lock` is gitignored (`.gitignore:20`). Commit it? → RATIFIED: commit it.**
Remove the ignore and check the lock in. *Why:* R4.2 is "identical input → identical output", and a
floating `^5` means CI and a developer machine can resolve different php-parser builds and emit
different rows from the same file — the lock is the only thing that closes that. The
library-vs-application rule of thumb applies: this adapter is an application, not a package anyone
depends on. *Uncodified-standard nudge:* "pin adapter dependencies with a committed lock file" is **not**
in `ENGINEERING_RULES.md` today — flagged for `codify` provisional→ratify so the next adapter
(`package.json`, `.csproj`) inherits a rule rather than a precedent.

**Q3 — Does the adapter emit `File` nodes and `CONTAINS` edges, or does the indexer synthesize them?
→ RATIFIED: the adapter emits both.** *Why:* only the parser knows line spans and containment, and the
`files` *table* (path, hash, `parsed_ok` — task 009) is a different object from a `File` *node* (a graph
vertex an edge can point at). `File` and `CONTAINS` are both in the §4.2 vocabulary; a vocabulary entry
no adapter ever emits is a dead abstraction (R7.4). Deciding it in the spike means 007 and 009 inherit
the shape instead of relitigating it. *If this is wrong*, the cost is confined to the visitor.

### Rule-compliance section coverage

Change types present: **new adapter source (PHP)** · **new tests + fixtures** · **CI guardrail edit** ·
**docs**. No migration, no schema change, no UI surface — so no DB-conventions or design-token section
is triggered.

```
RULE SECTIONS: §1, §2, §3, §4, §5, §6, §7, §8 — each checked ✅ / N/A (reason)
```

| § | Rule | Verdict |
|---|---|---|
| 1 | R1.1 zero language branches in core | **N/A** — no file under `code_atlas/` is touched by this ticket |
| 1 | R1.2 one seam, YAGNI | ✅ no registry, no base class; one adapter, one dir |
| 1 | R1.3 adapters depend on nothing in the core | ✅ **and now provable** — this ticket un-skips `test_no_adapter_source_reaches_into_the_core` |
| 1 | R1.4 SRP — adapters parse only | ✅ no SQLite, no core import, no resolution |
| 1 | R1.5 / R1.6 substitutability, capability flags | **N/A** — one adapter, no optional capability advertised until `--server` (007) |
| 2 | R2.1–R2.3 standard over sample | ✅ **mandatory here.** Adapter + fixtures encode PHP/PSR only; the underscore fixture uses neutral names (clarification 4) |
| 3 | R3.1 contract bump | **N/A** — no vocabulary change; `CONTRACT_VERSION` stays 1 |
| 3 | R3.2 `contract.py` sole source | ✅ for Python. The PHP side necessarily restates the kind spellings across a process boundary — R3.2 binds store/indexer/tools, not another language's process. **Drift risk is real and is what `tests/contract/` (task 012) exists to catch**; recorded, not waved away |
| 3 | R3.3 bare edges | ✅ every edge carries `target_raw` only; `target_qname` is the resolver's (F6) |
| 3 | R3.4 every adapter passes `tests/contract/` | **N/A here, deferred to 012** — that harness does not exist yet; this ticket proves validity against `contract.validate()` directly |
| 4 | R4.1 no LLM/network in core | ✅ — `composer install` is a build-time step of a sidecar, not a core runtime call |
| 4 | R4.2 identical input → identical output | ✅ parse is pure. **But see Gate-0 Q2**: a floating php-parser version is the one thing that could break it across machines |
| 4 | R4.3 single writer | **N/A** — no DB access |
| 5 | R5.1 per-file soft failure | **N/A** — `ErrorHandler\Collecting` is task 007's deliverable |
| 5 | R5.2 confidence tiers | ✅ the instance call emits `HEURISTIC`, never a guessed `RESOLVED` (F6) |
| 5 | R5.3 fail loud on config errors | **N/A** — no config path touched |
| 6 | R6.1 no task done without tests | ✅ fixture + assertion, per the proving test named at design |
| 6 | R6.2 spec-driven fixtures | ✅ clarification 4 |
| 6 | R6.3 cross-repo validation | **N/A** — task 018 |
| 6 | R6.4 guardrail tests are real tests | ✅ **and this is the finding**: F8 shows the R2.2 gate goes false-red on `vendor/`, and the adapter-source guard would sweep 280 dependency files. Both get scoped to authored source |
| 7 | R7.1 smallest useful thing | ✅ `--file` only; no `--server`, no full construct coverage, no conformance harness |
| 7 | R7.2 keep plan/backlog honest | ✅ F1 (leading `\`) is a PLAN §7 correction; BACKLOG + frontmatter sync at finalise |
| 7 | R7.3 small commits, no AI trailer | ✅ |
| 7 | R7.4 no dead abstractions | ✅ one visitor class, no interface above it |
| 7 | R7.5 comments ≤ 3 lines | ✅ binding on the PHP source too |
| 8 | R8.1 self-contained adapter + documented launch | ✅ `composer.json` + adapter-local README (clarification 5) |
| 8 | R8.2 minimal core deps | **N/A** — no Python dependency added; PHP deps stay inside `adapters/php/` |

### Gap analysis (enhancement, not a bug)

| Goal | Current | Target | `path:line` |
|---|---|---|---|
| A PHP adapter exists | `adapters/` holds only `ok.gitkeep` | three authored files + a README under `adapters/php/` | `adapters/ok.gitkeep` |
| The contract is proven against a real parser | `contract.validate()` has only ever seen Python-authored dicts and a spec-driven fake (`tests/fixtures/adapter/fake_adapter.py`) | it validates output produced by nikic/php-parser from real PHP | `tests/fixtures/adapter/fake_adapter.py:1` |
| The "adapters never import the core" guard is real | skipped, 0/0, vacuous | asserted over real adapter source | `tests/test_sql_confinement.py:51` |
| Guardrails survive a vendored dependency | untested — no adapter has ever had one | R2.2 gate + adapter sweep scoped to authored files | `.github/workflows/ci.yml:59`, `tests/test_sql_confinement.py:47` |

### Blast radius

**Entry point:** none in the core. This ticket adds a *new process*, and changes **no** module under
`code_atlas/`. Repos touched: 1 (`app`, root `.`). No `db-map`, no migrations, no schema dependents.

Collateral the change list must carry (traced now so the diff does not exceed the approved list):

| # | File | Why it is in the blast radius |
|---|---|---|
| 1 | `tests/test_sql_confinement.py:44` | its skip flips to a live assertion, and it will otherwise sweep 280 `vendor/` files (F8) |
| 2 | `.github/workflows/ci.yml:59` | R2.2 gate false-positives on `vendor/composer/ClassLoader.php` (F8) |
| 3 | `.gitignore:19` | `adapters/php/vendor/` already ignored; `composer.lock` is too — Gate-0 Q2 |
| 4 | `docs/PLAN.md:216` | §7's sketch omits the leading `\` the convention requires (F1) |
| 5 | `README.md:94` | the PHP status row and the `[adapter_cmd]` example |
| 6 | `docs/BACKLOG.md`, this file's frontmatter | status sync (R7.2) + the token row |

### Cost ledger

| Phase | Dispatch | Tokens |
|---|---|---|
| Phase 1 — analysis | **0 subagents** — no Explore fan-out (`explore_fanout: true`, but the surface is one empty directory and six known docs; five read-only spikes on the main model did the de-risking instead) | 0 dispatch · main-loop unmeasured (see `rtk gain`) |

### Session status

- **Phase:** 1 (analysis) complete → Gate 0 cleared (3 decisions ratified) → **STOPPED at Gate 1**.
- **Working doc:** `docs/tasks/006_php-adapter-spike.md` (embedded, below the separator).
- **Branch:** none yet — nothing has been written outside this working doc.
- **Next action:** run `/mango:design` — the change list must carry the six blast-radius files above,
  plus the two guardrail-scoping edits F8 forces and the three Gate-0 ratifications.
- **Revert path:** `git checkout -- docs/tasks/006_php-adapter-spike.md` restores the raw ticket
  (the file is committed and clean at `866d67d`; the working doc is the only uncommitted change).

---

## Phase 2 — Design

### Approach

One new self-contained process under `adapters/php/`, and **zero changes under `code_atlas/`**.

`index.php` is a thin CLI: it requires `vendor/autoload.php` (missing → loud stderr + non-zero exit,
R5.3), reads `--file <path>`, and runs the two-visitor traversal PLAN §7 sketches —
`NameResolver` first so every `Name` arrives resolved, then our `Visitor`. It prints exactly **one**
JSON object on stdout and nothing else. A `Throwable` from the parse is caught and turned into a
contract-shaped `{"path", "ok": false, "error"}` so the `--file` mode's output is *always* a valid
contract result; that is deliberately **not** `ErrorHandler\Collecting`, which is task 007's
deliverable — this is three lines that stop a PHP fatal from being the output format.

`src/Visitor.php` extends `NodeVisitorAbstract` and overrides `enterNode`. It keeps a container stack
so a member's qualified name is built as `container::member`, and it prepends the leading `\` that
CONVENTION §3 requires and NameResolver does not supply (finding F1). It emits:

- **nodes** `File · Namespace · Class · Method · Property · ClassConst · Function` — 7 of the 11 kinds;
- **edges** `CONTAINS · EXTENDS · IMPLEMENTS · IMPORTS · CALLS · NEW · INCLUDES` — 7 of the 9 kinds;
- **bare** edges only (`target_raw`, never `target_qname`) — R3.3;
- `HEURISTIC` on an instance `MethodCall`, whose receiver type is unknowable from one file (F6) — R5.2.

The class-like dispatch keys on the parser's own `Stmt_ClassLike` base with a four-entry map
(`Class_ · Interface_ · Trait_ · Enum_`). That is the *language's* structure, not speculative
generality — writing a `Class_`-only handler we already know is wrong would just make 007 rewrite it.
**Recorded gap:** the namespaced fixture declares a class *and* an interface, so two of the four map
entries are fixture-proven here; `Trait_` and `Enum_` are exercised by task 007's fixtures. Named, not
silent.

Everything the ticket does not name stays out: no `--server`, no handshake line, no
`ErrorHandler\Collecting`, no anonymous classes, closures, arrow functions, first-class callables,
attributes, group-use, promoted parameters, or enum cases. All of those are task 007.

### Rejected alternatives

1. **Emit the JSON inline from `index.php`, no `Visitor` class.** Shorter for a spike, but the ticket
   names `src/Visitor.php` and task 007 grows exactly that file — inlining buys ~20 lines now and costs
   a rewrite immediately after.
2. **`createForHostVersion()` instead of `createForNewestSupportedVersion()`.** Rejected: it pins the
   parseable grammar to whichever PHP the developer happens to run (8.3.6 here), so an 8.4/8.5
   construct would silently fail to parse on one machine and parse on another — an R4.2 violation
   dressed as a convenience. Spike S2 shows newest-supported costs nothing on an 8.3 host.
3. **Let the visitor fill `target_qname` for names it can resolve within the file.** Rejected by R3.3:
   a single file cannot know all targets, and a partially-resolved edge is worse than a bare one
   because the resolver can no longer tell which it must still do.
4. **Commit `vendor/`.** Rejected: 280 files of dependency, and it would weld Composer's "Symfony"
   docblock into the R2.2 grep-gate's search space permanently (F8).
5. **Skip the CI wiring and prove the AC only where PHP happens to be installed.** Rejected at Gate 0
   (Q1) — a proof that never runs on the machine that gates the merge is not a proof.

### Assumptions

| # | Assumption | Tag | Resolution |
|---|---|---|---|
| A1 | `nikic/php-parser: ^5` resolves to a build that parses PHP 8.5 grammar | **verified** | Spike S1/S2 — v5.8.0, `getNewestSupported()` = 80500, six 8.4/8.5 probes parse |
| A2 | `NameResolver` supplies `namespacedName` on declarations and resolved `Name_FullyQualified` on references, for both namespaced and global/underscore code | **verified** | Spike S3 — full node dump for both fixture shapes |
| A3 | A result assembled from that material passes `contract.validate()` with zero errors | **verified** | Spike S4 — clean, plus a planted bad kind rejected |
| A4 | A GitHub Actions ubuntu runner can install PHP and run `composer install` for `adapters/php/` | **novel-untested** (3p/runtime) | Cannot be spiked locally. **Resolved by shaping the proof:** the proving test is an integration test that runs *in CI*, so if `shivammathur/setup-php` or `composer install` fails, the job fails **loudly and visibly** — never a silent green. Risk further reduced by pinning the action to `@v2` and requesting `php-version: "8.3"`, the exact runtime the whole design was proven on locally |
| A5 | The CI runner has network for packagist | **verified** by analogy — the existing `Install` step already reaches PyPI (`ci.yml:21`) |

No `novel-untested` assumption is left unresolved.

### Smallest change list

| # | Change | File / area | `Ph2 covered by` | k/N |
|---|---|---|---|---|
| 1 | `composer.json` — require `nikic/php-parser: ^5`, PSR-4 `CodeAtlas\Php\ → src/` | `adapters/php/composer.json` | R1, R2 | 1/1 |
| 2 | Commit the resolved lock so every machine gets one parser build | `adapters/php/composer.lock` | R2, Gate-0 Q2 | 1/1 |
| 3 | `--file` CLI entry: autoload guard, argument parse, traversal, one JSON line | `adapters/php/index.php` | R1, AC1 | 1/1 |
| 4 | The visitor: container stack, leading `\`, 7 node kinds, 7 bare edge kinds | `adapters/php/src/Visitor.php` | R1, R3, AC2, G1 | 1/1 |
| 5 | Adapter-local README — runtime, `composer install`, `--file` usage | `adapters/php/README.md` | R1 + CONVENTION §5 / R8.1 (clarification 5) | 1/1 |
| 6 | Namespaced fixture — namespace, `use`+alias, class, interface, const, typed property, method with a typed param, instance call, free function, `new` | `tests/fixtures/php/namespaced.php` | R3, AC1(1), AC2 | 1/2 |
| 7 | Global/underscore fixture — no namespace, `require_once`, underscore class extending an underscore parent, method, static call, underscore free function, `new` | `tests/fixtures/php/global_underscore.php` | R3, AC1(2), AC2 | 2/2 |
| 8 | The proving test — parametrized over both fixtures, plus the two AC2 qname assertions and a no-PHP-needed guard-the-guard | `tests/test_php_adapter_spike.py` | AC1, AC2, G1, R6.1 | 2/2 |
| 9 | **Proof collateral** — exclude `vendor/` from the adapter-source sweep so the un-skipped guard checks authored files, not 280 dependency files | `tests/test_sql_confinement.py:44` | F8, R6.4 | 1/1 |
| 10 | **Proof collateral** — R2.2 grep-gate excludes `vendor/`; add PHP setup + `composer install` so the proving test runs in CI | `.github/workflows/ci.yml:55` | F8, Gate-0 Q1, R6.4 | 1/1 |
| 11 | Un-ignore `composer.lock` (keep `vendor/` ignored) | `.gitignore:20` | Gate-0 Q2 | 1/1 |
| 12 | §7: record the leading `\` the convention requires, and correct the sketch's stale `\CodeGraph\Php\Visitor` namespace | `docs/PLAN.md:216` | F1, R7.2 | 1/1 |
| 13 | PHP row status + a working `--file` line in the adapter section | `README.md:94` | R7.2 | 1/1 |

Items 14–15 (`docs/BACKLOG.md` status + token row, this file's frontmatter) land at **finalise**, per the
convention that status can only truthfully read `done` after the PR merges.

**Test blast-radius (mechanical, not a name grep).** Traced by *what this change creates*, not by one
string: creating `adapters/php/**.php` is what activates `tests/test_sql_confinement.py:51`'s skip
(item 9), and creating `adapters/php/vendor/` is what activates the `ci.yml:59` grep (item 10). Both are
**planned edits above**, not execute surprises. Nothing under `code_atlas/` is touched, so there is no
type/symbol fan-out and no builder call-site fan-out; `mypy code_atlas` and the other 237 tests are
untouched by construction. Grep confirms no existing test references `adapters/` other than
`tests/test_sql_confinement.py`.

### Rule compliance

The §1–§8 sweep is in Phase 1 (`RULE SECTIONS`). The rules that actively **constrain this design**:

- **R2.2 / R2.3** — the fixtures use neutral underscore names (`Foo_Bar_Baz`, `Legacy_Registry`), never
  `Zend_*` or any framework name, even though the validation sample has a `Zend/` tree.
- **R3.3** — every emitted edge carries `target_raw` and omits `target_qname`.
- **R5.2** — the instance call is `HEURISTIC`; nothing is guessed into `RESOLVED`.
- **R1.3** — no adapter file contains the string `code_atlas`; item 9 makes that assertion real rather
  than 0/0.
- **R7.5** — ≤ 3 lines per comment applies to the PHP source as much as the Python.
- **R8.1** — `composer.json` + an adapter-local README; no PHP dependency reaches `pyproject.toml`.

**Uncodified standard surfaced, not silently applied:** "pin an adapter's dependencies with a committed
lock file" (Gate-0 Q2) and "guardrail greps scan *authored* source, never vendored dependencies" (F8)
are both being *applied* here but are **not** in `ENGINEERING_RULES.md`. Flagged for `codify`'s
provisional→ratify flow at finalise so adapter #2 inherits a rule instead of a precedent. Neither
gate-blocks in the meantime.

### Verification plan (per-AC, layer-matched)

| AC / requirement | Risk layer | Proof artifact | layer-match? |
|---|---|---|---|
| AC1(1) namespaced fixture → schema-valid, `ok:true`, non-empty nodes | **integration** (a real subprocess, a real parser, JSON across a process boundary) | integration test spawning `php index.php --file` and running `contract.validate()` on stdout | ✅ |
| AC1(2) global/underscore fixture → same | **integration** | same test, second parametrized case | ✅ |
| AC2(a) FQNs resolved with the leading `\` (`\App\Models\User::save`) | **integration** | assertion on exact qname strings in the real emitted JSON | ✅ |
| AC2(b) global/underscore first-class: underscores intact, no namespace segment | **integration** | assertion on exact qname strings in the real emitted JSON | ✅ |
| R2 `createForNewestSupportedVersion()` + `NameResolver` used | logic | grep/read of `index.php` **plus** the integration proof above, which is what would break if either were dropped | ✅ |
| G1 the contract survives contact with a real parser | **integration** | the two AC1 cases *are* this | ✅ |
| R1.3 no adapter source imports the core | logic (a text property of files) | `tests/test_sql_confinement.py`, now non-vacuous | ✅ |
| F8 guardrails survive a vendored dependency | **integration** (CI job behaviour) | the CI run itself — the R2.2 gate executes against a populated `vendor/` for the first time | ✅ |

**No ❌ rows. No coverage-gap exclusion is needed** — every acceptance criterion is proven at the layer
where it can actually fail, and nothing is proven by a unit test standing in for a subprocess.

Two **recorded, non-blocking gaps** (neither is an AC): `Trait_`/`Enum_` dispatch-map entries are
fixture-proven in task 007, not here; and the PHP source's restatement of the contract vocabulary is
drift-checked by task 012's conformance harness (R3.4), which does not exist yet.

### Proving test

```
.venv/bin/pytest tests/test_php_adapter_spike.py -q
```

Named assertion (the per-item pair that carries AC1's N=2):

```
tests/test_php_adapter_spike.py::test_the_fixture_parses_to_a_valid_contract_result[namespaced]
tests/test_php_adapter_spike.py::test_the_fixture_parses_to_a_valid_contract_result[global-underscore]
```

**Fails pre-change** for a real reason, not an import error: `adapters/php/index.php` does not exist, so
the subprocess exits non-zero and no JSON is produced. **Passes post-change** with
`contract.validate(...) == []`, `ok is True`, `len(nodes) > 0` for each fixture.

It sits at the integration layer by construction — it spawns the real interpreter against the real
parser. It skips **only** when `shutil.which("php")` is None or `vendor/` is absent, and the skip
message names the exact command that fixes it; CI installs both, so **CI is where this test is
authoritative** and the skip is a developer-laptop convenience, never the merge gate.

### Rollback + porting

- **Rollback:** the work lands on `feat/006-php-adapter-spike`. Before merge, delete the branch — nothing
  under `code_atlas/` changed, so the core is untouched by construction. After merge, `git revert` the
  merge commit; the only non-additive hunks are `.gitignore:20`, `ci.yml:55`, and
  `tests/test_sql_confinement.py:44`, all one-liners that revert cleanly.
- **Reverting item 10 alone** restores a green CI without PHP, at the cost of making the proving test
  skip there — that is the fallback if `setup-php` misbehaves (assumption A4).
- **Porting:** none. `config.repos` has one entry (`app`, root `.`); no shared code is touched.

### SCOPE

**`SCOPE: M`** — unchanged from analysis. 13 change-list items, but 5 are new files in a brand-new
directory with no dependents, 3 are one-line guardrail/ignore edits, and 2 are docs. Nothing crossed a
tier; no *outgrew-its-ticket* nudge is raised. The two items beyond the ticket's literal file list
(9 and 10) are proof collateral forced by F8 and were traced at analysis, not discovered mid-execute.

### Cost ledger

| Phase | Dispatch | Tokens |
|---|---|---|
| Phase 1 — analysis | 0 subagents (5 read-only spikes on the main model) | 0 dispatch · main-loop unmeasured (`rtk gain`) |
| Phase 2 — design | 0 subagents | 0 dispatch · main-loop unmeasured (`rtk gain`) |

### Session status

- **Phase:** 2 (design) complete → **STOPPED at Gate 2**.
- **Branch:** none yet — nothing written outside this working doc.
- **Next action:** `/mango:execute` — branch `feat/006-php-adapter-spike`, implement items 1–13 and
  only those, add the proving test, run both sweep axes.
- **Revert path:** unchanged — `git checkout -- docs/tasks/006_php-adapter-spike.md` restores the raw
  ticket; the working doc is still the only uncommitted change against `866d67d`.

---

## Phase 3 — Execute

**Branch:** `feat/006-php-adapter-spike` · 4 commits (`c8fb10e`, `43d7561`, `f73db0a`, `abfe637`).

### Result against the recorded baseline

```
BASELINE was: green — 237 passed, 1 skipped
NOW:                  248 passed, 0 skipped · ruff clean · mypy clean (11 source files)
```

+11 tests, and the skip is gone — exactly the change Phase 1 predicted. The skip that disappeared is
`test_no_adapter_source_reaches_into_the_core`: it was 0/0 vacuous, and real adapter source turned it
into a live assertion.

### Verification sweep — axis 1, file set

`diff ⊆ approved change list` ✅. Every path in the diff is a numbered change-list item; no file
outside the list, no untouched-line reformatting, no formatter run over a shared file.

| Change-list item | Path | Landed |
|---|---|---|
| 1, 2 | `adapters/php/composer.json`, `composer.lock` | ✅ |
| 3 | `adapters/php/index.php` | ✅ |
| 4 | `adapters/php/src/Visitor.php` | ✅ |
| 5 | `adapters/php/README.md` | ✅ |
| 6, 7 | `tests/fixtures/php/{namespaced,global_underscore}.php` | ✅ |
| 8 | `tests/test_php_adapter_spike.py` | ✅ |
| 9 | `tests/test_sql_confinement.py` | ✅ |
| 10 | `.github/workflows/ci.yml` | ✅ |
| 11 | `.gitignore` | ✅ |
| 12 | `docs/PLAN.md` | ✅ |
| 13 | `README.md` | ✅ |

Zero files under `code_atlas/` are touched, as designed. `git status` confirms `adapters/php/vendor/`
stays ignored while `composer.lock` is tracked.

### Verification sweep — axis 2, design conformance (behaviour)

Every Gate-2 Approach bullet, walked:

| Approach bullet | Verdict |
|---|---|
| Thin `--file` CLI; loud on a missing `vendor/`, one JSON line on stdout | implemented-as-approved |
| `NameResolver` first, then `Visitor` | implemented-as-approved |
| `Throwable` caught into a contract-shaped `ok:false` — *not* `ErrorHandler\Collecting` | implemented-as-approved |
| Container stack; leading `\` prepended (F1) | implemented-as-approved |
| 7 node kinds, 7 bare edge kinds, `HEURISTIC` on the instance call | implemented-as-approved |
| `Stmt_ClassLike` dispatch, 4-entry map; class + interface fixture-proven, trait/enum to 007 | implemented-as-approved |
| Nothing from task 007's list (`--server`, handshake, attributes, closures, …) | implemented-as-approved |

**No behavioural deviation.** Two things were *added* inside approved item 3 rather than deviating from
it, and both are named here so review adjudicates rather than discovers them:

- **D1 — a `json_encode` failure path.** Item 3 approved "prints one JSON line". If a source file
  carries undecodable bytes, `json_encode` returns `false` and the approved design would have printed
  the bare word `false`. Four lines emit a soft `ok:false` instead. This is PLAN §4.1's "undecodable
  bytes fail *that file* softly — never repaired into mojibake"; it is the approved bullet done
  correctly, not a new feature, but it was not written down at Gate 2.
- **D2 — a second guard test.** `test_the_vendor_filter_narrows_the_sweep_without_emptying_it` was not
  named in item 9. It exists because item 9 *is* a filter, and a filter that swallowed the authored
  files too would silently restore the 0/0 vacuity that item 9 was written to remove (LESSONS 002).

### Proving test — and whether it can fail

```
.venv/bin/pytest tests/test_php_adapter_spike.py -q   →  9 passed
```

Four behaviour mutations and one guard negative control, each applied to a `cp` backup, run, then
restored and **verified byte-identical with `cmp`** against the working tree (never `git checkout --`,
LESSONS 004):

| # | Mutation | Result |
|---|---|---|
| M1 | `index.php` absent — the genuine pre-change state | **9 failed** — the subprocess cannot run. Not an ImportError |
| M2 | `fqn()` stops prepending the leading `\` | **2 failed** — both AC2 assertions |
| M3 | the instance `MethodCall` drops its `HEURISTIC` tier | **2 failed** |
| M4 | the `File` node emits an off-vocabulary kind | **2 failed** — `contract.validate()` catches it |
| NC1 | the vendor filter widened until it swallows all authored source | **1 failed** + the old guard silently re-skips — which is precisely what D2 catches |

**Live negative control on the R2.2 gate.** With `vendor/` populated, the unpatched gate matched
`vendor/composer/ClassLoader.php:21` and would have failed the build; the patched gate matches
nothing. Both states were observed, so the fix is evidenced rather than asserted.

### Per-item inventory — AC1, N = 2

| # | Item | Ph3/4 proven by |
|---|---|---|
| 1 | namespaced fixture | `test_the_fixture_parses_to_a_valid_contract_result[namespaced]` + `test_a_namespaced_file_resolves_every_name_to_a_leading_backslash_fqn` — **2/2** |
| 2 | global/underscore fixture | `…[global-underscore]` + `test_a_global_underscore_file_keeps_its_underscores_and_carries_no_namespace` — **2/2** |

### Emitted output, both shapes (the evidence behind the ACs)

- **namespaced** → 10 nodes (`File`, `\App\Models`, `\App\Models\Storable`, `\App\Models\User`,
  `…::ROLE`, `…::$name`, `…::save`, `…::store`, `\App\Models\Storable::store`, `\App\Models\helper`)
  and 15 edges, including `IMPORTS → \App\Contracts\Jsonable` (the `as J` alias resolved through to the
  FQN), `EXTENDS → \App\Models\Base`, both `IMPLEMENTS`, `NEW → \App\Models\User`, and
  `CALLS → put` at `HEURISTIC`.
- **global/underscore** → 6 nodes (`File`, `\Foo_Bar_Baz`, `…::TABLE`, `…::$rows`, `…::fetchRow`,
  `\foo_helper`) and 9 edges, including `INCLUDES → Legacy/Registry.php`,
  `EXTENDS → \Legacy_Table`, and `CALLS → \Legacy_Registry::get`. **No `Namespace` node**, and every
  qualified name carries exactly one separator — the underscore case needs no special path at all.

### SCOPE

`SCOPE: M`, unchanged. No *outgrew-its-ticket* nudge: the realized diff is the approved list.

### Cost ledger

| Phase | Dispatch | Tokens |
|---|---|---|
| Phase 1 — analysis | 0 subagents (5 read-only spikes on the main model) | 0 dispatch |
| Phase 2 — design | 0 subagents | 0 dispatch |
| Phase 3 — execute | 0 subagents | 0 dispatch · main-loop unmeasured (`rtk gain`) |

### Session status

- **Phase:** 3 (execute) complete → flowing into review.
- **Branch:** `feat/006-php-adapter-spike`, 4 commits, nothing pushed.
- **Next action:** review — challenger only, by user instruction (the `reviewer` dispatch is skipped).
- **Revert path:** `git checkout main && git branch -D feat/006-php-adapter-spike`. Nothing is pushed
  and no core module changed, so `main` at `866d67d` is untouched.

---

## Phase 4 — Review

**Dispatch:** `mango:challenger` only — the `mango:reviewer` pass was **skipped by user instruction**.
Recorded as a deliberate, human-made reduction in review depth, not an omission.

### Challenger verdict (ticket-blind)

**6/6 requirements met**, every one verified by execution rather than inference: it ran the adapter
against both fixtures itself, wrote two extra probe files of its own, and ran the full suite (248
passed at the time of review). **No information-barrier leak** — it confirmed it never read below the
separator in `docs/tasks/`, having scoped `docs/tasks/` out of every search per LESSONS 005.

Rule-book conformance it checked independently: R1.3/R1.4 (zero core files touched), R3.3 (bare edges),
R4.2 (determinism), R5.1/R5.2/R5.3, R7.5, R8.1, and the R2.2 gate change — all met, with the
guardrail-scoping edits judged "a justified, in-scope fix, not scope creep".

### Findings, and what was done

| # | Finding | Severity | Action |
|---|---|---|---|
| 1 | **Every scalar type hint reported `"type": null`.** `params()` tested `instanceof Node\Name`, but `string`/`int`/`bool` arrive as `Node\Identifier` — so a typed parameter was indistinguishable from an untyped one. Silent data loss, not a deferral | **real defect** | **Fixed** (`4f53155`). `typeName()` renders `Name`, `Identifier`, `NullableType`, and union/intersection types |
| 2 | **`Trait_` and `Enum_` were wired into the dispatch map with no fixture reaching them** — untested code that Phase 2 had recorded as a known gap, and the challenger found blind | **real gap** | **Fixed** (`4f53155`). The namespaced fixture now declares a trait and an enum; a dropped map entry now turns the suite red |
| 3 | **The R5.3 loud-failure branch had no test** — inferred safe from reading, never executed | **coverage gap** | **Fixed** (`4f53155`). A copy of the entry point with no `vendor/` beside it is asserted to exit 2 on stderr with empty stdout |
| 4 | **`BACKLOG.md` and the frontmatter still read `todo`** while the work was complete | **process** | **Partly accepted.** Both now read `in-progress`; `done` still lands after the merge, because a status that reads `done` before the PR merges is false. Same pattern as tasks 004 and 005 |
| 5 | **A class's `use <Trait>` emits no `USES_TRAIT` edge, silently** — the vocabulary has the kind but this adapter never populates it | **recorded, deferred** | Task 007's Scope names `TraitUse` explicitly, so it is owned. The adapter README now says so out loud rather than leaving it implicit |
| 6 | **`enum`, attributes, closures, arrow functions, first-class callables, group-use untested** | **recorded, deferred** | Correct per the ticket's "at least" wording; task 007 + 012 own them. `enum` moved out of this list by finding 2 |

### Re-verification after the fixes (verify-only, main-loop, no re-dispatch)

The fixes touched only files already inside the approved change list — items 4, 6, 8 — plus the two
bookkeeping status files, which are the exempt set. **No scope change, so no re-dispatch.**

```
251 passed, 0 skipped · ruff clean · mypy clean (11 source files)
R1.1 gate ok · R2.2 gate ok (with vendor/ populated)
```

Each fix is negative-controlled — the mutation was applied to a `cp` backup, run, then restored and
confirmed byte-identical with `cmp`:

| # | Mutation | Result |
|---|---|---|
| M5 | `typeName()` regressed to the class-names-only test | **1 failed** |
| M6 | `Enum_` removed from the dispatch map | **6 failed** — the parse itself now errors, so it cannot pass quietly |
| M7 | the loud `exit(2)` softened into an `ok:false` result | **1 failed** |

### Scope reconciliation

- **File axis:** `diff ⊆ approved change list` ✅. Every path traces to a numbered item; the fixes added
  no file. Zero files under `code_atlas/`.
- **Behaviour axis:** every Gate-2 Approach bullet is `implemented-as-approved`. Deviations D1 and D2
  from Phase 3 were surfaced by the author and stand adjudicated as in-scope corrections. Finding 1 is
  the one thing the author self-marked correct that was not — recorded here rather than quietly fixed.

### Layer-match re-confirmation

No AC closed on a layer-mismatched proof. Every AC's risk layer is **integration**, and every proof
spawns the real interpreter against the real parser. The three new tests sit at the same layer. No
coverage-gap exclusion was needed, so none stands unresolved.

### Verdict

**Clean**, with the review depth reduced by explicit user instruction (challenger only). `k = N = 2` on
the AC1 inventory, both items proven per-item; proving test green; baseline comparison is
`237 passed / 1 skipped → 251 passed / 0 skipped`, the skip having been converted to a live assertion
by design.

```
Reviewed at 4f53155
Reviewed files: adapters/php/{composer.json,composer.lock,index.php,README.md,src/Visitor.php},
  tests/fixtures/php/{namespaced,global_underscore}.php, tests/test_php_adapter_spike.py,
  tests/test_sql_confinement.py, .github/workflows/ci.yml, .gitignore, docs/PLAN.md, README.md,
  docs/BACKLOG.md
Working doc (exempt from the staleness comparison): docs/tasks/006_php-adapter-spike.md
```

### Cost ledger

| Phase | Dispatch | Tokens |
|---|---|---|
| Phase 1 — analysis | 0 subagents (5 read-only spikes on the main model) | 0 dispatch |
| Phase 2 — design | 0 subagents | 0 dispatch |
| Phase 3 — execute | 0 subagents | 0 dispatch |
| Phase 4 — review | 1 subagent — `mango:challenger`, 34 tool uses / 228 s | **73.9k dispatch** |
| Phase 4 — re-review | 0 subagents (verify-only in the main loop) | 0 dispatch |
| **Total** | **1 dispatch** | **73.9k dispatch** · main-loop unmeasured (`rtk gain`) |

### Session status

- **Phase:** 4 (review) complete, verdict **clean** → finalise.
- **Branch:** `feat/006-php-adapter-spike`, 6 commits, nothing pushed.
- **Next action:** finalise — PR body, push, open the PR.
- **Revert path:** `git checkout main && git branch -D feat/006-php-adapter-spike`; `main` at `866d67d`
  is untouched and no core module changed.
