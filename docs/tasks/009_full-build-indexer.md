---
id: 009
slug: full-build-indexer
title: Full build indexer + workers (M1)
phase: 1
milestone: M1
status: done
depends_on: [004, 005, 007]
---

## Goal
Index a whole repo end-to-end into SQLite (§8.1).

## Scope / Deliverables
- `indexer.full_build`: collect files (`git ls-files` per adapter extensions, minus ignores; walk fallback); reconcile vanished paths.
- Fan paths across N adapter processes (`min(cpu-2, 8)`); hash bytes; upsert `files`, replace `nodes`+bare `edges`. Single SQLite writer.
- Store `meta.last_commit`, `contract_version`, `built_at`; build `nodes_fts`.
- **CI:** pin `CA_WORKERS` in the fan-out tests instead of letting the default read the runner's core count — a hosted runner has fewer cores than a laptop, so an unpinned default makes worker-count assertions machine-dependent (R4.2). `git ls-files` is safe on the shallow clone CI checks out; `git diff` is not (see task 016).
- **Deadline for a hung adapter** (deferred here from task 005, Q5). A live-but-silent adapter blocks the driver's blocking read forever, at **`start()`** (waiting for the handshake) as well as at `parse()` — task 005 ships no protection either way. This task owns the fan-out, so it can bound a worker and kill it outright rather than paying for a per-request reader thread (`select` does not work on Windows pipes).

## Acceptance criteria
- Builds a small PHP repo to a queryable DB; re-run is idempotent.
- Single writer (no SQLite lock contention); worker count honors `CA_WORKERS`.
- A result rejected by `contract.validate()` sets `files.parsed_ok=0` and never breaks the stream (R5.1) — this closes the R5 integration-proof exclusion deferred from task 002.
- An adapter that never answers is killed and its files recorded as unparsed, rather than wedging the build — proven for **both** a silent boot and a silent reply. This closes task 005's recorded hung-adapter exclusion.
- The `busy_timeout` / two-writer contention proof deferred from task 004 lands here, where a real fan-out exists to contend.

## References
Plan §8.1, §4.1 (the wire rules and the deferred hang), §15 (M1). Carried exclusions: task 005 (hung adapter, both call sites), task 004 (`busy_timeout` contention).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Working doc — task 009

- **Key:** 009 · `docs/tasks/009_full-build-indexer.md`
- **Type:** enhancement (new core module — the build pipeline)
- **Repo(s) / Porting:** `app` (`.`) — single repo, no porting
- **SCOPE:** **L**
- **STRUCTURE:** native
- **TRACK:** backend — 0/N touched files under UI paths (this repo has no UI surface)
- **TIER:** full
- **BASELINE:** green — `pytest` **317 passed**; `ruff check .` clean; `mypy code_atlas` clean
  (untouched `b63397f`)
  <!-- baseline exclusions: none -->
- **work_doc_mode:** `embed` → this doc lives below the separator in the ticket file itself.

---

## Phase 0 — Refine

`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: the ticket is a structured, pre-written backlog card with native headers. The
decisions it leaves open are raised in *Clarifications* below and resolved under the user's standing
delegation ("if there is a question, take the best option for the project", 2026-07-31).

---

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope / Deliverables, Acceptance criteria, References) | 4 decomposed | ROWS: C=9, R=12, G=1, AC=7`

*References* decomposes to **0 requirement rows** by design: it points at PLAN §8.1/§4.1/§15 and the
two carried exclusions, all of which are consumed as Ph1 evidence throughout this matrix. C rows
carry no ticket header (the card has no *Constraint* section); they come from the binding rulebook
for this change type, per the step-11 rule-section coverage. Multi-clause bullets are **split one
row per clause** — the "Fan paths… hash bytes… upsert… Single SQLite writer" bullet alone is four
independent obligations.

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | "Index a whole repo end-to-end into SQLite (§8.1)." | One entry point, `indexer.full_build`, walking §8.1 steps 1–4 plus the FTS build. Step 5's *resolver* is **not** in this card (task 011) — see Q4. | `code_atlas/indexer.py` is a one-line stub naming this task | | | ❌ |
| R1 | Scope (b1, clause 1) | "collect files (`git ls-files` per adapter extensions, minus ignores…)" | `git ls-files` restricted to the suffixes the **handshakes announced** — never a literal suffix table in the core (R1.1) — then filtered through `ignore.load_ignore`. | `adapter.extension_index` (`adapter.py:254`) is the only suffix source; `ignore.load_ignore` (`ignore.py:66`) exists and is untested against a real collection | | | ❌ |
| R2 | Scope (b1, clause 2) | "walk fallback" | When `git ls-files` is unusable (not a repo / git absent), fall back to an `os.walk`-style traversal that prunes ignored **directories**. | `ignore.py:47` `is_ignored(..., is_dir=True)` exists precisely so a subtree can be pruned; nothing calls it | | | ❌ |
| R3 | Scope (b1, clause 3) | "reconcile vanished paths" | Every `files.path` in the DB that the collection no longer yields is dropped, with its nodes and edges. | `store.remove_file` (`store.py:181`) exists; **no store read lists the known paths** — a gap this task must close | | | ❌ |
| R4 | Scope (b2, clause 1) | "Fan paths across N adapter processes (`min(cpu-2, 8)`)" | N comes from `config.workers`, which already implements PLAN §8.1's `max(1, min(cpu-2, 8))` — the ticket omits the floor (see AC validation / Q1). | `config._default_workers()` (`config.py:104-106`); `os.cpu_count()` = 16 on this host → default 8 | | | ❌ |
| R5 | Scope (b2, clause 2) | "hash bytes" | A content hash of the file's **bytes** (not text) stored in `files.hash`, so task 016 can hash-skip an unchanged file. | `files.hash` column exists (`store.py:31`); `upsert_file` takes `file_hash` and nothing computes one | | | ❌ |
| R6 | Scope (b2, clause 3) | "upsert `files`, replace `nodes`+bare `edges`" | Per result: `upsert_file(path, hash, language, parsed_ok)` then `replace_file_rows(path, nodes, edges)`. Edges are stored **as the adapter gave them** — bare (R3.3); the core never fills `target_qname`. | `store.upsert_file` / `store.replace_file_rows` (`store.py:145,158`) are written and unit-tested, never driven end-to-end | | | ❌ |
| R7 | Scope (b2, clause 4) | "Single SQLite writer." | Parsing fans out; **writing does not**. Every `GraphStore` mutation happens on one thread (R4.3). | `store.py:3` states the intent; the exclusion carried from task 004 records that nothing proves it | | | ❌ |
| R8 | Scope (b3, clause 1) | "Store `meta.last_commit`, `contract_version`, `built_at`" | Three `meta` rows — a counted "for each of N=3", inventory A13–A15. `built_at` uses the store's **injectable** clock, so the wall-clock stays behind one seam (task 004's carve-out). | `store.META_KEYS` (`store.py:22`) already names all three plus `schema_version`; `set_meta` exists | | | ❌ |
| R9 | Scope (b3, clause 2) | "build `nodes_fts`" | The FTS index is consistent with `nodes` when the build returns. Triggers keep it current, so this is `rebuild_search_index()` once at the end — matching §8.1 step 5 rather than trusting the triggers silently. | `store.rebuild_search_index` (`store.py:203`) is documented "repair only"; the AFTER-INSERT trigger is `store.py:51` | | | ❌ |
| R10 | Scope (b4) | "**CI:** pin `CA_WORKERS` in the fan-out tests instead of letting the default read the runner's core count" | Every test that asserts anything about worker count or fan-out sets `CA_WORKERS` explicitly; a hosted runner has fewer cores than this 16-core host, so an unpinned default is machine-dependent (R4.2). | `config.py:106` reads `os.cpu_count()`; CI runs on `ubuntu-latest` (`ci.yml:14`) | | | ❌ |
| R11 | Scope (b5, clause 1) | "Deadline for a hung adapter … at **`start()`** (waiting for the handshake)" | A live-but-silent adapter must not block the handshake read forever. | `adapter.py:190` `_read_handshake` → `_read_line` → `process.stdout.readline()`, an unbounded blocking read | | | ❌ |
| R12 | Scope (b5, clause 2) | "…as well as at `parse()`" | Same deadline on the reply read. The ticket rules out a per-request reader thread (`select` does not work on Windows pipes) and says to "bound a worker and kill it outright". | `adapter.py:143` `_read_line` again; `fake_adapter.py:74-76` documents this exact hole as deferred to 009 | | | ❌ |
| AC1a | Acceptance criteria | "Builds a small PHP repo to a queryable DB" | End-to-end: a fixture tree → `full_build` → the store answers `nodes_by_name` / `search_nodes` / `edges_by_source` with the expected rows, and `meta` is populated. "Queryable" pinned in AC validation. | `tests/test_php_adapter_server.py` proves the driver+adapter pair; nothing yet writes their output to a DB | | | ❌ |
| AC1b | Acceptance criteria | "re-run is idempotent" | A second `full_build` over an unchanged tree produces identical row **content** ordered by a stable key, with `nodes.id`/`edges.id`/`files.updated_at` excluded — task 004's recorded determinism carve-out (Q6). | `store.py:7-9` records the carve-out; `replace_file_rows` deletes-then-inserts so content is replaceable | | | ❌ |
| AC2a | Acceptance criteria | "Single writer (no SQLite lock contention)" | Restates R7 as an assertion: during a `workers > 1` build, every store mutation is observed on exactly one thread. | as R7 | | | ❌ |
| AC2b | Acceptance criteria | "worker count honors `CA_WORKERS`" | With `CA_WORKERS=k`, **exactly k** adapter processes are booted for a repo with more than k files — countable via `fake_adapter.py`'s existing `CA_FAKE_BOOTLOG`. | `fake_adapter.py:12,63-66` already appends one line per boot — the counting mechanism exists | | | ❌ |
| AC3 | Acceptance criteria | "A result rejected by `contract.validate()` sets `files.parsed_ok=0` and never breaks the stream (R5.1) — this closes the R5 integration-proof exclusion deferred from task 002." | Two clauses in one: the row is written with `parsed_ok=0` **and** the next file still parses on the same boot. Closing 002's exclusion means the proof must run `contract.validate()` through the **real** indexer, not a unit call. | `adapter.py:237` already converts a rejected reply into a soft `ParseResult`; `docs/tasks/002_contract-schema.md:464` records the excluded integration half | | | ❌ |
| AC4 | Acceptance criteria | "An adapter that never answers is killed and its files recorded as unparsed, rather than wedging the build — proven for **both** a silent boot and a silent reply. This closes task 005's recorded hung-adapter exclusion." | A counted "for each of N=2" call sites, inventory B3/B4. "Rather than wedging" is the falsifiable half: the build **returns**. Disposition differs by call site — see Q5. | `docs/tasks/005_adapter-protocol.md:136-138` records the exclusion verbatim | | | ❌ |
| AC5 | Acceptance criteria | "The `busy_timeout` / two-writer contention proof deferred from task 004 lands here, where a real fan-out exists to contend." | A second writer against the same DB file waits out a held write lock instead of failing immediately — with a negative control at `busy_timeout=0`. | `store.PRAGMAS` (`store.py:27`) sets `busy_timeout=5000`; `docs/tasks/004_sqlite-store.md:567` records that **nothing asserts it** | | | ❌ |
| C1 | rulebook §1 (R1.1/R1.3/R1.4) | "Zero language branches in the core… store.py *persists/queries only*… Parsing code and storage code must never import each other." | `indexer.py` may name no language: every suffix and every `files.language` value comes from a handshake. It orchestrates `adapter` + `store`; it holds no SQL and opens no connection. | `tests/test_core_is_language_agnostic.py` bans the token `php` anywhere in `code_atlas/`; `tests/test_sql_confinement.py:49` asserts `store.py` is the **only** core module matching `sqlite3|SELECT|INSERT INTO|…` | | | ❌ |
| C2 | rulebook §4 (R4.2) | "Identical input → identical output… No wall-clock, randomness, or set-ordering leaking into stored data." | The hard one: fan-out makes **result arrival order** non-deterministic. Collection order must be sorted, and stored content must be order-independent under task 004's carve-out. | `store.py:79-82` full orderings; `store.py:7-9` names the three non-reproducible columns | | | ❌ |
| C3 | rulebook §4 (R4.3) | "Single SQLite writer. Concurrency is in parsing (N adapter workers), not in writing." | Restates R7/AC2a from the rulebook side; binding on the design, not just the test. | as R7 | | | ❌ |
| C4 | rulebook §5 (R5.1/R5.3) | "Fail loud on *config/programmer* errors…; fail soft on *data* errors." | The split this card must choose deliberately: a broken **configuration** aborts the build; a broken **file** or a broken **worker** does not. Q5 records where the line falls. | `adapter.py:26-28` `AdapterError` is the loud channel; `adapter.py:277` `_failure` the soft one | | | ❌ |
| C5 | rulebook §6 (R6.1) | "resolver/store/indexer change → an integration test asserting resolved rows" | The definition of done for this card is an **integration** test over a real fixture tree and real adapter subprocesses, not a mocked indexer. | R6.1's own wording names `indexer` explicitly | | | ❌ |
| C6 | rulebook §3 (R3.2) | "`contract.py` is the single source of truth… Store, indexer, and tools import from it; they never re-declare field lists." | `indexer.py` must not re-type a node/edge field list; it hands rows through opaquely. | `tests/test_contract_sole_source.py` fails a consumer that re-declares one | | | ❌ |
| C7 | rulebook §7 (R7.2/R7.5) | "A design decision updates the plan… Comments stay ≤ 3 lines." | A new `CA_*` knob (Q2) must land in PLAN §11 **and** CONVENTION §2, not only in `config.py`. All new comments ≤ 3 lines. | PLAN §11 lists the knob set; CONVENTION §2 lists the `CA_` env names | | | ❌ |
| C8 | rulebook §8 (R8.2) | "Keep core dependencies minimal (FastMCP + stdlib-first)." | Concurrency uses `threading` + `queue` + `hashlib` from the stdlib. No new dependency for a thread pool or a timeout. | `pyproject.toml` core deps unchanged | | | ✅ |
| C9 | rulebook §2 (R2.1–R2.3) | "Adapters implement the language specification… never encode a specific repo's… framework." | **N/A** — this card changes no adapter source. The only fixture it touches is `tests/fixtures/adapter/fake_adapter.py`, which is protocol-driven and language-free by construction, and sits outside the `adapters/` grep-gate. | `ci.yml:112` scopes the R2.2 gate to `adapters/` | | | ✅ |

