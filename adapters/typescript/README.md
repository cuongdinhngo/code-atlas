# TypeScript/JavaScript adapter

Parses TypeScript/JavaScript into the code-atlas contract vocabulary. Self-contained: its runtime and
dependencies live here and never reach the Python core (R8.1). Started as the task 128 M0 spike;
completed as the M7 adapter in task 019.

## Runtime

- **Node.js ≥ 18.**
- **[typescript](https://www.npmjs.com/package/typescript)** (the compiler package), pinned by the
  committed `package-lock.json` so every machine resolves the same build. Install with `npm ci`
  in this directory. `node_modules/` is git-ignored.

Parsing uses `ts.createSourceFile` — a **syntactic** parse, with no `Program` and no type checker.
That is deliberate: the v1 file-at-a-time contract survives a second language (PLAN §4.4). A receiver's
class is inferred syntactically by a local type table (`semantic_types`, task 153 — see below); a
`Program`/checker is still not used, and 153's verdict is that nothing the graph needs requires one.

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
| method / ctor / get / set | `Method` | constructor named `__construct`; a named class's carries `extra.constructor` (367) |
| property / field | `Property` | |
| module-scoped `const K = <value>` | `Const` | |
| unnamed `export default …` | (its kind) | qnamed `::default` so a default-import resolves |
| named `export default class Foo` | (its kind) | keeps `Foo`; an `ALIASES` from `::default` reaches it |

Decorators and declared types ride on a node's `extra` (`decorators`, `type`); a decorator and a
named type reference also emit a `REFERENCES` edge (232) — a decorator-factory call is not a `CALLS`.
A static field read or written as `Foo.x`, or as `this.x` in a static member (an arrow inherits
`this`, a `function` rebinds it), is a `REFERENCES` onto `Foo::x` when `Foo` is declared in the file
(369); an instance field, a base class's field and a class from another file are not followed.

**Edges:** `CONTAINS`, `EXTENDS`, `IMPLEMENTS`, `CALLS`, `NEW`, `IMPORTS`, `REFERENCES`, `ALIASES` (named
re-exports, and a named default export). Qnames are module-path-anchored and join every member
with `::`.

**A call is one of three things, and the adapter says which** (the split the PHP adapter documents):

| call shape | target | tier |
|---|---|---|
| `f()`, `this.m()`, `ns.f()`, `super(…)` | the full qname where the adapter can name it (`super(…)`: `<Base>::__construct`) | — (the core may reach `RESOLVED`) |
| `obj.method()`, `a.b.c()`, `super.m()` | the **bare method name** — the name is known, the receiver is not | `HEURISTIC` |
| `obj[name]()`, an IIFE | `(dynamic)` | `DYNAMIC` |

`HEURISTIC` there is load-bearing, not a label: the core's name-only fallback for a member call only
runs on an edge that claims it, and the claim caps the edge so a unique name is never promoted to
`RESOLVED` (R5.2). The receiver type table below (153) names the receiver where it can.

A body edge is **sourced at the scope that wrote it** — a call in a method is sourced at the method,
not at its class — the same stack the PHP adapter pushes (namespaces, class-likes and callables open
a scope; properties and consts only declare). `tests/contract/` freezes that source per case.

A string or template literal that begins a T-SQL write or `EXEC` emits that edge onto the named
object at `HEURISTIC` (371, PHP's 335 shape): `INSERT INTO`/`UPDATE`/`MERGE INTO` → `WRITES`, `DELETE
FROM` → `DELETES`, `EXEC` → `CALLS`, only when the clause T-SQL requires follows the name. A
template's head before `${…}` and a literal before `+` are cut short; the `EXEC` guard also reads
`$1`. A type, a module specifier and a member's name are not read: no driver runs them. `tests/contract/sql_literal_cases.json` keeps the three copies in step.

**Resolution (R3.3 — the adapter names, the core links).** A same-file target resolves to its full
qname; an imported name resolves to `<defining-file>::<exported>` by resolving the module specifier
(relative + `require`, extension/`index`, a NodeNext `./x.js` to the `./x.ts` **source** ahead of a
compiled sibling, and a non-relative `@alias` through the nearest tsconfig `baseUrl`/`paths` — task
155) and reading the import binding — so the core links it `RESOLVED`.
`export { X } from "./m"` emits an `ALIASES` edge naming the defining module, so an import through a
barrel resolves to where `X` is declared; `export default class Foo` aliases `::default` to `::Foo`
for the same reason. Anything unresolved stays bare.
A `require` whose path is built from `__dirname` and literals (`+`, a template, or `path.join` /
`path.resolve` of node's `path` module) imports the file it names exactly; another head with a `/…`
literal is a `HEURISTIC` tail, completed with the requirer's extension when it has none, which the
core links to the one file ending with it (370, as PHP's 353). Either way the file keeps its
`dynamic_import` stamp unless the path was exact, and a `require(name)` stays a stamped runtime load.
`path` is read by its file-level binding, so a function that rebinds the name is not followed.

## Static analysis (R6.6) — `tsc --checkJs --strict`

The adapter source is authored as CommonJS `.js`, so "the equivalent of PHPStan max" is a choice.
The gate runs **`tsc` in `checkJs` + `strict` mode** over `index.js` and `src/**/*.js`, configured by
the committed `tsconfig.json` and pinned by `@types/node` in `devDependencies`. Run it with
`npm run typecheck`; `scripts/gate.sh` and `ci.yml` run it beside the PHP adapter's phpstan.

**Why tsc and not ESLint.** phpstan's analogue is *type* analysis, not lint style — and `typescript`
is already a committed runtime dependency, so `tsc --checkJs` adds no new toolchain (only `@types/node`
for the CommonJS/`node:` globals). ESLint would add a large devDependency tree to do a lint job the
type-checker's soundness checks subsume. Rejected: ESLint.

**The one strict flag held off: `noImplicitAny`.** The adapter's *own* source is deliberately untyped,
so full `noImplicitAny` reports ~72 implicit-`any` parameters that only per-parameter JSDoc on the
adapter's own functions would close. Typing the adapter's source to turn the flag on is a separate
concern (a future extension of task 150's
gate), **not** task 154 — 154 reads JSDoc off the *indexed* code, it does not type this repo. This is a
scoped setting, **not** a suppression: there is no baseline file, no `@ts-nocheck`, no `eslint-disable`.
Every other strict check (`strictNullChecks`, `noUnusedLocals`, `noImplicitReturns`, …) is on and clean.

## Module aliases and `export *` (task 155)

A non-relative specifier is resolved through the **nearest `tsconfig.json`** up the tree (`extends`
followed), reading `baseUrl`/`paths`: `@app/models` names `src/models.ts` and every edge through it
resolves, the same as a relative import. The config is read from disk by the adapter (the core stays
language-blind, R1.1) and is the language's own standard, not a bundler's (R2). A missing or malformed
`tsconfig.json` degrades to a bare specifier — never a crash (§4.1). Each tsconfig is parsed at most
once per process.

**`export * from "./m"` stays `IMPORTS`-only — a documented file-at-a-time limit, not a gap.** A named
re-export (`export { X } from "./m"`) aliases `X` to its defining module, because the name is written
in the file. `export *` names nothing: enumerating what `./m` exports needs `./m` (and its own
transitive `export *`s) — whole-program knowledge a file-at-a-time parse does not have. A shallow
one-level disk read would resolve some names and silently miss re-exported ones, which is worse than an
honest bare edge. So the module dependency is recorded (`IMPORTS`) and per-name resolution through an
`export *` barrel is not; revisit only if the contract gains a resolve pass.

## Call arguments — `args` / `arg_keys` (task 152)

Every `CALLS`/`NEW` edge carries the contract's `args` (one category per argument, in source order)
and the parallel `arg_keys`, mirroring the PHP adapter. The category is the *shape*, never the value:
`string` · `number` · `true` · `false` · `null` · `array` (an object **or** array literal); any other
expression is `null`. `arg_keys` is the object literal's ordered string keys (`[]` for a positional
array literal, `null` otherwise).

Four TS shapes with no PHP analogue have a stated answer:

| shape | answer |
|---|---|
| a **spread** call argument (`f(...xs)`) | positions become untrustworthy → the whole `args` list is dropped (edge carries neither field), as PHP does for `...$unpack` |
| a **template literal** (`` f(`hi ${x}`) ``) | category `string` — a string-typed expression, as PHP treats an interpolated string |
| a **shorthand property** (`{ short }`) | its name is a key (`short`) |
| a **computed key** (`{ [k]: 1 }`) or an object **spread** (`{ ...rest }`) | contributes no key and does not shift later keys |

## Receiver types — `semantic_types` (task 153)

A member call `obj.method()` resolves to `<Class>::method` at `RESOLVED` when a **local type table**
(`src/types.js`) can name the receiver's class — otherwise it stays the bare, `HEURISTIC` method name.
The table is syntactic and file-at-a-time, mirroring the PHP `TypeTable`; every binding is one the
language itself puts in the file:

- `const x = new Foo()` — an inferred `new`;
- a parameter or property **annotation** (`(x: Foo)`, `dep: Foo` → `this.dep.m()`);
- an assignment `x = new Foo()`.

It is **flow-sensitive and forgetful**: `x = somethingElse()` re-opens `x`, so a stale class never
outlives the assignment that invalidated it. An arrow/function expression inherits the enclosing
scope's bindings; a function/method/constructor starts fresh with its typed parameters. The adapter
announces `capabilities: { semantic_types: true }` now the table backs it (R1.6 — announced data, no
core branch).

**No `Program`/checker (the 153 verdict).** 019 settled that a whole-program `ts.Program` is not
needed, and this table confirms it: the receiver classes the graph can act on are the ones the spec
writes into the file, which a syntactic pass reads directly. What a type table *cannot* reach — a
receiver that is the **return type of another call** (a fluent `a().b().c()` chain), or a type only a
cross-file/whole-program view knows — is a file-at-a-time limit, not a checker gap; it is the residual
the measured HEURISTIC share still carries, and would be its own ticket if a field round demands it.

## JSDoc as a type source (task 154)

A `.js`/`.jsx`/`.mjs`/`.cjs` file carries its types in **JSDoc**, and the adapter reads them off the
AST (`node.jsDoc`) — still syntactic, no `Program`:

- `@param {Foo}` / `@returns {Foo}` / `@type {Foo}` fill the same `extra.type` slot a TS annotation
  does, so a consumer sees one field regardless of flavour;
- those same JSDoc types feed the 153 local type table, so a JSDoc-typed receiver
  (`@param {Foo} p` → `p.method()`) resolves to `<Class>::method` exactly as a `.ts` one would;
- a `@typedef` / `@callback` is a named type — the `.js` analogue of a `type` alias — so it emits an
  `Interface` node (marked `extra.type_alias`).

The `.mjs`/`.cjs`/`.jsx` flavours are the same construct at a different `ScriptKind`, not new cases;
the R6.2 inventory carries one `jsdoc-types` entry. **Known limit:** an *inline* class-field JSDoc
(`/** @type {Foo} */ field`) is not attached to the field node by `ts.getJSDocType` in JS mode, so
that one placement is not typed; a `@param`/`@returns`/`@type`-on-a-variable is. Reading a declared
type is not verifying it — there is no type-checking of the indexed JS.
