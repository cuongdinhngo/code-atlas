# TypeScript/JavaScript adapter — M0 spike

Parses TypeScript/JavaScript into the code-atlas contract vocabulary. Self-contained: its runtime and
dependencies live here and never reach the Python core (R8.1). This is the **M0 spike** of task 128 —
it answers PLAN §4.4 with evidence; the full M7 adapter is task 019.

## Runtime

- **Node.js ≥ 18.**
- **[typescript](https://www.npmjs.com/package/typescript)** (the compiler package), pinned by the
  committed `package-lock.json` so every machine resolves the same build. Install with `npm install`
  (or `npm ci`) in this directory. `node_modules/` is git-ignored.

The spike uses `ts.createSourceFile` — a **syntactic** parse, with no `Program` and no type checker.
That is the point: it proves the v1 file-at-a-time contract survives a second language. Type-inferred
receivers (the `semantic_types` capability) are out of scope and belong to 019.

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

## What it emits (spike scope)

Nodes: `File`, `Namespace`, `Class`, `Interface`, `Enum`, `Function`, `Method`, `Property`,
`ClassConst`. Edges: `CONTAINS`, `EXTENDS`, `IMPLEMENTS`, `CALLS` (`this.m()` and identifier calls —
bare when cross-file), `NEW`, `IMPORTS`. Qualified names are module-path-anchored and join every member with
`::` — a TS `namespace` nests as `path::Ns::Class::method`, so `MEMBER_SEPARATOR` does not bend.

Same-file targets are resolved to their full qname (so the core resolver promotes a unique match to
`RESOLVED`); imported/unknown targets stay bare for the core to link (R3.3).

Out of scope for the spike (all 019): path aliases, ESM/CommonJS resolution breadth, `allowJs`,
`semantic_types`, CI's second runtime, and inventory beyond the two spike constructs.