Status legend: ✅ done/proven · ⚠ deferred (needs follow-up ticket) · ❌ not met.

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| R4 (worker count) | `min(cpu-2, 8)` | `max(1, min(cpu-2, 8))` — PLAN §8.1 spells the floor out ("the floor keeps a 1–2-core host at one worker") and `config.py:106` already implements it | **N** | measurable — `config.load_config(...).workers` | **Self-resolved Q1**, surfaced not silently corrected: the ticket drops the `max(1, …)` floor, which would yield **0 workers** on a 2-core host and **-1** on a 1-core host. The existing `config.workers` is authoritative; this card consumes it and adds no second formula. |
| AC1a ("queryable") | "a queryable DB" | Unmeasurable as an adjective. Pinned to: after `full_build`, (i) `nodes_by_name` returns the fixture's class node, (ii) `search_nodes` returns it through **fts5**, (iii) `edges_by_source` returns its bare edge with `target_qname` NULL, (iv) all four `meta` keys are set, (v) `files` has one row per collected path | **N** | measurable **after pinning** | Pinned definition proposed here and carried into the design's verification plan. A build that writes 0 rows would satisfy "no error" but not this. |
| AC1a ("small PHP repo") | "a small PHP repo" | The repo under test is a **fixture tree**, not a sample repo — R6.2 binds fixtures to language constructs, and R2.3 forbids a real repo defining correctness. Computed as: the existing `tests/fixtures/php/*.php` files driven through the **real** `adapters/php` subprocess | **Y** (compatible) | measurable — the assertion names the fixture files | none. Note the PHP-driven test must carry the same `needs_php` skip guard as task 007's, so `0 skipped` in CI stays the load-bearing evidence that the PHP path ran. |
| AC1b ("idempotent") | "re-run is idempotent" | Pinned to: run `full_build` twice over an unchanged tree; row **content** (ordered by `store`'s stable orderings) is byte-identical with `nodes.id`, `edges.id` and `files.updated_at` excluded — the carve-out `store.py:7-9` already records and task 004 already ratified | **N** | measurable **after pinning** | Pinned. Without the carve-out the AC is *unsatisfiable*: `nodes.id` is insert order and a delete-then-insert always renumbers. Surfaced rather than quietly asserting a weaker thing. |
| AC2a ("no lock contention") | "Single writer (no SQLite lock contention)" | Pinned to: during a `CA_WORKERS=4` build over ≥ 8 files, every `GraphStore` mutation is observed from **exactly one** `threading.get_ident()`, and that ident is the caller's | **N** | measurable **after pinning** | Pinned. "No contention" is an absence — unfalsifiable as stated; the positive form (one writer thread) is what the rulebook (R4.3) actually claims. |
| AC2b (`CA_WORKERS`) | "worker count honors `CA_WORKERS`" | Pinned to: `CA_WORKERS=k` over a tree of ≥ 2k files boots **exactly k** adapter processes, counted from `CA_FAKE_BOOTLOG` | **Y** | measurable — line count of the boot log | none. `fake_adapter.py` already writes that log (`fake_adapter.py:63-66`); no new mechanism needed. |
| AC3 | "sets `files.parsed_ok=0` and never breaks the stream" | Two clauses; both measurable. Computed addition: the proof must go through `full_build` (002's exclusion was specifically the **integration** half — `contract.validate()` was proven only as a unit call) | **Y** (with the integration qualifier) | measurable — `files.parsed_ok` = 0 for the bad path, = 1 for the next path, same boot | none — recorded so review checks the *layer*, not just the assertion. |
| AC4 | "killed … rather than wedging the build — proven for **both** a silent boot and a silent reply" | Both call sites are measurable, but the ticket does not name **the deadline**. There is no timeout value anywhere in the repo or rulebook | **N** — a missing number | **not falsifiable as written**; falsifiable once a number exists | **Q2** — an uncodified standard. Proposed: a new knob `CA_ADAPTER_TIMEOUT`, **default 30 s**, integer seconds. Resolved under the standing delegation; routed to `/mango:codify` for ratification, and it does **not** gate-block. |
| AC4 (disposition) | "its files recorded as unparsed" | At the **probe** boot — the one adapter started to learn its extensions — *zero* files are known yet, so "its files" is vacuous and the only honest outcome is a loud abort (R5.3) | **N** | measurable both ways | **Q5** — split recorded below: probe boot ⇒ loud; worker boot / silent reply ⇒ soft. |
| AC5 | "the `busy_timeout` … proof … lands here" | Pinned to: a competing connection holds `BEGIN IMMEDIATE`; a `GraphStore` write from another thread **blocks and then succeeds** once the lock is released; the **negative control** at `busy_timeout=0` raises `sqlite3.OperationalError`. Without the control the test passes on a machine where the lock is never actually contended | **N** | measurable **after pinning** | Pinned. Task 004 recorded that a truthful assertion looked like it needed a connection accessor; it does not — a second `GraphStore` and a raw competing connection *in the test* suffice, and `test_sql_confinement.py` scopes its SQL ban to `code_atlas/`, not `tests/`. |

**Uncodified-standard items** (detect-and-surface; not silently enforced, not silently dropped —
route through `/mango:codify` provisional→ratify if they should become rules):

1. **The rulebook still has no process/concurrency-management section** — the finding task 005 raised
   (`docs/tasks/005_adapter-protocol.md:146-151`) and nobody has codified. It now binds a **second**
   time and harder: this card must choose a timeout policy, a kill-vs-terminate policy, a
   thread-vs-process policy, and a worker-failure disposition. `docs/ENGINEERING_RULES.md` §1–§8
   covers none of them; `docs/CONVENTION.md` has no concurrency section either. Until ratified these
   do **not** gate-block.
2. **`ruff format` is applied by habit but is not a codified standard.** CI runs `ruff check` only
   (`ci.yml:47-48`); `ruff format --check .` reports **6 files** unformatted on untouched `main` — up
   from **4** at task 005 and **2** at task 004, so the drift keeps growing. Not a baseline failure,
   must not gate-block; if the formatter should be binding, codify it and add it to CI as its own
   change (a candidate for task 024's successor).
3. **A default timeout value is a going-forward standard being chosen for the first time** (Q2). 30 s
   is proposed as generous-but-bounded, not derived from a rule.

## Inventory (universal "all/every/no" requirements)

### Inventory A — the `full_build` obligations. **N = 16**

The denominator comes from **PLAN §8.1's steps plus the three carried exclusions**, not from the
ticket's five bullets — the ticket's prose is a hint, never the denominator. Each row is confirmed
individually at review; an aggregate `k/N` is not enough.

| # | Obligation | Ph1 state (measured) | Ph3/4 proven by | Status |
|---|------------|----------------------|-----------------|--------|
| A1 | Collect via `git ls-files`, restricted to the suffixes the handshakes announced | nothing collects | | ❌ |
| A2 | Apply built-ins + `.gitignore` + `.codeatlasignore` to the collected set | `ignore.load_ignore` never called by production code | | ❌ |
| A3 | Walk fallback when `git ls-files` is unusable (not a repo / git absent) | absent | | ❌ |
| A4 | Collection order is deterministic — sorted, repo-relative, POSIX separators | absent (R4.2, CONVENTION §3) | | ❌ |
| A5 | Reconcile: a vanished path loses its `files` row **and** its nodes/edges | `store.remove_file` exists; no caller, no path listing | | ❌ |
| A6 | Fan paths across N adapter **processes**, N from `config.workers` | absent | | ❌ |
| A7 | Worker count honors `CA_WORKERS`; fan-out tests pin it rather than reading the runner's cores | `config.py:106` reads `os.cpu_count()` (= 16 here, fewer on CI) | | ❌ |
| A8 | A content hash of the file's **bytes** is stored in `files.hash` | column exists, always written by hand in tests | | ❌ |
| A9 | `files.language` is the adapter's **announced** name, never a literal | `upsert_file` takes it as an argument | | ❌ |
| A10 | Per file: nodes + **bare** edges replaced, so a re-run is idempotent | `replace_file_rows` exists; no caller | | ❌ |
| A11 | Single SQLite writer — every mutation on one thread | asserted nowhere (task 004's exclusion) | | ❌ |
| A12 | `busy_timeout` proven under **real** contention, with a negative control | `store.py:27` sets it; nothing asserts it | | ❌ |
| A13 | `meta.last_commit` stored | `META_KEYS` names it; never written | | ❌ |
| A14 | `meta.contract_version` stored | as above | | ❌ |
| A15 | `meta.built_at` stored, from the store's **injectable** clock | as above | | ❌ |
| A16 | `nodes_fts` consistent with `nodes` when the build returns | triggers maintain it; unproven end-to-end | | ❌ |

### Inventory B — the failure obligations. **N = 6**

| # | Obligation | Loud or soft (R5.1/R5.3) | Ph3/4 proven by | Status |
|---|------------|--------------------------|-----------------|--------|
| B1 | An `ok:false` result → `files.parsed_ok=0`, the next file still parses on the same boot | soft | | ❌ |
| B2 | A result **rejected by `contract.validate()`** → `parsed_ok=0`, stream continues (closes 002) | soft | | ❌ |
| B3 | A **worker** adapter that never announces → killed at the deadline; the build returns and no path is silently lost | soft | | ❌ |
| B4 | An adapter that never **answers** → killed at the deadline; that file `parsed_ok=0`; the build returns | soft | | ❌ |
| B5 | The **probe** adapter never announces → loud `AdapterError`, no hang (Q5: zero files are known yet) | **loud** | | ❌ |
| B6 | An adapter that **exits** mid-stream → its in-flight file `parsed_ok=0`, the build still returns | soft at build level | | ❌ |

### Surface inventory

`SURFACES: N/A` — `TRACK: backend`; this repo has no UI surface, so the frontend gates (M1–M10) and
the proof manifest are inert for this card.

## Clarifications

`CLARIFICATION: 10 raised | 10 self-resolved (cited) | 0 for human decision`

Four of these (Q2, Q5, Q7, Q9) are genuine standard/product choices rather than lookups. They are
resolved under the user's **standing delegation** — *"a approval luôn các gates đó, nếu có câu hỏi gì
cứ làm theo gợi ý tốt nhất cho dự án"* (2026-07-31) — and are surfaced here in full so the delegation
is exercised visibly, not silently. **Gate 0 is cleared by that delegation, with `j = 0`.**

| # | Question | Resolution | Cited source |
|---|----------|------------|--------------|
| Q1 | Is the worker count `min(cpu-2, 8)` or `max(1, min(cpu-2, 8))`? | The floored form. Consume `config.workers`; add no second formula. | PLAN §8.1; `config.py:104-106` |
| Q2 | **What is the hung-adapter deadline, and where does it live?** | A new knob **`CA_ADAPTER_TIMEOUT`**, integer seconds, **default 30**. A knob, not a constant, because R10/R4.2 require CI to pin it and because §11 already has the derive-env-name-from-key machinery. Surfaced as an uncodified standard. | PLAN §11; `config.KNOB_KEYS` (`config.py:26-33`); `config._as_int` already rejects `< 1` |
| Q3 | Where does `git rev-parse HEAD` live — `indexer.py` or `gitutil.py`? | `gitutil.py`. This card fills it with the two **read-only** helpers it needs (`ls_files`, `head_commit`); task 016 adds `git diff` on top. Putting `subprocess.run(["git", …])` in `indexer.py` would give that module a second reason to change (R1.4). | CONVENTION §1 layout; `gitutil.py:1` "filled in task 016" |
| Q4 | Does `full_build` run the resolver (§8.1 step 5)? | **No.** `resolver.py` is task 011's card and this ticket's Scope never names it. `full_build` stops after the FTS build; 011 wires the call in. | `resolver.py:1`; `docs/BACKLOG.md` task 011 |
| Q5 | **A hung adapter: loud or soft?** | **Split by call site.** The **probe** boot (the one adapter started to learn its extensions) is a *configuration* failure — zero files are known, so "record its files unparsed" is vacuous — and raises `AdapterError` (R5.3). A **worker** boot or a silent **reply** is a *runtime* failure of one process among N: kill it, record what it owed as unparsed, let the build return (the ticket's "rather than wedging the build"). | R5.3; ticket AC4; `adapter.py:190-208` already treats a bad handshake as loud |
| Q6 | Fan-out makes result **arrival order** non-deterministic — does that break R4.2? | No, under task 004's **already-ratified** carve-out: `nodes.id`, `edges.id` and `files.updated_at` are declared non-reproducible, and determinism is asserted over row content ordered by a stable key. Collection order is still sorted so *which* files are parsed is deterministic. | `store.py:7-9`; `store.py:79-82` |
| Q7 | **How does a watchdog unblock a worker parked in `readline()`?** | Add a narrow **`SubprocessAdapter.kill()`** that kills the child; the blocked read then returns `""` and the existing `_read_line` raises `AdapterError`. It is **not** added to the `LanguageAdapter` Protocol: a deadline is a *driver* concern, not a language capability, and a one-implementer Protocol method is exactly R7.4's dead abstraction. `stop()` is not reused for this — it closes `stdout` under the reader and races into `ValueError`. | R1.2, R7.4; `adapter.py:45-72` (the Protocol), `adapter.py:221-231`, `adapter.py:282-299` |
| Q8 | `GraphStore` cannot list known paths, and `built_at` needs the store's clock. | Add two reads to `store.py`: `file_paths()` and a public `now()`. Both belong there — R1.4 makes `store.py` the only module that may touch SQLite, and the clock already has exactly one injection point. | R1.4; `store.py:111-118`, `test_sql_confinement.py:49` |
| Q9 | **After a parse timeout, does the worker restart or retire?** | **Restart once per timeout and continue**; a *boot* timeout retires the worker. This terminates (a boot that hangs ends the worker; a per-file hang costs one deadline per file over a finite file list) and does not hand a whole repo to `parsed_ok=0` when `CA_WORKERS=1`. Retiring on every timeout was rejected for that reason. | ticket AC4 ("rather than wedging the build"); ticket b5 ("bound a worker and kill it outright") |
| Q10 | What happens to a file no adapter claims? | It is never collected, so it is never recorded — §8.1 step 1 collects "per adapter's extensions". A `.md` file in the repo produces no `files` row. | PLAN §8.1 step 1 |

## Cause / gap analysis

Enhancement — per-goal gap, current vs target:

| Goal | Current (`path:line`) | Target |
|------|----------------------|--------|
| Index a whole repo into SQLite | `code_atlas/indexer.py:1` — a one-line stub. Every part exists in isolation and **nothing joins them**: `store.py` is unit-tested with hand-written rows, `adapter.py` is driven file-by-file in tests, `ignore.py` has no production caller, `gitutil.py` is a stub. | One `full_build(config)` that walks §8.1 steps 1–4 + FTS, with N worker threads over N adapter processes and one writer thread. |
| Survive a hung adapter | Absent at **both** call sites — `adapter.py:190` and `adapter.py:143` both bottom out in an unbounded `process.stdout.readline()`. `fake_adapter.py:74-76` names the hole in a comment and routes it here. | A watchdog that kills the child at `CA_ADAPTER_TIMEOUT`, turning a hang into the `AdapterError` the driver already handles. |
| Close three carried exclusions | 002's R5 integration half (`docs/tasks/002_contract-schema.md:464`), 005's hung adapter (`docs/tasks/005_adapter-protocol.md:136`), 004's `busy_timeout` (`docs/tasks/004_sqlite-store.md:567`) — all three explicitly name task 009 as the follow-up. | All three asserted here, each with a negative control. |

## Blast radius

- **Entry point:** `code_atlas.indexer.full_build` — new; no caller yet. Task 010 (`get_index_status`,
  `build_or_update_index`) and task 016 (incremental) are its future callers.
- **Files touched (predicted):** `code_atlas/indexer.py` (new body), `code_atlas/gitutil.py` (new
  body), `code_atlas/config.py` (+1 knob), `code_atlas/store.py` (+2 reads),
  `code_atlas/adapter.py` (+`kill()`), `tests/fixtures/adapter/fake_adapter.py` (+hang modes),
  a new `tests/test_indexer.py`, plus docs (PLAN §11, CONVENTION §2, BACKLOG, LESSONS).
- **Dependents / guards that will react:**
  - `tests/test_sql_confinement.py:32` asserts **exactly 11** core modules — this card adds no
    module, so the count holds; but it also asserts `store.py` is the *only* SQLite-touching module,
    which constrains `indexer.py` to hold no SQL and no `sqlite3` import.
  - `tests/test_core_is_language_agnostic.py` bans the token `php` (and 8 others) anywhere under
    `code_atlas/`, comments included — binding on every new line of `indexer.py`.
  - `tests/test_contract_sole_source.py` fails a consumer that re-declares a field list.
  - `tests/test_config.py` enumerates the knob set — a new knob lands there too.
  - `tests/test_backlog_bookkeeping.py` requires the BACKLOG status + token rows to match.
- **Repos touched:** `app` (`.`) only. No porting.
- **`db-map`:** none exists (`.harness.json` has `db_kind: null`), so no schema-dependent widening —
  noted, not required. The schema itself is **unchanged** by this card.

## Baseline

`BASELINE: green` — captured on untouched `main` @ `b63397f`:
`pytest -q` → **317 passed**; `ruff check .` → clean; `mypy code_atlas` → 11 source files clean.
Baseline exclusions: **none**. The 6 `ruff format` diffs are recorded as an uncodified standard
above, not as a baseline failure.

## Rule-section coverage

`RULE SECTIONS: §1, §2, §3, §4, §5, §6, §7, §8 — 6 checked ✅ / 2 N-A (reason) / 1 absent-mandatory (finding)`

Applicable sections derived from the **change types** present (new core orchestration module ·
concurrency/process management · a new config knob · two new store reads · new integration tests):

| § | Applies because | Verdict |
|---|-----------------|---------|
| §1 Architectural boundaries | a new core module sits between `adapter` and `store` | ✅ checked → C1 |
| §2 Standard over sample | — no adapter source changes; the only fixture touched is protocol-driven | **N/A (reason)** → C9 |
| §3 Frozen contract | the indexer is a contract consumer (R3.2), and stores bare edges (R3.3) | ✅ checked → C6, R6 |
| §4 Determinism | fan-out + wall-clock `built_at` + arrival order | ✅ checked → C2, C3 |
| §5 Error handling | the loud/soft split is the card's central design choice | ✅ checked → C4, Q5 |
| §6 Testing | R6.1 names `indexer` explicitly | ✅ checked → C5 |
| §7 Change discipline | a new knob must reach PLAN §11 and CONVENTION §2 | ✅ checked → C7 |
| §8 Dependencies | stdlib-only concurrency | ✅ checked → C8 |
| **process / concurrency conventions** | **the change type demands it** — timeout, kill, thread-vs-process, worker-failure disposition | **ABSENT — finding.** Same gap task 005 raised and nobody codified. Surfaced, not silently applied; routed to `/mango:codify`; does not gate-block. |

## Phase 1 — Analysis ✋ Gate 1

**Summary of what the analysis established:**

- `SECTIONS: 4 found | 4 decomposed | ROWS: C=9, R=12, G=1, AC=7` — every multi-clause bullet split
  one row per clause (the "Fan paths…" bullet is four obligations, "Deadline…" is two, AC1 and AC2
  are two each).
- **AC validation: 10 rows, 7 mismatches, every one carried forward rather than silently corrected.**
  Five acceptance values were **not falsifiable as written** ("queryable", "idempotent", "no lock
  contention", the missing deadline number, and the unproven `busy_timeout`) and each is pinned to a
  measurable form here. Manual-check exclusions: **none**. Coverage-gap exclusions: **none recorded
  at Gate 1** — this card is where three previous exclusions come to be closed, and adding a fourth
  would defeat the point.
- **No AC carries a `✅`** yet. The two ✅ rows in the matrix are C8 (stdlib-only, true today) and C9
  (N/A by change type).
- `BASELINE: green` @ `b63397f` — 317 passed · ruff clean · mypy clean.
- Inventories set as **per-item checklists**: **A = 16** build obligations, **B = 6** failure
  obligations. Review confirms every row, not a total. Both denominators come from PLAN §8.1 / §4.1
  and the three carried exclusions — not from the ticket's prose.
- `STRUCTURE: native` · `TRACK: backend` · `TIER: full` · `SCOPE: L`. `SURFACES`: N/A (backend).
- `RULE SECTIONS` emitted with every applicable section checked or N/A-with-reason; the one **absent
  mandatory** section (process/concurrency conventions) is surfaced as a finding for the second time
  in this project's history.
- **Why `SCOPE: L` and why it is not split:** 16 + 6 obligations across 6 source files, three
  carried exclusions, and the project's first concurrency. A split was considered and rejected — the
  deadline (AC4) and the contention proof (AC5) both *require* the fan-out to exist, so deferring
  them again would repeat exactly the deferral this card was created to end. Recorded so the
  outgrew-its-ticket nudge at Gate 2 compares against **L**, not a flattering **M**.
- **`j = 0` → Gate 0 CLEARED** under the user's standing delegation (2026-07-31). The four real
  choices — the deadline knob (Q2), the loud/soft split (Q5), `kill()` on the driver but not the
  Protocol (Q7), and restart-on-parse-timeout / retire-on-boot-timeout (Q9) — are recorded above
  with their reasoning, so they are reviewable rather than buried.
- **Carried into Phase 2 as mandatory change-list items** (each traces to a matrix row, so no hunk is
  untraceable — `LESSONS.md`): the `CA_ADAPTER_TIMEOUT` knob in PLAN §11 **and** CONVENTION §2 (C7) ·
  `store.file_paths()` + `store.now()` (Q8/A5/A15) · `SubprocessAdapter.kill()` (Q7/R11/R12) ·
  `gitutil.ls_files` + `gitutil.head_commit` (Q3/A1/A13) · the `fake_adapter.py` hang modes
  (B3/B4/B5) · pinned `CA_WORKERS` in every fan-out test (R10/A7).
- **Gate 1 status:** approved in advance by the user; proceeding to design.

---

## Phase 2 — Design ✋ Gate 2

### Approach

One new module, `code_atlas/indexer.py`, exposing **`full_build(config, store) -> BuildReport`**. It
owns §8.1 steps 1–4 plus the FTS build and nothing else — no SQL, no language name, no resolver.

```
              main thread (the ONLY writer)                      worker threads (N)
  probe one adapter per configured key ─────────────────────────────────────────────┐
  build extension_index  →  {suffix: key}                                           │
  collect(root, suffixes)  →  sorted repo-relative paths                            │
  reconcile: store.file_paths() - collected  →  store.remove_file                   │
  ┌── per adapter key ──────────────────────────────────────────────────────────┐   │
  │  work: Queue[path] ────────────────────────────────────────────▶ worker i ──┘   │
  │                                                                    │  hash bytes │
  │  results: Queue(maxsize=2N)  ◀──────── (path, digest, ParseResult) ┘  adapter.parse
  │  drain → store.upsert_file + store.replace_file_rows                            │
  └─────────────────────────────────────────────────────────────────────────────────┘
  any path that never produced a result  →  upsert_file(parsed_ok=False)
  set_meta ×3  →  rebuild_search_index()
                          ▲
        one _Watchdog thread arms a deadline around every blocking adapter call
        and calls adapter.kill() when it expires — the parked read then returns "".
```

Five load-bearing choices:

1. **Threads, not processes, for the workers.** The core's own work is blocking I/O on a pipe, which
   releases the GIL; the parallelism that matters is the N *adapter* processes. `threading` +
   `queue`, no new dependency (R8.2).
2. **The writer is the calling thread, and `sqlite3` enforces it.** Spike S6 (below) shows a
   `GraphStore` built on one thread **raises `ProgrammingError`** if another thread writes through
   it. R4.3's "single SQLite writer" is therefore a *runtime-enforced* property here, not a
   convention — a fan-out that tried to write would crash loudly, never corrupt quietly.
3. **Back-pressure instead of buffering.** `results` is bounded at `2N`; a worker blocks on `put`
   when the writer is behind. A 112k-file repo therefore never holds 112k node lists in memory.
4. **One watchdog thread, not one timer per request.** The ticket rules out a per-request reader
   thread; a `threading.Timer` per call is the same cost in disguise. One polling thread arms/disarms
   a deadline per in-flight blocking call and kills the child when it expires (spike S1).
5. **Every collected path gets a `files` row.** Results are matched against a `pending` set; whatever
   never came back — a retired worker, a killed adapter, a dead process — is upserted with
   `parsed_ok=0`. "Recorded as unparsed" becomes an invariant instead of a per-branch promise.

### Rejected alternatives

| Rejected | Why |
|----------|-----|
| **`multiprocessing` / `ProcessPoolExecutor` for the workers** | The parallelism is already in the adapter subprocesses; a second process layer would add pickling, a second failure surface, and no throughput. R1.2/R7.4 — the simplest thing that works. |
| **`selectors` / `select` on the adapter's stdout to implement the timeout** | The ticket rules it out explicitly, and correctly: `select` does not work on Windows pipes, so the timeout would silently not exist on one supported platform. Killing the child is platform-uniform. |
| **A `threading.Timer` armed per blocking call** | One thread created and destroyed per file. On 112k files that is 112k thread lifecycles — precisely the "per-request reader thread" cost the ticket rejects. One polling watchdog is O(1) threads. |
| **Reusing `SubprocessAdapter.stop()` as the watchdog's weapon** | `stop()` closes `stdout` while the worker is parked inside `readline()` on it, which races into `ValueError: readline of closed file` instead of the clean `AdapterError` the driver already models. `kill()` leaves the pipes alone; the read returns `""` and the existing `_read_line` raises (spike S1 + S7). |
| **Adding `kill()` to the `LanguageAdapter` Protocol** | A deadline is a *driver* concern, not a language capability; the Protocol is the language seam. A Protocol method with one implementer and no second in sight is R7.4's dead abstraction. |
| **Retiring a worker on every timeout (no restart)** | With `CA_WORKERS=1` one slow file would hand the entire rest of the repo to `parsed_ok=0`. Restart-on-parse-timeout keeps the build useful; retire-on-boot-timeout keeps it terminating (Q9). |
| **Buffering all results and writing them sorted by path** | Would make insert order deterministic — but at the cost of holding the whole graph in memory, which R4.3 forbids in the same breath as single-writer. Task 004's ratified id carve-out already makes this unnecessary. |
| **A fourth carried exclusion for the deadline** | Rejected on principle: this card exists to *close* three deferred exclusions. Deferring a fourth would repeat the pattern LESSONS records. |

### Assumptions

Every assumption the approach leans on. The five `novel-untested` runtime ones were **spiked before
this gate**; the spikes are throwaway scripts run against the project's own interpreter and store.

| # | Assumption | Tag | Resolution |
|---|-----------|-----|-----------|
| S1 | `Popen.kill()` from a **watchdog thread** unblocks a `readline()` parked in a **worker thread**, returning `""` rather than raising | novel-untested → **verified by spike** | Spiked: worker parked 1.0 s in `readline()`; after `kill()` it returned `''` in 0.99 s, thread exited, `returncode=-9`. So the hang collapses into the `AdapterError` `_read_line` already raises (`adapter.py:226-229`). |
| S2 | `busy_timeout=5000` makes a **second** writer wait out a held lock instead of failing at once | novel-untested → **verified by spike, with a negative control** | Spiked: with a competing `BEGIN IMMEDIATE` held 1.5 s, a second `GraphStore.upsert_file` **waited 1.53 s and succeeded**. Negative control at `busy_timeout=0`: `OperationalError: database is locked` after **0.00 s**. AC5 is provable exactly as pinned. |
| S3 | `git ls-files -z` yields sorted, repo-relative, POSIX-separated paths, and fails loudly outside a repo so the walk fallback has a trigger | novel-untested → **verified by spike** | Spiked in a throwaway repo: `a/y.aa`, `b/z.aa`, `m n.aa` — sorted, unquoted (`-z` bypasses `core.quotepath`), repo-relative. `git ls-files` in a non-repo dir → **exit 128**. `git rev-parse HEAD` before the first commit → **exit 128**, so `last_commit` is legitimately absent rather than a fabricated value. The core sorts anyway, so a git-version difference cannot leak into R4.2. |
| S6 | `sqlite3` objects are usable from any thread | novel-untested → **verified FALSE by spike, and the design is better for it** | Spiked: writing through a main-thread `GraphStore` from another thread raises `ProgrammingError: SQLite objects created in a thread can only be used in that same thread`. This makes R4.3 **runtime-enforced**: a worker that tried to write would crash loudly. It also dictates that AC5's contention test must build its second `GraphStore` *inside* the contending thread. |
| S7 | `stop()` is safe **after** the watchdog has already killed the child, and safe twice | novel-untested → **verified by spike** | Spiked against the real `fake_adapter.py`: `kill()` → `stop()` → `stop()` all clean. So the worker's cleanup path needs no new guard. |
| S4 | A reply rejected by `contract.validate()` already comes back as a **soft** `ParseResult(ok=False)`, so the indexer only has to write `parsed_ok=0` | **verified (code)** | `adapter.py:235-237` — `validate()` errors return `_failure(...)`, never raise. AC3 is therefore an integration wiring proof, which is exactly the half task 002 excluded. |
| S5 | The default worker count is already floored and capped, and CI's core count differs from this host's | **verified (code + measurement)** | `config.py:104-106`; `os.cpu_count()` = 16 here → default 8, vs `ubuntu-latest`. Hence R10: every fan-out test pins `CA_WORKERS`. |
| S8 | `store.upsert_file` / `replace_file_rows` / `remove_file` / `set_meta` / `rebuild_search_index` behave as unit-tested when driven end-to-end | **verified (code + task 004's suite)** | `store.py:145-206`; the proving test drives them for real, so a false assumption fails it. |
| S9 | `git ls-files` is safe on CI's shallow clone (`git diff` is not) | **verified (ticket + code)** | Ticket bullet 4 states it; `ls-files` reads the index, which a shallow clone has in full. `git diff` against a missing parent is task 016's problem, and this card calls no diff. |

**No unresolved `novel-untested` third-party/runtime assumption remains.**

### Smallest change list

| # | Change | File / area | Ph2 covered by | k/N |
|---|--------|-------------|----------------|-----|
| 1 | `full_build(config, store) -> BuildReport`; `collect()`; `_Watchdog`; the worker loop; the `pending` sweep | `code_atlas/indexer.py` (new body) | G1, R1–R9, C1–C6 | A1–A11, A13–A16 · B1–B4, B6 |
| 2 | `ls_files(root) -> tuple[str, ...] \| None` and `head_commit(root) -> str \| None`, both read-only and both `None` when git cannot answer | `code_atlas/gitutil.py` (new body) | R1, R8 (Q3) | A1, A3, A13 |
| 3 | `adapter_timeout` knob + `DEFAULT_ADAPTER_TIMEOUT = 30`, resolved by the existing `_as_int` (which already rejects `< 1`) | `code_atlas/config.py` | R11, R12, C7 (Q2) | B3, B4, B5 |
| 4 | `SubprocessAdapter.kill()` — kills the child, touches no pipe. **Not** on the Protocol | `code_atlas/adapter.py` | R11, R12 (Q7) | B3, B4, B5 |
| 5 | `GraphStore.file_paths()`, `GraphStore.now()`, and three named meta-key constants so `META_KEYS` is composed from them rather than re-typed across a module boundary | `code_atlas/store.py` | R3, R8 (Q8) | A5, A13–A15 |
| 6 | Hang modes: a `silent-boot` handshake that sleeps, a `hang/` path prefix that never replies, and a `silent-after-first-boot` mode keyed off the existing `CA_FAKE_BOOTLOG`; delete the `fake_adapter.py:74-76` comment that defers this to 009 | `tests/fixtures/adapter/fake_adapter.py` | R11, R12, AC4 | B3, B4, B5 |
| 7 | `tests/test_indexer.py` — the integration suite (the proving test lives here) | new test file | G1, R1–R12, AC1a–AC4, C1–C6 | A1–A11, A13–A16 · B1–B6 |
| 8 | **Proof collateral** — `store.file_paths()` / `now()` unit tests **and AC5's two-writer `busy_timeout` proof with its `busy_timeout=0` negative control**, placed in the file that recorded the exclusion | `tests/test_store.py` | R3, R8, AC5 | A5, A12, A15 |
| 9 | **Proof collateral** — the knob table this change invalidates: a `Knob` entry, `len(KNOB_KEYS) == 6` → `7`, and the `env_name` expectation list | `tests/test_config.py` | C7 | — |
| 10 | PLAN §11 knob line; a §8.1 note that the deadline and the worker-failure disposition are now defined; strike §4.1's "*(A child that hangs is not yet covered — see task 009.)*" | `docs/PLAN.md` | C7 (R7.2) | R11, R12 |
| 11 | CONVENTION §2 `CA_` env-var list gains `CA_ADAPTER_TIMEOUT` | `docs/CONVENTION.md` | C7 | — |
| 12 | BACKLOG status row + Token usage row; this ticket's frontmatter `status` | `docs/BACKLOG.md`, this file | C7 (R7.2) | — |
| 13 | LESSONS entry for the thread-affinity finding (S6) | `docs/LESSONS.md` | C7 (R7.2) | — |

**Test blast-radius, traced mechanically** (not a shallow grep — every consumer of each touched
symbol was enumerated):

| Touched symbol | Real consumers found | Folded in as |
|----------------|----------------------|--------------|
| `config.KNOB_KEYS` / `Config` fields | `tests/test_config.py:138` (`len == 6`), `:143` (the ordered `env_name` list), `KNOBS` at `:40` — the parametrized precedence suite derives from `KNOB_KEYS`, so a new knob **fails three assertions** unless the table grows with it. `code_atlas/config.py:74` is the only `Config(...)` construction site. | item 9 |
| `store.META_KEYS` | `tests/test_store.py:389` parametrizes over it. This card **adds no key** (all four already exist), so the parametrization is unaffected — verified, not assumed. | — (no edit) |
| new module content under `code_atlas/` | `tests/test_sql_confinement.py:32` asserts **exactly 11** core modules — this card adds none, so the count holds; `:49` constrains `indexer.py` to hold no `sqlite3`/SQL token. `tests/test_core_is_language_agnostic.py` bans nine language tokens anywhere under `code_atlas/`, comments included. `tests/test_contract_sole_source.py:27` already lists `indexer.py` as a consumer, so its literals are checked the moment the module has a body. | C1, C6 — no edit needed, but binding on item 1 |
| `SubprocessAdapter` public surface | no test enumerates its methods (`dir(`/`__all__`/Protocol-membership greps all return nothing), so `kill()` is purely additive. | — (no edit) |
| `GraphStore` public surface | same — no API-enumeration assertion exists. | — (no edit) |
| `tests/fixtures/adapter/fake_adapter.py` | consumed by `tests/test_adapter.py` only (`fake(...)` at `:33`). New modes are additive and change no existing mode's behaviour. | item 6 |

### Rule compliance

| Rule | How the design complies |
|------|-------------------------|
| **R1.1** zero language branches | `indexer.py` never names a language. Suffixes come from `extension_index(probes)`; `files.language` is the adapter's **announced** `name`; the adapter key is a config dict key. Guarded by `test_core_is_language_agnostic.py`. |
| **R1.3 / R1.4** one-way deps, SRP | `indexer` imports `adapter`, `store`, `config`, `contract`, `gitutil`, `ignore`. Neither `adapter` nor `store` gains an import of the other. `indexer.py` holds no SQL and opens no connection — guarded by `test_sql_confinement.py`. |
| **R1.2 / R7.4** one seam, no dead abstraction | No pool abstraction, no adapter registry, no injectable clock beyond the one `GraphStore` already has. `kill()` stays off the Protocol. |
| **R3.2** contract sole source | The indexer transports `nodes`/`edges` opaquely; it re-types no field list. |
| **R3.3** bare edges | Edges are handed to `replace_file_rows` exactly as the adapter emitted them; the core never writes `target_qname` (that is task 011). |
| **R4.2** determinism | Collection is `sorted()` in the core regardless of git's own ordering. Stored content is compared under task 004's ratified carve-out (`nodes.id`, `edges.id`, `files.updated_at`). `built_at` uses the store's single injectable clock. |
| **R4.3** single writer | Structural *and* runtime-enforced (S6). |
| **R5.1 / R5.3** failure split | Loud: an unlaunchable command, a bad handshake, a version mismatch, a probe that never announces (Q5). Soft: `ok:false`, a contract-rejected reply, a killed worker, a dead worker, an unreadable file. |
| **R6.1 / R6.2** testing | An integration suite over spec-driven fixtures + the real adapter subprocess. Every hang proof uses a genuinely hanging process, never a mock. |
| **R6.5** guards stay non-vacuous | The PHP-driven tests carry task 007's `needs_php` skip guard, so `0 skipped` in CI stays the evidence that the PHP path ran. |
| **R7.5** comments ≤ 3 lines | Binding on every new line. |
| **R8.2** minimal deps | `threading`, `queue`, `hashlib`, `subprocess` — stdlib only. |
| **CONVENTION §3** | Paths are repo-relative and POSIX-separated everywhere, including the walk fallback on any platform. |

### Verification plan (per-AC, layer-matched)

| AC / requirement | Risk layer | Proof artifact | Layer-match |
|------------------|-----------|----------------|-------------|
| AC1a — builds a repo to a **queryable** DB | integration (real subprocess + real SQLite) | `test_indexer.py` — real `adapters/php` driven by `full_build`; asserts `nodes_by_name`, `search_nodes` (through fts5), `edges_by_source` with `target_qname` NULL, four `meta` rows, one `files` row per collected path | ✅ |
| AC1b — re-run is idempotent | integration | two consecutive `full_build`s over an unchanged tree; row content compared under the ratified id/`updated_at` carve-out | ✅ |
| AC2a — single writer | runtime / concurrency | `CA_WORKERS=4` over ≥ 8 files; a wrapper records `threading.get_ident()` at every store mutation; assert exactly one ident, and that it is the caller's | ✅ |
| AC2b — worker count honours `CA_WORKERS` | integration | `CA_WORKERS=k` over ≥ 2k files; count boot-log lines from `CA_FAKE_BOOTLOG` == k | ✅ |
| AC3 — contract-rejected result → `parsed_ok=0`, stream continues | **integration** (this is exactly the half task 002 excluded) | drive `full_build` with the fake adapter's `invalid/` path alongside good paths; assert `parsed_ok=0` for the bad one, `1` for the next, **same boot** | ✅ |
| AC4 (i) — silent **boot** at a worker | runtime / 3p (process + blocking I/O) | a genuinely hanging subprocess; assert `full_build` **returns** inside a wall-clock bound and every path has a `files` row | ✅ |
| AC4 (ii) — silent **reply** | runtime / 3p | `hang/` path prefix; assert that path is `parsed_ok=0`, the build returns, and later paths still parse | ✅ |
| AC4 (iii) — silent **probe** boot | runtime / 3p | assert `full_build` raises `AdapterError` **within the deadline** rather than hanging (Q5) | ✅ |
| AC5 — `busy_timeout` under contention | runtime / 3p (SQLite locking) | `test_store.py` — a held `BEGIN IMMEDIATE`; a second `GraphStore` (built in the contending thread, per S6) waits then succeeds; **negative control** at `busy_timeout=0` raises `OperationalError` | ✅ |
| R1 / R2 — collect + walk fallback | integration (filesystem + git) | one tmp tree inside a git repo, one **not** a repo; assert both collect the same sorted set, and that ignored paths and unclaimed suffixes are absent | ✅ |
| R3 — reconcile vanished paths | integration | build, delete a file, rebuild; assert its `files` row **and** its nodes and edges are gone | ✅ |
| R5 — hash bytes | integration | assert `files.hash` equals the sha256 of the file's bytes | ✅ |
| R7 / C3 — single writer (rulebook side) | same as AC2a | — | ✅ |
| R9 / A16 — `nodes_fts` consistent | integration | `search_nodes` returns a symbol the build wrote, and returns nothing for one a rebuild removed | ✅ |
| R10 — fan-out tests pin `CA_WORKERS` | greppable | a meta-assertion in `test_indexer.py`: every build in the file passes an explicit `workers` value | ✅ |
| C1 — no language branch, no SQL in the indexer | greppable | the two existing guard suites sweep the new module automatically | ✅ |
| C2 — determinism | integration | AC1b + an assertion that `collect()` returns a sorted tuple | ✅ |
| C6 — contract sole source | greppable | `test_contract_sole_source.py` already lists `indexer.py` | ✅ |

**No layer-match `❌`.** `SURFACES: N/A` (backend), so the surface-coverage banner is inert.

### Coverage-gap exclusions

| Item | Risk tier | Why deferred | Follow-up |
|------|-----------|--------------|-----------|
| **Windows behaviour of the watchdog and the worker pool.** The design was chosen *because* `select` does not work on Windows pipes, and `Popen.kill()` maps to `TerminateProcess` there — but this host is Linux (`Platform: linux`) and no Windows runner exists. The kill-unblocks-a-parked-read behaviour (S1) is verified on Linux only. | **low** — the mechanism is the platform-uniform one; the alternative (`select`) is the one that would silently not exist on Windows | **Carried, not newly discovered:** task 005 recorded the identical exclusion (`docs/tasks/005_adapter-protocol.md:139-142`) and it was human-approved then. Restated here rather than quietly inherited. | a Windows CI matrix leg — task 024's successor |

No other exclusion. AC1–AC5 all close at their own risk layer, and the three exclusions this card
inherited (002's R5 integration half, 004's `busy_timeout`, 005's hung adapter) are **closed here,
not re-deferred**.

### Proving test

`tests/test_indexer.py::test_the_core_builds_a_repo_into_a_queryable_index`

Builds the spec-driven PHP fixture tree with the **real** `adapters/php` subprocess under
`full_build`, then asserts through the store that the index is queryable: the fixture's class node
comes back from `nodes_by_name`, the same node comes back from `search_nodes` (so fts5 is
consistent), its `EXTENDS`/`IMPORTS` edge comes back from `edges_by_source` with `target_qname`
NULL (R3.3 preserved end-to-end), all four `meta` rows are set, and `files` has exactly one row per
collected path with a sha256 hash and `parsed_ok=1`.

It sits at the **integration** layer — the layer where G1/AC1a can actually fail — and it fails
pre-change four independent ways: `indexer.full_build` does not exist, `gitutil.ls_files` does not
exist, `GraphStore.file_paths` does not exist, and no code path writes a single row. A valid but
empty build would satisfy "no exception" and still fail this test, which is the non-vacuity bar
tasks 004/006/007 all set.

Invocation:

```
.venv/bin/pytest tests/test_indexer.py -q
```

Full sweep: `.venv/bin/pytest -q` · `.venv/bin/ruff check .` · `.venv/bin/mypy code_atlas`.

### Rollback + porting

- **Rollback:** the whole card is one branch, `feat/009-full-build-indexer`. `git revert -m 1` the
  merge commit, or delete the branch pre-merge. There is **no migration and no schema change** — the
  DDL is untouched, and `.code-atlas/graph.db` is a regenerable build artifact, not data. The new
  knob is additive with a default, so an existing `.code-atlas.toml` keeps working; reverting it
  cannot orphan a config file. `SubprocessAdapter.kill()` and the two `GraphStore` reads are
  additive and have no callers outside this card.
- **Porting:** `config.repos` holds one repo (`app`, `.`). No shared code, no porting order.

### SCOPE

`SCOPE: L` — **re-affirmed, not grown.** The change list is 13 items: 5 source files, 3 test files,
4 docs. That is what `L` was declared against at Gate 1, so the *outgrew-its-ticket* nudge does not
fire and no branch/PR-type drift arises. A split was considered and rejected again at this gate for
the Gate-1 reason: AC4's deadline and AC5's contention proof both **require** the fan-out to exist,
so splitting them out would defer, for a second time, the exact exclusions this card was created to
close.

### Gate-2 self-audit

- Every change-list item traces to a matrix row — including items 9 and 8, which exist only because
  the blast-radius trace found the assertions this change invalidates **before** execute rather
  than after. `Ph2 covered by` filled on all 13.
- Every assumption tagged; **all five `novel-untested` runtime assumptions resolved by spike**, one
  of which (S6) came back **false** and improved the design.
- Proving test named, at the matching layer, runnable, and failing pre-change for four reasons.
- Verification plan has **no `❌`**; the single coverage-gap exclusion is carried from task 005 and
  was human-approved there.
- Rollback + porting recorded. `TRACK: backend`, so `DESIGN.md` and the frontend rubric are inert.
- **Gate 2 status:** approved in advance by the user; proceeding to execute.

---

## Phase 3 — Execute

Branch `feat/009-full-build-indexer`, six commits, all change-list items implemented.

### Proving test — result

`tests/test_indexer.py::test_the_core_builds_a_repo_into_a_queryable_index` — **passes**, driving
the real `adapters/php` subprocess through `full_build` into a real database. It failed pre-change
for the four reasons Gate 2 predicted (`full_build`, `gitutil.ls_files` and `GraphStore.file_paths`
all absent, and no code path writing a row).

`BASELINE: green` → the DoD is the usual one, and it is met:

| Check | Baseline (`b63397f`) | Now |
|-------|----------------------|-----|
| `pytest -q` | 317 passed | **342 passed, 0 skipped** (+25) |
| `ruff check .` | clean | clean |
| `mypy code_atlas` | 11 files clean | 11 files clean |

`0 skipped` is load-bearing: the proving test carries task 007's `needs_php` guard, so a skip would
mean the real adapter never ran.

### Negative controls — five mutations, each restored from a `cp` copy verified with `cmp`

A test that cannot fail is not evidence (LESSONS 002/004). Each control deleted one behaviour and
re-ran the suite. **Two came back green, and they meant opposite things** — see the new LESSONS entry.

| # | Mutation | Result | Verdict |
|---|----------|--------|---------|
| M1 | `_Watchdog._poll` no longer calls `adapter.kill()` | the suite **never returned** — `timeout 120` had to terminate it | ✅ the deadline is the only thing standing between a silent adapter and a wedged build |
| M3 | `collect()` no longer sorts | **20 passed** — the control proved nothing | ❌ **the test was too weak.** The fixture tree happened to be walked in order. Fixed: the tree now has a root-level file and a deeply nested one, so the walk provably reaches them out of order. **Re-run: 1 failed** (`…falls_back_to_a_walk…`) |
| M4 | the `pending` sweep is removed | 1 failed (`…never_announces_does_not_wedge_the_build`) | ✅ "every collected path leaves a `files` row" is enforced, not asserted |
| M5 | a killed or dead adapter is never replaced | 2 failed (`…exits_mid_stream…`, `…never_answers…`) | ✅ the restart is what keeps one bad file from costing the rest of the repo |
| M6 | `store.rebuild_search_index()` removed from `full_build` | **20 passed** — the control proved nothing | ❌ **the code was wrong.** §10's triggers already keep `nodes_fts` current, so the call was a full re-index that could not change any result. **Removed** — recorded as deviation D1 |
| M7 | `_reconcile` returns without removing anything | 1 failed (`…vanished_path…`) | ✅ reconciliation is real |

### Deviations from the Gate-2 approach

**D1 — the per-build FTS rebuild was removed, not implemented.** Gate 2's change-list item 1 said
"§8.1 steps 1–4 **+ FTS**", meaning a `rebuild_search_index()` call at the end of `full_build`.
Negative control M6 showed the call is unreachable by any test, and the reason is structural, not a
gap in coverage: `store.py`'s `nodes_ai`/`nodes_ad`/`nodes_au` triggers maintain `nodes_fts` through
every `replace_file_rows`, which task 004 already proved
(`test_store.py::test_the_search_index_follows_a_per_file_replace`) and documented as "repair only"
(`store.py:215`). On a 112k-file repo the call would cost a full FTS re-index per build for no
change in outcome, so R7.4 and R7.1 both point at deletion.

- **Behaviour is unchanged and still proven.** A16 ("`nodes_fts` consistent when the build returns")
  is asserted at the integration layer in both directions — the proving test gets the built node
  back out of `search_nodes`, and `…vanished_path…` asserts a removed node is no longer searchable.
- **Scope:** `docs/PLAN.md` §8.1 step 5 was corrected in the same commit. That file and section were
  already on the approved change list (item 10); the extra sentence is recorded here rather than
  absorbed. `GraphStore.rebuild_search_index` is **not** deleted — it keeps its task-004 test and
  remains the repair tool for a stale index.
- **Surfaced to review for adjudication.**

No other deviation. Every other Gate-2 Approach bullet is `implemented-as-approved`.

### Verification sweep

**Axis 1 — file set.** `git diff --stat main..HEAD` = 12 files, and **every one is on the Gate-2
change list**:

| File | Change-list item |
|------|------------------|
| `code_atlas/indexer.py` | 1 |
| `code_atlas/gitutil.py` | 2 |
| `code_atlas/config.py` | 3 |
| `code_atlas/adapter.py` | 4 |
| `code_atlas/store.py` | 5 |
| `tests/fixtures/adapter/fake_adapter.py` | 6 |
| `tests/test_indexer.py` | 7 |
| `tests/test_store.py` | 8 |
| `tests/test_config.py` | 9 |
| `docs/PLAN.md` | 10 (+ D1) |
| `docs/CONVENTION.md` | 11 |
| `docs/LESSONS.md` | 13 |

Item 12 (BACKLOG status + token row, and this file's frontmatter) is deliberately **still open** —
it lands at finalise, where the challenger's dispatch cost is known. Flipping one of the two status
sites early would fail `tests/test_backlog_bookkeeping.py`, which is the point of that guard.

- **Zero stray references:** `ruff check .` and `mypy code_atlas` clean; no dangling import or symbol.
- **No untouched-line reformatting:** no formatter was run over any file. The pre-existing
  `ruff format` drift (6 files) is untouched and stays an uncodified-standard item.
- **Every hunk maps to a matrix row** via the table above and the change list's `Ph2 covered by`.

**Axis 2 — design conformance (behaviour).** Each Gate-2 Approach bullet, classified:

| Approach bullet | Verdict |
|-----------------|---------|
| 1. Threads, not processes, for the workers | implemented-as-approved (`threading` + `queue`, no new dependency) |
| 2. The writer is the calling thread, and the database driver enforces it | implemented-as-approved — and asserted by `…single_writer_thread` |
| 3. Back-pressure instead of buffering (bounded result queue) | implemented-as-approved (`maxsize=max(2, workers * 2)`) |
| 4. One watchdog thread, not one timer per request | implemented-as-approved; the kill moved **inside** the lock so a call finishing exactly at its deadline cannot be killed on the way out |
| 5. Every collected path gets a `files` row | implemented-as-approved — and M4 proves it |
| (change list item 1) "§8.1 steps 1–4 **+ FTS**" | **deviated → D1** |

`SCOPE: L` holds — the realized diff is a strict subset of the approved list, so no
*outgrew-its-ticket* nudge and no branch/PR-type drift.

### Inventory progress

**Inventory A (16):** A1–A11 and A13–A16 proven by `tests/test_indexer.py`; **A12** (`busy_timeout`
under contention) proven in `tests/test_store.py`, beside the pragma. **16/16.**

**Inventory B (6):** B1 `…soft_parse_failure…` · B2 `…contract_rejects…` · B3
`…never_announces_does_not_wedge…` · B4 `…never_answers_is_killed…` · B5
`…never_announces_at_all_fails_loud…` · B6 `…exits_mid_stream…`. **6/6.**

**The three carried exclusions are closed:** task 002's `contract.validate()` integration half (AC3),
task 005's hung adapter at **both** call sites (AC4), task 004's `busy_timeout` contention with a
`busy_timeout=0` negative control (AC5).

---

## Phase 4 — Review ✋ (clean)

**Reviewer dispatch: skipped by user instruction** (*"execute xong thì chạy challenger là đủ rồi"*,
carried standing from task 007 and restated for this run). The ticket-blind `mango:challenger` ran;
`mango:reviewer` did not.

### Challenger — ticket-blind, round 1

Payload was **only** the raw ticket text above the working-doc separator plus the branch diff; the
working doc was withheld, and the agent confirmed in its own independence note that it did not open
this file. It rebuilt **12 requirements** from the ticket prose and ran the suite itself.

**Verdict: 12 met · 0 not met · 0 can't-tell.** It ran
`pytest tests/test_indexer.py tests/test_store.py tests/test_config.py` in the live tree: 136
passed, **0 skipped** — it verified for itself that the PHP-backed proving test was not skipped.

Its own summary of the concurrency work: *"the hang tests use genuinely sleeping subprocesses rather
than mocks, and the busy_timeout and single-writer claims each carry a negative control showing the
proof can actually fail."*

### Findings, and what was done

| # | Severity | Finding | Disposition |
|---|----------|---------|-------------|
| 1 | low | **`R10` is a dangling citation.** `tests/test_indexer.py` cited "R10" for the pinned worker count; the rule book stops at **R8.3**. R10 is this working doc's *matrix row* id, which means nothing to a reader holding only the test file. | **Fixed** — both sites now cite **R4.2**, the rule actually in play. Valid finding: the citation was traceable to nothing. |
| 2 | low | **The watchdog comment overstates its own guarantee.** It claimed that killing under the lock means "a call that just finished cannot be killed on its way out". It can: the poll thread may take the lock in the window between the guarded call returning and `guard()`'s `finally` popping the token. | **Fixed — the comment, not the code.** The race is inherent to any deadline (a call finishing *at* its deadline is indistinguishable from one that has not), and its whole cost is one adapter restart on the next path — never a lost result, never a hang, since the successful `ParseResult` is already captured before the kill. Pretending it away would have been the wrong fix; the comment now states the truth. |
| 3 | informational | BACKLOG status, this file's frontmatter, and the Token-usage row are still `todo` / absent. | **Expected mid-lifecycle**, and deliberate: flipping one status site without the other fails `tests/test_backlog_bookkeeping.py`. All three land together at finalise, where the dispatch cost is known. The challenger independently confirmed no PR exists yet. |

It also examined the **D1 deviation** without having seen the deviation record, and reached the same
conclusion independently: *"a defensible, disclosed deviation rather than a silent drop"*, noting the
in-code marker at `indexer.py` and the PLAN/LESSONS corrections. That is the adjudication D1 needed.

### Re-review — verify-only, in the main loop

Both fixes stayed **inside the two named findings** and touched only `code_atlas/indexer.py` and
`tests/test_indexer.py`, which were already on the approved change list. No scope changed, so no
subagent was re-dispatched and the requirement reconstruction was not repeated.

- Both fixes verified present as described.
- Affected proof re-run plus the full regression scan: **342 passed**, `ruff check .` clean,
  `mypy code_atlas` clean.

### Clean-verdict criteria

| Criterion | Result |
|-----------|--------|
| Reviewer reports no Critical | reviewer skipped by user instruction; the challenger reported no Critical and no High |
| Challenger finds every item met | **12/12 met**, 0 not met |
| No layer-match `❌` standing | none — the Gate-2 verification plan had no `❌` |
| `k = N` on every inventory | **A 16/16**, **B 6/6** — every row confirmed individually, not by total |
| Surface coverage `N == M + X` | inert (`TRACK: backend`, `SURFACES: N/A`) |
| Proving test green | `…builds_a_repo_into_a_queryable_index` passes against the real adapter |
| Baseline comparison | `BASELINE: green` → 317 passed then, **342 passed** now, **0 skipped**, no new failure |

**Verdict: clean.**

### Stale-review guard

`Reviewed at 104dc7ba39f38d64804d3ed8fd6fc511710ac346`

Reviewed files (13): `code_atlas/adapter.py`, `code_atlas/config.py`, `code_atlas/gitutil.py`,
`code_atlas/indexer.py`, `code_atlas/store.py`, `docs/CONVENTION.md`, `docs/LESSONS.md`,
`docs/PLAN.md`, `tests/fixtures/adapter/fake_adapter.py`, `tests/test_config.py`,
`tests/test_indexer.py`, `tests/test_store.py`, and this working doc.

Working-doc path (exempt from the staleness comparison, per `work_doc_mode: embed`):
`docs/tasks/009_full-build-indexer.md`. Also exempt: `docs/LESSONS.md` (mango bookkeeping) and
`docs/BACKLOG.md` (the status/token sync finalise still owes).

---

## Phase 5 — Finalise ✋ final gate

### Stale-review guard

Marker: `Reviewed at 104dc7ba39f38d64804d3ed8fd6fc511710ac346`.

- `git diff --name-only 104dc7b..HEAD` → **empty**.
- Uncommitted: `docs/tasks/009_full-build-indexer.md` only — the marker-bearing working doc, which
  `work_doc_mode: embed` makes an exempt path by construction.
- Non-exempt files beyond the reviewed set: **none** → **not stale, proceed.**

### Pre-PR self-check (`.github/pull_request_template.md`)

| Item | Verdict | Evidence |
|------|---------|----------|
| No language branch in the core — R1.1 | ✅ | `tests/test_core_is_language_agnostic.py` sweeps `code_atlas/` for nine language tokens including comments; `indexer.py` takes the suffix set and `files.language` from handshakes only |
| Adapters name no repo/framework — R2 | ✅ N/A | no adapter source changed; the CI gate over `adapters/` still passes |
| Contract changes bump `contract_version` — R3 | ✅ N/A | `CONTRACT_VERSION` unchanged at 1; no vocabulary, field or qname change |
| There is a test, and it is the smallest change that ships value | ✅ | +25 tests; `SCOPE: L` re-affirmed at Gate 2 and the realized diff is a strict subset of the approved list |
| Comments ≤ 3 lines each — R7.5 | ✅ | every new comment checked; the longest is 3 lines (`indexer.py` watchdog and D1 notes) |
| Related docs updated | ✅ | PLAN §4.1 + §8.1 (steps 3–5) + §11 · CONVENTION §2 · LESSONS ×2 · BACKLOG status + token row · this file's frontmatter. README needs no change — it documents no knob list |
| No `Co-Authored-By` / AI-attribution trailer | ✅ | CI's R7.3 gate runs over the PR's commit range; checked locally over all 8 commits |

### Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| 1 — analysis | none dispatched (`explore_fanout` available; the session forbids subagents unless requested) | — | 0 dispatch | rtk active; per-task saving not attributable (`rtk gain` is global all-time) |
| 2 — design | none dispatched — 5 runtime assumptions spiked on the main model against the real store, driver and git | — | 0 dispatch | as above |
| 3 — execute | none dispatched — 5 negative-control mutations run on the main model | — | 0 dispatch | as above |
| 4 — review | `mango:challenger` (ticket-blind), 30 tool uses / 378 s. `mango:reviewer` **skipped by user instruction** | 1 | **96.3k** | as above |
| 4 — review | re-review after findings 1–2: **verify-only, main loop, no dispatch** | 2 | 0 dispatch | the cheap path taken by default, not by luck |
| 5 — finalise | none dispatched | — | 0 dispatch | as above |

`LEDGER TOTAL: 96.3k dispatch · top cost driver: phase 4 — mango:challenger`

**Scope, stated honestly:** this ledger measures **subagent dispatch only**. Main-loop spend — the
five spikes, the six mutation runs, every test and lint invocation, every file read — is **not
measured by mango**, and no dispatch-vs-noise split is invented here. For the output-noise side, see
`rtk gain`, which reports a global all-time figure that cannot be attributed to one task.

### Durable lesson

**Yes — two, both written to `docs/LESSONS.md` and carried by a commit the branch push already
includes**, so neither is orphaned on a branch a merge will delete:

1. *"The runtime may already enforce the rule you were about to prove by convention"* — `sqlite3`
   binds a connection to its creating thread, so R4.3's single writer cannot be violated silently.
   Found by a spike tagged `novel-untested` **before** Gate 2, which came back **false**.
2. *"A negative control can indict the code instead of the test"* — of five mutations, two came back
   green and meant opposite things: M3 exposed a weak fixture, M6 exposed an unreachable line.

### Follow-up tickets

**None needed.** The matrix carries **zero ⚠ (deferred) rows**: A 16/16 and B 6/6 are proven in this
card, and the three exclusions it inherited are closed rather than re-deferred. The single
coverage-gap exclusion (Windows behaviour of the watchdog) is **carried from task 005**, was
human-approved there, and already has its follow-up recorded — a Windows CI matrix leg.

## Cost ledger — see Phase 5

## Decision log

| When | Decision | Why |
|------|----------|-----|
| Phase 1 | The denominator is **A=16 / B=6**, not the ticket's five bullets | PLAN §8.1 and the three carried exclusions are the real obligation set; counting only what the prose named is how a tail ships unproven |
| Phase 1 | Five acceptance values pinned to measurable forms before any code | "queryable", "idempotent", "no lock contention", the missing deadline number, and an unexercised pragma are each unfalsifiable as written |
| Gate 0 | **`CA_ADAPTER_TIMEOUT`, default 30 s** — a knob, not a constant | CI must pin it (R4.2), and §11 already derives the env name from the key, so a knob costs one entry |
| Gate 0 | A hung adapter is **loud at the probe, soft at a worker** | At the probe *no file is known*, so "record its files unparsed" is vacuous and R5.3 applies; at a worker the ticket's "rather than wedging the build" governs |
| Gate 0 | `kill()` on `SubprocessAdapter`, **not** on the `LanguageAdapter` Protocol | A deadline is a driver concern, not a language capability; a Protocol method with one implementer is R7.4's dead abstraction |
| Gate 0 | Parse timeout → **restart**; boot timeout → **retire** | Terminates either way, and does not hand a whole repo to `parsed_ok=0` when `CA_WORKERS=1` |
| Phase 2 | **S6 came back false** and improved the design | The database driver's thread affinity makes single-writer a runtime property; the fan-out needs no lock, no write queue, and no reviewer vigilance |
| Phase 2 | Kill the child rather than `select` on its stdout | `select` does not work on Windows pipes, so the timeout would silently not exist on a supported platform |
| Phase 2 | Bounded result queue rather than buffering | R4.3 forbids loading the whole graph into memory in the same breath as single-writer |
| Phase 3 | **D1 — the per-build FTS rebuild removed, not implemented** | Control M6 showed the call is unreachable by any test, and structurally so: §10's triggers already keep `nodes_fts` current. On 112k files it was a full re-index per build for no change in outcome (R7.1, R7.4) |
| Phase 3 | M3 came back green → **fix the test**, M6 came back green → **fix the code** | A green negative control is a question, not a verdict: can a test see this, or is the line unreachable by construction? |
| Phase 4 | Finding 2 fixed by correcting the **comment**, not the code | The race is inherent to any deadline and costs one restart, never a result; claiming it away would have been the dishonest fix |
| Phase 5 | Status/token bookkeeping lands **in this PR**, not a follow-up | `tests/test_backlog_bookkeeping.py` exists precisely because task 024's deferred sync was forgotten |

## Session status

- **Last updated:** Phase 5, at the final gate, on branch `feat/009-full-build-indexer`
- **Current phase:** Phase 5 — Finalise, **waiting on per-action approval** (nothing pushed yet)
- **Next action:** on approval, push `feat/009-full-build-indexer` and open the PR with
  `gh pr create -F /tmp/pr-009.md`; then correct the BACKLOG token row if the PR number is not #17.
- **Blocked on:** per-action approval for the branch push and the PR open
- **Revert path:** all work is on `feat/009-full-build-indexer` (8 commits, `ddd8e4d`..`104dc7b`
  plus bookkeeping). Pre-merge: delete the branch. Post-merge: `git revert -m 1 <merge sha>`. There
  is **no migration and no schema change** — the DDL is untouched and `.code-atlas/graph.db` is a
  regenerable build artifact, not data. `CA_ADAPTER_TIMEOUT` is additive with a default, so
  reverting it cannot orphan an existing `.code-atlas.toml`.
