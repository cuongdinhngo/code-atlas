---
id: 090
slug: llm-summarizer-impl
title: Onboarding — LLM summarizer behind the seam (M12, opt-in)
phase: 3
milestone: M12
status: done
depends_on: [085, 088]
---

## Goal
Real prose summaries (and layer-name refinement input) via an LLM, plugged into the 085 seam — the
first and only place an LLM touches this project. Opt-in and deferred until the deterministic path is
proven and measured.

## Scope / Deliverables
- New package **outside** `code_atlas/` (proposed `onboarding_llm/`, mirroring `adapters/`); provides a
  `Summarizer` impl for the 085 Protocol. Provider = **Claude** (confirm model/pricing against the API
  reference at implementation time).
- **Content-hash cache** (keyed on symbol content) so runs replay and diffs stay stable; cached outputs
  are committable.
- Opt-in via config (e.g. `CA_ONBOARDING_SUMMARIZER`); **never imported by the core; never runs in the
  per-PR gate** (R4.1).

## Acceptance criteria
- A test asserts the LLM path **never** executes in the CI gate (stub-only there).
- The cache makes a second run deterministic against a fixed input.
- Core behaviour is unchanged when the summarizer is off (default).

## References
[`../phase3-onboarding/PHASE3_ONBOARDING.md`](../phase3-onboarding/PHASE3_ONBOARDING.md) §4 (M12);
PLAN §14 (deterministic graph → LLM enrichment → presentation).

