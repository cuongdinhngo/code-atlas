# Conventions — code-atlas

The **what things are called and where they live** rules. Concrete and mechanical, so the codebase reads
as if one person wrote it. For the *why/how we build*, see [`ENGINEERING_RULES.md`](ENGINEERING_RULES.md).

---

## 1. Repository layout

```
code-atlas/
├── pyproject.toml
├── .harness.json                     # mango lifecycle config (committed team config; no secrets)
├── .github/                          # workflows/ci.yml + pull_request_template.md
├── AGENTS.md                         # agent guidance (points here + to ENGINEERING_RULES)
├── CLAUDE.md                         # one line: `@AGENTS.md` — Claude Code's entry point, not a second copy
├── README.md
├── code_atlas/                       # THE CORE — language-agnostic, no per-language branches
│   ├── main.py                       # FastMCP server + entry point
│   ├── config.py                     # CA_* env/config resolution
│   ├── contract.py                   # JSON schema + validation + version (single source of truth)
│   ├── adapter.py                    # LanguageAdapter Protocol + extension→adapter lookup
│   ├── store.py                      # SQLite schema + GraphStore (only file that touches SQLite)
│   ├── indexer.py                    # full_build / incremental_update
│   ├── enrichment.py                 # optional CA_INDIRECTION_RULES → HEURISTIC edges (task 040)
│   ├── resolver.py                   # phase-2 edge linking (generic, no language branches)
│   ├── gitutil.py  ignore.py
│   └── tools/                        # one module per MCP tool
├── adapters/
│   ├── php/                          # self-contained: composer.json, index.php, src/{Parser,Visitor}.php
│   ├── typescript/ python/ csharp/   # added in order; each self-contained
├── tests/
│   ├── contract/                     # schema-conformance every adapter must pass
│   ├── fixtures/<lang>/…             # spec-driven fixtures
│   └── test_*.py
└── docs/
    ├── PLAN.md                        # authoritative design
    ├── ENGINEERING_RULES.md  CONVENTION.md  BACKLOG.md
    ├── runbooks/                     # operator protocols (onboarding, recognition probe, field retro)
    └── tasks/NNN_slug.md             # one file per task
```

## 2. Naming

- **Python package:** `code_atlas` (underscore). Project/repo name: `code-atlas` (hyphen).
- **Modules/functions/vars:** `snake_case`. **Classes:** `PascalCase`. **Constants:** `UPPER_SNAKE`.
- **Adapter driver:** one generic `SubprocessAdapter` in the core — **no class per language**. A language
  names itself in its handshake (PLAN §4.1); a `PhpAdapter` in `code_atlas/` would break R1.1/R1.5.
- **Tools:** `snake_case` verb-first, matching the MCP tool name exactly (`search_symbol`, `find_callers`,
  `read_symbol`, `build_or_update_index`). One tool per file under `code_atlas/tools/`.
- **Env vars:** prefix **`CA_`** (`CA_DB_PATH`, `CA_WORKERS`, `CA_ADAPTER_TIMEOUT`, `CA_MAX_RESULTS`, `CA_IMPACT_DEPTH`,
  `CA_IMPACT_MAX_NODES`, `CA_ENTRY_POINTS`, `CA_STUB_ROOTS`, `CA_INDIRECTION_RULES`, `CA_TOOLS`, `CA_HOST_ROOT`, `CA_CONTAINER_ROOT`, per-adapter `CA_<LANG>_CMD` e.g. `CA_PHP_CMD`).
- **On-disk artifacts:** project config `.code-atlas.toml` (repo root, committed — keys are the env
  names lower-cased without the `CA_` prefix, plus an `[adapter_cmd]` table whose values are a
  complete argv, as a string or a list of words); DB at
  `<repo>/.code-atlas/graph.db`; ignore file `.codeatlasignore`; onboarding output under
  `.code-atlas/onboarding/`.
- **Task files:** `docs/tasks/NNN_slug.md`, zero-padded 3-digit id, `kebab-case` slug (`014_search-read-outline.md`).

