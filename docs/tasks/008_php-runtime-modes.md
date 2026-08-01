---
id: 008
slug: php-runtime-modes
title: PHP runtime invocation (host CLI / Docker)
phase: 1
milestone: M1
status: done
depends_on: [005, 007]
---

## Goal
Run the PHP adapter whether or not PHP is on the host PATH (§9).

## Scope / Deliverables
- `CA_PHP_CMD` wiring: (A) host PHP CLI (default), (B) `docker compose exec -T php php`.
- Path mapping for Docker (`CA_HOST_ROOT`/`CA_CONTAINER_ROOT`); store repo-relative paths regardless.
- Document the tokenizer-only requirement (no app extensions needed for indexing).
- **CI:** the Docker mode has no runner path today — CI installs PHP on the host only. Either add a service/compose step so the "same fixture under both modes" criterion is actually executed, or record Docker mode as a named, human-approved coverage-gap exclusion. A criterion that only ever runs on one developer's laptop is not proven (LESSONS 002).

## Acceptance criteria
- Same fixture parses identically under host mode and Docker mode (repo-relative paths match).
- Clear error if `CA_PHP_CMD` is unset/invalid.

## References
Plan §9.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 008 — PHP runtime invocation (host CLI / Docker) (working doc)

- **Ticket:** 008 · [docs/tasks/008_php-runtime-modes.md](008_php-runtime-modes.md) (raw above separator)
- **Type:** enhancement
- **Repo(s) / Porting:** `app` (`.`) only
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/N touched files under UI paths
- **TIER:** full
- **BASELINE:** green — `.venv/bin/pytest -q` → **388 passed** in 14.89s (untouched `e96c9c6`)
  <!-- baseline exclusions: none -->
- **work_doc_mode:** `embed` → this doc lives below the separator in the ticket file itself (harness `work_doc_mode: embed`; user override of mango's committed-stub→separate default)

---

## Phase 0 — Refine (the FIRST phase; skip when the ticket is already clear)

`REFINE: 1 unresolved surfaced | 1 want-decision asked | 4 how-decision resolved+cited | 0 ASSUMED | skip: no`

**INPUT KIND:** ticket (single deliverable — not an epic).

**Settled wants (want-decision — from the user; become acceptance-criteria constraints analysis must honour).**

| # | The want (in want-language) | Chosen direction (NOT a tool) | Becomes AC constraint |
|---|-----------------------------|-------------------------------|-----------------------|
| 1 | How should “same fixture under host + Docker” count as proven? | **Named coverage-gap** — keep CI on host PHP only; record Docker live dual-mode as an explicit human-approved exclusion | (W1a) CI stays host-PHP only — no compose/service step for dual-mode. (W1b) Docker live dual-mode identity is a named coverage-gap exclusion (LESSONS 002 / ticket Scope). Path-mapping logic + host mode remain CI-proven. |

**Resolved direction + citation (how-decision — refine-resolved + CITED):**

| # | HOW-decision | Resolution | Citation (`file:line` / convention / rulebook § / ticket line) |
|---|--------------|------------|----------------------------------------------------------------|
| 1 | Default runtime mode | Host PHP CLI is default (mode A); Docker exec is supported (mode B) — ship both | `docs/PLAN.md:261-265`; ticket Scope line 15 |
| 2 | Path-mapping knobs | Add generic `CA_HOST_ROOT` / `CA_CONTAINER_ROOT` (deferred from 003); store always repo-relative | `docs/PLAN.md:263`; `docs/tasks/003_config-and-ignore.md:125-127`; `docs/CONVENTION.md:70` |
| 3 | `CA_PHP_CMD` shape | Complete argv already (interpreter + entry + `--server`); core appends nothing — 008 wires modes/docs/tests, does not re-litigate argv form | `docs/PLAN.md:259-260`; task 005 ratification; `adapters/php/README.md:25-28` |
| 4 | Tokenizer-only docs | Document that indexing needs PHP CLI + tokenizer only (no app extensions) | ticket Scope line 17; `docs/PLAN.md:262`; already partly in `adapters/php/README.md:8` — extend host/Docker runbook |

**ASSUMED (awaiting ratification):** none (user explicitly chose option 2).

**Constraints surfaced from the scan:**

- R1.1 — path mapping must be language-agnostic (no `if language == "php"`); knobs are generic roots, not PHP-specific.
- R5.3 — unset/invalid `CA_PHP_CMD` and half-set root pairs fail loud.
- R8.1 — each adapter documents its own launch string; core does not invent Docker argv.
- No `docker-compose*.yml` in-repo; CI uses host `setup-php` only (`.github/workflows/ci.yml:36-38`).
- Protocol already sends repo-relative paths (`adapter.py` request; `indexer.py` collection).

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch): **0** still-unexposed product-decisions.

