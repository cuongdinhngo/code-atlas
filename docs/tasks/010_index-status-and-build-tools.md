---
id: 010
slug: index-status-and-build-tools
title: MCP server + status/build tools (M1)
phase: 1
milestone: M1
status: done
depends_on: [009]
---

## Goal
Expose the index over MCP; first two tools (§12).

## Scope / Deliverables
- `main.py`: FastMCP server (stdio) + entry point; tool allow-list via `CA_TOOLS`.
- `get_index_status` (stats, last_commit, staleness, `next_tool_suggestions`; ~100 tok).
- `build_or_update_index` (`full=false`) → counts, timing.
- Every tool takes `detail_level ∈ {minimal, standard}`.

## Acceptance criteria
- Server starts and lists tools via an MCP client (e.g. Claude Code `.mcp.json`).
- `get_index_status` on a built repo returns accurate stats; `build_or_update_index` triggers full build.

## References
Plan §12, §15 (M1).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Working doc — 010 MCP server + status/build tools

## Session status

- **Phase:** 1 — analysis (Gate 1)
- **Working doc mode:** `embed` (this file, below the separator) — same as tasks 002–009.
- **Branch:** not yet created.
- **Next action:** design (Gate 2).

---

## Phase 1 — Analysis

### Counted artifacts

```
SECTIONS: 4 found (Goal · Scope / Deliverables · Acceptance criteria · References) | 4 decomposed
ROWS: G=1 R=5 AC=3 REF=3
BASELINE: green — `pytest` 342 passed in 14.9 s; `ruff check .` clean; `mypy code_atlas` clean (11 files)
TRACK: backend — 0/N touched files under UI paths (this repo has no UI)
SURFACES: n/a (backend track)
SCOPE: M
TIER: full
STRUCTURE: native
CLARIFICATION: 6 raised | 6 self-resolved (cited) | 0 for human decision
RULE SECTIONS: R1.1 R1.2 R1.4 R4.1 R4.2 R4.3 R5.3 R6.1 R7.1 R7.5 R8.2 · CONVENTION §1 §2 §4 §6 §8 — each checked ✅ or N/A below
```

### Requirements matrix

The ticket's four bullets are the *summary*; the binding denominator is **PLAN §12 + CONVENTION §6**,
which the ticket's own References section points at. Rows R1–R5 come from the ticket, REF1–REF3 from
the referenced spec — the same rebuild-from-the-plan move task 009 made against §8.1.

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | Goal | "Expose the index over MCP; first two tools (§12)." | A FastMCP stdio server that an MCP client can connect to, registering exactly `get_index_status` and `build_or_update_index`. | `code_atlas/main.py:1` is a one-line stub; nothing serves MCP today. | ⬜ |
| R1 | Scope | "`main.py`: FastMCP server (stdio) + entry point" | `main.py` builds a `FastMCP` app and runs it over stdio; a callable entry point exists so an `.mcp.json` `command` can name it. | `pyproject.toml:11` already depends on `fastmcp>=2` (3.4.5 installed); `[project.scripts]` is absent. | ⬜ |
| R2 | Scope | "tool allow-list via `CA_TOOLS`" | Only tools named in `CA_TOOLS` are registered; unset/blank ⇒ every tool (PLAN §11). | `config.py:189` `_as_tools` already resolves the list and returns `None` for blank; **no consumer exists**. | ⬜ |
| R3 | Scope | "`get_index_status` (stats, last_commit, staleness, `next_tool_suggestions`; ~100 tok)" | Four payload parts, each derived from the store/meta/git — see the R3 per-part checklist below. | `store.get_meta` (`store.py:203`) holds `last_commit`/`built_at`/`contract_version`; **no row-count read exists**. | ⬜ |
| R4 | Scope | "`build_or_update_index` (`full=false`) → counts, timing" | Runs a build and returns the `BuildReport` counts plus elapsed wall time; accepts a `full` flag. | `indexer.full_build` (`indexer.py:51`) returns `BuildReport(files, parsed, failed, removed, nodes, edges)`. | ⬜ |
| R5 | Scope | "Every tool takes `detail_level ∈ {minimal, standard}`" | **Universal (N=2)** — per-tool checklist below; an invalid value fails loud (R5.3). | CONVENTION §6 repeats it as a tool convention. | ⬜ |
| AC1 | AC | "Server starts and lists tools via an MCP client (e.g. Claude Code `.mcp.json`)" | A real MCP client completes initialise + `list_tools` against the server and sees exactly the expected names. | Risk layer **runtime/3p** — nothing about this can fail at the logic layer. | ⬜ |
| AC2 | AC | "`get_index_status` on a built repo returns accurate stats" | Reported counts equal the database's own row counts after a real build. | Risk layer **integration**. | ⬜ |
| AC3 | AC | "`build_or_update_index` triggers full build" | Calling the tool produces the same index a direct `full_build` produces. | Risk layer **integration**. | ⬜ |
| REF1 | References →§12 | "`get_index_status` … **Call first (~100 tok).**" | The cheap entry point: its `minimal` payload is bounded — pinned below to a measurable budget. | PLAN §12 table. | ⬜ |
| REF2 | References →§12 / CONVENTION §6 | "suggests next tools" | `next_tool_suggestions` names tools that are **actually callable now** (registered ∩ allow-list), never a tool that does not exist yet. | CONVENTION §6 line 105. | ⬜ |
| REF3 | References →§15 | "**M1** Full build … `get_index_status`." | This task closes M1; 011/013/014 build on the server it stands up. | PLAN §15. | ⬜ |

