# Code-Atlas MCP — Build Plan

> Status: **shipped and in daily use** — Phase 1 (core + PHP, M0–M6) and Phase 3 (onboarding,
> M10–M12) are complete, 17 tools on the surface; Phase 2 (adapters #2–#4) is deferred (§19).
> A local-first, multi-language code-intelligence MCP server.
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
- No type inference **in the core** (adapters may supply it where free — e.g. Roslyn's semantic model, and a PHP local type table, now measured and owned by [137](tasks/137_php-local-type-table.md) / opt-in PHPStan `semantic_types`; §19).
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
- **Abstract nothing that does not yet have two implementations.** No plugin registry, base classes
  or DI container for one language. **Language #2 (TypeScript/JavaScript) reveals the correct
  abstraction** — deliberately chosen because its model is the *most different* from PHP (no FQNs;
  module-scoped `import`/`export`; ESM+CommonJS; `tsconfig` path aliases; project-context
  resolution). It stresses the two things most likely to be PHP-shaped after building only PHP: the
  `qualified_name` convention and file-at-a-time resolution. Expect a **contract v2** there (§4.4).
  C# and Python confirm and extend rather than reshape.
- **Standard over sample is a claim about scope, not just about naming:** if a fact about a repo
  would change adapter behaviour, it belongs in the language spec or nowhere. Sample repos buy test
  coverage and performance targets, never semantics (§6.1). §19 extends the same rule to *evidence*.

Precedent to copy: a mature multi-language LSP framework (one abstraction + N concrete language
servers + a `get_ls_class()`-style factory) is OCP/DIP at scale; a `Tool`/`ToolRegistry` +
marker-mixin design is ISP in practice.

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
← {"name":"php","extensions":[".php"],"capabilities":{},"contract_version":7}   # handshake, first line
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

**The DDL is not copied here.** It is one `DDL` string in `store.py`, which is the only module that
may hold it; this section is the inventory and the reasoning. What the schema is, in shape:

- **`files`** — one row per indexed path: content hash, language, `parsed_ok`, `updated_at`. The
  hash is what makes an incremental build possible (§8.3) and `parsed_ok` is why no parallel
  parse-failure counter exists (task 028).
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

**Resolution order: env `CA_*` → project file `.code-atlas.toml` → default.** The file lives at the
repo root, is meant to be committed, and is read with stdlib `tomllib`; its keys are the env names
lower-cased without the prefix, plus an `[adapter_cmd]` table holding one complete argv per language
(§9). A malformed value or an unknown key **fails loud** (R5.3) — it never falls back. Naming rules
are in [`CONVENTION.md`](CONVENTION.md) §2; what each knob *governs* is here.

| Knob | Default | Governs |
|---|---|---|
| `CA_DB_PATH` | `<repo>/.code-atlas/graph.db` | where the index lives |
| `CA_WORKERS` | `max(1, min(cpu-2, 8))` | adapter processes in a full build (§8.1) |
| `CA_ADAPTER_TIMEOUT` | `30` s | how long one adapter may stay silent before the build kills it (§8.1) |
| `CA_MAX_RESULTS` | `50` | rows a tool returns **and** the resolver's per-call-site candidate fan-out (§8.2) — one knob, two jobs; see the follow-up in BACKLOG |
| `CA_MAX_SUBJECTS` | `25` | subjects one `search_symbol` sweep may take (101) |
| `CA_IMPACT_DEPTH` / `CA_IMPACT_MAX_NODES` | `2` / `500` | impact/reachability/path walk bounds |
| `CA_ORPHANS_MAX_NODES` | `500` | the reachability walk inside `find_orphans` only — **not** borrowed from impact (124) |
| `CA_ENTRY_POINTS` | unset | reachability roots (file globs). Unset ⇒ the tools report *no roots*, never a guess (031) |
| `CA_STUB_ROOTS` | unset | dependency roots to index declarations-only (039) |
| `CA_INDIRECTION_RULES` | unset | rule files mapping framework indirection to ALIASES/CALLS/view-data edges (040/062/063) |
| `CA_TOOLS` | unset ⇒ all | the served tool allow-list (§12) |
| `CA_HOST_ROOT` / `CA_CONTAINER_ROOT` | unset | rewrite **absolute** host paths onto a container root; both set or neither (§9) |
| `CA_<LANG>_CMD` | — | the complete argv launching that adapter (§9), resolved generically from the variable name so no language is named in the core |

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

**Seventeen tools.** Token-efficient: qualified names + `file:line`, not bodies, unless a read tool
is called. The **payload contract** — `detail_level`, the provenance fields (`index_root`,
`last_ref`/`head_ref`, `server_version`/`server_build`), the honesty fields (`reason`,
`total_count`, `truncated`, `walk_truncated`, `try_instead`, `resolved_qname`, `result_kinds`,
`limit_capped_to`, `result_subtrees`), and the batching rules — is specified once in
[`CONVENTION.md`](CONVENTION.md) §6 and is **not** repeated per tool below. This table says what
each tool *answers*; §6 says what every answer must disclose. `get_index_status` (058) and
`architecture_overview` (086) additionally accept `verbose`, in both cases for a capped extra list
that must not ride the cheap path.

| Tool | Key args | Answers |
|---|---|---|
| `get_index_status` | `detail_level?`, `offset?`, `sign?` | is the index there, fresh and healthy — stats, `last_commit`, staleness, reactive `next_tool_suggestions`; `standard` adds `edge_health`, `parse_failures`, `db_path`; `verbose` adds capped `parse_failure_paths` (058) and **`collection`**, the denominator for reconciling `files` against your own `git ls-files` without reading source (082). **Call first (~100 tok).** |
| `build_or_update_index` | `full=false`, `detail_level?` | builds or refreshes; returns `wrote` (what *this run* wrote) + timing, and at `standard` `graph`, so a delta cannot be mistaken for a repo size (051/060). A concurrent writer returns `mode: "busy"` with `performed: false` and the loser's staleness (072); no usable adapter returns `mode: "refused"` and writes nothing — a payload, not a raise (064/079) |
| `search_symbol` | `query \| queries, kind?, namespace?, limit?, offset?` | ranked `{qname, kind, file:line}` (FTS + name); stub hits add `stub: true` (039); a zero hit may miss-repair the sole dirty file or report `index_stale` (073). **`queries` sweeps N subjects in one call** (101) |
| `file_outline` | `path, limit?, offset?` | the file's symbol map — symbols + line ranges, no body |
| `read_symbol` | `qname` | source of just that class/method + its docblock; stubs add `stub: true` (039). A qname with >1 definition **refuses the body** and lists `ambiguous_definitions` (070 → 078) |
| `find_callers` | `qname, depth?, include_source?, arg_position?, arg_is?, limit?, offset?, sign?` | who CALLS/NEW it, with confidence tier; opt-in capped call-site `source` (037); opt-in argument filter at a 1-based position, with `args_unrecorded` counting the sites it could not judge (049, depth 1 only). Depth 1 enumerates completely; deeper, `total_count` is a floor for that page |
| `find_references` | `qname, include_source?, limit?, offset?, sign?` | every mention — CALLS/NEW plus `REFERENCES` (`Foo::class`, 094). An all-`DYNAMIC` page sets `authoritative: false` so it reads as a candidate list |
| `find_implementations` | `qname, limit?, offset?` | EXTENDS/IMPLEMENTS subtypes |
| `find_view_data` | `qname \| key, limit?, offset?` | which view-scope keys a handler publishes, and which handlers publish a key — the `PROVIDES_VIEW_DATA` relation (062/063). Empty when no `view_data` rules are configured, and it says so rather than reporting a modelled zero (069) |
| `include_graph` | `path, direction` | the `include`/`require` graph; `unresolved_includes` on `imports`/`both` only — a counter that is structurally zero inbound is omitted rather than printed (065) |
| `impact` | `paths \| qnames, depth?, sign?` | blast radius — bounded best-score over resolver-linked IMPACT kinds; `seeds_dropped` (see below) |
| `subtree_dependencies` | `subtree, counterpart?, limit?` | tree-to-tree crossing with duplicate-declaration attribution — attributable vs unattributable always paired; dynamic bridges surfaced (120) |
| `reachable_from` | `depth?` | what is reachable from `CA_ENTRY_POINTS` over RESOLVED IMPACT kinds; HEURISTIC/DYNAMIC neighbours are `unproven`, not reachable |
| `find_orphans` | `depth?, limit?, offset?` | the complement — zero-inbound / unreachable-from-roots, each with `why`; never an empty success when no roots are configured |
| `explain_path` | `from_qname, to_qname, depth?` | the shortest A→B route over outgoing IMPACT kinds; `status` = `path` / `unproven` / `no_path` / `unknown` / `incomplete`, so a bound hit is never conflated with "no route" |
| `architecture_overview` | `detail_level?`, `offset?` | this repo's responsibility layers ordered by net dependency direction — one row per layer with its module count, and at `standard` its degree profile |
| `guided_tour` | `detail_level?`, `offset?` | a dependency-ordered reading list, seeded from zero-inbound entry points and cycle-safe via SCC condensation (087); seeds prefer out-degree > 0, capped at a quarter of the budget (106), ready-set ordered by reading-seed layer rank (131) |
| `generate_onboarding` | `detail_level?` | writes the committable artifact from the graph — `docs/onboarding/` markdown + `manifest.json` + a self-contained `index.html` system map (088/089/116). It removes only the pages its own last manifest recorded, and refuses a tree it does not own |

*Considered and not planned:* `namespace_tree` — named as a task-013/014 consumer of `split_qname` and
never built. `search_symbol` already takes a `namespace` filter, `architecture_overview` answers repo
shape, and §19's founding-premise benchmark found the gap is **demand and modelling, not capability**:
the whole-graph tools it would have joined had already shipped and no real question needed one. A
scanned tool surface has a budget (081), so re-propose it on a field question no shipped tool answers.

**Claim signing — `sign: true` on the four attesting tools (100).** An attestation that never reaches
the artifact where the claim is made has, practically, not been produced: the round-5 session pasted
nine kinds of counted evidence into its PR and **zero** code-atlas output. `impact`, `find_callers`,
`find_references` and `get_index_status` therefore take `sign: bool = False`, adding one `claim` key —
a single `key=value` line naming tool, subject, question, answer, the revision the index describes and
the running server. `claim.py` is a **pure formatter** over an already-computed payload, so R1.4/R4.1
hold by construction and key order is fixed for R4.2. **Every caveat owns its own key** — `tier` names
the *weakest* tier present, plus `index=behind`, `authoritative=false`, `truncated=true`, `reason=` —
so a degrading answer cannot drop one the way a prose clause can. **No line is emitted** for an unbuilt
index or an `impact` answer where no seed resolved: a claim that cannot be re-run is decoration. The
thirteen tools whose answers are lists of rows rather than claims are not signed. Measured cost: **+51
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

**Operator prompts, not agent routing (081).** `explore_area`, `impact_of_change`, `find_usages`,
`which_tool` hardcode the efficient recipe. An agent's client surfaces only *tools* to the model, so a
model never sees a prompt — they are human-invoked recipes, and routing for agents lives in the
descriptions above. Counting a human-facing channel as agent-facing was a category error, not a bug.

**Serving (010).** `main.build_server(config)` registers the allowed tools on one FastMCP app and
`main()` serves it over stdio; the entry point is `code-atlas` (or `python -m code_atlas.main`).
`CA_TOOLS` gates the surface. Each call opens its own `GraphStore` — see CONVENTION §6 for why.


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

**Shipped (M10–M12, §15).** Not a fork of Understand-Anything — a **consumer of the graph already
built**, which is the substrate UA spends its whole pipeline producing, at higher fidelity than
tree-sitter, and multi-language for free. Full detail in
[`phase3-onboarding/ROADMAP.md`](phase3-onboarding/ROADMAP.md).

It adds two things the graph lacks, and **both landed differently than this section first assumed:**

1. **Semantic layer.** Layers turned out to be **deterministic** — 110's ratified responsibility
   vocabulary names them, and 117 measured that 091's LLM rename seam fires on nothing. The LLM ended
   up owning **prose only** (layer descriptions, tour narratives, headline wording) behind three
   opt-in seams in `onboarding_llm/`, off by default. The per-module **summary is still empty**: the
   seam is fed read-through docblocks at build time (**118**, done).
2. **Presentation.** 116 replaced the imagined page dump with a **navigable system map** rendered from
   112's single compact dataset.

The discipline held throughout: **deterministic graph (core) → LLM enrichment (onboarding) →
presentation.** The LLM touches only the onboarding layer, is off by default, and lives outside
`code_atlas/` (R4.1, CI-gated). Surface: `architecture_overview`, `guided_tour`,
`generate_onboarding`, writing `docs/onboarding/` with a versioned `artifact.json`
(`ARTIFACT_VERSION`, gitignored under `.code-atlas/onboarding/`). **What the phase is measured as, after 121: a navigation and provenance
aid, not a reading order** (§19).

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

**Phase 2 — More languages (order: TS/JS → Python → C#) — deferred, §19:**
- **M7** **TypeScript/JavaScript adapter** (TS Compiler API via `ts-morph`, Node sidecar) behind the *unchanged* core — the real test of OCP/DIP. Expect **contract v2** here (project-context resolution, module-scoped qnames — §4.4).
- **M8** **Python adapter** (`ast` + `jedi`) — cheap once the contract is hardened.
- **M9** **C#/.NET adapter** (Roslyn sidecar) — confirms the contract holds for a second namespaced+semantic-model language.

**Phase 3 — Onboarding** (deterministic-first; LLM opt-in and out of core + CI). All three milestones
are **complete**; the per-task breakdown, including the 108–117 reshape, is in
[`phase3-onboarding/ROADMAP.md`](phase3-onboarding/ROADMAP.md).
- **M10** `architecture_overview` + deterministic layers — 083 · 084 · 085 · 103 · 104 · 086. The 15th tool; 105 elects the dominant subtree by graph mass, proven on three pinned repos.
- **M11** `guided_tour` (16th) · `generate_onboarding` (17th) · the viewer — **reshaped by 108–117 into the navigable system map**, rendered from 112's dataset alone (`DATASET_VERSION` 7). 116's AC4–AC6 are proven by running the page headlessly under `tests/viewer_dom_stub.js`, because a grep over the HTML sees zero rendered figures and would be a false green.
- **M12** LLM enrichment, opt-in and outside the core — 090 · 091 · 117. The per-run call ceiling is **derived, not invented**: 6 headline families + 12 responsibility layers + 109's 15-step ceiling = **33 calls a build**, enforced per slot so a repo falling back to per-directory layers cannot starve the tour (measured at 18,929 files: 1,176 requested, 12 served, 1,164 refused).

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
| No type inference for PHP instance calls | Name-match HEURISTIC; the LSP defer covers only the **≤0.6 %** late-binding residual. **136 measured** local type information as the cause of **≥99 %** of the HEURISTIC share, and `vendor/` coverage as its cap (0 / 22.5 / 92.5 % of that share is linkable across the three pins) — [benchmark](benchmarks/136_heuristic-causes.md), owned by 137. C# gets it free via Roslyn capability. |
| PHP 8.5 edge cases | nikic ^5 latest; collecting handler flags `parsed_ok=0`. |
| Host PHP absent | Docker-exec mode (§9-B) or tokenizer-only PHP CLI. |
| 100k-file DB/memory | SQLite WAL, serial writer, indexed queries, caps; traverse in SQL, never load whole graph. |
| Overlap with LSP-based tools | Clear division (§13); optionally trim the LSP tool's search tools. |

---

## 18. Open questions for review

Four of the original six are **closed** and recorded where they were decided: the language order and
its deferral (§3, §19 pivot), the PHP validation repos (task 018 — public pins in
`scripts/cross_repo_samples.json` plus an operator-local monorepo via `CODE_ATLAS_SCALE_SAMPLE`), the
ship point (M3, task 014 — shipped), and onboarding presentation (both: committed markdown *and* a
viewer, §14). Still open:

1. **PHP runtime** — both modes ship (§9); is a host PHP 8.5 CLI acceptable for indexing on the
   operator's machines, or is Docker-only the standing answer?
2. **LSP-tool coexistence** — keep a language server's PHP search tools on, or trim it to nav/edit?
   §13 says they are not substitutes and the founding-premise benchmark could not make an agent
   choose between them, so this stays a per-installation preference rather than a project decision.
3. **TS/JS validation repos** — unresolved, and only becomes live at M7.

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
- **Depth over breadth.** TS/JS (019) and Python/C# (020/021) are **deferred, not cancelled** — finish
  the PHP agent-loop first; breadth before depth would leave us mediocre at both. **Human-ratified
  2026-08-04:** a large private PHP monorepo is the anchor for **testing *and* evaluation**, so depth
  on PHP is measurable in a way breadth would not be.
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
  fan-out over worktrees OOM'd because each agent re-spawned a resident-LSP code-intelligence server
  (~5.6 GB each, and pointed at `main` rather than the worktree). code-atlas does **not** reproduce the
  *memory* half — no resident server, SQLite opened per call, adapters transient and one file at a
  time. It **does** reproduce the *routing* half; this entry originally claimed otherwise, corrected
  in the next one.

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
  fixed**, 2 improved, 1 reproduced (054), 2 not exercisable. **Three caveats it states about itself:**
  the protocol was violated (the verification section was read first, so its recognition test is void),
  the server process changed mid-session via a client reconnect, and 4 of 6 question shapes never arose
  in three hours. **The two findings that mattered came from outside the verification section**, which
  is a regression harness and cannot surface anything new — 075 (`read_symbol` answering
  `{"found": false, "reason": "ok"}` for a class the index holds, while the evaluator was reviewing a
  PR claiming to extend it) and 077 (an out-of-band branch switch left `staleness: "current"` true,
  correct and useless, because no payload names the revision).
  Order and the round's self-corrections: [`BACKLOG.md`](BACKLOG.md#where-these-tickets-came-from).

- **Qname-subject honesty — 075 + 076 shipped together (2026-08-11; one shared design).** A
  **malformed** subject (a class stored with a leading `\`, queried without it) and an
  **under-qualified** one (`find_callers("isEnabled")` while the qualified form has 82) were one defect
  class: both read as *absence*. One language-agnostic classifier
  (`nav_result.classify_missing_subject`) counts indexed qnames ending with the subject at a component
  boundary — **0** → `no_such_symbol`, **1** → resolve to the stored qname, **many** →
  `name_not_qualified` + `candidate_count` + `try_instead` — across all seven qname tools. No `\` is
  hardcoded in the core (that is PHP-adapter canon); the classifier keys off the generic identifier
  class `[A-Za-z0-9_]`, not a language branch (R1.1). **Decision: no adapter `contract_version`
  bump** — nav `reason` codes are tool-output vocabulary (`nav_result.NAV_REASONS`), not the adapter
  JSONL contract, and bumping it for a tool string would force every user to reindex for nothing.

- **Field retro round 5 (2026-08-14, `348a8a7`) — the first round with mechanism questions, and the
  first where cost changed what was asked.** **8 of 8 checked claims exact, zero false statements:**
  every failure was silence or ambiguity, never a wrong answer, which is why §10's carve-outs are
  narrow. Three things no earlier round could establish:
  - **Cost shapes behaviour, not just the bill.** Under 1 % of session tokens but **181.7 s** of
    in-work build time, and the cliff is entirely between zero files and one (0 → 2.1 s, 2 → 59.25 s).
    The evaluator batched 8 calls at the start, 7 at the end, **1 in three hours of writing code** →
    **096**, which scopes late resolution on **what the delta declares** (qnames + bare method names),
    not on which files it touched: file A can hold an unresolved edge to a class file B adds, and A is
    never a dependent while `target_qname` is still NULL.
  - **Recognition ≠ recall, and the probe only measured recognition.** It scored **14/14** while 7 of
    14 descriptions were never loaded, so 081's stated mechanism was never exercised → `NOT OBSERVED`,
    and **097** split the probe into name-only and description-backed rates. **Descriptions can name
    an occasion; they cannot make an agent notice it.**
  - **Two independent nothings were indistinguishable** (**092**): four newly written classes were
    untracked, so `collect()`'s `git ls-files` walk never saw them; the build reported no skip,
    `dirty_indexed_files: 0` was literally true and actively misleading, and the lookup answered
    `no_such_symbol` for a class on disk while the vocabulary already owned `not_indexed`. Shipped with
    093, 094 and 095.

  **Open, not ticketed:** nothing searches unlinked include text, so *who includes this file* stays
  unanswerable when the path is dynamic. **074 advances to n = 1** for session type *legacy→unified
  port* — **helped, narrowly**, after the retraction below.

- **Field interview — "the questions you did not ask" (2026-08-14, same session).** Six questions about
  the moments the evaluator **did not** call the tool. **Weight it as one observer, not two** — the
  interviewee authored the retro an hour earlier and declares itself contaminated; it survives because
  it inventories *non-events*, which no retro asked about. It earns its keep three times:
  - **It retracted the round's headline.** The "prevented a latent flag-gated fatal" story rests on PHP
    method names being case-sensitive; they are not. **The lesson is about the instrument, not the
    claim: a retro cannot audit itself, and a same-session interview is the cheapest thing that can.**
  - **Adoption is a *position* problem, not a speed problem** — the finding that matters. All **three**
    decisions made without the graph wanted **one line inside a `Read` already happening**, and none
    wanted a tool call; the two highest-value uncalled queries needed no rebuild and would have cost
    ~1 s. **Shipped (099), and the verdict is a position statement as much as a feature:** the signal
    lives in the **host's hook surface**, not on a payload rider — `next_tool_suggestions` reaches the
    agent *after it asks* and the core cannot observe a `Read`, so that channel is **structurally**
    incapable of carrying this, not merely too expensive (061). `code-atlas-signal` ships two lines, a
    ~150-token cap, no build and no write lock, and silence by default. **code-atlas offers the command
    and wires nothing.** The ceiling this records on 069/081-style routing work: *no description reaches
    an agent that never opens the tool list* — which is why 097 and 099 are one finding from two sides.
  - **The evidence-layer thesis has behavioural proof, against the evaluator's own interest:** the PR
    body pastes **nine** kinds of counted evidence and **zero** graph payloads, while `impact` had
    already returned `seeds_dropped: 0` → **100**. Also new, a **call-shape** miss no cost metric can
    see: the collision sweep had ten subjects, the graph takes one per call, a shell loop takes all ten
    → **101**.

  **The one judgement the interview cannot make for us:** the anchor's dominant chore is porting a
  legacy file into the unified tree without breaking the other region, and the graph holds **neither**
  relation that chore is made of. Its proposal — seed the first from a ~4,300-entry mapping the repo
  maintains — is **adopted in principle, rejected as proposed**: ingesting a repo's own mapping file is
  sample-over-standard (R2). What the core may learn is one **generic correspondence relation**,
  config-fed and adapter-blind, under which legacy↔unified and region-A↔region-B are the same
  primitive → [098](tasks/098_correspondence-relation-seam.md), deferred behind the evidence gate below.

- **Phase-3 reshape (2026-08-20; tasks 108–117) — a human read the emitted artifact and it was
  unusable.** M11 passed every test and failed its reader: 43 MB, a median module page of **82,218
  bytes** that was 99.96 % flat path lists, `Summary: (none)` on **500/500** pages, and a 500-stop
  "tour". **The decision it forced is an audience split: the MCP tools are the product for an AI, the
  onboarding artifact is the product for a human.** 116 then measured that **108 had already removed
  ~97 % of the 31 MB**, so the size half of the complaint was largely spent before the map was built —
  "data dump, not a map" was the whole of it. Two R2.2 judgments were settled: a generic architectural
  vocabulary **is** a standard (110, maintainer-ratified), and 113 needed **no** separate vendor signal
  because that vocabulary already carries `vendor`. Mockup and waves:
  [`ONBOARDING_MOCKUP.md`](phase3-onboarding/ONBOARDING_MOCKUP.md) ·
  [`ROADMAP.md`](phase3-onboarding/ROADMAP.md).

- **Field measurement on the anchor (2026-08-21) — two things the shipped map could not say.**
  Regenerating on 18,972 modules / 135,649 symbols took **17 s** and produced a **950 KB** map, 500
  pages at a **median 2,943 B** (against 82,218 B before 108), gate green. Both findings are open
  tickets. **118** — the `Summary: (none)` cause is **not** the one 117 recorded: `artifact.py` passes
  blank `NodeFacts`, so the deterministic summarizer is starved on *every* repo and the opt-in LLM
  implementer with it. The anchor has docblocks; **the graph has nowhere to carry one** — a contract
  gap, not a seam gap. **119** — a stale `CA_ENTRY_POINTS` glob put **560** unreachable files in *Web
  entry points*, made every unreferenced legacy page self-justifying to `find_orphans`, and nothing in
  the output could expose it; after the operator corrected the knob the bucket went **901 → 341**.
  *Classification changed; no fact did* — which is the argument for provenance beside a count.

- **Field retro round 6 (2026-08-21) — four findings, all payload honesty, none a graph defect.** The
  round's own closing line is the finding: *"the graph knew everything I asked it; the failures were
  the tool knowing and not saying how much it was not telling me, and the tool knowing and declining
  over punctuation."* Two lessons outlive the tickets. **How a sibling surface is closed:** 075
  recorded a prose verdict, four `find_*` tools went on discarding its resolved qname inside the shared
  `shape_exact_miss`, and only an enumerating test over the classifier's callers shut it — one silently
  empty answer had already moved the evaluator to `grep` for the remaining four of five tickets (122).
  **Once rows page, `truncated` must describe the page alone:** folding a walk budget into it left
  every page of a large repo reporting `truncated: true` forever, so the walk's own bound is
  `walk_truncated` (124). 123 and 124 are **recorded exclusions meeting their first field evidence**
  (057, 066), not oversights. 125 is the cheapest and most self-implicating: no payload named the
  server build, so every retro in this series has been told its own subject by an operator.

- **Phase 3's own cost gate ran (2026-08-23; task 121) — a split verdict, and the losing half narrows
  the phase.** `ROADMAP.md` §5 gated the whole phase on an onboarding question-class in the
  tokens-to-answer harness plus the recall gate; three milestones shipped while the file held **zero**
  onboarding questions. It now holds **twelve**, every ground truth read out of the source by hand
  before the tools ran. Numbers:
  [`benchmarks/121_onboarding-question-class.md`](benchmarks/121_onboarding-question-class.md).
  **The half that wins:** 12/12 correct, recall 1.0, `confidently_wrong` 0, and the fixture aggregate
  moved **0.29 → 0.789** because onboarding questions are the first fixture-tier questions that make
  grep read more than one file. Nine of the twelve have **no** fair baseline and say so in a
  `ratio_note` rather than inventing one that would flatter the comparison.
  **The half that loses, which is the more useful half:** where the question is a **reading order** the
  map is wrong — ~~`guided_tour`'s first five stops on `symfony/demo` are a lint config, two bootstrap
  configs and an importmap, front controller fifth (131)~~ **131 closed** — re-measured first five open
  on controllers and include `public/index.php`; ~~the `web_entry` bucket calls **8** files the
  web surface when 4 are `tests/Controller/*Test.php` (130)~~ **130 closed** — test-path signal
  outranks request-handling vocabulary; and `include_graph(direction="imports")`
  was a silent zero for every namespaced file (129).
  **The narrowing, in §5's own terms:** the onboarding layer is measured as a **navigation and
  provenance aid**, not a curated syllabus. ~~`guided_tour`'s ordering claim is **not earned**.~~
  **131** closed the lint/bootstrap opening; the walk still is not the hand kernel/entity order.
   Auto-generated documentation and diagrams stay behind this line and behind **118** (done) — the
  founding-premise mistake was building on an unmeasured premise, and one measurement saying *"cheap
  and correct for lookups, wrong for orderings"* licenses neither.
  **What the gate cannot see, recorded rather than implied:** it scores recall and cost, never
  **precision** — ~~130 passes every mechanical check while being a wrong answer~~ **130 fixed the
  web_entry collision; precision now catches the pre-fix shape** — and never whether a
  human would act on the answer: on `symfony/demo` the largest layer is `Uncategorised` (18 of 51
  modules), a complete, correct, low-information answer that scores 1.0. The **mirror** shape, the
  anchor's most valuable one, cannot be measured by any committed tier, so it ships as a local-tier
  template in [`runbooks/tokens-to-answer.md`](runbooks/tokens-to-answer.md).

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

**Why not option 3 (permanent non-goal), and why not option 2 (both sides) yet.** The shape is common
enough to justify a contract bump later — 100 clean producer sites, 84 keys, thousands of consumer
reads — and two independent field sessions named it as the reason the index got zero queries on a real
defect, so declaring it grep's job forever would leave the exact gap the founding-premise redirect
promoted 059 to close. Both sides at once is a separate large cost (a template reader for mixed
Twig/Blade/PHP markup, reversing 041's ignore reasons, and true pair linking with only 6 path-literal
pairs to go on), so: ship the producer, revisit the consumer if field retros still fail after 062.

**What a language server does *not* solve here.** LSP go-to-def / find-refs operate on *symbols*. The
data-bag link is a **string key** — a literal in an array or setter on the handler side, a bare
variable in markup on the template side. Neither end is a symbol the PHP language server binds, so
Serena-class tools are as blind as today's graph. This is unclaimed ground, not an LSP race.

**Nav answer after 062.** Given a handler method, list the view-scope keys it publishes and at which
lines; the agent still `Read`s the template to confirm the consumer name — the half no current tool
answers. Shipped as edge kind `PROVIDES_VIEW_DATA`, `viewdata:<key>` targets, `CA_INDIRECTION_RULES`
`view_data` setters, and the tool `find_view_data`.

**Reference material** (private, same folder): `understand-anything-how-it-works.md`, `code-review-graph-how-it-works.md`.

**Primary validation sample:** a large private PHP 8.5 monorepo — PSR-4 `src/` + ~18k non-namespaced legacy + a ZF1 area, ~112k files, run via Docker (PHP not on host PATH). Used for scale/coverage testing **and (from 2026-08-04) as the agent-first evaluation anchor** (task 034) — always test/metrics only; no repo-specific behavior lives in the adapter (R2, §2 "standard over sample").
