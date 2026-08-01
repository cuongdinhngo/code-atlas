---
id: 011
slug: resolver
title: Cross-file edge resolver (M2)
phase: 1
milestone: M2
status: in-progress
depends_on: [009]
---

## Goal
Link bare edges to nodes, generically — no language branches (§8.2).

## Scope / Deliverables
- After all nodes exist: resolve `EXTENDS/IMPLEMENTS/USES_TRAIT/NEW/FuncCall` FQN `target_raw` → `nodes.qualified_name`, set `target_qname`, tier `RESOLVED`; leave NULL if external/vendor.
- Instance `CALLS` with unknown receiver → name-match across index: 1 candidate = `HEURISTIC`; many = top-N `HEURISTIC`; `$x->$m()` = `DYNAMIC`, unlinked.
- `INCLUDES`: literal path resolved relative to includer; variable = `DYNAMIC`.
- Honor `semantic_types` capability when present (pre-resolved edges kept as `RESOLVED`).

## Acceptance criteria
- Resolver contains **zero** `if language == …` (grep-gate).
- Known symbol → correct resolved caller chain on fixtures.

## References
Plan §8.2, §2 (LSP litmus).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 011 — Cross-file edge resolver (M2) (working doc)

- **Ticket:** 011 · [docs/tasks/011_resolver.md](011_resolver.md)
- **Type:** enhancement
- **Repo(s) / Porting:** `app` (`.`) only
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/N touched files under UI paths
- **TIER:** full
- **BASELINE:** green — `.venv/bin/pytest -q` → **375 passed** in 14.84s (untouched `958f949`)
  <!-- baseline exclusions: none -->
- **work_doc_mode:** `embed` → this doc lives below the separator in the ticket file itself.

---

## Phase 0 — Refine

`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: structured backlog card with native headers (`Goal`, `Scope / Deliverables`,
`Acceptance criteria`). Open product/standard choices are raised in *Clarifications* below.

---

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope / Deliverables, Acceptance criteria, References) | 4 decomposed | ROWS: C=8, R=5, G=1, AC=2`