### Universal inventories (per-item checklists — an aggregate count is not enough)

**R5 — `detail_level` on every tool. N = 2.**

| # | Tool | Accepts `detail_level` | `minimal` differs from `standard` | Invalid value fails loud |
|---|---|---|---|---|
| 1 | `get_index_status` | ⬜ | ⬜ | ⬜ |
| 2 | `build_or_update_index` | ⬜ | ⬜ | ⬜ |

**R2 — `CA_TOOLS` gates availability. N = 2** (each tool must be independently suppressible).

| # | Tool | Suppressed when absent from `CA_TOOLS` | Present when `CA_TOOLS` unset |
|---|---|---|---|
| 1 | `get_index_status` | ⬜ | ⬜ |
| 2 | `build_or_update_index` | ⬜ | ⬜ |

**R3 — `get_index_status` payload parts. N = 4.**

| # | Part | Source | Proven by |
|---|---|---|---|
| 1 | stats (files · parsed · failed · nodes · edges) | new bounded `store` read | ⬜ |
| 2 | `last_commit` | `meta.last_commit`, absent when the build could not name one (§8.1 step 4) | ⬜ |
| 3 | staleness | `meta.last_commit` vs `gitutil.head_commit(root)` | ⬜ |
| 4 | `next_tool_suggestions` | index state × registered tools | ⬜ |

### AC validation (re-derived values, falsifiability)

| AC value as written | Re-derived / pinned value | Falsifiable? | Disposition |
|---|---|---|---|
| "~100 tok" (REF1) | Not measurable as written. Pinned: the **`minimal` payload serialises to ≤ 400 characters**, the ~4 chars/token rule of thumb for ~100 tokens. Asserted as a test. | ✅ after pinning | Q2 below — self-resolved, pinned. |
| "lists tools via an MCP client" (AC1) | `list_tools()` over a client session returns exactly `{get_index_status, build_or_update_index}`. | ✅ | Automatable with a real client; the `.mcp.json` wording is an *example* of a client, not a manual-only requirement. |
| "accurate stats" (AC2) | `files == COUNT(files)`, `nodes == COUNT(nodes)`, `edges == COUNT(edges)`, `parsed == COUNT(files WHERE parsed_ok=1)` — compared against the database, not against the tool's own return. | ✅ | Pinned. |
| "triggers full build" (AC3) | The store after the tool call is row-identical to the store after a direct `full_build` on the same tree. | ✅ | Pinned. |
| "`full=false`" (R4) | See Q1 — `full` is accepted and echoed, both values run a full build until task 016 exists. | ✅ | Self-resolved. |

No AC is left unfalsifiable, so there are **no manual-check exclusions** to record.

### Clarifications (all self-resolved — cited)

1. **`full=false` with no incremental path yet.** `indexer.py:1` states `incremental_update` lands in
   task 016 (BACKLOG: 016 `todo`). Resolved: the parameter is accepted now so the signature is stable,
   both values run `full_build`, and the response reports the mode that actually ran. Inventing a
   fake incremental would be a lie in the payload; rejecting `full=false` would break the documented
   signature the ticket names.
2. **"~100 tok".** PLAN §12 gives no unit. Resolved by pinning to a character budget (above) — the
   analysis rule requires a measurable or a recorded exclusion, and a budget is cheap to assert.
