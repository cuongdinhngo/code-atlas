---
id: 003
slug: config-and-ignore
title: Config (CA_*) & ignore rules
phase: 1
milestone: Setup
status: done
depends_on: [001]
---

## Goal
Central config resolution and file-ignore logic (§11).

## Scope / Deliverables
- `config.py`: env `CA_*` → project file → defaults. Knobs: `CA_DB_PATH` (default `<repo>/.code-atlas/graph.db`), `CA_WORKERS`, `CA_MAX_RESULTS`, `CA_IMPACT_DEPTH=2`, `CA_IMPACT_MAX_NODES=500`, per-adapter `CA_<LANG>_CMD`, `CA_TOOLS` allow-list.
- `ignore.py`: built-ins (`vendor/ var/ uploads/ log/ node_modules/ .git/`) + `.gitignore` + optional `.codeatlasignore`.

## Acceptance criteria
- Precedence (env > project file > default) covered by tests.
- Ignore matcher unit-tested against built-ins, `.gitignore`, and `.codeatlasignore` cases.

## References
Plan §11.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 003 — Config (CA_*) & ignore rules (working doc)

- **Ticket:** 003 · [`docs/tasks/003_config-and-ignore.md`](003_config-and-ignore.md) (local-file ticket)
- **Type:** enhancement (new core capability; no bug to root-cause)
- **Repo(s) / Porting:** `app` (`.`) only — single-repo project, no porting
- **work_doc_mode:** `embed` (`.harness.json:13`) — working doc appended below the separator, as in task 002
- **SCOPE:** M
- **STRUCTURE:** native (all four ticket headers map to `config.ticket_header_schema`)
- **TRACK:** backend — `0/6` touched files under UI paths (no UI exists; `config.track = "backend"`)
- **TIER:** full (SCOPE=M, multiple files, universal requirement with N=7 > 1)
- **BASELINE:** **green** — `pytest -q` → 34 passed; `ruff check .` → clean; `mypy` → no issues (untouched `main` @ `8431e89`, worktree clean)
  <!-- baseline exclusions: none -->

---

## Phase 0 — Refine

`REFINE: not run for this ticket | skip: n/a` — the ticket is a pre-written scaffold stub with native
sections; unresolved product-decisions are surfaced below as Gate-0/1 clarifications instead.

