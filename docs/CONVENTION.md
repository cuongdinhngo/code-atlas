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
- **Edge kinds:** `CONTAINS EXTENDS IMPLEMENTS USES_TRAIT CALLS NEW IMPORTS INCLUDES REFERENCES ALIASES`.
- **Confidence tiers:** `RESOLVED | HEURISTIC | DYNAMIC`.
- **Node fields:** `kind, name, qualified_name, file_path, line_start, line_end, modifiers, params, is_test, extra`.
- **Edge fields:** `kind, source_qname, target_qname?, target_raw, file_path, line, confidence_tier, args?`.
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
  validates it and publishes the choice in the input schema. Default **`standard`**; `minimal` is a
  strict subset — the tool's own payload with the provenance fields dropped.
  `get_index_status` also accepts `verbose` (task 058): `standard` plus a capped
  `parse_failure_paths` list (`PARSE_FAILURE_PATHS_LIMIT`, not `CA_MAX_RESULTS`) with optional
  `offset` — never on the cheap path; other tools stay `{minimal, standard}`.
- One module per tool at `code_atlas/tools/<tool_name>.py`, named exactly as the MCP tool. Each
  exposes `NAME` and a `create(...)` that returns the registered function: **the returned function's
  signature is the MCP signature and its docstring is the tool description**, so configuration flows
  in through the closure rather than through global state.
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
