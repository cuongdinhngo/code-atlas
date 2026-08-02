---
id: 014
slug: search-read-outline
title: Search / read / outline + FTS (M3 — first daily release)
phase: 1
milestone: M3
status: done
depends_on: [010, 004]
---

## Goal
The daily-usable core: find, outline, and read symbols cheaply (§12). **Ship point.**

## Scope / Deliverables
- `search_symbol(query, kind?, namespace?, limit?)` — ranked `{qname, kind, file:line}` (FTS + name).
- `file_outline(path)` — symbols + line ranges, no body.
- `read_symbol(qname)` — source of just that class/method + docblock.
- Efficiency prompts: `explore_area`, `find_usages` (status → search/outline → read only what's needed).
- **CI:** this is the first tagged release, so it needs a release path — at minimum a build/install check (`pip install .` from a clean checkout) proving the package installs outside the dev venv, and a tag-triggered workflow if artifacts are published.

## Acceptance criteria
- Search returns ranked, relevant symbols on the fixture repo within `CA_MAX_RESULTS`.
- `read_symbol` returns only the target's source + docblock (not the whole file).
- Tagged as the first daily-usable release.

## References
Plan §12, §15 (M3).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 014 — Search / read / outline + FTS (working doc)

- **Ticket:** 014 · [docs/tasks/014_search-read-outline.md](014_search-read-outline.md) (raw above separator)
- **Type:** enhancement
- **Repo(s) / Porting:** `app` (`.`) only
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — `471 passed in 17.09s` (`.venv/bin/pytest -q` on `main` @ `46d766c`; run required `all` perms so PHP adapter subprocesses are not sandboxed-hung). baseline exclusions: none
- **work_doc_mode:** `embed` → this doc lives below the separator (harness `work_doc_mode: embed`)

---

## Phase 0 — Refine

`PREMISE: 7 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`

`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

`REFINE: 4 unresolved surfaced | 4 want-decision asked | 6 how-decision resolved+cited | 4 ASSUMED | skip: no`

**INPUT KIND:** ticket (single deliverable — not an epic).

**Settled wants / ASSUMED (awaiting Gate-1 ratification)** — user `okok` / `approve` on recommended W1–W4:

| # | Assumed choice | Why ASSUMED | Explicit confirm at gate | Reverses prior? |
|---|----------------|-------------|--------------------------|-----------------|
| A1 | Release bar = CI `pip install .` from clean checkout + git version tag; **no** package-registry publish workflow | Recommended; user ok | Gate 1 | no |
| A2 | Search “ranked/relevant” = fixture known hits within `CA_MAX_RESULTS`, ordered by FTS rank + stable tie-break; camelCase is HOW-5 | Recommended; user ok | Gate 1 | no |
| A3 | First daily-usable tag = bump package to **0.1.0** | Recommended; user ok | Gate 1 | no |
| A4 | `read_symbol` = file slice `line_start…line_end` **plus** contiguous comment lines immediately above `line_start`; **no** contract/adapter `doc` field | Recommended; user approve | Gate 1 | no |

**Resolved HOW (+ citation):**

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| 1 | Tool layout / registration | One module per tool under `code_atlas/tools/`; extend `main.TOOL_NAMES` + `CA_TOOLS` | CONVENTION §2; `main.py`; Plan §12; 013 |
| 2 | `detail_level` | Every tool takes `detail_level ∈ {minimal, standard}` | Plan §12:331 |
| 3 | Store / SQL ownership | Per-call `GraphStore`; FTS via `search_nodes` (extend helpers as needed) | Plan §12:351; R1.4; lesson 010 |
| 4 | Efficiency prompts | MCP prompts `explore_area` / `find_usages` (status→search/outline→read) | Plan §12:347; ticket Scope |
| 5 | camelCase FTS | **In scope** — tokenizer/search-form change + `schema_version` bump | 004 Q8 / decision log |
| 6 | `namespace?` filter | Prefix match on `qualified_name` (segment-aware), not substring | Plan §12; CONVENTION qname; exposure-checker |

**Constraints from scan:**
- Tools today: status, build, callers, refs, impls — no search/outline/read; no MCP prompts.
- `store.search_nodes` exists (`ORDER BY nodes_fts.rank, …`); no namespace filter helper yet.
- Contract has `line_start`/`line_end`, **no** `doc` field (`contract.py:59-70`).
- `SCHEMA_VERSION = "1"`; camelCase deferred test pins current unicode61 behaviour (`test_store.py:329`).
- `pyproject.toml` version `0.0.1`; only `ci.yml` (editable install) — no release/tag workflow.

**Exposure-checker** ([challenger](91fa727d-f259-4e91-b28c-8709423e2a31)): `UNEXPOSED: 2` → filed as A4 (WANT) + HOW-6 above.

---

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope / Deliverables, Acceptance criteria, References) | 4 decomposed | ROWS: C=0 R=5 G=1 AC=10`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | daily-usable core: find, outline, read cheaply (§12). **Ship point.** | Three MCP tools + prompts + release path so M3 is usable daily | Plan §12/§15; tools gap | Approach + change-list | | ❌ |
| R1 | Scope | `search_symbol(query, kind?, namespace?, limit?)` — ranked `{qname, kind, file:line}` (FTS + name) | Tool + store FTS/name search; namespace prefix (HOW-6); cap limit/`CA_MAX_RESULTS`; A2 ranking | `search_nodes` exists; no tool | change-list | | ❌ |
| R2 | Scope | `file_outline(path)` — symbols + line ranges, no body | Tool lists nodes in file with `line_start`/`line_end`; no source bodies | `nodes_by_file` exists | change-list | | ❌ |
| R3 | Scope | `read_symbol(qname)` — source of just that class/method + docblock | Tool returns A4 slice (span + comments above); not whole file | no tool; no `doc` field | change-list | | ❌ |
| R4 | Scope | Efficiency prompts: `explore_area`, `find_usages` | Two FastMCP prompts with status→search/outline→read recipe | no prompts registered | change-list | | ❌ |
| R5 | Scope | CI release path: `pip install .` check; tag workflow if publishing | Per A1: install-check job + version tag; **no** registry publish | `ci.yml` editable-only | change-list | | ❌ |
| AC1 | AC | Search returns ranked, relevant symbols on the fixture repo within `CA_MAX_RESULTS` | Pinned by A2 → AC-A2a/AC-A2b | fixture PHP + FTS | proving test | | ❌ |
| AC2 | AC | `read_symbol` returns only the target's source + docblock (not the whole file) | Pinned by A4 → AC-A4a/AC-A4b | | proving test | | ❌ |
| AC3 | AC | Tagged as the first daily-usable release | Pinned by A1+A3 → AC-A1*/AC-A3 | `version = "0.0.1"` | version bump + tag notes | | ❌ |
| AC-A1a | refine A1 | CI proves `pip install .` from clean checkout | Workflow/job installs non-editable and imports/`code-atlas --help` or equivalent | | change-list | | ❌ |
| AC-A1b | refine A1 | Git version tag marks the ship | Package version matches tag; release notes / tag process documented or workflow on `v*` (no publish) | | change-list | | ❌ |
| AC-A1c | refine A1 | No package-registry publish in this ticket | No PyPI/GH-release-asset publish job | | change-list / absense | | ❌ |
| AC-A2a | refine A2 | Fixture known hits appear within `CA_MAX_RESULTS` | Named expected qnames from PHP fixtures after index | | proving test | | ❌ |
| AC-A2b | refine A2 | Results ordered by FTS rank + stable tie-break | Order matches `nodes_fts.rank, qualified_name, file_path, id` (or successor after camelCase) | `store.py:90` | proving test | | ❌ |
| AC-A3 | refine A3 | Package version **0.1.0** for first daily-usable tag | `pyproject.toml` / dist metadata = `0.1.0` | `pyproject.toml:7` | change-list | | ❌ |
| AC-A4a | refine A4 | Return only target span, not whole file | Response body length / content equals lines in `[line_start, line_end]` plus optional upward comments — never full file | | proving test | | ❌ |
| AC-A4b | refine A4 | Include contiguous comment lines above `line_start` | Docblock-before-decl included when present; no contract bump | | proving test | | ❌ |
| HOW-5 | refine / 004 Q8 | camelCase FTS splitting | `findByEmail` matches `email` / `find`; `schema_version` bump; update tokenizer test | deferred test | change-list | | ❌ |

`PREMISE:` / `RECALL:` carried from refine.

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | Gate-1 if needed |
|-------|---------------|------------------------|--------|--------------|------------------|
| AC1 | ranked, relevant | Vague → pin A2 (fixture hits + FTS order) | Y under A2 | measurable after A2 | ratify A2 |
| AC2 | source + docblock only | No `doc` field → pin A4 (span + comments above) | Y under A4 | measurable after A4 | ratify A4 |
| AC3 | tagged first daily release | Vague → pin A1+A3 (install CI + 0.1.0 tag; no publish) | Y under A1/A3 | measurable after A1/A3 | ratify A1, A3 |
| AC-A* | ASSUMED clauses | as above | Y if ratified | measurable | Gate 1 |

**Coverage-gap exclusions:** none — all ACs pinned to falsifiable forms under ASSUMED A1–A4.

**Uncodified-standard nudge:** schema/`schema_version` change (HOW-5) has **no DB-conventions section** in the rulebook (same gap 004 surfaced). Detect-and-surface only — do not silent-gate; optional `/mango:codify` later. Until then, follow PLAN §10 + R3.2/R4.2/R5.3 as today.

## Inventory

- **N = 3 tools** (search / outline / read) + **2 prompts** + release/FTS bookkeeping.

| # | Item | Ph3/4 proven by | Status |
|---|------|-----------------|--------|
| T1 | `search_symbol` | | ❌ |
| T2 | `file_outline` | | ❌ |
| T3 | `read_symbol` | | ❌ |
| P1 | `explore_area` prompt | | ❌ |
| P2 | `find_usages` prompt | | ❌ |
| Rel | install-check CI + `0.1.0` | | ❌ |
| FTS | camelCase + `schema_version` bump | | ❌ |

`SURFACES:` N/A — `TRACK: backend`.

## Clarifications

`CLARIFICATION: 4 raised | 6 how self-resolved (cited in Phase 0) | 4 for human (ASSUMED A1–A4 at Gate 1)`

`j = 4` at Gate 1 as ASSUMED confirms (not open design questions beyond ratification).

## Cause / gap analysis

| Slice | Current | Target | Evidence |
|-------|---------|--------|----------|
| Search / outline / read tools | absent | three tools + registration | `main.py:25-31` — five tools, no search/outline/read |
| FTS helper | `search_nodes(query, kind?, limit)` | + namespace prefix; camelCase (HOW-5) | `store.py:291-298`; tokenizer test `test_store.py:329` |
| Outline data | `nodes_by_file` | tool shaping, no bodies | `store.py:253` |
| Read body | nowhere | file slice + comment walk (A4) | contract lacks `doc` |
| Prompts | none | two MCP prompts | Plan §12:347; no `server.prompt` |
| Release | editable `pip install -e` in CI; version `0.0.1` | non-editable install check + `0.1.0` | `ci.yml:31-34`; `pyproject.toml:7` |

## Blast radius

- **Entry:** `code_atlas/tools/{search_symbol,file_outline,read_symbol}.py`, prompts registration, `main.py` `TOOL_NAMES`, `store.py` (search/namespace/FTS), `SCHEMA_VERSION`, tests, `ci.yml` / `pyproject.toml`, docs (PLAN/BACKLOG/README).
- **Repos:** `app` only.
- **db-map:** N/A.
- **Adapter:** **not** required under A4 (no `doc` field).

`TRACK: backend — 0/N UI paths`

## Rule-compliance section coverage

`RULE SECTIONS: §1 (R1.1 ✅ · R1.2 ✅ · R1.3 ✅ · R1.4 ✅ tools present / store queries · R1.5–R1.6 N/A no adapter) · §2 N/A (no adapter) · §3 (R3.1 ✅ no contract bump under A4 · R3.2 ✅ store/tools import contract · R3.3–R3.4 N/A) · §4 (R4.1 ✅ · R4.2 ✅ FTS/schema deterministic · R4.3 ✅ per-call store) · §5 (R5.3 ✅ schema mismatch loud; missing DB → empty/indexed:false) · §6 (R6.1 ✅ tool+store tests · R6.2 ✅ fixture-driven) · §7 (R7.1 ✅ this *is* the ship · R7.2 ✅ PLAN/BACKLOG · R7.3–R7.5 ✅) · §8 N/A (stdlib sqlite; FastMCP already) · DB-conventions section ❌ ABSENT — uncodified-standard nudge above (not silent-gated)`

## Scope / Tier

- **SCOPE:** M — three tools + two prompts + FTS schema bump + release/install CI + version bump (one milestone; not a multi-deliverable epic).
- **TIER:** full — inventory N>1; not lite-eligible.

---

## Decision log

| When | Decision | Rationale |
|------|----------|-----------|
| Phase 0 | W1–W4 recommended → ASSUMED | user `okok` / `approve` |
| Phase 0 | HOW-5 camelCase in scope | 004 Q8 deferral |
| Phase 0 | HOW-6 namespace = qname prefix | exposure-checker + CONVENTION |
| Gate 1 | Ratify A1–A4 + HOW-5/HOW-6; clear Gate 1 | Standing approve: “best option, pass all gates” |
| Gate 2 | Approve approach + change-list (trigram FTS) | Standing approve; spike verified trigram |

---

## Phase 2 — Design

### Approach

Ship M3 as three MCP tools (`search_symbol`, `file_outline`, `read_symbol`) one-module-each under `code_atlas/tools/`, registered like 013; two FastMCP prompts (`explore_area`, `find_usages`) with the status→search/outline→read recipe; bump FTS to **`tokenize='trigram'`** and **`schema_version="2"`** so camelCase substrings match (004 Q8 / HOW-5 — spike-confirmed); extend `search_nodes` with optional **namespace prefix** (exact or `ns` + `\` / `.` / `::`); `read_symbol` slices `line_start…line_end` and walks contiguous comment lines upward (A4); CI gains a **non-editable** `pip install .` check; package version → **0.1.0** (tag marks the ship at release; no registry publish).

### Rejected alternatives

| Alternative | Why rejected |
|-------------|--------------|
| Aux camel-split FTS column | Works, but heavier than `tokenize='trigram'` which 004’s “change tokenize=” language pointed at; spike shows trigram satisfies `email`⊂`findByEmail` |
| Contract `doc` field + adapter emit | Violates A4; `contract_version` bump out of ship-minimal |
| PyPI publish on tag | Violates A1 |
| New tool registry / base class | R1.2 |

### Assumptions

| Assumption | Tag | Resolution |
|------------|-----|------------|
| FTS5 `tokenize='trigram'` makes `email` match `findByEmail` with our `fts_term` quoting | novel-untested → **verified** | analysis spike: `"email"*` → findByEmail + find_by_email |
| FastMCP `.prompt` registers usable MCP prompts | novel-untested → **verified** | `FastMCP.prompt` exists (2.14.7); proving test lists prompts |
| Per-call GraphStore + fixture `full_build` pattern | verified | 010 / 013 |
| Existing DBs refuse open on schema 2 (delete+rebuild) | verified | `SchemaVersionError` path from 004 |

### Smallest change-list

| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|--------|-----------|--------------|----------------|-----|
| 1 | `SCHEMA_VERSION="2"`; `nodes_fts … tokenize='trigram'`; `search_nodes(…, namespace=?)` prefix filter | `code_atlas/store.py` | all DBs must rebuild; tokenizer + search tests; PLAN §10 | R1, HOW-5, AC-A2*, HOW-6 | 1 |
| 2 | `search_symbol` tool | `code_atlas/tools/search_symbol.py` | MCP TOOL_NAMES / suggestions | R1, AC1, AC-A2*, T1 | 1/3 |
| 3 | `file_outline` tool | `code_atlas/tools/file_outline.py` | MCP | R2, T2 | 1/3 |
| 4 | `read_symbol` tool (+ comment walk) | `code_atlas/tools/read_symbol.py` | MCP; needs readable source under `config.root` | R3, AC2, AC-A4*, T3 | 1/3 |
| 5 | Prompts `explore_area` / `find_usages` | `code_atlas/tools/prompts.py` (+ register in `main`) | MCP list_prompts | R4, P1–P2 | 2/2 |
| 6 | Register tools (+ prompts) in `TOOL_NAMES` / `build_server` | `code_atlas/main.py` | `test_mcp_server` TOOL_NAMES equality | G1, T1–T3 | 1 |
| 7 | Proving + store tokenizer + MCP collateral tests | `tests/test_search_read_outline.py` (new); `tests/test_store.py`; `tests/test_mcp_server.py` | schema foreign-version fixture (`"2"`→other) | AC*, HOW-5 | 1 |
| 8 | CI non-editable `pip install .` check | `.github/workflows/ci.yml` | CI minutes only | R5, AC-A1a, AC-A1c | 1 |
| 9 | Version `0.1.0` | `pyproject.toml` | packaging metadata | AC-A3, AC-A1b | 1 |
| 10 | Docs: PLAN §10 trigram + schema 2; BACKLOG/frontmatter; README knobs if needed | `docs/PLAN.md`, `docs/BACKLOG.md`, task frontmatter, `README.md` | readers | R7.2, G1 | 1 |

**Test blast-radius:** `test_mcp_server.py:157` TOOL_NAMES tuple; `test_store.py` tokenizer + foreign schema `"2"`; any schema-object introspection unchanged (still 14 objects). Guardrail count tests if they hardcode tool counts.

### Rule compliance

- R1.1/R1.2/R1.4 — no language branches; no new seam; SQL in store; tools present only.
- R3.1 — **no** contract bump (A4).
- R4.2/R4.3 — deterministic FTS order; per-call store.
- R5.3 — schema mismatch fails loud; missing DB → empty/`indexed:false`.
- R6.1/R6.2 — fixture-driven proving tests.
- R7.1 — this *is* the ship point.

### Verification plan

| AC | risk layer | proof artifact | layer-match? |
|----|------------|----------------|--------------|
| AC1 / AC-A2a/b | integration (index + search tool) | integration over PHP fixtures | ✅ |
| AC2 / AC-A4a/b | integration (file on disk + read tool) | integration with fixture source + planted docblock | ✅ |
| AC3 / AC-A3 | logic (metadata) | assert `pyproject` version + importlib metadata after install job shape | ✅ |
| AC-A1a | runtime/CI | workflow step `pip install .` (not `-e`) | ✅ |
| AC-A1c | logic | no publish job in workflow | ✅ |
| HOW-5 | integration (SQLite) | store test: `email` hits `findByEmail` | ✅ |
| R4 prompts | runtime/3p (FastMCP) | list_prompts contains both names | ✅ |

### Proving test

Fails pre-change (tool missing); passes post-change:

```text
.venv/bin/pytest -q tests/test_search_read_outline.py::test_search_symbol_returns_ranked_fixture_hits -q
```

Full module also covers outline, read(+docblock), camelCase FTS, namespace prefix, prompts.

### Rollback + porting

- Revert branch; delete `.code-atlas/graph.db` (schema 2 refuses old files).
- Porting: `app` only.

### SCOPE confirm

**SCOPE: M** — unchanged (ship milestone, not an epic split).

---

## Phase 3 — Execute

**Branch:** `feat/014-search-read-outline`

**Implemented (Axis 2):**

| Approach bullet | Status |
|-----------------|--------|
| Three tools under `code_atlas/tools/` + `main` registration | implemented-as-approved |
| Trigram FTS + `schema_version=2` + namespace prefix on `search_nodes` | implemented-as-approved |
| `read_symbol` span + contiguous comments above (no contract bump) | implemented-as-approved |
| Prompts `explore_area` / `find_usages` via FastMCP | implemented-as-approved |
| CI non-editable install check + version `0.1.0` | implemented-as-approved |
| Docs PLAN §10 / BACKLOG in-progress | implemented-as-approved |

**Deviations:**
- **D1 — CI install proof uses importlib, not `code-atlas --help`.** FastMCP treats `--help` as starting stdio transport (hangs CI). Proof is: non-editable `pip install .`, `version==0.1.0`, `search_symbol` in `TOOL_NAMES`, console_scripts entry `code-atlas`. Same AC-A1a intent.

**Verification (paste):**
```
.venv/bin/pytest -q tests/test_search_read_outline.py::test_search_symbol_returns_ranked_fixture_hits
→ 1 passed
.venv/bin/pytest -q --tb=line
→ 498 passed in 17.83s
ruff + mypy → clean
```

**Axis 1:** diff ⊆ change-list (+ guardrail count 17→21 proof collateral, same as 013 pattern).

---

## Phase 4 — Review

**Reviewed at** `43753657c829c1efeb2f91a8c36ed73e3fac5573`

**Working-doc path:** `docs/tasks/014_search-read-outline.md`

**Reviewed files:** `code_atlas/main.py`, `code_atlas/store.py`, `code_atlas/tools/{search_symbol,file_outline,read_symbol,prompts}.py`, `tests/test_search_read_outline.py`, `tests/test_mcp_server.py`, `tests/test_store.py`, `tests/test_core_is_language_agnostic.py`, `tests/test_sql_confinement.py`, `.github/workflows/ci.yml`, `pyproject.toml`, `docs/PLAN.md`, `docs/BACKLOG.md`, `README.md`, `docs/tasks/014_search-read-outline.md`

| Critic | Result |
|--------|--------|
| mango:reviewer ([Reviewer](924a83ea-6a4c-42df-8b33-87b169ade718)) | Round 1 **CHANGES REQUESTED** — README Planned table; BACKLOG token row; optional LIKE `_` escape. Round 2 verify-only: all three landed; **499 passed** |
| mango:challenger ([Challenger](9893455f-6a10-4886-92b9-95e0157254bf)) | **6 met · 1 not met · 1 can't tell** — “not met” = no git tag yet (deferred to finalise/release per A1); 5b tag workflow N/A (no publish) |

**Scope reconcile:** file axis ✅ · behaviour axis ✅ (D1 documented) · inventory T1–T3 + P1–P2 ✅

**Layer-match:** AC1/AC2 integration over fixtures ✅

**Proving (re-check):** `test_search_symbol_returns_ranked_fixture_hits` PASS. Baseline 471 → 499.

**Verdict:** clean after round-2 doc/LIKE fixes — Gate 4 does not stop.

---

## Cost ledger

| Phase | Dispatch | Round | Tokens | Notes |
|-------|----------|-------|--------|-------|
| refine | challenger (exposure-checker) | 1 | unmeasured (blocking retrieval) | [91fa727d](91fa727d-f259-4e91-b28c-8709423e2a31) |
| review | reviewer | 1 | unmeasured (blocking retrieval) | [924a83ea](924a83ea-6a4c-42df-8b33-87b169ade718) |
| review | challenger | 1 | unmeasured (blocking retrieval) | [9893455f](9893455f-6a10-4886-92b9-95e0157254bf) |

---

## Session status

- **Phase:** 5 finalise — outward actions in flight
- **PR:** (opening)
- **Reviewed at:** `43753657c829c1efeb2f91a8c36ed73e3fac5573`
- **Gate:** final — approved push + PR + bookkeeping; tag deferred post-merge
- **Blocked by:** none
- **Revert path:** close/delete PR branch `feat/014-search-read-outline`; `git revert` merge on main if needed