---

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope / Deliverables, Acceptance criteria, References) | 4 decomposed | ROWS: C=6 R=2 G=1 AC=2`

*"References" carries no requirement — it is decomposed as the evidence pointer (PLAN §11) used
throughout this analysis. C rows are constraints surfaced from the rulebook scan (the ticket has no
Constraint section); they are binding on the change and are listed so every hunk can trace to a row.*

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | "Central config resolution and file-ignore logic (§11)." | One place resolves every `CA_*` knob; one place decides whether a path is ignored. No other module re-reads `os.environ` or re-lists ignore patterns. | `code_atlas/config.py:1`, `code_atlas/ignore.py:1` are one-line stubs; zero importers repo-wide (grep over `code_atlas/`, `tests/`) | **2/2** (items 1, 2) | **2/2** — `config.py`, `ignore.py` written; 86 tests green | ✅ |
| R1 | Scope / Deliverables | "`config.py`: env `CA_*` → project file → defaults. Knobs: `CA_DB_PATH` (default `<repo>/.code-atlas/graph.db`), `CA_WORKERS`, `CA_MAX_RESULTS`, `CA_IMPACT_DEPTH=2`, `CA_IMPACT_MAX_NODES=500`, per-adapter `CA_<LANG>_CMD`, `CA_TOOLS` allow-list." | A three-layer resolver over **7** knobs (inventory A). `CA_<LANG>_CMD` must be a generic lookup, never a language branch (R1.1). | `config.py:1` stub; knob list matches CONVENTION §2 (`CONVENTION.md:47-48`) and PLAN §11 (`PLAN.md:274`), which omits `CA_TOOLS` — it is specified at `PLAN.md:295` | **5/5** (items 1, 5, 6, 7, 8) | **5/5** — 7 knobs resolve, 3 layers each; docs match | ✅ |
| R2 | Scope / Deliverables | "`ignore.py`: built-ins (`vendor/ var/ uploads/ log/ node_modules/ .git/`) + `.gitignore` + optional `.codeatlasignore`." | A matcher over **3** ordered sources (inventory B) with **6** built-in patterns; `.codeatlasignore` is optional (absent ⇒ no error). | `ignore.py:1` stub; pattern list verbatim from `PLAN.md:274`; `.codeatlasignore` name fixed by `CONVENTION.md:49` | **4/4** (items 2, 4, 5, 8) | **4/4** — 6 built-ins + 2 files; 23 ignore cases | ✅ |
| AC1 | Acceptance criteria | "Precedence (env > project file > default) covered by tests." | For **each** of the 7 knobs, tests assert all three layers and their ordering — a per-item checklist, not one aggregate test (inventory A). | No `tests/test_config*.py` exists | **7/7** (item 3 — 28 assertions over the 7 knobs) | **7/7** — 28 assertions, 7 parametrized ids | ✅ |
| AC2 | Acceptance criteria | "Ignore matcher unit-tested against built-ins, `.gitignore`, and `.codeatlasignore` cases." | Named unit cases per source, including near-miss **non**-matches (a matcher that ignores everything would pass a match-only suite). "cases" is not falsifiable as written → pinned in AC validation. | No `tests/test_ignore*.py` exists | **3/3** (item 4 — 16 named cases over the 3 sources) | **3/3** — 23 cases incl. 4 near-miss non-matches | ✅ |
| C1 | rulebook scan | R1.1 — "No `if language == "php"` (or any per-language switch) anywhere under `code_atlas/`." | `CA_<LANG>_CMD` resolves via `f"CA_{language.upper()}_CMD"`; no hardcoded language name or language list in `config.py`. | `ENGINEERING_RULES.md:18-19`; CI gate `.github/workflows/ci.yml:46-53` | **1/1** (item 1 — regex env lookup, no language list) | **1/1** — R1.1 gate re-run clean; unknown-language test | ✅ |
| C2 | rulebook scan | R5.3 — "Fail loud on *config/programmer* errors (bad `CA_*`, missing adapter command)." | A malformed value (non-int workers, unknown project-file key) raises; it never silently falls back to the default. | `ENGINEERING_RULES.md:77-78` | **2/2** (items 1, 3) | **2/2** — 8 fail-loud cases, all ConfigError | ✅ |
| C3 | rulebook scan | R8.2 — "Keep core dependencies minimal (FastMCP + stdlib-first)." | Ignore matching and project-file parsing use stdlib only (`fnmatch`/`re`, `tomllib`). Adding `pathspec` needs an explicit human call → Q5. | `ENGINEERING_RULES.md:113-114`; `pyproject.toml:12` | **1/1** (item 2 — `re` + `pathlib`, `tomllib` for item 1) | **1/1** — stdlib only; `pyproject.toml` unchanged | ✅ |
| C4 | rulebook scan | R4.2 — "Identical input → identical output." | Pattern iteration order is deterministic; `os.cpu_count()` (the `CA_WORKERS` default) is machine-dependent, so it must be injectable and never leak into stored rows. | `ENGINEERING_RULES.md:65-67`; `PLAN.md:227` (`min(cpu-2, 8)`) | **3/3** (items 1, 2, 3) | **3/3** — identical-input + 3 cpu_count cases | ✅ |
| C5 | rulebook scan | R1.4 / R7.5 — SRP per module; comments ≤ 3 lines. | `config.py` resolves config only, `ignore.py` matches only; neither imports `store.py` or an adapter. Every comment ≤ 3 lines. | `ENGINEERING_RULES.md:26-31`, `104-105` | **2/2** (items 1, 2) | **2/2** — ruff/mypy clean; no cross-import | ✅ |
| C6 | rulebook + `CLAUDE.md` scan | R7.2 — "A design decision updates the plan; task status updates both `BACKLOG.md` and the task file's frontmatter" + CLAUDE.md's "Docs before PR" / "Token usage on PR" | The four ratified values that exist nowhere in the repo (`.code-atlas.toml`, `CA_MAX_RESULTS=50`, `CA_TOOLS` format, the worker floor) land in PLAN/CONVENTION/README in **this** diff, plus status + token-ledger sync. | `ENGINEERING_RULES.md:98-99`; `CLAUDE.md` "Docs before PR"; `LESSONS.md:16` (untraceable governance hunks read as scope creep) | **5/5** (items 5, 6, 7, 8, 9) | **5/5** — PLAN, CONVENTION, README, BACKLOG, frontmatter | ✅ |

Status legend: ✅ done/proven · ⚠ deferred (needs follow-up ticket) · ❌ not met · ⬜ not yet started (Phase 1).

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| AC1 | "Precedence … covered by tests" (no count) | **7 knobs × 3 layers = 21 assertions**, plus 7 ordering assertions (env wins over file, file wins over default) | **N** (ticket gives no denominator) | measurable/greppable (per-knob test exists + asserts each layer) | **Q6** — confirm AC1 means per-knob (N=7), not one aggregate test |
| AC1 | `CA_IMPACT_DEPTH=2` | `2` — `PLAN.md:274` | Y | measurable | — |
| AC1 | `CA_IMPACT_MAX_NODES=500` | `500` — `PLAN.md:274` | Y | measurable | — |
| AC1 | `CA_DB_PATH` default `<repo>/.code-atlas/graph.db` | same — `PLAN.md:274`, `CONVENTION.md:49` | Y | measurable | — |
| AC1 | `CA_WORKERS` — no default stated | `max(1, min((os.cpu_count() or 1) - 2, 8))` — `PLAN.md:227` gives `min(cpu-2, 8)`; the `max(1, …)` floor and the `or 1` guard are **my additions** (a 1–2-core host would otherwise get 0 workers; `os.cpu_count()` may return `None`) | **N** → **resolved Q3a** | measurable | **RATIFIED** — floor + `or 1` guard adopted; `PLAN.md:227` to be corrected in the Phase-2 change-list |
| AC1 | `CA_MAX_RESULTS` — no default stated | **no source anywhere** in PLAN/CONVENTION/ticket. Computed **50** | **N** → **resolved Q3b** | measurable | **RATIFIED** — `50`; `PLAN.md:274` to gain the value in the Phase-2 change-list |
| AC1 | `CA_TOOLS` "allow-list" — no format or default stated | Comma-separated tool names; **unset or blank ⇒ all 11 tools** (`PLAN.md:283-293` lists 11). Enforcement lives in task 010 | **N** → **resolved Q4** | measurable | **RATIFIED** — `tuple[str, ...] \| None`, `None` = unrestricted; parse-only here |
| AC1 | `<repo>` in the `CA_DB_PATH` default | Undefined — nothing says how the repo root is discovered (`gitutil.py` is task 016) | **N** → **resolved Q2** | measurable | **RATIFIED** — `load_config(root, env=None)`, caller supplies `root`; no `CA_REPO_ROOT` knob |
| AC1 | "project file" layer | **Unnamed and unformatted** anywhere in PLAN/CONVENTION/README — the middle precedence layer has no artifact to read | **N** → **resolved Q1** | measurable | **RATIFIED** — `.code-atlas.toml` at repo root, flat lowercase keys + `[adapter_cmd]` table, stdlib `tomllib` |
| AC2 | "built-ins, `.gitignore`, and `.codeatlasignore` **cases**" | "cases" is a vague adjective — no count, no semantics. Computed pin: **≥14 named cases across 3 sources** (6 built-in matches at root + nested, 2 near-miss non-matches, 5 `.gitignore` syntax cases, 2 `.codeatlasignore` cases incl. additivity) | **N** → **resolved Q5** | **now falsifiable** — the ratified subset fixes the case list at ≥14 named cases | **RATIFIED** — stdlib subset, last-match-wins across the 3 sources, no re-include under an excluded directory |

**No AC carries a `✅` in the matrix** *(as of Phase 1 — rows were filled `✅` at Phase 4, each with
its proving test named)*. Every acceptance
value is now falsifiable (no manual-check exclusion needed): each knob's default is a concrete value a
test can assert, and AC2's "cases" is pinned to an enumerated list by the ratified Q5 subset.

**Uncodified-standard items surfaced (never silently applied, never silently dropped):**

1. **A gitignore-semantics subset is a standard, not a detail.** Deciding which gitignore syntax we
   honour (`!` negation, `**`, anchoring, dir-only `/`, nested `.gitignore` files) is a going-forward
   project standard with no rule in `docs/ENGINEERING_RULES.md`. Surfaced as **Q5**; route through
   `/mango:codify` provisional→ratify if you want it written down. Until ratified it does **not**
   gate-block.
2. **Ecosystem directory names in the core.** The built-in ignore list (`vendor/`, `var/`, `log/`,
   `uploads/`) contains ecosystem-flavoured names. **R2.2 binds adapters only** (`ENGINEERING_RULES.md:44-45`)
   and the CI gate is scoped to `adapters/` (`ci.yml:58`) — so this is compliant, and PLAN §11 mandates
   the list verbatim. Recorded so review does not re-litigate it as an R2 violation.

## Inventory (universal "all/every/no" requirements)

Two counted denominators. AC1 is a "do X for each of N" requirement → the list below **is** the
per-item checklist; review must confirm every row, not a total.

### Inventory A — `CA_*` knobs (AC1 / R1) · **Denominator N = 7**

Every row's default is ratified (Gate 0 cleared). Each knob needs 3 layer assertions (env / project
file / default) + 1 ordering assertion ⇒ **28 assertions** over the 7 rows.

| # | Knob | Project-file key | Ratified default | Ph3/4 proven by | Status |
|---|------|------------------|------------------|-----------------|--------|
| 1 | `CA_DB_PATH` | `db_path` | `<root>/.code-atlas/graph.db`, `root` supplied by the caller (`PLAN.md:274`; Q2) | `test_env_beats_project_file_beats_default[CA_DB_PATH]` + `test_an_absolute_db_path_wins_over_the_root` | ✅ |
| 2 | `CA_WORKERS` | `workers` | `max(1, min((os.cpu_count() or 1) - 2, 8))` (`PLAN.md:227` + Q3a floor) | `…[CA_WORKERS]` + `test_the_worker_default_is_floored_and_capped[1/3/64-cpus]` | ✅ |
| 3 | `CA_MAX_RESULTS` | `max_results` | `50` (Q3b — new value, no prior source) | `…[CA_MAX_RESULTS]` — default asserted as 50 | ✅ |
| 4 | `CA_IMPACT_DEPTH` | `impact_depth` | `2` (`PLAN.md:274`) | `…[CA_IMPACT_DEPTH]` — default asserted as 2 | ✅ |
| 5 | `CA_IMPACT_MAX_NODES` | `impact_max_nodes` | `500` (`PLAN.md:274`) | `…[CA_IMPACT_MAX_NODES]` — default asserted as 500 | ✅ |
| 6 | `CA_<LANG>_CMD` (generic) | `[adapter_cmd].<lang>` | `None` (absent ⇒ `None`; fail-loud at launch, task 005) | `…[CA_PHP_CMD]` + `test_any_language_resolves_without_a_core_change` | ✅ |
| 7 | `CA_TOOLS` | `tools` | `None` = unrestricted; unset **or** blank ⇒ `None` (Q4) | `…[CA_TOOLS]` + `test_the_tool_allow_list_parses` ×4 | ✅ |

**Out of scope, recorded so review does not read it as a miss:** `CA_HOST_ROOT` / `CA_CONTAINER_ROOT`
(`PLAN.md:245`, Docker path mapping) are real `CA_*` knobs but belong to **task 008**; the ticket's knob
list omits them and N stays **7**.

### Inventory B — ignore sources (AC2 / R2) · **Denominator N = 3**, built-in patterns **6**

| # | Source | Cases to cover | Ph3/4 proven by | Status |
|---|--------|----------------|-----------------|--------|
| 1 | Built-ins: `vendor/`, `var/`, `uploads/`, `log/`, `node_modules/`, `.git/` | each of the 6 matched at repo root **and** nested; 2 near-miss non-matches (`vendored/`, `src/vendor.php`) | `test_a_builtin_directory_is_ignored_at_root_and_nested` ×6 + `test_a_near_miss_is_not_ignored` ×4 | ✅ |
| 2 | `.gitignore` | comment/blank skipped · `*.log` glob · anchored `/build` · dir-only `dist/` · `!` negation (subset per ratified **Q5**) | comments · glob · anchor · dir-only · class/`?` · `**` · negation (7 tests) | ✅ |
| 3 | `.codeatlasignore` (optional) | absent ⇒ no error · patterns apply **additively** to sources 1–2 · a `!` here re-includes a built-in/`.gitignore` match, **unless** a parent directory is excluded | last-match-wins · additive · no-re-include-under-excluded-dir · absent-file (4 tests) | ✅ |

### Surface inventory

**N/A — TRACK is backend.** No reachable UI surface exists in this repo (no routes, templates, or
frontend entry points; `code_atlas/tools/` is an MCP tool surface, not a rendered one).

## Clarifications

`CLARIFICATION: 11 raised | 11 resolved (5 self-resolved+cited · 6 human-ratified at Gate 0) | 0 for human decision`

**Gate 0: CLEARED** — the user explicitly ratified all six recommendations (Q1–Q6) on 2026-07-29. None
of them reverses a prior decision; Q3a, Q3b, Q4 and Q1 add values `PLAN.md`/`CONVENTION.md` never
carried, so those doc updates ride the Phase-2 change-list (R7.2).

**Self-resolved (cited):**

1. **`CA_<LANG>_CMD` without a language branch.** `config.py` exposes a generic
   `adapter_cmd(language)` → `os.environ.get(f"CA_{language.upper()}_CMD")`; no language name or list
   appears in the core. *R1.1 (`ENGINEERING_RULES.md:18-19`) + R1.2 (`:20-22`) — no registry until
   adapter #2.*
2. **Where "missing adapter command" fails loud.** Not at config load — `config.py` has no language
   list to validate against (`adapter.py:1` is a stub, task 005). Config returns `None`; the launch
   site raises. *R5.3 (`:77-78`) pairs "missing adapter command" with the launch, and R1.2 forbids
   inventing a registry here.*
3. **Unknown key / malformed value handling.** Both raise a loud config error rather than falling back
   to the default. *R5.3 (`:77-78`).*
4. **`.codeatlasignore` name and location.** Exactly that spelling, at the repo root, optional.
   *`CONVENTION.md:49`; ticket line 16 ("optional").*
5. **Ignore built-ins in the core are not an R2 violation.** R2.2 binds adapter source only and the CI
   grep-gate is scoped to `adapters/`. *`ENGINEERING_RULES.md:44-45`; `ci.yml:55-63`; list mandated by
   `PLAN.md:274`.*

**Human-ratified at Gate 0 — 6 items (asked with a recommendation each; all recommendations adopted
verbatim, 2026-07-29):**

- **Q1 — What is the "project file"?** *(blocking — one of AC1's three precedence layers had no
  artifact to read.)* **Ratified: `.code-atlas.toml` at the repo root**, flat lowercase keys
  (`db_path`, `workers`, `max_results`, `impact_depth`, `impact_max_nodes`, `tools`) plus an
  `[adapter_cmd]` table (`php = "…"`), parsed with stdlib `tomllib`.
  *Why:* (i) it **cannot** live under `.code-atlas/` — that directory is gitignored (`.gitignore:2`)
  and a project config must be committable team-wide; (ii) the env↔file mapping is mechanical
  (`CA_<KEY>` ↔ `<key.lower()>`), so the precedence loop is data-driven over one knob tuple with no
  per-knob mapping table; (iii) `[adapter_cmd].<lang>` gives knob #6 the same three layers as the other
  six while keeping the lookup generic (R1.1); (iv) `tomllib` is stdlib on `requires-python >=3.12`
  (`pyproject.toml:10`), so no new dependency (R8.2). Rejected: `.code-atlas.json` (no comments) and
  `[tool.code-atlas]` in `pyproject.toml` (couples a per-repo index config to a Python build file —
  wrong for indexing a PHP repo). Unknown key ⇒ raise (R5.3).
- **Q2 — Repo-root resolution.** **Ratified: `load_config(root: Path, env: Mapping[str, str] | None = None)`**
  — the caller supplies `root` (`main.py`, task 010, from CWD). *Why:* pure function, hermetic tests,
  and it matches "config flows in, isn't reached out to" (`CONVENTION.md:72`). Rejected: git-toplevel
  discovery (pulls `gitutil.py` forward from task 016) and a `CA_REPO_ROOT` knob (makes N=8 and is
  circular — the root is needed to *find* the project file).
- **Q3a — `CA_WORKERS` default.** **Ratified: `max(1, min((os.cpu_count() or 1) - 2, 8))`.**
  *Why:* `PLAN.md:227`'s literal `min(cpu-2, 8)` yields 0 or a negative on a 1–2-core host, and
  `os.cpu_count()` can return `None`. Tests **monkeypatch `os.cpu_count`** rather than the module
  taking a `cpu_count=` parameter — no production API surface added for test convenience (R7.4), while
  still satisfying C4's injectability. `PLAN.md:227` gets corrected in the Phase-2 change-list.
- **Q3b — `CA_MAX_RESULTS` default.** **Ratified: `50`.** *Why:* ~50 rows × ~20 tokens ≈ 1k tokens per
  call — within the token-efficiency goal without truncating results on a large repo; `search_symbol`
  keeps its own `limit?` override (`PLAN.md:285`). This value exists nowhere in the repo today, so
  `PLAN.md:274` gains it in the Phase-2 change-list.
- **Q4 — `CA_TOOLS` format, default, enforcement boundary.** **Ratified:** comma-separated names →
  `tuple[str, ...] | None`; **unset *or* blank ⇒ `None` = unrestricted** (all 11 tools,
  `PLAN.md:283-293`); whitespace trimmed, input order preserved, duplicates collapsed first-wins
  (R4.2). **`config.py` parses only** — name validation and tool-registration gating land in **task
  010**. *Why the split:* `code_atlas/tools/` is empty today, so a validator here would be precisely
  the guard-that-cannot-fail from `LESSONS.md:6`. Recorded as a coverage-gap exclusion at Gate 2.
- **Q5 — `.gitignore` semantics.** **Ratified: a documented stdlib subset, no `pathspec` dependency.**
  *Why:* `PLAN.md:225` collects files through `git ls-files`, which already applies `.gitignore`, so
  our matcher mainly serves the non-git walk fallback — not worth trading R8.2
  (`ENGINEERING_RULES.md:113-114`) for.
  - **Supported:** comments/blank lines skipped · `*` `?` `[seq]` `**` globs · root-anchored `/build` ·
    dir-only `dist/` · `!` negation · a pattern without `/` matches at any depth.
  - **Not supported (stated in the module docstring):** per-directory nested `.gitignore` files ·
    `\!` / `\#` escapes.
  - **Decision order:** the three sources concatenate built-ins → `.gitignore` → `.codeatlasignore`,
    **last match wins** — so if `.gitignore` has `*.log`, a `.codeatlasignore` line `!keep.log` brings
    that file back in.
    *(Corrected during Phase 3: this bullet originally used `!vendor/keep.php` as the example, which
    contradicts the next bullet — `vendor/` is an excluded **directory**, so nothing under it can be
    re-included. The behaviour ratified is the next bullet's; only the example was wrong, and
    `tests/test_ignore.py::test_an_excluded_directory_cannot_be_re_included` pins it.)*
  - **One deliberate git-compatible restriction:** a path under an **excluded directory** cannot be
    re-included. Kept not for git fidelity but because it is what lets the walk **prune whole
    directories** — without it, task 015's 112k-file target would `stat` every file inside `vendor/`.
