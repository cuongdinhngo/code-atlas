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
│   ├── cli.py  gitutil.py  ignore.py  index_lock.py  tokens.py   # cli.py: code-atlas-build (176)
│   ├── onboarding/                   # Phase-3 enrichment, deterministic — one module per concern
│   ├── hooks/                        # opt-in editor/checkout hooks (036, 053)
│   └── tools/                        # one module per MCP tool
├── onboarding_llm/                   # the LLM implementers, OUTSIDE the core by R4.1 (CI grep-gated)
├── scripts/                          # operator reports & benchmarks (never imported by the server)
├── docker/                           # test image, runtime image, compose
├── contrib/                          # offered, never installed: skill/ (generated Agent Skill,
│                                     #   200) claude-code/ codex/ opencode/ git/
├── adapters/
│   ├── php/                          # self-contained: composer.json, index.php, src/{Parser,Visitor}.php
│   ├── typescript/ sql/              # landed; python/ csharp/ deferred (PLAN §19)
├── tests/
│   ├── contract/                     # schema-conformance every adapter must pass
│   ├── fixtures/<lang>/…             # spec-driven fixtures
│   └── test_*.py
└── docs/                             # each doc's audience, content and boundary: §8.1 below
    ├── PLAN.md  TOOLS.md  ENGINEERING_RULES.md  CONVENTION.md  BACKLOG.md  AGENT_BRIEF.md
    ├── LESSONS.md  TOKEN_LEDGER.md  SKILL_GAP_CANDIDATES.md  FEEDBACK.md
    ├── design/  assets/  phase3-onboarding/  benchmarks/  runbooks/
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
  `<repo>/.code-atlas/graph.db`; ignore file `.codeatlasignore`; onboarding markdown +
  `manifest.json` + self-contained `index.html` viewer under `<repo>/docs/onboarding/`
  (committed); regenerable onboarding cache under `<repo>/.code-atlas/onboarding/`
  (gitignored with the rest of `.code-atlas/`). `manifest.json` is the one compact,
  versioned aggregate dataset renderers consume (task 112: counts, layer table, matrix,
  hubs, classes, directory tree, a capped path index) plus this run's `pages` record.
  The committed tree is owned by that manifest: regeneration removes only the pages it
  lists, so a hand-authored file there is safe.
- **Task files:** `docs/tasks/NNN_slug.md`, zero-padded 3-digit id, `kebab-case` slug (`014_search-read-outline.md`).

## 3. The contract vocabulary (fixed spelling — do not vary)

- **Node kinds:** `File Namespace Class Interface Trait Enum Function Method Property ClassConst Const Table Column`.
- **Edge kinds:** `CONTAINS EXTENDS IMPLEMENTS USES_TRAIT CALLS NEW IMPORTS INCLUDES REFERENCES ALIASES PROVIDES_VIEW_DATA WRITES`.
- **`INCLUDES`:** `include`/`require` — `source_qname` is the **including file's path**, never the
  enclosing namespace or class (task 129) — the target resolves relative to that file's directory,
  so both ends are paths. `target_raw` is the literal as written (`'../helpers.php'`) or `(dynamic)`
  at `DYNAMIC` for a non-literal expression.
- **`REFERENCES`:** a textual class mention (`Foo::class` — task 094). FQN-linked at `DYNAMIC`;
  not a `CALLS` and not a `NEW`. `self`/`static`/`parent` name the enclosing class-like (as
  `CALLS` does), never a literal `\self`. Leftover unlinked rows still feed
  `relationship_not_modelled`.
- **`WRITES`:** a routine assigns a column (v9, task 022). The **target kind** says whether the
  statement named its columns: a `Column` (`dbo.T::Col`) it did, the `Table` it did not — that is
  *unmeasured*, never *writes none*. `Column.extra`: `data_type`, `default`.
- **`PROVIDES_VIEW_DATA`:** handler method → synthetic view-scope key. `target_raw` is
  `viewdata:<key>` (not an FQN; not in `FQN_EDGE_KINDS`). Emitted only by `CA_INDIRECTION_RULES`
  `view_data` setter rules (task 062); query with `find_view_data`.