*References* decomposes to **0 requirement rows** by design — it points at PLAN §8.2 and §2, consumed
as Ph1 evidence throughout. C rows carry no ticket header (the card has no *Constraint* section);
they come from the binding rulebook for this change type. The Scope bullet on instance `CALLS` is
**split one row per clause** (1-candidate / many-candidates / dynamic).

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | "Link bare edges to nodes, generically — no language branches (§8.2)." | Implement `code_atlas.resolver` as phase-2 edge linking: FQN/name/path → `nodes.qualified_name`, writing `target_qname` + `confidence_tier`. Zero language names or branches anywhere under `code_atlas/` (R1.1). | `code_atlas/resolver.py:1` — one-line stub only; `indexer.full_build` (`indexer.py:54-55`) deliberately skips the resolver | | | ❌ |
| R1 | Scope (clause 1) | "After all nodes exist: resolve `EXTENDS/IMPLEMENTS/USES_TRAIT/NEW/FuncCall` FQN `target_raw` → `nodes.qualified_name`, set `target_qname`, tier `RESOLVED`; leave NULL if external/vendor." | **FQN-resolution bucket:** for these edge kinds (plus any `CALLS` whose `target_raw` is already an FQN — StaticCall — see Q3), look up `target_raw` against indexed nodes. **One** matching node ⇒ `target_qname` + `RESOLVED`. **Zero** matches (vendor/external) ⇒ leave `target_qname` NULL. **Two or more** matches for the same qname across files ⇒ `HEURISTIC` top-N per PLAN §10 (not silently `RESOLVED`) — see Q4. Runs only after all nodes are stored. | No `nodes_by_qualified_name` read on `GraphStore` (`store.py:242-255` has `nodes_by_name` only); no edge UPDATE API; `test_indexer.py:246` asserts `target_qname is None` post-build | | | ❌ |
| R2 | Scope (clause 2a) | "Instance `CALLS` with unknown receiver → name-match across index: **1 candidate** = `HEURISTIC`" | `CALLS` edges already at tier `HEURISTIC` with method-name-only `target_raw` (e.g. `"put"`) → find `Method` nodes with that `name` index-wide. Exactly **one** ⇒ set `target_qname` to that method's qname, keep tier `HEURISTIC` (R5.2 — never upgrade a guess to `RESOLVED`). | PHP adapter emits this shape: `Visitor.php:112-115` | | | ❌ |
| R3 | Scope (clause 2b) | "…**many** = top-N `HEURISTIC`" | When >1 `Method` node shares the name, emit **up to N** linked `HEURISTIC` rows (or update the single bare row into N — design choice). **N is not codified** — see Q1. | No `N` in PLAN §8.2, rulebook, or config beyond `CA_MAX_RESULTS` (tool cap, `config.py:39`) | | | ❌ |
| R4 | Scope (clause 2c) | "`$x->$m()` = `DYNAMIC`, unlinked." | Edges already stored as tier `DYNAMIC` with a non-linkable `target_raw` stay unlinked; resolver must not overwrite them with a guess. | PHP adapter sets `DYNAMIC` on variable includes (`Visitor.php:170`); dynamic method calls are not emitted as edges today — N/A until adapter grows them | | | ❌ |
| R5 | Scope (clause 3) | "`INCLUDES`: literal path resolved relative to includer; variable = `DYNAMIC`." | For `INCLUDES` with literal `target_raw`, resolve path relative to the includer's `file_path` (repo-relative, POSIX), map to a `File` node qname (= path). Variable/dynamic includes (`confidence_tier='DYNAMIC'`) → leave unlinked. | PHP adapter: literal vs dynamic at `Visitor.php:162-171` | | | ❌ |
| R6 | Scope (clause 4) | "Honor `semantic_types` capability when present (pre-resolved edges kept as `RESOLVED`)." | When adapter handshake advertises `semantic_types`, edges that already carry `target_qname` + `RESOLVED` must be **left unchanged** — the resolver is a no-op for them (R1.6). PHP adapter does not use this today; proven via a unit/integration fixture with pre-resolved rows. | `contract.KNOWN_CAPABILITIES` (`contract.py:99`); PHP emits bare edges only (`test_php_adapter_server.py:276-282`) | | | ❌ |
| R7 | Scope (implicit) | *(PLAN §8.1 step 5 — deferred from task 009 Q4)* | **`full_build` must invoke the resolver** after steps 1–4 and meta write, before returning. Task 009 explicitly left this wire for 011. | `indexer.py:54-55`, `docs/tasks/009_full-build-indexer.md` Q4 | | | ❌ |
| AC1 | Acceptance criteria | "Resolver contains **zero** `if language == …` (grep-gate)." | Falsifiable: CI guardrails job (`ci.yml:91-101`) **and** `tests/test_core_is_language_agnostic.py` (stronger — no language *names* anywhere in core) both pass on the resolver diff. | Both gates green today on the stub; `resolver.py` has no branches yet | | | ❌ |
| AC2 | Acceptance criteria | "Known symbol → correct resolved caller chain on fixtures." | **Pinned (Q2):** after `full_build` on a new multi-file PHP fixture (≥2 files): (i) cross-file `EXTENDS` → `target_qname` set, tier `RESOLVED`; (ii) FQN `CALLS` → `RESOLVED`; (iii) one-candidate instance `CALLS` → `HEURISTIC` linked; (iv) `edges_by_target(callee)` returns the caller edge. One hop (task 013 owns multi-hop). | Existing fixtures are single-file (`tests/fixtures/php/namespaced.php`); no resolver tests exist | | | ❌ |
| C1 | rulebook §1 (R1.1/R1.4) | "Zero language branches in the core… `resolver.py` *links edges only*… Parsing code and storage code must never import each other." | Resolver orchestrates lookups + writes through `store.py`; it holds no SQL, no adapter imports, no language names. | `tests/test_sql_confinement.py`; `tests/test_core_is_language_agnostic.py` | | | ❌ |
| C2 | rulebook §3 (R3.2/R3.3) | "`contract.py` is the single source of truth… Adapters emit **bare** edges… cross-file linking is the core resolver's job." | Edge kinds and tiers come from `contract.py`; resolver fills `target_qname` only — never re-parses source. | `contract.REQUIRED_EDGE_FIELDS` omits `target_qname` (`contract.py:86-92`) | | | ❌ |
| C3 | rulebook §1 (R1.6) | "Richer data… advertised as a capability the core *may* use… degrades gracefully when absent." | Without `semantic_types`, resolver still runs the generic rules; with it, pre-resolved edges are preserved (R6). | | | | ❌ |
| C4 | rulebook §5 (R5.2) | "Unresolvable-but-static references are `HEURISTIC`; dynamic constructs… are `DYNAMIC`… Never silently link a guess as `RESOLVED`." | Instance `CALLS` name-match stays `HEURISTIC` even when linked; ambiguous multi-candidate FQN lookup is `HEURISTIC`, not `RESOLVED`. | PLAN §10:297-301 | | | ❌ |
| C5 | rulebook §4 (R4.2) | "Identical input → identical output." | Resolver output must be order-independent: stable tie-breaking when selecting top-N (e.g. by `qualified_name, file_path` — same keys `store.py:88` uses). | | | | ❌ |
| C6 | rulebook §6 (R6.1) | "resolver/store/indexer change → an integration test asserting resolved rows" | Minimum: new `tests/test_resolver.py` (unit + fixture-backed integration); update `test_indexer.py` proving post-build edges are linked. | 0 resolver tests today | | | ❌ |
| C7 | rulebook §7 (R7.2/R7.5) | "Keep the plan and backlog honest… Comments stay ≤ 3 lines." | Doc updates: BACKLOG status, task frontmatter, PLAN only if behaviour differs from §8.2 as written. | | | | ❌ |
| C8 | rulebook §8 (R8.2) | "Keep core dependencies minimal (FastMCP + stdlib-first)." | Resolver uses stdlib + existing store/contract only — no new deps. | | | | ✅ |