- **Q6 — AC1's denominator.** **Ratified: per-knob, N=7** — 21 layer assertions (7 × 3) + 7 ordering
  assertions = **28**. *Why:* one aggregate precedence test cannot show which knob was skipped.

---

## Phase 1 — Analysis ✋ Gate 1

- **Gap analysis (enhancement — per goal, with `path:line`):**

  | Goal | Current | Target | Gap |
  |------|---------|--------|-----|
  | G1 / R1 — central config resolution | `code_atlas/config.py:1` is a one-line docstring stub; **no** module reads `CA_*`; zero importers repo-wide | 3-layer resolution over 7 knobs, typed, fail-loud on bad input | Whole module. Blocked on Q1 (project-file layer) and Q2 (repo root) |
  | G1 / R2 — file-ignore logic | `code_atlas/ignore.py:1` is a one-line docstring stub; `.gitignore` exists at the repo root but nothing reads it | matcher over built-ins + `.gitignore` + optional `.codeatlasignore` | Whole module. Semantics scope blocked on Q5 |
  | AC1 / AC2 — tests | `tests/` has 34 passing tests, none touching config or ignore (`tests/test_smoke.py`, `tests/test_contract_sole_source.py`, `tests/contract/test_contract_schema.py`) | per-knob precedence suite + enumerated ignore case suite | Both suites absent |

