---
id: 004
slug: sqlite-store
title: SQLite store & schema
phase: 1
milestone: Core
status: done
depends_on: [001, 002]
---

## Goal
Persist and query the graph (§10). Single-writer, WAL, indexed.

## Scope / Deliverables
- `store.py` `GraphStore`: create schema (`files`, `nodes`, `edges`, `nodes_fts` fts5, `meta`), WAL mode.
- Upsert file + replace-per-file nodes/edges; meta get/set (`schema_version`, `contract_version`, `last_commit`, `built_at`).
- Query helpers used by tools (by name/kind/file, edges by source/target).
- Only component that touches SQLite (SRP): adapters never import it.

## Acceptance criteria
- Schema matches §10; re-indexing a file replaces its rows idempotently.
- FTS search returns expected rows; identical input → identical rows (determinism test).

## References
Plan §10, §2 (SRP boundary).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 004 — SQLite store & schema (working doc)

- **Ticket:** 004 · [`docs/tasks/004_sqlite-store.md`](004_sqlite-store.md) (local-file ticket)
- **Type:** enhancement (new core capability; no bug to root-cause)
- **Repo(s) / Porting:** `app` (`.`) only — single-repo project, no porting
- **work_doc_mode:** `embed` (`.harness.json:13`) — explicit, so the working doc is appended below the
  separator as in tasks 001–003, not written to a `.work.md` sibling
- **SCOPE:** M
- **STRUCTURE:** native (all four ticket headers map to `config.ticket_header_schema`)
- **TRACK:** backend — `0/N` touched files under UI paths (no UI exists; `config.track = "backend"`)
- **TIER:** full (SCOPE=M, multiple universal requirements with N > 1: schema objects N=14, meta keys N=4,
  query helpers N=6, core modules N=11)
- **BASELINE:** **green** — `pytest -q` → **86 passed**; `ruff check .` → clean; `mypy` → no issues in 11
  source files (untouched `main` @ `88676c4`, worktree clean)
  <!-- baseline exclusions: none. `ruff format --check .` reports 2 files unformatted
  (docs/PLAN.md code block, tests/test_config.py) but the formatter is NOT in CI (ci.yml:29-38 runs
  `ruff check` only), so it is not a declared lint — recorded as an uncodified-standard item below. -->

---

## Phase 0 — Refine

`REFINE: not run for this ticket | skip: n/a` — the ticket is a pre-written scaffold stub with native
sections; unresolved product-decisions are surfaced below as Gate-0/1 clarifications instead.