Status legend: ✅ done/proven · ⚠ deferred (needs follow-up ticket) · ❌ not met.

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| AC1 | "zero `if language == …`" | CI regex at `ci.yml:97` + pytest parametrization over all 13 core modules (`test_core_is_language_agnostic.py:56-63`) | **Y** | ✅ greppable + tested | none |
| AC2 | "Known symbol → correct resolved caller chain on fixtures" | **Pinned (Q2 ratified):** multi-file fixture; after `full_build`, assert specific `target_qname` + tier on `EXTENDS`, FQN `CALLS`, and one-candidate instance `CALLS`; assert `edges_by_target` returns the caller edge | **Y** (after pin) | ✅ falsifiable after Q2 | none — ratified Gate 1 |

**Uncodified-standard items** (detect-and-surface; route through `/mango:codify` if ratified):

1. **top-N for multi-candidate `HEURISTIC`** — PLAN §8.2 says "top-N" but names no N. `CA_MAX_RESULTS=50`
   (`config.py:39`, PLAN §11) caps **tool** results, not resolver fan-out. Until ratified, this must
   not silently gate-block.
2. **Multi-candidate FQN policy** — ticket prose reads like single-match ⇒ `RESOLVED`, but PLAN §10
   (`PLAN.md:297-301`) + R5.2 require `HEURISTIC` when the same qname exists in multiple files.
   Self-resolved toward PLAN (Q4 below); surfaced so design does not silently pick one winner.

## Inventory (universal "all/every/no" requirements)

### Inventory A — FQN-resolution edge kinds. **N = 5**

Per-item checklist — review confirms **each** kind, not just a count.

| # | Edge kind (`target_raw` shape) | Ph3/4 proven by | Status |
|---|--------------------------------|-----------------|--------|
| A1 | `EXTENDS` — class FQN | | ❌ |
| A2 | `IMPLEMENTS` — interface FQN | | ❌ |
| A3 | `USES_TRAIT` — trait FQN | | ❌ |
| A4 | `NEW` — class FQN | | ❌ |
| A5 | `CALLS` — function/static FQN (`FuncCall` / `StaticCall` in adapter terms) | | ❌ |

