# TypeScript/JavaScript adapter

Parses TypeScript/JavaScript into the code-atlas contract vocabulary. Self-contained: its runtime and
dependencies live here and never reach the Python core (R8.1). Started as the task 128 M0 spike; task
019 is growing it into the full M7 adapter (in slices — see the task for what has landed).

## Runtime

- **Node.js ≥ 18.**
- **[typescript](https://www.npmjs.com/package/typescript)** (the compiler package), pinned by the
  committed `package-lock.json` so every machine resolves the same build. Install with `npm ci`
  in this directory. `node_modules/` is git-ignored.

Parsing uses `ts.createSourceFile` — a **syntactic** parse, with no `Program` and no type checker.
That is deliberate: the v1 file-at-a-time contract survives a second language (PLAN §4.4). Type-
*inferred* receivers (the `semantic_types` capability) are the one thing that would need more, and
are still out of scope.

## Protocol

Two modes, mirroring `adapters/php/index.php`:

```bash
node index.js --file <path>     # parse one file, emit one JSON result line, exit
node index.js --server          # emit the handshake, then one result per request line on stdin
```

Configure the server launch via `CA_TYPESCRIPT_CMD` (the core resolves any `CA_<LANG>_CMD` generically
— no core change was needed to add this adapter):

```bash
CA_TYPESCRIPT_CMD="node /abs/path/adapters/typescript/index.js --server"
```

## What it emits

**Nodes** (contract kinds, keyed on TS syntax, never on an identifier — R2):

| TS construct | node kind | notes |
|---|---|---|
| source file | `File` | qnamed by its repo-relative posix path — the CONTAINS root |
| `namespace` / `module` | `Namespace` | nests with `::`, never TS's `.` |
| `class` | `Class` | type params erased from the qname (`Box`, not `Box<T>`) |
| `interface`, `type X = …` | `Interface` | a `type` alias is marked `extra.type_alias` |
| `enum`, `const enum` | `Enum` | `const enum` marked `extra.const`; members → `ClassConst` (`extra.enum_case`) |
| `function`, name-bound `const f = () =>`/`function` | `Function` | anonymous inline callables get no node |
| method / ctor / get / set | `Method` | constructor named `__construct` |
| property / field | `Property` | |
| module-scoped `const K = <value>` | `Const` | |
| unnamed `export default …` | (its kind) | qnamed `::default` so a default-import resolves |
| named `export default class Foo` | (its kind) | keeps `Foo`; an `ALIASES` from `::default` reaches it |

Decorators and declared types ride on a node's `extra` (`decorators`, `type`) — a decorator annotates
a declaration, so like a PHP attribute it emits **no** edge.

**Edges:** `CONTAINS`, `EXTENDS`, `IMPLEMENTS`, `CALLS`, `NEW`, `IMPORTS`, `ALIASES` (named
re-exports, and a named default export). Qnames are module-path-anchored and join every member
with `::`.

**A call is one of three things, and the adapter says which** (the split the PHP adapter documents):

| call shape | target | tier |
|---|---|---|
| `f()`, `this.m()`, `ns.f()` | the full qname where the adapter can name it | — (the core may reach `RESOLVED`) |
| `obj.method()`, `a.b.c()`, `super.m()` | the **bare method name** — the name is known, the receiver is not | `HEURISTIC` |
| `obj[name]()`, an IIFE | `(dynamic)` | `DYNAMIC` |

`HEURISTIC` there is load-bearing, not a label: the core's name-only fallback for a member call only
runs on an edge that claims it, and the claim caps the edge so a unique name is never promoted to
`RESOLVED` (R5.2). An inferred-receiver type table would promote these — still out of scope.

A body edge is **sourced at the scope that wrote it** — a call in a method is sourced at the method,
not at its class — the same stack the PHP adapter pushes (namespaces, class-likes and callables open
a scope; properties and consts only declare). `tests/contract/` freezes that source per case.

**Resolution (R3.3 — the adapter names, the core links).** A same-file target resolves to its full
qname; an imported name resolves to `<defining-file>::<exported>` by resolving the module specifier
(relative + `require`, extension/`index`, and a NodeNext `./x.js` to the `./x.ts` **source** ahead of
a compiled sibling) and reading the import binding — so the core links it `RESOLVED`.
`export { X } from "./m"` emits an `ALIASES` edge naming the defining module, so an import through a
barrel resolves to where `X` is declared; `export default class Foo` aliases `::default` to `::Foo`
for the same reason. Anything unresolved stays bare.

## Still out of scope (later 019 slices)

`args`/`arg_keys` on calls; the `semantic_types` inferred-receiver type table; `allowJs`/JSDoc types;
tsconfig `paths`/`baseUrl` aliases (an aliased specifier resolves to nothing, so its target stays
bare); `export *` per-name resolution; a `tsc`/eslint strictest-clean gate on this source (R6.6).