## 3. The contract vocabulary (fixed spelling — do not vary)

- **Node kinds:** `File Namespace Class Interface Trait Enum Function Method Property ClassConst Const`.
- **Edge kinds:** `CONTAINS EXTENDS IMPLEMENTS USES_TRAIT CALLS NEW IMPORTS INCLUDES REFERENCES ALIASES PROVIDES_VIEW_DATA`.
- **`REFERENCES`:** a textual class mention (`Foo::class` — task 094). FQN-linked at `DYNAMIC`;
  not a `CALLS` and not a `NEW`. `self`/`static`/`parent` name the enclosing class-like (as
  `CALLS` does), never a literal `\self`. Leftover unlinked rows still feed
  `relationship_not_modelled`.
- **`PROVIDES_VIEW_DATA`:** handler method → synthetic view-scope key. `target_raw` is
  `viewdata:<key>` (not an FQN; not in `FQN_EDGE_KINDS`). Emitted only by `CA_INDIRECTION_RULES`
  `view_data` setter rules (task 062); query with `find_view_data`.
- **Confidence tiers:** `RESOLVED | HEURISTIC | DYNAMIC`.
- **Node fields:** `kind, name, qualified_name, file_path, line_start, line_end, modifiers, params, is_test, extra`.
- **Edge fields:** `kind, source_qname, target_qname?, target_raw, file_path, line, confidence_tier, args?, arg_keys?`.
- **`arg_keys` (contract v5):** optional list parallel to `args`. For an `"array"` arg, a list of
  top-level string keys from the array literal (empty list = captured, none found). `null` for
  non-array args. Absent field = keys not captured (pre-v5). Used by `view_data` rules with
  `key_from: "array_keys"` (task 063).
- **Argument literals (`args` entries):** `null true false number string array` — the literal's
  *category*, never its value; a JSON `null` entry means "not a literal". Omitting `args` means the
  arguments are unknown, which is never the same as "no arguments".