- **Handler / entry point + blast radius:** No entry point exists — `code_atlas/main.py:1` is a stub
  (task 010). **Current blast radius: zero.** `grep -rn "config\|ignore" --include=*.py code_atlas/ tests/`
  returns only the two stub docstrings, so nothing imports either module today. **Future consumers**
  (all stubs, all downstream tasks): `store.py:1` ← `CA_DB_PATH` (004) · `adapter.py:1` ←
  `CA_<LANG>_CMD` (005) · `indexer.py:1` ← `CA_WORKERS` + ignore matcher (009) · `main.py:1` ←
  `CA_TOOLS` (010) · `tools/` ← `CA_MAX_RESULTS`, `CA_IMPACT_*` (013/014/017). Repos touched: `app`
  only. No `db-map` exists (`config.db_kind` is null) — no schema dependents.

  **Vacuity warning (`LESSONS.md:6`).** Because every consumer is a stub, two behaviours this ticket
  names **cannot** be proven here: `CA_TOOLS` enforcement and `CA_<LANG>_CMD` fail-loud-at-launch.
  Both are recorded as coverage-gap exclusions at Gate 2 rather than closed with a self-reported ✅.

- **Rule-compliance section coverage** (applicable sections derived from the change type: *new core
  Python module + new test suite*; no migration/schema, no UI surface, no contract change):

  `RULE SECTIONS: §1 ✅ · §2 N/A (adapter-only; core built-ins recorded above) · §3 N/A (no contract vocabulary/field/qname change — `CA_*` knobs are not contract fields) · §4 ✅ · §5 ✅ · §6 ✅ · §7 ✅ · §8 ✅`

  | § | Applicable? | Check |
  |---|-------------|-------|
  | §1 Architectural boundaries | ✅ mandatory (new core module) | R1.1 generic `CA_<LANG>_CMD` lookup (C1) · R1.2 no registry/factory/DI (R7.4) · R1.3 no parser import · R1.4 config resolves / ignore matches, neither imports `store.py` (C5) · R1.5–R1.6 N/A (no adapter surface here) |
  | §2 Standard over sample | N/A | R2.1–R2.3 bind **adapter** source; this change touches `code_atlas/` only. Core built-in ignore names recorded as a non-violation above |
  | §3 Contract frozen & versioned | N/A | No node/edge vocabulary, field, or qname change ⇒ no `contract_version` bump, no conformance update. `config.py` must not re-declare any contract field (R3.2) |
  | §4 Determinism & purity | ✅ mandatory | R4.1 env + file reads only, no network/LLM · R4.2 deterministic pattern order; `os.cpu_count()` injectable (C4) · R4.3 N/A (no SQLite) |
  | §5 Error handling | ✅ mandatory (this **is** the config module R5.3 names) | Bad `CA_*` / unknown project-file key ⇒ raise (C2). R5.1–R5.2 N/A (no parsing, no edges) |
  | §6 Testing | ✅ mandatory | R6.1 tests are the ACs themselves · R6.2 N/A (no language fixtures) · R6.4 no new grep-gate needed |
  | §7 Change discipline | ✅ mandatory | R7.1 smallest useful · R7.4 no dead abstractions — one frozen dataclass, not a Config hierarchy · R7.5 comments ≤ 3 lines (C5) |
  | §8 Dependencies | ✅ mandatory (a `pathspec` temptation exists) | R8.2 stdlib-only (`tomllib`, `fnmatch`/`re`, `pathlib`); any new dependency needs the Q5 decision (C3) |

- **Self-audit:** 4/4 sections decomposed ✅ · AC table complete, every acceptance value falsifiable or
  pinned by a Gate-1 question, **no AC carries a bare ✅** ✅ · `BASELINE: green` captured on the
  untouched checkout ✅ · inventory denominators set (A: N=7, B: N=3) with per-item checklists ✅ ·
  matrix `Status` filled (all `⬜`, Phase 1) ✅ · `RULE SECTIONS` emitted, every applicable section
  checked or N/A-with-reason ✅ · `STRUCTURE: native`, `TRACK: backend`, `TIER: full`, `SCOPE: M`
  declared ✅ · Surface inventory N/A (backend track) ✅ · **`j = 0` — Gate 0 cleared by explicit
  human ratification of Q1–Q6** ✅.
- **Gate 1 status:** **cleared** (2026-07-29) — all six clarifications ratified, every acceptance value
  falsifiable, baseline green. Proceeding to design.

## Phase 2 — Design ✋ Gate 2

### Approach

Two small pure-function modules, no shared abstraction between them.

**`config.py` — one data-driven knob table, one resolver loop.** A module-level tuple describes each
scalar knob once (`env name`, `project-file key`, `parser`, `default`); `load_config(root, env=None)`
loops it and applies `env → .code-atlas.toml → default` uniformly. Because the env name is derived
mechanically (`"CA_" + key.upper()`), adding a knob later is one tuple entry — no per-knob branch, and
AC1's 28 assertions are a `parametrize` over the same tuple.

- Returns a **frozen `Config` dataclass** (`slots=True`) — immutable, so "config flows in, isn't
  reached out to" (`CONVENTION.md:72`) is structurally true, not a convention.
- `CA_<LANG>_CMD` is resolved **generically by regex over the environment**: keys matching
  `^CA_([A-Z0-9_]+)_CMD$` become `{language.lower(): cmd}`, merged over the `[adapter_cmd]` table so env
  wins. Nothing anywhere enumerates languages (R1.1), and knob #6 gets the same three layers as the
  other six. Verified against the 6 scalar knob names: none ends in `_CMD`, so there is no collision.
- Parsers accept **both layers' native types** — env gives `str`, TOML gives `int`/`list` — and raise
  `ConfigError` (a bare `Exception` subclass, so no `except ValueError` swallows it) with the source
  label (`CA_WORKERS` or `.code-atlas.toml:workers`) on anything malformed. Unknown key, unknown table,
  non-string `[adapter_cmd]` value, and a TOML parse error are all loud (R5.3, C2).
- `os.cpu_count()` is called **qualified** (never `from os import cpu_count`) so `monkeypatch.setattr(os, "cpu_count", …)` reaches it (C4).
- `db_path` uses `root / raw` — verified that `Path("/repo") / "/tmp/x.db" == /tmp/x.db`, so one
  expression handles absolute and relative values. No `.resolve()`: it would make output depend on
  symlinks in the environment (R4.2).

**`ignore.py` — compile each pattern to a regex once, then last-match-wins.** `load_ignore(root)`
concatenates rules in source order (built-ins → `.gitignore` → `.codeatlasignore`) into one
`IgnoreMatcher`; `is_ignored(rel_path, is_dir=False)` walks the ancestor prefixes first, returning
`True` on the first excluded directory, then evaluates the path itself last-match-wins.

The ancestor loop is doing **two jobs at once**, which is why it is the core of the design: it makes a
directory pattern (`vendor/`) exclude everything under it, and it implements the ratified
"no re-include below an excluded directory" rule that lets task 009's walker `prune` a whole subtree
instead of stat-ing 112k files.

### Rejected alternatives

1. **`pathspec` for full gitignore fidelity** — rejected: a dependency in the core (R8.2) to make the
   *fallback* path perfect, when `git ls-files` already applies `.gitignore` on the primary path
   (`PLAN.md:225`). Revisit only if the walk fallback becomes the common case.
2. **A `Settings` class with per-knob properties / a loader class hierarchy** — rejected by R7.4 and
   R1.2: one call site, one seam in this project, and the seam is the adapter contract. A frozen
   dataclass plus a module function is the whole need.
