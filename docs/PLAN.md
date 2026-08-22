# Code-Atlas MCP — Build Plan

> Status: **Draft** · A local-first, multi-language code-intelligence MCP server.
> Name: **`code-atlas`** (evolved: `php-code-graph` → `code-graph` → **`code-atlas`**; it's multi-language). GitHub repo: `code-atlas`.

A local-first MCP server that indexes a codebase into SQLite and exposes **fast, resolved, token-efficient** search / read / navigation / impact tools — above all the **resolved relationships** between symbols, which text search cannot produce at any speed. (This line used to claim native tools and grep are weak at search on large repos; that premise was measured and refuted on 2026-08-08 — see §19.)

**Language-agnostic core + per-language adapters.** PHP ships first; TypeScript/JavaScript, then Python, then C#/.NET follow behind the *same* contract. On top of the graph, a later phase adds an **Understand-Anything-style onboarding** feature.

---

## 0. Priorities (driving order)
1. **Make the MCP work.** PHP end-to-end, daily-usable, before anything is generalized.
2. **Extensible to other languages** (TypeScript/JavaScript next, then Python, then C#/.NET) **without touching the core.**
3. **Onboarding feature** (Understand-Anything style) as a Phase-3 consumer of the graph.

These are in tension if mishandled — see the design principles (§2). The rule: architect for multi-language, but *implement* one language first; let language #2 harden the abstraction.

---

## 1. Goals & non-goals

### Goals
- Replace "grep + read whole file" with **symbol-level, name-resolved** queries.
- **Primary consumer is an AI coding agent in a terminal**, not a human in an IDE — so optimize for *tokens-to-correct-answer against a grep+`Read` baseline*, and for **machine-trustable responses**: calibrated confidence tiers, honest empties/truncation, enforced freshness (§19 agent-first pivot, 2026-08-04).
- **Work on ANY repo of a supported language.** Adapters implement the **language standard** (full grammar + the language's standards/PSRs), never a specific repo's conventions. Specific repos are *validation samples*, not design inputs (see §2 "Standard over sample" and §6).
- **One core, many languages**: each language uses its *best* parser (PHP→nikic, TS/JS→TypeScript Compiler API, Python→`ast`+jedi, C#→Roslyn), all speaking one JSON contract. Roll-out order: **PHP → TypeScript/JavaScript → Python → C#/.NET** (§3).
- Complement LSP-based tools, not duplicate them (§13).
- Deterministic, offline, token-efficient. LLM used only in the onboarding layer (§14), never in the core.

### Non-goals (core, v1)
- No rename/refactor/edit — **permanently ceded to the agent's native `Edit`/`Write`** (the consumer is an agent, not an IDE; §19). code-atlas returns exact symbol line ranges those edits act on; it never mutates code.
- No type inference **in the core** (adapters may supply it where free — e.g. Roslyn's semantic model, and a planned PHP local type table / opt-in PHPStan `semantic_types`; §19).
- **Framework-magic as adapter code** (hard-coded facades/DI/`__call` in adapters) stays forbidden (R2.2).
  Opt-in **indirection rules as data** (`CA_INDIRECTION_RULES`, task 040) are an in-core enrichment
  pass on the standard-language graph — off by default. ORM/`__call` heuristics remain future/out-of-band.
- No cloud LLM calls in the core.

---

## 2. Design principles (SOLID at the boundaries)

SOLID applied where a **real axis of change** exists — languages. Not speculative interfaces inside single-purpose components.

- **SRP** — one reason to change per component: *sidecar/adapter* parses only (never touches SQLite); *store* persists/queries; *enrichment* applies optional rule-file edges only (never owns SQL; may read a single already-indexed call-site line to recover string literals when `view_data` rules request it — task 062; never runs a language parser); *resolver* links edges; *tools* present. Enforced rule: parsing code and storage code never import each other.
- **OCP** — **adding a language must not modify the core.** New language = new adapter satisfying the contract (§4). The core is closed for modification, open for extension.
- **LSP (Liskov)** — every adapter is substitutable behind the contract: same node/edge vocabulary, same guarantees. **Litmus test: the core contains zero `if language == "…"`.** Any such branch = leaked abstraction → fix the contract instead.
- **ISP** — the adapter interface is tiny (≈ "given files → emit `{nodes, edges}`"). Optional power (e.g. Roslyn's semantic types) is exposed via **capability flags**, never as methods all adapters must implement.
- **DIP** — the core depends on the **contract abstraction**, not on `nikic`/`Roslyn`. The genuine inversion boundary is the **JSON contract + subprocess protocol** (a .NET adapter can't implement a Python ABC), so the contract is treated as a **versioned, validated, tested artifact**.

**Standard over sample** — an adapter implements its **language specification** (grammar + ecosystem standards: for PHP that's the full 8.5 grammar, namespaces, PSR-4/PSR-0 autoloading, `use`/aliases, traits, enums, attributes, closures/arrow-fns, first-class callables, the global namespace, `include`/`require`). It must **never** encode a particular repo's directory names, class-naming habits, or framework. Sample repos drive **test coverage and performance targets only** — never adapter semantics. If a fact about a repo would change adapter behavior, it belongs in the language spec or nowhere.

**Counter-principle (YAGNI, to keep #1 achievable):** abstract nothing that doesn't yet have two implementations. Define exactly **one** seam now — the adapter contract — and let PHP be a concrete implementation. Do **not** build a plugin registry, base classes, or a DI container for one language. **Language #2 (TypeScript/JavaScript) reveals the correct abstraction** — deliberately chosen because its model is the *most different* from PHP (no FQNs — module-scoped `import`/`export`; ESM+CommonJS; `tsconfig` path aliases; project-context resolution). It stresses the two things most likely to be PHP-shaped after building only PHP: the `qualified_name` convention and file-at-a-time resolution. Expect a **contract v2** here (see §4.4). C# and Python confirm/extend rather than reshape.

Precedent to copy: a mature multi-language LSP framework (one abstraction + N concrete language servers + a `get_ls_class()`-style factory) is OCP/DIP at scale; a `Tool`/`ToolRegistry` + marker-mixin design is ISP in practice.

---

## 3. Why this backend (decision record)

Per-language, pick the best parser; do **not** force one parser across all languages. **Roll-out order and rationale:**

| # | Language | Adapter parser | Why this parser / why this position |
|---|---|---|---|
| 1 | PHP | **nikic/php-parser** (^5) | Only reliable **PHP 8.5** parse. `NameResolver` gives FQNs for PSR-4 *and* global code. Needs only the tokenizer ext. **First = a large PHP monorepo is available as a stress-test sample.** |
| 2 | TypeScript/JavaScript | **TypeScript Compiler API** (via `ts-morph`, Node sidecar) | Official parser+**type checker**; parses JS too (`allowJs`); resolves ESM/CommonJS imports + `tsconfig` path aliases + types. **Second = most popular (BE+FE) AND the best contract-hardener** — module-scoped symbols (no FQNs) + project-context resolution stress the abstraction hardest (§2 counter-principle, §4.4). Also proves the `semantic_types` capability early. |
| 3 | Python | **`ast`** builtin + `jedi` | Zero-dependency parse; `jedi` for import/name resolution. Popular, cheap to add once the contract is hardened. |
| 4 | C#/.NET | **Roslyn** (.NET sidecar) | Full **semantic model** → precise type/call/ref edges. Last: its namespace+FQN model is close to PHP's, so it *confirms* rather than reshapes the contract. |

Rejected globally:
- **tree-sitter everywhere** — grammar lags releases (misparses PHP 8.5); forces hand-written resolution (the hard part) per language.
- **Wrapping LSPs as the core** — existing LSP-based tools already do that; an LSP indexing 100k+ files *live* is the sluggishness we're avoiding. (An adapter *may* wrap an LSP internally if that's a language's best option, but the core stays index-based.)

Engine lineage: **code-review-graph** (parse → SQLite, incremental, token-budgeted tools), generalized behind an adapter contract.

---

## 4. The contract (first-class deliverable)

The single seam between core and every language. Two parts:

### 4.1 Subprocess protocol (streaming, language-neutral)
Adapter runs as a long-lived process; core feeds newline-delimited requests, reads JSONL results. One process boot amortized across all files.
```
← {"name":"php","extensions":[".php"],"capabilities":{},"contract_version":3}   # handshake, first line
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
**Node kinds** (language-neutral superset): `File, Namespace, Class, Interface, Trait, Enum, Function, Method, Property, ClassConst, Const`.
Node fields: `kind, name, qualified_name, file_path, line_start, line_end, modifiers, params, is_test, extra(JSON)`.

**Edge kinds**: `CONTAINS, EXTENDS, IMPLEMENTS, USES_TRAIT, CALLS, NEW, IMPORTS, INCLUDES, REFERENCES, ALIASES`.
Edge fields: `kind, source_qname, target_qname?, target_raw, file_path, line, confidence_tier(RESOLVED|HEURISTIC|DYNAMIC), args?(JSON), arg_keys?(JSON)`.
`args` (contract v3, task 049) is one entry per argument at a `CALLS`/`NEW` site, in source order: `null` when the argument is any non-literal expression, otherwise its literal **category** from `contract.ARG_LITERALS` (`null, true, false, number, string, array`) — never the value. The whole field is omitted when positions cannot be trusted (a spread, a named argument) or when the adapter does not record arguments; omitted means *unknown*, never *no arguments*.
`arg_keys` (contract v5, task 063) is optional and parallel to `args`: `null` for a non-array arg; a list of top-level **string keys** from an array literal (empty list = captured, none found). Absent field = keys not captured (pre-v5 indexes). Values are never recorded.

**Qualified-name convention** (identical across languages, adapter's job to honor):
`\Ns\Class`, `\Ns\Class::method`, `\Ns\Class::$prop`, `\Ns\Class::CONST`, `\ns\func`, files as repo-relative paths. The **container** keeps its language-native separator (`\`, `.`, `/`); the **member** boundary is always `::` (`contract.MEMBER_SEPARATOR`), so C# maps to `Namespace.Type::Member` and Python to `module.Class::method`. **JS/TS has no namespaces** — symbols are module-scoped, so the qname is module-path–anchored, e.g. `src/user.ts::User::save`, `src/util.ts::default`, `src/util.ts::helper` (see §4.4 — this is the case that pressure-tests the convention).

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

The core resolves adapters by file suffix — `extension_index(adapters)` builds the map from what the adapters announced, `adapter_for(path, index)` reads it. **That's the only registry — a dict over already-constructed adapters, not a plugin system; the real one waits until the 2nd adapter exists.**

### 4.4 Project-context resolution (anticipated contract v2, forced by TS/JS)
The v1 protocol is **file-at-a-time** (`parse(path) → {nodes, edges}`), which suits PHP (NameResolver works per file). But the best parsers for **TS/JS (TypeScript Compiler API)** and **C# (Roslyn)** resolve imports/types only against a whole **program / tsconfig / project** — a single file can't see cross-file types or alias mappings. So the contract likely gains, at language #2:
- an adapter **lifecycle** that loads a project once (`open_project(root)` → hold the program in the sidecar) and answers `parse(path)` against it, so cross-file edges come back `RESOLVED` not `HEURISTIC`;
- or a **two-pass** mode: adapter emits nodes + `IMPORTS` first, the core builds the file/module map, then asks the adapter to resolve edges with that context.

This is *why* TS/JS is #2 — better to evolve the protocol here than after four languages assume file-at-a-time. PHP/Python keep working under either shape (they just don't need the program context). Bump `contract_version` when this lands.

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
```
code-atlas/
├── pyproject.toml
├── .harness.json                  # mango lifecycle config
├── .github/                       # workflows/ci.yml + pull_request_template.md
├── code_atlas/                    # THE CORE — language-agnostic, no per-language branches
│   ├── main.py                    # FastMCP server + entry point
│   ├── config.py                  # env/config (adapter cmd, paths, ignores, workers)
│   ├── contract.py                # JSON schema + validation + version
│   ├── adapter.py                 # LanguageAdapter Protocol + extension→adapter lookup
│   ├── store.py                   # SQLite schema + GraphStore
│   ├── indexer.py                 # full_build / incremental_update (drives adapters)
│   ├── resolver.py                # phase-2 edge linking (generic FQN→node)
│   ├── gitutil.py  ignore.py
│   └── tools/                     # search read outline refs impact context (+ onboarding later)
├── adapters/
│   └── php/                       # FIRST adapter
│       ├── composer.json          # nikic/php-parser ^5
│       ├── index.php              # --server (stdin loop) | --file
│       └── src/Visitor.php        # emits contract JSON
│       # then typescript/ , python/ , csharp/  — each self-contained
└── tests/
    ├── contract/                  # schema-conformance tests EVERY adapter must pass
    ├── fixtures/php/…             # namespaced, global, underscore(PSR-0), trait, enum, attributes, include
    └── test_*.py
```

Two processes: **adapter** (parse only, stateless per file) and **core** (owns SQLite, orchestration, resolver, tools).

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
- Instance `CALLS` with unknown receiver type: match by **method name** across the index → one candidate = `HEURISTIC`; many = record top-N `HEURISTIC`; dynamic (`$x->$m()`) = `DYNAMIC`, unlinked. *(Adapters with `semantic_types` capability — Roslyn — pre-resolve these to `RESOLVED`; the resolver just honors what's provided. This is how the same generic code serves both.)* PHP (task 029) emits FQN `target_raw` for lexically bound `$this` / `self` / `static` / `parent` when the enclosing class-like **declares** the method in-file (inherited / trait-mixin `$this->m` stays bare HEURISTIC so name-match still links). Tier convention: RESOLVED names the **declaration site** the file can prove (`$this`/`self`/`parent` at default tier); `static::` is late binding so it keeps the FQN but at `HEURISTIC`.
- `ALIASES` (task 030): adapter emits alias FQN → real class FQN; resolver links the real target like other FQN kinds, then remaps later CALLS/NEW whose `target_raw` is an alias onto the real class (transitively through alias chains, cycle-safe) so `find_callers` / `find_references` / impact see Alias users under Real. A stored `meta.contract_version` that lags `CONTRACT_VERSION` forces a full rebuild on incremental (never mix vocabulary eras).
- `REFERENCES` (task 094): a `Foo::class` mention (array value, argument, or assignment — the language construct, not a routing table) is a `DYNAMIC` FQN edge from the enclosing declaration to the named class. The resolver links it and **keeps** `DYNAMIC` (`_weaker_tier`). `skip_dynamic` still drops unlinkable `(dynamic)` CALLS/NEW/INCLUDES, but not `REFERENCES`. Variable-method dispatch stays unmodelled. Leftover unlinked `REFERENCES`/`IMPORTS` still feed `relationship_not_modelled` (065).
- `INCLUDES`: literal paths resolved relative to includer; variable = `DYNAMIC`.
- **top-N** is `CA_MAX_RESULTS` / `config.max_results` (default 50) — the same cap the search/nav tools use; no separate resolver knob.
- Linked tier is the **weaker** of the adapter's incoming `confidence_tier` and the lookup outcome: an FQN hit is would-be `RESOLVED` regardless of how many files declare it (task 046), while a **method-name** match is would-be `HEURISTIC` because those candidates carry genuinely different qnames. A resolved name never upgrades a guess (R5.2).
- **M4 scale:** per-edge `link_edge`/`insert_edge` commits and loading all unresolved edges into Python
  are addressed in task 015 — the resolver streams unresolved edges in batches and applies links in
  one transaction per batch. Name-match fan-out remains capped by `CA_MAX_RESULTS`.

### 8.3 Incremental (`indexer.incremental_update`)
**Shipped (task 016).** Diff = `last_commit..HEAD` **∪** working-tree changes vs `HEAD` (so
uncommitted edits are visible to `full=false`). Add single-hop **dependents** (files with edges
into changed or departing symbols — including rename sources that git only reports as the new
path); reparse `changed ∪ dependents` (hash-skip only unchanged *changed* paths — dependents are
always reparsed so adapter tiers and duplicate keys stay intact); `resolve_edges`; bump
`meta.last_commit` / `meta.last_ref`. `build_or_update_index(full=false)` runs this when `last_commit` and the diff
are usable; otherwise it falls back to a full build and reports the mode that actually ran.
Staleness stays `current | behind | unknown` (commit equality, or `behind` when the worktree is
dirty). Tests use hermetic throwaway repos so CI can keep a shallow checkout. Field retros saw
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

Default A; ship both. (C# adapter will need the .NET SDK; Python adapter runs in-process or a venv — each adapter documents its own runtime.)

---

## 10. SQLite schema
`store.py` is the only module that opens the database (§2 SRP). Connection state, set **before any
transaction** (`foreign_keys` is silently ignored inside one): `journal_mode=WAL`, `foreign_keys=ON`,
`busy_timeout=5000`.

```sql
PRAGMA journal_mode = WAL;
CREATE TABLE files (path TEXT PRIMARY KEY, hash TEXT, language TEXT, parsed_ok INT DEFAULT 1, updated_at TEXT);
CREATE TABLE nodes (
  id INTEGER PRIMARY KEY, kind TEXT, name TEXT, qualified_name TEXT,
  file_path TEXT REFERENCES files(path), line_start INT, line_end INT,
  modifiers TEXT, params TEXT, is_test INT DEFAULT 0, extra TEXT,
  UNIQUE(qualified_name, file_path));            -- NOT globally unique: see below
CREATE INDEX idx_nodes_name ON nodes(name);
CREATE INDEX idx_nodes_kind ON nodes(kind);
CREATE INDEX idx_nodes_file ON nodes(file_path);
CREATE TABLE edges (
  id INTEGER PRIMARY KEY, kind TEXT, source_qname TEXT, target_qname TEXT, target_raw TEXT,
  file_path TEXT, line INT, confidence_tier TEXT DEFAULT 'RESOLVED', args TEXT, arg_keys TEXT);
CREATE INDEX idx_edges_src ON edges(source_qname, kind);
CREATE INDEX idx_edges_tgt ON edges(target_qname, kind);
CREATE INDEX idx_edges_tier ON edges(confidence_tier);
CREATE INDEX idx_edges_raw ON edges(target_raw, kind);
CREATE VIRTUAL TABLE nodes_fts USING fts5(
  name, qualified_name, file_path, params,
  content='nodes', content_rowid='id', tokenize='trigram');
-- An external-content fts5 table indexes nothing on its own, so three triggers mirror `nodes`
-- into it. They are load-bearing, not an optimisation: without them every MATCH returns 0 rows
-- while `SELECT count(*) FROM nodes_fts` still reports the content table's size.
-- ``tokenize='trigram'`` (schema_version **2**) makes camelCase substrings match
-- (e.g. ``email`` ⊂ ``findByEmail``); unicode61 did not. Trigram cannot match terms
-- shorter than three characters — ``search_nodes`` falls back to a name/qname prefix
-- ``LIKE`` for those queries so ``DB`` / ``Us`` / ``Go`` stay findable.
CREATE TRIGGER nodes_ai AFTER INSERT ON nodes BEGIN … END;   -- insert
CREATE TRIGGER nodes_ad AFTER DELETE ON nodes BEGIN … END;   -- 'delete' with the OLD values
CREATE TRIGGER nodes_au AFTER UPDATE ON nodes BEGIN … END;   -- 'delete' then insert
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);  -- schema_version, contract_version, last_commit, last_ref, built_at
```

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

**`schema_version` is `"4"` and enforced loud.** On open, a database carrying a different value raises
— the DB is a derived cache, so there is no migration runner (this section's decision; R7.4 is about
dead abstractions and was cited here in error). Version **2** added
`tokenize='trigram'` on `nodes_fts` (camelCase substring search); version **3** adds the `edges.args`
column that carries contract v3's per-call-site argument shapes (task 049); version **4** adds
`edges.arg_keys` for array-literal string keys (contract v5, task 063).

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
Env `CA_*` → **project file `.code-atlas.toml`** (repo root, committed, stdlib `tomllib`) → defaults. The env name is derived from the file key: `workers` ⇄ `CA_WORKERS`, and `[adapter_cmd]` holds one entry per language — each a complete argv (§9), given either as a string or, preferably where quoting bites, as a list of words. A malformed value or an unknown key **fails loud** (R5.3); it never falls back.

Knobs: `CA_DB_PATH` (default `<repo>/.code-atlas/graph.db`), `CA_WORKERS` (default `max(1, min(cpu-2, 8))`), `CA_ADAPTER_TIMEOUT=30` (seconds one adapter may stay silent before the build kills it — §8.1), `CA_MAX_RESULTS=50`, `CA_IMPACT_DEPTH=2`, `CA_IMPACT_MAX_NODES=500`, `CA_ORPHANS_MAX_NODES=500` (reachability walk budget for `find_orphans` only — task 124), `CA_ENTRY_POINTS` (optional list of file/globs — reachability roots for `reachable_from` / `find_orphans`; unset ⇒ tools report no roots rather than guessing — task 031), `CA_STUB_ROOTS` (optional list of dependency roots such as `vendor` — declarations-only stub indexing; unset/blank ⇒ off — task 039), `CA_INDIRECTION_RULES` (optional list of repo-relative JSON rule files mapping framework indirections to ALIASES/CALLS; unset/blank ⇒ off — task 040), `CA_HOST_ROOT` / `CA_CONTAINER_ROOT` (optional pair — rewrite absolute host paths only; both set or both unset; unused on the relative-path build path — §9), per-adapter `CA_<LANG>_CMD` (resolved generically from the variable name — no language is named in the core), `CA_TOOLS` allow-list (unset or blank ⇒ every tool; §12).

Ignore: built-ins (`vendor/ var/ uploads/ log/ node_modules/ .git/ *.blade.*`) + `.gitignore` + optional `.codeatlasignore`, concatenated in that order with the **last matching rule winning**, so a later source can re-include. A path below an excluded **directory** stays excluded — that is what lets the walk prune a subtree. Supported gitignore subset: comments/blanks, `*` `?` `[seq]` inside a segment, `**` across segments, leading `/` anchoring, trailing `/` directory-only, `!` negation. Not supported: nested per-directory ignore files, `\` escapes. `git ls-files` already applies `.gitignore` on the primary path (§8.1), so this matcher chiefly serves the walk fallback **and** the census attribution (095): verbose `skipped.ignore_sources` names the last excluding source of each ignore-skip (`builtin` / `gitignore` / `codeatlasignore`, derived from that composition — not a hand-kept `vendor`/`config` list). On the git path most `.gitignore` hits never enter `collected`, so the counts name what **this matcher** dropped from the walked set. `*.blade.*` skips compound Blade templates on both `collect` and `collect_stubs` (task 041) — the pattern names no language. The PHP adapter handshake may announce `.phtml` (PHP template suffix) beside `.php`; shared suffixes such as `.module`/`.inc` stay out of the default announce because they are not PHP-owned and would index non-PHP bytes as junk File nodes (R2.3). Non-UTF-8 sources already fail that file softly into `parse_failures` (§4.1); task 041 pins that with an indexer-level proving test.

**Stub roots (task 039).** `CA_STUB_ROOTS` walks named dependency trees **outside** the ignore/git collect path (so `vendor/` can be indexed without weakening directory exclusion). Files under those roots are parsed with `declarations_only` (signatures + EXTENDS/IMPLEMENTS/…; no CALLS/NEW from bodies); nodes carry `extra.stub=true` and surface as `stub: true` on `search_symbol` / `read_symbol`. Off by default — enabling it costs one declarations pass over the dependency tree. Matching is **case-sensitive** (`Vendor` ≠ `vendor`); a configured root that is missing, not a directory, or overlaps git-collected source fails loud (R5.3). `BuildReport.stubs` / `get_index_status.stubs` count stub files so a zero is visible.

**Indirection rules (task 040 / 062 / 063).** `CA_INDIRECTION_RULES` names repo-relative JSON files **outside** `adapters/` (R2.2). Each file may list `aliases` (`from`/`to` FQNs → HEURISTIC `ALIASES` edges), `calls` (`source`/`target`/`line` → HEURISTIC `CALLS`), and `view_data` (`setter` + `key_arg` + optional `key_from` → HEURISTIC `PROVIDES_VIEW_DATA` with `target_raw` `viewdata:<key>`). Default `key_from` is `"string"` (062: recover the string literal at that arg from the call line). `"array_keys"` (063) reads `arg_keys` from the adapter for that array arg. Applied after parse and before `resolve_edges`. Off by default — no rules ⇒ graph unchanged. Missing/invalid rule files fail loud **before** parse (R5.3). Rule edges live on a synthetic bookmark path **without** a `files` row or File node (task 068); nav hits carry `rule: true`. `PROVIDES_VIEW_DATA` hits keep call-site `line` and resolve `file` from the subject method. **v1 limit:** `calls` entries are exact qname pairs (hand-enumerated); `view_data` setters match exact `target_raw` or `::<method>` suffix (indexed per setter via `idx_edges_raw`); one-line string-arg extraction only; array keys are top-level literal strings only — `self::K`, `"$k"`, spread, nested arrays, and decimal-integer-like string keys contribute nothing.

---

## 12. MCP tools (language-agnostic — same tools for every language)
Token-efficient: return qualified names + `file:line`, not bodies, unless a read tool is called. Every tool takes `detail_level ∈ {minimal, standard}`; `get_index_status` (task 058) and `architecture_overview` (task 086) also accept `verbose` — in both cases for a capped extra list that must not ride the cheap path. Each tool's own `DetailLevel` alias is the published enum, and the guard derives the expectation from it rather than naming the exceptions (R6.7).

| Tool | Key args | Returns |
|---|---|---|
| `get_index_status` | `detail_level?`, `offset?`, `sign?` | stats, last_commit, staleness, `next_tool_suggestions` (reactive: build when not current / no index, else empty — 061); **`index_root`** on every detail level (071 — source tree the answers describe); **`last_ref`/`head_ref`** on every detail level when known (077 — human name of the revision the index was built on and HEAD is on now; `HEAD` when detached; `null` when non-git; **omitted** when the index predates 077 so `null` is not overloaded — staleness vocabulary unchanged); `standard` also `edge_health` (`by_tier` = trust tiers; `linked`/`unlinked` = whether an edge found any target at all), `parse_failures`, and **`db_path`** (with build reports; nav/search/read omit `db_path` — 061); `verbose` adds capped `parse_failure_paths` + `parse_failures_truncated` (058 — page size `PARSE_FAILURE_PATHS_LIMIT=50`, not `CA_MAX_RESULTS`; `offset` walks further pages) and **`collection`** — the denominator to reconcile `files` against your own `git ls-files` without reading source: `{collected, skipped:{suffix, ignore, untracked}, kept, indexed_suffixes}` where `collected − skipped.suffix − skipped.ignore == kept` and `kept + stubs == files` (082 — from the single collect walk, R4; omitted for a pre-082 index). `skipped.untracked` sits **beside** that identity (092): indexable-suffix, not-ignored files git does not list. At `verbose` only, `skipped.ignore_sources` names which composed source dropped each ignore-skip (095 — keys derived from `load_ignore`: `builtin`, `gitignore`, `codeatlasignore`; last excluding rule; `ignore` stays the int so 082 still closes; omitted when empty). On the git path most `.gitignore` hits never enter `collected`, so the breakdown names what **this matcher** dropped. **Call first (~100 tok).** |
| `build_or_update_index` | `full=false`, `detail_level?` | `wrote` (BuildReport — what this run wrote) + timing; **`index_root`** on *every* outcome and detail level (079 — the build is the one write, so it names its tree like every nav payload; the process fingerprint round 4 relied on); `standard` also `graph` (`store.counts()` — 060; not on the cheap path) so scales are labelled, plus `last_commit` and **`last_ref`** (077 — the revision the index was just built on) and **`db_path`** (kept here — a write names its target; 079) and **`collection`** (the 082 census including `skipped.untracked` — 092; omitted on `minimal`). A concurrent writer returns `mode: "busy"`, `performed: false`, and the staleness of the index the loser would read — `staleness`/`last_commit`/`head_commit`/`last_ref`/`head_ref`, the `get_index_status` vocabulary (072 / 077) — so a refusal is not misread as a completed refresh; the read is read-only (053 unchanged) and lands only on the rare busy payload (061). A build with no usable adapter (unconfigured / bad handshake) returns `mode: "refused"`, `reason: "no_usable_adapter"` + `detail`, still naming `index_root`/`db_path` and writing no index — a payload, not a raise (064 / 079) |
| `search_symbol` | `query \| queries, kind?, namespace?, limit?, offset?` | ranked `{qname, kind, file:line}` (FTS + name); stub hits add `stub: true` (039); `reason` + `total_count` (033); zero-hit may miss-repair the sole dirty indexed file or emit empty `index_stale`+`try_instead` when several are dirty (073); `offset` pages in search order (057); **`queries` sweeps N subjects in one call** — `subjects` in caller order, each with its own `results`/`reason`/`total_count`, bounded by `max_subjects` with `subjects_capped_to` + `subjects_dropped` (101) |
| `file_outline` | `path, limit?, offset?` | symbols + line ranges, no body; ``total_count`` is the file's full symbol count (123); ``limit``/``offset`` page in store order (057); a truncated map adds ``result_kinds`` (kind→count over the whole file, 067/123) |
| `read_symbol` | `qname` | source of just that class/method + docblock; stub symbols add `stub: true` (039); a qname with >1 definition adds `ambiguous_definitions` (each site's `file`/`line`/`kind`, plus `stub` when set) and **refuses the body** with `reason=subject_ambiguous`, `found=false`, empty `source`, no `file`/`line_*`, and `try_instead: search_symbol` — so one region's code cannot be read while ignoring the list (070 warn; 078 refuse); an untracked indexable file matching the subject is `reason=not_indexed` with `try_instead=build_or_update_index` (092 — never `no_such_symbol`) |
| `find_callers` | `qname, depth?, include_source?, arg_position?, arg_is?, limit?, offset?, sign?` | who CALLS/NEW it + confidence; `reason` + `total_count` (033); opt-in capped call-site `source` (037); opt-in argument filter at a 1-based position — a literal category, `absent` or `dynamic` — with `total_count` counting matches and `args_unrecorded` counting the sites it could not judge (049, depth 1 only); `limit`/`offset` page results (057 — depth 1 uses store OFFSET; depth>1 pages the BFS hit stream; complete enumeration guaranteed at depth 1; at depth>1 `total_count` is a floor valid for that page only); a truncated depth-1 page whose full result spans >1 top-level path subtree adds `result_subtrees` (segment→count) so a one-page reader sees the subtrees it did not (067); a subject qname with >1 definition adds `ambiguous_definitions` (each site's `file`/`line`/`kind`) so the merged callers read as ambiguous, not authoritative (070); an untracked indexable file matching the subject is `reason=not_indexed` + `try_instead=build_or_update_index` (092) |
| `find_references` | `qname, include_source?, limit?, offset?, sign?` | all **linked** edges targeting it; `reason` + `total_count` (033); `REFERENCES` `::class` mentions are `DYNAMIC` and an all-`DYNAMIC` page sets `authoritative: false` (094 — candidate list, not a proven use); empty + unlinked `REFERENCES`/`IMPORTS` → `relationship_not_modelled` + `try_instead=search_symbol` + `try_instead_hint` naming the method-qname two-step (065; callable, progress-making route 093); opt-in capped call-site `source` (037); `offset` pages in edge order (057); a truncated page whose full result spans >1 top-level path subtree adds `result_subtrees` (segment→count) so a one-page reader sees the subtrees it did not (067); a subject qname with >1 definition adds `ambiguous_definitions` (each site's `file`/`line`/`kind`) — 070 |
| `find_implementations` | `qname, limit?, offset?` | EXTENDS/IMPLEMENTS subtypes; `reason` + `total_count` (033); `limit`/`offset` page in edge order (057) |
| `include_graph` | `path, direction` | `include`/`require` graph; `unresolved_includes` on imports/both only — omitted for `imported_by`; empty inbound with unlinked basename hits → `relationship_not_modelled` + `try_instead_hint` and deliberately **no** `try_instead` — no registered tool reads unlinked include text (065/093) |
| `impact` | `paths|qnames, depth?, sign?` | blast radius, bounded best-score; `sign` adds the claim line (100) |
| `reachable_from` | `depth?` | nodes reachable from `CA_ENTRY_POINTS` (RESOLVED IMPACT kinds, forward); `unproven` for HEURISTIC/DYNAMIC-only |
| `find_orphans` | `depth?, limit?, offset?` | complement: zero-inbound / unreachable-from-roots with `why`; never empty-success without roots; ``total_count`` is the orphan population and ``truncated`` describes the page alone, so a pager terminates (124); walk budget is ``CA_ORPHANS_MAX_NODES`` and a budget-bound walk adds ``walk_truncated`` (the population is then an over-estimate); ``minimal`` omits ``unproven`` rows, ``unproven_total`` carries the full count either way |
| `explain_path` | `from_qname, to_qname, depth?` | shortest A→B path over outgoing IMPACT kinds; `status` = `path` / `unproven` / `no_path` / `unknown` / `incomplete` |
| `architecture_overview` | `detail_level?`, `offset?` | this repo's architectural layers, ordered by net dependency direction — one row per layer with its module count, and at `standard` its degrees, a repo-level `summary` and `cross_layer_edges` (layer → layer crossings, heaviest first). **A layer is a *sub*directory of the dominant subtree, not a top-level directory**, so a monorepo yields hundreds: `results` and `cross_layer_edges` are both capped at `CA_MAX_RESULTS`, `truncated` describes `results` (the shared `nav_result` convention) and `cross_layer_edges_truncated` its own list, while `total_count` is the layer count **before** the cap and `summary.cross_layer_edges` the crossing count before its own. `verbose` adds one row per module **in layer order** (rank 0 first — an alphabetical cap hands back one directory and omits whole layers the same payload just named) with `modules_truncated` and `modules_offset`; `offset` pages further and is refused outside `verbose`, so no layer's modules are unreachable. `method` names how the grouping was derived (`dominant-subtree`, or the `dependency-direction-fallback` a flat tree falls back to) (086). **`summary.reachability` splits the zero-inbound modules into the populations they actually are** (113) — a declared or role-named web surface, vendored dependencies, tests, files with no inbound edge but outbound ones of their own, and files with no edge either way — because one number (`module entry points: 8,477` on the anchor monorepo) read to a first-day developer as "8,475 endpoints". Buckets are disjoint and sum to the raw total, which stays beside them as `summary.module_entry_points`. The only bucket worth investigating as possible dead code is the no-edge-either-way one, carried as a capped sample worded as *a list to check, not a conclusion*; the outbound-only bucket says outright that it is **not** dead code, because a dynamically included file has no static inbound edge. Membership uses only R2.2-safe signals — the operator's own `entry_points`/`stub_roots` declarations, and 110's ratified responsibility vocabulary — never a library-name list. Where no indexed path names any responsibility, those three buckets are **dropped with the reason stated** rather than rendered as a misleading zero. **`summary.business_modules` is the capability table** (114) — the bridge from *"I was told to fix the X screen, which file do I open?"* to a path, which a map of files, symbols and edges cannot answer. The container level is **derived**, never named: the directory fanning out into at least four peer subtrees of at least three files each, with its children as the modules and its own parent as their tree — so region and container names cannot become modules, they sit above the module level by construction. A container where at least half its children name a 110 responsibility is **refused with its reason** rather than reported, because a table listing `Controller`/`Entity`/`Form` as business capabilities is worse than no table. Each row carries files, classes, its trees, its directories and its busiest file; a module present under one tree and absent under a sibling is flagged `single_tree` (the divergence signal), but only where a sibling container exists to diverge from. **Coverage rides with the rows** — covered/total/percent plus the count excluded as vendored or test code — so the table cannot be mistaken for the whole repo, and a repo with no capability layout reports zero modules and says why . **`summary.mirrors` names the duplication trap** (115): sibling subtrees whose *relative path sets* largely coincide, discovered rather than configured, gated on both the shared count and the Jaccard fraction — because a pinned public repo scores a **perfect** overlap on a pair sharing one file, so the fraction alone accepts noise. Each pair carries shared / left-only / right-only, the overlap and a bounded sample, and `resolve_counterpart` answers the lookup a reader actually wants with three outcomes: the parallel path, `no_counterpart` (inside a mirror, nothing parallel — the divergence marker), or `outside_mirror` (a clean negative, never a guess). A negative drawn from a capped path index is **qualified**, because a trimmed file and a diverged file are otherwise indistinguishable. The caveat that this compares **paths, not bytes** ships inside the report, so no renderer can print the counts without it |
| `guided_tour` | `detail_level?`, `offset?` | dependency-ordered reading list of files, seeded from zero-inbound entry points, cycle-safe via SCC condensation (087). **Seeds are ranked by out-degree and capped at `CA_IMPACT_MAX_NODES // 4`** (106): a repo with more entry points than budget — 8,477 against 500 on the anchor monorepo — otherwise filled the budget with the alphabetically-first *isolated* files, so the walk traversed no edge, every stop read `entry point (zero inbound)` and every generated page had empty neighbour lists. The cap orders budget spend rather than cutting coverage: a component **no entry point reaches** (it must hold a cycle) is re-seeded from the widest-reaching unseen files rather than silently omitted, and an edgeless repo still fills the budget; earlier rounds outrank later ones under the node budget. The walk is bounded by `CA_IMPACT_MAX_NODES` (R4.3); `results` is one page of `CA_MAX_RESULTS` stops from `offset` (`results_offset` echoes it, so the tail stays reachable — 086's convention). `truncated` is true when the budget left an indexed file out of the tour or when stops remain after this page. `minimal` is files only; `standard` adds a one-line `rationale` and, for a cycle, the `scc` members. A stop only claims `entry point (zero inbound)` where the store proved zero inbound — a cycle member the budget cut off reads `reached from outside the walk`. |
| `generate_onboarding` | `detail_level?` | write committable onboarding docs from the graph (088/089): `docs/onboarding/overview.md`, `tour.md`, per-module pages, `manifest.json`, and a self-contained `index.html` **system map** (116). The HTML **embeds the 112 dataset and nothing else** (``file://`` cannot fetch a sibling JSON); no CDN, `connect-src 'none'`. 089's page embedded a rendered body per module and was a paginated dump; the map renders the dataset's spatial aggregates instead — sitemap treemap sized by symbol count and coloured by dominant layer with drill-down, layer table with its node-kind composition bar, the **full** layer x layer matrix (a "who calls whom" that omits participants is a trust bug), hubs, the 114 capability table, the 113 zero-inbound split, the 115 mirror panel, a search palette over the path index with counterpart lookup, and a provenance section naming which parts are derived. Every displayed figure is interpolated from the dataset — no literal number in the template, which is why an empty matrix cell renders blank and the sections carry no numbered badges. Rendering is a pure function of the dataset, so the same dataset yields identical bytes; measured under 1 MB with the path index and under 150 KB without it at the anchor's cardinality. The embedded JSON escapes `<`, because a repo path can itself hold `</script>` (a directory `a<` plus a file `script>x`) and would otherwise end the payload block and leave the rest as live markup — a pinned guard, not a convention. Content reaches the DOM through `textContent` only, and a `<noscript>` block points at the markdown so the page is never blank. Regenerable cache at `.code-atlas/onboarding/artifact.json` (gitignored). Deterministic given the 085 summarizer seam — no timestamps. Tour + per-module pages use the same node-budgeted subgraph as `guided_tour` (`CA_IMPACT_MAX_NODES`); overview layers come from 084/086 over the full metrics. `results` lists committed relative paths, capped at `CA_MAX_RESULTS`; `truncated` is true when the walk left an indexed file out or when paths remain after the cap. `standard` adds `cache`; `minimal` omits it. Unbuilt → `not_indexed` and writes nothing; empty index → `no_matches`. **The write owns only what it wrote:** regenerating removes exactly the module pages the previous `manifest.json` recorded (a hand-authored file in that tree survives), and a tree holding `overview.md`/`tour.md`/`index.html` *without* that manifest is refused rather than overwritten (the 050 rule — never destroy what this server did not write). `overview.md` carries `module pages`, `modules with no page (isolated, no summary)` and `truncated`, so a committed map that covers only the node budget says so **and** cannot pass a page count off as coverage (107): a module with full-graph `fan_in == fan_out == 0` and no summary gets no page — one would repeat its path and nothing else (`laravel/laravel`: 20 of 26 pages, `symfony/demo`: 7 of 51) — while a page whose neighbours the **budget** cut is kept and reads `(none admitted in this tour; N in the full graph)`, because absence inside the budget is not absence in the graph (102). Suppressed modules keep their tour stop, are named in `manifest.json` (`isolated`, and `stops[].page: null` rather than a dead link), and are counted by `isolated_modules` on `standard`. |
| `namespace_tree` | `prefix?` | namespaces + members |

**Claim signing — `sign: true` on the four attesting tools (task 100).** An attestation that never
reaches the artifact where the claim is made has, for practical purposes, not been produced: the
round-5 field session pasted nine kinds of counted evidence into its PR and **zero** code-atlas
output, while holding `seeds_dropped: 0` over the four changed paths. `impact`, `find_callers`,
`find_references` and `get_index_status` therefore take **`sign: bool = False`**, adding one payload
key — `claim` — holding a single `key=value` line: `code-atlas/1 tool= subject= question= answer=`
plus the revision the index describes (`rev`/`ref`/`index`, from `staleness.compute_staleness` —
071/077). `code_atlas/tools/claim.py` is a **pure formatter**: the tool passes it an already-computed
payload and an already-read staleness dict, so R1.4/R4.1 hold by construction and key order is fixed
for R4.2. Every caveat owns its own key — `tier` names the **weakest** tier present (R5.2),
`index=behind`, `authoritative=false`, `truncated=true`, `reason=` — so a degrading answer cannot
drop one the way a prose clause can. **Not signed:** the eleven tools whose answers are lists of rows
rather than claims; the exclusion list, with the caveat each would have lost, is in the README.
**No line is emitted** for an unbuilt index, or for an `impact` answer where no seed resolved — the
latter because a question nothing answered would be signed `answer=0` for a subject the index never
held, and a claim that cannot be re-run is decoration. (Until task **102** the stated reason was
different and weaker: `seeds_dropped` was `0` for a lost subject too, so the payload could not tell
an absent subject from a genuine zero and the guard was covering for the count. The count is honest
now — the guard is kept on its own merits.) Measured cost: **+51 tokens** on `impact`, **+46** on
`find_callers`; default payloads byte-identical (061).

**`seeds_dropped` counts every requested subject that produced no seed (task 102).** A qname that is
absent or resolves to many, a path with no indexed node, and any seed the node budget pruned all
count — the tool's lost-subject count added to the store's prune count. So `results: []` with
`seeds_dropped: 0` means a **modelled zero and nothing else**, which is the claim `impact` exists to
make and a text search cannot. When *every* named subject was lost the answer also carries `reason`
(`no_such_symbol` / `name_not_qualified` / `not_indexed`, with `candidate_count` / `try_instead`
where the classifier has them — the same `shape_exact_miss` machinery as 075/076/092). A merged
multi-subject radius states only the base class it can prove for every subject: it has no per-subject
reason channel, and inventing one is the batch shape 101 gave `search_symbol`, not this tool.

**Sweeps — one call for a list of subjects (task 101).** *"Are any of these ten names already
taken?"* was ten calls, so the round-5 field session framed it as a sweep and ran `grep -rn` over two
directories instead — one call for all ten, where the index would have searched the whole tree. The
tool was known and the cost was not the complaint: **ten calls is the wrong granularity for one
question**, and any tool answering *"is this name taken"* loses to a shell loop until it takes a
list. `search_symbol` therefore accepts **`queries`** beside `query` (never both — `ValueError`), and
answers `subjects`: one entry per subject **in the caller's order**, each carrying its own `results`,
`reason`, `total_count`, `truncated` and route. Never a merged set — that is 070's defect at batch
scale, and `impact`'s seed merge (why 102 exists) is the live counter-example. Fan-out is bounded by
**`CA_MAX_SUBJECTS` (default 25)**, disclosed as `subjects_capped_to` plus `subjects_dropped` naming
every subject refused (066 applied to subjects rather than rows) — a sweep exists to be complete, so
a silent truncation is worse than ten honest calls. The envelope (`indexed`, `index_root`,
`subject_count`) is stated once, not per subject (061). Two costs are stated rather than hidden: the
subject is no longer schema-`required` (two spellings, so neither can be — validated at runtime, as
`impact` has done since M6), and a sweep shares **one** read-through repair budget, because scaling
it per subject is the unbounded fan-out the bound exists to prevent. **Measured** (200 files / 2,000
nodes, ten names): 361 → 316 tokens (**−12.5%**) and 21.24 → 15.00 ms (**−29.4%**) — but the token
half tracks `index_root`'s length (29/32/42 tokens for roots of 2/16/53 chars), so it does not
generalise and is **not** the argument. The argument is shape. Only `search_symbol` batches; the
per-tool verdict for the other 13 is in the README (R1.2 — one batched tool first).

Every `limit`-taking tool (`search_symbol`, `find_callers`, `find_references`, `find_implementations`, `find_view_data`) adds `limit_capped_to: <cap>` when a caller's `limit` exceeded `max_results` and was reduced — present only when a clamp occurred (066, via `config.clamp_limit` + `nav_result.attach_limit_capped`); a request at or below the ceiling is byte-identical to before. `get_index_status` (`standard`/`verbose`) carries `max_results` = `{value, governs}`, stating the ceiling's double duty (returned rows **and** resolver candidate fan-out — 066).

**Ambiguous qnames — warn, never scope (task 070); refuse the body (task 078).** A qname is not unique: on the anchor index 22,261 qnames have >1 definition (`function_exists`-guarded redefinitions, per-region copies). The single-subject nav tools (`find_callers`, `find_references`, `read_symbol`) add a conditional `ambiguous_definitions` list — every definition site's `file`/`line`/`kind` (plus `stub` when set), in `_NODE_ORDER` — **only** when the subject resolves to >1 node (`nav_result.attach_ambiguous_definitions`; absent for a unique qname, so that payload is byte-identical). The list names the sites and **picks none**: which definition a call site binds to can be load-order dependent, and R4 forbids a guess dressed as a fact. **`read_symbol` additionally refuses the body** when the list is present — `reason=subject_ambiguous` (tool vocab in `NAV_REASONS`, not a `CONTRACT_VERSION` bump), `found=false`, empty `source`, omit `file`/`line_*`, `try_instead: search_symbol` — so an agent cannot silently read one declaration while ignoring the warning, and an empty answer is never badged `reason=ok` (075/076). Refusal runs **before** freshness; only a unique definition's file is ensured (same as `find_*`). Multiplicity is probed with `limit=max_results+1` so `CA_MAX_RESULTS=1` cannot hide a second site. **Scoping ("callers of the definition at `path:line`") is deliberately not offered — it cannot be answered with the current edge model.** An edge stores only its `target_qname` (`resolver.py`); when N nodes share a qname the resolver collapses them to one edge, never one per file ("an edge cannot record a file" — 046). Per-definition caller attribution would need edges to carry a resolved definition-node id, which is impossible for load-order-dependent bindings without inventing one. `impact`/`explain_path` inherit the same merge (their subject is a set/pair, so the signal is a documented follow-up, not yet emitted); `reachable_from` has no qname subject; `search_symbol` already lists definitions as separate rows.

**Descriptions are question-first (task 069).** The description a client reads is each tool's inner-fn docstring (`CONVENTION.md` §"the returned function… its docstring is the tool description"; preserved through `schema_guard.guard`'s `functools.wraps`). Field round 3 called only 5/14 tools — the misses (`find_view_data`, `explain_path`, `reachable_from`) were recognition failures, not "no such question". So every opener now leads with the caller's question and moves mechanism/edge-kinds/config-vars after it; a mechanical guard (`tests/test_tool_descriptions.py`) fails any opener that names an `EDGE_KINDS` constant, a `CA_*` var, "edge(s)", or a language. Relatedly, `find_view_data` distinguishes **inert from empty**: with no rules configured (`config.indirection_rules is None`) an indexed-but-empty subject reports `reason=capability_not_configured` (the tool cannot answer on this index) instead of `no_matches` (065-shaped; a missing subject stays `no_such_symbol`).

**Operator prompts, not agent routing (task 081).** `explore_area`, `impact_of_change`, `find_usages` — each hardcodes the efficient recipe (status → search/outline → read only what's needed) — plus `which_tool` (069), a question→tool map covering all 17 tools on today's surface. **Surface fact, from outside:** across four field rounds no prompt was ever invoked, and round 4's evaluator recorded it *could not* call `which_tool` — in its client only the tools themselves are exposed to the model (14 of them at that round; 17 today), while MCP prompts surface as human-invoked entries (round 4 §0.5/§A.5). So these four are **operator-facing recipes a human opens, labelled as such in the README and here** — never the agent's routing channel. **Design decision (081):** of three candidates — (1) descriptions carry all routing, (2) add a 15th `which_tool` *tool*, (3) keep the prompts for humans and route agents via descriptions — **(3) is chosen.** (1) is already shipped and field-verified (069's question-first descriptions — `find_view_data` was recognised by its description alone), and (3) simply stops miscounting the prompts as agent-facing. **(2) is rejected:** 069's own reasoning is that a scanned tool surface has a budget, so a 15th entry taxes every agent scan to serve routing the descriptions already carry — the cost of the 15th tool is paid on *every* call, not on demand, and it duplicates 069. Prompts load on demand, so they cost nothing on the always-paid tool list. Tool allow-list via `CA_TOOLS`. A future field round measures recognition with the blind probe in [`docs/runbooks/tool-recognition-probe.md`](runbooks/tool-recognition-probe.md), not a self-report.

**Shipped (task 010).** `main.build_server(config)` registers the allowed tools on one FastMCP app and `main()` serves it over stdio; an entry point `code-atlas` (or `python -m code_atlas.main`) is what an `.mcp.json` names. `CA_TOOLS` gates registration and an **unknown name fails loud** — `config.py` validates the list's shape, but only the server knows the tool names. `detail_level` is a `Literal`, so the protocol itself rejects anything else and publishes the choice in the input schema; `minimal` returns exactly the parts named above, `standard` adds provenance (`built_at`, `head_commit`, `contract_version`, `schema_version`, `db_path`) plus index-health (`edge_health`, `parse_failures` — task 028; counts from indexed rows only). `verbose` (task 058, this tool only) is `standard` plus a `PARSE_FAILURE_PATHS_LIMIT`-capped `parse_failure_paths` list (default 50 — **not** `CA_MAX_RESULTS`, so tuning the disk/nav knob does not shrink the diagnostic list) and `parse_failures_truncated` when more failed files remain past `offset + len(paths)`; pass `offset` to page. Failure *reasons* are not stored (`files` has no error column), so the list is paths only. Staleness is `current | behind | unknown`, and it is **`unknown` whenever either commit is unknown** — an unbuilt index and a tree git cannot name a commit for both qualify (§8.1 step 4 leaves `last_commit` unset rather than fabricating one). A dirty tree reads as `behind` **only for files the index covers** (task 047): the build stamps `indexed_suffixes` into `meta`, and the status read applies `indexer.indexable` to the dirty set, so editing a README does not ask an agent for a rebuild that would reindex nothing. `standard` reports how many indexed files are dirty as `dirty_indexed_files`; an index built before 047 has no stamp and falls back to the whole tracked tree, over-reporting rather than promising a freshness it cannot check. `next_tool_suggestions` is filtered to the tools this server actually registered, so it can never name one the client cannot call. `full=false` is accepted and echoed but **only a full build exists until §8.3 lands (task 016)** — the response reports the mode that ran, never the one requested.

**Each tool call opens its own `GraphStore`.** FastMCP runs a tool on a worker thread, and a sqlite3 connection may only be used from the thread that created it — so a store held by the server raises on first use. The per-call connection is also what keeps R4.3 true here: one writer, on the thread that owns it. A read tool opens nothing when the database file is absent; it reports `indexed: false` rather than creating an empty index as a side effect.

### Impact engine
code-review-graph's **bounded best-score relaxation in SQLite**: seed = changed qnames; per-edge-kind weight/direction policy (`CALLS/NEW`→callers, `EXTENDS/IMPLEMENTS`→subtypes, `INCLUDES` follows requires, `CONTAINS` not traversed); one best score/node, decay per hop, floor, bounded by depth & max_nodes; `DYNAMIC` edges excluded by default.

### Reachability / orphans (task 031)
Inverse of impact: `CA_ENTRY_POINTS` names file/glob roots (every indexed node on matched files is a seed). Globs use the **same segment-aware language as ignore** (`*` stays in one path segment; `**` crosses). `reachable_from` walks **outgoing** `IMPACT_KINDS` with the same RESOLVED-only frontier rule; default `depth` is **unset** (closure until frontier empties or `CA_IMPACT_MAX_NODES`); an explicit `depth` sets `depth_exhausted`/`truncated` when hops remain. A reached member keeps its container qnames alive (`split_qname`) so classes are not orphaned when only methods are called. HEURISTIC/DYNAMIC neighbors are `unproven`, not reachable. `find_orphans` returns the complement with `why` (`no_inbound` | `unreachable_from_roots`); unset roots → `no_roots_configured`. Orphan **rows** page via `limit`/`offset` (057/124); the reachability walk inside `find_orphans` is bounded by **`CA_ORPHANS_MAX_NODES`**, not `CA_IMPACT_MAX_NODES`. At `minimal`, `unproven` rows are omitted; at `standard` they are capped to the page; `unproven_total` names the full population under one name in both cases. `truncated` describes the orphan page alone — folding the walk's budget into it left every page of a large repo reporting `truncated: true` forever — and a walk that stopped on its own budget adds `walk_truncated`, the signal that unreached nodes are inflating the orphan count. Results carry `authoritative: false` and `edge_health` on `standard`.

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

Built **after** the MCP is in daily use. Not a fork of Understand-Anything — a **consumer of the graph you already have** (which is the substrate UA spends its whole pipeline building, at higher fidelity than tree-sitter). Multi-language for free: works for every language with an adapter.

> **Shipped, and not in the order this section assumed.** M10–M12 are complete (§15). The layer
> assignment turned out to be **deterministic**, not LLM-refined: 110's ratified responsibility
> vocabulary names layers, and 117 measured that 091's LLM rename seam then fires on nothing. The LLM
> ended up owning *prose only* — layer descriptions, tour-step narratives, headline wording — behind
> three opt-in seams in `onboarding_llm/`, off by default. The emitted artifact is a **navigable system
> map** (116), not the page dump this section imagined. Detail:
> [`phase3-onboarding/PHASE3_ONBOARDING.md`](phase3-onboarding/PHASE3_ONBOARDING.md).

Adds, on top of the existing graph, the two things it lacks:
1. **Semantic layer:** per-module/symbol summaries + **architectural layers**. *As built:* layers are
   deterministic (responsibility vocabulary + dependency direction) and the LLM writes prose only, opt-in.
   The per-module **summary is still empty** — the seam is fed hardcoded blank facts and the contract
   carries no docblock, so every page reads `Summary: (none)` (**118**).
2. **Presentation:** dependency-ordered **guided tour** + generated **markdown onboarding docs** (version-controllable) and/or a small viewer.

Clean split (same discipline as the reference repos): **deterministic graph (core) → LLM enrichment (onboarding) → presentation.** The LLM touches only the onboarding layer; the core stays deterministic and cheap.

New surface (separate from indexing): `generate_onboarding`, `architecture_overview`, `guided_tour` — reading the graph, writing an enriched artifact (`docs/onboarding/` committed markdown + manifest + self-contained `index.html`; regenerable cache under `.code-atlas/onboarding/`).

---

## 15. Milestones

**Phase 1 — Core + PHP (make it work):**
- **M0** Adapter spike: PHP `--file` parses a namespaced *and* a global/underscore(PSR-0) file → valid contract JSON.
- **M1** Full build: streaming adapter + N workers + SQLite; `get_index_status`. (Validate on a small PHP repo first, then a slice of the large sample.)
- **M2** Resolver + contract tests; `find_callers`/`find_references` correct on a known symbol.
- **M3** Read/search/outline + FTS. **← ship for daily use here.**
- **M4** Full-language coverage + scale: global-namespace & PSR-0 resolution, `include_graph`, run the 112k-file sample end-to-end (perf target).
- **M5** Incremental + git; staleness in status.
- **M6** Impact engine + `impact` tool + prompts.

**Phase 2 — More languages (order: TS/JS → Python → C#):**
- **M7** **TypeScript/JavaScript adapter** (TS Compiler API via `ts-morph`, Node sidecar) behind the *unchanged* core — the real test of OCP/DIP. Expect the **contract v2** here (project-context resolution, module-scoped qnames — §4.4). Proves the `semantic_types` capability flag too.
- **M8** **Python adapter** (`ast` + `jedi`) — cheap once the contract is hardened.
- **M9** **C#/.NET adapter** (Roslyn sidecar) — confirms the contract holds for a second namespaced+semantic-model language.

**Phase 3 — Onboarding** (deterministic-first; LLM opt-in and out of core + CI — breakdown in
[`phase3-onboarding/PHASE3_ONBOARDING.md`](phase3-onboarding/PHASE3_ONBOARDING.md)):
- **M10** `architecture_overview` + layers (deterministic) — 083 graph-metrics · 084 layer assignment ·
  085 summarizer seam + deterministic default · 086 `architecture_overview` tool. **M10 complete** —
  the tool ships as the 15th on the surface; 104's dominant-subtree grouping (105: elected by graph
  mass, not file count) is proven on three real pinned repos with no residual collapse (see 104/105).
- **M11** `guided_tour` + markdown docs + viewer — 087 tour (topological, carries SCC; the 16th tool) ·
  088 `generate_onboarding` (17th tool: committable markdown + manifest under `docs/onboarding/`) ·
  089 static HTML viewer (`index.html` emitted by `generate_onboarding`; offline) — **reshaped by
  116 into the navigable system map, rendered from the 112 dataset alone**.
  Reshaped by 108–117 after a human read the emitted artifact and found it unusable: 112 reduced
  the manifest to one compact versioned dataset, and **113 replaced the single zero-inbound
  headline with the five populations it actually is** (`DATASET_VERSION` 2), and **114 added the capability table that bridges a screen name to a file
  path** (`DATASET_VERSION` 3), with its own coverage stated beside it.
  **116 replaced the page dump with the map itself** (`DATASET_VERSION` 5, adding `commit`,
  each layer's node-kind composition and the prune threshold, so the page renders from the dataset
  alone and states the threshold that emptied a section). Its AC4/AC5/AC6 are proven by running the
  page headlessly under `tests/viewer_dom_stub.js`: the content is built in the browser, so a grep
  over the HTML sees zero rendered figures and would be a false green.
  **115 named the duplication trap** (`DATASET_VERSION` 4) as a lookup rather than three
  numbers, and its measured absence on three public repos is the evidence keeping 098 deferred.
  **117 closed the reshape** by routing the map's prose — layer descriptions, tour-step narratives,
  and the wording of the headline facts (`DATASET_VERSION` 6, adding `headlines`) — through one new
  seam, leaving every count, ranking and grouping derived as before.
- **M12** LLM enrichment (opt-in, deferred, out of core + CI) — 090 LLM summarizer behind the 085 seam ·
  091 LLM layer-name refinement · 117 the `ProseWriter` seam for the map's three prose slots.
  117 measured that 091's rename seam **fires on nothing** once 110 made `responsibility` the
  primary layer method: all three pinned public repos yield zero weak layers, so a description is
  wanted for *every* layer and cannot hang off a weakness-gated seam. The prose seam is therefore
  one Protocol with one method serving all three slots, which is also what gives the filler guard,
  the failure degradation and the per-run call ceiling exactly one home each (R1.2/R7.1). The
  ceiling is derived, not invented — 6 headline families + 110's 12 responsibility layers + 109's
  15-step C4 ceiling = **33 calls for a whole build**, enforced per slot so a repo falling back to
  per-directory layers cannot starve the tour: measured at 18,929 files, 1,176 layer descriptions
  were requested, the ceiling served 12 and refused 1,164.

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
| Over-abstraction before it works (fights priority #1) | One seam only (contract); PHP concrete; no registry/base-classes until adapter #2. |
| **Adapter tuned to a sample repo** (breaks "works on any repo") | "Standard over sample" (§2): adapter encodes only the language spec/PSRs; CI grep-gate bans repo/framework names in adapter source; cross-repo validation (§16). |
| Wrong abstraction guessed from one language | TS/JS (language #2) is what hardens the contract — its module-scoped, project-context model is the most PHP-unlike; expect a contract v2 at M7 (§4.4). |
| TS/JS project-context resolution doesn't fit file-at-a-time protocol | Anticipated (§4.4): adapter loads the tsconfig program once and resolves against it, or a two-pass resolve; PHP/Python unaffected. |
| PHP process startup × 112k | Long-lived streaming adapter + N workers. |
| Dynamic PHP (`$obj->$m()`, magic, variable include) | `DYNAMIC` tier, excluded from traversal; name-based `HEURISTIC` fallback. |
| No type inference for PHP instance calls | Name-match HEURISTIC; defer precise cases to an LSP. C# gets it free via Roslyn capability. |
| PHP 8.5 edge cases | nikic ^5 latest; collecting handler flags `parsed_ok=0`. |
| Host PHP absent | Docker-exec mode (§9-B) or tokenizer-only PHP CLI. |
| 100k-file DB/memory | SQLite WAL, serial writer, indexed queries, caps; traverse in SQL, never load whole graph. |
| Overlap with LSP-based tools | Clear division (§13); optionally trim the LSP tool's search tools. |

---

## 18. Open questions for review
1. **PHP runtime**: OK to install a host PHP 8.5 CLI (tokenizer only) for indexing, or Docker-only?
2. **Language order — DECIDED**: PHP → TypeScript/JavaScript → Python → C#/.NET (§3). (Was "C# second"; changed to TS/JS for reach + best contract-hardening.) **Timing revised 2026-08-04 (§19 pivot):** the *order* stands, but TS/JS (019) and Python/C# (020/021) are **deferred** until the PHP agent-loop is complete — depth before breadth.
3. **Validation repos** — **DECIDED for PHP (task 018):** public pins in
   `scripts/cross_repo_samples.json` (`laravel/laravel`, `symfony/demo`, `brick/math`) + operator-local
   large monorepo via `CODE_ATLAS_SCALE_SAMPLE`. TS/JS samples still open at M7.
4. **LSP-tool coexistence**: keep its PHP search tools on, or trim to nav/edit?
5. **Ship point**: M3 (search/read/outline) as first daily-usable release — agreed?
6. **Onboarding presentation**: markdown-in-repo (version-controlled) vs a dashboard viewer?

---

## 19. Project context & decision log
> This is the durable record — kept **in this plan**, not in any external memory store. Do not use the Claude Code Memory feature for this project; decisions live here and in the repo.

**What & why.** Build a local-first, multi-language code-intelligence MCP (`code-atlas`) ~~because native Claude Code tools and grep are weak at language-specific, name-resolved search on large repos~~. It indexes into SQLite and serves fast, token-efficient search/read/nav/impact tools.

> **The struck clause was the founding premise and it was measured false on 2026-08-08.** It is kept, struck, as the historical motivation rather than deleted, because every decision below was taken under it. What replaces it is narrower: **the index sells resolved relationships, not search speed.** See *Founding-premise benchmark* at the end of this list.

**Decisions locked so far:**
- **Architecture** — language-agnostic core + per-language adapters, each using the language's best parser, joined by one frozen/versioned JSON contract (§4). Engine lineage: code-review-graph.
- **Language order** (§3) — **PHP → TypeScript/JavaScript → Python → C#/.NET.** PHP first (large stress sample). TS/JS second: most popular (BE+FE) *and* the best contract-hardener (module-scoped, project-context, no FQNs → §4.4). Python cheap third. C# last (Roslyn semantic model; confirms the contract). **Revised 2026-08-04:** order retained, but **deferred** behind PHP agent-depth — see the pivot below.
- **SOLID at the boundaries + YAGNI** (§2) — one seam (the contract); PHP built end-to-end first; language #2 (TS/JS) hardens the abstraction. No registry/base-classes until adapter #2.
- **Standard over sample** (§2) — adapters implement the language spec/PSRs only; sample repos drive test coverage & perf targets, never adapter semantics. CI grep-gate bans repo/framework names in adapter source.
- **Priorities** (§0): make it work (PHP) → extend without touching core → onboarding feature.
- **Onboarding** (§14) is Phase 2, a graph *consumer* that adds an LLM layer; the core stays deterministic.
- **LSP-tool coexistence** (§13) — code-atlas is the indexed search/impact layer; a language server stays for LSP nav/edit.

**Decision — Agent-first PHP-depth pivot (adopted 2026-08-04; source: [`FEEDBACK.md`](FEEDBACK.md)).**
The consumer is an **AI coding agent in a terminal**, so the incumbent to beat is `grep + Read + context window`, not an IDE. This reframes goals and roadmap:
- **Metric.** Success is measured as **tokens-to-correct-answer vs a grep+`Read` baseline** on a fixed question set — not precision-vs-LSP. Build this harness before proving any accuracy change (task 034).
- **Machine-trustable responses first.** Empty ≠ unknown: `find_*`/`search` must carry reason codes and `total_count`, generalizing the `get_index_status.next_tool_suggestions` instinct (033). A subject the index has no exact node for is **classified before answering** (`nav_result.classify_missing_subject`): a leading-anchor or bare form that N indexed qnames end with returns `name_not_qualified` + `candidate_count` + `try_instead: search_symbol` (or, for a unique candidate, resolves to the stored qname — `read_symbol` is then byte-identical to the anchored form; the four `find_*` tools re-point and disclose `resolved_qname` when the typed subject differed — 122), never a confident `no_such_symbol` or `reason: ok` (075/076/122). An untracked indexable file the collect walk never saw is `reason=not_indexed` with `try_instead=build_or_update_index` — never `no_such_symbol` for a class that is on disk (092). Freshness is **enforced, not surfaced** — inline reparse on hash drift for read/nav tools with per-call cap + `index_stale` overflow (035); zero-hit queries miss-repair the sole dirty indexed file or signal `index_stale` when several are dirty (073); opt-in Claude Code `PostToolUse` Edit/Write poke via `code-atlas-poke` (`code_atlas.hooks.poke`) + `async` settings snippet (036); opt-in git `post-merge` / `post-checkout` refresh via `code-atlas-refresh` + `contrib/git/` (053, background, never auto-installed).
- **Fewer round-trips beats fewer rows.** `find_callers`/`find_references` take an opt-in
`include_source` that rides each site's own source line along with the hit — measured at **180 vs 249
tokens (−28%) end-to-end for the identical answer**, one round-trip removed (037); counting only the
relation calls and excluding the `get_index_status` preamble both paths pay, **107 vs 176 (−39%)**. A drifted site file is never
quoted (`source_stale`), since 035 refreshes only the subject file. **Consolidation was measured and
rejected — but on smallness, not on a win:** one `find_relations(qname, relation)` saves 241 schema
tokens once and costs 6.75 per call, so it is cheaper below **≈36 relation calls per session** and
dearer above, a spread of only −234…+434 tokens over 1–100 calls. No net win ⇒ the ticket's default
holds, reinforced by the unpriced cost of one muddier description (C3) and R1.2. The A/B lives in
`scripts/relation_surface_ab.py`; `find_relations` was never shipped (037).
- **Depth over breadth.** TS/JS (019) and Python/C# (020/021) are **deferred, not cancelled** — finish the PHP agent-loop first. Breadth before depth would leave us mediocre at both. **Human-ratified 2026-08-04:** PHP is the focus because a large private PHP monorepo is the anchor for **testing *and* evaluation** — the tokens-to-answer harness (034) and the accuracy work lean on it — so depth on PHP is measurable in a way breadth would not be.
- **Editing permanently ceded** to the agent's native `Edit`/`Write` (§1). code-atlas serves exact line ranges; it never mutates code.
- **Framework magic stays an enrichment layer** (§1 non-goal) — vendor stubs + indirection-as-data (039, 040), sequenced *below* the response-shape work: an agent can verify a shallow edge by reading one file, but cannot recover from an empty array it misread as proof.
- **Open risk (recorded, not resolved).** At the limit this resembles a language server, and a better PHP language-server backend might reach further. We still go depth-first — the founding complaint is that live LSP indexing of tens of thousands of files is too slow, and no backend fixes an architecture — but the objection is acknowledged, and the tokens-to-answer harness (034) is what keeps us honest about it.
- **Cheap unblocker:** resolve the license (`README.md` "TBD" → a real `LICENSE`, task 032) — an unlicensed MCP server doesn't get installed.
- **Field-report validation (2026-08-05; [`FEEDBACK.md`](FEEDBACK.md) Round 4).** A parallel `claude --bg` fan-out over worktrees of a large private PHP monorepo OOM'd because each agent inherited and re-spawned a resident-LSP code-intelligence MCP server (~5.6 GB/agent, and pointed at `main` not the worktree — wasteful *and* wrong). Repo-verified: code-atlas does **not** reproduce the *memory* half — no resident language server (query tools open/close SQLite per call, `find_callers.py:67`; adapters are transient and parse one file at a time, `adapter.py:83-88` / `indexer.py:102-104`). Concrete confirmation of the SQLite-index thesis. **It does reproduce the *routing* half, and this entry originally claimed otherwise** — see the correction below.

- **Memory & concurrency field run (2026-08-09; commit `869dcc6`, anchor monorepo, 16-core / 27.8 GB Linux).** N = 1/2/3/5 servers, 4,500 tool calls at N=5, PSS sampled per stage. **The memory thesis holds with room to spare:** the n-th agent costs **~70 MB PSS** and the 925 MB index costs **0 MB** — `graph.db` is never mmapped and no descriptor outlives a call, so it is resident once in the OS page cache (93.7 %), shared and reclaimable. Five agents = 1.3 % of RAM and **4.3×** single-agent throughput. Write contention was equally clean: 452 drift events under 3-way contention, **zero** `index_stale` soft-fails, zero `SQLITE_BUSY` reaching a caller, a 121 MB WAL that checkpointed itself away. **Correction to the 2026-08-05 entry above:** `db_path` being `cwd`-relative does **not** mean a worktree agent reads its own index. The dispatched registration bakes `cd <main repo>` into the server command, so cwd is the main checkout; a two-marker probe showed a worktree agent asking `file_outline` about **its own path** and receiving the **main checkout's** symbol, with `reason: "ok"` and — since 061 removed `db_path` from nav payloads — no field naming the tree. **Shipped (071):** every answer payload now carries `index_root` = configured source root so a mismatch is visible; isolation via `CA_DB_PATH` remains the recommended fix. Tickets [071](tasks/071_answers-do-not-name-their-tree.md) (routing — done), [072](tasks/072_busy-build-hides-staleness.md) (a `busy` build refusal that reads as success — done: the refusal now carries staleness + `performed: false`), [073](tasks/073_freshness-cannot-find-what-is-not-indexed.md) (freshness miss-repair — done). Recipe: [`runbooks/parallel-agents.md`](runbooks/parallel-agents.md).

- **Field retro round 4 — the first verification round (2026-08-10; commit `e8f56d0`, contract v5 / schema 4, anchor monorepo).** Eleven fixes from rounds 2–3 were in the binary and none had been seen by an agent doing real work. Of twelve verification items: **7 fixed and verified** (066 `limit_capped_to`, 067 `result_subtrees`, 070 `ambiguous_definitions`, 071 `index_root` on 8/8 nav payloads, 073 both halves, 062/063 view-data with 5/5 keys exact on a real array-literal setter, 051/060 build-vs-status totals), **2 improved but not fixed** (065, 069), **1 not fixed and reproduced** (054), **2 not exercisable** (068, 072). **Three caveats the round states about itself:** the protocol was violated (retro filled in after the work with the verification section read first, so its recognition test is void and every verification verdict is a post-hoc probe — evidence about payloads, not usefulness); the **server process changed mid-session** via a client reconnect, so all verdicts are from the post-reconnect build — round 2's failure mode from a direction the pre-flight does not check; and the session was review/orchestration, not a bug hunt, with **4 of 6 question shapes — every control-flow and mechanism shape — never arising in 3 hours**, which is a lead for 074 rather than a verdict on the graph. **The two findings that matter came from outside the verification section**, which is a regression harness and cannot surface anything new: [075](tasks/075_read-symbol-confident-zero-on-unnormalised-qname.md) — `read_symbol` returned `{"found": false, "reason": "ok"}` for a class the index holds under a leading backslash, while the evaluator was reviewing an agent's PR that claimed to extend it, so believing it meant a false CRITICAL on a correct PR; and [077](tasks/077_index-cannot-name-the-revision-it-describes.md) — an out-of-band branch switch left `staleness: "current"` true, correct and useless, because no payload names the revision, only SHAs (071 answers *which directory*, this is *which revision*). Tickets 075–082; order and the round's two self-corrections are in [`BACKLOG.md`](BACKLOG.md#phase-15b--large-monorepo-validation-hardening).

- **Qname-subject honesty — 075 + 076 shipped together (2026-08-11; one shared design).** The two
  round-4 findings were one defect class: a **malformed** subject (`read_symbol` for a class stored
  with a leading `\`, queried without it → `{"found": false, "reason": "ok"}`) and an **under-qualified**
  subject (`find_callers("isEnabled")` → `no_such_symbol` while the qualified form has 82) both read as
  *absence*. One language-agnostic classifier (`nav_result.classify_missing_subject`) resolves both:
  on an exact miss it counts indexed qnames ending with the subject at a component boundary — **0** →
  `no_such_symbol` (unchanged), **1** → resolve to the stored qname (`read_symbol` reads it and is
  byte-identical to the anchored form; `find_*` re-point and attach `resolved_qname` when the typed
  subject differed — 122; multi-subject `impact`/`explain_path` re-point the seed/endpoint),
  **many** → `name_not_qualified` + `candidate_count` + `try_instead: search_symbol`, across all seven
  qname tools. No `\` is hardcoded in the core (it is PHP-adapter canon, `Visitor.php:1087`); the
  classifier keys off the generic identifier class `[A-Za-z0-9_]`, not a language branch (R1.1).
  **Decision: no adapter `contract_version` bump.** The ticket asked for one, but nav `reason` codes are
  **tool-output vocabulary** (`nav_result.NAV_REASONS`, tested in `test_nav_reason_codes.py`), not the
  adapter JSONL contract (`CONTRACT_VERSION`, still 5 across the 054/065/069 reason additions). Bumping
  the adapter contract for a tool string would force every user to reindex for nothing; the new reason
  extends `NAV_REASONS` and its own conformance test instead.

- **Field retro round 5 — the first round with mechanism questions, and the first where cost changed
  what was asked (2026-08-14; commit `348a8a7`, contract v5 / schema 4, anchor monorepo at 18,926
  indexed files · 186,463 nodes · 1,788,290 edges).** Session was a legacy→unified **port**: two
  procedural pages (1,196 + 717 lines) into the unified tree, region-split, reviewed, shipped —
  ~5 h, ~95 tool calls, **16 of them code-atlas**. Run blind (R-1 clean) with two declared caveats.
  **The round is positive on truth and negative on reach.** All **8 of 8 checked claims exact, zero
  false statements**; every failure was *silence or ambiguity*, never a wrong answer, which is why
  §10's carve-outs are narrow. Verification of round 4's eight: **7 fixed** (075 met unprompted in
  real work — an unnormalised qname resolved; 077 the headline round-4 defect closed, a mid-session
  branch switch was legible at a glance from `head_ref`/`last_ref` with no SHA memorised; 076, 078,
  079, 082 fixed on probes; **080 fixed and confirmed in the field — no-op 56.1 s → 2.113 s, 26×,
  `wrote.edges: 0`, two no-ops byte-identical**), and **081 `NOT OBSERVED`** — see below.
  **Three things this round establishes that no earlier round could.** *(i)* **The graph's win is
  real and narrower than this round first claimed** — ~~a renamed-and-recased method behind an
  off-by-default feature flag, a latent fatal grep could not have caught~~ **retracted the same day by
  the round-5 interview (§6.5, entry below): PHP method names are case-insensitive, so the recasing
  could never have fataled.** What `search_symbol` actually did: the *class* had been ported under a
  different name, and grep for the legacy class name returns **0 hits** in the unified tree — one
  precise call in place of a name-similarity hunt. Real, but **no demonstrable defect prevented**.
  *(ii)* **Cost now shapes behaviour, not just the bill.** code-atlas was **well under 1 %** of
  session tokens but **181.7 s of in-work build time for 35 changed files**; the cliff is entirely
  between zero and one file (0 → 2.1 s, 2 → 59.25 s, 14 → 61.6 s). The evaluator batched: 8 calls at
  the start, 7 at the end, **1 in three hours of writing code** — including the moment it was
  hand-counting closures and got the count wrong into a committed comment. 080 removed the idle-poll
  tax and left the **edit-then-ask** tax, which is the one an agent actually pays →
  [096](tasks/096_edit-then-ask-tax-two-files-cost-a-minute.md). **Qualified the same day by the
  interview (§4):** cost shaped the *cadence*, but the two calls that mattered most needed **no
  rebuild at all** — cost is the second constraint, framing is the first.
  **Shipped (096):** the profile confirmed 080's pointer and narrowed it — `resolve` was the only
  late writer scanning the whole graph (enrichment is already O(rule matches)), and it measured
  **flat across delta size** at two scales, i.e. O(residue). `resolve_edges` now takes an optional
  delta scope keyed on **what the delta declares** (its qnames plus bare method names), not on which
  files it touched: file A can hold an unresolved edge to a class file B adds, and A is never a
  dependent because `file_paths_targeting` matches `target_qname`, still NULL. Equivalence to a full
  resolve is the gate (R4.2) and needs the alias map fixed, so it is snapshotted before the parse and
  any change falls back to a full pass. **No schema change** — the ticket assumed one was required;
  `idx_edges_raw` already indexed the lookup, and the persisted-watermark route is recorded as
  rejected. Full builds and 080's no-op guard are untouched.
  *(iii)* **Recognition ≠ recall, and the probe only measures recognition.** §0.5 scored **14/14** —
  but **7 of 14 tool descriptions were never loaded** (this harness defers MCP schemas), so 081's
  stated mechanism (routing moved *into* descriptions) was never exercised and the rate measures
  **names**. Recorded `NOT OBSERVED`, not fixed-or-broken. The failure that cost real time is one
  register down: `file_outline` — named correctly at Q4, description loaded — went uncalled on a
  1,196-line port source whose 7 functions + 2 closures it returns in ~1 KB →
  [097](tasks/097_recognition-probe-measures-names-not-recall.md).
  **Shipped (097):** the probe records resident descriptions and marks each answer name-only or
  description-backed; the 081 score is the description-backed rate (or `NOT OBSERVED` when `K = 0`).
  Q4 is occasion-worded so a bare name list can miss it. Retro §2 has a fourth bucket (*knew it, it
  fit, did not think of it* → workflow trigger, not a better description). The `file_outline`
  occasion lives in the tool description and the onboarding runbook — not in `next_tool_suggestions`
  (061 / R4). That is the bound on 081-style fixes: descriptions can name the occasion; they cannot
  make the agent notice. 074's n = 1 for legacy→unified port is unchanged.
  **The §9 primary is [092](tasks/092_untracked-files-are-invisible-and-answer-no-such-symbol.md):**
  four newly written classes were **untracked**, so `collect()`'s `git ls-files` walk never saw them;
  the build reported `wrote:{files:14}` with no skip, `dirty_indexed_files: 0` was literally true and
  actively misleading, and the lookup answered `no_such_symbol` — for a class on disk — while the
  vocabulary already owns `not_indexed`. **Shipped (092):** untracked files sit beside the 082 census (`skipped.untracked`); a miss that maps to a stored untracked indexable path returns `not_indexed` + `try_instead=build_or_update_index`. Two independent nothings (untracked invisibility, an
  unmodelled edge kind) were indistinguishable until a commit changed the reason string.
  **Shipped (093):** `try_instead` is now one register — every value it can emit is a **registered
  tool name**, and the qualifier that says how to re-ask moved to the sibling `try_instead_hint`
  (092's shape, generalised). A route must also **make progress** and **be able to answer**: the
  class-level `find_references` miss routes to `search_symbol` (it enumerates the method qnames the
  hint asks for — routing back to `find_references` would loop), and `include_graph`'s
  unlinked-inbound miss carries the **hint alone with no route**, because the evidence is include
  text in `edges.target_raw` and no registered tool reads it — `search_symbol` there answers
  `reason=ok` with the symbols declared *in* the file, omitting the includer.
  `tests/test_try_instead_is_a_callable_tool_name.py` derives the route set from `main.TOOL_NAMES`
  and the hint set from the module namespace, so the next prose value fails the gate instead of
  shipping (R1.1). No `contract_version` bump — `try_instead` is tool-output vocabulary, not the
  adapter contract (075/076 precedent). **Open, not ticketed:** nothing searches unlinked include
  text, so "who includes this file" stays unanswerable when the include path is dynamic.
  **Shipped (095):** `skipped.ignore` stays the 082 int; `get_index_status(verbose)` adds
  `skipped.ignore_sources` (keys derived from `load_ignore`'s composition; last excluding rule,
  matching the matcher). Retro's `{gitignore, config, vendor}` was a hint, not the schema — `vendor/`
  is a pattern, there is no `CA_*` ignore, and `collection_census()` int-casts so the dict lives on a
  sibling meta key. Per-pattern counts rejected (061). The anchor's 9,541 is an operator-confirmed
  follow-up, not a merge gate (080/074). Also ticketed:
  [094](tasks/094_class-constant-in-array-literal-is-not-an-edge.md) (`::class` in a routing
  array refused as `relationship_not_modelled` while a `DYNAMIC` tier holds 2,956 edges — "partly
  wrong to be silent").
  **Shipped (094):** `Foo::class` emits a `DYNAMIC` `REFERENCES` edge; the resolver links it
  without promoting the tier. `find_references` returns the mention and sets `authoritative: false`
  when every hit is `DYNAMIC`. Variable-method dispatch stays unmodelled — §10 carve-out (a)
  narrows to *"not for which action a variable-method dispatch reaches — grep the front
  controller"*. The table of named classes is now in the graph. Anchor edge-count delta is an
  operator paste (no private checkout here), not a merge gate (080/074). **Two carry-overs, not ticketed:** the session's
  highest-defect-value question was again **outside the graph's remit** (a PHP→JS asset-lineage
  breakage, found by grep + a live browser probe) — the same shape as round 4's property-write
  question on a different axis; and 067 **partially recurred** — `search_symbol` returned
  `total_count: 417`, `truncated: true`, 6 rows, with **no `result_subtrees`** to say the page was
  skewed, and the evaluator acted on page 1 without paging. **074 advances to n = 1** for session type
  *legacy→unified port*: **helped, narrowly** (see the retraction above), on one question class; mild
  harm on the routing question it cannot model (5 calls, a wrong belief about the cause). Tickets
  092–097; order in [`BACKLOG.md`](BACKLOG.md#open-work).

- **Field interview — "the questions you did not ask" (2026-08-14, same session as round 5, same
  commit `348a8a7`).** A second instrument, run on the same evaluator right after the retro: six
  questions about the moments it **did not** call the tool. **Weight it as one observer, not two** —
  the interviewee authored the retro an hour earlier and declares itself maximally contaminated; §1–§5
  survive only because they inventory *non-events*, which no retro asked about. It earns its keep
  three times over.
  **(a) It retracted the round's headline** (§6.5, applied above). The evaluator asserted a
  language-semantics claim it had never tested; PHP method names are case-insensitive, so the
  "prevented a latent flag-gated fatal" story is void. **The lesson is about the instrument, not the
  claim: a retro cannot audit itself, and a same-session interview is the cheapest thing that can.**
  **(b) Adoption is a *position* problem, not a speed problem** — the single most important finding
  here. All **three** decisions the evaluator made without the graph wanted the same thing: **one line
  inside a `Read` it was already performing**, and **none wanted a tool call**. Reinforced by §4: the
  two highest-value uncalled queries (`file_outline` on a months-old legacy file, `search_symbol
  kind:"Function"` for a name-collision sweep) needed **no rebuild** and would have cost ~1 s at any
  point — and were still not made. Framing, not latency → [099](tasks/099_write-time-signal-seam.md).
  **Shipped (099) — the verdict, which is a position statement as much as a feature:** the signal
  lives in the **host's hook surface**, not on a payload rider. `next_tool_suggestions` reaches the
  agent *after it asks*, and the core cannot observe a `Read` — so that channel is **structurally**
  incapable of carrying this, not merely too expensive (061). `code-atlas-signal` ships as the third
  hook of 036/053's kind: two lines only (the outline at `Read`, the untracked warning at a creating
  `Write`), a ~150-token hard cap, no build and no write lock, and a **structural** silence rule —
  any other tool, an existing path, a file below the symbol floor, or no index, all silent with no
  session state. **code-atlas offers the command and wires nothing.** The bound this records is the
  ceiling on 069/081-style routing work: *no description reaches an agent that never opens the tool
  list* — which is why 097 (recognition) and 099 (position) are one finding from two sides. The
  falsifier is in retro §0.6: a next round that reports the signal *tuned out* at the shipped cap
  makes this session-specific.
  **(c) The evidence-layer thesis now has behavioural proof, against the evaluator's own interest**
  (§2): the PR body pastes **nine** kinds of counted evidence — HTTP status, byte counts, row counts,
  two verbatim `alert()` strings, test and assertion counts — and **zero** graph payloads, although
  `impact` had already returned `seeds_dropped: 0, frontier_skipped_non_resolved: 0`. The evaluator's
  own reading: *"my behaviour treated the browser as an evidence source and code-atlas as a search
  layer."* → [100](tasks/100_claim-signing-output-mode.md).
  **Also new:** a **call-shape** miss no cost metric can see — the collision sweep had **10 subjects at
  once**, the graph takes one per call, a shell loop takes all ten (§7.3) →
  [101](tasks/101_nav-tools-take-one-subject-at-a-time.md); and an evidence-backed hazard in
  `find_orphans` — **the evaluator's own two new controllers are orphans by the graph's accounting**,
  being live entry points reached by dynamic dispatch (recorded in [031](tasks/031_reachability-orphans.md)).
  **The strategic ask, and the one judgement the interview cannot make for us** (§8, explicitly opinion
  and explicitly design, which the instrument otherwise forbids): the anchor repo's dominant chore is
  *port a legacy file into the unified tree without breaking the other region*, and the graph holds
  **neither** relation that chore is made of — legacy↔unified, and region-A↔region-B. Its proposal is
  to seed the first from a ~4,300-entry mapping the repo already maintains. **Adopted in principle,
  rejected as proposed:** ingesting a repo's own mapping file is sample-over-standard (R2). What the
  core may learn is one **generic correspondence relation**, config-fed, adapter-blind — under which
  legacy↔unified and region-A↔region-B are the *same* primitive, and "has this mapping rotted?" becomes
  checkable → [098](tasks/098_correspondence-relation-seam.md). Its third ask (cross-language asset
  lineage) is **not** a language problem as it assumed: *N files share a basename across different
  roots* is a file-level relation over rows the core already holds, needing no JS adapter — folded into
  098's design as the second correspondence source to weigh — **and 098 is `deferred` behind a written
  evidence gate, not scheduled** (see the decision below). Full instrument and answers live with the
  retros, outside this repo (R-8/I-8: the anchor repo is not named here).

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
  drawn from work already done); the one accidental repeat — the mechanism question, run twice under the
  indexed arm's configuration with the server denied and then granted — produced **opposite verdicts**,
  and whether that is session variance or the index steering the agent away from a control-flow defect is
  unresolved. The refutation rests on the aggregate, not on any single cell. Details in the private
  benchmark notes; nothing repo-identifying is reproduced here.

**Decision — Handler → template data-bag edge (task 059, 2026-08-08). Option 1 — producer side only.**

Do framework-shaped *view data-bag* edges belong in the graph? **Yes, on the producer side only**, as
opt-in rules data outside `adapters/` applied by `enrichment.py` (the 040 channel) — not as adapter
code (R2). Implementation is follow-up [062](tasks/062_view-databag-producer.md); this entry is the
design note.

**Occurrence count** (operator-local §19 anchor; shape only — no private paths or identifiers).
Raw `->with(` is ~3k sites on the anchor but is dominated by ORM eager-load, not view publish — the
clean producer tally below **excludes** it; including it would inflate the case for a contract bump
with the wrong evidence.

| Signal | Count |
|--------|------:|
| Clear view-publish sites (`->render` / `->display` / `->fetch` / `->setVar` / `$this->view->…=`, string keys; **excluding** ORM-contaminated `->with(`) | **100** sites in **35** handler files |
| Key occurrences / distinct keys in those sites | **296** / **84** |
| PHP files under view/views/template dirs that read `$this->…` / `<?= $…` | **2159** of **3094** (~33k occurrences, **1364** distinct) |
| Twig files with `{{ rootVar` roots | **180** of **202** (**1245** / **155** distinct) |
| Producer files also containing a literal template-path string (pair proxy) | **6** |
| Field-session qualitative | Round 1: **5** mismatched controller/template pairs; Round 2: request-/branch-key mirror |

**Why not option 3 (permanent non-goal).** The shape is common enough to justify a contract bump later
(100 clean producer sites, 84 keys, thousands of consumer reads) and two independent field sessions
named it as the reason the index got zero queries on a real defect. Declaring “grep’s job forever”
would leave the exact gap the founding-premise redirect promoted 059 to close.

**Why not option 2 (both sides) now.** A template reader for mixed markup (Twig / Blade / PHP views),
reversing 041’s ignore reasons, and true pair linking (framework-implicit — only 6 path-literal pairs)
is a separate large cost. YAGNI: ship producer first; revisit consumer if field retros still fail after
062.

**What a language server does *not* solve here.** LSP go-to-def / find-refs operate on *symbols*. The
data-bag link is a **string key** — a literal in an array (or setter) on the handler side, a bare
variable in markup on the template side. Neither end is a symbol the PHP language server binds, so
Serena-class tools are as blind as today’s graph. This is unclaimed ground, not an LSP race.

**Nav answer after 062.** Given a handler method, list the view-scope keys it publishes (and at which
lines). The agent still `Read`s the template to confirm the consumer name — half of round 1’s question,
the half no current tool answers. **Implemented in [062](tasks/062_view-databag-producer.md):** edge
kind `PROVIDES_VIEW_DATA`, `viewdata:<key>` targets, `CA_INDIRECTION_RULES` `view_data` setters, tool
`find_view_data`.

**Reference material** (private, same folder): `understand-anything-how-it-works.md`, `code-review-graph-how-it-works.md`.

**Primary validation sample:** a large private PHP 8.5 monorepo — PSR-4 `src/` + ~18k non-namespaced legacy + a ZF1 area, ~112k files, run via Docker (PHP not on host PATH). Used for scale/coverage testing **and (from 2026-08-04) as the agent-first evaluation anchor** (task 034) — always test/metrics only; no repo-specific behavior lives in the adapter (R2, §2 "standard over sample").