## Session status
- **Runner:** `/mango:solve 090` — **review & challenger WAIVED** by run args ("skipped review &
  challenger"). `CHALLENGER: OFF (--no-challenger)`; review phase replaced by a main-loop
  self-verification sweep. Maintainer standing approval (`AGENTS.md`) + explicit run args cover the
  two outward actions (push branch, open PR).
- **work_doc_mode:** embed. **Branch:** `feat/090-llm-summarizer-impl`.
- `STRUCTURE: native` · `TRACK: backend` · `SCOPE: M` · `TIER: full`.

## Phase 0 — refine
`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous` — 085 (`code_atlas/onboarding/summary.py`,
the `Summarizer` seam) **done**; 088 (`generate_onboarding`) **done**; PHASE3 §4 (M12) and PLAN §14
resolve. The LLM impl itself is to-be-created (not missing) → `m = 0`, continue.
`REFINE: 4 unresolved surfaced | 0 want-decision asked | 4 how-decision resolved+cited | 0 ASSUMED | skip: no`
- **Provider** → **Claude** (ticket names it; per-language SDK = `anthropic`). Cited: ticket Scope +
  claude-api skill.
- **Model** → default **`claude-sonnet-5`**, overridable via `CA_ONBOARDING_LLM_MODEL`. Cited: PHASE3
  §4 M12 decision "recommend Claude: a **mid tier for per-module summaries**, a top tier only for the
  layer-refinement pass (091)." Mid tier today = Sonnet 5 (claude-api Current Models). Layer refinement
  stays 091.
- **Opt-in mechanism** → `CA_ONBOARDING_SUMMARIZER` env (`llm`/`claude` enables; unset/other =
  deterministic default). Cited: ticket Scope ("e.g. `CA_ONBOARDING_SUMMARIZER`").
- **Placement / "never imported by the core"** → a separate top-level package `onboarding_llm/` with
  its **own entry point** (`code-atlas-llm`) that injects the summarizer into the core's widened
  `build_server(config, summarizer)` seam. The core keeps **zero** reference to the LLM — strictest
  reading of R4.1 ("never imported by the core"), mirroring how adapters live outside `code_atlas/`
  with their own launch. Cited: ticket Scope + PHASE3 §3 (R4/R4.1 row).

## Phase 1 — analysis
`SECTIONS: 4 found (Goal, Scope/Deliverables, Acceptance criteria, References) | References informational → 0 rows | ROWS: C=0 R=3 G=1 AC=3`

### Requirements matrix
| ID | Source | Verbatim (compressed) | Interpretation | Status |
|---|---|---|---|---|
| G1 | Goal | Real prose summaries via an LLM, plugged into the 085 seam; the only place an LLM touches the project; opt-in, deferred | `LLMSummarizer` satisfies the `Summarizer` Protocol, overrides `docline` via Claude; injected through the seam, off by default | pending |
| R1 | Scope | New package **outside** `code_atlas/` (`onboarding_llm/`, mirroring `adapters/`); a `Summarizer` impl for the 085 Protocol; provider = Claude | `onboarding_llm/` top-level package; `LLMSummarizer` + own entry point; core never imports it | pending |
| R2 | Scope | Content-hash cache keyed on symbol content; runs replay; diffs stable; cached outputs committable | `ContentHashCache`: sha256(key+sig+doc+direction+model+prompt-ver) → sorted-key JSON, deterministic, git-friendly | pending |
| R3 | Scope | Opt-in via config (`CA_ONBOARDING_SUMMARIZER`); never imported by the core; never runs in the per-PR gate (R4.1) | env opt-in read by the plugin entry point; deferred `anthropic` import; CI never runs the LLM path | pending |
| AC1 | AC | A test asserts the LLM path **never** executes in the CI gate (stub-only there) | Confinement test: no `code_atlas/**` names `anthropic`/`onboarding_llm`; seam tests inject a fake client (no network) | pending |
| AC2 | AC | The cache makes a second run deterministic against a fixed input | Test: 1st run hits fake client + writes cache; 2nd run with a raising client returns the identical cached `Summary` | pending |
| AC3 | AC | Core behaviour unchanged when the summarizer is off (default) | `build_server(config)` default → `None` → `StructuralSummarizer`; core has no LLM edge (proven by confinement) | pending |

### AC validation (falsifiability)
- **AC1** falsifiable — grep core for `anthropic`/`onboarding_llm` (must be 0); the seam test drives a
  fake client, so a real API call in CI would require an import the confinement test forbids.
- **AC2** falsifiable — the second run's client **raises if called**; a cache miss would surface as that
  exception, so a green test proves the replay came from cache, byte-identical.
- **AC3** falsifiable — the confinement grep would go red if any core module imported the LLM; the
  default `build_server`/tool path resolves `StructuralSummarizer` (085 tests already pin that).

### Blast radius
- **New (outside core):** `onboarding_llm/{__init__,summarizer,cache,server,__main__}.py`, `README.md`;
  `tests/test_onboarding_llm.py`.
- **Modified (core):** `code_atlas/main.py` — widen `build_server(config, summarizer=None)`, thread into
  the two onboarding tools. **No new core module** → the `core_modules() == 51` count-pins
  (`test_core_is_language_agnostic`, `test_sql_confinement`) are **untouched**.
- **Modified (packaging/docs):** `pyproject.toml` (packages, `code-atlas-llm` script, `llm` extra,
  mypy files); `docs/BACKLOG.md` (status + token row); this working doc + frontmatter; `README.md`
  (opt-in note).
- **Untouched:** `store.py`, `contract.py`, `summary.py`, adapters, resolver, all query tools. No
  contract/schema change; no `contract_version` bump.

`TRACK: backend` · `SCOPE: M` · `TIER: full` · `STRUCTURE: native`.

### RULE SECTIONS
`RULE SECTIONS: R1.1 · R1.2 · R4/R4.1 · R4.2 · R7.4`
- **R1.1** — the two edited/new core lines name no language; role derives from generic direction.
- **R1.2** — the seam already exists (085); this adds an impl behind it, no registry/factory.
- **R4/R4.1** — LLM lives outside `code_atlas/`; deferred `anthropic` import; CI never executes it.
- **R4.2** — cache JSON is sorted-key + content-hash → byte-stable, committable.
- **R7.4** — no dead abstraction; `LLMSummarizer` delegates role/signature to `StructuralSummarizer`.

## Phase 2 — design

### Approach
1. **Core seam widened at the composition root (no LLM name in core).** `build_server(config,
   summarizer: Summarizer | None = None)` threads the optional summarizer into
   `architecture_overview.create(config, summarizer)` and `generate_onboarding.create(config,
   summarizer)` (both already accept it, defaulting to `StructuralSummarizer`). `main()` calls
   `build_server(load_config(...))` unchanged → default behaviour identical (AC3).
2. **`onboarding_llm/` (outside core), mirroring `adapters/`:**
   - `summarizer.py` — `LLMSummarizer(client, model, cache, *, max_tokens, prompt_version)`. `summarize`
     delegates `signature`/`role` to `StructuralSummarizer` (DRY, R7.4), and replaces `docline` with a
     cached-or-generated one-sentence Claude summary. `anthropic` imported **only** in the factory.
   - `cache.py` — `ContentHashCache(path)`: load-on-init, write-through atomic `os.replace`, sorted-key
     JSON keyed by sha256(key, signature, doc, direction, model, prompt_version). Committable, stable
     diffs (R2/R4.2).
   - `server.py` — `run()` (`code-atlas-llm`): `build_summarizer(config, env)` returns `None` unless
     `CA_ONBOARDING_SUMMARIZER ∈ {llm, claude}`, else builds `LLMSummarizer` (model/cache from env);
     then `build_server(config, summarizer).run()`.
   - `__main__.py`, `README.md`.
3. **Packaging:** `pyproject.toml` — add `onboarding_llm*` to packages, `code-atlas-llm` console script,
   `llm = ["anthropic>=0.40"]` optional extra, `onboarding_llm` to mypy files.

### Rejected alternatives
1. **Config knob read by core + deferred `import onboarding_llm` in `main.py`** → rejected: the core
   source would still name the LLM package. A separate entry point keeps the core→LLM edge literally
   absent (strictest R4.1), matching the adapters precedent.
2. **LLM overrides `role` too** → rejected: role refinement is **091**'s scope. 090 changes only the
   prose `docline`; role stays the deterministic 083-derived tag.
3. **Registry/factory for summarizer selection** → rejected: R1.2 YAGNI; one `if opted-in` in the
   plugin entry point, no core registry.
4. **Cache write-once at end** → rejected: the `Summarizer` Protocol has no flush hook; write-through
   (bounded by `CA_IMPACT_MAX_NODES`, opt-in offline tool) is simpler and crash-safe.

### Smallest change-list
| change | file/area | Ph2 covered by |
|---|---|---|
| Widen `build_server(config, summarizer=None)` + thread to the 2 onboarding tools | `code_atlas/main.py` | G1, AC3 |
| `LLMSummarizer` (seam impl, docline via Claude, delegates role/sig) | `onboarding_llm/summarizer.py` | G1, R1 |
| `ContentHashCache` (committable content-hash JSON) | `onboarding_llm/cache.py` | R2 |
| `run()` entry + opt-in gate + deferred anthropic import | `onboarding_llm/server.py`, `__main__.py` | R3 |
| package init + README | `onboarding_llm/__init__.py`, `README.md` | R1, R3 |
| packages, `code-atlas-llm` script, `llm` extra, mypy files | `pyproject.toml` | R1, R3 |
| confinement + cache-determinism + core-off tests | `tests/test_onboarding_llm.py` | AC1, AC2, AC3 |
| status + token row | `docs/BACKLOG.md` | bookkeeping |
| opt-in note | `README.md` | R3 |

### Verification plan (per-AC)
| AC | proof artifact |
|---|---|
| AC1 | `test_no_core_module_imports_an_llm` — grep `code_atlas/**` for `anthropic`/`onboarding_llm` = 0; seam test drives a fake client |
| AC2 | `test_cache_replays_without_a_second_call` — 2nd summarizer's client raises if called; identical `Summary` returned |
| AC3 | AC1 confinement + `LLMSummarizer` delegates role/sig to `StructuralSummarizer` (byte-checked) |

### Proving test
`tests/test_onboarding_llm.py::test_cache_replays_without_a_second_call`.

## Phase 3 — execute
Branch `feat/090-llm-summarizer-impl` off `main`. Implemented exactly the approved change-list:

- **Core (no LLM name):** `code_atlas/main.py` — `build_server(config, summarizer=None)` imports the
  `Summarizer` *type* only (from the 085 seam) and threads the optional summarizer into
  `architecture_overview.create` / `generate_onboarding.create`. `main()` unchanged → default is the
  deterministic `StructuralSummarizer`.
- **`onboarding_llm/` (outside core):** `summarizer.py` (`LLMSummarizer` — docline via Claude, role +
  signature delegated to `StructuralSummarizer`), `cache.py` (`ContentHashCache` — sorted-key JSON,
  atomic write-through, sha256 content key), `server.py` (`run()`/`build_summarizer`, opt-in gate,
  deferred `anthropic` import), `__init__.py`, `__main__.py`, `README.md`.
- **Packaging:** `pyproject.toml` — `onboarding_llm*` package, `code-atlas-llm` script, `llm` extra
  (`anthropic>=0.40`), `onboarding_llm` added to mypy files.
- **Tests:** `tests/test_onboarding_llm.py` — 6 hermetic tests (fake client, no network) + a
  parametrized core-confinement guard.
- **Docs:** BACKLOG (status + token row), README (opt-in subsection), PHASE3 (M12 row), this doc.

### Verification sweep
**Axis 1 — file set.** `git status`: new `onboarding_llm/*`, new `tests/test_onboarding_llm.py`,
modified `code_atlas/main.py`, `pyproject.toml`, docs. **No new file under `code_atlas/`** → the
`core_modules() == 51` count-pins are untouched (confirmed green). `diff ⊆ approved change-list`, no
recorded deviation.

**Axis 2 — design-conformance (per Approach bullet).** All `implemented-as-approved`: seam widened at
the composition root ✅ · `LLMSummarizer` overrides only `docline`, delegates role/sig ✅ ·
`ContentHashCache` committable sorted JSON ✅ · opt-in gate + deferred `anthropic` import ✅ ·
packaging ✅. No `deviated` bullet.

**Empirical (Windows dev host):**
```
$ ruff check onboarding_llm code_atlas/main.py tests/test_onboarding_llm.py   → All checks passed!
$ mypy onboarding_llm    → clean for onboarding_llm/* (the 5 index_lock fcntl errors are the known
                            Windows-only artifact; green in Docker where fcntl.flock exists)
$ pytest tests/test_onboarding_llm.py -q          → 56 passed, 1 skipped (opt-in test → Docker)
$ pytest test_onboarding_summary + language_agnostic + sql_confinement + onboarding_llm
                                                  → 170 passed, 1 skipped (count-pins 51 unchanged)
```
Full-suite delta-green proven in **Docker** (the Windows `fcntl` exclusion): `scripts/docker-test.sh`
→ **1384 → 1441 passed, 0 failed** (+57), ruff clean, mypy clean including `onboarding_llm`. (The
opt-in `build_summarizer` test that skips on Windows runs green here.)

`Ph3 proven by:` the 6 authored tests + confinement sweep pass; ruff clean; mypy clean on the new
package.

## Phase 4 — review (WAIVED by run args)
`CHALLENGER: OFF (--no-challenger)`. Review phase **waived** ("skipped review & challenger"). No
`mango:reviewer`/`mango:challenger` dispatched. In place of the review phase, a main-loop
self-verification sweep (above) confirmed: diff ⊆ approved list, every Approach bullet
implemented-as-approved, all matrix rows k=N, count-pins intact, rules R1.1/R1.2/R4/R4.1/R4.2/R7.4
satisfied. **Result recorded as `clean (self-verified — REVIEW & CHALLENGER: OFF by run args)`.**

### k/N + matrix close-out
G1 ✅ · R1 ✅ · R2 ✅ · R3 ✅ · AC1 ✅ · AC2 ✅ · AC3 ✅ — every row `k = N`.

### Post-PR review round (`/code-review #129`, main-loop review — still 0 dispatch)
Maintainer asked for a direct `/code-review` on the open PR. **5 findings, all reproduced, all
fixed** on the generation/cache path (the reviewer verified the Anthropic API shapes themselves are
correct):
1. **Empty/refused result cached permanently** — an empty `_generate` (refusal / `max_tokens`
   truncation) was cached and replayed forever. Fix: empty → fall back to the structural docline and
   **do not cache** the blank (`summarizer.py`).
2. **`max_tokens=256` shared with adaptive thinking** could truncate the answer to empty on a
   thinking model. Fix: raised to **2048** (room for thinking + one sentence) — model-agnostic, since
   the model is operator-configurable.
3. **`anthropic>=0.40` floor** predated `output_config`. Fix: **dropped `output_config`** (the call
   now uses only universally-supported `messages.create` params) and raised the floor to `>=0.69`.
4. **Malformed committed cache entry → `KeyError`.** Fix: a missing/empty `docline` is treated as a
   **miss** (regenerate), via `cached.get("docline")`.
5. **Cache key omitted `_SYSTEM`/`MAX_TOKENS`.** Fix: both folded into the content key, so a prompt or
   limit change auto-invalidates without a manual `PROMPT_VERSION` bump.
Two new tests lock findings 1 and 4 (`test_empty_generation_falls_back_and_is_not_cached`,
`test_malformed_cache_entry_is_a_miss_not_a_crash`).

## Phase 5 — finalise
Stale-review guard: review waived, so the guard is N/A (no `Reviewed at` marker); self-verification
covers the same tree. Ledger: **0 dispatch rows** (no subagent dispatched) — complete. Main-loop
spend **unmeasured (host does not surface usage)**.

### Cost ledger (subagent dispatch only)
| Dispatch | Tokens | Outcome |
|---|---|---|
| *(none — review & challenger waived; refine/analysis/design/execute all main-loop)* | — | — |
**Total dispatch: 0.** Main-loop unmeasured (host surfaces no usage block).

### Outward actions (maintainer standing approval + explicit run args cover these two)
1. **Commit** the code + tests + docs in logical units.
2. **Push** `feat/090-llm-summarizer-impl` and **open the PR** from the template.
Merge, tracker transition, and branch deletion remain the maintainer's.

### Learning loop
`CLAIMS: 1 | T2=1 | 0 unclassified` — one durable, type-2, seen-once lesson recorded to
`docs/LESSONS.md` (090-C1 `plugin-entry-point-keeps-the-core-import-clean`): when a rule says "the
core must never import X", a **separate entry point outside the core that injects X through the seam**
keeps the core→X edge literally absent — stronger than a config-gated deferred import, which still
names X in core source. `PROMOTION: 0` (seen once; promote only at seen ≥ 2 via `/mango:promote`).