3. **`next_tool_suggestions` when the downstream tools do not exist.** CONVENTION §6:105 says the
   status tool "suggests next tools"; suggesting `search_symbol` (task 014) today would be a dangling
   reference. Resolved: suggestions are filtered to the tools actually registered on the server, so
   the list grows by itself as 013/014 land and never names a tool a client cannot call.
4. **Where the server gets its config.** `config.load_config(root, env)` (`config.py:74`) is the only
   resolution path and PLAN §11 makes environment the top layer. Resolved: the server resolves once at
   start-up from the process CWD, which is what an `.mcp.json` `cwd` already controls.
5. **`detail_level` default.** PLAN §12 phrases `minimal` as the reduction of a normal answer.
   Resolved: default `standard`; `minimal` drops the optional parts.
6. **Entry point shape.** CONVENTION §1 says `main.py` is the "FastMCP server + entry point", but
   `pyproject.toml` declares no `[project.scripts]`, so an `.mcp.json` today could only say
   `python -m code_atlas.main`. Resolved: add a console script so AC1's example is real, and keep
   `python -m` working too.

### Cause / gap analysis (enhancement — current vs target)

| Goal | Current | Target | Gap |
|---|---|---|---|
| Serve MCP | `main.py:1` — one-line stub | FastMCP app over stdio + entry point | whole module |
| Report index stats | `store.py` has no aggregate read; every read is row-returning and `LIMIT`-bounded | one bounded counts read | new `store` method (SQL must stay in `store.py` — `tests/test_sql_confinement.py`) |
| Staleness | `gitutil.head_commit` (`gitutil.py`) and `meta.last_commit` both exist but nothing compares them | a compared verdict | new tool logic |
| Trigger a build | `indexer.full_build(config, store)` exists and is proven (task 009) | reachable over MCP | new tool wrapper |
| Honour `CA_TOOLS` | resolved by `config.py:189`, consumed by nobody | gates registration | new registration logic |

### Blast radius

- **Entry point:** `code_atlas/main.py` (new body) + `code_atlas/tools/` (new modules).
- **Store:** one new read method; SQL confined there by `tests/test_sql_confinement.py:49`.
- **Proof collateral — the two module-count guards break the moment a module is added:**
  - `tests/test_sql_confinement.py:32` — `assert len(core_modules()) == 11`
  - `tests/test_core_is_language_agnostic.py:42` — `assert len(core_modules()) == 11`
  Both are `rglob("*.py")` over `code_atlas/`, so each new tool module must be counted in.
- **Language-agnosticism:** every new core module is swept by
  `tests/test_core_is_language_agnostic.py:48` (no language name anywhere, comments included) and by
  the CI R1.1 grep-gate.
- **Docs:** README (tools table + how to run it), PLAN §12 (nothing to change if the payload matches),
  CONVENTION §6 if the payload shape needs pinning, BACKLOG + this file's frontmatter.
- **Repos touched:** `app` (the only entry in `.harness.json`).
- No schema change, no migration, no contract change, no adapter change.

### Rule-section coverage (derived from the change type)

Change types present: **new core modules**, **new store read**, **new dependency surface (FastMCP)**,
**new tests**, **docs**. No migration, no adapter change, no contract change, no UI.

| Rule | Applies because | Verdict |
|---|---|---|
| R1.1 zero language branches | new core modules | ✅ must hold — swept by two tests + CI |
| R1.2 one seam, YAGNI | tempting to add a tool registry/base class for 2 tools | ✅ no registry; plain functions |
| R1.4 SRP | tools present only; store persists only | ✅ tools call `store`/`indexer`, never SQL |
| R4.1 no LLM/network in core | an MCP server is a *server*, not a network client | ✅ stdio only, no outbound calls |
| R4.2 determinism | timing and `built_at` are wall-clock | ✅ they are *response* fields, never stored rows; nothing new is persisted |
| R4.3 single writer | the build tool triggers a fan-out | ✅ `full_build` already owns this (task 009) |
| R5.3 fail loud on config errors | `CA_TOOLS`, `detail_level`, missing adapter command | ✅ loud; a bad `detail_level` raises rather than defaulting |
| R6.1 no task done without tests | tool change → "a test over a fixture repo" | ✅ integration tests over a built fixture repo |
| R7.1 smallest useful thing | M1 is two tools, not nine | ✅ exactly two |
| R7.5 comments ≤ 3 lines | new source | ✅ |
| R8.2 minimal core deps | FastMCP | ✅ already declared; nothing new added |
| CONVENTION §1 layout | new files | ✅ `code_atlas/tools/<tool_name>.py` |
| CONVENTION §2 naming | tool module names | ✅ file name == MCP tool name |
| CONVENTION §4 style | typing, docstrings, no scattered SQL | ✅ |
| CONVENTION §6 tool conventions | this is the first tool | ✅ `detail_level`, cheap status, allow-list |
| CONVENTION §8 docs | status in two places | ✅ BACKLOG + frontmatter, in the delivering PR |
| R2.x standard-over-sample | *no adapter touched* | N/A |
| R3.x contract | *no vocabulary/field change* | N/A |
| DB conventions / migration | *no schema change* | N/A |
| Frontend/a11y | *backend track* | N/A |