### Inventory B — instance `CALLS` resolution cases. **N = 3**

| # | Case | Expected tier | Ph3/4 proven by | Status |
|---|------|---------------|-----------------|--------|
| B1 | 1 method candidate index-wide | `HEURISTIC`, linked | | ❌ |
| B2 | Many method candidates | `HEURISTIC`, top-N linked | | ❌ |
| B3 | Dynamic receiver (`DYNAMIC` tier from adapter) | `DYNAMIC`, unlinked | | ❌ |

### Inventory C — `INCLUDES` cases. **N = 2**

| # | Case | Ph3/4 proven by | Status |
|---|------|-----------------|--------|
| C1 | Literal path, resolved relative to includer | | ❌ |
| C2 | Variable path (`DYNAMIC`) | | ❌ |

### Surface inventory

`SURFACES: N/A` — `TRACK: backend`.

## Clarifications

`CLARIFICATION: 8 raised | 8 self-resolved (cited) | 0 for human decision`

**Self-resolved (with citation):**

| # | Question | Resolution | Citation |
|---|----------|------------|----------|
| Q3 | Ticket says `FuncCall`; contract edge kind is `CALLS` — which edges get FQN resolution? | All `CALLS` edges whose `target_raw` is already a resolvable FQN (FuncCall **and** StaticCall). Method-name-only instance calls fall under R2–R4. | `Visitor.php:116-123`; PLAN §8.2 lists `FuncCall` as PHP terminology |
| Q4 | Same qname in two files — `RESOLVED` or `HEURISTIC`? | **`HEURISTIC` top-N**, never pick-one `RESOLVED`. | PLAN §10:297-301; R5.2 |
| Q5 | Does 011 wire `full_build` → resolver? | **Yes.** Task 009 deferred step 5 to this card. | `docs/tasks/009_full-build-indexer.md` Q4; PLAN §8.1 step 5 |
| Q6 | Does resolver touch `IMPORTS`? | **No** — not in ticket scope; stays bare until contract v2 / TS adapter. | ticket Scope; PLAN §4.4 |
| Q7 | Where does SQL for edge updates live? | **`store.py` only** — resolver calls new store methods; no SQL in `resolver.py`. | R1.4; `tests/test_sql_confinement.py` |
| Q8 | Dependency 009 satisfied? | **Yes** — BACKLOG marks 009 `done`; `full_build` exists and is tested. | `docs/BACKLOG.md:21` |
| **Q1** | What is N for "top-N `HEURISTIC`"? | **Reuse `config.max_results`** (`CA_MAX_RESULTS`, default **50**). No new knob. | Gate 1 ratified 2026-08-01 |
| **Q2** | Pin AC2 "caller chain on fixtures" | After `full_build` on a **new multi-file PHP fixture** (≥2 files): (i) cross-file `EXTENDS` → `RESOLVED`; (ii) FQN `CALLS` → `RESOLVED`; (iii) one-candidate instance `CALLS` → `HEURISTIC` linked; (iv) `edges_by_target(callee)` returns the caller edge. One hop only. | Gate 1 ratified 2026-08-01 |

## Cause / gap analysis

Enhancement — per-goal gap (current vs target):

| Goal | Current (`path:line`) | Target |
|------|----------------------|--------|
| Link bare edges generically | `code_atlas/resolver.py:1` — stub docstring only. `GraphStore` has reads but **no** `nodes_by_qualified_name`, **no** edge UPDATE. `full_build` returns with all `target_qname` NULL (`indexer.py:54-55`, `test_indexer.py:246`). | `resolve(store, …)` runs after indexing; edges carry `target_qname` + correct tier per §8.2. |
| Prove on fixtures | No `tests/test_resolver.py`. Single-file PHP fixtures cannot exercise cross-file linking. | Task-owned multi-file fixture + integration test (R6.1). |
| Zero language branches | Vacuously true (empty stub). | Implementation stays branch-free; CI + pytest guards stay green. |