---

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope / Deliverables, Acceptance criteria, References) | 4 decomposed | ROWS: C=8 R=4 G=1 AC=2`

*"References" carries no requirement — it is decomposed as the evidence pointer (PLAN §10, §2) used
throughout this analysis. C rows are constraints surfaced from the rulebook scan (the ticket has no
Constraint section); they are binding on the change and are listed so every hunk can trace to a row.*

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | "Persist and query the graph (§10). Single-writer, WAL, indexed." | One module owns the DB file: it creates the schema, writes rows, and answers every read. No other module opens a connection or holds SQL. | `code_atlas/store.py:1` is a one-line stub; zero importers repo-wide; `grep -rln 'sqlite3\|SELECT\|INSERT\|CREATE TABLE' code_atlas/` → **no matches** (nothing touches SQLite yet) | **5/5** (items 1, 2, 3, 4, 6) | **5/5** — `GraphStore` written; 74 store tests + the R4 guard green | ⬜ |
| R1 | Scope / Deliverables | "`store.py` `GraphStore`: create schema (`files`, `nodes`, `edges`, `nodes_fts` fts5, `meta`), WAL mode." | Idempotent `CREATE … IF NOT EXISTS` of the **14** schema objects of inventory A (1 pragma + 4 tables + 1 virtual table + 5 indexes + 3 FTS-sync triggers ratified by Q2), driven off `contract.py` field tuples rather than a re-typed column list (R3.2). | `PLAN.md:251-269` is the authoritative DDL; `store.py:1` stub | **3/3** (items 1, 2, 5) | **3/3** — 14 objects introspected; WAL asserted on a file DB | ⬜ |
| R2 | Scope / Deliverables | "Upsert file + replace-per-file nodes/edges; meta get/set (`schema_version`, `contract_version`, `last_commit`, `built_at`)." | `upsert_file(path, hash, language, parsed_ok)`; `replace_file_rows(path, nodes, edges)` = delete-then-insert scoped to that path, so re-indexing is idempotent; `get_meta`/`set_meta` over the **4** keys of inventory B. `built_at` is **not** in `PLAN.md:268` — the ticket adds it (see AC validation). | `PLAN.md:268` lists 3 meta keys; ticket line 16 lists 4; `PLAN.md:227-228` (upsert + replace per file, single writer) | **2/2** (items 3, 5) | **2/2** — upsert/replace/remove + 4 meta keys round-trip | ⬜ |
| R3 | Scope / Deliverables | "Query helpers used by tools (by name/kind/file, edges by source/target)." | The **6** read axes of inventory C (nodes by name, by kind, by file; edges by source, by target; FTS search from AC2), each bounded by an explicit `limit` (R4.3 forbids loading the graph into memory) and each with a deterministic `ORDER BY` tie-break (R4.2). | `PLAN.md:285-298` names the consuming tools; `PLAN.md:265-266` gives the two edge indexes these helpers must actually use | **2/2** (items 4, 5) | **2/2** — 6 helpers, each limit-bounded and tie-ordered | ⬜ |
| R4 | Scope / Deliverables | "Only component that touches SQLite (SRP): adapters never import it." | Two separate claims: (a) of the **11** core modules (inventory D) exactly one contains SQL/`sqlite3`; (b) adapter source never imports the store. **(b) is vacuously true today** — `adapters/` holds only `.gitkeep` — so its guard must be negative-controlled (LESSONS 002). | `ENGINEERING_RULES.md:26-31`; `CONVENTION.md:77` ("SQL lives in `store.py`"); `git ls-files adapters/` → `adapters/.gitkeep` only | **1/1** (item 6) | **1/1** — `test_exactly_one_core_module_touches_sqlite`; adapters half skipped as 0/0 | ⬜ |
| AC1 | Acceptance criteria | "Schema matches §10; re-indexing a file replaces its rows idempotently." | Two falsifiable halves: (a) introspect `sqlite_master` and assert all 14 inventory-A objects exist with the §10 column names/order (§10 as amended by Q1/Q2 in this diff); (b) index → re-index the same file twice and assert byte-identical row sets, including that a **removed** symbol disappears (a delete-blind implementation passes an insert-only assertion). | `PLAN.md:251-269`; no `tests/test_store*.py` exists | **4/4** (items 2, 3, 5, 8) | **4/4** — `test_schema_object_is_created` ×13 + idempotency + removed-symbol | ⬜ |
| AC2 | Acceptance criteria | "FTS search returns expected rows; identical input → identical rows (determinism test)." | Both halves now falsifiable by ratification: "expected rows" = **≥10 named cases, each asserted through `MATCH`** (Q9b, never `count(*)`); determinism = **row content ordered by a stable key with `nodes.id`/`edges.id` excluded and the clock injected**, so `files.updated_at`/`meta.built_at` are reproducible under a fixed clock (Q3). | Spike (below): §10's external-content FTS table returns **0 MATCH rows** as written; `SELECT count(*)` on it returns 1, so a count-based test passes while search is broken | **3/3** (items 4, 5, 8) | **3/3** — proving test + 14 MATCH cases + `test_identical_input_produces_identical_rows` | ⬜ |
| C1 | rulebook scan | R3.2 — "`contract.py` is the single source of truth for the schema. Store, indexer, and tools import from it; they never re-declare field lists." | The `nodes`/`edges` DDL and every INSERT column list derive from `NODE_FIELDS`/`EDGE_FIELDS`. Verified 1:1 and **in the same order** as `PLAN.md:255-264`, so the derivation is exact, not approximate. | `ENGINEERING_RULES.md:52-53`; `contract.py:47-68` vs `PLAN.md:255-264` — identical names, identical order | **4/4** (items 3, 4, 7, 9) | **4/4** — columns == `('id',) + contract` fields; R3.2 guard negative-controlled | ⬜ |
| C2 | rulebook scan | R4.2 — "Identical input → identical output. No wall-clock, randomness, or set-ordering leaking into stored data." | Rowid assignment follows insert order (worker-dependent, `PLAN.md:227`), and `updated_at`/`built_at` are wall-clock by definition. Both must be made injectable/excluded rather than asserted over. | `ENGINEERING_RULES.md:65-67`; `PLAN.md:254` (`updated_at`), ticket line 16 (`built_at`); spike: rowid restarted at 1 after a delete-all | **3/3** (items 1, 4, 5) | **3/3** — fixed clock reproducible; `test_ids_follow_insert_order_while_content_does_not` | ⬜ |
| C3 | rulebook scan | R4.3 — "Single SQLite writer… WAL, indexed queries, bounded traversal in SQL — never load the whole graph into memory." | One `GraphStore` = one connection = one writer; WAL set at open; every read helper takes a `limit`; no `fetchall()` over an unbounded table. | `ENGINEERING_RULES.md:68`; spike: `PRAGMA journal_mode=WAL` → `'wal'` on a file DB (`'memory'` for `:memory:`) | **2/2** (items 1, 4) | **2/2** — WAL asserted on a file DB; FK enforcement asserted; every helper requires `limit`. `busy_timeout` is **set but not asserted** → recorded coverage-gap exclusion | ⬜ |
| C4 | rulebook scan | R1.4 / R1.2 / R7.4 — SRP per component; one seam only; no dead abstractions. | `store.py` persists and queries only; it imports `contract` (and nothing else from the core) and is imported by indexer/resolver/tools. **No** `StoreProtocol`, backend abstraction, or migration framework — one implementation. | `ENGINEERING_RULES.md:20-22`, `26-31`, `102` | **3/3** (items 1, 3, 4) | **3/3** — one class, one connection; no protocol or migration runner added | ⬜ |
| C5 | rulebook scan | R5.1 / R5.3 — a failed parse sets `parsed_ok=0` and keeps going; config/programmer errors fail loud. | Store must accept a file row with `parsed_ok=0` and **zero** nodes/edges (that is the R5.1 path). A `schema_version` mismatch is a programmer error → raise, never silently reuse a foreign DB. | `ENGINEERING_RULES.md:72-78`; `PLAN.md:254` (`parsed_ok INT DEFAULT 1`) | **3/3** (items 1, 3, 5) | **3/3** — `parsed_ok=0` with zero rows; `SchemaVersionError` on a foreign version | ⬜ |
| C6 | rulebook scan | R6.1 / R6.4 — "store change → an integration test asserting resolved rows"; guardrail tests are real tests. | Tests drive a real `GraphStore` over a temp DB file (not a mock), and the R4 guard is negative-controlled so it cannot pass vacuously. | `ENGINEERING_RULES.md:82-92`; `LESSONS.md:18-26` (task 002's vacuous guard) | **3/3** (items 5, 6, 7) | **3/3** — real temp-DB tests, no mocks; both guards negative-controlled | ⬜ |
| C7 | rulebook scan + LESSONS | R1.1 CI grep-gate fires on prose, not just code. | `store.py` will legitimately contain the token `language` (the `files.language` column). Any line under `code_atlas/` where `match` appears **before** `language` fails the build — including the phrase "schema **matches** §10 … `language`" in a docstring. | `LESSONS.md:6-16`; `.github/workflows/ci.yml:49` | **1/1** (item 1) | **1/1** — R1.1 gate re-run locally: ok | ⬜ |
| C8 | rulebook + `CLAUDE.md` scan | R7.2 + "Docs before PR" / "Token usage on PR" | Every ratified decision that changes or extends `PLAN.md:251-269` (FTS sync objects, `built_at`, `schema_version`, pragma set) lands in PLAN **in this diff**, plus BACKLOG status + frontmatter + the token row. | `ENGINEERING_RULES.md:98-99`, `120-121`; `CLAUDE.md` "Docs before PR"; `LESSONS.md:28-34` | **3/3** (items 8, 9, 10) | **3/3** — PLAN §10 amended, CONVENTION §4 rule added, BACKLOG + frontmatter synced | ⬜ |

Status legend: ✅ done/proven · ⚠ deferred (needs follow-up ticket) · ❌ not met · ⬜ not yet started (Phase 1).

## AC validation

Every acceptance value independently re-derived. Three spikes were run read-only against the project's
own interpreter (`sqlite3` 3.53.1, FTS5 compiled in) to check §10's DDL actually satisfies the ACs.

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| R1 | "create schema (`files`, `nodes`, `edges`, `nodes_fts` fts5, `meta`)" — 5 objects | **11 schema objects** in `PLAN.md:251-269`: 1 pragma + 4 tables + 1 virtual table + **5 indexes** (`idx_nodes_name`, `idx_nodes_kind`, `idx_nodes_file`, `idx_edges_src`, `idx_edges_tgt`). The ticket's list omits the indexes, but "indexed" is in the Goal | **N** (ticket undercounts by 6) | measurable via `sqlite_master` introspection | **RATIFIED (Q9a)** — AC1's denominator is the schema objects, not the ticket's 5; with Q2's triggers **N = 14** |
| R2 | meta keys `schema_version, contract_version, last_commit, built_at` — 4 | `PLAN.md:268` lists **3** (`schema_version`, `contract_version`, `last_commit`); the ticket adds **`built_at`** | **N** (ticket adds a 4th key PLAN lacks) | measurable (key present, value shape asserted) | **RATIFIED (Q4)** — `built_at` adopted; `PLAN.md:268`'s comment gains it in this diff |
| R2 | `schema_version` — **no value and no mismatch policy anywhere** | Nothing in PLAN/CONVENTION/README defines the value or what happens when a DB carries a different one. Computed: **`"1"`**, mismatch ⇒ fail loud + require a full rebuild | **N** → **resolved Q4** | measurable once pinned | **RATIFIED (Q4)** — `schema_version = "1"`; a differing value **raises** (R5.3) telling the user to delete the DB and rebuild; no migration machinery (R7.4) |
| AC1 | "Schema matches §10" | Falsifiable **only** as introspection: assert `nodes` columns == `("id",) + contract.NODE_FIELDS` and `edges` == `("id",) + contract.EDGE_FIELDS` (verified identical in name and order, `contract.py:47-68` vs `PLAN.md:255-264`), plus the 5 index names and the `files`/`meta` column sets | Y | **measurable/greppable** | — (but see C7: the word "matches" near "language" in prose trips the R1.1 gate) |
| AC1 | "re-indexing a file replaces its rows idempotently" | Falsifiable as: index file → re-index **identical** content → identical rows; and re-index with a **symbol removed** → the stale row is gone. The second case is the one an insert-only implementation fails | Y | measurable | — |
| AC1 | `qualified_name TEXT UNIQUE` (`PLAN.md:257`) | **Cannot hold across files as specified.** Two files in the same PHP namespace each emit a `Namespace` node with the same qname; `if (!function_exists(…))` polyfills and legacy re-declarations do the same for `Function`/`Class`. Spike: the second insert raises `IntegrityError: UNIQUE constraint failed: nodes.qualified_name` | **N** — §10's constraint conflicts with §4.2's node vocabulary | measurable once the policy is pinned | **RATIFIED (Q1)** — key relaxed to `UNIQUE(qualified_name, file_path)`; `PLAN.md:257` corrected in this diff, and §8.2 gains the "one *or more* candidates" consequence |
| AC2 | "FTS search returns expected rows" | **§10's FTS table returns nothing as written.** `nodes_fts` uses `content='nodes'` (external content), which fts5 never auto-populates. Spike after a plain `INSERT INTO nodes`: `MATCH 'User'` → **0 rows**, while `SELECT count(*) FROM nodes_fts` → **1**. So a count-based test passes while search is broken | **N** — §10 cannot satisfy AC2 without added sync objects | measurable — but only if the test asserts via `MATCH`, never `count(*)` | **RATIFIED (Q2)** — 3 `AFTER INSERT/UPDATE/DELETE` triggers on `nodes`, added to `PLAN.md:251-269`; `'rebuild'` kept as a repair command |
| AC2 | "expected rows" | Vague adjective — no count, no semantics. Computed pin: **≥10 named cases** — exact name hit, qname-segment hit (`App` inside `\App\UserRepo`), member hit, no-match control, hit removed after delete, hit updated after replace, `integrity-check` clean, limit honoured, deterministic order, and a punctuation query that must not raise | **N** → **resolved Q9b** | **now falsifiable** — the case list is enumerated | **RATIFIED (Q9b)** — ≥10 named cases, every assertion through `MATCH` |
| AC2 | "identical input → identical rows (determinism test)" | **Four columns are non-deterministic by construction:** `nodes.id`/`edges.id` (rowids follow insert order, and `PLAN.md:227` fans files across N workers — spike confirmed rowids restart at 1 after a delete-all), `files.updated_at` and `meta.built_at` (wall-clock). Computed: assert over content ordered by a stable key, with those four excluded and the clock injected | **N** — the AC as written is unsatisfiable against R4.2 | **now falsifiable** — the carve-out is recorded | **RATIFIED (Q3)** — content compared ordered by a stable key, `nodes.id`/`edges.id` excluded, clock injected (`now: Callable[[], str]`, UTC ISO-8601); the carve-out is documented next to §10 |
| AC2 | FTS query safety (implied by "search") | A bare term containing `.` is **not** a legal fts5 query — spike: `MATCH 'user.ts'` → `OperationalError: fts5: syntax error near "."`. Since qnames are module-path-anchored for JS/TS (`CONVENTION.md:66`), this is a first-class input, not an edge case | **N** (unstated) | measurable (a `.`/`-`/`"`/`*` query must not raise) | **RATIFIED (Q7)** — the argument is a **literal term**: double-quoted with internal `"` doubled, `*` appended for prefix match; punctuation must never raise |
| AC2 | FTS tokenizer (implied by "expected rows") | §10 declares no `tokenize=`, so unicode61 applies. Spike: `_` **does** split (`User_Repo` matches `User` and `Repo`) but **camelCase does not** (`findByEmail` does not match `email` or `find`). Changing `tokenize=` later requires a full FTS rebuild ⇒ a `schema_version` bump | **N** (unstated, and expensive to change later) | measurable (assert the tokenizer's actual behaviour either way) | **RATIFIED (Q8)** — keep §10's unicode61 default; assert the actual behaviour in a test and **defer camelCase splitting to task 014** (which can afford the `schema_version` bump) |
| R4 | "adapters never import it" | **Vacuously true today**: `git ls-files adapters/` → `adapters/.gitkeep` only, so any guard over `adapters/` passes while proving nothing (exactly task 002's failure, `LESSONS.md:18-26`) | **N** — the value is 0/0 | measurable **only** with a negative control | self-resolved **S9** (negative-control the guard, per LESSONS 002) |

**No AC carries a `✅` at Phase 1** — nothing is built yet. Three acceptance values were **not
falsifiable as written** (AC2's "expected rows", AC2's determinism claim, R2's undefined
`schema_version`); Q9b / Q3 / Q4 pinned each to a measurable form at Gate 0, so **every acceptance value
is now falsifiable** and **none** needs a manual-check exclusion. **Coverage-gap exclusions: none.**

**Uncodified-standard items surfaced (never silently applied, never silently dropped):**

1. **The rulebook has no DB-conventions section, and this ticket is a schema change.** Per the
   rule-section coverage step, a schema/DDL change makes a DB-conventions section mandatory —
   `docs/ENGINEERING_RULES.md` has §1–§8 with **none** covering SQLite conventions (schema-version /
   migration policy, index policy, pragma set, NULL-vs-default policy, JSON-column encoding). Q1–Q5 are
   each really *a going-forward DB standard being chosen for the first time*. Route them through
   `/mango:codify` provisional→ratify if you want them written down as rules; until ratified they do
   **not** gate-block. (`.harness.json` also has `db_kind: null` / `migrations_path: null`, so no
   `db-map` exists to widen the blast radius against — noted, not required.)
2. **`ruff format` is applied by habit but is not a codified standard.** CI runs `ruff check` only
   (`ci.yml:29-30`); `ruff format --check .` currently reports **2 files unformatted** on untouched
   `main` (`docs/PLAN.md`'s Python code block and `tests/test_config.py:115`). So "the repo is
   ruff-formatted" is an uncodified standard. It is **not** treated as a baseline failure here and must
   not gate-block; if the formatter should be binding, codify it and add it to CI as its own change.
3. **`CLAUDE.md` and `BACKLOG.md` name a working-doc file that this project does not use.** Both point
   the cost ledger at `docs/tasks/NNN_slug.work.md` (`BACKLOG.md:51`), but `work_doc_mode` is `embed`,
   so the ledger lives in the ticket file. Recorded as a docs-truth fix candidate for the Phase-2
   change-list, traced to C8 — not silently absorbed.

## Inventory (universal "all/every/no" requirements)

Four counted denominators. R1/AC1 and R3 are "do X for each of N" requirements → the lists below **are**
the per-item checklists; review must confirm every row, not a total.

### Inventory A — schema objects per PLAN §10 as amended (R1 / AC1) · **Denominator N = 14**

| # | Object | Kind | Ph3/4 proven by | Status |
|---|--------|------|-----------------|--------|
| 1 | `journal_mode = WAL` | pragma | ⬜ | ⬜ |
| 2 | `files(path, hash, language, parsed_ok, updated_at)` | table | ⬜ | ⬜ |
| 3 | `nodes(id + contract.NODE_FIELDS)`, key `UNIQUE(qualified_name, file_path)` (Q1) | table | ⬜ | ⬜ |
| 4 | `idx_nodes_name` | index | ⬜ | ⬜ |
| 5 | `idx_nodes_kind` | index | ⬜ | ⬜ |
| 6 | `idx_nodes_file` | index | ⬜ | ⬜ |
| 7 | `edges(id + contract.EDGE_FIELDS)` | table | ⬜ | ⬜ |
| 8 | `idx_edges_src(source_qname, kind)` | index | ⬜ | ⬜ |
| 9 | `idx_edges_tgt(target_qname, kind)` | index | ⬜ | ⬜ |
| 10 | `nodes_fts(name, qualified_name, file_path, params)` fts5 | virtual table | ⬜ | ⬜ |
| 11 | `meta(key, value)` | table | ⬜ | ⬜ |
| 12 | `nodes_ai` — `AFTER INSERT ON nodes` → FTS insert | trigger (Q2) | ⬜ | ⬜ |
| 13 | `nodes_ad` — `AFTER DELETE ON nodes` → FTS `'delete'` | trigger (Q2) | ⬜ | ⬜ |
| 14 | `nodes_au` — `AFTER UPDATE ON nodes` → FTS delete + insert | trigger (Q2) | ⬜ | ⬜ |

Objects 12–14 do **not** exist in `PLAN.md:251-269` — that omission is exactly why AC2 fails against §10
as written. Ratified by Q2, so they land in §10 in this diff (C8), along with Q1's relaxed key on object 3.
`INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild')` stays available as a repair/verify command but is no
longer the sync mechanism. **Not in N:** the pragma set beyond WAL (`foreign_keys=ON`, `busy_timeout=5000`,
ratified Q5) — connection state, not schema objects; asserted separately via `PRAGMA` reads.