No uncodified standard was applied at any gate: every judgement above cites an existing rule.

### Gate 1 self-audit

- Every section decomposed (4/4) ✅ · every AC value falsifiable or pinned ✅ · no bare `✅` on an
  unmeasurable AC ✅
- `BASELINE` captured on the untouched checkout ✅ · `j = 0` ✅ · inventories N=2/N=2/N=4 as per-item
  checklists ✅ · `RULE SECTIONS` emitted ✅ · `STRUCTURE`/`TRACK`/`TIER`/`SCOPE` declared ✅
- **Gate 1: passed** (gates pre-approved by the user for this task).

---

## Phase 2 — Design

### Approach

1. **`build_server(config) -> FastMCP` is the whole server.** One function builds an app with the
   allowed tools registered on it; `main()` resolves config from the CWD and runs it over stdio. Tests
   get the same object an MCP client gets, so nothing is proven against a test-only construction.
2. **Config flows in through a closure per tool** (CONVENTION §4). Each tool module exposes
   `NAME` and `create(...)`, returning the function FastMCP registers — its signature *is* the MCP
   signature, its docstring *is* the tool description. No base class, no registry, no plugin table
   (R1.2/R7.4): `build_server` names its two tools in two `if` statements.
3. **The store is opened inside each tool call, never held by the server** — forced by spike S2
   (below). `get_index_status` does not open one at all when the database file is absent: a *read*
   tool must not create a database as a side effect.
4. **`detail_level` is `Literal["minimal", "standard"]`**, so the protocol layer rejects a bad value
   with a client-visible error (spike S4) instead of the tool re-implementing validation. `minimal`
   returns exactly the four parts §12 lists; `standard` adds provenance (`built_at`, `head_commit`,
   `contract_version`, `schema_version`, `db_path`).
5. **`CA_TOOLS` gates registration, and an unknown name fails loud** (R5.3). `config.py` validates the
   list's *shape* but cannot know tool names; membership is checked in `main.py`, which does.
6. **`full` is accepted, echoed, and honoured as far as it can be** — both values run `full_build`
   until task 016 exists, and the response reports `mode: "full"` so a client is never told an
   incremental ran when one did not (clarification Q1).
7. **`next_tool_suggestions` is filtered to the tools actually registered**, computed once in
   `build_server` and closed over — so it can never name a tool the client cannot call, and it grows
   by itself as tasks 013/014 register more (clarification Q3).

### Rejected alternatives

- **Hold one `GraphStore` on the server and share it across calls.** Rejected: spike S2 proves it
  raises `sqlite3.ProgrammingError` on every call. Making it work would need
  `check_same_thread=False` plus a lock — trading a runtime-enforced single-writer guarantee (the
  property task 009 built on) for a hand-maintained one.
- **`run_in_thread=False` on both tools** so they execute on the event-loop thread and could share a
  store. Rejected: it puts a multi-minute build on the loop thread, so one build freezes the whole
  protocol session.
- **A `Tool` base class / registry mapping names to factories.** Rejected by R1.2 and R7.4 — two
  implementations and no second axis of change. Two `if`s read better and cost nothing to extend.
- **Validate `detail_level` by hand inside each tool.** Rejected: `Literal` publishes the choice in
  the input schema, so a client sees the allowed values before calling (spike S4).
- **Truncate `last_commit` to keep `minimal` small.** Rejected: the measured `minimal` payload is
  ~180 chars against a 400-char budget, so lossy truncation buys nothing.

### Assumptions (all resolved before this gate)

