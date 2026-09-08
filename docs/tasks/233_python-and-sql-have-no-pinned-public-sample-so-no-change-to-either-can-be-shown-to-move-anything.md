---
id: 233
slug: python-and-sql-have-no-pinned-public-sample-so-no-change-to-either-can-be-shown-to-move-anything
title: 'Python and SQL have no row in `cross_repo_samples.json`, so seven reports and every before/after measurement cover PHP and TS only — 137 could prove the type table moved 36.3 % → 2.6 % and 227 has no way to prove the same thing, on machinery that is already language-parameterised and needs two data rows'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [018, 150, 147, 228]
---

## Why this exists

`scripts/cross_repo_samples.json` holds **six** pinned public samples: three PHP (018) and three
TS/JS (150). **Zero Python. Zero SQL** — two of the four shipped adapters.

Everything that measures a change over real code reads that file:
`cross_repo_validate.py`, `edge_health_report.py`, `layer_report.py`, `module_report.py`,
`reachability_report.py`, `layer_diagram_report.py`, `tokens_to_answer.py`. All seven therefore
report on half the adapters.

**What that costs, concretely.** [137](../benchmarks/137_type-table.md) could state that the PHP
local type table took the HEURISTIC share from **36.3 % → 2.6 % on `brick/math`** and **36.1 % →
3.9 % on `symfony/demo`**, with a baseline reproduced on the same host before the change.
[227](227_python-has-no-local-type-table-so-every-member-call-is-heuristic.md) proposes the same
change for Python and **cannot make that claim at all** — there is no before, so there can be no
after. The same holds for 229's node-count correction, 230's source roots, and 231/232's field
parity: each would land with a fixture proving the mechanism and nothing proving the size.

**The machinery is already language-parameterised and the gap is data.** `edge_health_report.py:220`
reads `sample.get("language", "php")` and hands it to `index_root(root, language=…)`;
`cross_repo_validate.py:46-49` resolves the adapter command from `_ADAPTERS`, a dict keyed by
language — 147 moved that out of a code branch precisely so a new language is a row. Today that dict
names `php` and `typescript`, and `:247-249` refuses an unknown language by design. So this ticket
is **two rows in `_ADAPTERS`, four to six rows in the sample manifest, and their measured floors** —
not a code path.

**The one place a branch survives.** `layer_report.py:41-43` pins expected layer names per sample id
(`laravel_app`, `symfony_demo`, `brick_math`) — three PHP entries with no shape for anything else.
A Python or SQL sample needs its row there or that report has nothing to assert.

## Scope

1. **Add two rows to `_ADAPTERS`** — `python` → `CA_PYTHON_CMD`, `sql` → `CA_SQL_CMD`, with the same
   default shape the existing two use. Data, not a branch (147).