- **Qualified-name convention (identical across languages):** the **container** keeps its language-native
  separator (`\`, `.`, `/`); the **member** boundary is always `::` (`contract.MEMBER_SEPARATOR`).
  - PHP/namespaced: `\Ns\Class`, `\Ns\Class::method`, `\Ns\Class::$prop`, `\Ns\Class::CONST`, `\ns\func`.
  - C#: `Namespace.Type::Member`. Python: `module.Class::method`.
  - JS/TS (no namespaces): module-path-anchored, e.g. `src/user.ts::User::save`, `src/util.ts::default`.
  - Files: **repo-relative** paths, always (even under Docker path mapping).
- **Contract version:** `contract_version` in result meta; bump on any vocabulary/field/qname change.

## 4. Python style

- Target modern Python; format/lint with **ruff**; type-check with **mypy**. CI runs both.
- **Type hints on all public functions**; prefer `Protocol` over ABCs for the one seam (`LanguageAdapter`).
- Prefer pure functions and explicit arguments over hidden global state; config flows in, isn't reached out to.
- Docstrings: one line saying *what* + *why* for non-obvious modules/functions; skip the obvious.
- Imports: stdlib, third-party, local — grouped; no wildcard imports.
- SQL lives in `store.py`; no raw SQL strings scattered across tools/indexer.
  Host SQLite must be **≥ 3.25** (window functions). Large `IN (...)` lists are chunked at
  `_IN_CHUNK` so hosts below 3.32's higher `SQLITE_MAX_VARIABLE_NUMBER` still work.
- **Node/edge column lists are derived from `contract.py`**, never re-typed in a consumer: build them
  with `", ".join(contract.NODE_FIELDS)` and rebuild result rows with
  `dict(zip(("id", *contract.NODE_FIELDS), row, strict=True))`. Binding on `indexer.py`, `resolver.py`
  and `tools/` too; `tests/test_contract_sole_source.py` fails a consumer that re-declares one (R3.2).

## 5. Adapter conventions

- Each adapter is a **long-lived subprocess** speaking the JSONL protocol: `--server` (stdin loop) and a
  `--file <path>` mode for spiking/debugging.
- **Each adapter ships a static analyser and CI runs it at its strictest clean setting** (R6.6) — the
  language's answer to the core's `mypy`. PHP: PHPStan `level: max` via `adapters/php/phpstan.neon`.
  Suppression (baseline, `@phpstan-ignore`, inline `@var`) is not how a finding is closed.
- **Announces itself first.** The first stdout line is the handshake —
  `{"name", "extensions", "capabilities", "contract_version"}` — before any result. The suffix list in it
  is what routes files to this adapter; nothing in the core knows them otherwise.
- Emits **bare** edges (targets as FQNs/names); never resolves cross-file — that's the core resolver.
- **stdout carries the protocol and nothing else.** Diagnostics go to stderr, which the core sends to
  `DEVNULL` or a file — never an undrained pipe (it deadlocks) and never merged into stdout.
- Self-contained: own manifest + runtime; documents its runtime **and its complete launch argv** in an
  adapter-local README. `CA_<LANG>_CMD` is that whole argv, `--server` included — the core appends
  nothing to it.
- Zero repo/framework names in adapter source (grep-gated).

## 6. MCP tool conventions

- Return **qualified names + `file:line`**, not source bodies — unless it's a read tool (`read_symbol`,
  `file_outline`), or an explicitly opt-in `include_source` on `find_callers` / `find_references`
  (037): default **off**, at most **one capped line** per hit (never a body), and never quoted from a
  file whose indexed hash has drifted — such hits carry `source_stale` instead.
- Every tool accepts `detail_level ∈ {minimal, standard}`, typed as a `Literal` so the protocol
  validates it and publishes the choice in the input schema. Default **`standard`**. `minimal` is a
  subset of `standard` (never a superset). After task 061, `db_path` provenance is only on
  `get_index_status` / `build_or_update_index` at `standard`; after task 071, **`index_root`** (the
  configured source tree) ships on every answer payload including status at every detail level —
  identity of the tree, not the database file. After task 077, status (and the busy build refusal
  that shares its vocabulary) also names **`last_ref`/`head_ref`** — the human revision the index
  was built on and HEAD is on now (`HEAD` when detached; `null` when non-git; omitted when the
  index predates 077 so `null` is not read as "not under git"); nav payloads stay
  on `index_root` only. For nav/search/read/outline/reach/explain, `minimal`
  and `standard` may share the same top-level keys.
  `get_index_status` also accepts `verbose` (task 058): `standard` plus a capped
  `parse_failure_paths` list (`PARSE_FAILURE_PATHS_LIMIT`, not `CA_MAX_RESULTS`) with optional
  `offset` — never on the cheap path; other tools stay `{minimal, standard}`. Verbose `collection`
  (082) also carries `skipped.untracked` beside the `collected − suffix − ignore == kept` identity
  (092). At `verbose` only, `skipped.ignore_sources` names which composed ignore source dropped each
  skip (095); `ignore` stays the int so 082 still closes; omit when empty (061). `not_indexed` on a payload with `indexed: true` means the subject maps to an untracked
  indexable file; `try_instead` is a real tool name and `try_instead_hint` carries the git-add
  prose (061 omit when empty). A subject matches an untracked file on its **stem** — a path-shaped
  qname's trailing ident is the file extension, so `Missing.aa` must not match `aa.aa` (092).
- **A batched answer keys on position, and states the envelope once (101).** A tool that takes a
  list of subjects (`search_symbol`'s `queries`) returns `subjects`: entry *i* answers subject *i*,
  in the caller's order, never deduped, never merged. Each entry carries only what varies —
  `query`, `results`, `truncated`, `reason`, `total_count`, and its own `try_instead` when it has
  one — while `indexed`, `index_root` and `subject_count` sit once on the envelope (061). The
  envelope carries **no** `reason` of its own: a batch-level verdict would colour subjects it knows
  nothing about. The fan-out bound is `max_subjects`, disclosed as `subjects_capped_to` plus
  `subjects_dropped` naming every subject refused, both omitted when nothing was dropped (066/061).
  A missing index answers the **call** — `indexed: false`, `reason: not_indexed`, no `subjects`
  list — for the same reason `schema_guard.payload` ships no empty `results`: N identical empty
  answers read as N proofs of absence. Where a subject has two spellings (`query` or `queries`),
  neither is schema-`required` and passing both raises (R5.3).
- **`try_instead` is two registers, and each stays in its own field (093).** Every value the core
  can emit is a **registered MCP tool name the reader can call**; the qualifier that says *how* to
  re-ask is prose in the sibling `try_instead_hint`, attached only alongside a route (061 omit when
  empty). Prose in the identifier slot is what made the field ambiguous — a reader could not tell
  a route from an instruction without trying one. The naming rule carries the split in the source:
  `TRY_INSTEAD_*` is a tool name, `TRY_INSTEAD_HINT_*` is prose, and neither holds the other's kind.
  `tests/test_try_instead_is_a_callable_tool_name.py` derives both sets from the module namespace
  and `main.TOOL_NAMES`, so a future value is gated without editing a hand-kept list (R1.1).
  Two further rules the route must satisfy, because "callable" is not the same as "useful":
  **a route must make progress** — a tool never routes to itself (`find_references` on a class
  routes to `search_symbol`, which enumerates the method qnames the hint asks for; routing back to
  itself loops for the mechanical reader the field exists for); and **a route must be able to
  answer** — where no registered tool can, the payload carries the **hint alone and no
  `try_instead`** (`include_graph`'s unlinked-inbound miss: the evidence is include text in
  `edges.target_raw` and `nodes_fts` covers name/qname/file_path/params only, so `search_symbol`
  would answer `reason=ok` with the symbols declared *in* the file and silently omit the includer).
  Naming a tool that cannot answer is worse than naming none — the reader spends a call and gets a
  confident wrong answer, which is the 075/076 failure this vocabulary exists to prevent.
  **Known boundary, not closed:** callability is checked against the full `main.TOOL_NAMES`, while
  `CA_TOOLS` may serve a subset — `nav_result` has no `Config`, so a restricted deployment can be
  offered a route it does not expose (pre-existing; also true of `file_outline`).
- One module per tool at `code_atlas/tools/<tool_name>.py`, named exactly as the MCP tool. Each
  exposes `NAME` and a `create(...)` that returns the registered function: **the returned function's
  signature is the MCP signature and its docstring is the tool description**, so configuration flows
  in through the closure rather than through global state. Logic two tools share lives in its own
  helper module beside them (`nav_result`, `staleness`, `reach_shared`, `collection`) — a tool module
  never imports another tool module.
- `get_index_status` is the cheap entry point (~100 tok) and suggests next tools — **only tools the
  server actually registered**, never one a client could not call.
- Tool availability gated by the `CA_TOOLS` allow-list; a name that is not a served tool is a loud
  `ConfigError`, checked in `main.py` (the only place that knows the tool names).
- A tool opens its own `GraphStore` **inside the call**. FastMCP runs tools on a worker thread, and a
  sqlite3 connection belongs to the thread that created it, so a store held by the server raises.

## 7. Git conventions

- **Branch naming:** `type/NNN-slug`, where `type ∈ {feat, fix, chore, docs}`, `NNN` is the task id, and
  `slug` is the task's kebab-case slug (`feat/014-search-read-outline`, `fix/011-resolver`). Branch per
  change; small, single-purpose commits. Never commit directly to `main`.
- **Imperative** subject line (`Add PHP trait resolution`, not `Added…`); body explains *why* when not obvious.
- **No `Co-Authored-By` / AI-attribution trailer.**
- **Pull requests:** open against `main` using `.github/pull_request_template.md`; fill every section and
  complete the pre-PR self-check before requesting review.

## 8. Docs & tracking

- Design decisions → the [build plan](PLAN.md).
- Task status kept in sync in **both** [`BACKLOG.md`](BACKLOG.md) and the task file's frontmatter.
- Do **not** use the Claude Code Memory feature for this project — decisions live in the repo.
