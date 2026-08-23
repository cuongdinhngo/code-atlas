---
id: 088
slug: generate-onboarding-markdown
title: Onboarding — generate_onboarding markdown + manifest (M11)
phase: 3
milestone: M11
status: done
depends_on: [084, 086, 087]
---

## Goal
Emit committable, version-controllable onboarding docs from the graph — the human-facing side of the
same enrichment the tools serve.

## Scope / Deliverables
- New `code_atlas/tools/generate_onboarding.py`: write markdown (overview · tour · per-module pages)
  under `docs/onboarding/` **plus a `manifest.json`** the viewer (089) reads. Regenerable caches under
  `.code-atlas/onboarding/`.
- Deterministic given a fixed summarizer stub (R4.2).

## Acceptance criteria
- Generated markdown is committable; CI asserts **structure** — expected sections present, dependency
  order respected, deterministic given the stub. Coherence is a **recorded manual check** (not
  falsifiable — task-023 note).
- No PHP-specific logic.

## References
[`../phase3-onboarding/ROADMAP.md`](../phase3-onboarding/ROADMAP.md) §4 (M11);
PLAN §14, §15 (M11).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 088 — Onboarding — generate_onboarding markdown + manifest (M11) (working doc)

- **Ticket:** 088 · local file `docs/tasks/088_generate-onboarding-markdown.md`
- **Type:** enhancement
- **Repo(s) / Porting:** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/N touched files under UI paths
- **TIER:** full
- **BASELINE:** green — `.venv/bin/pytest -q` → **1353 passed, 0 failed** (untouched `main` `38f1d24`, 2026-08-18). baseline exclusions: none.
- **CHALLENGER:** OFF (`--no-challenger` / operator: skipped Review + Challenger)
- **REVIEW:** SKIPPED (operator argument). Do not reintroduce.

---

## Session status

