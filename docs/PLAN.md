# Code-Atlas MCP — Build Plan

> Status: **shipped and in daily use** — Phase 1 (core + PHP, M0–M6) and Phase 3 (onboarding,
> M10–M12) are complete, 24 tools on the surface; adapters #2–#4 (TS/JS, T-SQL, Python) have landed,
> C#/.NET stays deferred (§19).
> A local-first, multi-language code-intelligence MCP server.
> Name: **`code-atlas`** (evolved: `php-code-graph` → `code-graph` → **`code-atlas`**; it's multi-language). GitHub repo: `code-atlas`.

A local-first MCP server that indexes a codebase into SQLite and exposes **fast, resolved, token-efficient** search / read / navigation / impact tools — above all the **resolved relationships** between symbols, which text search cannot produce at any speed. (This line used to claim native tools and grep are weak at search on large repos; that premise was measured and refuted on 2026-08-08 — see §19.)

**Language-agnostic core + per-language adapters**, every one behind the *same* contract (order and status: §3). On top of the graph sits the **Understand-Anything-style onboarding** feature (§14).

---

## 0. Priorities (driving order)
1. **Make the MCP work.** PHP end-to-end, daily-usable, before anything is generalized.
2. **Extensible to other languages without touching the core** (§3).
3. **Onboarding feature** (Understand-Anything style) as a Phase-3 consumer of the graph.

These are in tension if mishandled — see the design principles (§2). The rule: architect for multi-language, but *implement* one language first; let language #2 harden the abstraction.

---

## 1. Goals & non-goals

### The two pillars

**This subsection is authoritative.** Everything below in §1 is the *how*; these are the two things
being built. Where another document states the value of this project, it states it from here.

> **PILLAR 1 — GRAPH.** Resolved code relationships for AI coding agents: who calls this,
> what implements that, what breaks if this changes. The value is accuracy and
> consistency, bought at a token cost low enough that an agent can afford to ask.
> Accuracy means a wrong answer is not an acceptable failure mode; silence is.
> Consistency has two halves: the same question at the same commit returns the same
> rows, and two tools asked about the same fact do not contradict each other.
> Serves the agent, as caller. Surface: the MCP tools.
>
> **PILLAR 2 — ONBOARDING.** A rendering of what the code actually is — layers, modules,
> hubs, entry points, flow — built from the same graph, as diagrams and documents.
> Two uses, one artifact. SUPERVISION: the rules and the architecture are given to the
> agent up front, and the agent still drifts; the map shows what was actually generated,
> so a human can see where it went. PRESENTATION: a human shows the state of the project
> to someone else. Serves the human, as reviewer and as presenter.
>
> **SHARED CONSTRAINT:** both read the same graph. The map never runs a second pipeline —
> a number on the map is reachable through a tool, at the same commit, at the same
> confidence tier.

**Supervision is the larger half of Pillar 2**, and it is newer than the directory name
`code_atlas/onboarding/` — which stays as it is. The code is not renamed from this subsection.

### Goals
- Replace "grep + read whole file" with **symbol-level, name-resolved** queries.
- **Primary consumer is an AI coding agent in a terminal**, not a human in an IDE — so optimize for *tokens-to-correct-answer against a grep+`Read` baseline*, and for **machine-trustable responses**: calibrated confidence tiers, honest empties/truncation, enforced freshness (§19 agent-first pivot, 2026-08-04).
- **Work on ANY repo of a supported language.** Adapters implement the **language standard** (full grammar + the language's standards/PSRs), never a specific repo's conventions. Specific repos are *validation samples*, not design inputs (see §2 "Standard over sample" and §6).
- **One core, many languages**: each language uses its *best* parser (PHP→nikic, TS/JS→TypeScript Compiler API, Python→`ast`+jedi, C#→Roslyn), all speaking one JSON contract. Roll-out order: **PHP → TypeScript/JavaScript → Python → C#/.NET** (§3).
- Complement LSP-based tools, not duplicate them (§13).
- Deterministic, offline, token-efficient. LLM used only in the onboarding layer (§14), never in the core.

### Non-goals (core, v1)
- No rename/refactor/edit — **permanently ceded to the agent's native `Edit`/`Write`** (the consumer is an agent, not an IDE; §19). code-atlas returns exact symbol line ranges those edits act on; it never mutates code.
- No type inference **in the core** (adapters may supply it where free — Roslyn's semantic model, the PHP local type table [137](tasks/137_php-local-type-table.md) **shipped**, opt-in PHPStan `semantic_types`; §19). The core still resolves *across* files, because a declared type the adapter recorded is graph data, not inference.
- **Framework-magic as adapter code** (hard-coded facades/DI/`__call` in adapters) stays forbidden (R2.2).
  Opt-in **indirection rules as data** (`CA_INDIRECTION_RULES`, task 040) are an in-core enrichment
  pass on the standard-language graph — off by default. ORM/`__call` heuristics remain future/out-of-band.
- No cloud LLM calls in the core.

---

## 2. Design principles (SOLID at the boundaries)

SOLID applied where a **real axis of change** exists — languages. Not speculative interfaces inside
single-purpose components. The rules themselves are binding text in
[`ENGINEERING_RULES.md`](ENGINEERING_RULES.md) and are **not** restated here: **R1.1** zero language
branches in the core · **R1.2** one seam only · **R1.3** one-way dependency direction · **R1.4** SRP
per component · **R1.5** substitutability · **R1.6** capability flags · **R2.1–R2.3** standard over
sample. What belongs in the plan is *why the seam is where it is*:

- The one axis is **languages**, so the one seam is the **adapter contract** (§4) — and it is a JSON
  contract plus a subprocess protocol rather than a Python base class, because a .NET adapter cannot
  implement a Python ABC. That is what makes the inversion real rather than nominal.
- **Abstract nothing that does not yet have two implementations.** Adapter #2 (TS/JS) — chosen as the
  *most different* from PHP (no FQNs; module-scoped `import`/`export`; `tsconfig` aliases;
  project-context resolution) — proved the seam: **no registry, no contract v2** (§19, §4.4).
- **Standard over sample is a claim about scope, not just about naming:** if a fact about a repo
  would change adapter behaviour, it belongs in the language spec or nowhere. Sample repos buy test
  coverage and performance targets, never semantics (§6.1). §19 extends the same rule to *evidence*.

Precedent to copy: a mature multi-language LSP framework (one abstraction + N concrete language
servers + a `get_ls_class()`-style factory) is OCP/DIP at scale; a `Tool`/`ToolRegistry` +
marker-mixin design is ISP in practice.

---

## 3. Why this backend (decision record)

Per-language, pick the best parser; do **not** force one across all languages. **Roll-out order and rationale:**

| # | Language | Adapter parser | Why this parser / why this position |
|---|---|
| 1 | PHP | **nikic/php-parser** (^5) | Only reliable **PHP 8.5** parse. `NameResolver` gives FQNs for PSR-4 *and* global code. Needs only the tokenizer ext. **First = a large PHP monorepo is the stress-test sample.** |
| 2 | TypeScript/JavaScript | **TypeScript Compiler API** (via `ts-morph`, Node sidecar) | Official parser+**type checker**; parses JS too (`allowJs`); resolves ESM/CommonJS + `tsconfig` aliases + types. **Second = most popular AND best contract-hardener** — module-scoped symbols (no FQNs) + project-context resolution stress the abstraction hardest (§2, §4.4). Proves `semantic_types` early. |
| 3 | Python | **`ast`** builtin; `jedi` unbought | Zero-dependency parse. **Shipped stdlib-only** (020 tier 1a · 217 tier 2): nothing so far needed import/name resolution, so `jedi` waits for a tier that does. |
| 4 | C#/.NET | **Roslyn** (.NET sidecar) | Full **semantic model** → precise type/call/ref edges. Last: its namespace+FQN model resembles PHP's, so it *confirms* rather than reshapes the contract. |

**A fifth capability — SQL / DB-schema awareness** (**landed** as `adapters/sql/`, outside the order above): schema facts are *not* source symbols and needed their own vocabulary (R3), so it sat behind 022's evidence gate until measured demand discharged it (§19). 184 tier 1a · 022 tier 2 (`Table`, `Column`, `WRITES`, contract **v9**).

Rejected globally:
- **tree-sitter everywhere** — grammar lags releases (misparses PHP 8.5); forces hand-written resolution (the hard part) per language.
- **Wrapping LSPs as the core** — existing LSP tools already do that; an LSP indexing 100k+ files *live* is the sluggishness we're avoiding. (An adapter *may* wrap an LSP internally, but the core stays index-based.)

Engine lineage: **code-review-graph** (parse → SQLite, incremental, token-budgeted tools), generalized behind an adapter contract.

---

## 4. The contract (first-class deliverable)

The single seam between core and every language. Two parts:

### 4.1 Subprocess protocol (streaming, language-neutral)
Adapter runs as a long-lived process; core feeds newline-delimited requests, reads JSONL results. One process boot amortized across all files.
```
← {"name":"php","extensions":[".php",".phtml"],"capabilities":{},"contract_version":10}   # handshake, first line
→ {"path":"src/Models/User.php"}                              # stdin, one JSON/line
← {"path":"src/Models/User.php","ok":true,"nodes":[…],"edges":[…]}   # stdout JSONL
← {"path":"legacy/foo.php","ok":false,"error":"syntax error @12"}
```

**The handshake is how the core stays language-agnostic.** An adapter announces itself on one unprompted line before any result: its name, the **file suffixes it owns**, and its capability flags. That is the *only* source of the extension→adapter mapping, so the core never carries a table of who parses what (R1.1), and it is the channel capability flags need to exist at all (R1.6). A handshake that is malformed or declares a different `contract_version` is a **loud startup failure** (R5.3). Validated by `contract.validate_meta`.

**Wire rules the protocol depends on:**
- **Lock-step.** One request, one reply, correlated by `path`. Concurrency is N *processes* (§8.1), never several requests in flight on one pipe. A reply for a path that was not asked is a **desync** — loud, because it would otherwise misattribute every later result.
- **stdout is protocol-only; stderr must never be an undrained pipe.** An adapter that writes more than a pipe buffer of diagnostics deadlocks a driver that is blocked reading stdout, and merging stderr into stdout corrupts the stream. The driver sends stderr to `DEVNULL`, or to a file when diagnostics are wanted.
- **UTF-8, `\n`-framed, one line per message**, however large (a 2 MB result line is normal). Undecodable bytes fail *that file* softly — never repaired into mojibake, which would parse as valid JSON and store silently corrupt rows.
- **Failure split (R5.1/R5.3).** Soft, per file: `ok:false`, a result rejected by `validate()`, a non-JSON line, a blank line, undecodable bytes. Loud, per process: an unlaunchable command, a child that exited mid-stream, a desync, a bad handshake. A child that **hangs** is bounded by the build's deadline (§8.1), not by the driver, which stays free of a per-request reader thread.

### 4.2 JSON schema (the vocabulary every adapter emits)
**The vocabulary itself is not listed here.** It is defined once in `code_atlas/contract.py` — the
node kinds (`NODE_KINDS`, derived from an ordered `Literal` so the typing and the tuple cannot
disagree), the edge kinds (`EDGE_KINDS`), the field sets (`NODE_FIELDS`, `EDGE_FIELDS`, and the
`REQUIRED_*` subsets that say which may be omitted), `CONFIDENCE_TIERS`, `ARG_LITERALS`, and
`CONTRACT_VERSION` — and its **spelling plus per-kind semantics** are in
[`CONVENTION.md`](CONVENTION.md) §3. This section says what the shape *is* and why; it does not
repeat the members, for the same reason R6.7 forbids a guard that lists a set it could derive: a
hand-kept copy drifts silently, and the reader who satisfies one copy believes they are done.

**The shape.** A node carries its kind, its name and qualified name, where it is (file plus line
range), and a few optional descriptors; an edge carries its kind, the qname it comes from, the
target both **raw** and (after the resolver) **resolved**, where the reference sits, and the
confidence tier that says how much to trust the link. Adapters emit edges **bare** — `target_raw`
is required, `target_qname` is the resolver's to fill (R3.3, §8.2).

**Why `extra['type']` is the return type too.** Properties already store a declared type under
`extra['type']`. Methods and functions now use the same key for their declared return type (contract
v7, task 144). An index built before return types and updated after would mix eras, so
`contract_version` bumps and forces a full rebuild — the same trigger as the v6 `INCLUDES` anchor
change (129). Spelling: [`CONVENTION.md`](CONVENTION.md) §3.

**Why `INCLUDES` anchors on the file.** `source_qname` for an include is the **including file's**
path, never the enclosing namespace (contract v6, task 129). The deciding argument is that the other
end already was one: the resolver joins `target_raw` onto the includer's *directory*, never onto
`source_qname`, so the target side had always treated an include as file-to-file and the source side
was the inconsistent one. Anchoring on the container made `include_graph(direction="imports")` answer
`[]` **with** `unresolved_includes: 0` for every file declaring a namespace — in a PSR-4 repo, every
file. Spelling and per-kind semantics: [`CONVENTION.md`](CONVENTION.md) §3.

**Why `args` records categories and never values.** `args` (contract v3, task 049) is one entry per
argument at a `CALLS`/`NEW` site, in source order: `null` for any non-literal expression, otherwise
the literal's **category**, never the literal. A value would make the graph a copy of the source and
a leak of whatever the source holds; a category is enough to answer *which call sites pass an array
here*. The whole field is **omitted when positions cannot be trusted** — a spread, a named argument —
or when the adapter does not record arguments; omitted means *unknown*, never *no arguments*.
`arg_keys` (contract v5, task 063) is parallel to it and follows the same discipline: keys, never
values, and an absent field means *not captured* (a pre-v5 index), not *none found*.

**Qualified-name convention** (identical across languages, adapter's job to honor): the **container**
keeps its language-native separator (`\`, `.`, `/`); the **member** boundary is always
`contract.MEMBER_SEPARATOR`. That is what lets one resolver serve every language. **JS/TS has no
namespaces** — symbols are module-scoped, so the qname is module-path–anchored, and that is the case
that pressure-tests the convention (see §4.4). Worked examples per language: CONVENTION §3.

**Capability flags** (ISP): adapter advertises optionals, e.g. `{"semantic_types": true}` (Roslyn) so the core can *use* richer data when present but never *require* it.

**Contract is versioned** (`contract_version` in meta) and covered by a schema-validation test each adapter must pass — this is what makes LSP-substitutability real.

### 4.3 Python-side abstraction (thin)
```python
class LanguageAdapter(Protocol):
    name: str
    extensions: tuple[str, ...]
    capabilities: dict
    def start(self) -> None: ...          # spawn sidecar, read the handshake
    def parse(self, path: str) -> ParseResult: ...   # {nodes, edges} or error
    def stop(self) -> None: ...
```
Concrete: **one** generic `SubprocessAdapter` — *not* a class per language. It is constructed with a configuration key and the launch argv, and everything language-specific (name, suffixes, capabilities) arrives in the handshake. A `PhpAdapter`/`TsAdapter` subclass would put a language name in the core, which is exactly what R1.1/R1.5 forbid, and would add a type with no behaviour of its own (R7.4).

The core resolves adapters by file suffix — `extension_index(adapters)` builds the map from what the adapters announced, `adapter_for(path, index)` reads it. **That's the only registry — a dict over already-constructed adapters, not a plugin system, and after adapter #2 it is the final answer (§19, R1.2).**

### 4.4 Project-context resolution — settled: no bump, neither option needed
The v1 protocol is **file-at-a-time** (`parse(path) → {nodes, edges}`). The best TS/JS and C# parsers resolve types only against a whole **program / tsconfig / project**, so this section anticipated the contract gaining either an adapter **lifecycle** (`open_project(root)`, program held in the sidecar) or a **two-pass** mode (adapter emits nodes + `IMPORTS`, core builds the file map, adapter resolves against it). **Both were measured unnecessary** — first the M0 spike (128), then all 13 of 149's constructs at scale (019): the adapter resolves each module specifier per file and emits the defining module's qname, a re-export barrel is followed through an `ALIASES` edge, and `CONTRACT_VERSION` never moved. Qnames stay module-path-anchored (`src/user.ts::User::save`) with `::` joining every member including a TS `namespace`; only the root token differs from PHP, which path-qnamed `File` nodes already permit.

Two facts settled it, both arriving later than this section. **One program per worker:** §8.1 fans a language's files across independent processes, so a lifecycle would load the program N times and would need a handshake capability capping that adapter's workers — data the adapter announces, never a branch in the core (R1.6). **Less to resolve than assumed:** name resolution is the adapter's job and node linking the core's (R3.3), and 137's local type table bought inferred receivers without touching the protocol at all.

**Live residual.** `open_project`/two-pass is wanted only for *type-inferred* receivers (`semantic_types`), the one 019 slice still deferred; a bump would be scoped there. Adapter #2 did force one **core** change — task 188 linked the specifiers it had already resolved to their `File` nodes (§8.2) — and it needed no new vocabulary, no new field and no language branch, so the seam held.

---

## 5. Architecture

```
Claude Code / any MCP client
        │ MCP (stdio)
 ┌──────▼────────────┐   contract (JSONL over stdin/stdout)   ┌──────────────────────────┐
 │  Core (Python /    │ ─────────────────────────────────────►│  Language adapter          │
 │  FastMCP)          │                                        │  PHP:  nikic/php-parser     │
 │  store · indexer   │ ◄───────────────────────────────────  │  (later) C#: Roslyn         │
 │  resolver · tools  │        {nodes, edges}                  │          Py: ast + jedi     │
 └──────┬────────────┘                                        └──────────────────────────┘
        │
 ┌──────▼───────────────────────────┐
 │  SQLite  .code-atlas/graph.db     │  nodes · edges · files · fts5 · meta   (WAL, incremental)
 └────────────────────────────────────┘
```

### Repo layout
The authoritative layout is [`CONVENTION.md`](CONVENTION.md) §1 — it is kept current and this plan
would only drift from it. In one line: `code_atlas/` is the language-agnostic core (`main` ·
`config` · `contract` · `adapter` · `store` · `indexer` · `resolver` · `enrichment` · `tools/` ·
`onboarding/` · `hooks/`), `onboarding_llm/` holds the opt-in LLM implementers **outside** the core
(R4.1), `adapters/<lang>/` is one self-contained sidecar per language, and `tests/contract/` is the
conformance suite every adapter must pass.

---

## 6. PHP adapter scope — the language standard (not any repo)

The adapter targets the **PHP language + ecosystem standards**, so it works on *any* PHP repo. It must handle the full PHP **8.5** grammar and semantics:

- **Namespaces & `use`**: declarations, aliases, group-use, function/const imports; resolve every name to an FQN.
- **All type declarations**: `class` (incl. `abstract`/`final`/`readonly`), `interface`, `trait` (+ `use`/conflict resolution/aliasing), `enum` (pure & backed), anonymous classes.
- **Members**: methods, properties (incl. promoted constructor params, typed, readonly), class constants, enum cases.
- **Functions & callables**: named functions, closures, arrow functions (`fn`), first-class callable syntax (`f(...)`), `static` closures.
- **The global namespace**: global functions and global classes are first-class — including classes whose names contain underscores (PSR-0 maps `Foo_Bar_Baz` ↔ `Foo/Bar/Baz.php`; this is a *standard*, not a special case).
- **Autoloading standards**: PSR-4 and PSR-0 name↔path mapping (read from `composer.json` when present, but resolution primarily uses **actual indexed declarations**, so it works even without composer).
- **Loading & references**: `include`/`require`(`_once`) as first-class edges; `new`, `extends`/`implements`, static/instance/function calls, class-const & static-prop access.
- **Attributes** (`#[...]`) captured on declarations (raw; framework *meaning* is the optional enrichment layer, not core).
- **Graceful degradation** on syntax errors (per-file), and on dynamic constructs (`$obj->$m()`, variable includes) via confidence tiers.

> Everything above is PHP-spec / PSR behavior — it holds for Laravel, Symfony, WordPress, ZF1, or hand-rolled procedural code alike. The adapter encodes **none** of those by name.

### 6.1 A large PHP monorepo as a validation sample (test target, NOT a design input)
Used only to size **test coverage** and **performance**, per §2 "Standard over sample":

| Sample fact | What it *validates* (not what it configures) |
|---|---|
| ~112k PHP files | scale/perf target for full build + incremental |
| `src/` PSR-4 + `legacy/` non-namespaced + `Zend/` underscore names | breadth: namespaced, global, and PSR-0-style resolution all exercised |
| Heavy `include`/`require` loading | the include-graph edges get real coverage |
| PHP **8.5** | confirms nikic ^5 handles newest grammar |
| No framework | confirms plain-PHP path; framework enrichment tested separately elsewhere |
| PHP not on host PATH (Docker) | exercises the runtime-invocation modes in §9 |

None of these appear as branches or constants in the adapter. Other repos (a Laravel app, a Symfony app, a tiny library) should be added as additional validation samples.

---

## 7. PHP adapter (`adapters/php/`)

- Parse with `ParserFactory::createForNewestSupportedVersion()` (8.5); add `NameResolver` so every `Name` carries a resolved FQN and declarations get `namespacedName`. **`NameResolver` writes those FQNs without a leading separator** (`App\Models\User`), while the qname convention (§4.2) is anchored at the global namespace (`\App\Models\User`) — the adapter prepends it. Note the parser is pure PHP: it parses 8.5 grammar on an 8.1+ runtime, so the host PHP version is a speed choice, not a grammar one.
- Custom `Visitor` (extends `NodeVisitorAbstract`, overrides `enterNode`) emits contract nodes/edges from: `Namespace_, Class_, Interface_, Trait_, Enum_, Function_, ClassMethod, Property, ClassConst` and edges from `extends/implements`, `TraitUse`, `MethodCall/StaticCall/FuncCall`, `New_`, `Use_`, `Include_`.
- Per-file `ErrorHandler\Collecting` → a bad file returns `ok:false`, never breaks the stream.
- Emits **bare** edges (targets are FQNs/names); cross-file linking is the core's resolver (§8.2) — a single file can't know all targets.

Sketch:
```php
$parser = (new ParserFactory())->createForNewestSupportedVersion();
$tr = new NodeTraverser();
$tr->addVisitor(new NameResolver($errors));      // FQNs + namespacedName
$tr->addVisitor($v = new \CodeAtlas\Php\Visitor($path));
$tr->traverse($ast);
echo json_encode(['path'=>$path,'ok'=>true,'nodes'=>$v->nodes,'edges'=>$v->edges]), "\n";
```

---

## 8. Build & resolution

### 8.1 Full build (`indexer.full_build`)
1. Collect files: `git ls-files` per adapter's extensions, minus ignore rules (§11). Walk fallback.
2. Reconcile: drop rows for vanished paths.
3. Fan paths across **N adapter processes** (`max(1, min(cpu-2, 8))` — the floor keeps a 1–2-core host at one worker); per result hash bytes, upsert `files`, replace that file's `nodes`+bare `edges`. Single SQLite writer.

**Bounding a silent adapter (deadline).** One watchdog thread per build arms a deadline of `CA_ADAPTER_TIMEOUT` seconds around every blocking adapter call — the handshake as well as a reply — and **kills the child** when it expires; the parked read then returns nothing and the driver raises. Disposition by call site: a **probe** boot that never announces is **loud** (no file is known yet, so there is nothing to record as unparsed — R5.3); a **worker** boot or a silent **reply** is **soft** — the worker retires or replaces its adapter, and the build returns. Every collected path leaves a `files` row, `parsed_ok=0` when nothing ever answered for it. Killing, rather than `select`, is deliberate: `select` does not work on Windows pipes.
4. Store `meta.last_commit`, `meta.last_ref` (077 — branch/ref name, or `HEAD` when detached),
   `contract_version`, `built_at`. `last_commit` / `last_ref` are **cleared** when git cannot name
   them (no repo, no commit yet) rather than left inheriting a prior build's stamp.
5. Run **resolver** (§8.2), then report. **`BuildReport` counts what the run *wrote*, not what the graph holds** (task 051). Steps 3–4 tally adapter output, but enrichment (§13) and the resolver both insert rows afterwards — synthetic ALIASES/CALLS, and one sibling per extra candidate at a multi-match call site — so a report taken from the parse tally alone understates the graph it just built: 949,808 against 1,775,812 stored on the anchor repo, and 3,481 against 4,373 on a public PSR-4 library. Both writers now return what they wrote and the report folds it in, so a full build agrees with `store.counts()` (what `get_index_status` reports) while an incremental run still reports its own delta. The MCP tool nests those under `wrote` so a delta cannot be mistaken for a repo size; `standard` also carries `store.counts()` as `graph` (task 060 — not on `minimal`, which stays cheap). Rule edges keep a synthetic `file_path` bookmark with no `files` row and no File node (task 068), so `files`/`parsed` stay aligned with `BuildReport`.
6. `nodes_fts` needs **no rebuild**: §10's triggers keep it current through every per-file replace, so a rebuild per build would cost a full re-index and change nothing. `GraphStore.rebuild_search_index` stays as the repair tool for a stale index.

### 8.2 Resolver (phase 2, generic — no language branches)
Runs after all nodes exist:
- `EXTENDS/IMPLEMENTS/USES_TRAIT/NEW/FuncCall`: `target_raw` is an FQN from the adapter → look up `nodes.qualified_name`, set `target_qname`, tier `RESOLVED`; leave NULL if external/vendor. A qname that appears in multiple files (§10) is linked **once**, still `RESOLVED` — the lookup is keyed by qname, so a hit means the name resolved, and an edge records a `target_qname`, never a node id, so "which declaring file" is not representable. **Revised by task 046:** this previously emitted one top-N `HEURISTIC` edge per declaring node, which produced rows identical in every column but `id` (38.8% of the graph on a monorepo carrying two regional copies of one tree) and downgraded 1.66M edges for a multiplicity that was never ambiguity. Every declaration remains a `nodes` row, so nothing is lost.
- Instance `CALLS` with unknown receiver type: match by **method name** across the index → one candidate = `HEURISTIC`; many = **one unresolved site**, candidates expanded at query time (258); dynamic (`$x->$m()`) = `DYNAMIC`, unlinked. *(Adapters with `semantic_types` capability — Roslyn — pre-resolve these to `RESOLVED`; the resolver just honors what's provided. This is how the same generic code serves both.)* PHP (task 029) emits FQN `target_raw` for lexically bound `$this` / `self` / `static` / `parent` when the enclosing class-like **declares** the method in-file (inherited / trait-mixin `$this->m` stays bare HEURISTIC so name-match still links). Tier convention: RESOLVED names the **declaration site** the file can prove (`$this`/`self`/`parent` at default tier); `static::` is late binding so it keeps the FQN but at `HEURISTIC`.
- `ALIASES` (task 030): adapter emits alias FQN → real class FQN; resolver links the real target like other FQN kinds, then remaps later CALLS/NEW whose `target_raw` is an alias onto the real class (transitively through alias chains, cycle-safe) so `find_callers` / `find_references` / impact see Alias users under Real. A stored `meta.contract_version` that lags `CONTRACT_VERSION` forces a full rebuild on incremental (never mix vocabulary eras).
- `REFERENCES` (094, widened by 232): a `Foo::class` mention is a `DYNAMIC` FQN edge; a named class type on a declaration and an attribute / decorator are `RESOLVED` ones. The resolver links both and **keeps** the incoming tier (`_weaker_tier`), so `skip_dynamic` still drops unlinkable `(dynamic)` CALLS/NEW/INCLUDES and never a `REFERENCES`. Variable-method dispatch stays unmodelled. Leftover unlinked `REFERENCES`/`IMPORTS` still feed `relationship_not_modelled` (065).
- **Path-shaped kinds** (`contract.PATH_TARGET_BASIS` — `INCLUDES`, `IMPORTS`): the target is a **file**, so the lookup is over `File` qnames, never by FQN, and the two kinds are disjoint from `FQN_EDGE_KINDS` so no edge id is double-linked. The contract declares how `target_raw` names the file — `INCLUDES` is includer-relative, `IMPORTS` is the repo-relative path the adapter already resolved (155) — so the resolver reads a declaration instead of sniffing a string (R5.2). **The discriminator is the graph:** a raw naming no indexed file stays bare, which is what leaves a symbol-shaped `IMPORTS` (a class FQN) unlinked with no language branch, and leaves an unresolvable specifier as honest `relationship_not_modelled` evidence (task 188). Variable include = `DYNAMIC`. `IMPORTS` carries `INCLUDES`' impact weight — a module dependency is a file-level dependency — so impact / reachability / orphans finally cross a module boundary.
- **Fan-out** is `CA_MAX_CANDIDATES` / `config.max_candidates` (default 50; `CA_MAX_RESULTS` aliases here). **Page length** is `CA_PAGE_LIMIT` / `config.page_limit` (default 50, query-only — 259).
- Linked tier is the **weaker** of the adapter's incoming `confidence_tier` and the lookup outcome: an FQN hit is would-be `RESOLVED` regardless of how many files declare it (task 046), while a **method-name** match is would-be `HEURISTIC` because those candidates carry genuinely different qnames. A resolved name never upgrades a guess (R5.2).
- **M4 scale:** per-edge `link_edge`/`insert_edge` commits and loading all unresolved edges into Python
  are addressed in task 015 — the resolver streams unresolved edges in batches and applies links in
  one transaction per batch. Multi-match name fan-out is gone (258); remaining candidate lookups stay capped by `CA_MAX_CANDIDATES`.

### 8.3 Incremental (`indexer.incremental_update`)
**Shipped (task 016).** Diff = `last_commit..HEAD` **∪** working-tree changes vs `HEAD` (so
uncommitted edits are visible to `full=false`). Add single-hop **dependents** (files with edges
into changed or departing symbols — including rename sources that git only reports as the new
path); reparse `changed ∪ dependents` (hash-skip only unchanged *changed* paths — dependents are
always reparsed so adapter tiers and duplicate keys stay intact); `resolve_edges`; bump
`meta.last_commit` / `meta.last_ref`. `build_or_update_index(full=false)` runs this when `last_commit` and the diff
are usable; otherwise it escalates to a full build and reports the mode that actually ran — or,
where that escalation is unbounded, answers with the route instead of starting it (201/202).
Staleness is `current | behind | incomplete | unknown` (commit equality; `behind` when the worktree
is dirty; `incomplete` outranks both after a build died mid-write, 202). Tests use hermetic throwaway repos so CI can keep a shallow checkout. Field retros saw
~62 s flat fee for no-op and small incrementals on a large index (task 052) — profile phases with
`scripts/profile_incremental.py --root …` (optional `phase_times` on `incremental_update`; not on
the MCP payload). **No-op short-circuit (task 080):** when the delta is empty (`to_parse` and
`removed` both empty), the late writers (`apply_indirection_rules` + full-graph `resolve_edges`) are
skipped — their output is already in the store and idempotent — so a true no-op costs only
collect+diff+hash and reports an honest `wrote:{files:0,parsed:0,nodes:0,edges:0}` instead of
re-derived siblings (the field's `edges:6071` at ~56 s). A *non-empty* delta still runs them
(correctness unchanged). The general small-delta case (a few files still pay a full-graph resolve)
would need delta-scoped resolver state (a schema change) and is a separate follow-up.

---

## 9. Running adapters given Docker (PHP not on host PATH)
`CA_<LANG>_CMD` is the **complete argv that launches the adapter in server mode** — interpreter, entry script and `--server`. The core appends nothing to it: completing a bare interpreter would mean knowing where a language's adapter lives, which is a language name in the core. Each adapter documents its own launch string (R8.1). A list in `.code-atlas.toml` avoids quoting entirely; a string is split for the host platform, because POSIX splitting eats the backslashes of a Windows path.

Configurable per adapter via `CA_PHP_CMD`:
- **A. Host PHP CLI (recommended for indexing).** Install PHP 8.5 CLI (tokenizer only — no app extensions). Native paths, fastest, no mapping. `CA_PHP_CMD="C:\\php\\php.exe adapters/php/index.php --server"` — on Windows prefer the list form in `.code-atlas.toml`.
- **B. Docker exec.** `CA_PHP_CMD="docker compose exec -T php php /app/adapters/php/index.php --server"`. The build always sends **repo-relative** paths; point the container service's working directory at the mounted repo so those open correctly — that is the Docker happy path. Optional `CA_HOST_ROOT` / `CA_CONTAINER_ROOT` only rewrite **absolute** host paths onto the container root (and the driver rebases echoed wire paths back to the caller). The indexer never passes absolutes today; the pair is for defensive/callers that do. SQLite stores caller-facing paths either way.

Default A; ship both. Each adapter is a subprocess documenting its own runtime (CONVENTION §5); C# will need the .NET SDK.

---

## 10. SQLite schema
`store.py` is the only module that opens the database (§2 SRP). Connection state, set **before any
transaction** (`foreign_keys` is silently ignored inside one): `journal_mode=WAL`, `foreign_keys=ON`,
`busy_timeout=5000`.

**The DDL is not copied here.** It is one `DDL` string in `store.py`, which is the only module that
may hold it; this section is the inventory and the reasoning. A dated column/index snapshot and its
rendered page are [`design/storage.md`](design/storage.md). What the schema is, in shape:

- **`files`** — one row per indexed path: content hash, whitespace-normalised `fingerprint`
  (task 213), language, `parsed_ok`, `updated_at`. The hash is the fast incremental path (§8.3);
  the fingerprint is consulted only after a hash miss and normalises **line endings and trailing
  whitespace only** — every newline survives, because equating two files whose lines sit differently
  would strand the `line_start` / `edges.line` the graph stores (R4.2). `parsed_ok` is why no
  parallel parse-failure counter exists (task 028).
- **`nodes`** — the symbols, keyed `UNIQUE(qualified_name, file_path)` and deliberately **not**
  globally unique (see below), with three indexes for the three ways they are looked up: by bare
  name, by kind, by file.
- **`edges`** — the relationships: kind, source qname, target both raw and resolved, site, tier, and
  the two optional argument columns. Four indexes, one per query direction the tools actually use —
  outgoing by source, incoming by target, by tier, and by `target_raw` for the pre-resolver and
  never-resolvable cases.
- **`nodes_fts`** — an **external-content** fts5 table over four `nodes` columns, mirrored by three
  triggers. The triggers are load-bearing, not an optimisation: without them every `MATCH` returns
  0 rows while `SELECT count(*) FROM nodes_fts` still reports the content table's size — a failure
  that looks like an empty repo. `tokenize='trigram'` (schema_version **2**) is what makes camelCase
  substrings match (`email` ⊂ `findByEmail`); unicode61 did not. Trigram cannot match terms shorter
  than three characters, so `search_nodes` falls back to a name/qname prefix `LIKE` for those and
  `DB` / `Us` / `Go` stay findable.
- **`meta`** — the key/value stamps. The keys are the `*_KEY` constants in `store.py`; they are not
  listed here, because the list kept here fell four keys behind the code (task 132) — the precise
  drift R6.7 exists to prevent.

**`qualified_name` is unique per file, not globally.** Two files in one PHP namespace each emit a
`Namespace` node with the same qname, and `if (!function_exists(…))` polyfills or legacy
re-declarations do the same for functions and classes — a global `UNIQUE` makes the second insert an
`IntegrityError`. Consequence for the resolver (§8.2): a qname lookup may return **one or more**
candidates, which is a `HEURISTIC` multi-candidate (§5 R5.2), not a lost row.

The *same-file* case is different: one file may legally declare a qname twice (a `function_exists`
guard's two branches, an `interface X` + `class X` fixture), which **would** trip the per-file
`UNIQUE`. `replace_file_rows` de-dupes by that exact key **keep-first** (source order, so it is
deterministic — R4.2) before insert, so a duplicate-declaration file soft-succeeds with one node per
qname rather than aborting the build (R5.1, task 043). NULL/anonymous qnames are never collapsed.

**`schema_version` is `"6"` and enforced loud.** On open, a database carrying a different value raises
— the DB is a derived cache, so there is no migration runner. Each bump names the task that
holds it: **2** `nodes_fts` trigram (camelCase substring search); **3** `edges.args` (049); **4**
`edges.arg_keys` (063); **5** `files.fingerprint` (213); **6** one unresolved site per call in place
of materialised Method-name siblings (258).

**The mismatch has a direction, and the two directions need opposite actions (task 050).** The stamp
is read *before* the DDL runs, so a database this build cannot read is never written to, and
`SchemaVersionError` carries `direction` plus the action that fixes it. An index **older** than the
server is a stale cache: `build_or_update_index` deletes and rebuilds it in-band. An index **newer**
than the server means the *server process* is stale — the index is current, and deleting it would
destroy a good graph to write an older one, so the build refuses and leaves the file untouched; the
fix is restarting the client. A stamp that will not parse is never treated as older. Every tool
answers a mismatch with `{error, index_schema_version, server_schema_version, direction, action}`
instead of raising — `get_index_status` in the `_unbuilt` family, the query tools through one
wrapper applied at registration (`main.build_server`). **No query tool rebuilds**: a `search_symbol`
that silently costs a full build is worse than the error it replaced.

**Determinism carve-out (R4.2).** `nodes.id`/`edges.id` follow insert order, which follows worker
completion order (§8.1), and `files.updated_at` / `meta.built_at` are wall-clock. The store takes an
injectable clock, and "identical input → identical rows" is asserted over row **content** ordered by a
stable key with the two id columns excluded. Ids are not stable identifiers — never store one.

**Column defaults apply when a field is absent.** Adapters may omit optional fields (§4.2), so the
store inserts only the fields a row carries; `is_test` and `confidence_tier` then take their DDL
defaults. A field present as `None` is stored as an explicit NULL.

---

## 11. Config & ignore

**Resolution order: env `CA_*` → project file `.code-atlas.toml` → default.** The file lives at the
repo root, is meant to be committed, and is read with stdlib `tomllib`; its keys are the env names
lower-cased without the prefix, plus an `[adapter_cmd]` table holding one complete argv per language
(§9). A malformed value or an unknown key **fails loud** (R5.3) — it never falls back. Naming rules
are in [`CONVENTION.md`](CONVENTION.md) §2, and **every knob, its default and what it governs is in
[`TOOLS.md`](TOOLS.md) *Configuration reference*** — the copy this section used to keep went two
knobs out of date, so it is not kept twice (R6.7).

Three knob decisions are design rather than reference, and stay here. `CA_MAX_RESULTS` caps both
the rows a tool returns and the resolver's candidate lookups (§8.2); 258 ended the job that sized
the graph. `CA_ORPHANS_MAX_NODES` is deliberately
**not** the impact budget, so tuning one cannot change which orphans exist (124). And `CA_<LANG>_CMD`
is resolved **generically from the variable name**, which is what keeps §9's launch mechanism from
naming a language in the core (R1.1).

**Ignore.** Built-ins (`vendor/ var/ uploads/ log/ node_modules/ .git/ *.blade.*`) + `.gitignore` +
optional `.codeatlasignore`, concatenated in that order with the **last matching rule winning**, so a
later source can re-include. A path below an excluded **directory** stays excluded — that is what lets
the walk prune a subtree. Supported gitignore subset: comments/blanks, `*` `?` `[seq]` within a
segment, `**` across segments, leading `/` anchoring, trailing `/` directory-only, `!` negation. Not
supported: nested per-directory ignore files, `\` escapes.

`git ls-files` already applies `.gitignore` on the primary path, so this matcher chiefly serves the walk
fallback **and** the census attribution (095): `skipped.ignore_sources` names the last excluding source
of each skip, **derived from the composition rather than hand-kept**, so the counts name what *this
matcher* dropped from the walked set. `*.blade.*` skips compound Blade templates on both `collect` and
`collect_stubs` (041) — the pattern names no language. Shared suffixes such as `.module`/`.inc` stay out
of the PHP handshake, because they are not PHP-owned and would index non-PHP bytes as junk File nodes
(R2.3). Non-UTF-8 sources fail that file softly into `parse_failures` (§4.1).

**Stub roots (039).** `CA_STUB_ROOTS` walks named dependency trees **outside** the ignore/git collect
path, so `vendor/` can be indexed without weakening directory exclusion. Those files are parsed
`declarations_only` (signatures + EXTENDS/IMPLEMENTS, no CALLS/NEW from bodies); nodes carry
`extra.stub=true` and surface as `stub: true`. Off by default; matching is case-sensitive; a root that
is missing, not a directory, or overlapping git-collected source fails loud (R5.3). `BuildReport.stubs`
counts them so a zero is visible.

**Indirection rules (040 / 062 / 063).** `CA_INDIRECTION_RULES` names repo-relative JSON files
**outside** `adapters/` (R2.2), each listing `aliases`, `calls` and/or `view_data` entries that become
HEURISTIC `ALIASES` / `CALLS` / `PROVIDES_VIEW_DATA` edges. Applied after parse, before
`resolve_edges`; off by default, so no rules ⇒ graph unchanged, and a missing or invalid rule file
fails loud **before** parse (R5.3). Rule edges live on a synthetic bookmark path with **no** `files`
row and no File node (068); nav hits carry `rule: true`. **v1 limits:** exact qname pairs for `calls`;
exact `target_raw` or `::<method>` suffix for `view_data` setters; one-line string-arg extraction only;
top-level literal string array keys only — `self::K`, `"$k"`, spread, nested arrays and
integer-like keys contribute nothing.

---

## 12. MCP tools (language-agnostic — same tools for every language)

Token-efficient: qualified names + `file:line`, not bodies, unless a read tool is called. The
**payload contract** — `detail_level`, the provenance fields (`index_root`, `last_ref`/`head_ref`,
`server_version`/`server_build`), the honesty fields (`reason`, `total_count`, `truncated`,
`walk_truncated`, `try_instead`, `resolved_qname`, `result_kinds`, `limit_capped_to`,
`result_subtrees`), and the batching rules — is specified once in
[`CONVENTION.md`](CONVENTION.md) §6 and is **not** repeated per tool below.

**The registered surface is [`TOOLS.md`](TOOLS.md), not this table** — it is the doc of record for
what each tool returns, and it is the one that stays in step. This table keeps only the *key args*
and the design decision behind each, for the tools whose shape a decision here settled; the later
tools (`impact_modules`, `trace_capability`, the architecture-rule and diagram tools) carry theirs in
their task files and [`design/`](design/). A per-tool count in prose here is R6.7's case: derive it.

| Tool | The decision this section settled |
|---|---|
| `get_index_status` | **call first (~100 tok).** `standard` carries a bounded `cross_language` census (no `pairs` — 243) on a multi-language index, `capabilities_by_language` for the languages it covers (231/244; omit when absent/empty), and the per-language `edge_health_by_language` verdict (`unlinked` / `by_tier` only — 261); `verbose` adds what must not ride the cheap path: capped `parse_failure_paths` (058), `collection` — the denominator for reconciling `files` against your own `git ls-files` without reading source (082) — and replaces that verdict with the full `edge_health_by_language` census including `pairs`, stamped per build and omitted under two buckets (183) |
| `build_or_update_index` | builds/refreshes; returns `wrote` (this run's writes) + timing, and at `standard` `graph`, so a delta isn't read as repo size (051/060). Every refusal is a payload naming its route, never a raise: a concurrent writer is `mode: "busy"` with the loser's staleness (072), no usable adapter `mode: "refused"` (064/079), and an unbounded escalation — a vocabulary era behind (201), or an index a killed build left incomplete (202) — the same way, in-band |
| `search_symbol` | FTS + name ranking; stub hits declare themselves (039); a zero hit may miss-repair the sole dirty file or report `index_stale` rather than answer a confident zero (073). **`queries` sweeps N subjects in one call** (101). At `standard`, a `Column` FK hit names its target from existing `REFERENCES` edges: `references` (resolved column) or `references_unresolved` (table only, R5.6) (239) |
| `file_outline` | line ranges, never bodies — the read is a separate, priced call |
| `read_symbol` | docblock at `standard`, none at `minimal` (163); stubs declare themselves (039). A qname with >1 definition **refuses the body** and lists the candidates rather than picking one (070 → 078). At `standard`, a **callable** hit carries `params` (name + declared type) when the language stamps capture — else `params_not_captured_by_adapter`, never a lying empty list; a non-callable kind carries neither (242). A **Table** pages `columns` from `CONTAINS` (248). `stored_fields` lists populated node/`extra` keys only; Column always lists both 239 FK lists (250) |
| `find_callers` | opt-in capped call-site source (037); `args_unrecorded` on the argument filter (049, depth 1). Opt-in `confidence_tier` is a store predicate, never a post-page filter; default order unchanged (251). An empty linked answer may expand to proximity-ranked unresolved same-named sites — `reason=proximity_candidates`, never `ok`, each row naming `candidate_of` (258). Depth 1 enumerates completely; deeper, `total_count` is a floor. Unmodelled `*->L` ⇒ `authoritative: false` even with hits (238) |
| `find_references` | CALLS/NEW plus `REFERENCES` (`Foo::class`, 094). All-`DYNAMIC` page ⇒ `authoritative: false`. A Class with unlinked refs and CONTAINS children returns member CALLS/NEW as `via_members` (never `ok`; 252) |
| `find_implementations` | EXTENDS/IMPLEMENTS, resolver-linked only |
| `find_view_data` | the `PROVIDES_VIEW_DATA` relation (062/063). With no `view_data` rules configured it says so, rather than reporting a modelled zero (069) |
| `include_graph` | the `include`/`require` graph; `unresolved_includes` on `imports`/`both` only — a counter that is structurally zero inbound is omitted rather than printed (065) |
| `impact` | bounded best-score over resolver-linked IMPACT kinds; `seeds_dropped` (see below) |
| `subtree_dependencies` | attributable and unattributable crossings are always paired, so neither can be read alone; dynamic bridges surfaced (120) |
| `reachable_from` | what is reachable from `CA_ENTRY_POINTS` over RESOLVED IMPACT kinds; HEURISTIC/DYNAMIC neighbours are `unproven`, not reachable |
| `find_orphans` | the complement, each row carrying its `why`; never an empty success when no roots are configured |
| `explain_path` | shortest A→B over outgoing IMPACT kinds, with a five-value `status` so a bound hit is never conflated with "no route" |
| `architecture_overview` | responsibility layers ordered by **net dependency direction**, which is a derived fact, not a naming convention |
| `guided_tour` | a dependency-ordered reading list, seeded from zero-inbound entry points and cycle-safe via SCC condensation (087); seeds prefer out-degree > 0, capped at a quarter of the budget (106), ready-set ordered by reading-seed layer rank (131) |
| `generate_onboarding` | the committable artifact, from the same graph (088/089/116). It removes only the pages its own last manifest recorded, and refuses a tree it does not own |

*Considered and not planned:* `namespace_tree` (013/014, never built) — `search_symbol` already takes
a `namespace` filter and `architecture_overview` answers repo shape; §19's founding-premise benchmark
found the gap is **demand, not capability**. A scanned tool surface has a budget (081), so re-propose
it on a field question no shipped tool answers.

**Claim signing — `sign: true` on the five attesting tools (100).** An attestation that never reaches
the artifact where the claim is made has, practically, not been produced: the round-5 session pasted
nine kinds of counted evidence into its PR and **zero** code-atlas output. `impact`, `impact_modules`, `find_callers`,
`find_references` and `get_index_status` therefore take `sign: bool = False`, adding one `claim` key —
a single `key=value` line naming tool, subject, question, answer, the revision the index describes and
the running server. `claim.py` is a **pure formatter** over an already-computed payload, so R1.4/R4.1
hold by construction and key order is fixed for R4.2. **Every caveat owns its own key** — `tier` names
the *weakest* tier present, plus `index=behind`, `authoritative=false`, `truncated=true`, `reason=` —
so a degrading answer cannot drop one the way a prose clause can. **No line is emitted** for an unbuilt
index or an `impact` answer where no seed resolved: a claim that cannot be re-run is decoration. The
rest are not signed: their answers are lists of rows rather than claims. (A count kept here in prose
would drift the moment a tool lands, which is R6.7 — the signed set is the five above.) Measured cost: **+51
tokens** on `impact`, **+46** on `find_callers`; default payloads byte-identical (061).

**`seeds_dropped` counts every requested subject that produced no seed (102).** An absent qname, one
that resolves to many, a path with no indexed node, and any seed the node budget pruned all count. So
`results: []` with `seeds_dropped: 0` means a **modelled zero and nothing else** — the claim `impact`
exists to make and text search cannot. When *every* named subject was lost the answer also carries
`reason` through the same `shape_exact_miss` machinery as 075/076/092; a merged multi-subject radius
states only the base class it can prove for every subject, because it has no per-subject reason channel.

**Sweeps — one call for a list of subjects (101).** *"Are any of these ten names already taken?"* was
ten calls, so the round-5 session ran `grep -rn` instead. Cost was not the complaint: **ten calls is
the wrong granularity for one question**, and any tool answering *"is this name taken"* loses to a
shell loop until it takes a list. `search_symbol` accepts **`queries`** beside `query` (never both) and
answers `subjects`, one entry per subject in the caller's order — never a merged set, which is 070's
defect at batch scale. Fan-out is bounded by **`CA_MAX_SUBJECTS` (default 25)** and disclosed: a sweep
exists to be complete, so a silent truncation is worse than ten honest calls. Two costs are stated
rather than hidden — the subject is no longer schema-`required` (two spellings, so neither can be), and
a sweep shares **one** read-through repair budget. The measured token win tracks `index_root`'s length
and so does not generalise; **the argument is shape, not cost.** Only `search_symbol` batches (R1.2).

**Ambiguous qnames — warn, never scope (070); refuse the body (078).** A qname is not unique: on the
anchor index 22,261 qnames have more than one definition. Nav tools merge their callers and disclose
`ambiguous_definitions`; `read_symbol` refuses to return a body at all, because a warning field beside
a body is ignorable and the agent reads the body. Scoping by file was rejected as a surface the caller
cannot be expected to know it needs.

**Descriptions are question-first (069).** Each tool's inner-fn docstring *is* the description a client
reads (CONVENTION §6), opening with the question the tool answers, not its mechanism. The blind
recognition probe that scores whether they route is
[`runbooks/tool-recognition-probe.md`](runbooks/tool-recognition-probe.md) (081, 097). **The bound
(099):** no description reaches an agent that never opens the tool list.

**Operator prompts, not agent routing (081).** An agent's client surfaces only *tools* to the model,
so a prompt is a human-invoked recipe and routing for agents lives in the descriptions above. Counting
a human-facing channel as agent-facing was a category error, not a bug — which is why 200 had to
*generate* `which_tool`'s map into a channel a model does read, rather than improve the prompt.

**Serving (010).** `main.build_server(config)` registers the allowed tools on one FastMCP app and
`main()` serves it over stdio; the entry point is `code-atlas` (or `python -m code_atlas.main`).
`CA_TOOLS` gates the surface. Each call opens its own `GraphStore` — see CONVENTION §6 for why.


### Impact engine
code-review-graph's **bounded best-score relaxation in SQLite**: seed = changed qnames; per-edge-kind weight/direction policy (`CALLS/NEW`→callers, `EXTENDS/IMPLEMENTS`→subtypes, `INCLUDES` follows requires, `CONTAINS` not traversed); one best score/node, decay per hop, floor, bounded by depth & max_nodes; `DYNAMIC` edges excluded by default.

### Reachability / orphans (task 031)
Inverse of impact: `CA_ENTRY_POINTS` names file/glob roots (every indexed node on matched files is a seed). Globs use the **same segment-aware language as ignore** (`*` stays in one path segment; `**` crosses). `reachable_from` walks **outgoing** `IMPACT_KINDS` with the same RESOLVED-only frontier rule; default `depth` is **unset** (closure until frontier empties or `CA_IMPACT_MAX_NODES`); an explicit `depth` sets `depth_exhausted`/`truncated` when hops remain. A reached member keeps its container qnames alive (`split_qname`) so classes are not orphaned when only methods are called. HEURISTIC/DYNAMIC neighbors are `unproven`, not reachable. `find_orphans` returns the complement with `why` (`no_inbound` | `unreachable_from_roots`); unset roots → `no_roots_configured`. Its reachability walk is bounded by **`CA_ORPHANS_MAX_NODES`**, never borrowed from impact, so tuning one cannot change which orphans exist (124). The walk's own budget is disclosed separately from the row page (`walk_truncated`, §19 round 6) — unreached nodes inflate an orphan count, and a reader must be able to see that they did.

### explain_path (task 038)
Shortest path from `from_qname` to `to_qname` over **outgoing** `IMPACT_KINDS` (same relation set as impact/reachability). Iterative SQL BFS with parent pointers — never a whole-table edge load (R4.3). Caps reuse `CA_IMPACT_MAX_NODES`; default `depth` unset (closure). **RESOLVED-first:** a proven path is preferred; a path that exists only via HEURISTIC/DYNAMIC hops is `status=unproven`. Missing endpoints → `unknown`; bound exhaustion before `to` → `incomplete` (never conflated with `no_path`); both present with no route → `no_path`. Same-qname → empty proven path.

---

## 13. Relationship to LSP-based tools
| Need | Use |
|---|---|
| Go-to-def, precise find-refs, rename, types | **an LSP-based tool** |
| Fast symbol search across 100k+ files | **code-atlas** |
| Read one method w/o whole file; impact/blast radius; include graph; global-namespace symbols | **code-atlas** |
| Editing | Native Edit + LSP symbolic edit |

Coexist in `.mcp.json`. If tool overlap annoys, trim the LSP tool's search tools via its context/mode, keep it for nav/edit.

---

## 14. Phase 3 — Onboarding feature (Understand-Anything style)

**Shipped (M10–M12, §15).** Not a fork of Understand-Anything — a **consumer of the graph already
built**, which is the substrate UA spends its whole pipeline producing, at higher fidelity than
tree-sitter, and multi-language for free. Full detail in
[`phase3-onboarding/ROADMAP.md`](phase3-onboarding/ROADMAP.md).

It adds two things the graph lacks, and **both landed differently than this section first assumed:**

1. **Semantic layer.** Layers turned out to be **deterministic** — 110's ratified responsibility
   vocabulary names them, and 117 measured that 091's LLM rename seam fires on nothing. The LLM ended
   up owning **prose only** (layer descriptions, tour narratives, headline wording) behind three
   opt-in seams in `onboarding_llm/`, off by default. 118 fed the summary seam real facts, and 205
   then deleted the per-module page tree it wrote onto — summaries now ride tour modules only.
2. **Presentation.** 116 replaced the imagined page dump with a **navigable system map** rendered from
   112's single compact dataset.

The discipline held throughout: **deterministic graph (core) → LLM enrichment (onboarding) →
presentation.** The LLM touches only the onboarding layer, is off by default, and lives outside
`code_atlas/` (R4.1, CI-gated). Surface: `architecture_overview`, `guided_tour`,
`generate_onboarding`, writing `docs/onboarding/` with a versioned `artifact.json`
(`ARTIFACT_VERSION`, gitignored under `.code-atlas/onboarding/`). **What the phase is measured as, after 121: a navigation and provenance
aid, not a reading order** (§19). One surface follows a single capability *running* rather than
aggregating — `flows.md` (197), one trace per capability; 225 renders each trace as a mermaid
`sequenceDiagram` beside its `flowchart LR`, in call order (the trace now carries `edges.line`) and
disclosing every hop whose order it cannot prove.

---

## 15. Milestones

**Phase 1 — Core + PHP (make it work):**
- **M0** Adapter spike: PHP `--file` parses a namespaced *and* a global/underscore(PSR-0) file → valid contract JSON.
- **M1** Full build: streaming adapter + N workers + SQLite; `get_index_status`.
- **M2** Resolver + contract tests; `find_callers`/`find_references` correct on a known symbol.
- **M3** Read/search/outline + FTS. **← ship for daily use here.**
- **M4** Full-language coverage + scale: global-namespace & PSR-0 resolution, `include_graph`, the 112k-file sample end-to-end.
- **M5** Incremental + git; staleness in status.
- **M6** Impact engine + `impact` tool + prompts.

**Phase 2 — More languages** (T-SQL took M7's slot ahead of Python, §19):
- **M7** **TypeScript/JavaScript adapter** (TS Compiler API, Node sidecar) behind the *unchanged* core — the real test of OCP/DIP. Landed (019) with no contract v2 and no core registry (§4.4, §19).
- **M8** **Python adapter** (stdlib `ast`) — tier 1a (020) and tier 2 (217) landed; the residual is type-inferred receivers (`semantic_types`), the same one TS/JS carries.
- **M9** **C#/.NET adapter** (Roslyn sidecar) — deferred (§3, §19).

**Phase 3 — Onboarding** (deterministic-first; LLM opt-in and out of core + CI). All three milestones
are **complete**; the per-task breakdown, including the 108–117 reshape, is in
[`phase3-onboarding/ROADMAP.md`](phase3-onboarding/ROADMAP.md).
- **M10** `architecture_overview` + deterministic layers — 083 · 084 · 085 · 103 · 104 · 086. The 15th tool; 105 elects the dominant subtree by graph mass, proven on three pinned repos.
- **M11** `guided_tour` (16th) · `generate_onboarding` (17th) · the viewer — **reshaped by 108–117 into the navigable system map**, rendered from 112's dataset alone. 116's AC4–AC6 are proven by running the page headlessly under `tests/viewer_dom_stub.js`, because a grep over the HTML sees zero rendered figures and would be a false green.
- **M12** LLM enrichment, opt-in and outside the core — 090 · 091 · 117. The prose ceiling is **derived, never listed** (R6.7): `prose.MAX_PROSE_CALLS` sums `SLOT_LIMITS`, so a new slot moves it and no doc goes stale. It is enforced **per slot**, so a repo falling back to per-directory layers cannot starve the tour (measured at 18,929 files: 1,176 requested, 12 served, 1,164 refused).

---

## 16. Testing
- **Contract-conformance** (`tests/contract/`): every adapter must pass — fixtures per language asserting the emitted JSON matches the schema and known node/edge counts. This is the LSP-substitutability guarantee.
- **PHP language coverage** (spec-driven, not repo-driven): namespaced / global / underscore(PSR-0) / trait+conflict-resolution / enum / attributes / closures & arrow-fns / first-class-callable / include / static-vs-instance-call / syntax-error fixtures.
- **Core integration**: build over fixtures, assert a resolved caller chain; assert **zero language branches** in `code_atlas/` (grep gate in CI).
- **Cross-repo validation** (proves "works on any repo"): run the adapter against *several varied* PHP repos — a Laravel app, a Symfony app, a small PSR-4 library, and a large PHP monorepo — asserting no crashes and sane node/edge counts. The large monorepo is one sample among several, not the definition of correct.
- **Correctness**: known class → `find_callers` vs a manual baseline (accounting for dynamic calls).
- **Scale/perf & determinism**: time full build on the 112k sample; identical rows for identical input.

---

## 17. Risks & mitigations
| Risk | Mitigation |
|---|---|
| **Adapter tuned to a sample repo** (breaks "works on any repo") | "Standard over sample" (§2): adapter encodes only the language spec/PSRs; CI grep-gate bans repo/framework names in adapter source; cross-repo validation (§16). |
| PHP process startup × 112k | Long-lived streaming adapter + N workers. |
| Dynamic PHP (`$obj->$m()`, magic, variable include) | `DYNAMIC` tier, excluded from traversal; name-based `HEURISTIC` fallback. |
| No type inference for PHP instance calls | **Closed by [137](tasks/137_php-local-type-table.md)**: the HEURISTIC share fell to **1.1 / 3.9 / 2.6 %** across the three pins, with no call site losing a target — [benchmark](benchmarks/137_type-table.md). What is left is the late binding 136 predicted, which is the LSP defer's ≤0.6 %, plus receivers whose declaring member is unindexed (136's `vendor/` cap, unchanged). C# gets it free via Roslyn capability. |
| PHP 8.5 edge cases | nikic ^5 latest; collecting handler flags `parsed_ok=0`. |
| Host PHP absent | Docker-exec mode (§9-B) or tokenizer-only PHP CLI. |
| 100k-file DB/memory | SQLite WAL, serial writer, indexed queries, caps; traverse in SQL, never load whole graph. |
| Overlap with LSP-based tools | Clear division (§13); optionally trim the LSP tool's search tools. |

---

## 18. Open questions for review

Six of the original eight are **closed** and recorded where they were decided: the language order and
its deferral (§3, §19 pivot), the PHP *and* TS/JS validation repos (018 · 150 — public pins in
`scripts/cross_repo_samples.json` plus an operator-local monorepo via `CODE_ATLAS_SCALE_SAMPLE`), the
ship point (M3, task 014 — shipped), onboarding presentation (both: committed markdown *and* a
viewer, §14), and schema-state awareness (**no, permanently** — §19, 2026-08-30). Still open:

1. **PHP runtime** — both modes ship (§9); is a host PHP 8.5 CLI acceptable for indexing, or is
   Docker-only the standing answer?
2. **LSP-tool coexistence** — keep a language server's PHP search tools on, or trim to nav/edit?
   §13 says they are not substitutes and the founding-premise benchmark could not make an agent
   choose, so this stays a per-installation preference, not a project decision.

---

## 19. Project context & decision log
> This is the durable record — kept **in this plan**, not in any external memory store. Do not use the Claude Code Memory feature for this project; decisions live here and in the repo.

**What & why.** Build a local-first, multi-language code-intelligence MCP (`code-atlas`) ~~because native Claude Code tools and grep are weak at language-specific, name-resolved search on large repos~~. It indexes into SQLite and serves fast, token-efficient search/read/nav/impact tools.

> **The struck clause was the founding premise and it was measured false on 2026-08-08.** It is kept, struck, as the historical motivation rather than deleted, because every decision below was taken under it. What replaces it is narrower: **the index sells resolved relationships, not search speed.** See *Founding-premise benchmark* at the end of this list.

**Decisions locked so far:**
- **Architecture** — language-agnostic core + per-language adapters, each using the language's best parser, joined by one frozen/versioned JSON contract (§4). Engine lineage: code-review-graph.
- **T-SQL ordered ahead of Python and C#/.NET — 2026-08-30, reversing the order below.** Not on
  breadth (which ordered 019/020/021) but on **measured in-anchor demand**: a field retro found the
  decisive fact of a critical-path ticket inside 378,790 lines of T-SQL the index does not read, and
  **tier 1a costs zero contract vocabulary** (`Function`/`CALLS` exist). Honest counter-case: `n = 1`
  repo. The retros hold the round-by-round demand; adapter #2's zero was **roll-out** (an absent env
  var), not absent demand.
- **Task 022's evidence gate: discharged, not widened — 2026-08-30.** §1 asked for a second
  independent repo, and is scoped to the *schema-state* question §18.4 closed permanently, so it no
  longer describes the ticket. Its premise — nothing every user inherits — survives and is answered
  by proof: `Table`, `Column` and `WRITES` (**v9**) join **no** existing named subset, so a repo
  with no `.sql` is unchanged. §1's text stands; round 12's four tickets are demand, not a repo.
- **Language order and its rationale** — §3's table. Ordered PHP → TS/JS → Python → C#/.NET, deferred behind PHP agent-depth 2026-08-04, T-SQL inserted ahead of Python 2026-08-30; #2–#4 have landed and only C#/.NET remains.
- **Native Windows runtime taken — 2026-09-10, superseding 220's `unsupported`.** A
  `sys.platform`-selected lock arm keeps POSIX byte-identical and 072's property. Tiered: native
  runtime supported, WSL2-on-ext4 for heavy indexing, dev/test loop stays POSIX. 220 fused "cannot
  import" (one `fcntl` import) with "slow" (Defender scan, not the
  disk); detail + evidence in [237](tasks/237_native-windows-was-declined-on-a-defender-setting-not-a-platform-limit.md).
- **SOLID at the boundaries + YAGNI** (§2) — one seam (the contract). The registry question is settled: see the R1.2 verdict below.
- **Standard over sample** (§2) — adapters implement the language spec/PSRs only; sample repos drive test coverage & perf targets, never adapter semantics. CI grep-gate bans repo/framework names in adapter source.
- **Priorities** (§0): make it work (PHP) → extend without touching core → onboarding feature.
- **Onboarding** (§14) is **Phase 3**, a graph *consumer*; the core stays deterministic and the LLM
  prose seams live outside it (R4.1). Shipped M10–M12.
- **LSP-tool coexistence** (§13) — code-atlas is the indexed search/impact layer; a language server stays for LSP nav/edit.

**Decision — Agent-first PHP-depth pivot (adopted 2026-08-04; source: [`FEEDBACK.md`](FEEDBACK.md)).**
The consumer is an **AI coding agent in a terminal**, so the incumbent to beat is
`grep + Read + context`, not a language server.

- **Metric.** Success is **tokens-to-correct-answer vs a grep+`Read` baseline** on a fixed question
  set — not precision-vs-LSP. The harness comes before any accuracy claim (034).
- **Machine-trustable responses first.** Empty ≠ unknown: every `find_*`/`search` answer carries a
  reason code and `total_count`, and a subject the index has no exact node for is **classified before
  it is answered** rather than returned as a confident zero (033 · 065 · 075/076 · 092 · 122 — the
  vocabulary and the full payload contract live in [`CONVENTION.md`](CONVENTION.md) §6). Freshness is
  **enforced, not surfaced**: inline reparse on hash drift with a per-call cap (035), zero-hit
  miss-repair (073), and opt-in host hooks for edit and checkout (036 · 053), never auto-installed.
- **Fewer round-trips beats fewer rows.** `find_callers`/`find_references` take an opt-in
  `include_source` riding each site's own source line — **180 vs 251 tokens (−28 %)** for the identical
  answer with one round-trip removed, and **107 vs 176 (−39 %)** counting relation calls alone (037).
  **Consolidation was measured and rejected — on smallness, not on a loss:** one
  `find_relations(qname, relation)` saves 241 schema tokens once and costs 6.75 per call, so it wins
  below ≈36 relation calls per session and loses above, a spread of only −234…+434 tokens over 1–100
  calls. No net win ⇒ R1.2 holds, reinforced by the unpriced cost of one muddier description. The A/B
  lives in `scripts/relation_surface_ab.py`; `find_relations` was never shipped.
- **Depth over breadth — reversed for 020, 2026-09-04.** 019/020/021 were deferred behind the PHP
  agent-loop (human-ratified 2026-08-04, the private PHP monorepo being the anchor for testing *and*
  evaluation). **020 un-deferred by maintainer decision**, without the field-measured demand the
  T-SQL reorder above required; **021 stays deferred.**
- **Editing permanently ceded** to the agent's native `Edit`/`Write` (§1). code-atlas serves exact line
  ranges; it never mutates code.
- **Framework magic stays an enrichment layer** (§1 non-goal) — vendor stubs and indirection-as-data
  (039 · 040), sequenced *below* the response-shape work: an agent can verify a shallow edge by reading
  one file, but cannot recover from an empty array it misread as proof.
- **Open risk (recorded, not resolved).** At the limit this resembles a language server, and a better
  PHP language-server backend might reach further. We still go depth-first — live LSP indexing of tens
  of thousands of files is the founding complaint and no backend fixes an architecture — but the
  objection is acknowledged, and 034 is what keeps us honest about it.
- **Cheap unblocker (done):** resolve the license — an unlicensed MCP server does not get installed (032).
- **Field-report validation (2026-08-05; [`FEEDBACK.md`](FEEDBACK.md) Round 4).** A parallel agent
  fan-out over worktrees OOM'd on resident-LSP servers (~5.6 GB each, pointed at `main`). code-atlas
  does **not** reproduce the *memory* half — no resident server, SQLite opened per call. It **does**
  reproduce the *routing* half; both halves are measured in the next entry.

- **Memory & concurrency field run (2026-08-09, `869dcc6`; 16-core / 27.8 GB Linux).** N = 1/2/3/5
  servers, 4,500 calls at N = 5. **The memory thesis holds with room to spare:** the n-th agent costs
  **~70 MB PSS** and the 925 MB index costs **0 MB** — `graph.db` is never mmapped and no descriptor
  outlives a call, so it is resident once in the page cache, shared and reclaimable. Five agents =
  1.3 % of RAM at **4.3×** single-agent throughput; 452 drift events, zero `index_stale` soft-fails,
  zero `SQLITE_BUSY` reaching a caller. **Correction to the entry above:** a `cwd`-relative `db_path`
  does **not** give a worktree agent its own index — the dispatched registration bakes `cd <main repo>`
  into the server command, and a two-marker probe showed a worktree agent asking about its own path and
  receiving the main checkout's symbol with `reason: "ok"`. Shipped 071 (`index_root` on every
  payload); `CA_DB_PATH` remains the recommended isolation. Recipe:
  [`runbooks/parallel-agents.md`](runbooks/parallel-agents.md).

- **Field retro round 4 — the first verification round (2026-08-10, `e8f56d0`).** Eleven fixes from
  rounds 2–3 were in the binary and none had been seen by an agent doing real work: **7 verified
  fixed**, 2 improved, 1 reproduced (054), 2 not exercisable — under three recorded caveats that void
  its recognition test. **The two findings that mattered came from outside the verification section**,
  which is a regression harness and cannot surface anything new: 075 and 077. The round's caveats,
  both findings and its self-corrections are in those task files and
  [`BACKLOG.md`](BACKLOG.md#where-these-tickets-came-from).

- **Qname-subject honesty — 075 + 076 shipped together (2026-08-11; one shared design).** A
  **malformed** subject and an **under-qualified** one were one defect class: both read as *absence*.
  One language-agnostic classifier (`nav_result.classify_missing_subject`) serves all seven qname
  tools, keying off the generic identifier class rather than any language's separator (R1.1).
  **Decision: no adapter `contract_version` bump** — nav `reason` codes are tool-output vocabulary
  (`nav_result.NAV_REASONS`), not the adapter JSONL contract, and bumping it for a tool string would
  force every user to reindex for nothing.

- **Field retro round 5 (2026-08-14, `348a8a7`) — the first round with mechanism questions, and the
  first where cost changed what was asked.** **8 of 8 checked claims exact, zero false statements:**
  every failure was silence or ambiguity, never a wrong answer, which is why §10's carve-outs are
  narrow. Three things no earlier round could establish:
  - **Cost shapes behaviour, not just the bill.** Under 1 % of session tokens but **181.7 s** of
    in-work build time, the cliff entirely between zero files and one (0 → 2.1 s, 2 → 59.25 s). The
    evaluator batched 8 calls at the start, 7 at the end, **1 in three hours of writing code** →
    **096**, which scopes late resolution on what the delta *declares*, not on which files it touched.
  - **Recognition ≠ recall, and the probe only measured recognition.** It scored 14/14 while 7 of 14
    descriptions were never loaded, so 081's mechanism was never exercised → **097** split the probe
    into name-only and description-backed rates. **Descriptions can name an occasion; they cannot make
    an agent notice it.**
  - **Two independent nothings were indistinguishable** (**092**): untracked new classes were invisible
    to `collect()`'s `git ls-files` walk, `dirty_indexed_files: 0` was literally true and actively
    misleading, and the lookup said `no_such_symbol` for a class on disk while the vocabulary already
    owned `not_indexed`. Shipped with 093, 094, 095.

  **Open, not ticketed:** nothing searches unlinked include text, so *who includes this file* stays
  unanswerable when the path is dynamic.

- **Field interview — "the questions you did not ask" (2026-08-14, same session).** Six questions about
  the moments the evaluator **did not** call the tool. **Weight it as one observer, not two** — the
  interviewee authored the retro an hour earlier and declares itself contaminated; it survives because
  it inventories *non-events*, which no retro asked about. Three durable results:
  - **A retro cannot audit itself.** It retracted the round's headline (a story resting on PHP method
    names being case-sensitive; they are not). A same-session interview is the cheapest instrument
    that can catch that.
  - **Adoption is a *position* problem, not a speed problem.** All three decisions made without the
    graph wanted **one line inside a `Read` already happening**, none wanted a tool call. Shipped
    (099), and the verdict is a position statement: the signal lives in the **host's hook surface**,
    never on a payload rider — `next_tool_suggestions` reaches the agent *after it asks* and the core
    cannot observe a `Read`, so that channel is **structurally** incapable of carrying this, not
    merely too expensive (061). code-atlas offers the command and wires nothing. The ceiling this
    records on 069/081-style routing work: *no description reaches an agent that never opens the tool
    list* — which is why 097 and 099 are one finding from two sides.
  - **The evidence-layer thesis has behavioural proof, against the evaluator's own interest:** the PR
    body pasted nine kinds of counted evidence and zero graph payloads (→ **100**), and a ten-subject
    sweep went to a shell loop because the graph took one subject per call (→ **101**).

  **The one judgement the interview cannot make for us:** the anchor's dominant chore is porting a
  legacy file into the unified tree without breaking the other region, and the graph holds **neither**
  relation that chore is made of. Its proposal — seed the first from a ~4,300-entry mapping the repo
  maintains — is **adopted in principle, rejected as proposed**: ingesting a repo's own mapping file is
  sample-over-standard (R2). What the core may learn is one **generic correspondence relation**,
  config-fed and adapter-blind, under which legacy↔unified and region-A↔region-B are the same
  primitive → [098](tasks/098_correspondence-relation-seam.md), deferred behind the evidence gate below.

- **Phase-3 reshape (2026-08-20; tasks 108–117) — a human read the emitted artifact and it was
  unusable.** M11 passed every test and failed its reader: 43 MB, a median module page of 82,218 bytes
  that was 99.96 % flat path lists, `Summary: (none)` on 500/500 pages. **The decision it forced is an
  audience split: the MCP tools are the product for an AI, the onboarding artifact is the product for
  a human.** 116 measured that 108 had already removed ~97 % of the size, so *"data dump, not a map"*
  was the whole of the complaint. Two R2.2 judgments settled: a generic architectural vocabulary **is**
  a standard (110, maintainer-ratified), and 113 needed no separate vendor signal because that
  vocabulary already carries `vendor`. Mockup and waves:
  [`ONBOARDING_MOCKUP.md`](phase3-onboarding/ONBOARDING_MOCKUP.md) ·
  [`ROADMAP.md`](phase3-onboarding/ROADMAP.md).

- **Field measurement on the anchor (2026-08-21) — two things the shipped map could not say.**
  Regenerating on 18,972 modules / 135,649 symbols took 17 s for a 950 KB map, 500 pages at a median
  2,943 B (against 82,218 B before 108). **118** — the `Summary: (none)` cause was a **contract gap,
  not a seam gap**: the graph had nowhere to carry a docblock, so the deterministic summarizer was
  starved on *every* repo and the opt-in LLM implementer with it. **119** — a stale `CA_ENTRY_POINTS`
  glob put 560 unreachable files in *Web entry points* and nothing in the output could expose it;
  correcting the knob moved the bucket 901 → 341. *Classification changed; no fact did* — which is the
  argument for provenance beside a count.

- **Field retro round 6 (2026-08-21) — four findings, all payload honesty, none a graph defect.** Its
  own closing line is the finding: *"the graph knew everything I asked it; the failures were the tool
  knowing and not saying how much it was not telling me, and the tool knowing and declining over
  punctuation."* Two lessons outlive the tickets. **A sibling surface is closed by an enumerating test
  over the shared caller, not by a prose verdict** — 075's verdict left four `find_*` tools still
  discarding its resolved qname inside `shape_exact_miss` (122). **Once rows page, `truncated` must
  describe the page alone**, so a walk's own bound is `walk_truncated` (124). 123 and 124 are recorded
  exclusions meeting their first field evidence (057, 066), not oversights; 125 is the most
  self-implicating — no payload named the server build, so every retro in this series had been told
  its own subject by an operator.

- **Phase 3's own cost gate ran (2026-08-23; task 121) — a split verdict, and the losing half narrows
  the phase.** Three milestones shipped while `ROADMAP.md` §5's gating question-class held **zero**
  onboarding questions; it now holds twelve, ground truth hand-read before the tools ran. Numbers:
  [`benchmarks/121_onboarding-question-class.md`](benchmarks/121_onboarding-question-class.md).
  **Won:** 12/12 correct, recall 1.0, `confidently_wrong` 0, fixture aggregate **0.29 → 0.789**. Nine
  of the twelve have no fair baseline and say so in a `ratio_note` rather than inventing one that
  would flatter the comparison. **Lost, and it is the more useful half:** where the question is a
  **reading order** the map was wrong (129, 130, 131 — all closed).
  **The narrowing, binding:** the onboarding layer is a **navigation and provenance aid, not a
  curated syllabus** — `guided_tour`'s walk still is not the hand kernel/entity order. Auto-generated
  documentation and diagrams stay behind that line; the founding-premise mistake was building on an
  unmeasured premise, and one measurement saying *"cheap and correct for lookups, wrong for
  orderings"* licenses neither.
  **What the gate cannot see, recorded rather than implied:** it scores recall and cost, never
  **precision**, and never whether a human would act on the answer — on `symfony/demo` the largest
  layer is `Uncategorised` (18 of 51 modules), a complete, correct, low-information answer that
  scores 1.0. The **mirror** shape, the anchor's most valuable one, no committed tier can measure, so
  it ships as a local-tier template in
  [`runbooks/tokens-to-answer.md`](runbooks/tokens-to-answer.md).

**Decision — how one user's evidence is weighed (2026-08-14, prompted by the round-5 interview).**
The anchor repo is the project's **first production user**: a real adopter with real work, and the
source of every field finding this project has acted on since round 1. It is **not** the roadmap. A
general MCP server is installed by repositories that share none of its shape, and a relation, field or
tool added for one adopter is paid for by all of them. So field evidence is filtered, not obeyed:

- **A finding whose subject is the *agent* generalises by default** — how an agent frames a task, when
  it is receptive to information, what it will paste into a PR, what interface shape it reaches for.
  These hold wherever an agent works, and the next round can falsify them cheaply. Tickets
  [099](tasks/099_write-time-signal-seam.md), [100](tasks/100_claim-signing-output-mode.md),
  [101](tasks/101_nav-tools-take-one-subject-at-a-time.md) are all of this kind.
- **A finding whose subject is the *repository* does not** — its migration lane, its regional split, its
  mapping file, its dispatch idiom. Such a finding is recorded and gated: it needs a **second,
  independent repository**, a stated cost to users who declare nothing, and a written rejection of the
  cheaper alternative before it may spend schema or surface. [098](tasks/098_correspondence-relation-seam.md)
  is the first ticket to carry that gate, and it is deferred under it.
- **A finding about the *language* is neither** — it belongs to the adapter and is settled by the
  language spec, never by a repo's usage (**R2**, already CI-gated).

This is R2's rule applied one level up, to evidence rather than to code: **standard over sample holds
for what we learn as well as for what we encode.** The reflex to guard against is the flattering one —
a detailed, well-argued field report from the only user we have reads like a product spec, and the
better the report, the stronger the pull.

**Decision — Founding-premise benchmark (2026-08-08). The premise is refuted; the claim that replaces it is narrower.**
Five symptom-first questions on the anchor monorepo — none naming a file, class or method — with ground
truth established by hand beforehand, one fresh headless session per (question × arm), no coaching.
Results, and every one of them cuts against the premise:

- **Native tools only: 5/5 correct**, zero confidently-wrong answers, no index, no cold start; four of
  the five answered in 46–164 s. On one question it *beat* the operator's own hand-written ground truth.
- **code-atlas: 3 correct · 1 partial · 1 wrong cause**, at **1.85×** the native arm's tokens across all
  five (0.84× excluding one outlier question — both numbers are true and neither stands alone).
- **A third arm with a resident-LSP code-intelligence MCP server available scored 4 correct · 1 partial
  while invoking that server zero times in 84 tool calls.** It measured adoption, not capability.
- Separately, broad `grep` over the same tree was timed at **0.07–8.7 s at every scope**, against a
  standing claim in that repo's own agent instructions that it "routinely times out". Not reproducible.

Consequences, all adopted:

- **Search speed is not the product.** Drop any work aimed at beating grep on per-symbol lookup or on
  counting; two of the five questions measured that race and it is neither winnable nor worth winning.
- **What survives is relationships, not locations.** The one cell code-atlas won outright: `find_callers`
  returned resolved-edge counts that the agent cross-checked against grep's raw counts and reconciled by
  tier. Text search cannot produce an independent second count at all. This is the replacement claim.
- **Fit, not accuracy, is the binding constraint.** Given the index, the agent reached for it in **22 of
  117 tool calls (19 %)**, and on two of five questions essentially not at all; the LSP arm's 0 % is the
  same finding at its limit. The whole-graph tools this argues for — `impact` (017),
  `find_orphans`/`reachable_from` (031), `explain_path` (038) — **already shipped**, and no real question
  needed one. So the gap is demand and modelling, not capability, and building more tools does not close it.
- **Redirect (see [`BACKLOG.md`](BACKLOG.md) tiers).** 059 — the unmodelled handler → template data-bag
  edge — moves to the head of tier 1: two independent field sessions produced it, it is a relation rather
  than a location, and neither grep nor a language server answers it. 061 (payload weight) is demoted.
- **§13 is unchanged and now has evidence.** code-atlas and a language server are not substitutes; the
  benchmark could not even make an agent choose between them.
- **Threats, recorded rather than hidden.** n = 1 per cell; question selection was not blind (all five
  drawn from work already done); the one accidental repeat — the mechanism question run with the server
  denied and then granted — produced **opposite verdicts**, and whether that is session variance or the
  index steering the agent off a control-flow defect is **unresolved by decision**: 074 closed
  `deferred` (2026-08-27), replication aborted at one cell on an arm with 0 index calls in 68
  (`benchmarks/074_*`). The refutation rests on the aggregate, not any single cell.

**Decision — Handler → template data-bag edge (task 059, 2026-08-08). Option 1 — producer side only.**

Do framework-shaped *view data-bag* edges belong in the graph? **Yes, on the producer side only**, as
opt-in rules data outside `adapters/` applied by `enrichment.py` (the 040 channel) — not as adapter
code (R2). Implementation is follow-up [062](tasks/062_view-databag-producer.md); this entry is the
design note.

**Occurrence count** (operator-local; shape only). Clear view-publish sites — `->render` /
`->display` / `->fetch` / `->setVar` / `$this->view->…=` with string keys, **excluding** the
ORM-contaminated `->with(` (~3k sites, dominated by eager-load, not view publish) — number
**100** sites in **35** handler files, key occurrences / distinct keys **296** / **84** — consumer side larger; detail in 059.

**Why not option 3 (permanent non-goal), and why not option 2 (both sides) yet.** Two field sessions
named this shape as why the index got zero queries on a real defect, so grep-forever leaves the gap
059 exists to close; both sides at once is a separate large cost (template reader, reversing 041's
ignores, pair linking with no path literals). Ship the producer, revisit the consumer if field retros
still fail after 062. Rationale in 059.

**What a language server does *not* solve here.** LSP go-to-def / find-refs operate on *symbols*. The
data-bag link is a **string key** — a literal in an array or setter on the handler side, a bare
variable in markup on the template side. Neither end is a symbol the PHP language server binds, so
Serena-class tools are as blind as today's graph. This is unclaimed ground, not an LSP race.

**Nav answer after 062.** `PROVIDES_VIEW_DATA` / `find_view_data` — view-scope keys; agent `Read`s
the template consumer name.

**Decision — keyed_calls may target File qnames (task 256, 2026-09-12).** 222's E2 left dispatch
routing to grep; field evidence contradicted that. **Locked:** `target_template` → indexed File qname
links as HEURISTIC CALLS (exact path). Detail: [256](tasks/256_the-dispatch-exclusion-was-decided-before-the-evidence-existed.md).

**Decision — R1.2 registry verdict: NO registry (task 156, 2026-08-27).** Adapter #2 landed (019) with
an empty core diff: adapters are selected from data — `CA_<LANG>_CMD` → `config.adapter_cmds`
(`config.py:87`), `indexer._announce` (`indexer.py:576`) loops them, and `extension_index`
(`adapter.py:289`) builds the extension→owner map from what each announces. The only per-adapter table
is test-side (`tests/contract/adapter_registry.py`, 147). Reverses only if an adapter needs core-side
per-language logic (its own ticket; see R1.2).

**Decision — populated-rebuild tax: truncate-first, defer-FTS waits (task 219, 2026-09-07).** 203
measured 2.6× populated vs fresh. **Locked: truncate-first** — `GraphStore.truncate_graph` once at
`full_build` top, so a populated rebuild matches a fresh growth curve; output byte-identical (R4.2).
**defer-FTS deferred** (its own ticket). Detail:
[219](tasks/219_a-full-rebuild-pays-the-populated-db-tax-nobody-chose.md).

**Decision — ClassConst evidence (task 234, 2026-09-08).** Spec markers (`Final`, `readonly`,
`const`, enum members) **and** PEP 8 upper-case count under R2. Python applies that at every scope
(module=`Const`, class=`ClassConst`); TS keeps `EnumMember`→`ClassConst`. No new kind / no bump.
Detail: [234](tasks/234_classconst-is-a-php-only-kind-and-the-two-signals-that-would-fill-it-elsewhere-are-discarded.md).

**Decision — annotation / decorator → REFERENCES in every adapter (task 232, 2026-09-08).** 019 put
TS decorators and declared types on `extra`; 217 chose edges for Python, so one construct answered
`find_references` three ways. **Locked: edges** — PHP and TS emit `REFERENCES` from named class types
(params/returns/properties) and from attributes/decorators; `Foo::class` stays `DYNAMIC` (094).
Withdraw-Python rejected: a TS type-site zero is a false claim. Detail:
[232](tasks/232_the-same-construct-is-a-references-edge-in-python-and-node-extra-in-php-and-ts.md).

**Decision — unmodelled `*->L` is a partition even with hits (task 238, 2026-09-10).** 221/AC5 kept
a confident hit byte-identical; that is the dangerous shape. **Locked:** the census is language-scope
— hits on an unmodelled crossing carry `authoritative: false`; `reason` stays `ok`. Detail:
[238](tasks/238_the-honest-zero-predicate-is-gated-on-the-zero.md).

**Decision — serve_behind labelled reads (257, 2026-09-12).** Opt-in: behind + unchanged subject →
`reason=index_behind` + revision on payload/rows/`claim` (never `ok`); drifted stay
repair/`index_stale`; off ⇒ byte-identical. Detail:
[257](tasks/257_the-index-goes-blind-at-the-moment-it-is-most-wanted.md).

**Decision — unresolved CALL site once (258, 2026-09-12).** The site is the fact, the candidate
set is a query: `max_results` stops governing graph content. AC1/AC5 are E1 — the anchor-scale
figures the ticket binds were not measured.
[258](tasks/258_the-graph-stores-the-cartesian-product-of-call-site-and-same-named-symbol.md).

**Reference material** (private, same folder): `understand-anything-how-it-works.md`, `code-review-graph-how-it-works.md`.

**Primary validation sample:** a large private PHP 8.5 monorepo — PSR-4 `src/` + ~18k non-namespaced legacy + a ZF1 area, ~112k files, run via Docker (PHP not on host PATH). Used for scale/coverage testing **and (from 2026-08-04) as the agent-first evaluation anchor** (task 034) — always test/metrics only; no repo-specific behavior lives in the adapter (R2, §2 "standard over sample").