3. **`[tool.code-atlas]` in `pyproject.toml`** — rejected at Gate 0 (Q1): couples a per-repo index
   config to a Python build file, which is wrong when the repo being indexed is PHP.
4. **Merging `config.py` and `ignore.py`** (config owns the matcher) — rejected by R1.4: resolving knobs
   and matching paths are two reasons to change. `load_ignore(root)` stays callable without a `Config`.
5. **Validating `CA_TOOLS` names inside `config.py`** — rejected: `code_atlas/tools/` is empty, so the
   check could not fail (`LESSONS.md:6`). Recorded as a coverage-gap exclusion below.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|------------|---------------------------|----------|
| `tomllib` is stdlib on the supported floor, so Q1 adds no dependency | **verified** | stdlib since 3.11; `pyproject.toml:10` requires `>=3.12`; imported successfully in this repo's venv |
| `Path(root) / "<absolute>"` yields the absolute path, so one join covers both cases | **verified** | ran it: `Path("/repo") / "/tmp/x.db"` → `/tmp/x.db` |
| `monkeypatch.setattr(os, "cpu_count", …)` reaches the default computation | **verified** | true **only** if the call is qualified `os.cpu_count()`; recorded as a design constraint above, asserted by item 3's determinism test |
| The R1.1 CI grep-gate will not false-positive on this diff | **verified** (design-time) | Ran the gate's exact regex over candidate lines. Hazard found and characterised: the gate also flags `match[^\n]*\blanguage\b`, so **any line where the token `match` precedes the word `language` fails CI** — a plain prose comment could trip it. `language … match` order is safe. Item 1's code and comments avoid the order; execute re-runs the gate locally before the PR |
| No existing assertion or call site is invalidated by this change | **verified** (mechanical, below) | see *Test blast-radius* |
| A `.gitignore` subset is sufficient for the walk fallback | **novel-untested — accepted, not deferred** | Bounded by design, not by proof: the subset's behaviour is fully pinned by item 4's 16 cases, and the untested part is *coverage of exotic gitignore syntax*, not runtime/3p behaviour — so it needs no spike. Any gap surfaces at task 009/015 as a file that should have been skipped, and widens the subset then |

No unresolved `novel-untested` third-party or runtime assumption remains → Gate 2 is not blocked on a spike.

### Test blast-radius (mechanical)

Traced to real producers/consumers, not a name grep of one directory:

- **Every test root enumerated:** `tests/test_smoke.py`, `tests/test_contract_sole_source.py`,
  `tests/contract/test_contract_schema.py` (`find . -name "test_*.py" -o -name "*_test.py"`, excluding
  `.venv`). There is no separate e2e/integration root in this repo.
- **Symbols this change exports** (`load_config`, `Config`, `ConfigError`, `IgnoreMatcher`,
  `is_ignored`, `load_ignore`, `BUILTIN_PATTERNS`, `adapter_cmd`) and the new artifact names
  (`.code-atlas.toml`, `CA_TOOLS`, `CA_MAX_RESULTS`) — grepped case-insensitively across `*.py`,
  `*.toml`, `*.json`, `*.yml`: **zero hits** outside `docs/`. Nothing to update.
- **`tests/test_contract_sole_source.py:25-28` deliberately does not list `config.py`/`ignore.py`** in
  `consumers()`. Confirmed correct, not an omission: neither module declares any of the 38 contract
  vocabulary strings (`CA_TOOLS` holds *tool* names, not node/edge kinds), so R3.2 has nothing to guard
  here. Its `len(consumers()) >= 5` self-check is unaffected.
- **`typecheck` fan-out:** `mypy` runs over all of `code_atlas` (`pyproject.toml:26`); the two modules
  gain types but no existing signature changes, so no cascade.

**Proof collateral: none.** No existing assertion breaks, no call site produces a value this change
threads. This is credible only because the blast radius is genuinely zero (both modules are stubs with
no importers) — recorded so review can check the claim rather than take it.

### Smallest change-list

| # | Change | File / area | Ph2 covered by (matrix rows) |
|---|--------|-------------|------------------------------|
| 1 | Replace the stub: `PROJECT_FILE`, defaults, the knob tuple, `ConfigError`, frozen `Config` + `adapter_cmd()`, `load_config(root, env=None)`, `_read_project_file`, per-type parsers, regex env scan for `CA_<LANG>_CMD` | `code_atlas/config.py` | G1, R1, C1, C2, C4, C5 |
| 2 | Replace the stub: `BUILTIN_PATTERNS` (6), `_Rule`, `_compile()`, `IgnoreMatcher.is_ignored()` with the ancestor loop, `load_ignore(root)` | `code_atlas/ignore.py` | G1, R2, C3, C4, C5 |
| 3 | New: 28 precedence assertions parametrized over the 7 knobs, `ConfigError` fail-loud cases (bad int, unknown key, bad TOML, non-string adapter cmd), determinism + `cpu_count` monkeypatch | `tests/test_config.py` | AC1, C2, C4 |
| 4 | New: 16 named cases — 6 built-ins × (root, nested), 2 near-miss non-matches, 5 `.gitignore` syntax cases, `.codeatlasignore` additivity + re-include, no-re-include-under-excluded-dir, absent file ⇒ no error | `tests/test_ignore.py` | AC2, R2 |
| 5 | §11: name `.code-atlas.toml`, add `CA_TOOLS` + `CA_MAX_RESULTS=50`, state the ignore subset + last-match-wins | `docs/PLAN.md` (§11, line 274) | R1, R2, C6 |
| 6 | §8.1: correct `min(cpu-2, 8)` → `max(1, min(cpu-2, 8))` | `docs/PLAN.md` (line 227) | R1, C6 |
| 7 | §2 on-disk artifacts: add `.code-atlas.toml` (committed, root) alongside `.codeatlasignore` | `docs/CONVENTION.md` (line 49) | R1, C6 |
| 8 | New **Configuration** section: knob table with defaults + a `.code-atlas.toml` example | `README.md` | R1, R2, C6 |
| 9 | 003 status `todo → in-progress → done`, both places; token-usage row | `docs/BACKLOG.md`, task frontmatter | C6 |

Nine items, every one traced to a matrix row. Item 8 is the one judgment call: README has no config
section today, and deferring it to task 010 would ship a user-facing knob set documented only in a
design doc — the "Docs before PR" rule reads on the docs the change *affects*, and this change creates
the artifact a user edits.

### Rule compliance

| Rule | How this design complies |
|------|--------------------------|
| R1.1 no language branches | `CA_<LANG>_CMD` via `^CA_([A-Z0-9_]+)_CMD$` + `dict.get(language.lower())`. No language name, no language list, no `if`/`match` on language. Gate hazard characterised in *Assumptions* |
| R1.2 / R7.4 one seam, no dead abstractions | One frozen dataclass + module functions. No loader class, no registry, no Protocol — rejected alternative 2 |
| R1.3 dependency direction | Neither module imports an adapter or a parser |
| R1.4 SRP | `config.py` resolves knobs, `ignore.py` matches paths; neither imports the other or `store.py` — rejected alternative 4 |
| R3.2 contract sole source | Neither module declares any contract vocabulary; `consumers()` legitimately unchanged (see blast radius) |
| R4.1 no network/LLM | Reads `os.environ` and up to three local files. Nothing else |
| R4.2 determinism | Rules kept in source order; duplicate `CA_TOOLS` entries collapse first-wins; no `.resolve()`; `cpu_count` isolated to one default and monkeypatched in tests |
| R5.3 fail loud on config errors | Every malformed value / unknown key raises `ConfigError` with its source label. Missing `CA_<LANG>_CMD` returns `None` — R5.3's "missing adapter command" fails at the launch site (task 005), per the Gate-0 self-resolved item 2 |
| R6.1 tests | Items 3 and 4 are the definition of done for AC1/AC2 |
| R7.1 smallest useful | Two modules, ~200 lines total, no forward-built validation for consumers that do not exist |
| R7.5 comments ≤ 3 lines | Enforced while writing; the regex translation gets a 3-line comment, not a paragraph |
| R8.2 minimal deps | `os`, `re`, `tomllib`, `pathlib`, `dataclasses` — all stdlib. Zero additions to `pyproject.toml` |
| CONVENTION §2 naming | `snake_case` functions, `PascalCase` classes, `UPPER_SNAKE` constants; `.code-atlas.toml` follows the hyphenated project name like `.code-atlas/` |
| CONVENTION §4 style | Type hints on every public function; ruff `E,F,I,UP,B` at line-length 100; mypy clean |