| # | Assumption | Tag | Resolution |
|---|---|---|---|
| S1 | FastMCP registers a plain function, and an in-memory `Client` can list and call it; a raised exception reaches the client as an error carrying the message | novel-untested → **verified** | Spike: `fastmcp 3.4.5`, `mcp.tool(fn)` registers; `Client(mcp)` lists `['boom','build','status']`; `call_tool` returns `.data`; a `ValueError` surfaces as `ToolError: Error calling tool 'boom': bad detail_level …` |
| S2 | A `GraphStore` created at server start-up is usable from a tool call | novel-untested → **FALSE** | Spike: every call ran on a worker thread (`same_as_main: False`) and every store touch raised `ProgrammingError: SQLite objects created in a thread can only be used in that same thread`. FastMCP's `mcp.tool(...)` defaults to `run_in_thread=True`. **This shaped approach item 3.** |
| S3 | A real MCP client can start this server as a subprocess over stdio and list its tools | novel-untested → **verified** | Spike: `StdioTransport(command=sys.executable, args=["srv.py"])` → `TOOLS: ['ping']`, `CALL: {'pong': True, …}`. Server logs go to stderr, so stdout stays protocol-only (CONVENTION §5). This is AC1's proof shape. |
| S4 | `Literal["minimal","standard"]` yields protocol-level validation with a loud error | novel-untested → **verified** | Spike: `ToolError: 1 validation error … Input should be 'minimal' or 'standard' [type=literal_error, input_value='bogus']` |
| S5 | `dict[str, object]` returns (including `None` values) serialise without a schema complaint | novel-untested → **verified** | Spike S4 returned `{'detail_level': 'minimal', 'maybe': None, 'n': 3}` intact |
| S6 | `full_build` works when called from a FastMCP worker thread (it creates its own threads and store there) | novel-untested | **Resolved by proving-test shape**: the stdio end-to-end test drives a real build through the tool and fails if it does not (per the design rule, an integration-shaped proof that fails if the assumption is false) |
| S7 | The installed FastMCP (3.4.5) satisfies the declared `fastmcp>=2` | verified → **inadequate** | The API above is what 3.x was tested against; `>=2` lets a fresh install resolve 2.x. Pin to `>=3,<4` (change-list item 5). |
| S8 | Async client code runs inside a plain sync pytest test | verified | `asyncio.run(...)` inside a sync test — avoids adding `pytest-asyncio` (R8.2) |

### Smallest change list

| # | Change | File / area | Ph2 covered by | k/N |
|---|---|---|---|---|
| 1 | `build_server(config)`, allow-list membership check, `main()` entry point, `__main__` guard | `code_atlas/main.py` | G1, R1, R2 | 0/3 |
| 2 | `NAME` + `create(config, registered)` → the status tool; payload parts 1–4; `minimal`/`standard` split | `code_atlas/tools/get_index_status.py` | R3, R5, REF1, REF2 | 0/4 |
| 3 | `NAME` + `create(config)` → the build tool; counts + timing; `full` echoed | `code_atlas/tools/build_or_update_index.py` | R4, R5 | 0/2 |
| 4 | `GraphStore.counts()` — one aggregate read (SQL stays here) | `code_atlas/store.py` | R3 part 1 | 0/1 |
| 5 | `[project.scripts] code-atlas` + pin `fastmcp>=3,<4` | `pyproject.toml` | R1 (Q6), S7 | 0/2 |
| 6 | **Proof collateral** — module count 11 → 13 | `tests/test_sql_confinement.py:32` | blast radius | 0/1 |
| 7 | **Proof collateral** — module count 11 → 13 | `tests/test_core_is_language_agnostic.py:42` | blast radius | 0/1 |
| 8 | New: stdio e2e, allow-list, detail_level, stats accuracy, staleness, suggestions, budget | `tests/test_mcp_server.py` | AC1, AC2, AC3, R2, R3, R5, REF1, REF2 | 0/8 |
| 9 | `counts()` test beside the store it reads | `tests/test_store.py` | R3 part 1 | 0/1 |
| 10 | Tools table status; a "Run it" section with a real `.mcp.json`; the `CA_ADAPTER_TIMEOUT` row missing from the config table since task 009 | `README.md` | R1, docs rule | 0/3 |
| 11 | §12: pin the two shipped payloads and the `full=false` disposition | `docs/PLAN.md` | R3, R4, Q1 | 0/2 |
| 12 | §6: `detail_level` default + `minimal` = the §12 parts; module-per-tool naming already stated | `docs/CONVENTION.md` | R5 | 0/1 |
| 13 | 010 → done, token row, suggested-order note | `docs/BACKLOG.md` + this file's frontmatter | REF3, CONVENTION §8 | 0/2 |
| 14 | The S2 finding as a durable lesson | `docs/LESSONS.md` | finalise step 8 | 0/1 |