**Handler / entry point:** `code_atlas.resolver.resolve` (name TBD in design) called from `indexer.full_build` after `_record_meta`.

**Blast radius:**
- **Primary:** `code_atlas/resolver.py`, `code_atlas/store.py` (new read/update helpers), `code_atlas/indexer.py` (wire call).
- **Tests:** new `tests/test_resolver.py`; new multi-file fixture under `tests/fixtures/`; update `tests/test_indexer.py` (post-build edges linked).
- **Docs:** `docs/BACKLOG.md`, this task's frontmatter, possibly `docs/PLAN.md` if top-N policy is added to §8.2.
- **Dependents:** task **013** (nav tools read `target_qname`); task **016** (incremental re-run resolver); MCP tools unchanged until 013.
- **Guards that will react:** `test_core_is_language_agnostic.py` (13 modules); `test_sql_confinement.py` (store-only SQL); `test_contract_sole_source.py`.
- **Repos touched:** `app` (`.`) only.
- **`db-map`:** none (`.harness.json` `db_kind: null`).

## Rule-section coverage

`RULE SECTIONS: §1 (R1.1 ✅ · R1.2 N/A no new seam · R1.3 ✅ one-way deps · R1.4 ✅ resolver/store boundary · R1.5 ✅ LSP/no branches · R1.6 ✅ semantic_types) · §2 (R2.1–R2.3 N/A — no adapter source change) · §3 (R3.1 N/A no contract bump · R3.2 ✅ · R3.3 ✅) · §4 (R4.1 ✅ · R4.2 ✅ stable ordering · R4.3 N/A single-writer unchanged) · §5 (R5.1 N/A · R5.2 ✅ tier discipline · R5.3 N/A) · §6 (R6.1 ✅ integration tests · R6.2 ✅ spec-driven fixtures · R6.3 N/A · R6.4 ✅ grep-gates · R6.5 N/A) · §7 (R7.1 ✅ smallest useful · R7.2 ✅ · R7.3 ✅ · R7.4 ✅ · R7.5 ✅) · §8 (R8.1 N/A · R8.2 ✅ · R8.3 N/A) · CONVENTION §3 ✅ qname shape · §4 ✅ SQL in store only · DB-conventions N/A (no schema migration)`

## Phase 1 — Analysis ✋ Gate 1

- **Root cause / gap:** resolver never implemented; store lacks link APIs; indexer skips step 5 (table above).
- **Handler:** `resolver.resolve` ← `indexer.full_build`.
- **Blast radius:** see above — backend-only, 3 core modules + tests/fixtures.
- **Self-audit:** 4 sections decomposed; AC1 falsifiable; AC2 pinned via Q2; baseline green; inventories N=5+3+2; RULE SECTIONS emitted; TRACK/TIER/SCOPE declared; multi-clause CALLS split (R2–R4); `j = 0`.
- **Gate 1 status:** **cleared** — Q1 (`max_results`) + Q2 (AC2 pin) ratified 2026-08-01

## Phase 2 — Design ✋ Gate 2

### Approach

One pure function `resolve_edges(store, *, max_candidates: int) -> None` in `resolver.py`.
`full_build` calls it once after `_record_meta`, passing `config.max_results` (Q1).

Per unresolved edge (`target_qname IS NULL`), in stable order:

1. **Skip** `confidence_tier == DYNAMIC` (leave unlinked).
2. **Skip** edges whose `target_qname` is already set — this *is* how `semantic_types` is honored
   without reading capability flags (R1.6): pre-linked rows stay `RESOLVED`; bare rows still resolve.
3. **`INCLUDES`:** resolve `target_raw` as a POSIX path relative to the includer's `file_path`
   directory; look up a `File` node whose `qualified_name` equals that path; 1 hit → link
   `RESOLVED`; 0 → leave NULL.