### Verification plan (per-AC, layer-matched)

| AC / row | risk layer | proof artifact | layer-match? |
|----------|-----------|----------------|--------------|
| AC1 precedence, 7 knobs | **logic + real-file parsing** — a pure resolver over an injected env map and a TOML file on disk | unit: `tests/test_config.py`, parametrized ×7, writing a **real** `.code-atlas.toml` in `tmp_path`; `tomllib` and `open` are never mocked | ✅ |
| AC2 ignore matching | **logic + real-file parsing** — string→regex matching plus reading two real ignore files | unit: `tests/test_ignore.py`, 16 named cases against real files in `tmp_path`, including **non**-matches so a match-everything matcher fails | ✅ |
| C1 no language branch in core | **CI grep-gate** (the only place it can fail) | the gate itself: `.github/workflows/ci.yml:46-53`, re-run locally before the PR | ✅ |
| C2 fail loud on bad config | **logic** | unit: `pytest.raises(ConfigError)` ×4 (bad int, unknown key, malformed TOML, non-string adapter cmd), asserting the source label appears in the message | ✅ |
| C4 determinism | **logic** | unit: two `load_config` calls on identical input compare equal; `cpu_count` monkeypatched to 1, 3 and 64 → 1, 1, 8 | ✅ |
| C6 docs match the work | **review-time** (no runtime failure mode) | the pre-PR self-check + reviewer/challenger reading items 5–9 | ✅ |
| `CA_TOOLS` **enforcement** | integration (tool registration) | **none in this task** → coverage-gap exclusion below | ❌ → excluded |
| `CA_<LANG>_CMD` **fail-loud at launch** | integration (subprocess launch) | **none in this task** → coverage-gap exclusion below | ❌ → excluded |

No layer mismatch stands unexcluded. Surface / proof-manifest rows: **N/A — backend track.**

### Coverage-gap exclusions

| Item | Risk tier | Why deferred | Follow-up |
|------|-----------|--------------|-----------|
| `CA_TOOLS` allow-list is **parsed but not enforced** | medium — a mis-set allow-list would not gate tools until 010 | `code_atlas/tools/` is empty and `main.py` is a stub; a validator or gate here could not fail, which is exactly `LESSONS.md:6`'s vacuous guard | **Task 010** — validate names against the registered tools and gate registration; add the enforcement test there |
| Missing `CA_<LANG>_CMD` **fails loud at launch**, untested here | medium — R5.3 names it explicitly | `adapter.py` is a stub (task 005); config correctly returns `None`, and the raise belongs at the launch site | **Task 005** — assert the launch raises on an absent adapter command |

Both need explicit human approval at this gate (they are the only two ❌ rows).

### Proving test

**`tests/test_config.py::test_env_beats_project_file_beats_default`** — parametrized over the 7 knobs
(ids `CA_DB_PATH`, `CA_WORKERS`, `CA_MAX_RESULTS`, `CA_IMPACT_DEPTH`, `CA_IMPACT_MAX_NODES`,
`CA_PHP_CMD`, `CA_TOOLS`). Each case writes a `.code-atlas.toml` in `tmp_path` with a file-layer value,
calls `load_config` three times — with the env key set, with it absent, and with no project file — and
asserts all three layers plus the ordering.

- **Fails pre-change:** `from code_atlas.config import load_config` raises `ImportError` — `config.py`
  is a one-line docstring stub today.
- **Passes post-change**, at the same layer the requirement can fail (pure resolution over injected env
  + a real file).
- **Invocation:** `pytest tests/test_config.py::test_env_beats_project_file_beats_default -q`, or the
  full `pytest` (`config.test_command`).

Companion for AC2 (same layer, same run): `tests/test_ignore.py::test_excluded_directory_cannot_be_re_included`
— the one case that would silently pass if the ancestor loop were dropped, which is what makes task
009's directory pruning safe.

### Rollback + porting

Single repo (`app`), single branch `feat/003-config-and-ignore`. Rollback is `git revert` of the branch
merge: items 1–2 return to their one-line stubs, items 3–4 delete cleanly, items 5–9 are doc text. No
schema, no migration, no on-disk artifact written by this change (`.code-atlas.toml` is *read* only; it
is created by the user, and its absence is the default path). Nothing to port.

### SCOPE

**Confirmed `M`** — unchanged from analysis. 2 core modules + 2 test files + 5 doc edits; no tier
crossing, no branch-type drift (`feat/` matches). The `outgrew-its-ticket` baseline for later gates is
this 9-item change-list.

### Self-audit

Every change-list item traces to a matrix row ✅ · `Ph2 covered by` filled `k/N` on all 11 rows ✅ ·
every assumption tagged, 5 verified and the 1 `novel-untested` is neither 3p nor runtime (so no spike
is owed) ✅ · proving test named, layer-matched, runnable, and fails pre-change for a stated reason ✅ ·
verification plan has 2 ❌, **both** recorded as coverage-gap exclusions with follow-up tasks ✅ ·
test blast-radius traced mechanically across every test root, not a single grep ✅ · rollback + porting
recorded ✅ · `DESIGN.md` N/A (backend track) ✅ · SCOPE re-confirmed `M` ✅.

**Gate 2 status:** **cleared** (2026-07-29) — user approved the 9-item change-list **and** both
coverage-gap exclusions (`CA_TOOLS` enforcement → task 010; `CA_<LANG>_CMD` fail-loud → task 005),
including item 8 (README Configuration section) as the one flagged judgment call.

## Phase 3 — Execute

- **Branch:** `feat/003-config-and-ignore` (CONVENTION §7, `config.branch_strategy`)
- **Commits** (one logical unit each, no AI-attribution trailer):

  | SHA | Subject | Change-list items |
  |-----|---------|-------------------|
  | `6f3025c` | Add CA_* config resolution: env, project file, defaults | 1, 3 |
  | `7773bce` | Add ignore matching over built-ins, .gitignore, .codeatlasignore | 2, 4 |
  | `ac7eebd` | Document the config file, knob defaults, and the ignore subset | 5, 6, 7, 8 |
  | *(pending)* | bookkeeping: status + working doc | 9 |

- **Proving test added and confirmed at both ends:**
  - Pre-change (stubs restored via `git stash`):
    `ImportError: cannot import name 'ADAPTER_CMD_TABLE' from 'code_atlas.config'` — collection error,
    test cannot run.
  - Post-change: `pytest tests/test_config.py::test_env_beats_project_file_beats_default
    tests/test_ignore.py::test_an_excluded_directory_cannot_be_re_included -q` → **8 passed**.
- **Result vs `BASELINE: green`:** `pytest` **86 passed** (34 baseline + 52 new — 29 config, 23 ignore),
  `ruff check .` clean, `mypy` clean. No new failure, no baseline exclusion needed.
- **AC1 count delivered:** the precedence test is 7 parametrized cases × 4 assertions = **28**, matching
  the ratified denominator (21 layer + 7 ordering). **AC2:** 23 ignore cases across the 3 sources,
  above the ≥14–16 pinned at Gate 0/2, including 4 near-miss **non**-matches.

### Verification sweep — both axes

**Axis 1 — file set.** Zero stray references ✅ (both modules import cleanly; exported symbols
enumerated and all resolve) · diff ⊆ approved change list ✅ (7 committed + 2 bookkeeping files = the
9 approved items, nothing outside) · each hunk maps to a matrix row ✅ (see the commit table) · no
untouched-line reformatting ✅ — `git diff --numstat` shows the only deletions are the 2 stub
docstrings being replaced and the 4 doc lines rewritten in place (`README.md` 31/0, `config.py` 179/1,
`ignore.py` 127/1, `CONVENTION.md` 4/2, `PLAN.md` 6/2, tests 239/0 and 148/0). No formatter was run
over any pre-existing file.