**Test blast-radius trace (mechanical).** `rglob("*.py")` over `code_atlas/` is the real consumer of
the module count — `/usr/bin/grep -rn "core_modules()) ==" tests/` returns exactly the two sites in
items 6–7, both `== 11`, both breaking on the first new module. No fixture/factory helper keys on
`main.py` (it is a one-line stub today), and `tests/test_smoke.py` imports the package, not the
module. `mypy code_atlas` is in the sweep, so a signature mistake in the new modules surfaces at
execute, not in CI.

### Rule compliance

- **R1.1** — the new modules name no language; both language sweeps parametrise over `rglob`, so they
  pick the new files up automatically once the count is corrected.
- **R1.2 / R7.4** — no registry, no base class, no factory indirection beyond one closure per tool.
- **R1.4** — `counts()` is the only new SQL and it lives in `store.py`; the tools call `store` and
  `indexer` and never write SQL. `tests/test_sql_confinement.py` enforces this mechanically.
- **R4.1** — stdio only; nothing in the core dials out.
- **R4.2** — timing and `built_at` appear in *responses*; no new row is stored, so identical input
  still yields identical rows.
- **R4.3** — a per-call connection is created and used on the same thread; the build tool's fan-out
  keeps writing from its own calling thread, exactly as task 009 proved.
- **R5.3** — an unknown `CA_TOOLS` name and a bad `detail_level` both raise; neither falls back.
- **R7.5** — comments ≤ 3 lines.
- **R8.2** — no new dependency; the existing one is pinned tighter.

### Verification plan (per-AC, layer-matched)

| ID | Risk layer | Proof artifact | Layer-match |
|---|---|---|---|
| AC1 · G1 · R1 | runtime / 3p | e2e — a real `Client` over `StdioTransport` spawning `python -m code_atlas.main` in a fixture repo; asserts the tool names | ✅ |
| AC2 | integration | build a fixture repo, call the tool, compare each count against the database's own `SELECT COUNT(*)` | ✅ |
| AC3 | integration | call the tool, then compare the resulting rows against a direct `full_build` on the same tree | ✅ |
| R2 (N=2) | integration | in-memory client `list_tools()` under three allow-lists (each tool alone, unset) + a loud error on an unknown name | ✅ |
| R3 part 1 (stats) | integration | as AC2, plus a `counts()` unit beside the store | ✅ |
| R3 part 2 (`last_commit`) | integration | a repo with a commit vs a repo without git — present vs absent, never fabricated | ✅ |
| R3 part 3 (staleness) | integration | build, then commit again → `behind`; unbuilt → `unknown` | ✅ |
| R3 part 4 (suggestions) | integration | suggestions ⊆ registered names, under a restricted allow-list | ✅ |
| R5 (N=2) | integration | both tools accept `detail_level`; `minimal` ≠ `standard`; `"bogus"` raises through the client | ✅ |
| REF1 (~100 tok) | logic (serialisation size) | `len(json.dumps(minimal)) <= 400` on a real built repo | ✅ |
| REF2 | integration | covered by R3 part 4 | ✅ |
| REF3 | docs/bookkeeping | `tests/test_backlog_bookkeeping.py` (status in both places, token row) | ✅ |

No `❌` rows → **no coverage-gap exclusions to record.**

### Proving test

`tests/test_mcp_server.py::test_a_real_client_over_stdio_lists_the_tools_then_builds_and_reports_the_index`

A real MCP client spawns `python -m code_atlas.main` as a subprocess in a fixture repo wired to the
fake adapter, lists the tools, calls `build_or_update_index`, then calls `get_index_status` and
asserts the reported counts match what the build reported. It fails pre-change (`main.py` is a stub
that serves nothing) and passes post-change. It is also S6's integration-shaped proof: if `full_build`
could not run on a FastMCP worker thread, this test is what fails.

```
.venv/bin/pytest tests/test_mcp_server.py -q
```

### Negative controls planned (mutation testing — LESSONS 002/004)

| # | Mutation | Test that must go red |
|---|---|---|
| M1 | drop the `CA_TOOLS` filter in `build_server` | allow-list test |
| M2 | return the `standard` payload for `minimal` | budget + minimal/standard test |
| M3 | report `parsed` as the file total | stats-accuracy test |
| M4 | stop filtering suggestions by registered names | suggestions test |
| M5 | make the build tool return counts without building | AC3 test |
| M6 | open the store once in `build_server` instead of per call | the proving test (guards spike S2) |