4. **FQN kinds** (`EXTENDS` / `IMPLEMENTS` / `USES_TRAIT` / `NEW` / `CALLS`): look up
   `nodes.qualified_name == target_raw` (may return 0..N per PLAN §10).
   - 1 → set `target_qname`, tier `RESOLVED`
   - 0 + kind `CALLS` + tier already `HEURISTIC` → **name-match** `Method` nodes by `name == target_raw` (instance call)
   - 0 otherwise → leave NULL (external/vendor)
   - \>1 → link top-`max_candidates` as `HEURISTIC` (update the original edge to candidate[0];
     insert sibling edges for candidates[1..N-1] sharing source/kind/target_raw/file/line)
5. **Instance name-match:** 1 → update edge, keep `HEURISTIC`; many → same top-N expand as above;
   0 → leave NULL.

Candidate order is always `qualified_name, file_path` (same keys as `_NODE_ORDER`) so output is
deterministic (R4.2). SQL stays in `store.py`; the resolver only calls store methods (R1.4).

### Rejected alternatives

1. **Resolve inside `replace_file_rows` / per-file as results arrive** — rejected: targets in other
   files may not exist yet (PLAN §8.2 "after all nodes exist"; R3.3).
2. **New knob `CA_RESOLVER_MAX_CANDIDATES`** — rejected at Gate 1 (Q1): reuse `max_results`.
3. **Pick one winner on multi-candidate FQN and mark `RESOLVED`** — rejected by PLAN §10 + R5.2.
4. **Branch on `capabilities.semantic_types`** — rejected: checking a flag that names a future
   adapter's power is unnecessary; "already linked → leave alone" is language-agnostic and sufficient.
5. **Put UPDATE SQL in `resolver.py`** — rejected by R1.4 / `test_sql_confinement.py`.

### Assumptions

| Assumption | verified / novel-untested | Resolution |
|------------|---------------------------|------------|
| A1 | Adapter MethodCall edges arrive as `CALLS` + `HEURISTIC` + bare method `target_raw` | **verified** | `Visitor.php:112-115` |
| A2 | FuncCall/StaticCall arrive as `CALLS` with FQN `target_raw` and default/`RESOLVED` tier | **verified** | `Visitor.php:116-123` |
| A3 | File nodes use the repo-relative path as `qualified_name` | **verified** | `contract.py:13`; `Visitor.php:45` |
| A4 | `UNIQUE(qualified_name, file_path)` can yield multiple nodes for one qname | **verified** | PLAN §10; `test_store.py:213` |
| A5 | Expanding one bare edge into N sibling rows is safe under `replace_file_rows` re-runs (delete-then-insert bare, then resolve again) | **verified** | `store.replace_file_rows` deletes all edges for the path first |
| A6 | Relative include path join + `..` collapse via `PurePosixPath` is enough (no OS `realpath`) | **novel-untested** (stdlib path logic) | Covered by a **unit** proof that seeds an `INCLUDES` edge + File node and asserts the linked path — fails if join/normalize is wrong |
| A7 | Existing `test_indexer` EXTENDS→`Base` stays `NULL` after resolve (Base not in that fixture) | **verified** | `namespaced.php` has no `Base` declaration |

No unresolved novel-untested **third-party/runtime** assumption. A6 is stdlib path arithmetic proven by unit test.

### Smallest change list

| # | Change | File / area | Ph2 covered by | k/N |
|---|--------|-------------|----------------|-----|
| 1 | Implement `resolve_edges(store, *, max_candidates)` — FQN / name-match / INCLUDES / DYNAMIC skip / pre-linked skip / top-N expand | `code_atlas/resolver.py` | G1, R1–R6, C1–C5 | 0/11 |
| 2 | Store APIs: `nodes_by_qualified_name`, `unresolved_edges`, `link_edge`, `insert_edge` (or equivalent minimal set); SQL only here | `code_atlas/store.py` | R1, R3, C1, C2, Q7 | 0/5 |
| 3 | Wire `resolve_edges(store, max_candidates=config.max_results)` after `_record_meta` in `full_build`; update docstring | `code_atlas/indexer.py` | R7, G1 | 0/2 |
| 4 | Multi-file PHP fixture (≥2 files): Base, Repo::put, helper(), User extends+calls | `tests/fixtures/php/resolve/` | AC2, R1, R2, inventory A/B | 0/4 |
| 5 | Proving + unit tests: integration over fixture; units for multi-candidate, INCLUDES, DYNAMIC, pre-linked | `tests/test_resolver.py` | AC1, AC2, R1–R6, C6, inventories A–C | 0/10 |
| 6 | Store unit coverage for the new read/write helpers | `tests/test_store.py` | item 2 | 0/1 |
| 7 | **Proof collateral** — reword EXTENDS assertion comment (Base still external → still NULL; no longer "resolver not run") | `tests/test_indexer.py:244-246` | blast radius / A7 | 0/1 |
| 8 | PLAN §8.2: pin top-N = `CA_MAX_RESULTS` / `max_results` | `docs/PLAN.md` | Q1, C7, R7.2 | 0/1 |
| 9 | BACKLOG 011 → in progress/done + token row at finalise; task frontmatter status | `docs/BACKLOG.md` + this file | C7 | 0/2 |