**Axis 2 — design conformance (per Gate-2 Approach bullet).**

| Approved bullet | Verdict |
|-----------------|---------|
| Frozen `Config` dataclass (`slots=True`), immutable | implemented-as-approved (`config.py:44`; asserted by `test_the_resolved_config_is_immutable`) |
| `CA_<LANG>_CMD` resolved by regex over the environment, merged over `[adapter_cmd]`, env winning | implemented-as-approved (`config.py:22`, `config.py:124`; `test_any_language_resolves_without_a_core_change`) |
| Parsers accept both layers' native types and raise `ConfigError` with the source label | implemented-as-approved (`config.py:143-176`; 8 fail-loud cases) |
| `os.cpu_count()` called qualified so monkeypatch reaches it | implemented-as-approved (`config.py:103`; `test_the_worker_default_is_floored_and_capped` at 1/3/64 CPUs) |
| `db_path` as `root / raw`, no `.resolve()` | implemented-as-approved (`config.py:74`; `test_an_absolute_db_path_wins_over_the_root`) |
| ignore: compile once, last-match-wins, ancestor loop enabling prune | implemented-as-approved (`ignore.py:41-63`) |
| **"A module-level tuple describes each scalar knob once (env name, key, parser, default); `load_config` loops it"** | **deviated** — see below |

### Design-conformance deviations

| Approved Gate-2 bullet | What was implemented instead | `path:line` | Surfaced to review |
|------------------------|------------------------------|-------------|--------------------|
| A single module-level table carrying (env name, file key, parser, default) that `load_config` **loops** | `KNOB_KEYS` names the six knobs once and `env_name()` derives the variable; `load_config` then makes six explicit `_resolve(...)` calls sharing **one** precedence helper — a shared helper rather than a loop | `code_atlas/config.py:24` (`KNOB_KEYS`), `:64` (`env_name`), `:69-86` (`load_config`), `:88` (`_resolve[T]`) | **yes** — adjudicate at Gate 4 |

**Why:** a table whose rows carry heterogeneous parsers and defaults (`Path`, `int`, `tuple \| None`)
forces `cast()` at construction and silently discards mypy's checking of the seven `Config` fields — the
one thing that catches a knob wired to the wrong parser. The generic `_resolve[T]` keeps full type
inference. **What Gate 2 actually asked for is preserved and asserted:** each knob is named exactly once
(`KNOB_KEYS`), the env name is derived mechanically (`env_name`, asserted by
`test_env_name_is_derived_from_the_project_file_key`), precedence is one implementation shared by every
knob, and AC1's parametrization reads from the same `KNOB_KEYS` — with
`test_every_knob_has_a_precedence_case` failing if the two ever drift. Judged a wording deviation, not a
behavioural one, but recorded rather than absorbed.

### Working-doc correction (not a behaviour change)

The Q5 clarification's re-include **example** (`!vendor/keep.php`) contradicted the very next bullet:
`vendor/` is an excluded directory, so nothing beneath it can be re-included. The example is corrected
in *Clarifications*; the ratified behaviour is unchanged and is pinned by
`tests/test_ignore.py::test_an_excluded_directory_cannot_be_re_included`.

### Out-of-scope observation (not touched)

`docs/BACKLOG.md` still lists **task 002 as `in-progress`** although PR #4 merged (`0644947`). It is
outside this change-list, so it was deliberately left alone — flagged for a one-line follow-up rather
than absorbed into this diff.

### `Ph3/4 proven by` progress

AC1 **7/7** · AC2 **3/3** · R1 5/5 · R2 4/4 · G1 2/2 · C1–C5 proven by the sweep + suites · C6 5/5
(item 9 completes with the bookkeeping commit). No `⚠`/`❌` rows.

## Phase 4 — Review ✋

- **reviewer verdict: NOT RUN — skipped by user decision.** Asked at the top of this phase with the
  cost trade-off stated; the user chose **challenger-only (1 dispatch)**. Recorded as a **named review
  coverage gap**, not a pass: no independent agent scored the diff against `ENGINEERING_RULES.md`.
  The rule-compliance table below is a **main-loop self-review by the change's author** — weaker
  evidence than an independent reviewer, and labelled as such.
- **challenger (ticket-blind) result: every item met — 13 reconstructed requirements, 13 met, 0 not
  met, 0 can't tell, 0 findings.** Payload was the raw ticket portion (above the separator) + the
  branch diff only; it confirmed it never opened the working-doc portion. It independently re-derived
  the requirements, ran the suite (52 new / 86 total), and checked R1.1, R5.3, R8.2, R7.5 itself.
  - Its one flag was **not** a finding: the ticket says "project file" without naming it, so
    `.code-atlas.toml` is an implementation decision it declined to count as scope creep — "flagging
    only so a human reviewer who cares about bikeshedding the filename can weigh in". That decision
    is the ratified Q1 (Gate 0), so it is already a human call.
  - Independence is **procedural, not cryptographic**: it rests on the separator split and on
    withholding the file. Its own note confirms it read only the frontmatter + the four raw sections.
- **security agent:** none defined for this project.
- **Scope reconciliation — file axis:** clean. 9 files changed = the 9 approved change-list items,
  nothing outside. No untouched-line reformatting; the only deletions are the 2 stub docstrings and 4
  doc lines rewritten in place. No formatter was run over any pre-existing file.
- **Scope reconciliation — behaviour axis:** 6 of 7 Gate-2 Approach bullets `implemented-as-approved`;
  **1 recorded deviation adjudicated below.** No bullet was found diverged that execute had missed,
  and no feature is self-marked `✅` without a named test behind it.

  **Deviation adjudication — `_resolve[T]` helper instead of a looped knob table: ACCEPTED.**
  The properties Gate 2 approved are all present and independently asserted: each knob named once
  (`config.py:24`), env name derived mechanically (`config.py:64`, asserted by
  `test_env_name_is_derived_from_the_project_file_key`), one shared precedence implementation
  (`config.py:88`), and AC1 parametrized from the same `KNOB_KEYS` with
  `test_every_knob_has_a_precedence_case` failing on drift. The change buys full mypy checking of the
  seven `Config` fields, which a heterogeneous table would have discarded behind `cast()`.
  **Honesty note:** this adjudication was made in the main loop **by the author of the change**, and
  the challenger could not corroborate it (it never saw the approved design). The user remains the
  final adjudicator at Gate 5 and can overrule.
- **Regression on Phase-1 callers:** none possible and none observed. The Phase-1 blast radius was
  **zero importers**, and the diff touches no other module — `store.py`, `indexer.py`, `resolver.py`,
  `adapter.py`, `main.py`, `tools/` are byte-identical (`git diff --name-only main...HEAD`). The R3.2
  guard `tests/test_contract_sole_source.py` still passes (6 tests), so `consumers()` is intact.
- **Proving test result + "would it fail without the change?"** `pytest
  tests/test_config.py::test_env_beats_project_file_beats_default -q` → **7 passed**. Without the
  change it does not merely fail, it cannot collect: with the stubs restored (`git stash`) the run
  ended `ImportError: cannot import name 'ADAPTER_CMD_TABLE' from 'code_atlas.config'`. Judged against
  `BASELINE: green`: **86 passed** (34 baseline + 52 new), `ruff` clean, `mypy` clean → no new
  failure, no baseline exclusion in play.
- **Layer-match re-confirmation:** no AC closed clean on a layer-mismatched proof. The 6 `✅` rows in
  design's verification plan all keep proof at their risk layer (unit tests over a **real** TOML file
  and **real** ignore files in `tmp_path`; nothing mocked). The 2 `❌` rows are exactly the two
  human-approved coverage-gap exclusions (`CA_TOOLS` enforcement → task 010; `CA_<LANG>_CMD`
  fail-loud at launch → task 005) — recorded before execute, so they do not block clean.
- **`Ph3/4 proven by` filled:** all 11 matrix rows plus both inventory checklists item-by-item
  (Inventory A 7/7 knobs, Inventory B 3/3 sources — per-item, not an aggregate).