- **Runner:** `/mango:solve 088 with skipped Review + Challenger`. Standing approval: suggest and take the best option, pass all gates; after the task, commit + push + open PR (`AGENTS.md` *Maintainer workflow* + this run's args).
- **work_doc_mode:** embed (`.harness.json`; plain local-file ticket, not a breakdown stub). **Path:** `docs/tasks/088_generate-onboarding-markdown.md` (below this separator).
- **Phase:** 5 finalise — review waived; proceeding to PR under standing approval.
- **Branch:** `feat/088-generate-onboarding-markdown`.
- **Gate 0:** j = 0 — no human questions.
- **Gate 1:** cleared on standing approval (best-option + pass-all-gates).
- **Gate 2:** cleared on standing approval.
- **Gate 4:** **waived** (REVIEW: SKIPPED, CHALLENGER: OFF). Not a clean-review claim.
- **Final gate:** cleared on standing approval (commit + push + open PR).

---

## Phase 0 — Refine (the FIRST phase)

`PREMISE: 8 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 4 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

**refine skipped: 0 unresolved product-decisions**

**Premise (all resolve):**
| Ref | Class | Found |
|-----|-------|-------|
| `code_atlas/tools/generate_onboarding.py` | to-be-created | absent, as framed |
| tickets 084, 086, 087 | referenced-as-existing | all `status: done` (087 merged `38f1d24`) |
| PHASE3 §4 M11 | referenced-as-existing | present; artifact location already in this ticket's Scope |
| PLAN §14, §15 (M11) | referenced-as-existing | present |
| R4.2 / R1.1 | referenced-as-existing | `docs/ENGINEERING_RULES.md` |
| 085 summarizer seam | referenced-as-existing | `code_atlas/onboarding/summary.py` |
| CONVENTION on-disk artifacts | referenced-as-existing | was `.code-atlas/onboarding/` only — 088 extends it |

**Skip rationale.** The ticket names the module, the output split (committed `docs/onboarding/` + gitignored cache), the three markdown kinds + manifest, the stub-determinism bar, and structure-only CI. 087 already locked file-level stops + `CA_IMPACT_MAX_NODES`. Coherence is explicitly a recorded exclusion. No acceptance-bar want survives. Exposure-checker does not run on skip.

**Recalled claims (ADVISORY — surfaced only):**

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | 085-C1 / 087-C1 count-pin-in-blast-radius | 2 | handle — new core modules + 17th tool | yes — `len(core_modules()) == 48`; live "16 tools" strings |
| 2 | derived-not-listed-invariant (097-C1 / R6.7) | 2 | handle — new member of `TOOL_NAMES` | yes — probe / which_tool / listed tuples |
| 3 | prove-the-guard-fails (093-C3) | 2 | handle — proving test must fail pre-change | yes |
| 4 | 087-C2 / 100-C4 do-not-attest-past-the-payloads-resolution | 2 | handle — `truncated` on a budgeted walk | yes — reuse `tour_subgraph.truncated` |
| 5 | 087-C3 bound-the-recursion | 2 | area: graph walk | does not apply — no new recursive walk |

**Constraints from scan:** R1.1 / R1.2 / R1.4 / R4.1 / R4.2 / R4.3 / R6.1 / R6.5 / R6.7 / R7.2 / R7.5; CONVENTION §6 (one module per tool, `NAME` + `create`); 086 payload conventions; SQL only in `store.py`; no LLM.

**INPUT KIND:** ticket (single deliverable — not an epic).

---

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope / Deliverables, Acceptance criteria, References) | 4 decomposed | ROWS: C=2 R=2 G=1 AC=3`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | Emit committable, version-controllable onboarding docs from the graph — the human-facing side of the same enrichment the tools serve. | 17th MCP tool `generate_onboarding`: writes overview · tour · per-module markdown + `manifest.json` from 084/085/086/087 facts. | `main.py` has 16 tools, no `generate_onboarding`. PHASE3 §4 M11. | change-list 1–4 | `tests/test_generate_onboarding.py` + `TOOL_NAMES` | ✅ |
| R1 | Scope | New `code_atlas/tools/generate_onboarding.py`: write markdown (overview · tour · per-module pages) under `docs/onboarding/` **plus a `manifest.json`** the viewer (089) reads. Regenerable caches under `.code-atlas/onboarding/`. | Presentation+IO tool; pure renderer in `onboarding/artifact.py`; store reads in the tool. Per-module pages = tour stops (087 budget). | `architecture_overview` / `guided_tour` pattern; CONVENTION named only the cache dir. | change-list 1–3 | `code_atlas/tools/generate_onboarding.py` · `onboarding/artifact.py` | ✅ |
| R2 | Scope | Deterministic given a fixed summarizer stub (R4.2). | `create(..., summarizer=)` like 086; default `StructuralSummarizer`; no timestamps; two runs byte-identical. | 085 seam `summary.py`. | change-list 1–2, 5 | proving test stub + byte-stability test | ✅ |
| C1 | AC | No PHP-specific logic. | Language-neutral `.aa` fixture; generated text names no language. | R1.1 grep-gate glob. | change-list 1–2, 5 | `test_generate_onboarding_names_no_language` + R1.1 pins | ✅ |
| C2 | Goal / R4.2 | Committable / version-controllable | Relative paths only in markdown+manifest; cache gitignored via existing `.code-atlas/`. | `.gitignore` already ignores `.code-atlas/`. | change-list 1–3 | proving test writes under `docs/onboarding/` | ✅ |
| AC1 | AC | CI asserts **structure** — expected sections present, dependency order respected, deterministic given the stub. | Headings derived from renderer constants; tour order matches 087 stops; stub docline appears on pages. | unbuilt | change-list 5 | proving test | ✅ |
| AC2 | AC | Coherence is a **recorded manual check** (not falsifiable — task-023 note). | **Coverage-gap exclusion** — not a test. Recorded below. | PHASE3 §4; task-023. | — (exclusion) | recorded exclusion | ✅ recorded exclusion |
| AC3 | AC | No PHP-specific logic. | Same as C1. | R1.1. | change-list 5 | language-name test + grep-gate | ✅ |

**Coverage-gap (AC2):** coherence of generated prose is a recorded manual check, not a CI gate. PHASE3 and the ticket say so. 089's viewer will render whatever 088 wrote.

**Clarifications:** j = 0.

**TIER: full** — new MCP tool + renderer + surface blast-radius (not lite).

**HANDLES (design-time answers, traced):**

| Handle | Answer | Where |
|--------|--------|-------|
| count-pin-in-blast-radius | traced — bump `len(core_modules())` 48→50; live "16 tools" → 17 | change-list 4 |
| derived-not-listed-invariant | traced — probe Q17; `which_tool`; listed `TOOL_NAMES` tuple; CALLS | change-list 4–5 |
| prove-the-guard-fails | traced — proving test fails pre (module absent) | change-list 5 |
| do-not-attest-past-the-payloads-resolution | traced — `truncated` from `tour_subgraph.truncated` (or results cap) | change-list 1–2 |
| bound-the-recursion-or-make-it-iterative | does not apply — no new walk | — |

---

## Phase 2 — Design

**Approach.** Compose 083–087 in a new pure `onboarding/artifact.py` (metrics, layers, summaries, ordered stops) and write files from `tools/generate_onboarding.py`. Do not import other tools. Overview layers use full `node_universe` (same as 086). Tour + per-module pages use `tour_subgraph(max_nodes=CA_IMPACT_MAX_NODES)` (same as 087). Output: `<root>/docs/onboarding/{overview.md,tour.md,modules/<path>.md,manifest.json}` plus `<root>/.code-atlas/onboarding/artifact.json`. `detail_level` `minimal`/`standard` (required by `declared_levels` == `TOOL_NAMES`); write is identical; `standard` adds `cache`. Unbuilt → `not_indexed`, no IO. Empty → `no_matches`.

**Rejected alternatives.**
1. Call `architecture_overview`/`guided_tour` internally — couples MCP caps into committed docs; tools-importing-tools. Rejected.
2. One markdown file — ticket names overview · tour · per-module + manifest for 089. Rejected.
3. Put manifest only in `.code-atlas/` — 089 must open offline from the repo; gitignored cache would hide it. Rejected.
4. A page per indexed module (unbudgeted) — 40k-file blast; 087 already locked the budget. Rejected.

**Assumptions.** 087 `tour_subgraph` + `ordered_stops` are the tour; 084 `assign_layers` is the overview; 085 seam is the stub surface. No new env knob.

**Change list**

| # | Change | Path | Rows |
|---|--------|------|------|
| 1 | Pure artifact: headings, `build_artifact`, renderers, manifest/cache JSON | `code_atlas/onboarding/artifact.py` (new) | G1, R1, R2, C1, AC1 |
| 2 | MCP tool: store reads, write tree, payload | `code_atlas/tools/generate_onboarding.py` (new) | G1, R1, R2, C2 |
| 3 | Register 17th tool | `code_atlas/main.py` | G1 |
| 4 | Surface blast-radius: `which_tool`, count-pins 48→50, listed `TOOL_NAMES`, CALLS, probe Q17, README/PLAN/CONVENTION/PHASE3/BACKLOG | `prompts.py`, tests, docs | G1, C1 |
| 5 | Proving + support tests | `tests/test_generate_onboarding.py` (new) | AC1, AC3, R2 |

**Proving test:** `tests/test_generate_onboarding.py::test_generate_onboarding_writes_structured_markdown_in_dependency_order` — cycle fixture from 087; headings present; ROUTES before {A,B} before LEAF; each cycle file once; stub docline on pages; second call byte-identical. **Fails pre** (import missing). **Passes post.**

**Verification plan.** Scoped pytest → full `.venv/bin/pytest -q` → ruff → mypy. Record SHA beside counts (P4).

---

## Phase 3 — Execute

- **Branch:** `feat/088-generate-onboarding-markdown` from `main` `38f1d24`.
- **Implemented:** change-list 1–5 as approved. CALLS gained `TOUR` as well as `ONBOARD` (087 had left the 16th tool off that listed subset — proof collateral of registering the 17th).
- **Deviation:** none vs the approved list. CALLS+TOUR is blast-radius of a listed `TOOL_NAMES` subset, not extra product scope.
- **Proving test:** `pytest tests/test_generate_onboarding.py -k writes_structured_markdown -q` → pass.
- **Delta-green:** baseline **1353** → **1373 passed, 0 failed** (+20: 6 authored in `test_generate_onboarding.py` + parametrized `TOOL_NAMES`/`CALLS` cases; none removed). `.venv/bin/ruff check code_atlas tests` clean. `.venv/bin/mypy code_atlas` → **50 source files**. Host `.venv/bin/pytest -q` (Linux + PHP) at feature commit `bd431a4`. Token-usage / `done` bookkeeping is a follow-up commit; re-run the gate there (P4).
- **Golden/snapshot change:** none.
- **Design-invalidation / re-gate:** none.

## Phase 4 — Review ✋ (waived at solve time; a direct review was run on the PR)

- reviewer verdict: **not run** (operator: skipped Review + Challenger)
- challenger: **OFF**
- Clean? **not claimed.** Finalise proceeds under the waiver + handover authorisation.
- **Reviewed at:** n/a (review waived — stale-review guard does not apply)

### Review round on PR #127 (maintainer asked for a direct review; 0 dispatch, in-session)

CI on the PR is red for the same **four billing-blocked jobs** as #126 ("recent account payments have
failed") — no job started, so the red says nothing about the code. Gate proven in Docker.

Two findings, both reproduced against `bd431a4` before the fix and green after (one probe, both trees:
`3 FAIL → 4 PASS`, the fourth being the positive control that stale pages still go):

| # | Finding | Repro on `bd431a4` | Fix |
|---|---------|--------------------|-----|
| 1 | `_write` ran `shutil.rmtree(docs/onboarding/modules)` — **deleting files the tool never wrote**. A hand-authored page in that tree was destroyed silently; a pre-existing `docs/onboarding/overview.md` was overwritten. Same class as 050 (never destroy what this server did not write), and reachable by any agent that can call the tool | `modules/HAND_WRITTEN.md` gone after a regeneration; a foreign `overview.md` replaced by generated bytes | ownership is now the manifest: `recorded_pages()` (pure, in `artifact.py`) returns the page list the previous `manifest.json` claims, `_remove_recorded_pages` unlinks exactly those and prunes empty dirs, and `_refuse_foreign_tree` raises when `overview.md`/`tour.md` exist with **no** manifest. Hostile recorded paths (`..`, absolute, outside `modules/*.md`) are dropped, not unlinked |
| 2 | The committed `overview.md` could not be told apart from a complete map: it counted every module (`- modules: 4`) while only the budgeted stops got pages (1), and nothing in the file said so. `tour.md` and the manifest carried `truncated`; the overview — the page a human opens first — did not | `impact_max_nodes=1` → overview lists `- modules: 4`, no truncation line, 1 page on disk | `- module pages: N` and `- truncated: true/false` in the overview summary block |

**Delta-green after the fixes:** `1373 → 1377 passed, 0 failed` (+4 authored tests; none removed),
ruff clean, mypy **50 files**; confirmed in Docker (`scripts/docker-test.sh`).

Observations left as-is, no change: `manifest["stops"][].page` is computed from `page_relpath` rather
than the written page set, so it *could* advertise a page that was skipped — unreachable today (every
tour file is in `metrics.modules`), and 089 is the ticket that will consume the field; and `results` has
no `offset`, which is fine for a write receipt whose subject is on disk with an honest `total_count`.

## Phase 5 — Finalise ✋ final gate

- PR draft: from `.github/pull_request_template.md`
- Planned outward actions (each approved by this run's args + `AGENTS.md` maintainer workflow):
  - [x] push branch
  - [x] bookkeeping (lesson + BACKLOG) folds into the branch-push / follow-up commit
  - [x] open PR via `gh`
  - [ ] tracker comment — N/A (local-file ticket, no tracker issue)
  - [ ] tracker transition — N/A
- Follow-up tickets: none deferred. 089 remains the next M11 card.
- **Durable lesson:** 088 in `docs/LESSONS.md` (`CALLS` is a listed tool-surface pin). `seen:` appended on 085-C1, 087-C1, 087-C2, 097-C1, 093-C3, 100-C4 per P1.
- Revert path: revert the feature branch / PR.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified | 0 not cheaply checkable`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/AGENT_BRIEF.md | mango files written: 0`

| # | Claim (id) | Type (proposed) | Evidence | Handle / area | Recurred? (`seen:`) | Falsified? | Proposed destination | Human ratified? |
|---|------------|-----------------|----------|---------------|---------------------|------------|----------------------|-----------------|
| 1 | 088-C1 / 085-C1 / 087-C1 | 2 | `test_mcp_server.CALLS` omitted `guided_tour` until 088 added it beside `generate_onboarding` | count-pin-in-blast-radius | 085, 087, 088 (**3**) | still true: CALLS is a listed subset; 087 missed it; 088 hit it | `agent_brief_path` (process) | **proposed** — `/mango:promote` is the cross-ticket pass |

Cross-ticket: `count-pin-in-blast-radius` now `seen:` 085, 087, 088. Human runs `/mango:promote` between tickets.

---

## Cost ledger (descriptive — facts only, never auto-cuts)

`COST-LEDGER: 0 dispatch row(s) | complete`

Dispatch **0 rows** — no subagent was dispatched: refine self-skipped, review waived, challenger off, analysis fan-out done in the main loop. Main-loop **unmeasured (host does not surface usage)**.

| phase | dispatch | round | tokens |
|-------|----------|-------|--------|
| (none) | — | — | unmeasured (host does not surface usage) |