**Test blast-radius trace (mechanical).**

- `grep -rn 'target_qname is None' tests/` → **one hit**: `test_indexer.py:246` (item 7). Assertion **still holds** (external Base); comment must change so the intent stays true.
- `grep -rn 'resolve_edges\|resolver\.py\|from code_atlas.resolver' tests/ code_atlas/` → **zero** production callers today; only the stub docstring. New call site is item 3 only.
- `nodes_by_qualified_name` / `link_edge` / `unresolved_edges` — **new symbols**, no existing consumers.
- Module count guards (`== 13`) — **unchanged** (`resolver.py` already exists).
- Fake adapter emits **no edges** → MCP/indexer fake-path tests unaffected by linking.
- `test_contract_sole_source` / language-agnostic / SQL confinement — react only if we put SQL or language names in the wrong module; design forbids that (no count bump).

### Rule compliance

- **R1.1 / R1.5** — no language tokens or `if language ==` in resolver/indexer/store changes; existing pytest + CI gates remain the proof (AC1).
- **R1.4** — resolver links only; store persists/queries only; no cross-imports of parse code.
- **R1.6** — pre-linked edges left alone (= honor `semantic_types` without requiring the flag).
- **R3.2 / R3.3** — field lists from `contract`; adapters still emit bare edges; core fills `target_qname`.
- **R4.2** — stable candidate order; expand inserts are deterministic.
- **R5.2** — never upgrade a name-match or multi-candidate to `RESOLVED`; DYNAMIC stays unlinked.
- **R6.1 / R6.2** — integration test + spec-driven multi-file fixture (not a real app repo).
- **R7.2 / R7.5** — PLAN pin for top-N; comments ≤ 3 lines.
- **R8.2** — stdlib only (`pathlib.PurePosixPath`).
- **CONVENTION §3 / §4** — qname/`::` unchanged; SQL confined to `store.py`.

### Verification plan (per-AC, layer-matched)

| AC / req | Risk layer | Proof artifact | Layer-match? |
|----------|------------|----------------|--------------|
| AC1 (zero language branches) | logic (source text) | existing `test_core_is_language_agnostic` + CI grep-gate on the new resolver body | ✅ |
| AC2 (caller chain on fixtures) | integration | `test_resolver.py` proving test — real PHP adapter + multi-file fixture + `full_build` | ✅ |
| R1 / inventory A (FQN kinds) | integration + logic | proving test covers EXTENDS+FQN CALLS; unit seeds cover IMPLEMENTS/USES_TRAIT/NEW | ✅ |
| R2 (1-candidate HEURISTIC) | integration | proving test clause (iii) | ✅ |
| R3 (many → top-N HEURISTIC) | logic | unit: seed 3 Method nodes same name, `max_candidates=2` → 2 linked HEURISTIC edges | ✅ |
| R4 (DYNAMIC unlinked) | logic | unit: DYNAMIC edge stays `target_qname IS NULL` after resolve | ✅ |
| R5 (INCLUDES literal / variable) | logic | unit: literal path links to File qname; DYNAMIC include untouched | ✅ |
| R6 (pre-resolved kept) | logic | unit: edge with `target_qname` set beforehand unchanged | ✅ |
| R7 (wired into full_build) | integration | proving test goes through `full_build`, not a bare `resolve_edges` call alone | ✅ |
| C5 (R4.2 ordering) | logic | multi-candidate unit asserts stable qname/file order | ✅ |