- **Frontend rubric / proof manifest / surfaces:** n/a — `TRACK: backend`.
- **Clean?** **Yes, with one named limitation.** Challenger: every item met · no layer-match `❌`
  unresolved · `k = N` on every row and inventory item · both exclusions human-approved and recorded ·
  proving test green against a green baseline · scope clean on both axes. The limitation is the
  **skipped independent reviewer** (user decision), recorded above rather than papered over.
- **Reviewed at** `8677475d50e7bb5322eb29117e27c53620b63968` · reviewed files: `README.md`,
  `code_atlas/config.py`, `code_atlas/ignore.py`, `docs/BACKLOG.md`, `docs/CONVENTION.md`,
  `docs/PLAN.md`, `tests/test_config.py`, `tests/test_ignore.py`. Working doc (exempt from the
  staleness comparison): `docs/tasks/003_config-and-ignore.md` — embedded per `work_doc_mode: embed`.

## Phase 5 — Finalise ✋ final gate

- **Stale-review guard: PASS.** `git diff --name-only 8677475..HEAD` = `docs/tasks/003_config-and-ignore.md`
  only — the marker-bearing working doc, exempt by `work_doc_mode: embed`. Non-exempt set beyond the
  reviewed files is **empty**, so the clean review still covers the tree. Working tree clean.
- **PR draft:** `/tmp/pr-003.md`, rendered from `.github/pull_request_template.md` (the project
  template CLAUDE.md mandates), not mango's generic one.
- **Project finalise checklist:** `config.pr_checklist_path` is null, so the hook is skipped; the
  template's own pre-PR self-check is filled in the draft instead.
- **Outward actions (approved individually, then executed):**
  - [x] pushed branch `feat/003-config-and-ignore` → `origin` @ `2971f81`. Verified the durable lesson
        landed on the shared ref (`git show origin/feat/003-config-and-ignore:docs/LESSONS.md`), so it is
        not orphaned on a local branch.
  - [x] opened **PR [#5](https://github.com/cuongdinhngo/code-atlas/pull/5)** against `main` via `gh`,
        body from `/tmp/pr-003.md`.
  - [ ] tracker comment / transition — **n/a**, the tracker *is* this GitHub repo and the PR is the
        record; `docs/BACKLOG.md` + the task frontmatter are already in the diff.
  - [ ] **not approved, not done:** the optional one-line pointer in `docs/tasks/005_*.md` and
        `docs/tasks/010_*.md` carrying the two coverage-gap exclusions forward. Until it is added, those
        two obligations live only in this working doc.
- **Follow-up tickets for deferred (⚠) rows:** none — there are no `⚠` rows. The two Gate-2
  coverage-gap exclusions are already owned by existing tasks (`CA_TOOLS` enforcement → **010**,
  `CA_<LANG>_CMD` fail-loud at launch → **005**); adding a one-line pointer to those two task files is
  offered as an optional action rather than done silently, since both files are outside the approved
  change-list.
- **Durable lesson:** yes — *"The R1.1 grep-gate fires on ordinary English, not just on code"*, written
  to [`docs/LESSONS.md`](../LESSONS.md) and riding the branch-push above so it reaches a shared ref.
- **Revert path:** the branch is 6 commits over `main` and nothing outside it changed. Before merge:
  `git checkout main && git branch -D feat/003-config-and-ignore` (add `git push origin
  --delete feat/003-config-and-ignore` if pushed). After merge: `git revert -m 1 <merge-sha>` — this
  restores both modules to their one-line stubs and deletes the two test files; no schema, no
  migration, and no on-disk artifact was written (`.code-atlas.toml` is only ever *read*).

---

## Cost ledger (descriptive — facts only, never auto-cuts)

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| 1 Analysis | none — no fan-out dispatched (all evidence gathered in the main loop; 6 files read, 5 greps) | 1 | 0 dispatch | RTK live (`.harness.json:25`) · main-loop saving per `rtk gain`, not measured here |
| 2 Design | none — no fan-out dispatched (blast-radius greps + 3 runtime verifications run inline via Bash) | 1 | 0 dispatch | as above |
| 3 Execute | none — implementation, tests, sweep and commits all in the main loop | 1 | 0 dispatch | as above |
| 4 Review | `challenger` (ticket-blind) — 17 tool uses, 126 s | 1 | **52,361** | as above |
| 4 Review | `reviewer` — **not dispatched** (skipped by user decision; recorded as a review coverage gap) | 1 | 0 | — |
| 1–5 main loop | **not a dispatch — read from the session transcript**, so a `1 dispatch` row is never left standing as the total: 167 calls, **638.3k fresh** (223.3k output + 415.0k input incl. cache creation) + **24.4M cache reads**. Largest single response 10.1k output | — | 638,341 fresh | RTK live; its `rtk gain` counters are global/all-time, **not** session-scoped, so no per-task saving can be attributed here |

`LEDGER TOTAL: 52.4k dispatch (1 dispatch) + 638.3k fresh main-loop · top cost driver: the main loop,
not the dispatch — the challenger is 7.6% of fresh spend` — measured at finalise; the main-loop figure
grows slightly as this phase writes. **Scope caveat:** mango measures dispatch only; the main-loop
figure here comes from the session transcript, and main-loop *output noise* (test/lint dumps, file
reads) is not separable from it — do not read the 7.6% as a dispatch-vs-noise split.

---

## Decision log

| When | Decision | Why |
|------|----------|-----|
| Phase 1 | Working doc **embedded** below the separator in the ticket file | `config.work_doc_mode = "embed"` (`.harness.json:13`) and task 002 set the same precedent. Note: `CLAUDE.md` and `BACKLOG.md:51` both reference `docs/tasks/NNN_slug.work.md` (the *separate* path) — a wording drift to fix in whichever direction is chosen |
| Phase 1 | `TIER: full` | SCOPE=M, 2 new modules + 2 test suites, universal requirement with N=7 > 1 ⇒ lite ineligible |
| Phase 1 | Rulebook constraints recorded as C1–C5 matrix rows | The ticket has no Constraint section, and `LESSONS.md:16` warns that any hunk not traceable to a row reads as scope creep to the challenger |
| Gate 0 (2026-07-29) | **Q1–Q6 all ratified** as recommended — `.code-atlas.toml` · caller-supplied `root` · `max(1, min(cpu-2, 8))` · `CA_MAX_RESULTS=50` · `CA_TOOLS` parse-only, unset⇒all · stdlib gitignore subset with last-match-wins + no re-include under an excluded dir · AC1 per-knob N=7 | User reviewed each recommendation with its rationale and adopted all six verbatim. `j` 6 → 0; Gate 0 and Gate 1 cleared |
| Gate 0 (2026-07-29) | Doc corrections deferred to the Phase-2 change-list, not applied ad hoc | Q1/Q3a/Q3b/Q4 introduce values `PLAN.md` §11/§8.1 and `CONVENTION.md` §2/§49 never carried; R7.2 + the "Docs before PR" rule want them traced to a matrix row, not a stray edit |
| Gate 0 (2026-07-29) | `CA_HOST_ROOT` / `CA_CONTAINER_ROOT` explicitly out of scope; N stays **7** | They are real `CA_*` knobs (`PLAN.md:245`) but belong to task 008; recorded so the challenger does not read their absence as an incomplete knob inventory |
| Gate 2 (2026-07-29) | **Approved** the 9-item change-list + both coverage-gap exclusions | Every item traces to a matrix row; the two ❌ rows are integration-layer behaviours whose consumers are stubs, so proving them here would repeat `LESSONS.md:6`'s vacuous guard. Item 8 (README) approved as scoped |

## Session status

- **Last updated:** 2026-07-29 · **done** — PR [#5](https://github.com/cuongdinhngo/code-atlas/pull/5)
  merged `2026-07-29T14:43Z`
- **Current phase:** complete. Status `done` in both [`BACKLOG.md`](../BACKLOG.md) and this
  frontmatter; the same sync also corrected task **002**, whose PR #4 merged earlier while its status
  still read `in-progress`.
- **Next action:** none for 003. Next task on the critical path is **004** (SQLite store & schema) —
  its `depends_on: [001, 002]` is now satisfied. Still open, and deliberately not done here: carrying
  the two coverage-gap exclusions into `docs/tasks/005_*.md` and `docs/tasks/010_*.md` (offered at the
  final gate, not approved), so they currently live only in this working doc.
- **Blocked on:** nothing