### Inventory B — `meta` keys (R2) · **Denominator N = 4**

| # | Key | Value | Written by | Ph3/4 proven by | Status |
|---|-----|-------|------------|-----------------|--------|
| 1 | `schema_version` | `"1"`; mismatch on open ⇒ raise (ratified **Q4**) | store, at create | ⬜ | ⬜ |
| 2 | `contract_version` | `str(contract.CONTRACT_VERSION)` = `"1"` (`contract.py:16`) | indexer (`PLAN.md:228`) | ⬜ | ⬜ |
| 3 | `last_commit` | git SHA | indexer (task 016) | ⬜ | ⬜ |
| 4 | `built_at` | injected clock, UTC ISO-8601 (**not in `PLAN.md:268`** — ticket-added, adopted by Q4) | indexer | ⬜ | ⬜ |

### Inventory C — query helpers (R3 + AC2) · **Denominator N = 6**

Every row must be bounded by an explicit `limit` (R4.3) and carry a deterministic `ORDER BY` (R4.2).

| # | Read axis | Index it must use | Ph3/4 proven by | Status |
|---|-----------|-------------------|-----------------|--------|
| 1 | nodes by `name` | `idx_nodes_name` | ⬜ | ⬜ |
| 2 | nodes by `kind` | `idx_nodes_kind` | ⬜ | ⬜ |
| 3 | nodes by `file_path` | `idx_nodes_file` | ⬜ | ⬜ |
| 4 | edges by `source_qname` (+ optional kind) | `idx_edges_src` | ⬜ | ⬜ |
| 5 | edges by `target_qname` (+ optional kind) | `idx_edges_tgt` | ⬜ | ⬜ |
| 6 | FTS search (from **AC2**, not R3) | `nodes_fts` | ⬜ | ⬜ |