No `❌` → **no coverage-gap exclusions.**

`SURFACES: N/A` — backend track.

### Proving test

`tests/test_resolver.py::test_full_build_resolves_a_known_caller_chain_on_fixtures`

- Build a temp repo from `tests/fixtures/php/resolve/` (≥2 PHP files) via real `adapters/php`.
- `full_build(...)` then assert Q2's four clauses.
- **Fails pre-change** (`resolve_edges` is a no-op / missing → `target_qname` stays NULL).
- **Passes post-change.** Invocation: `.venv/bin/pytest tests/test_resolver.py::test_full_build_resolves_a_known_caller_chain_on_fixtures -q`

### Rollback + porting

- Revert the feature branch / PR. DB is a derived cache — delete `.code-atlas/graph.db` and rebuild.
- **Porting:** `app` (`.`) only; no shared packages across `config.repos`.

### SCOPE confirmed

`SCOPE: M` — unchanged from analysis (resolver + store APIs + indexer wire + fixture + tests). Did not cross into L.

### Self-audit

- Every change-list item traces to a matrix row; blast-radius collateral item 7 included.
- Assumptions tagged; no unresolved novel-untested 3p/runtime.
- Verification plan has no `❌`.
- Proving test named at integration layer matching AC2.
- Rollback + porting recorded; SCOPE = M.

- **Gate 2 status:** **cleared** — user invoked `/mango:execute 011` (2026-08-01)

## Phase 3 — Execute

- **Branch:** `feat/011-resolver`
- **Commits:** logical units (store/resolver/indexer · tests/fixtures · docs)
- **Proving test added:** `tests/test_resolver.py::test_full_build_resolves_a_known_caller_chain_on_fixtures` — green; full suite **386 passed**
- **Verification sweep — BOTH axes.**
  - *File axis:* diff ⊆ approved list ✅ · each hunk maps to a row ✅ · zero stray refs ✅
  - *Behaviour axis:* Approach bullets 1–5 `implemented-as-approved` ✅ (DYNAMIC skip, pre-linked skip, INCLUDES path, FQN + name-match, top-N expand)
- **Design-conformance deviations:** none
- **Design-invalidation / re-gate:** none
- **Fixture note:** proving fixture uses `\App\helper()` (FQN call) — unqualified `helper()` emits `\helper` from the adapter, which correctly stays unlinked as external

| Change-list # | Status |
|---------------|--------|
| 1 resolver.py | ✅ |
| 2 store APIs | ✅ |
| 3 indexer wire | ✅ |
| 4 php/resolve fixtures | ✅ |
| 5 test_resolver.py | ✅ |
| 6 test_store helpers | ✅ |
| 7 test_indexer comment | ✅ |
| 8 PLAN §8.2 top-N | ✅ |
| 9 BACKLOG + frontmatter in-progress | ✅ (token row at finalise) |

## Phase 4 — Review ✋ (stop only if not clean)

*(in progress — dispatched after commit)*

## Session status

- **Last updated:** 2026-08-01
- **Current phase:** 3 → 4 (execute complete; review next)
- **Next action:** commit change-set; dispatch reviewer + challenger
- **Blocked on:** none

## Decision log

| When | Decision | Why |
|------|----------|-----|
| 2026-08-01 | Gate 1 cleared: Q1 = reuse `max_results`; Q2 = AC2 pin as proposed | User: "approve" |
| 2026-08-01 | Design: skip-already-linked for semantic_types; HEURISTIC CALLS → name-match; top-N expand via sibling inserts | Smallest language-agnostic reading of §8.2 + R5.2 + R1.6 |
| 2026-08-01 | Gate 2 cleared | User: `/mango:execute 011` |
| 2026-08-01 | Fixture uses `\App\helper()` not bare `helper()` | Adapter NameResolver emits `\helper` for unqualified calls; FQN call is the honest RESOLVED path |