- **Confidence tiers:** `RESOLVED | HEURISTIC | DYNAMIC`.
- **Node fields:** `kind, name, qualified_name, file_path, line_start, line_end, modifiers, params, is_test, extra`.
- **`extra['type']` (contract v7):** declared type on `Property` / `ClassConst`, and declared **return
  type** on `Method` / `Function` (including closures). Same key; a pre-v7 index is rebuilt on bump
  (task 144).
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
- **Contract version:** `contract_version` in result meta; R3 governs when it bumps.
- **Onboarding `artifact.json` (145):** top-level `version` (`ARTIFACT_VERSION` in `artifact.py`). Not
  the adapter contract and not `DATASET_VERSION`. Bump when `OnboardingArtifact.as_dict` keys change.

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

This section is the mechanical rule; the reasoning behind each one is in its task and in
[`ENGINEERING_RULES.md`](ENGINEERING_RULES.md).

- **Answer shape.** Return **qualified names + `file:line`**, not source bodies — except the read
  tools (`read_symbol`, `file_outline`) and the opt-in `include_source` on
  `find_callers`/`find_references` (037): default **off**, at most **one capped line** per hit,
  never a body, and never quoted from a file whose indexed hash drifted (those hits carry
  `source_stale`).
- **`detail_level`.** Every tool takes `detail_level ∈ {minimal, standard}`, typed as a `Literal`
  so the protocol validates it and publishes the choice in the input schema. Default **`standard`**;
  `minimal` is always a **subset**, never a superset, and for nav/search/read/outline/reach/explain
  the two may share the same top-level keys. `get_index_status` alone also accepts `verbose` (058);
  every other tool stays `{minimal, standard}`.

**Provenance and honesty fields.** One name per fact; each is omitted where it would only restate
what the payload already says (061). An answer must state what it is *not* telling you.