### Rollback + porting

Single branch `feat/010-index-status-and-build-tools`; revert with
`git revert -m 1 <merge-sha>` — no schema change, no data migration, nothing to undo in an existing
index. Only repo `app` is touched, so there is no porting order.

### SCOPE

`SCOPE: M`, unchanged from analysis. Fourteen change-list items, but eight are tests/docs/bookkeeping
and the three new source modules are small. No tier crossing, no *outgrew-its-ticket* nudge.

### Gate 2 self-audit

- Every change-list item traces to a matrix row ✅ · `Ph2 covered by` filled ✅
- Every assumption tagged; S2 came back **false** and changed the design; S6 is resolved by an
  integration-shaped proving test; S7 became change-list item 5 ✅
- Proving test named and runnable ✅ · verification plan has **no ❌** ✅ · rollback recorded ✅
- **Gate 2: passed** (pre-approved).

---

## Phase 3 — Execute

**Branch:** `feat/010-index-status-and-build-tools` · **Commits:** `8acc2b4` `1099c10` `109ad1b`
`868d513`

### Result

`pytest` **375 passed** (342 baseline + 33 new) · `ruff check .` clean · `mypy code_atlas` clean
(13 source files).

### Proving test — fails before, passes after

Restoring `main.py` to its stub and running the proving test in isolation:

```
E   ImportError: cannot import name 'TOOL_NAMES' from 'code_atlas.main'
ERROR tests/test_mcp_server.py — 1 error in 0.34s
```

Post-change the same test passes, and the file was restored byte-for-byte (`sha256` re-checked
against a `cp` copy — never `git checkout --`, LESSONS 004).

### Negative controls — six run, six red

| # | Mutation | Result |
|---|---|---|
| M1 | drop the `CA_TOOLS` filter in `allowed_tools` | **2 failed** — `test_each_tool_can_be_served_alone` (both parameters) |
| M2 | `minimal` returns the `standard` payload | **1 failed** — the reduction test; the budget test still passed, since a `standard` payload with a short tmp path fits inside 400 chars. Recorded rather than papered over: the budget is not what catches this. |
| M3 | report `parsed` as the file total | **1 failed** — `test_a_failed_parse_is_counted_as_failed_not_parsed`. `test_the_counts_read_agrees_with_a_real_build` stayed green **correctly**: its fixture has no failed parse, so `parsed == files` there either way. |
| M4 | stop filtering suggestions by what is served | **1 failed** — the restricted-allow-list case |
| M5 | build tool reports counts without building | **1 failed** — the direct-build comparison |
| M6 | hold one store in `create()` instead of per call | **2 failed** — the thread test and the stats test, both with `sqlite3.ProgrammingError` |

Every mutation was applied to a `cp`-backed copy and reverted; the four source files' `sha256` sums
after the run are identical to the ones taken before it.

### Verification sweep — Axis 1 (file set)

| Check | Result |
|---|---|
| Diff ⊆ approved change list | ✅ — 13 paths touched, each one a change-list item (10 modified + 3 added) |
| No file outside the list | ✅ |
| No reformatting of untouched lines | ✅ — no formatter run over a shared file; `ruff format --check` reports the new test file already formatted |
| Every hunk maps to a matrix row | ✅ — see the change-list `Ph2 covered by` column |
| No stray references | ✅ — `mypy` clean, and the two module-count guards were updated to 13 rather than left to fail |

### Verification sweep — Axis 2 (design conformance)

| Gate-2 approach bullet | Verdict |
|---|---|
| 1 · `build_server(config)` is the whole server | implemented-as-approved |
| 2 · config through a closure per tool; no registry | implemented-as-approved |
| 3 · store opened per call; status opens none when the file is absent | implemented-as-approved |
| 4 · `detail_level` as `Literal` | implemented-as-approved |
| 5 · `CA_TOOLS` gates registration, unknown name fails loud | implemented-as-approved |
| 6 · `full` accepted and echoed, mode that ran is named | implemented-as-approved |
| 7 · suggestions filtered to registered tools | implemented-as-approved |

### Deviation records

**D1 — one extra README edit inside an approved file.** Change-list item 10 named three README
edits; a fourth was needed. The `.code-atlas.toml` example listed
`tools = ["get_index_status", "search_symbol", "read_symbol"]`, and the new loud membership check
(approach bullet 5) turns that documented example into a `ConfigError`. Shipping the check while
leaving the example standing would have documented a configuration that cannot start. The example
now names only served tools. Same file, same matrix row (R2), surfaced here rather than absorbed.