---

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope / Deliverables, Acceptance criteria, References) | 4 decomposed | ROWS: C=6 R=6 G=1 AC=4`

*References* → 0 requirement rows (points at Plan §9). No ticket *Constraint* header — C rows from the rulebook for this change type. Scope CI bullet split into want clauses W1a/W1b as AC3/AC4. Scope path-mapping bullet split: knobs (R3) + store invariant (R4).

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | "Run the PHP adapter whether or not PHP is on the host PATH (§9)." | Support host CLI (A) and Docker-exec (B) launch of the PHP adapter via `CA_PHP_CMD` + optional root mapping so indexing works when PHP is absent from host PATH. | Host path works today via `CA_PHP_CMD` + `SubprocessAdapter`; Docker path-mapping knobs absent (`config.py` KNOB_KEYS); no dual-mode proof | | | ❌ |
| R1 | Scope | "`CA_PHP_CMD` wiring: (A) host PHP CLI (default)" | Document + test host mode: complete argv launches adapter; default documented as A. | `adapters/php/README.md:27-28`; README host MCP example; CI host PHP | | | ❌ |
| R2 | Scope | "(B) `docker compose exec -T php php`" | Document Docker-mode complete argv (entry script under container path); wiring is config/docs — core still just `Popen`s the argv. | README project-file example `README.md:103-104`; no path-map knobs; no dual-mode test | | | ❌ |
| R3 | Scope | "Path mapping for Docker (`CA_HOST_ROOT`/`CA_CONTAINER_ROOT`)" | Add the two knobs (env + `.code-atlas.toml`); when both set, rewrite absolute host-rooted paths to container-rooted before the adapter sees them; relative paths pass through. One set without the other → `ConfigError`. | Knobs absent from `KNOB_KEYS` / `Config` / PLAN §11 list (`PLAN.md:324`) | | | ❌ |
| R4 | Scope | "store repo-relative paths regardless" | After any mapping, `files.path` / node `file_path` / edge `file_path` remain repo-relative POSIX (never host or container absolute). | Already true for current host flow (`indexer.py` relative paths); must hold when roots are set | | | ❌ |
| R5 | Scope | "Document the tokenizer-only requirement" | Runbook states indexing needs PHP CLI + `tokenizer` only — no app extensions — for both modes. | Partially present `adapters/php/README.md:8`; Docker/path-map section missing; README knobs omit roots | | | ❌ |
| R6 | Scope / want | CI fork (settled want #1) | See AC3 + AC4 (one row per clause). | CI host-only today; no compose file | | | ❌ |
| AC1 | Acceptance criteria | "Same fixture parses identically under host mode and Docker mode (repo-relative paths match)." | **Pinned:** (i) host mode: same fixture → stable repo-relative paths in results (CI). (ii) path-map transform: synthetic `HOST_ROOT`/`CONTAINER_ROOT` unit proof that absolute-under-host → container path and relative unchanged (CI). (iii) **live** Docker↔host identity → coverage-gap exclusion (AC4). | No dual-mode or root-mapping tests | | | ❌ |
| AC2 | Acceptance criteria | "Clear error if `CA_PHP_CMD` is unset/invalid." | **Pinned (S3):** unset/`None` command → error text includes the env name `CA_<LANG>_CMD` (PHP: `CA_PHP_CMD`); invalid/unlaunchable argv → `AdapterError` naming the failure (existing `cannot run` ok once unset names the knob). Blank/` ` CMD already fails at config layer. | `indexer.py:165-166` says `has no configured command` **without** env name; `adapter.py:134-136` `cannot run`; tests match `cannot run` only | | | ❌ |
| AC3 | Want W1a | CI stays host-PHP only | No compose/service step added to CI for dual-mode; host PHP setup remains. | `ci.yml` host `setup-php` only | | | ❌ |
| AC4 | Want W1b | Docker live dual-mode named exclusion | Working-doc + task/docs record Docker live dual-mode as human-approved coverage-gap exclusion (this Gate-1 ratification). | Ticket Scope; refine want #1 | | | ❌ |
| C1 | rulebook §1 R1.1/R1.4 | Zero language branches; SRP | Path mapping + knobs live in language-agnostic core (`config` / driver or small helper); no `php` string branch; adapters still parse-only. | `tests/test_core_is_language_agnostic.py` | | | ❌ |
| C2 | rulebook §5 R5.3 | Fail loud on bad CA_* | Half-set roots, malformed root paths, unset/invalid CMD → loud config/adapter errors, never silent fallback. | pattern in `config.py` ConfigError | | | ❌ |
| C3 | rulebook §6 R6.1 | Tests required | Config + mapping unit tests; host-mode fixture assertion; error-message tests for unset CMD. | gap | | | ❌ |
| C4 | rulebook §7 R7.2/R7.5 | Docs honest; comments ≤3 lines | Update PLAN §9/§11, CONVENTION env list, README knob table, adapter README Docker section, BACKLOG + frontmatter. | | | | ❌ |
| C5 | rulebook §8 R8.1 | Adapter documents launch | PHP README documents both mode A and B argv + root mapping. | Docker section absent | | | ❌ |
| C6 | rulebook §4 R4.2 | Deterministic | Same roots + same relative path → identical mapped path every time. | | | | ❌ |

Status legend: ✅ done/proven · ⚠ deferred (needs follow-up ticket) · ❌ not met.

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| AC1 | Same fixture parses identically under host + Docker (repo-relative paths match) | With want #1: live Docker half is **excluded**; measurable remainder = host fixture paths repo-relative + unit-tested root rewrite. "Identically" for live Docker is **not** CI-falsifiable under the ratified exclusion. | Y (pinned) | host+mapping: measurable · live Docker: **manual-check / coverage-gap exclusion (AC4)** | Confirm pin at Gate 1 (below) |
| AC2 | Clear error if `CA_PHP_CMD` unset/invalid | "Clear" → error string includes `CA_PHP_CMD` (or generic `CA_<LANG>_CMD` for key `php`) on unset; invalid → existing `cannot run` / ConfigError | Y (pinned S3) | measurable (pytest `match=`) | Confirm pin at Gate 1 |
| AC3 | (want) CI host-only | No Docker service/compose job in CI | Y | greppable (`ci.yml`) | — |
| AC4 | (want) named Docker exclusion | Exclusion row in Coverage-gap exclusions + docs mention | Y | greppable in working doc / task | Ratify exclusion at Gate 1 |

## Inventory (universal "all/every/no" requirements)

### Inventory A — runtime modes (AC1) · **Denominator N = 2**

| # | Item | Ph3/4 proven by (`path:line` / test) | Status ✅/⚠/❌ |
|---|------|--------------------------------------|----------------|
| 1 | Host PHP CLI (mode A) | | ❌ |
| 2 | Docker exec (mode B) — **live** dual-mode identity | | ⚠ coverage-gap (AC4) |

### Inventory B — path-mapping knobs (R3) · **Denominator N = 2**

| # | Item | Ph3/4 proven by | Status |
|---|------|-----------------|--------|
| 1 | `CA_HOST_ROOT` / `host_root` | | ❌ |
| 2 | `CA_CONTAINER_ROOT` / `container_root` | | ❌ |

### Surface inventory

**N/A — TRACK is backend.**

## Clarifications

`CLARIFICATION: 5 raised | 5 self-resolved (cited) | 0 for human decision`

**Self-resolved (cited):**

1. **S1 — Path-map transform.** When both roots are set, absolute paths under `CA_HOST_ROOT` rewrite to the same relative suffix under `CA_CONTAINER_ROOT` before the adapter request; already-repo-relative paths pass through unchanged; store writes stay repo-relative. *`PLAN.md:263`; `CONVENTION.md:70`.*
2. **S2 — Half-set roots fail loud.** Exactly one of host/container root set → `ConfigError` (R5.3). *`ENGINEERING_RULES.md:77-78`.*
3. **S3 — "Clear" unset error names the env var.** Unset command error must include `CA_<LANG>_CMD` (for PHP tests: `CA_PHP_CMD`). Invalid launch keeps `cannot run`. *Ticket AC line 22; task 005 S6 intent; R5.3.*
4. **S4 — No in-repo compose required.** Want #1 rejects adding CI compose; documenting example argv is enough for mode B. *Refine want #1; BACKLOG "008 is Docker path-mapping".*
5. **S5 — PLAN §18 Q1 is stale.** §9 already says "Default A; ship both." This ticket implements that; no re-open of host-vs-Docker-only. *`PLAN.md:265` vs `PLAN.md:434`.*

**For human decision:** none (j = 0). Gate 1 still needs ratification of AC pins + coverage-gap exclusion (below).

---

## Phase 1 — Analysis ✋ Gate 1

- **Type:** enhancement — per-goal gap analysis:
  - **G1 / modes:** Host launch works (`CA_PHP_CMD` complete argv + `SubprocessAdapter.start` at `adapter.py:115-136`). Docker example exists in README but **no** `CA_HOST_ROOT`/`CA_CONTAINER_ROOT`, **no** rewrite helper, **no** dual-mode test. Gap = knobs + mapping + docs + proofs/exclusion.
  - **AC2:** Unset path says `has no configured command` without env name (`indexer.py:165-166`) — short of pinned S3.
  - **Docs:** tokenizer-only present; Docker path-map runbook and §11 knob list incomplete.
- **Handler / entry point + blast radius:** `config.load_config` / `Config` · `indexer._adapter` · `SubprocessAdapter.start`/`parse` · docs (`PLAN` §9/§11, `CONVENTION` env list, `README`, `adapters/php/README`) · tests (`test_config`, new mapping tests, adapter/indexer error tests). No store schema change. No contract bump.
- **Rule-compliance section coverage:**

  `RULE SECTIONS: §1 arch (R1.1/R1.4) ✅ · §4 determinism (R4.2) ✅ · §5 errors (R5.3) ✅ · §6 testing (R6.1) ✅ · §7 discipline (R7.2/R7.5) ✅ · §8 deps (R8.1) ✅ · §2 standard-over-sample N/A (docs/runtime only, no new language constructs) · §3 contract N/A (no vocabulary change)`

- **Self-audit:** sections 4=4 decomposed; AC table complete with falsifiable-or-exclusion; BASELINE green; j=0; inventories N set; want clauses → AC3+AC4; STRUCTURE native; TRACK backend; SCOPE M; TIER full; RULE SECTIONS emitted.
- **Gate 1 status:** **cleared** — AC1/AC2 pins + AC4 Docker coverage-gap + SCOPE M / TIER full ratified 2026-08-01 (user: "approve")

---

## Phase 2 — Design ✋ Gate 2

### Approach

1. **Knobs.** Add `host_root` / `container_root` to `KNOB_KEYS` + `Config` (default `None`). Env `CA_HOST_ROOT` / `CA_CONTAINER_ROOT`; project-file keys `host_root` / `container_root`. After resolve: both set or both unset; exactly one → `ConfigError` (R5.3).
2. **Pure rewrite.** `to_adapter_path(path, host_root, container_root) -> str` in `config.py` (language-agnostic): roots unset → path unchanged; relative path → unchanged; absolute under `host_root` → same suffix under `container_root` (POSIX); absolute outside host_root → `ConfigError`.
3. **Wire at the process boundary.** `SubprocessAdapter` takes optional roots from `Config`. In `parse(path)`: `wire = to_adapter_path(...)`; send `wire` on the JSONL request; build `ParseResult` so **store-facing** `path` and any `file_path` / File `qualified_name` that equal `wire` are rebased back to the caller's `path` (PHP echoes the request path into nodes — without rebase, Docker absolutes would leak into SQLite). Relative-path host mode is a no-op (wire == path).
4. **Clear unset CMD.** `indexer._adapter`: when `adapter_cmd` is `None`, raise `AdapterError` whose message includes `CA_{KEY}_CMD` (PHP → `CA_PHP_CMD`). Invalid launch keeps existing `cannot run`.
5. **Docs.** PLAN §9/§11, CONVENTION env list, README knob table + Docker example with roots, `adapters/php/README` host/Docker runbook (tokenizer-only restated). **Do not** add compose/CI Docker service (AC3).
6. **Proofs.** Unit tests for knobs + pair rule + `to_adapter_path`; adapter/fake integration that an absolute host wire path rebases to repo-relative in the result; unset-CMD message test; host-mode fixture still parses with repo-relative paths (existing PHP server path is enough + one explicit assert). Live Docker dual-mode → coverage-gap exclusion only.

### Rejected alternatives

1. **Require live Docker in CI (compose service)** — rejected at refine want #1 / Gate 1 (AC3/AC4).
2. **Send mapped absolute paths and trust the adapter echo** — rejected: PHP puts request `path` into `file_path` / File `qualified_name` (`Visitor.php:46-48`); store would get container absolutes, violating R4 / CONVENTION repo-relative.
3. **New `paths.py` module / mapper class** — rejected (R1.2 / YAGNI): one pure function + two optional Config fields; no second call-site abstraction.
4. **Rewrite only in the indexer, leave adapter unaware** — rejected: the process boundary owns the wire path; rebasing belongs next to the request/reply (one place).
5. **Core appends adapter entry script for Docker** — rejected: task 005 already froze complete-argv; language path in core would break R1.1.

### Assumptions

| Assumption | verified / novel-untested | If novel-untested 3p/runtime → spike OR integration-shaped proving test |
|------------|---------------------------|--------------------------------------------------------------------------------|
| A1 | Repo-relative requests already work under host `CA_PHP_CMD` | **verified** — `tests/test_php_adapter_server.py`, CI host PHP |
| A2 | PHP adapter echoes request `path` into result + node `file_path` | **verified** — `adapters/php/src/Visitor.php:46-48`; README:44-45 |
| A3 | Fake adapter can echo the requested path into a File-shaped node for rebase proof without PHP/Docker | **verified** — `tests/fixtures/adapter/fake_adapter.py` already speaks the protocol |
| A4 | `Path.is_relative_to` / `relative_to` is enough for host→container rewrite (no `realpath`) | **novel-untested** (stdlib) | **Unit proving test** on synthetic roots — fails if join/prefix logic is wrong |
| A5 | Docker users can set container `working_dir` to the mounted repo so **relative** paths need no rewrite | **verified** (operational doc, not runtime-proven here) — live Docker excluded (AC4); relative pass-through is the documented happy path |

No unresolved novel-untested **third-party/runtime** assumption blocking Gate 2.

### Smallest change list

| # | Change | File / area | Ph2 covered by | k/N |
|---|--------|-------------|----------------|-----|
| 1 | Add `host_root` / `container_root` knobs + pair validation + `to_adapter_path` | `code_atlas/config.py` | R3, R4, C1, C2, C6, inv B | 0/6 |
| 2 | Pass roots into `SubprocessAdapter`; wire rewrite + rebase reply paths to caller `path` | `code_atlas/adapter.py` | G1, R3, R4, C1, C6, AC1 | 0/6 |
| 3 | Thread roots from `Config` in `_adapter`; unset CMD error includes `CA_{KEY}_CMD` | `code_atlas/indexer.py` | AC2, G1, C2 | 0/3 |
| 4 | Knob precedence cases + `len(KNOB_KEYS)==9` + env_name list; pair-error cases; `to_adapter_path` units | `tests/test_config.py` | R3, C3, inv B, blast radius | 0/4 |
| 5 | **Proving test** + rebase integration via fake adapter; unset-CMD message; host relative no-op | `tests/test_adapter.py` (and/or small `tests/test_path_mapping.py`) | AC1, AC2, C3, C6 | 0/4 |
| 6 | **Proof collateral** — any `SubprocessAdapter(` / `_adapter` call sites that need the new optional args (defaults `None` keep host callers green) | `tests/test_adapter.py`, `tests/test_indexer.py`, `tests/test_php_adapter_server.py`, `tests/test_resolver.py` as needed | blast radius | 0/1 |
| 7 | Docs: PLAN §9/§11 knobs; CONVENTION env list; README table + Docker roots example; PHP README host/Docker + tokenizer | `docs/PLAN.md`, `docs/CONVENTION.md`, `README.md`, `adapters/php/README.md` | R1, R2, R5, C4, C5 | 0/5 |
| 8 | Record AC4 exclusion; BACKLOG 008 → in-progress/done + frontmatter (status at execute/finalise) | this file + `docs/BACKLOG.md` | AC3, AC4, R6, C4 | 0/4 |
| 9 | **Do not** add compose / Docker service to `.github/workflows/ci.yml` | (absence) | AC3 | 0/1 |

**Test blast-radius trace (mechanical).**

- `tests/test_config.py`: `len(KNOB_KEYS) == 7` → **9**; `KNOBS` table + `env_name` ordered list — **must** grow (item 4). Only `Config(...)` construction: `config.py` `load_config`.
- `SubprocessAdapter(` in tests — grep consumers; new optional kwargs default `None` so existing constructors stay valid; item 6 only if a call must pass roots for a new case.
- `indexer._adapter` / `has no configured command` — one raise site; update message + any test matching the old string.
- `test_core_is_language_agnostic` / `test_sql_confinement` — no language names, no SQL in adapter/config; expect green without edits.
- No `docker-compose` / CI job changes (item 9).

### Rule compliance

- **R1.1 / R1.4:** generic roots + pure path helper; no `php` branch; adapter still parse-transport only.
- **R5.3:** pair rule + unset CMD + bad absolute outside host_root fail loud.
- **R4.2:** rewrite is pure prefix/join; identical inputs → identical wire path.
- **R6.1 / R7.2 / R8.1:** tests + docs + adapter launch runbook.
- **CONVENTION:** store paths remain repo-relative after rebase.

### Proving test

**Name:** `test_absolute_host_paths_are_rewritten_on_the_wire_and_caller_paths_are_preserved`

**Invocation:** `.venv/bin/pytest -q tests/test_adapter.py::test_absolute_host_paths_are_rewritten_on_the_wire_and_caller_paths_are_preserved`

**Shape:** Fake adapter records the JSON `path` it received and echoes it into `result.path` + a Class node `file_path`/`qualified_name`. Driver configured with synthetic `host_root`/`container_root`. Absolute-under-host `parse`: (1) wire under `container_root`; (2) `ParseResult` keeps the **caller** path (Approach §3). Relative `parse`: wire and store-facing paths stay repo-relative. **Fails pre-change** (no roots / no rewrite / no rebase). **Passes post-change.**

Companion asserts (same PR): unset `CA_PHP_CMD` → message matches `CA_PHP_CMD`; `to_adapter_path` relative pass-through; half-set roots → `ConfigError`.

### Verification plan

| AC | risk layer | proof artifact | layer-match? |
|----|------------|----------------|--------------|
| AC1 (host relative + synthetic map) | logic (rewrite) + integration (wire/rebase via fake adapter) | unit + integration proving test above | ✅ |
| AC1 (live Docker↔host identity) | runtime-3p / e2e | **manual-recorded exclusion** (AC4) | ✅ (excluded) |
| AC2 | integration (indexer/adapter launch path) | unit/integration `match=CA_PHP_CMD` / `cannot run` | ✅ |
| AC3 | process (CI surface) | absence of compose service in diff + review check | ✅ |
| AC4 | process | Coverage-gap exclusions row below | ✅ |

### Coverage-gap exclusions

| Item | Risk tier | Why deferred | Follow-up |
|------|-----------|--------------|-----------|
| Live Docker↔host identical parse on a real `docker compose exec` | runtime-3p / e2e | No in-repo compose; CI is host-PHP only; ratified Gate 1 want #1 (option 2) | Optional later chore if a shared compose fixture appears; not on critical path to 014 |

### Proof manifest (frontend)

**N/A — TRACK backend.**

### Rollback + porting

- Revert the feature branch / PR. No schema migration; knobs default `None` so absent config is unchanged host behaviour.
- Single repo (`app` / `.`); no porting order.

### SCOPE confirmed

**SCOPE: M** — unchanged (config + adapter wire/rebase + indexer error + tests + docs; no CI Docker). Did not outgrow analysis.

- **Gate 2 status:** **cleared** — approach + change-list + proving test + coverage-gap ratified 2026-08-01 (user: "approve")

---

## Phase 3 — Execute

- **Branch:** `feat/008-php-runtime-modes`
- **Commits (logical units; no AI co-author trailer):** pending at write-time — core / tests / docs
- **Proving test added:** `tests/test_adapter.py::test_absolute_host_paths_are_rewritten_on_the_wire_and_caller_paths_are_preserved` (+ unset-CMD + `to_adapter_path` units)
- **Verification sweep — BOTH axes.**
  - *File axis:* zero stray references ✅ · diff ⊆ approved list ✅ · each hunk maps to a row ✅
  - *Behaviour axis:* Approach bullets 1–6 → `implemented-as-approved` (knobs+pair, `to_adapter_path`, wire+rebase, unset CMD names env, docs, proofs+AC4 exclusion; no CI compose)
- **Design-conformance deviations:** none
- **Design-invalidation / re-gate:** n/a
- **Suite:** `.venv/bin/pytest -q` → **395 passed** (baseline 388 + 7 new)

**Ph3/4 proven by (delta):** AC1 proving test + relative no-op; AC2 `match=CA_PHP_CMD`; R3 pair fail-loud + knob precedence N=9; inv B both roots; AC3/AC4 by absence of CI compose + exclusion row; docs R1/R2/R5.

---

## Phase 4 — Review ✋ (stop only if not clean)

- **reviewer verdict:** round 1 **CHANGES REQUESTED** (Important: proving-test name/shape overclaimed repo-relative on absolute half) → fix landed in `590ee7d` → **verify-only** (main-loop): finding 1 addressed; suite **395 passed**; no re-dispatch.
- **challenger (ticket-blind):** MET 7 · NOT MET 0 · CAN'T TELL 1 (literal live Docker dual-mode = AC4 exclusion)
- **security agent:** n/a
- **Scope reconciliation:** diff ⊆ approved list; no CI compose; no reformatting creep
- **Regression:** green vs BASELINE 388 (delta +7)
- **Proving test:** renamed; wire + caller-path + relative store path asserted; would fail without rewrite/rebase
- **Layer-match:** AC1 exclusion for live Docker recorded; no unresolved ❌
- **Ph3/4 proven by:** filled for AC1–AC4, R3, inv A/B (k=N with AC4 excluded)
- **Clean?** yes (after verify-only)
- **Reviewed at:** `590ee7d5fe991e9ae9b88932ae067a77002e0d48` · reviewed files: `code_atlas/config.py`, `code_atlas/adapter.py`, `code_atlas/indexer.py`, `tests/test_config.py`, `tests/test_adapter.py`, `tests/fixtures/adapter/fake_adapter.py`, `README.md`, `adapters/php/README.md`, `docs/PLAN.md`, `docs/CONVENTION.md`, `docs/BACKLOG.md`, `docs/tasks/008_php-runtime-modes.md`

## Phase 5 — Finalise ✋ final gate

- **PR draft:** `/tmp/pr-008.md`
- **Planned outward actions:** A commit bookkeeping · B push · C open PR · D mark done — user **"ok"** (2026-08-01)
- **Follow-up tickets:** none (AC4 exclusion stands; no deferred matrix row needing a new card)
- **Durable lesson:** yes — proving-test names must not overclaim path shape → `docs/LESSONS.md` (008)
- **Revert path:** revert the feature branch / PR; knobs default unset → host behaviour unchanged

## Session status

- **Last updated:** 2026-08-01
- **Current phase:** Phase 5 — Finalise (executing approved outward actions)
- **Next action:** push + open PR
- **Blocked on:** none

---

## Cost ledger (descriptive — facts only, never auto-cuts)

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| refine | challenger (exposure-checker) | 1 | unmeasured (blocking retrieval) | none |
| analysis | extractor (path-mapping facts) | 1 | unmeasured (blocking retrieval) | none |
| review | reviewer | 1 | unmeasured (blocking retrieval) | none |
| review | challenger | 1 | unmeasured (blocking retrieval) | none |

`LEDGER TOTAL:` unmeasured (blocking retrieval) ×4 · top cost driver: review (2 dispatches)

---

## Decision log

| When | Decision | Why |
|------|----------|-----|
| 2026-08-01 refine | Want #1 → named coverage-gap (option 2) | User chose; ticket Scope fork; 008 off critical path to 014 |
| 2026-08-01 refine | work_doc_mode=separate (initial) | Committed stub default from solve |
| 2026-08-01 | work_doc_mode→embed; merge into task file; delete `.work.md` | User: honour harness embed — update existing tasks, no separate work doc |
| 2026-08-01 Gate 1 | AC1/AC2 pins + AC4 exclusion + SCOPE M / TIER full **cleared** | User: "approve" |
| 2026-08-01 Gate 2 | Approach + change-list 1–9 + proving test **cleared** | User: "approve" |
| 2026-08-01 review | Rename proving test; verify-only clean | Reviewer finding 1 |

## Session status

- **Last updated:** 2026-08-01
- **Current phase:** Phase 4 clean → Phase 5 Finalise · **final gate waiting**
- **Next action:** User approves each outward action (push / PR / status); commit working-doc bookkeeping first if needed
- **Blocked on:** final-gate per-action approvals