| Field | On | Rule |
|---|---|---|
| `index_root` | **every** payload, every detail level | the configured source tree — identity of the tree, not the database file (071) |
| `db_path` | `get_index_status` / `build_or_update_index` at `standard` | nowhere else after 061 |
| `last_ref` / `head_ref` | status + the busy-build refusal sharing its vocabulary | the revision the index was built on and the one HEAD is on now. `HEAD` when detached, `null` when non-git, **omitted** pre-077 so `null` is not read as "not under git". Nav payloads stay on `index_root` alone (077) |
| `server_version` / `server_build` / `server_stale_process` | status at `standard`/`verbose`; `minimal` omits all three | the running package, a build id from git or package content (not the index schema), and whether the loaded code still matches the disk. `+dirty` on the id is the **worktree** axis, orthogonal to that process one. The verdict rides **unconditionally** — omitting it on the clean case made *checked-and-matching* identical to *never checked* (170); `server_repo_head` is divergence context and stays conditional. Signed claims add `server=`/`build=` (100/125) |
| `config_build` / `config_stale_process` | status at `standard`/`verbose`; `build_or_update_index` at `standard` | which **config** answered — a hash of the project file plus the `CA_*` it reads, no timestamps — and whether the disk still matches it. The verdict is stated, never omitted (170's rule). `index_config_build` names the config that built the index, only when it differs (061). **Not** on nav payloads: the code axis is already a standing cost there (175) |
| `parse_failure_paths` | status at `verbose` | capped by `PARSE_FAILURE_PATHS_LIMIT`, not `CA_MAX_RESULTS`; optional `offset`; never on the cheap path (058) |
| `skipped.*` breakdowns | `collection` | `collected − suffix − ignore == kept`; `untracked` sits **beside** it (092). Each breakdown leaves its parent int intact so 082 closes, and is omitted when empty (061): `ignore_sources` names each ignore-skip's composed source, verbose only (095); `suffix_top` names what `suffix` is made of by **extension** — top 10, count desc then suffix asc, `suffix_kinds` the true denominator, `(none)` for a suffix-less file. Extensions only: the core names no language; the reader joins `unconfigured_adapters` (174/R1.1) |
| `not_indexed` | any payload with `indexed: true` | the subject maps to an untracked indexable file. Match on the file **stem**: a path-shaped qname's trailing ident is its extension, so `Missing.aa` must not match `aa.aa` (092) |
| `resolved_qname` | nav answers | the stored qname actually queried, when a leading anchor made it differ from the typed subject; omitted on an exact hit (075/122) |
| `result_kinds` | a truncated `file_outline` page | symbol kind → count over the **whole** file, when the file spans more than one kind, so a capped map cannot read as complete (067/123) |
| `total_count` | `find_orphans` | the orphan population, not the page length (124) |
| `unproven_total` | `find_orphans` | the full population of the `unproven` rows, one name at both levels — those rows are omitted at `minimal` and capped to the page at `standard` (124) |
| `truncated` | paged answers | describes **the page alone**, so a pager terminates (057/124) |
| `walk_truncated` | `find_orphans` | the walk hit `CA_ORPHANS_MAX_NODES`, so the population is an over-estimate — unreached nodes look orphaned (124) |
| `walk_truncated` | `impact_modules` | the walk hit `CA_IMPACT_MAX_NODES`, so every per-module count is an **under**-estimate — a module reached only beyond the bound is missing from the table entirely, not merely undercounted (140) |
| `module_table_truncated` | `impact_modules` | 114's module table was itself capped at `CA_MAX_RESULTS`, so rows counted under `unassigned` include files whose module exists and was cut — that bucket is an **over**-count, distinct from the walk bound (140) |

- **`try_instead` is two registers, each in its own field (093).** The value is always a
  **registered MCP tool name the reader can call**; the *how to re-ask* qualifier is prose in the
  sibling `try_instead_hint`, attached only alongside a route (061 omit when empty). The source
  carries the split — `TRY_INSTEAD_*` is a tool name, `TRY_INSTEAD_HINT_*` is prose, neither holds
  the other's kind — and `tests/test_try_instead_is_a_callable_tool_name.py` derives both sets from
  the module namespace and `main.TOOL_NAMES` rather than a hand-kept list (R1.1). Callable is not
  sufficient. A route must also **make progress**: no tool routes to itself (`find_references` on a
  class routes to `search_symbol`, which enumerates the method qnames the hint asks for). And it
  must be **able to answer**: where no registered tool can, emit the **hint alone, no
  `try_instead`**, since naming a tool that cannot answer buys a confident wrong answer (075/076).
  Two live cases, both `include_graph`: its **unlinked-inbound** miss stays route-less because the
  evidence is include text in `edges.target_raw`, which `nodes_fts` does not index; its **language**
  miss had no route either until 188 linked `IMPORTS`, and now names `find_references` — emitted on
  positive evidence that the language emits the carrying kind, never on the index's silence (186/188).
  **Known boundary, not closed:** callability is checked against the full `main.TOOL_NAMES` while
  `CA_TOOLS` may serve a subset — `nav_result` has no `Config`, so a restricted deployment can be
  offered a route it does not expose (also true of `file_outline`).
- **A batched answer keys on position and states the envelope once (101).** A tool taking a list of
  subjects (`search_symbol`'s `queries`) returns `subjects`: entry *i* answers subject *i*, in the
  caller's order, never deduped, never merged. An entry carries only what varies — `query`,
  `results`, `truncated`, `reason`, `total_count`, its own `try_instead` — while `indexed`,
  `index_root` and `subject_count` sit once on the envelope (061). The envelope carries **no
  `reason`**: a batch-level verdict would colour subjects it knows nothing about. The fan-out bound
  is `max_subjects`, disclosed as `subjects_capped_to` plus `subjects_dropped` naming every refused
  subject, both omitted when nothing was dropped (066/061). A missing index answers the **call**
  (`indexed: false`, `reason: not_indexed`, no `subjects` list), like `schema_guard.payload`
  shipping no empty `results` — N identical empty answers read as N proofs of absence. Where a
  subject has two spellings (`query` or `queries`), neither is schema-`required` and passing both
  raises (R5.3).
- **Module layout.** One module per tool at `code_atlas/tools/<tool_name>.py`, named exactly as the
  MCP tool, exposing `NAME` and a `create(...)` returning the registered function: **its signature
  is the MCP signature and its docstring is the tool description**, so configuration flows in
  through the closure, not global state. Logic two tools share lives in its own helper module beside
  them (`nav_result`, `staleness`, `reach_shared`, `collection`); a tool module never imports
  another tool module.
- **Surface and runtime.** `get_index_status` is the cheap entry point (~100 tok) and suggests next
  tools — **only tools the server actually registered**. `CA_TOOLS` gates availability; an unserved
  name is a loud `ConfigError`, checked in `main.py` (the only place that knows the tool names). A
  tool opens its own `GraphStore` **inside the call**: FastMCP runs tools on a worker thread and a
  sqlite3 connection belongs to the thread that created it, so a server-held store raises.

## 7. Git conventions

- **Branch naming:** `type/NNN-slug`, where `type ∈ {feat, fix, chore, docs}`, `NNN` is the task id, and
  `slug` is the task's kebab-case slug (`feat/014-search-read-outline`, `fix/011-resolver`). Branch per
  change; small, single-purpose commits. Never commit directly to `main`.
- **Imperative** subject line (`Add PHP trait resolution`, not `Added…`); body explains *why* when not obvious.
- **No `Co-Authored-By` / AI-attribution trailer.**
- **Pull requests:** open against `main` using `.github/pull_request_template.md`; fill every section and
  complete the pre-PR self-check before requesting review.

## 8. Docs & tracking

### 8.1 What each standing document is — and is not

The **UPPER_SNAKE standing documents are a closed set.** One may be merged or deleted; a new one
needs an argument in the ticket that proposes it. The *Is NOT* column is the load-bearing one: a
document without a stated boundary absorbs whatever its author had in mind that day, and rows
describe what a file contains, not what its title suggests.

**Tier** is what a session pays (task 133). **1** = on `AGENTS.md`'s *read before non-trivial work*
list, charged to every session, under the 25,000-token cap; **2** = on its *consult when you need it*
list, reached by a pointer; **—** = neither, opened only by the reader in its *Reader* column. A new
document lands in a tier on purpose, here, or it lands in tier 1 by accident.

| Doc | Tier | Reader | Answers | Is **NOT** |
|---|---|---|---|---|
| [`README.md`](../README.md) | — | a stranger deciding in 60 s whether to install | what it does, one demo, how to install, the measured claims, where the rest is | not the tool reference (→ `TOOLS.md`); **not the design record** (→ `design/`); never the authority for a number |
| [`TOOLS.md`](TOOLS.md) | — | someone choosing which tool to call | the agent-facing surface: every tool, the batching verdicts, prompts, hooks, config | not the field contract (→ §6); not why (→ `design/`) |
| [`design/`](design/)`*.md` | — | anyone asking *why is an answer shaped like this* | one file per axis (payload · indexing · impact/claims); each section is a field incident | not a rule (→ `ENGINEERING_RULES.md`); not status (→ `BACKLOG.md`) |
| [`AGENTS.md`](../AGENTS.md) | 1 | an agent at session start | orientation: what this is, where things live, which docs bind, how the maintainer authorises finishing steps, how to run the gate and the suite | **not a rule origin** — every rule here is a summary with a destination; not a lifecycle rule book (→ `AGENT_BRIEF.md`) |
| `CLAUDE.md` | 1 | the Claude Code harness | one line: `@AGENTS.md` | not content |
| [`PLAN.md`](PLAN.md) | 2 | anyone asking *why is it shaped this way* | **§1 the two pillars (authoritative)**; the design and its reasoning; §19 the durable decision log — what was measured, what was refuted | not the vocabulary of record (→ `contract.py`, §3 above); not a schema listing (→ `store.py`); not task status (→ `BACKLOG.md`) |
| [`BACKLOG.md`](BACKLOG.md) | 1 | anyone asking *what is open and what landed* | the ticket tables by pillar and the shipped record by phase | not rationale (→ PLAN §19); not lessons (→ `LESSONS.md`); not cost (→ `TOKEN_LEDGER.md`); not a rule origin |
| [`TOKEN_LEDGER.md`](TOKEN_LEDGER.md) | 2 | anyone asking what a ticket cost | one spend row per ticket, required before its PR (R7.2) | not the per-phase breakdown (→ the task's working doc); not status; append-only, so no size ceiling |
| [`ENGINEERING_RULES.md`](ENGINEERING_RULES.md) | 1 | an agent about to write code | the binding *how we build* rules R1.1…, and the pre-PR self-check | not process (→ `AGENT_BRIEF.md`); not naming or style (→ this file); not evidence (→ `LESSONS.md`) |
| [`AGENT_BRIEF.md`](AGENT_BRIEF.md) | 1 | an agent running the lifecycle | the binding *how we run it* rules P1…, each earned by a cited incident. **A `/mango:promote` destination** | never restates a code rule (it says so itself); not orientation; not a harness-gap log (→ `SKILL_GAP_CANDIDATES.md`) |
| `CONVENTION.md` (this file) | 1 | an agent naming or placing something | repo layout, naming, the fixed contract **spelling** and per-kind semantics (§3), Python style, tool/payload conventions (§6), git, and this table | not the authoritative field set (→ `contract.py`); not design reasoning (→ `PLAN.md`) |
| [`LESSONS.md`](LESSONS.md) | 2 | an agent about to propose a rule | per-task claims with handles and `seen:` counts — the corpus rules are promoted from | not a rule (a claim is promoted, not applied); not a decision log |
| [`SKILL_GAP_CANDIDATES.md`](SKILL_GAP_CANDIDATES.md) | 2 | the mango maintainer | type-3 signals: a phase that could have run a check and did not | never a change to a mango skill |
| [`FEEDBACK.md`](FEEDBACK.md) | — | anyone auditing an outside claim | external review rounds 1–4, each repo-verified — **series closed** | not a decision (→ PLAN §19); not the field retros |
| [`phase3-onboarding/ROADMAP.md`](phase3-onboarding/ROADMAP.md) | — | anyone asking how Pillar 2 was decided | the delivered M10–M12 roadmap and the deterministic/LLM split | not current status (→ `BACKLOG.md`); its §7 table is a historical copy |
| [`phase3-onboarding/ONBOARDING_MOCKUP.md`](phase3-onboarding/ONBOARDING_MOCKUP.md) | — | a reviewer of the system map | the design note the map was reshaped from (2026-08-19), and which parts are deterministic vs prose | not shipped behaviour (→ README, PLAN §14) |
| [`runbooks/`](runbooks/)`*.md` | — | an operator reproducing a number | one protocol each, re-runnable, with the conditions the number holds under | never a summary — the caveat travels with the number |
| [`benchmarks/`](benchmarks/)`*.md` | — | a reader checking one measurement | the raw result of one question class, cited from its ticket | not a claim about the product — README/PLAN quote these, never the reverse |
| directory `README.md`s (`adapters/php/`, `onboarding_llm/`, `contrib/*/`, `phase3-onboarding/mockup/`) | — | someone working in that directory | how to run or launch what is in this directory | not repo-level anything |
| `.github/pull_request_template.md` | — | the author opening a PR | the sections and the self-check every PR fills | not the rule it checks (→ `ENGINEERING_RULES.md`, `AGENTS.md`) |

### 8.2 Tracking

- Design decisions → the [build plan](PLAN.md).
- Task status kept in sync in **both** [`BACKLOG.md`](BACKLOG.md) and the task file's frontmatter.
- Do **not** use the Claude Code Memory feature for this project — decisions live in the repo.