*Also needed by name for downstream tasks but **not** ticket-required, so out of N:* `get_node(qname)`
(task 014's `read_symbol`), `remove_file(path)` (§8.1 step 2 reconcile). Recorded so review does not read
them as scope creep — each will trace to R2/R3 in the Phase-2 change-list or be dropped.

### Inventory D — core modules vs the "only component that touches SQLite" claim (R4) · **Denominator N = 11**

Exactly **1** of the 11 may contain `sqlite3`/SQL. Current state: **0/11** (grep confirms no match), so
after this change the guard must read exactly `store.py`.

| # | Module | May contain SQL? | Status |
|---|--------|------------------|--------|
| 1 | `code_atlas/__init__.py` | no | ⬜ |
| 2 | `code_atlas/adapter.py` | no | ⬜ |
| 3 | `code_atlas/config.py` | no | ⬜ |
| 4 | `code_atlas/contract.py` | no | ⬜ |
| 5 | `code_atlas/gitutil.py` | no | ⬜ |
| 6 | `code_atlas/ignore.py` | no | ⬜ |
| 7 | `code_atlas/indexer.py` | no | ⬜ |
| 8 | `code_atlas/main.py` | no | ⬜ |
| 9 | `code_atlas/resolver.py` | no | ⬜ |
| 10 | **`code_atlas/store.py`** | **yes — the only one** | ⬜ |
| 11 | `code_atlas/tools/__init__.py` | no | ⬜ |

**Second half of R4 — "adapters never import it" — is 0/0 today** (`adapters/` holds only `.gitkeep`).
Handled by **S9**: assert the guard's inputs are non-empty and negative-control it, per `LESSONS.md:18-26`.

### Surface inventory

**N/A — TRACK is backend.** No reachable UI surface exists in this repo (no routes, templates, or
frontend entry points; `code_atlas/tools/` is an MCP tool surface, not a rendered one).

## Clarifications

`CLARIFICATION: 19 raised | 19 resolved (10 self-resolved+cited · 9 human-ratified at Gate 0) | 0 for human decision`

**Gate 0: CLEARED** — the user ratified all nine recommendations ("ratify all", 2026-07-29). None reverses
a prior decision. Q1, Q2 and Q4 each **amend `PLAN.md:251-269`**, which §10 has carried since the plan was
written, so those doc corrections ride the Phase-2 change-list (R7.2 / C8) rather than being applied
silently to the schema alone.

**Self-resolved (cited):**

1. **S1 — The store does not validate the contract.** It persists what it is handed;
   `contract.validate()` runs at the indexer/adapter boundary. *R1.4 (`ENGINEERING_RULES.md:26-31`) —
   store persists/queries only; `contract.py:112-118` returns errors so the indexer can set `parsed_ok=0`.*
2. **S2 — The store creates its parent directory and accepts `:memory:`.** `config.db_path` is
   `<root>/.code-atlas/graph.db` and that directory is gitignored, so it may not exist. *`config.py:74`,
   `config.py:33`; `.gitignore` excludes `.code-atlas/`.*
3. **S3 — `meta` is a `str → str` API.** §10 types both columns TEXT; callers coerce
   (`str(CONTRACT_VERSION)`). No per-key typing table. *`PLAN.md:268`.*
4. **S4 — The store only *provides* meta get/set; the indexer decides *when*.** `contract_version`,
   `last_commit` and `built_at` are written by the build, not by schema creation. *`PLAN.md:228`
   (step 4 of full build); ticket line 16 says "meta get/set", not "meta policy".*
5. **S5 — No store abstraction, no migration framework.** One implementation, one backend; a
   `StoreProtocol` or a migration runner would be a dead abstraction. *R1.2 (`:20-22`), R7.4 (`:102`).*
6. **S6 — Every read helper is bounded and ordered.** Each takes an explicit `limit` (the caller passes
   `config.max_results`; the store never reaches out to config) and carries a full `ORDER BY` so ties
   cannot reorder between runs. *R4.3 (`:68`), R4.2 (`:65-67`), `CONVENTION.md:74`.*
7. **S7 — `modifiers`/`params`/`extra` are canonicalised by the store.** They are TEXT in §10 but
   adapters may emit lists/objects, so the store serialises non-strings with sorted keys and compact
   separators, and maps `None` → NULL. Determinism forces the sorted keys. *R4.2 (`:65-67`);
   `contract.py:57` (`extra`); `PLAN.md:258` (TEXT columns).* Whether the *contract* should pin these
   types is a task-005/007 question, recorded not answered.
8. **S8 — Ecosystem/`language` prose in `store.py` must keep `language` before `match`.** The
   `files.language` column is mandated by §10, and the R1.1 gate's second alternative has no code
   anchor. The exact regex is re-run locally before the PR. *`LESSONS.md:6-16`; `ci.yml:49`;
   `PLAN.md:254`.*
9. **S9 — The R4 guard is negative-controlled rather than trusted.** Assert the guard's inputs are
   non-empty (`len(core_modules()) == 11`), inject a real violation (a `sqlite3` import into another
   core module), confirm the guard fails, remove it, confirm the file is byte-identical. For the
   adapters half, record the 0/0 vacuity out loud instead of letting a passing grep imply coverage.
   *`LESSONS.md:18-26`.*
10. **S10 — No contract-version bump.** This task adds no node/edge kind, field, or qname change; it
    only persists the existing vocabulary. *R3.1 (`:51-53`); `contract.py:16` stays at 1.*

**Human-ratified at Gate 0 — 9 items (each was asked with a recommendation; all recommendations adopted
verbatim, 2026-07-29). The "Recommended" option in each item below *is* the ratified decision; the
rejected alternatives are kept so Phase 2 does not re-litigate them and the reviewer can see the
trade-off that was made:**

- **Q1 — `qualified_name TEXT UNIQUE` collides across files. What is the policy?** *(blocking)*
  §10 declares the constraint; §4.2's vocabulary guarantees it will be violated — two files in one PHP
  namespace both emit `Namespace \App\Models`, and `if (!function_exists(…))` polyfills / legacy
  re-declarations do the same for `Function`/`Class`. Spike confirms the second insert raises
  `IntegrityError`.
  - **(a) Recommended — relax the constraint to `UNIQUE(qualified_name, file_path)`.** Replace-per-file
    stays correct and order-independent: file A's rows are keyed by A, file B's by B, so nothing one file
    owns can be destroyed by re-indexing another. Costs a `PLAN.md:257` correction and means resolver
    lookups (§8.2) may return >1 candidate for a duplicated qname — which is *true* and better modelled
    as a `HEURISTIC` multi-candidate (R5.2 already has that tier) than hidden behind a lost row.
  - (b) Keep `UNIQUE(qualified_name)` and `INSERT OR REPLACE` — last writer wins. **Rejected:** worker
    order decides which file owns the row (`PLAN.md:227`), and then re-indexing the winner deletes a row
    the loser needed. That is a direct R4.2 violation and silently loses symbols.
  - (c) Keep `UNIQUE(qualified_name)` and skip-with-count on conflict. Deterministic only if insert order
    is; still loses real symbols.
- **Q2 — §10's `nodes_fts` is never populated. Which sync mechanism?** *(blocking)*
  `content='nodes'` makes it an external-content table: fts5 does not index anything on its own. Proven —
  after a plain `INSERT INTO nodes`, `MATCH 'User'` returns **0 rows** while `count(*)` returns **1**.
  - **(a) Recommended — three `AFTER INSERT/UPDATE/DELETE` triggers on `nodes`.** Verified in the spike:
    `MATCH` hits after insert, drops to 0 after `DELETE … WHERE file_path=?`, and
    `INSERT INTO nodes_fts(nodes_fts) VALUES('integrity-check')` is clean. It is correct for **both** the
    full build and task 016's incremental path, and the store cannot forget to call it. Adds 3 objects to
    §10 (inventory A → 14) and a `PLAN.md` update.
  - (b) Explicit `VALUES('rebuild')` only, as `PLAN.md:229` step 5 implies. Simple, but O(all nodes) per
    build and wrong for incremental — a per-file update would need a full rebuild to stay correct.
  - (c) Drop external content (plain fts5 table). Duplicates every indexed string on disk for no gain.
  - Either way I keep `'rebuild'` available as a repair/verify command; the question is whether it is the
    *only* mechanism.
- **Q3 — Ratify the determinism carve-out for AC2.** *(blocking — it is what makes AC2 falsifiable)*
  Four columns cannot be deterministic: `nodes.id`/`edges.id` (rowids follow insert order, which follows
  worker completion order per `PLAN.md:227`; the spike showed rowids restarting at 1 after a delete-all)
  and `files.updated_at` / `meta.built_at` (wall-clock, which R4.2 explicitly bans from stored data).
  - **Recommended:** (i) the determinism test compares row **content** ordered by a stable key
    (`qualified_name`, then `file_path`/`line` for edges) with the two `id` columns excluded; (ii) the
    clock is injected into `GraphStore` (`now: Callable[[], str]`, default UTC ISO-8601) so tests pin it
    and `built_at`/`updated_at` become reproducible under a fixed clock; (iii) the carve-out is recorded
    in `PLAN.md` next to §10 so a later reader does not think ids are stable identifiers.
  - Alternative: make ids stable by having the indexer insert in sorted path order. **Rejected** — it
    serialises the write side against the point of N workers, and ids still shift when a file's symbol
    count changes.
- **Q4 — `schema_version`: value, and what happens on a mismatch?** Nothing in the repo defines either,
  and the ticket adds a `built_at` key that `PLAN.md:268` does not list.
  - **Recommended:** `schema_version = "1"`. On open, a DB carrying a different value **raises** (R5.3 —
    a programmer/config error) with a message telling the user to delete `.code-atlas/graph.db` and
    rebuild. **No migration machinery** (R7.4) — the DB is a derived cache, cheap to rebuild. Add
    `built_at` to `PLAN.md:268` in this diff.
  - Alternative: auto-drop-and-recreate on mismatch. Convenient, but it silently deletes a
    possibly-expensive index without asking; fails loud is the rulebook's default.
- **Q5 — Which pragmas beyond WAL, and is `foreign_keys` enforced?** §10 gives WAL and declares
  `file_path TEXT REFERENCES files(path)`, but SQLite leaves FK enforcement **off** by default (spike:
  `PRAGMA foreign_keys` → `0`), so the declared reference is currently decorative.
  - **Recommended:** `journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`. With FKs on, the §8.1
    reconcile and the per-file replace delete in dependency order (edges → nodes → file row), which is a
    real ordering constraint worth having a test for. No `ON DELETE CASCADE` (it would change §10's DDL
    and hide ordering bugs). `synchronous` left at its default — this is a rebuildable cache, not a
    ledger, and I would rather not tune what we have not measured.
  - Alternative: leave FKs off, matching today's behaviour exactly. Then the `REFERENCES` clause should
    be documented as documentation-only, not silently unenforced.
- **Q6 — The exact query-helper surface and return type.** Inventory C fixes the six axes; the shape is
  open, and R3.2 constrains it: a `Node` dataclass with 10 fields would **re-declare** `NODE_FIELDS`.
  - **Recommended:** each helper returns `list[dict[str, object]]` with keys built from
    `("id",) + contract.NODE_FIELDS` / `EDGE_FIELDS`, so the field list exists once (`contract.py:47-68`)
    and a contract change cannot silently desynchronise the store. Signatures:
    `nodes_by_name(name, *, kind=None, limit)`, `nodes_by_kind(kind, *, limit)`,
    `nodes_by_file(path, *, limit)`, `edges_by_source(qname, *, kind=None, limit)`,
    `edges_by_target(qname, *, kind=None, limit)`, `search_nodes(query, *, kind=None, limit)`.
  - Alternative: return `sqlite3.Row`. Cheaper, but leaks the driver type into `tools/` and gives no
    contract coupling.
- **Q7 — FTS query escaping policy.** Proven: `MATCH 'user.ts'` raises
  `OperationalError: fts5: syntax error near "."`, and JS/TS qnames are module-path-anchored
  (`CONVENTION.md:66`), so dotted input is normal, not exotic.
  - **Recommended:** `search_nodes` treats the argument as a **literal term**, not fts5 syntax: wrap it
    in double quotes with internal `"` doubled, and append `*` for prefix matching. A punctuation-bearing
    query must return rows or nothing — never raise. Falsifiable with `.`, `-`, `"`, `*`, `:` cases.
  - Alternative: pass the query through raw and let task 014 own syntax. **Rejected** — it makes the
    store crash on ordinary input, and SQL/FTS syntax is the store's job per `CONVENTION.md:77`.
- **Q8 — Pin the FTS tokenizer now, or accept the camelCase gap?** §10 declares no `tokenize=`, so
  unicode61 applies. Spike: `_` splits (`User_Repo` → `User`, `Repo`) but camelCase does **not**
  (`findByEmail` matches neither `email` nor `find`). Changing `tokenize=` later needs a full FTS
  rebuild ⇒ a `schema_version` bump.
  - **Recommended:** keep §10's default in task 004 and **record the camelCase limitation as an explicit
    deferred item for task 014** (which owns search ranking and semantics and can afford the bump). Add a
    test asserting the tokenizer's *actual* behaviour, so the limitation is documented in code rather
    than discovered later.
  - Alternative: add a `tokenize` clause now. It is a search-quality decision made before any search
    tool exists, i.e. tuning ahead of measurement.
- **Q9 — Two AC denominators to confirm.** (a) **AC1 = 11 schema objects**, not the ticket's 5 — the
  ticket's list omits the five indexes, though "indexed" is in the Goal (§10 mandates all five). If Q2
  ratifies triggers, N becomes 14. (b) **AC2's "expected rows" = ≥10 named cases**, every one asserted
  through a `MATCH` query — never `count(*)`, which the spike showed returns 1 on an unpopulated index
  and so would pass while search is broken.

---

## Phase 1 — Analysis ✋ Gate 1

**Gap analysis (enhancement — no bug to root-cause).** Per goal, current vs target:

| Goal clause | Current state (`path:line`) | Target | Gap |
|---|---|---|---|
| "Persist … the graph" | `code_atlas/store.py:1` — a one-line docstring stub; `grep -rln 'sqlite3\|SELECT\|INSERT\|CREATE TABLE' code_atlas/` → **no matches** | `GraphStore` creates the 11 inventory-A objects and writes rows | Nothing persists; the DB file is never created |
| "… and query" | no read path anywhere; `code_atlas/tools/__init__.py` is empty | the 6 inventory-C helpers, each bounded + ordered | No read surface; `tools/` (010/013/014) has nothing to call |
| "Single-writer" | n/a | one `GraphStore` = one connection = one writer (R4.3) | Unimplemented; `PLAN.md:227` fans **parsing** across N workers, so the single-writer boundary must be explicit or it will be violated at task 009 |
| "WAL" | n/a | `PRAGMA journal_mode=WAL` at open (verified `'wal'` on a file DB) | Unimplemented |
| "indexed" | n/a | all 5 §10 indexes, and helpers whose predicates actually use them | Unimplemented; the ticket's own deliverable list omits the indexes (→ Q9a) |
| "(§10)" | `PLAN.md:251-269` is authoritative but **incomplete/incorrect** in three places | §10 amended in this diff (all three ratified at Gate 0) | `qualified_name UNIQUE` unsatisfiable → relaxed key (Q1); `nodes_fts` never populated → 3 triggers (Q2); `built_at` missing from the meta comment → added (Q4) |

**Handler / entry point + blast radius.**

- **Entry point:** `GraphStore` in `code_atlas/store.py` (currently a stub). It is constructed with a
  `db_path` from `config.load_config()` (`config.py:74`) — the store never reads `os.environ`.
- **Upstream dependency:** `code_atlas/contract.py` only (`NODE_FIELDS`, `EDGE_FIELDS`,
  `CONTRACT_VERSION`) — R3.2. No other core import.
- **Blast radius — all four dependents are still stubs, so nothing can regress today:**
  `indexer.py:1` (task 009 — upsert/replace/meta), `resolver.py:1` (task 011 — reads nodes, updates
  `edges.target_qname`), `tools/` (tasks 010/013/014 — the six read helpers), `gitutil.py:1` (task 016 —
  `last_commit`). Consequence: **no integration test can prove a caller**; AC coverage is unit/integration
  tests driving a real `GraphStore` over a temp DB (R6.1's "integration test asserting resolved rows"
  applies with the store itself as the system under test).
- **Forward blast radius of the Q1/Q2 decisions** (why they are blocking rather than deferrable):
  Q1 changes what `resolver.py` (§8.2) may assume when it looks up `nodes.qualified_name` — a relaxed
  key means "one candidate" becomes "one *or more*"; Q2 decides whether task 016's incremental path can
  keep FTS correct without a full rebuild. Both are cheap now and expensive after 009/011/016 exist.
- **Repos touched:** `app` (`.`) only. **`db-map`:** none exists (`db_kind: null`,
  `migrations_path: null`) — this task *creates* the schema a future `db-map` would describe, so there
  is no schema-dependents graph to widen against.

**Rule-compliance section coverage.** Change type = *new core module* + *SQLite schema/DDL creation* +
*tests* + *docs*. Sections derived from that, not hand-picked:

`RULE SECTIONS: §1 (R1.1 ✅ · R1.2 ✅ · R1.3 ✅ · R1.4 ✅ · R1.5 N/A no adapter touched · R1.6 N/A no capability consumed) · §2 (R2.1–R2.3 N/A — adapter-only, no adapter source in the change-list) · §3 (R3.1 ✅ no bump needed · R3.2 ✅ mandatory · R3.3 ✅ store persists target_qname NULL · R3.4 N/A no adapter) · §4 (R4.1 ✅ · R4.2 ✅ mandatory · R4.3 ✅ mandatory) · §5 (R5.1 ✅ parsed_ok=0 with zero rows must persist · R5.2 N/A resolver-owned · R5.3 ✅ schema_version mismatch fails loud) · §6 (R6.1 ✅ · R6.2 N/A no language fixture · R6.3 N/A single repo · R6.4 ✅ R4 guard is a real, negative-controlled test) · §7 (R7.1 ✅ · R7.2 ✅ · R7.3 ✅ · R7.4 ✅ · R7.5 ✅) · §8 (R8.1 N/A no adapter runtime · R8.2 ✅ sqlite3 is stdlib, no new dependency) · CONVENTION §2 ✅ on-disk artifact path · §4 ✅ SQL confined to store.py · DB-conventions section ❌ ABSENT from the rulebook — a mandatory section for a schema change, surfaced as uncodified-standard item 1 (codify nudge), not silently skipped`

**Self-audit.**

- 4 sections found, 4 decomposed; 15 matrix rows (C=8 R=4 G=1 AC=2), every `Status` filled (`⬜` — nothing
  built yet, by design at Phase 1).
- AC validation table complete: **12 values re-derived**, 8 mismatches, each raised as a Gate-1 question
  carrying the computed value and each now **RATIFIED** — no silent correction. The three values that were
  not falsifiable as written are pinned by Q9b / Q3 / Q4, so **every acceptance value is falsifiable** and
  **no AC carries a `✅`** yet. Manual-check exclusions: none needed. Coverage-gap exclusions: none.
- `BASELINE: green` captured on untouched `main` @ `88676c4` (86 passed · ruff check clean · mypy clean);
  the unformatted-files observation is recorded as an uncodified standard, not a baseline exclusion.
- Inventories set: **A=14** schema objects (11 from §10 + 3 triggers ratified by Q2), **B=4** meta keys,
  **C=6** query helpers, **D=11** core modules, each as a per-item checklist. R4's adapters half recorded
  as **0/0 vacuous** with a negative control (S9).
- `STRUCTURE: native` · `TRACK: backend` · `TIER: full` · `SCOPE: M` declared. `SURFACES`: N/A (backend).
- `RULE SECTIONS` emitted with every applicable section checked or N/A-with-reason; the one **absent**
  mandatory section (DB conventions) is surfaced as a finding.
- **`j = 0` → Gate 0 CLEARED** ("ratify all", 2026-07-29). The three blocking §10 defects (Q1, Q2, Q3) are
  settled, so a design can now be written against an amended §10.
- **Carried into Phase 2 as mandatory change-list items** (each traces to a matrix row, so no hunk is
  untraceable — `LESSONS.md:28-34`): `PLAN.md:257` relaxed key · `PLAN.md:251-269` + 3 FTS triggers ·
  `PLAN.md:268` + `built_at` · the §10-adjacent determinism carve-out note · `schema_version` policy ·
  the pragma set — all under **C8**. Deferred, not silently dropped: camelCase FTS splitting → **task 014**
  (Q8), and the two uncodified-standard items (DB-conventions section, `ruff format`) → `/mango:codify`.
- **Gate 1 status:** waiting on user

## Phase 2 — Design ✋ Gate 2

**Approach.** One class, `GraphStore`, in `code_atlas/store.py`, owning one `sqlite3.Connection`:

1. **Schema as SQL text, field lists imported from `contract.py`.** The §10 DDL (as amended by Q1/Q2)
   lives in one `CREATE … IF NOT EXISTS` script — verified idempotent, so `__init__` can run it every
   open. The **write path** builds its column lists from `contract.NODE_FIELDS`/`EDGE_FIELDS`
   (`", ".join(...)` + placeholders) and the **read path** rebuilds rows with
   `dict(zip(("id", *NODE_FIELDS), row, strict=True))`, so no Python literal ever re-types a field name
   (R3.2). AC1's introspection test then asserts the DDL text agrees with `contract.py` — the two
   representations are mechanically cross-checked rather than trusted.
2. **Open sequence, in this order:** `PRAGMA journal_mode=WAL` → `foreign_keys=ON` → `busy_timeout=5000`
   (all **before** any transaction — `foreign_keys` is silently ignored inside one), then the DDL script,
   then the `schema_version` check: absent ⇒ write `"1"`; present and different ⇒ raise (Q4/R5.3).
3. **Writes are per-file and transactional.** `upsert_file` (ON CONFLICT DO UPDATE) →
   `replace_file_rows(path, nodes, edges)` deletes that path's edges and nodes then inserts, inside one
   `with self._conn:` block. Delete-then-insert is what makes AC1's idempotency true, and the three FTS
   triggers make the search index follow automatically — including for task 016's incremental path.
   `remove_file` is the same delete without the insert (§8.1 step 2 reconcile) and must delete nodes
   **before** the `files` row, because FK enforcement is on.
4. **Reads are bounded and totally ordered.** Six helpers, each with an explicit `limit` parameter (the
   caller passes `config.max_results`; the store never reaches for config) and a full `ORDER BY` so ties
   cannot reorder between runs (R4.2/R4.3). `search_nodes` treats its argument as a **literal** term —
   `'"' + query.replace('"', '""') + '"*'` — so punctuation and fts5 operators are neutralised instead
   of raising.
5. **The clock is injected** (`now: Callable[[], str]`, default UTC ISO-8601) so `files.updated_at` is
   reproducible under a fixed clock; `built_at` is written by the indexer through `set_meta` (S4).

**Rejected alternatives.**

- **Generate the DDL entirely from `contract.py` via a name→SQL-type map.** Rejected on two counts:
  the map has to live somewhere, and as a Python dict/tuple in `store.py` it holds ≥2 contract field
  names in one literal, which **fails the existing R3.2 guard** (`tests/test_contract_sole_source.py:57`);
  moving it into `contract.py` leaks storage types into the contract and breaks R1.4's SRP. Keeping SQL
  as SQL and cross-checking it by introspection gets the same guarantee with no new coupling.
- **`INSERT OR REPLACE` on a global `UNIQUE(qualified_name)`** — rejected at Gate 0 (Q1): worker order
  would decide row ownership, violating R4.2 and silently losing symbols.
- **`'rebuild'`-only FTS sync** — rejected at Gate 0 (Q2): O(all nodes) per build and unusable for
  incremental. It survives as a repair command only.
- **A `StoreProtocol` / repository interface, or a migration runner.** One implementation, one backend;
  both would be dead abstractions (R1.2, R7.4). `schema_version` mismatch fails loud instead (Q4).
- **`get_node(qname)` as a seventh helper.** No ticket requirement needs it — `read_symbol` is task
  014's, and under Q1's relaxed key it would return a list anyway. Dropped (R7.1/R7.4) rather than added
  speculatively; recorded so review sees the omission is deliberate.
- **A separate `schema.sql` resource file.** `CONVENTION.md:77` puts SQL in `store.py`; an extra file
  adds packaging concerns for no benefit at this size.

### Assumptions

Every runtime assumption below was **de-risked by a throwaway spike during this phase** (read-only,
against the project's own interpreter — `sqlite3` 3.53.1, FTS5 compiled in). None is left unresolved.

| Assumption | verified / novel-untested | Spike result |
|---|---|---|
| `PRAGMA foreign_keys=ON` takes effect and survives `executescript` | **verified** | `pragma foreign_keys` → `1` both before and after the DDL script. Must be set **outside** a transaction — that ordering is now step 2 of the approach |
| FK enforcement makes the delete order a real constraint, not decoration | **verified** | Inserting a node for an absent `files` row → `IntegrityError: FOREIGN KEY constraint failed`; deleting a `files` row that still has nodes → same. Both become named tests |
| `CREATE … IF NOT EXISTS` (tables + vtable + 3 triggers) is idempotent per open | **verified** | Script run twice; object count stable at 9 non-internal entries, no error |
| `UNIQUE(qualified_name, file_path)` admits the same qname from two files | **verified** | Two `Namespace \App` rows from `a.php`/`b.php` coexist (count = 2) |
| Replace-per-file is content-idempotent, and `id` genuinely is not | **verified** | Ordered content before == after (`True`), while ids moved `1,2,3` → `2,3,4`. This is why Q3's id carve-out is necessary rather than theoretical |
| The 3 triggers keep FTS correct across a per-file replace | **verified** | `MATCH '"save"*'` → 1 hit, 0 after `DELETE … WHERE file_path='a.php'`, 1 again after re-insert; `'integrity-check'` clean |
| Quoted-prefix escaping never raises on real input | **verified** | `user.ts`, `src/user.ts::User`, `sa`, `App`, `he"llo`, `''`, `'  '`, `*`, `-x`, `NOT App` — all return a count, **none raises**; operators are neutralised (`NOT App` → 0) |
| `rank` is usable but needs a tie-break | **verified** | Two equally-ranked `App` rows returned — so every helper carries a full `ORDER BY`, not `ORDER BY rank` alone |
| unicode61 splits `_` but not camelCase | **verified** (analysis spike) | `User_Repo` matches `User`/`Repo`; `findByEmail` matches neither `find` nor `email` → asserted as documented behaviour, camelCase deferred to task 014 (Q8) |
| `sqlite3` needs no third-party dependency | **verified** | stdlib; `pyproject.toml` unchanged (R8.2) |

### Smallest change-list

Every item traces to a matrix row. **Proof collateral is listed up front, not discovered at execute.**

| # | Change | File / area | Ph2 covered by | k/N |
|---|--------|-------------|----------------|-----|
| 1 | `GraphStore.__init__` / `close` / context manager: open sequence (3 pragmas → DDL script → `schema_version` check), injected clock, parent-dir creation | `code_atlas/store.py` | G1, R1, C3, C5, C4 | 5/5 |
| 2 | The §10-as-amended DDL script: 4 tables + `nodes_fts` + 5 indexes + 3 triggers, `UNIQUE(qualified_name, file_path)` | `code_atlas/store.py` | R1, AC1 | 2/2 |
| 3 | Write path: `upsert_file`, `replace_file_rows`, `remove_file`, `get_meta`/`set_meta`, `rebuild_search_index` — column lists derived from `contract.NODE_FIELDS`/`EDGE_FIELDS`, JSON canonicalised | `code_atlas/store.py` | R2, C1, C5, AC1 | 4/4 |
| 4 | Read path: the 6 inventory-C helpers, each `limit`-bounded and fully ordered; `search_nodes` escapes its term | `code_atlas/store.py` | R3, C3, C4, AC2 | 4/4 |
| 5 | Store tests: schema introspection (14 objects), idempotency + removal, ≥10 `MATCH` cases, determinism under a fixed clock, pragma + FK-ordering, `schema_version` mismatch, `parsed_ok=0` with zero rows, 6 helpers, JSON canonicalisation, escaping, tokenizer behaviour | `tests/test_store.py` *(new)* | AC1, AC2, R2, R3, C2, C5, C6 | 7/7 |
| 6 | **Proof collateral / new guard:** R4 — exactly 1 of the 11 core modules contains `sqlite3`/SQL, guard inputs asserted non-empty, negative-controlled, adapters' 0/0 vacuity recorded in the test itself | `tests/test_sql_confinement.py` *(new)* | R4, C6, D-inventory | 3/3 |
| 7 | **Proof collateral (no edit, hard design constraint):** `test_consumer_does_not_redeclare_the_contract_vocabulary[store.py]` currently passes **vacuously** (store.py is a 1-line stub). Writing store.py makes it a live assertion, so **no Python collection literal in `store.py` may hold ≥2 contract vocabulary strings** — this is what forces items 3–4's derived column lists | `tests/test_contract_sole_source.py:57` (unchanged) | C1, C6 | 2/2 |
| 8 | `PLAN.md` §10 amendments: relaxed key (`:257`), 3 FTS triggers, `built_at` in the meta comment (`:268`), the pragma set, `schema_version` policy, and the determinism carve-out note (ids/wall-clock are not stable) | `docs/PLAN.md` | C8, AC1, AC2 | 3/3 |
| 9 | `CONVENTION.md` §4: one line — node/edge column lists are derived from `contract.py`, never re-typed in a consumer (the rule items 3–4 obey, binding on indexer/resolver/tools next) | `docs/CONVENTION.md` | C1, C8 | 2/2 |
| 10 | Status sync: `BACKLOG.md` row 004 + task frontmatter, and the token-usage row | `docs/BACKLOG.md`, `docs/tasks/004_sqlite-store.md` | C8 | 1/1 |

**Test blast-radius, traced mechanically (not a name grep).**

- **Producers/consumers of `store.py`:** `git ls-files` + import grep → **zero importers today**;
  `indexer.py`, `resolver.py`, `tools/`, `gitutil.py` are all one-line stubs, so no existing assertion
  about store behaviour can break.
- **Symbol-level fan-out:** the change consumes `contract.NODE_FIELDS`/`EDGE_FIELDS`/`CONTRACT_VERSION`.
  Grepping those symbol names across **every** test root (`tests/`, `tests/contract/`,
  `tests/fixtures/`) finds `tests/contract/test_contract_schema.py` (asserts the tuples themselves —
  untouched by this change) and `tests/test_contract_sole_source.py`, which **parametrizes over
  `store.py` by name** (`:27`) — confirmed live via `pytest --collect-only`. That is item 7.
- **Typecheck fan-out:** `mypy` covers `code_atlas` (`pyproject.toml`), so `store.py` gaining a real
  public API is type-checked at design-time cost zero — no other module annotates against it yet.
- **Conclusion:** exactly one existing test changes meaning (item 7, no edit needed) and none needs its
  assertion rewritten. `README.md` describes the DB only at the diagram level (`README.md:32`, already
  lists `nodes · edges · files · fts5 · meta`) and stays accurate, so it is deliberately **not** in the
  change-list.

**Rule compliance.**

- **R1.1** — no language branch; `files.language` is a column, never a predicate. Per `LESSONS.md:6-16`
  every docstring in `store.py` keeps `language` **before** `match` (notably: the phrase "schema matches
  §10" must not precede the word `language` on one line), and the gate's exact regex is re-run locally
  before the PR.
- **R1.2 / R7.4** — no protocol, factory, or migration runner. One class, one backend.
- **R1.3 / R1.4** — `store.py` imports `contract` only, and nothing parsing-related; adapters are PHP
  subprocesses, so the forbidden import direction is structurally impossible today (recorded as 0/0, not
  claimed as proven — item 6).
- **R3.1 / R3.2** — no vocabulary change ⇒ `CONTRACT_VERSION` stays 1. Field lists imported, never
  re-typed; enforced by the pre-existing guard (item 7) *and* the introspection test (item 5).
- **R4.1 / R4.2 / R4.3** — no network or LLM; determinism with the Q3 carve-out; one connection = one
  writer, WAL, every read indexed and `limit`-bounded.
- **R5.1 / R5.3** — a `parsed_ok=0` file row with zero nodes/edges persists (tested); a `schema_version`
  mismatch raises.
- **R6.1 / R6.4** — tests drive a real `GraphStore` over a temp DB file, no mocks; the new R4 guard is
  negative-controlled per `LESSONS.md:18-26`.
- **R7.5** — every comment ≤ 3 lines. **CONVENTION §2/§4** — `snake_case`, type hints on all public
  functions, SQL confined to `store.py`.
- **Uncodified standards untouched:** the absent DB-conventions rulebook section and the non-gated
  `ruff format` are **not** enforced here; they stay routed to `/mango:codify`.

### Verification plan (per-AC, layer-matched)

`SURFACES`: n/a (backend). Risk layer classified first, proof chosen to match.

| AC / requirement | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1a — schema matches §10 (14 objects, columns == `("id",) + contract fields`) | integration (a real DB must be created; wording *"persists"*) | integration — introspect `sqlite_master` + `PRAGMA table_info` on a temp DB file created by `GraphStore` | ✅ |
| AC1b — re-indexing replaces rows idempotently, incl. a **removed** symbol | integration | integration — index → re-index identical → assert equal ordered content; then re-index with a symbol dropped → assert the stale row is gone | ✅ |
| AC2a — FTS returns expected rows (≥10 named cases) | integration (fts5 is runtime behaviour; a mocked index proves nothing) | integration — every case asserted through a `MATCH` query, **never** `count(*)` (spike: `count(*)`=1 while `MATCH`=0 on an unpopulated index) | ✅ |
| AC2b — identical input → identical rows | integration | integration — two independent `GraphStore` builds over identical input under a **fixed injected clock**; compare ordered content with `nodes.id`/`edges.id` excluded (Q3) | ✅ |
| R1 — WAL + 5 indexes + pragma set | runtime/3p (SQLite decides, not our code) | integration — `PRAGMA journal_mode`/`foreign_keys`/`busy_timeout` read back on a **file** DB (spike: `:memory:` reports `memory`, so the test must use a real file) | ✅ |
| R2 — meta get/set over the 4 keys; `parsed_ok=0` with zero rows | logic + integration | integration — round-trip each key; assert a failed-parse file row persists with no nodes/edges | ✅ |
| R3 — 6 helpers bounded + deterministically ordered | integration | integration — each helper: correct rows, `limit` honoured, and stable order across two runs with equal-ranking rows present (spike showed ties are real) | ✅ |
| C1 / R3.2 — no re-declared field list | logic (static/AST property) | static — the pre-existing AST guard, now live on `store.py` (item 7), plus the introspection cross-check | ✅ |
| C2 / R4.2 — no wall-clock or ordering leak | integration | integration — fixed clock makes `updated_at` reproducible; the carve-out (ids excluded) is recorded, not silently skipped | ✅ |
| C4 / R4.3 — single writer, bounded reads | logic + integration | integration — one connection; every helper requires `limit`; assert no helper returns more than `limit` | ✅ |
| C5 / R5.3 — `schema_version` mismatch fails loud; FK delete order | runtime/3p | integration — open a DB whose `schema_version` is `"2"` → raises; delete a `files` row with nodes present → `IntegrityError` (spike-confirmed) | ✅ |
| R4 — only `store.py` touches SQLite | logic (static) | static, **negative-controlled** — assert `len(core_modules()) == 11` and exactly 1 contains SQL; inject a violation, confirm failure, remove it, confirm byte-identical | ✅ |
| Q8 — tokenizer behaviour (documented limitation) | runtime/3p | integration — assert `_` splits and camelCase does **not**, so the limitation is pinned in code | ✅ |

**No `❌` rows.** Deferred-with-record (not exclusions, because nothing in *this* ticket goes unproven):
camelCase FTS splitting → task 014 (Q8); the two uncodified standards → `/mango:codify`.

**Coverage-gap exclusions** *(one added at Phase 4 — the plan said "none" and that was wrong)*:

| Item | Risk tier | Why deferred | Follow-up |
|------|-----------|--------------|-----------|
| `busy_timeout=5000` and the "single writer" property under real contention. The pragma is set (`store.py:27`) but **nothing asserts it**, and no test opens two writers against one file. `busy_timeout` is per-connection and the store deliberately exposes no connection accessor, so a truthful assertion would mean adding an accessor purely for the test. | **low** — one `GraphStore` is one connection by construction, so contention cannot arise until a second writer exists | Concurrency arrives with task 009's worker fan-out, which is where a contention test belongs and where the single-writer boundary is actually load-bearing. Raised by the challenger as "can't tell"; recorded rather than argued away. | task 009 |

**Proving test.**

`tests/test_store.py::test_the_search_index_follows_a_per_file_replace`

Indexes one file containing `\App\UserRepo`, asserts `search_nodes("UserRepo")` returns it, re-indexes
the same path with that symbol **removed**, and asserts the search result is now empty **and**
`PRAGMA integrity_check`-equivalent `INSERT INTO nodes_fts(nodes_fts) VALUES('integrity-check')` is
clean. It sits at the integration layer, and it fails pre-change three separate ways: `store.py` has no
`GraphStore`; §10's external-content FTS returns 0 rows even once populated by plain inserts; and a
delete-blind implementation leaves the stale row searchable. Invocation:

```
pytest tests/test_store.py::test_the_search_index_follows_a_per_file_replace
```

Full suite via `config.test_command`: `pytest`.

**Rollback + porting.** Single repo (`app`), no porting. The change is additive — `store.py` is a stub
with zero importers, and both test files are new — so rollback is `git revert` of the branch commit(s),
or `git checkout main -- code_atlas/store.py docs/PLAN.md docs/CONVENTION.md` plus deleting the two new
test files. No data migration exists to undo: `.code-atlas/graph.db` is a gitignored derived cache, and
any DB written by this branch is discarded by the `schema_version` check or by deleting the file.

**SCOPE confirmed: M** — unchanged from analysis. One new module, two new test files, three doc edits;
the change-list did not grow past the analysis baseline (items 8–10 were already anticipated as C8), so
the *outgrew-its-ticket* nudge does not fire and the branch type stays `feat/004-sqlite-store`.

**Self-audit.**

- 10 change-list items, **every one traced to a matrix row**, `Ph2 covered by` filled `k/N` for all 15
  matrix rows.
- 10 assumptions tagged; **zero `novel-untested`** — each runtime/3p assumption was spiked in this phase
  with the result recorded above.
- Verification plan: 13 rows, risk layer classified before the proof, **no `❌`**, no coverage-gap
  exclusion needed.
- Proving test named, at the integration layer of the AC it proves, with the exact invocation and three
  named pre-change failure modes.
- Rollback + porting recorded. `DESIGN.md`: **n/a** (TRACK=backend). Surface proof manifest: n/a.
- **Gate 2 status:** waiting on user

## Phase 3 — Execute

- **Branch:** `feat/004-sqlite-store` (per `config.branch_strategy`)
- **Commits** (logical units, no AI co-author trailer):
  1. `8e01259` — *Add GraphStore: SQLite schema, per-file writes, bounded reads* (`code_atlas/store.py`,
     `tests/test_store.py`, `tests/test_sql_confinement.py` — change-list items 1–6)
  2. *Amend PLAN §10 and record the derived-column-list convention* (`docs/PLAN.md`,
     `docs/CONVENTION.md`, `docs/BACKLOG.md`, task frontmatter + this working doc — items 8–10)
- **Proving test added:** `tests/test_store.py::test_the_search_index_follows_a_per_file_replace` —
  green. It fails on the pre-change state at import (`store.py` had no `GraphStore`), and it fails on
  §10-as-written for the reason Gate 0 recorded: an external-content fts5 table returns 0 `MATCH` rows.
- **Test result vs `BASELINE: green`:** `pytest` → **162 passed, 1 skipped** (baseline was 86 passed);
  `ruff check .` clean; `mypy` → no issues in 11 source files. Both grep-gates re-run locally: R1.1 ok,
  R2.2 ok. The one skip is deliberate — see the R4 guard below.

**Verification sweep — BOTH axes.**

*Axis 1 — file set.* Zero stray references ✅ (`grep` for every symbol removed mid-implementation —
`_INSERT_NODE`, `_INSERT_EDGE`, `_NODE_PLACEHOLDERS`, `_EDGE_PLACEHOLDERS`, `_values`, `REPO_NODE`,
`SAVE_NODE` — returns nothing; `ruff --select F401,F841` clean) · diff ⊆ approved list ✅ (7 files, each
mapping to an approved item: `store.py`→1–4, `test_store.py`→5, `test_sql_confinement.py`→6,
`PLAN.md`→8, `CONVENTION.md`→9, `BACKLOG.md` + frontmatter→10; item 7 needed no edit, as designed) ·
each hunk maps to a matrix row ✅ · no untouched-line reformatting ✅ (`PLAN.md` is `+33/-3` with all
three removals intentional; `CONVENTION.md` `+4/-0`; `BACKLOG.md` `+1/-1`; the formatter was not run
over any file).

*Axis 2 — design-conformance self-check (per Gate-2 Approach bullet).*

| # | Approach bullet | Verdict |
|---|-----------------|---------|
| 1 | Schema as SQL text, field lists imported from `contract.py`; introspection cross-check | **deviated** (write path — see below) |
| 2 | Open sequence: 3 pragmas → DDL → `schema_version` check | implemented-as-approved |
| 3 | Per-file transactional writes; triggers carry FTS; `remove_file` deletes nodes before the files row | implemented-as-approved |
| 4 | Six bounded, totally-ordered reads; `search_nodes` quotes its term | implemented-as-approved |
| 5 | Injected clock; `built_at` written by the indexer via `set_meta` | implemented-as-approved |

**Design-conformance deviations** (surfaced to review for adjudication):

| Approved Gate-2 bullet | What was implemented instead | `path:line` | Surfaced to review |
|------------------------|------------------------------|-------------|--------------------|
| Bullet 1 — "the write path builds its column lists from `contract.NODE_FIELDS`/`EDGE_FIELDS`" (read as: one statement over **all** fields, absent ones bound as NULL) | One statement **per distinct present-field set**: a field absent from the row is left out of the INSERT so the column's §10 `DEFAULT` applies. Still derived from the contract tuples, still no literal field list. **Why:** the all-fields form bound an explicit NULL over `confidence_tier`, so every edge stored `NULL` instead of `'RESOLVED'` — §10's `DEFAULT` was dead and R5.2's tier logic would have read NULL tiers. Caught by `test_edges_by_source`. | `code_atlas/store.py:172` (`_insert`), `code_atlas/store.py:243` (`_grouped`) | yes |

**Design-invalidation / re-gate:** none. No approved premise turned out false; the deviation above is a
defect found *by* the approved verification plan, fixed inside the approved approach.

**Two findings worth recording (neither changes scope).**

1. **A partial `ORDER BY` silently reintroduced insert-order dependence — in the test helper, not the
   store.** `content()` first ordered edges by `source_qname, target_raw, line`, which is not a total
   order across two files, so the comparison fell back to rowid and the determinism test failed for the
   right reason. Fixed by ordering over **every** selected column
   (`tests/test_store.py:106-122`). The store's own `_EDGE_ORDER` was already total — this is why the
   design insisted on it.
2. **Process: `git checkout -- <file>` destroyed uncommitted work during the R3.2 negative control.**
   The second negative control appended a violating literal to `store.py`, then restored with
   `git checkout`, which reverted the file to the **committed stub** — the whole implementation was
   uncommitted at that point. It was rewritten from context and the implementation was committed
   **before** any further guard experiment. Durable lesson candidate for Phase 5.

**Negative controls run (LESSONS 002 — a guard that cannot fail is not evidence).**

| Guard | Injected violation | Result | Restored |
|---|---|---|---|
| R4 — `test_exactly_one_core_module_touches_sqlite` | `import sqlite3` appended to `code_atlas/config.py` | **FAILED** as required | `sha256` verified byte-identical |
| R3.2 — `test_consumer_does_not_redeclare_the_contract_vocabulary[store.py]` (item 7, pre-existing) | `COLUMNS = ["kind", "name", "qualified_name"]` appended to `code_atlas/store.py` | **FAILED** for `store.py` — the parametrization is now live, no longer vacuous | file rewritten and committed (see finding 2) |
| R4 — adapters half | *not run* | **skipped, not passed** — `adapters/` holds only `.gitkeep`, so the guard is 0/0 and says nothing until task 006 | n/a |

## Phase 4 — Review ✋

- **reviewer verdict:** **not run — skipped by user decision** (2026-07-29, "chỉ chạy challenger thôi"),
  as in tasks 002–003. Recorded as a gap, not as an LGTM: no senior-reviewer pass exists for this diff.
- **Re-review path:** n/a (round 1).
- **challenger (ticket-blind) result:** **7 of 8 requirements met · 1 met-with-caveat · 0 not met · 1
  sub-item can't-tell.** Isolation held — it was given only the raw ticket (extracted to a scratchpad
  file, verified to contain no matrix/design text) plus `git diff main...feat/004-sqlite-store`, and it
  confirmed it never opened this working doc. It worked in a throwaway clone and left the checkout
  untouched.
- **security agent:** n/a (no auth, network, or user input; SQL is fully parameterised).

**Challenger findings and adjudication.**

| # | Finding | Verdict | Action |
|---|---------|---------|--------|
| 1 | **`nodes_au` (AFTER UPDATE) was never exercised.** Verified by mutation, not inspection: it replaced the trigger body with a reference to a nonexistent column and the **full suite still passed 162/1**. `replace_file_rows` only ever DELETEs then INSERTs, so nothing fired the trigger; `test_schema_object_is_created` proved the trigger *object* was registered and was being read as if it proved the trigger *body*. | **Accepted — a real self-reported-green.** | **Fixed:** `tests/test_store.py::test_the_update_trigger_keeps_the_search_index_in_step` fires `nodes_au` with a real rename and asserts the index moved with it plus a clean `integrity-check`. Re-ran the challenger's exact mutation against a **copy** of `store.py`: the new test now **fails with `OperationalError`**, so the mutation is killed. The trigger is kept rather than deleted (R7.4) because it closes the mirror invariant for a write path a later task may take — an FTS mirror with a hole desyncs silently. |
| 2 | **`busy_timeout` / two-writer contention is `can't tell`.** The pragma is set but nothing asserts it, and no test proves two writers serialise. | **Accepted.** | **Recorded as a coverage-gap exclusion** (risk tier low, follow-up task 009) — see the Phase-2 exclusions table. It also exposed an **overstated cell in my own bookkeeping**: matrix C3's `Ph3/4` claimed "WAL/FK/busy_timeout asserted" when `busy_timeout` was not asserted at all. Cell corrected. |
| 3 | `docs/CONVENTION.md`'s new rule binds `indexer.py`/`resolver.py`/`tools/`, which do not exist yet — forward-looking policy the ticket did not ask for. | **Traceable, not creep.** | It is approved change-list **item 9**, tracing to C1 (R3.2) and C8; `store.py` is its first consumer and R7.2 requires the convention be written where conventions live. No change. |
| 4 | `SchemaVersionError` goes beyond the literal ticket text. | **Traceable.** | Ratified at Gate 0 as **Q4** and traced to R2 (`schema_version` is a ticket-named meta key) + C5 (R5.3 fail-loud). No change. |
| 5 | The diff **changes `PLAN.md` §10 and claims conformance to the changed §10 in the same commit set** — a reader checking only "code matches §10" gets a tautology. The challenger independently traced each edit and judged all three **legitimate spec corrections**, not a bar-move. | **Accepted as a fair characterisation.** | No change to the edits — they were ratified at Gate 0 (Q1/Q2/Q4) *before* any code was written, and §10's own text now states each reason. Recorded here so the tautology is named rather than relied on. |
| 6 | The uniqueness relaxation has downstream consequences for the resolver (§8.2) that **task 004 does not own**, and a later reviewer should not assume they were re-litigated there. | **Accepted.** | Already stated in `PLAN.md` §10's amendment ("a qname lookup may return one *or more* candidates… a `HEURISTIC` multi-candidate"), which is the authoritative place task 011 will read. Flagged for the PR body so it is not discovered late. |

- **Scope reconciliation:** 7 files, all inside the approved change-list; the Phase-4 fix adds one test to
  `tests/test_store.py` (item 5), no new file. No reformatting of untouched lines. `SCOPE` stays **M** —
  the *outgrew-its-ticket* nudge does not fire.
- **Regression on Phase-1 callers:** none possible — `store.py` still has zero importers (indexer,
  resolver, tools, gitutil remain stubs), which is why the challenger's mutation testing was the only
  way to find finding 1.
- **Proving test result + "would it fail without the change?"** `test_the_search_index_follows_a_per_file_replace`
  green; it cannot pass pre-change (no `GraphStore`) nor on §10-as-written (0 `MATCH` rows). Judged
  against `BASELINE: green`: **163 passed, 1 skipped** (baseline 86 passed), `ruff check` clean, `mypy`
  clean, R1.1/R2.2 gates ok. **No new failure, no baseline exclusion needed.**
- **Layer-match re-confirmation:** every AC's proof still sits at its risk layer; the one new exclusion
  is recorded with an approver-visible reason and a follow-up, not left as a silent pass.
- **Frontend rubric:** n/a (TRACK=backend). **Proof manifest / surfaces:** n/a.
- `Ph3/4 proven by` filled `k/N` for all 15 rows — see matrix.
- **Clean?** **Qualified yes.** Challenger: 0 "not met" after finding 1 was fixed and findings 2/6
  recorded. No layer-match ❌ unresolved. k=N on every row, with one human-visible coverage-gap
  exclusion. Proving test green. **The honest caveat: no reviewer agent ran**, so "clean" here rests on
  the challenger plus the guards — it is not a two-critic verdict.
- **Reviewed at:** `79765b6` on `feat/004-sqlite-store` (the finding-1 fix commit) · reviewed files:
  `code_atlas/store.py`, `tests/test_store.py`, `tests/test_sql_confinement.py`, `docs/PLAN.md`,
  `docs/CONVENTION.md`, `docs/BACKLOG.md`, `docs/tasks/004_sqlite-store.md`. `finalise` must re-review if
  `HEAD` or the diff moves beyond this set.

## Phase 5 — Finalise ✋ final gate

- **Stale-review guard:** **not stale.** `git diff --name-only 79765b6..HEAD` ∪ worktree = **empty**;
  `HEAD` is `79765b6`, the reviewed commit. No non-exempt file sits beyond the reviewed set.
- **PR:** [#7](https://github.com/cuongdinhngo/code-atlas/pull/7) — opened from `/tmp/pr-004.md`, rendered from **`.github/pull_request_template.md`** (the project rule
  in `CLAUDE.md` names that template, so it is used in place of mango's generic `templates/pr.md`).
- **Project finalise-checklist:** `config.pr_checklist_path` is **null**, so the hook is formally
  skipped — but `.github/pull_request_template.md` carries a *Pre-PR self-check* that is exactly the
  checklist this step exists for. It was walked item by item anyway (results in the PR body).
  **Recommendation:** set `pr_checklist_path` to that template so the hook stops depending on a human
  remembering it.
- **Planned outward actions (each needs separate approval; nothing taken yet):**
  - [x] **DONE** — pushed `feat/004-sqlite-store` to `origin` (4 commits; `@{u}..HEAD` empty). This
        carried LESSONS + BACKLOG + this working doc to a shared ref **before** the PR was opened, so the
        durable lessons are not orphaned on a branch a merge would delete.
  - [x] **DONE** — PR [#7](https://github.com/cuongdinhngo/code-atlas/pull/7) opened against `main`
        via `gh`, body from `/tmp/pr-004.md`
  - [ ] tracker comment — **n/a**: `tracker.base_url` is the GitHub repo itself, so the PR *is* the
        tracker artifact; there is no second system to notify
  - [ ] tracker transition — **n/a** for the same reason; task status lives in `BACKLOG.md` +
        frontmatter, already synced to `in-progress`, and moves to `done` only after the PR merges
        (the pattern tasks 002/003 followed)
- **Follow-ups drafted (no ⚠ matrix row, but three items must not evaporate).** Deliberately **not**
  written into `docs/tasks/009*.md` / `014*.md` in this change: those files are outside the reviewed set,
  so editing them now would trip the stale-review guard for no benefit. They ride the PR body instead,
  and are offered as a separate follow-up change:
  1. **task 009** — assert `busy_timeout` and prove the single-writer boundary under real contention
     (the recorded coverage-gap exclusion); it becomes load-bearing when the worker fan-out lands.
  2. **task 014** — camelCase FTS splitting. Changing `tokenize=` forces a full index rebuild ⇒ a
     `schema_version` bump, which 014 can afford and 004 could not justify.
  3. **`/mango:codify`** — the two uncodified standards: the rulebook has **no DB-conventions section**
     though this was a schema change, and `ruff format` is applied by habit but is not CI-gated.
- **Durable lesson:** **two**, written to `docs/LESSONS.md` (a repo artifact, and they ride the
  branch-push above so they reach a shared ref rather than dying with the branch):
  1. *A schema object that exists is not a schema object that runs* — the `nodes_au` mutation finding,
     generalised to existence-vs-behaviour tests and to mutating on a copy to tell them apart.
  2. *`git checkout -- <file>` restores the committed state, so it deletes uncommitted work* — the
     negative-control incident, generalised to committing before guard experiments.
- **Revert path (corrected after the merge):** GitHub **fast-forwarded** #7 — `main` had no divergent
  commits — so there is **no merge commit** and `git revert -m 1 <merge-sha>` does not apply, unlike
  PRs #5/#6. Undo the whole task with `git revert --no-commit 8e01259..13ecd22 && git commit`, or revert
  a single commit from that range. That restores the doc files and returns `store.py` to its stub;
  nothing imports it, so no caller breaks. `.code-atlas/graph.db` is a gitignored derived cache — deleting it is the whole data rollback,
  and any DB this branch wrote is refused on open by the `schema_version` check.

---

## Cost ledger (descriptive — facts only, never auto-cuts)

Dispatch-only: this phase ran **0 subagents** (no Explore fan-out — the repo is 11 small core modules and
4 docs, all read directly; judgment work stays on the strong model). Main-loop spend is therefore
unmeasured by mango and must be read from the session transcript before the PR (see `rtk gain`), exactly
as tasks 002 and 003 recorded it.

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| 1 — Analysis | none (0 dispatch) | — | n/a — no dispatch; main-loop read from transcript at PR time | RTK expected (`.harness.json:25`); `rtk gain` at PR time |
| 4 — Review | `mango:challenger` (ticket-blind) | 1 | **78,095** (27 tool uses, 313 s) | RTK expected; `rtk gain` at PR time |
| 2 — Design | none (0 dispatch) | — | n/a — no dispatch; main-loop read from transcript at PR time | RTK expected; `rtk gain` at PR time |

## Decision log

| When | Decision | Why |
|------|----------|-----|
| 2026-07-29 | `work_doc_mode: embed` honoured (appended below the separator) rather than a `.work.md` sibling | `.harness.json:13` sets `embed` explicitly, and tasks 001–003 all embed; the separator keeps the raw ticket challenger-blind |
| 2026-07-29 | Three read-only SQLite spikes run during analysis (FTS5 availability, external-content behaviour, tokenizer) | Two blocking findings (Q1, Q2) are claims *about SQLite*, not about our code; asserting them without evidence would have shipped a schema that cannot satisfy AC2 |
| 2026-07-29 | `TIER: full` | SCOPE=M with four universal denominators > 1 (14 / 4 / 6 / 11); lite requires a single row and no universal requirement with N > 1 |
| 2026-07-29 | **Gate 0 cleared — all 9 recommendations ratified verbatim** ("ratify all") | Q1–Q3 were blocking §10 defects; Q4–Q9 pinned values and denominators the repo never carried. Inventory A grew 11 → 14 (FTS triggers), and `PLAN.md:251-269` is amended in this diff rather than diverging from the code |
| 2026-07-29 | Camelcase FTS splitting deferred to task 014, not solved here | Changing `tokenize=` needs a full FTS rebuild ⇒ a `schema_version` bump; task 014 owns search semantics and no search tool exists yet to measure against (Q8) |
| 2026-07-29 | The 2 uncodified standards (absent DB-conventions section, non-gated `ruff format`) are surfaced, not enforced | mango detects and surfaces; the human ratifies via `/mango:codify`. Until ratified neither may gate-block |
| 2026-07-29 | **Gate 2 design: DDL stays SQL text; only the column *lists* are derived from `contract.py`** | Full DDL generation needs a name→SQL-type map, and any such Python literal in `store.py` **fails the existing R3.2 guard** (`test_contract_sole_source.py:57`); putting it in `contract.py` leaks storage into the contract (R1.4). Introspection cross-checks the two representations instead |
| 2026-07-29 | `get_node(qname)` dropped from the helper set | No ticket requirement needs it; `read_symbol` is task 014's, and under Q1's relaxed key it would return a list anyway (R7.1/R7.4). Recorded so the omission reads as deliberate |
| 2026-07-29 | A second spike run **during design** (10 runtime assumptions) rather than deferring them to execute | Gate 2 may not pass with an unresolved novel-untested runtime assumption; three results changed the design — pragma ordering (`foreign_keys` is ignored inside a transaction), FK-enforced delete order, and empirical proof that `id` moves across an idempotent replace |
| 2026-07-29 | `SCOPE` stays **M**; branch stays `feat/004-sqlite-store` | Change-list did not exceed the analysis baseline (items 8–10 were already anticipated under C8), so the *outgrew-its-ticket* nudge does not fire |
| 2026-07-29 | Reviewer agent **skipped**, challenger only (user decision) | Recorded as a gap, not an LGTM: the clean verdict rests on one critic plus the guards, not two |
| 2026-07-29 | Keep `nodes_au` and **test** it rather than delete it as dead code | Nothing currently UPDATEs `nodes`, so R7.4 would argue for deletion — but an FTS mirror with a hole desyncs *silently* the first time a later task updates a row. Closing the invariant beats removing it |
| 2026-07-29 | `busy_timeout`/two-writer contention recorded as a **coverage-gap exclusion**, not asserted | A truthful assertion needs a connection accessor added purely for the test; contention cannot arise until task 009's fan-out exists |

## Session status

- **Last updated:** 2026-07-29
- **Current phase:** **CLOSED.** PR [#7](https://github.com/cuongdinhngo/code-atlas/pull/7) merged
  2026-07-29; status set to `done` here and in `BACKLOG.md` via `chore/004-status-sync`.
- **Next action:** task **005** (adapter protocol) or **009** (full-build indexer) — 009 now has its
  store dependency satisfied. Carry forward the three recorded follow-ups: the `busy_timeout`/contention
  proof into 009, camelCase FTS into 014, and `/mango:codify` for the two uncodified standards.
- **Blocked on:** nothing.