**D2 — the counts proof landed in two files, not one.** Item 9 placed a `counts()` test in
`test_store.py`; the integration check that the *reported* stats equal the database's own
`SELECT COUNT(*)` sits in `test_mcp_server.py` (item 8), because that is where the tool is driven.
Both files are in the approved list; the split is noted so review sees the coverage in one place.

No design invalidation, no stuck-detector trip: the design's one false assumption (S2) was caught at
Gate 2 by a spike, not during execution.

### Cost ledger

| Phase | Dispatch | Tokens |
|---|---|---|
| 1 — analysis | none (no Explore fan-out; the reading was done on the main model) | 0 |
| 2 — design | none (four runtime spikes against real FastMCP, run on the main model) | 0 |
| 3 — execute | none | 0 |
| 4 — review | `mango:challenger` (ticket-blind) | *pending* |
| 5 — finalise | none | 0 |

**Phase 3: complete.**

---

## Phase 4 — Review (ticket-blind challenger)

The `mango:reviewer` pass is skipped by standing user instruction; the ticket-blind `mango:challenger`
ran on the branch with **only** the raw ticket text (above the separator) plus the diff. It was told
not to open this file, and reported that it did not.

### Verdict

**8 of 8 rebuilt requirements met · 0 not met · 0 can't-tell.** No code finding. It independently
re-derived the requirements from the ticket and checked each against `path:line`, then ran the
toolchain itself: `pytest` 375 passed, `ruff` clean, `mypy` clean.

Notable in its own words — it verified the things a green suite does not prove on its own:

- the stats check compares against ground-truth `SELECT COUNT(*)` **"not against the same code path
  the tool itself used — a real independent check"**;
- the build tool comparison **"proves the tool isn't a no-op/stub"**;
- R1.4 confirmed by its own grep: `execute|SELECT|INSERT` is empty across `code_atlas/tools/`;
- R1.2 confirmed: no registry or base class, two literal `if`s;
- no AI-attribution trailer in any of the four commits;
- `CA_TOOLS` plumbing pre-dates the branch (checked with `git show 72cf94f:code_atlas/config.py`), so
  the branch consumes it rather than duplicating it — i.e. no scope creep.

### Its one open item, and its disposition

> `docs/BACKLOG.md` still lists task 010 as `status: todo` and has **no row yet** in the "Token usage"
> table … an open item against the project's own PR gate if a PR hasn't been opened yet.

Correct, and correctly scoped as process rather than ticket. Both are bookkeeping this task's own
rules place **in the delivering PR** (CLAUDE.md, and `tests/test_backlog_bookkeeping.py` enforces the
pair mechanically). Closed after the challenger returned, since the token row cannot be written until
the dispatch it records has finished:

- `docs/BACKLOG.md` 010 → `done`; this file's frontmatter → `done`; Token-usage row added.
- `tests/test_backlog_bookkeeping.py` — 51 passed, which is what makes the pair provable rather than
  promised.

No re-dispatch: the fix touched only the exempt bookkeeping files (working doc, BACKLOG, LESSONS),
which is the docs/bookkeeping carve-out, not a scope change.

### Clean-decision checklist

| Criterion | Result |
|---|---|
| Reviewer: no Critical | n/a — pass skipped by user instruction (as for 004–009) |
| Challenger: every item met | ✅ 8/8, no exclusion needed |
| No layer-match `❌` outstanding | ✅ the verification plan had none to begin with |
| `k = N` on every inventory | ✅ R5 2/2 · R2 2/2 · R3 4/4 |
| Proving test green | ✅ green post-change, `ImportError` pre-change |
| Baseline comparison | ✅ baseline was `green`; 342 → 375 passed, no pre-existing failure and no new one |

**Phase 4: clean.**

**Reviewed at `868d513`** — files covered: `code_atlas/main.py`, `code_atlas/store.py`,
`code_atlas/tools/get_index_status.py`, `code_atlas/tools/build_or_update_index.py`,
`pyproject.toml`, `tests/test_mcp_server.py`, `tests/test_store.py`,
`tests/test_sql_confinement.py`, `tests/test_core_is_language_agnostic.py`, `README.md`,
`docs/PLAN.md`, `docs/CONVENTION.md`. Staleness-exempt bookkeeping paths:
`docs/tasks/010_index-status-and-build-tools.md` (this working doc, `work_doc_mode: embed`),
`docs/BACKLOG.md`, `docs/LESSONS.md`.
