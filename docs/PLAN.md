# Code-Atlas MCP — Build Plan

> Status: **Draft** · A local-first, multi-language code-intelligence MCP server.
> Name: **`code-atlas`** (evolved: `php-code-graph` → `code-graph` → **`code-atlas`**; it's multi-language). GitHub repo: `code-atlas`.

A local-first MCP server that indexes a codebase into SQLite and exposes **fast, resolved, token-efficient** search / read / navigation / impact tools — above all the **resolved relationships** between symbols, which text search cannot produce at any speed. (This line used to claim native tools and grep are weak at search on large repos; that premise was measured and refuted on 2026-08-08 — see §19.)

**Language-agnostic core + per-language adapters.** PHP ships first; TypeScript/JavaScript, then Python, then C#/.NET follow behind the *same* contract. On top of the graph, a later phase adds an **Understand-Anything-style onboarding** feature.

---

## 0. Priorities (driving order)
1. **Make the MCP work.** PHP end-to-end, daily-usable, before anything is generalized.
2. **Extensible to other languages** (TypeScript/JavaScript next, then Python, then C#/.NET) **without touching the core.**
3. **Onboarding feature** (Understand-Anything style) as a Phase-2 consumer of the graph.

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

- **SRP** — one reason to change per component: *sidecar/adapter* parses only (never touches SQLite); *store* persists/queries; *enrichment* applies optional rule-file edges only (never parses source; never owns SQL); *resolver* links edges; *tools* present. Enforced rule: parsing code and storage code never import each other.
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
Edge fields: `kind, source_qname, target_qname?, target_raw, file_path, line, confidence_tier(RESOLVED|HEURISTIC|DYNAMIC), args?(JSON)`.
`args` (contract v3, task 049) is one entry per argument at a `CALLS`/`NEW` site, in source order: `null` when the argument is any non-literal expression, otherwise its literal **category** from `contract.ARG_LITERALS` (`null, true, false, number, string, array`) — never the value. The whole field is omitted when positions cannot be trusted (a spread, a named argument) or when the adapter does not record arguments; omitted means *unknown*, never *no arguments*.

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
4. Store `meta.last_commit`, `contract_version`, `built_at`. `last_commit` is left **unset** when git cannot name one (no repo, no commit yet) rather than fabricated.
5. Run **resolver** (§8.2), then report. **`BuildReport` counts what the run *wrote*, not what the graph holds** (task 051). Steps 3–4 tally adapter output, but enrichment (§13) and the resolver both insert rows afterwards — synthetic ALIASES/CALLS, and one sibling per extra candidate at a multi-match call site — so a report taken from the parse tally alone understates the graph it just built: 949,808 against 1,775,812 stored on the anchor repo, and 3,481 against 4,373 on a public PSR-4 library. Both writers now return what they wrote and the report folds it in, so a full build agrees with `store.counts()` (what `get_index_status` reports) while an incremental run still reports its own delta. The MCP tool nests those under `wrote` so a delta cannot be mistaken for a repo size; `standard` also carries `store.counts()` as `graph` (task 060 — not on `minimal`, which stays cheap). The one remaining difference is the synthetic rules path, which `files`/`parsed` do not count and the `files` table does.
6. `nodes_fts` needs **no rebuild**: §10's triggers keep it current through every per-file replace, so a rebuild per build would cost a full re-index and change nothing. `GraphStore.rebuild_search_index` stays as the repair tool for a stale index.

### 8.2 Resolver (phase 2, generic — no language branches)
Runs after all nodes exist:
- `EXTENDS/IMPLEMENTS/USES_TRAIT/NEW/FuncCall`: `target_raw` is an FQN from the adapter → look up `nodes.qualified_name`, set `target_qname`, tier `RESOLVED`; leave NULL if external/vendor. A qname that appears in multiple files (§10) is linked **once**, still `RESOLVED` — the lookup is keyed by qname, so a hit means the name resolved, and an edge records a `target_qname`, never a node id, so "which declaring file" is not representable. **Revised by task 046:** this previously emitted one top-N `HEURISTIC` edge per declaring node, which produced rows identical in every column but `id` (38.8% of the graph on a monorepo carrying two regional copies of one tree) and downgraded 1.66M edges for a multiplicity that was never ambiguity. Every declaration remains a `nodes` row, so nothing is lost.
- Instance `CALLS` with unknown receiver type: match by **method name** across the index → one candidate = `HEURISTIC`; many = record top-N `HEURISTIC`; dynamic (`$x->$m()`) = `DYNAMIC`, unlinked. *(Adapters with `semantic_types` capability — Roslyn — pre-resolve these to `RESOLVED`; the resolver just honors what's provided. This is how the same generic code serves both.)* PHP (task 029) emits FQN `target_raw` for lexically bound `$this` / `self` / `static` / `parent` when the enclosing class-like **declares** the method in-file (inherited / trait-mixin `$this->m` stays bare HEURISTIC so name-match still links). Tier convention: RESOLVED names the **declaration site** the file can prove (`$this`/`self`/`parent` at default tier); `static::` is late binding so it keeps the FQN but at `HEURISTIC`.
- `ALIASES` (task 030): adapter emits alias FQN → real class FQN; resolver links the real target like other FQN kinds, then remaps later CALLS/NEW whose `target_raw` is an alias onto the real class (transitively through alias chains, cycle-safe) so `find_callers` / `find_references` / impact see Alias users under Real. A stored `meta.contract_version` that lags `CONTRACT_VERSION` forces a full rebuild on incremental (never mix vocabulary eras).
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
`meta.last_commit`. `build_or_update_index(full=false)` runs this when `last_commit` and the diff
are usable; otherwise it falls back to a full build and reports the mode that actually ran.
Staleness stays `current | behind | unknown` (commit equality, or `behind` when the worktree is
dirty). Tests use hermetic throwaway repos so CI can keep a shallow checkout. Field retros saw
~62 s flat fee for no-op and small incrementals on a large index (task 052) — profile phases with
`scripts/profile_incremental.py --root …` (optional `phase_times` on `incremental_update`; not on
the MCP payload) before deciding whether unscoped `resolve_edges` is a defect or the honest price.

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
  file_path TEXT, line INT, confidence_tier TEXT DEFAULT 'RESOLVED', args TEXT);
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
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);  -- schema_version, contract_version, last_commit, built_at
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

**`schema_version` is `"3"` and enforced loud.** On open, a database carrying a different value raises
— the DB is a derived cache, so there is no migration runner (this section's decision; R7.4 is about
dead abstractions and was cited here in error). Version **2** added
`tokenize='trigram'` on `nodes_fts` (camelCase substring search); version **3** adds the `edges.args`
column that carries contract v3's per-call-site argument shapes (task 049).

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

Knobs: `CA_DB_PATH` (default `<repo>/.code-atlas/graph.db`), `CA_WORKERS` (default `max(1, min(cpu-2, 8))`), `CA_ADAPTER_TIMEOUT=30` (seconds one adapter may stay silent before the build kills it — §8.1), `CA_MAX_RESULTS=50`, `CA_IMPACT_DEPTH=2`, `CA_IMPACT_MAX_NODES=500`, `CA_ENTRY_POINTS` (optional list of file/globs — reachability roots for `reachable_from` / `find_orphans`; unset ⇒ tools report no roots rather than guessing — task 031), `CA_STUB_ROOTS` (optional list of dependency roots such as `vendor` — declarations-only stub indexing; unset/blank ⇒ off — task 039), `CA_INDIRECTION_RULES` (optional list of repo-relative JSON rule files mapping framework indirections to ALIASES/CALLS; unset/blank ⇒ off — task 040), `CA_HOST_ROOT` / `CA_CONTAINER_ROOT` (optional pair — rewrite absolute host paths only; both set or both unset; unused on the relative-path build path — §9), per-adapter `CA_<LANG>_CMD` (resolved generically from the variable name — no language is named in the core), `CA_TOOLS` allow-list (unset or blank ⇒ every tool; §12).

Ignore: built-ins (`vendor/ var/ uploads/ log/ node_modules/ .git/ *.blade.*`) + `.gitignore` + optional `.codeatlasignore`, concatenated in that order with the **last matching rule winning**, so a later source can re-include. A path below an excluded **directory** stays excluded — that is what lets the walk prune a subtree. Supported gitignore subset: comments/blanks, `*` `?` `[seq]` inside a segment, `**` across segments, leading `/` anchoring, trailing `/` directory-only, `!` negation. Not supported: nested per-directory ignore files, `\` escapes. `git ls-files` already applies `.gitignore` on the primary path (§8.1), so this matcher chiefly serves the walk fallback. `*.blade.*` skips compound Blade templates on both `collect` and `collect_stubs` (task 041) — the pattern names no language. The PHP adapter handshake may announce `.phtml` (PHP template suffix) beside `.php`; shared suffixes such as `.module`/`.inc` stay out of the default announce because they are not PHP-owned and would index non-PHP bytes as junk File nodes (R2.3). Non-UTF-8 sources already fail that file softly into `parse_failures` (§4.1); task 041 pins that with an indexer-level proving test.

**Stub roots (task 039).** `CA_STUB_ROOTS` walks named dependency trees **outside** the ignore/git collect path (so `vendor/` can be indexed without weakening directory exclusion). Files under those roots are parsed with `declarations_only` (signatures + EXTENDS/IMPLEMENTS/…; no CALLS/NEW from bodies); nodes carry `extra.stub=true` and surface as `stub: true` on `search_symbol` / `read_symbol`. Off by default — enabling it costs one declarations pass over the dependency tree. Matching is **case-sensitive** (`Vendor` ≠ `vendor`); a configured root that is missing, not a directory, or overlaps git-collected source fails loud (R5.3). `BuildReport.stubs` / `get_index_status.stubs` count stub files so a zero is visible.

**Indirection rules (task 040).** `CA_INDIRECTION_RULES` names repo-relative JSON files **outside** `adapters/` (R2.2). Each file may list `aliases` (`from`/`to` FQNs → HEURISTIC `ALIASES` edges) and `calls` (`source`/`target`/`line` → HEURISTIC `CALLS`). Applied after parse and before `resolve_edges`, so facade aliases reuse task 030’s remap. Off by default — no rules ⇒ graph unchanged. Missing/invalid rule files fail loud **before** parse (R5.3). Rule edges live on a synthetic bookmark path (not on disk); nav hits carry `rule: true` and omit `file`/`line` so they never read as `source_stale`. **v1 limit:** `calls` entries are exact qname pairs (hand-enumerated) — no pattern/glob; aliases scale because the resolver remaps every call through the facade. Pattern-shaped rules are a follow-up.

---

## 12. MCP tools (language-agnostic — same tools for every language)
Token-efficient: return qualified names + `file:line`, not bodies, unless a read tool is called. Every tool takes `detail_level ∈ {minimal, standard}`; `get_index_status` also accepts `verbose` (task 058).

| Tool | Key args | Returns |
|---|---|---|
| `get_index_status` | `detail_level?`, `offset?` | stats, last_commit, staleness, `next_tool_suggestions`; `standard` also `edge_health` (`by_tier` = trust tiers; `linked`/`unlinked` = whether an edge found any target at all) and `parse_failures`; `verbose` adds capped `parse_failure_paths` + `parse_failures_truncated` (058 — page size `PARSE_FAILURE_PATHS_LIMIT=50`, not `CA_MAX_RESULTS`; `offset` walks further pages). **Call first (~100 tok).** |
| `build_or_update_index` | `full=false`, `detail_level?` | `wrote` (BuildReport — what this run wrote) + timing; `standard` also `graph` (`store.counts()` — 060; not on the cheap path) so scales are labelled |
| `search_symbol` | `query, kind?, namespace?, limit?, offset?` | ranked `{qname, kind, file:line}` (FTS + name); stub hits add `stub: true` (039); `reason` + `total_count` (033); `offset` pages in search order (057) |
| `file_outline` | `path` | symbols + line ranges, no body |
| `read_symbol` | `qname` | source of just that class/method + docblock; stub symbols add `stub: true` (039) |
| `find_callers` | `qname, depth?, include_source?, arg_position?, arg_is?, limit?, offset?` | who CALLS/NEW it + confidence; `reason` + `total_count` (033); opt-in capped call-site `source` (037); opt-in argument filter at a 1-based position — a literal category, `absent` or `dynamic` — with `total_count` counting matches and `args_unrecorded` counting the sites it could not judge (049, depth 1 only); `limit`/`offset` page results (057 — depth 1 uses store OFFSET; depth>1 pages the BFS hit stream; complete enumeration guaranteed at depth 1; at depth>1 `total_count` is a floor valid for that page only) |
| `find_references` | `qname, include_source?, limit?, offset?` | all edges targeting it; `reason` + `total_count` (033); opt-in capped call-site `source` (037); `offset` pages in edge order (057) |
| `find_implementations` | `qname, limit?, offset?` | EXTENDS/IMPLEMENTS subtypes; `reason` + `total_count` (033); `limit`/`offset` page in edge order (057) |
| `include_graph` | `path, direction` | `include`/`require` graph (any include-based code) |
| `impact` | `paths|qnames, depth?` | blast radius, bounded best-score |
| `reachable_from` | `depth?` | nodes reachable from `CA_ENTRY_POINTS` (RESOLVED IMPACT kinds, forward); `unproven` for HEURISTIC/DYNAMIC-only |
| `find_orphans` | `depth?` | complement: zero-inbound / unreachable-from-roots with `why`; never empty-success without roots |
| `explain_path` | `from_qname, to_qname, depth?` | shortest A→B path over outgoing IMPACT kinds; `status` = `path` / `unproven` / `no_path` / `unknown` / `incomplete` |
| `namespace_tree` | `prefix?` | namespaces + members |

Prompts: `explore_area`, `impact_of_change`, `find_usages` — each hardcodes the efficient recipe (status → search/outline → read only what's needed). Tool allow-list via `CA_TOOLS`.

**Shipped (task 010).** `main.build_server(config)` registers the allowed tools on one FastMCP app and `main()` serves it over stdio; an entry point `code-atlas` (or `python -m code_atlas.main`) is what an `.mcp.json` names. `CA_TOOLS` gates registration and an **unknown name fails loud** — `config.py` validates the list's shape, but only the server knows the tool names. `detail_level` is a `Literal`, so the protocol itself rejects anything else and publishes the choice in the input schema; `minimal` returns exactly the parts named above, `standard` adds provenance (`built_at`, `head_commit`, `contract_version`, `schema_version`, `db_path`) plus index-health (`edge_health`, `parse_failures` — task 028; counts from indexed rows only). `verbose` (task 058, this tool only) is `standard` plus a `PARSE_FAILURE_PATHS_LIMIT`-capped `parse_failure_paths` list (default 50 — **not** `CA_MAX_RESULTS`, so tuning the disk/nav knob does not shrink the diagnostic list) and `parse_failures_truncated` when more failed files remain past `offset + len(paths)`; pass `offset` to page. Failure *reasons* are not stored (`files` has no error column), so the list is paths only. Staleness is `current | behind | unknown`, and it is **`unknown` whenever either commit is unknown** — an unbuilt index and a tree git cannot name a commit for both qualify (§8.1 step 4 leaves `last_commit` unset rather than fabricating one). A dirty tree reads as `behind` **only for files the index covers** (task 047): the build stamps `indexed_suffixes` into `meta`, and the status read applies `indexer.indexable` to the dirty set, so editing a README does not ask an agent for a rebuild that would reindex nothing. `standard` reports how many indexed files are dirty as `dirty_indexed_files`; an index built before 047 has no stamp and falls back to the whole tracked tree, over-reporting rather than promising a freshness it cannot check. `next_tool_suggestions` is filtered to the tools this server actually registered, so it can never name one the client cannot call. `full=false` is accepted and echoed but **only a full build exists until §8.3 lands (task 016)** — the response reports the mode that ran, never the one requested.

**Each tool call opens its own `GraphStore`.** FastMCP runs a tool on a worker thread, and a sqlite3 connection may only be used from the thread that created it — so a store held by the server raises on first use. The per-call connection is also what keeps R4.3 true here: one writer, on the thread that owns it. A read tool opens nothing when the database file is absent; it reports `indexed: false` rather than creating an empty index as a side effect.

### Impact engine
code-review-graph's **bounded best-score relaxation in SQLite**: seed = changed qnames; per-edge-kind weight/direction policy (`CALLS/NEW`→callers, `EXTENDS/IMPLEMENTS`→subtypes, `INCLUDES` follows requires, `CONTAINS` not traversed); one best score/node, decay per hop, floor, bounded by depth & max_nodes; `DYNAMIC` edges excluded by default.

### Reachability / orphans (task 031)
Inverse of impact: `CA_ENTRY_POINTS` names file/glob roots (every indexed node on matched files is a seed). Globs use the **same segment-aware language as ignore** (`*` stays in one path segment; `**` crosses). `reachable_from` walks **outgoing** `IMPACT_KINDS` with the same RESOLVED-only frontier rule; default `depth` is **unset** (closure until frontier empties or `CA_IMPACT_MAX_NODES`); an explicit `depth` sets `depth_exhausted`/`truncated` when hops remain. A reached member keeps its container qnames alive (`split_qname`) so classes are not orphaned when only methods are called. HEURISTIC/DYNAMIC neighbors are `unproven`, not reachable. `find_orphans` returns the complement with `why` (`no_inbound` | `unreachable_from_roots`); unset roots → `no_roots_configured`. Caps reuse `CA_IMPACT_MAX_NODES` (not `CA_IMPACT_DEPTH`). Results carry `authoritative: false` and `edge_health` on `standard`.

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

## 14. Phase 2 — Onboarding feature (Understand-Anything style)

Built **after** the MCP is in daily use. Not a fork of Understand-Anything — a **consumer of the graph you already have** (which is the substrate UA spends its whole pipeline building, at higher fidelity than tree-sitter). Multi-language for free: works for every language with an adapter.

Adds, on top of the existing graph, the two things it lacks:
1. **Semantic layer (LLM):** per-module/symbol plain-English summaries + tags; **architectural layers** (start heuristic by namespace/directory, refine with LLM).
2. **Presentation:** dependency-ordered **guided tour** + generated **markdown onboarding docs** (version-controllable) and/or a small viewer.

Clean split (same discipline as the reference repos): **deterministic graph (core) → LLM enrichment (onboarding) → presentation.** The LLM touches only the onboarding layer; the core stays deterministic and cheap.

New surface (separate from indexing): `generate_onboarding`, `architecture_overview`, `guided_tour` — reading the graph, writing an enriched artifact (e.g. `.code-atlas/onboarding/`).

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

**Phase 3 — Onboarding:**
- **M10** `architecture_overview` + layers (heuristic → LLM).
- **M11** `guided_tour` + markdown onboarding docs.

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
- **Machine-trustable responses first.** Empty ≠ unknown: `find_*`/`search` must carry reason codes and `total_count`, generalizing the `get_index_status.next_tool_suggestions` instinct (033). Freshness is **enforced, not surfaced** — inline reparse on hash drift for read/nav tools with per-call cap + `index_stale` overflow (035); opt-in Claude Code `PostToolUse` Edit/Write poke via `code-atlas-poke` (`code_atlas.hooks.poke`) + `async` settings snippet (036).
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
- **Field-report validation (2026-08-05; [`FEEDBACK.md`](FEEDBACK.md) Round 4).** A parallel `claude --bg` fan-out over worktrees of a large private PHP monorepo OOM'd because each agent inherited and re-spawned a resident-LSP code-intelligence MCP server (~5.6 GB/agent, and pointed at `main` not the worktree — wasteful *and* wrong). Repo-verified: code-atlas does **not** reproduce this — no resident language server (query tools open/close SQLite per call, `find_callers.py:67`; adapters are transient and parse one file at a time, `adapter.py:83-88` / `indexer.py:102-104`), and `db_path` is `cwd`-relative so a worktree agent reads its own index, not `main` (`config.py:117`). Concrete confirmation of the SQLite-index thesis. Residual caveat is a transient build-time process burst under many concurrent builds — see [`runbooks/parallel-agents.md`](runbooks/parallel-agents.md).

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
the half no current tool answers.

**Reference material** (private, same folder): `understand-anything-how-it-works.md`, `code-review-graph-how-it-works.md`.

**Primary validation sample:** a large private PHP 8.5 monorepo — PSR-4 `src/` + ~18k non-namespaced legacy + a ZF1 area, ~112k files, run via Docker (PHP not on host PATH). Used for scale/coverage testing **and (from 2026-08-04) as the agent-first evaluation anchor** (task 034) — always test/metrics only; no repo-specific behavior lives in the adapter (R2, §2 "standard over sample").