2. **Pin Python samples by *shape*, not by popularity.** The shapes that decide open tickets:
   a **`src/`-layout package** (230's source root is invisible without one), a **decorator-heavy
   framework app** (217/232's annotation and decorator counts), and a **flat package with deep
   member calls** (227's type table, 229's method-local assignments). Candidates worth evaluating:
   `pallets/flask`, `pydantic/pydantic`, `psf/requests`. **The implementer pins the SHA and measures
   the floors; this ticket does not guess either** — the manifest's own contract note sets floors at
   ≈80 % of a known-good smoke at the pinned SHA.
3. **Pin SQL samples, and accept that public T-SQL is scarce.** `microsoft/sql-server-samples` is the
   obvious source. **228 must land first**: today the adapter publishes a table named `IF` from
   `CREATE TABLE IF NOT EXISTS` and a column named `COLUMN` from `ALTER TABLE … ADD COLUMN`, so
   floors measured now would pin the defect as the baseline. Ordering, not a blocker on scope.
4. **Give each new sample its `layer_report.py` shape row,** or state in the PR which report is
   deliberately left unasserted for it and why (R5.6 — silence is not evidence).
5. **Re-run 137's protocol per language and file the results as benchmarks.** One `benchmarks/`
   file per language with the same columns 137 used, so 227 and 231 have a before to move.

**Not in scope:** the private consumer repos — they stay operator-local via
`CODE_ATLAS_SCALE_SAMPLE`, and a claim that cannot be reproduced from a pinned public SHA is an
anchor-only claim (R2). Fixing what the new samples reveal: each finding is its own ticket, as
221-232 were.

## Acceptance criteria

- **AC1** `cross_repo_validate.py` runs green over at least one Python and one SQL sample, with
  `failed=0` and floors recorded in the manifest's contract note beside the existing PHP and TS
  figures, naming the host and date (018's discipline).
- **AC2 (R6.5)** The floors are shown to bite: lowering a sample's `min_nodes` below its measured
  value and re-running must fail. A floor nobody has seen fail is not a gate.
- **AC3** `edge_health_report.py` produces a per-cause breakdown for a Python sample, and that table
  is committed as the baseline 227 will be measured against — dated, with the host named.
- **AC4** Every report that reads the manifest either asserts something for each new sample or
  states in the PR why it does not. A report silently skipping two of four languages is the state
  this ticket exists to end.
- **AC5** Determinism holds across the added languages: two clean runs over one pinned sample
  produce identical ordered rows (R4.2).

## Exclusions

- **E1** Network and both toolchains are required, so this cannot join per-PR CI — the same
  constraint `cross_repo_validate.py` already documents (`workflow_dispatch` / weekly schedule, or
  local). The deliverable is the committed floors and the benchmark files, not a green CI job.
- **E2** Repo choice is a judgement this ticket deliberately leaves open beyond the shape list in
  scope item 2. A sample chosen for stars rather than shape teaches nothing about the adapter.

## Notes

**Why the gap survived four adapters.** 018 pinned samples for PHP because PHP was the whole
product; 150 pinned them for TS because 150 was *"the TS adapter has no gate but its own fixtures"*.
020 · 217 (Python) and 184 · 022 (SQL) shipped against fixtures and the conformance registry, both of
which prove **construct correctness** and neither of which can show a **ratio over real code** —
the distinction [`../ADAPTER_PLAYBOOK.md`](../ADAPTER_PLAYBOOK.md) §4 now makes a required gate
rather than a habit.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 233 — Python and SQL pinned public samples (working doc)

- **Ticket:** 233 · docs/tasks/233_python-and-sql-have-no-pinned-public-sample-so-no-change-to-either-can-be-shown-to-move-anything.md
- **Type:** measure / infrastructure
- **Repo(s) / Porting:** app (`.`) — `scripts/` harness + manifest + reports + docs; adapters unchanged except workflow launch wiring
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0 UI paths
- **TIER:** full
- **BASELINE:** green — `tests/test_cross_repo_validation.py` + `tests/test_cross_repo_workflow_installs_every_adapter.py` → 14 passed, 1 skipped on untouched `e092835`

## Session status

- **KEY:** 233 · **work_doc_mode:** embed · **Current phase:** Phase 5 finalise; PR pending
- **Branch:** `feat/233-python-and-sql-pinned-samples`
- **Blocked on:** nothing. Handover authorises approach choice + gate passage + push/PR.

---

## Phase 0 — Refine

`PREMISE: 10 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

Premise references (referenced-as-existing, all resolve): `scripts/cross_repo_samples.json`, `scripts/cross_repo_validate.py` (`_ADAPTERS`), `scripts/edge_health_report.py:220`, `scripts/layer_report.py:41-43`, `scripts/module_report.py`, `scripts/reachability_report.py`, `scripts/layer_diagram_report.py`, `scripts/tokens_to_answer.py`, `docs/benchmarks/137_type-table.md`, dependency 228 (merged — `adapters/sql` dialect honesty on main).

refine self-skips: ticket is fully specified (5 scope items, 5 falsifiable ACs, E1–E2). Sample *choice* is an explicit HOW left to the implementer (Scope 2–3 / E2); handover authorises autonomous approach choice.

**HOW decisions (documented under skip:yes — not counted as unresolved on the REFINE line; handover authorises):**

1. **Python shapes:** keep `flask` (decorator-heavy, already pinned by 227); add `pydantic/pydantic` (`src/`-layout for 230) and `psf/requests` (flat package + deep member calls for 227/229). Cite ticket Scope 2 candidates.
2. **SQL pins:** `microsoft/sql-server-samples` @ pinned SHA with optional `sparse_paths` for AdventureWorks OLTP install script + Wide World Importers DW SSDT tables — avoids cloning the whole multi-GB tree. Cite ticket Scope 3 + 228 prerequisite landed.
3. **Report language wiring:** every `load_manifest` reporter that calls `index_root` must pass `language=` (today only `edge_health_report` / `cross_repo_validate` do). Cite ticket AC4 + `layer_report.py:92` defaulting to php.

**Recalled claims (ADVISORY):**

| # | Claim | Type | Matched by | Relevant? |
|---|-------|------|------------|-----------|
| 1 | `prove-the-guard-fails` (R6.5) | 2 | handle: AC2 floors must fail when lowered | Yes |
| 2 | `fixture-shape-begs-the-question` → R6.3 | 2 | handle: real pins not fixtures | Yes — this ticket *is* the R6.3 corpus for py/sql |

---

## Requirements matrix

`SECTIONS: 3 found (Scope, Acceptance criteria, Exclusions) | 3 decomposed | ROWS: C=2 R=5 G=0 AC=5`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| R1 | Scope 1 | Add python+sql rows to `_ADAPTERS` | `CA_PYTHON_CMD` already present (227); add `sql`→`CA_SQL_CMD` | `cross_repo_validate.py:49-53` | | | ✅ |
| R2 | Scope 2 | Pin Python samples by shape | flask + pydantic + requests with floors | manifest | | | ✅ |
| R3 | Scope 3 | Pin SQL samples (228 first) | 228 on main; AW OLTP + WWI DW via sparse_paths | sql-server-samples | | | ✅ |
| R4 | Scope 4 | layer_report shape row or PR statement | `_EXPECT` entries and/or explicit non-assert note | `layer_report.py` | | | ✅ |
| R5 | Scope 5 | 137 protocol benchmarks per language | `docs/benchmarks/233_*.md` | 137 columns | | | ✅ |
| AC1 | AC1 | cross_repo_validate green ≥1 py + ≥1 sql; floors in note | measured floors; failed=0 | harness | | | ✅ |
| AC2 | AC2 | floors bite when min_nodes lowered | proving test | R6.5 | | | ✅ |
| AC3 | AC3 | edge_health Python breakdown committed | benchmark baseline dated+host | edge_health | | | ✅ |
| AC4 | AC4 | every manifest reader asserts or states why not | language= + _EXPECT / PR notes | reports | | | ✅ |
| AC5 | AC5 | determinism two clean runs | identical ordered rows | R4.2 | | | ✅ |
| C1 | Not in scope | No private consumer repos | public pins only | ticket | | | ✅ |
| C2 | E1 | Not a per-PR CI job | floors+benchmarks are the deliverable | ticket E1 | | | ✅ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch |
|-------|---------------|------------------------|--------|--------------|-------------|
| AC1 | green validate + floors in contract_note | Same bar as 018/150; floors ≈80% of smoke | Y | measurable | — |
| AC2 | lowering min_nodes fails | assert_plausible_counts already rejects; need end-to-end on a pin | Y | measurable | — |
| AC3 | edge_health per-cause for Python | script already language-aware | Y | measurable | — |
| AC4 | every report asserts or discloses | fix language= silent php default; _EXPECT or PR note | Y | measurable | — |
| AC5 | two runs identical ordered rows | R4.2; compare report JSON / node+edge dumps | Y | measurable | — |

## Inventory (universal "all/every")

- **N=7 reports that read the manifest** (ticket Why): `cross_repo_validate`, `edge_health_report`, `layer_report`, `module_report`, `reachability_report`, `layer_diagram_report`, `tokens_to_answer`.

| # | Item | Ph3/4 proven by | Status |
|---|------|-----------------|--------|
| 1 | cross_repo_validate | AC1 run + _ADAPTERS sql | ✅ |
| 2 | edge_health_report | AC3 baseline + language= already | ✅ |
| 3 | layer_report | language= + _EXPECT / disclose | ✅ |
| 4 | module_report | language= + disclose if no assert | ✅ |
| 5 | reachability_report | language= + disclose | ✅ |
| 6 | layer_diagram_report | language= + disclose | ✅ |
| 7 | tokens_to_answer | no new sample questions — PR states why | ✅ |

## Clarifications

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

---

## Phase 1 — Analysis ✋ Gate 1

- **Gap (enhancement):** Python has one pin (flask via 227) and `_ADAPTERS.python`; SQL has neither `_ADAPTERS` row nor pins. Six of seven reporters still call `index_root(root)` without `language=`, so a non-PHP pin is indexed with the PHP adapter. `layer_report._EXPECT` is PHP-only. ADAPTER_PLAYBOOK §4 still says pins exist for php+typescript only.
- **Blast radius:** `scripts/cross_repo_validate.py`, `scripts/cross_repo_samples.json`, seven reporters, `.github/workflows/cross-repo.yml`, `tests/test_cross_repo_*.py`, `docs/benchmarks/`, `docs/ADAPTER_PLAYBOOK.md`, BACKLOG/TOKEN_LEDGER/working doc. No `code_atlas/` core edits (R1.1).
- **Rule-compliance section coverage:**

  `RULE SECTIONS: 6 applicable — 5 by change-type | 1 by recalled handle — §1 (change-type) ✅ | §2 (change-type) ✅ | §4 (change-type) ✅ | §5 (change-type) ✅ | §6 (change-type) ✅ | §6 (recalled handle) ✅`

  - §1 — harness/scripts only; no language branch in `code_atlas/`.
  - §2 — public pins outside `adapters/`; sample names stay out of adapter source.
  - §4 — determinism AC5; identical rows across two runs.
  - §5 — absence over wrong index (language= so SQL is not parsed as PHP).
  - §6 — R6.3 corpus + R6.5 floor bite (recalled `prove-the-guard-fails`).
  - §3 N/A — no contract vocabulary change. §7 ledger at finalise. §8 N/A no new dep.

Ran at d02ab64b13f9b0d7562e48d84c0ae4abce4d6f76
```
$ .venv/bin/python -m pytest tests/test_cross_repo_validation.py tests/test_cross_repo_workflow_installs_every_adapter.py -q --tb=no
.......s.......                                                          [100%]
14 passed, 1 skipped in 0.08s
```

- **Gate 1 status:** cleared (autorun — j = 0)

## Phase 2 — Design ✋ Gate 2

- **Approach:**
  1. Add `_ADAPTERS["sql"]` + `_DEFAULT_SQL` (`node adapters/sql/index.js --server`).
  2. Optional `sparse_paths` on a sample → `git sparse-checkout` in `checkout_pinned` (data-driven; needed for sql-server-samples).
  3. Manifest: keep flask; add pydantic + requests; add `adventureworks_oltp` + `wwi_dw` SQL pins with floors from measured smoke; update `contract_note` with host/date.
  4. Pass `language=` in every reporter that indexes from the manifest; add `_EXPECT` rows where layers are meaningful, else record non-assert in PR/working doc (R5.6).
  5. Workflow: `npm ci` for SQL adapter + `CA_SQL_CMD`; INSTALL_MARKERS sql row.
  6. Proving tests: manifest languages include python+sql; floor bite; AC5 determinism helper; workflow install markers.
  7. Benchmarks: `docs/benchmarks/233_python-edge-health.md` (AC3) + `docs/benchmarks/233_sql-cross-repo.md` (137-shaped floors table).
- **Rejected alternatives:**
  - **Clone full sql-server-samples.** Rejected: multi-GB; sparse_paths keeps the pin public+reproducible without the weight.
  - **Author a tiny SQL fixture repo under tests/.** Rejected: R2/R6.3 — fixtures prove construct correctness, not ratio-over-real-code; ticket forbids substituting private/fixture for public pins.
  - **Skip extra Python shapes (flask only).** Rejected: Scope 2 names three shapes that open tickets need; flask alone leaves src-layout and flat-package shapes unpinned.

**Assumptions**

| Assumption | verified / novel-untested | Resolution |
|------------|---------------------------|------------|
| sparse-checkout at depth-1 fetches listed paths | novel-untested | proving smoke: checkout_pinned + index must produce files>0 or Gate-3 fails |
| SQL adapter indexes only .sql under sparse root | verified | adapter file filter / existing SQL fixtures |
| 228 refuse reserved / dialect honesty holds on AW scripts | verified | 228 on main; floors measured after index |

**Smallest change-list**

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|--------|-----------|--------------|----------------|-----|
| `_ADAPTERS` sql + sparse_paths checkout | `scripts/cross_repo_validate.py` | all reporters using checkout_pinned | R1,R3,AC1 | 3/3 |
| manifest pins + floors + note | `scripts/cross_repo_samples.json` | weekly cross-repo job | R2,R3,AC1,C1 | 4/4 |
| language= + _EXPECT / skip notes | `scripts/{layer,module,reachability,layer_diagram}_report.py` (+ others that load_manifest) | report CLIs | R4,AC4 | 2/2 |
| workflow SQL install + CA_SQL_CMD | `.github/workflows/cross-repo.yml` | scheduled job | R1,AC1 | 2/2 |
| proving tests + INSTALL_MARKERS | `tests/test_cross_repo_*.py` | CI | AC2,AC5,R1 | 3/3 |
| benchmarks | `docs/benchmarks/233_*.md` | none | R5,AC3 | 2/2 |
| playbook §4 + BACKLOG + ledger + working doc | docs | R7.2 | C2 | 1/1 |

**Recalled type-2 handles**

| # | Handle | Answer |
|---|--------|--------|
| 1 | `prove-the-guard-fails` | traced — `rg -n "assert_plausible_counts|min_nodes" tests/test_cross_repo_validation.py` shows floor helpers; Gate-3 adds `test_manifest_floor_bites_when_min_nodes_lowered` that mutates a copy below measured floor and expects PlausibleCountsError |
| 2 | `fixture-shape-begs-the-question` | does not apply because this change *adds* real public pins rather than substituting fixtures for them; fixtures stay for construct tests only |

`HANDLES: 2 recalled | 1 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

Handle-1 trace command output (design-time):

Ran at d02ab64b13f9b0d7562e48d84c0ae4abce4d6f76
```
$ rg -n "assert_plausible_counts|min_nodes" tests/test_cross_repo_validation.py
97:def test_assert_plausible_counts_respects_sample_floors() -> None:
100:        assert_plausible_counts(weak, label="weak", min_files=5, min_nodes=60, min_edges=1)
```

- **Proving test:** `tests/test_cross_repo_validation.py` (floor bite + language coverage) + live `python scripts/cross_repo_validate.py --public-only` for AC1/AC5 (E1: not per-PR CI).
- **Verification plan**

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | integration | cross_repo_validate over pins | real corpus (pinned SHAs) | ✅ |
| AC2 | logic | unit: lowered min_nodes fails | authored copy of manifest floors | ✅ |
| AC3 | integration | edge_health + committed benchmark | real corpus (flask) | ✅ |
| AC4 | logic | language= wired; inventory checklist + PR notes | reporters | ✅ |
| AC5 | integration | two runs compare ordered rows | real corpus | ✅ |

`EXCLUSIONS: 2 recorded | 2 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 2 input-shape-dependent AC(s) | 2 proven on a real corpus`

Coverage-gap exclusions:
- **E1** (ticket): not per-PR CI — deliverable is committed floors/benchmarks. `expiry: when a hosted runner job is added that clones pins under budget`
- **E2** (ticket): sample choice is judgement — choices recorded above. `expiry: when a later ticket replaces a pin and remeasures floors`

Input-shape-dependent AC1+AC3 proven on real pinned corpus (c=2).

- **Gate 2 status:** cleared (autorun)



## Phase 3 — Execute

- **Branch:** `feat/233-python-and-sql-pinned-samples`
- **Proving test:** `tests/test_cross_repo_validation.py` + workflow install markers
- **Verification sweep:** diff ⊆ approved list.
- **Design-conformance deviations:** none.

Ran at 2cd6bf2ad0af574b83bfb4a85fb82a41cc16e62c
```
$ .venv/bin/python -m pytest tests/test_cross_repo_validation.py tests/test_cross_repo_workflow_installs_every_adapter.py -q
18 passed, 1 skipped
```

AC1: Python+SQL pins failed=0 with floors in contract_note. AC5: requests two-run identity OK.

- **Gate 3 status:** cleared (autorun)

## Phase 4 — Review ✋ Gate 4

- **Reviewer:** OFF (`--no-reviewer`).
- **Challenger:** ON — ticket-blind.
- **Challenger verdict:** 12/12 reconstructed requirements MET (ticket-blind; main-loop).
- **Gate 4 status:** cleared (autorun — reviewer waived; challenger LGTM)

## Phase 5 — Finalise

- Outward actions: push + open PR only. Merge NOT authorised.

