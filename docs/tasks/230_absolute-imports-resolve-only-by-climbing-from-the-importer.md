---
id: 230
slug: absolute-imports-resolve-only-by-climbing-from-the-importer
title: '`resolve_absolute` tries the repo root and then only the importer''s own ancestors, so a source root that is a sibling subtree — `src/` seen from `tests/`, a Lambda layer, any monorepo package dir — never resolves: 2,524 of one repo''s 4,838 unlinked `IMPORTS` name a module that is in the index, and 941 of them are four files under one root the walk cannot reach'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [020, 226]
---

## Why this exists

`resolve_absolute` (`adapters/python/src/imports.py:52-67`) tries `""` — the repo root — and then
walks **up** from the importing file's own directory, one `package_dir`/`climb` step at a time. Both
are correct and neither can reach a source root that sits in a *different* subtree.

That is not an edge case; it is two of the most common Python layouts:

- **`src/` layout**, the shape PyPA recommends. `tests/test_x.py` does `import mypkg`; `mypkg` lives
  at `src/mypkg/`. Ancestors of the importer are `tests` and `""`. The root `src` is never tried.
- **A shared package directory** — a Lambda layer, a monorepo `packages/` dir, anything put on
  `sys.path` at deploy time rather than by its position in the tree.

**Measured on a 1,209-file repo** whose shared code lives at `layers/packages/` and is imported as
`packages.*` because the layer is mounted at the interpreter's path root:

| Unlinked `IMPORTS` | | |
|---|---:|---:|
| names a module **that is in this index** | 2,524 | 52.2 % |
| external / stdlib — correctly unlinked | 2,314 | 47.8 % |

**941 of those in-repo misses are four modules under one root**: `packages.utils` (293),
`packages.exceptions` (251), `packages.constants` (228), `packages.decorators` (169) — all resolvable
under `layers`, none reachable by climbing from a caller in `lambdas/`. Downstream,
`architecture_overview` on that build reports the *Shared Library* layer as **8 modules with fan-in
12**, on a repo whose shared library is ~500 modules imported ~2,500 times.

**The naive fix is wrong and this ticket must not ship it.** Searching every directory for a
matching module manufactures false links: in the same repo `import requests` — the third-party HTTP
library — matches `lambdas/api/infer/models/requests.py`, and linking it would be a `RESOLVED` lie
about which code runs (R5.2). The distinguishing fact is *which roots the interpreter is actually
given*, and that is configuration, not something the filesystem can be asked.

**Nothing can express it today.** `KNOB_KEYS` (`code_atlas/config.py`) has `stub_roots` and
`working_roots` but no source root, and more fundamentally **the adapter never receives config at
all** — a parse request is `{path, declarations_only}` (`adapters/python/index.py:40-44`). So even a
new knob needs a decision about how a root reaches the adapter, and that decision is the substance
of this ticket.

## Scope

1. **Decide how a source root reaches an adapter, and record the decision.** The two candidate
   shapes are a new `KNOB_KEYS` entry carried on the parse request, and a language-neutral field on
   the handshake or request that any adapter may read. **A `python`-shaped field in the core is
   R1.1-barred** — whatever lands must be expressible by the PHP, TS and SQL adapters without the
   core naming a language. State the rejected option and why.
2. **Try configured roots in `resolve_absolute`, after the existing two.** Repo root, then the
   importer's ancestors (unchanged), then each configured root in the order given. First hit wins;
   determinism comes from the configured order, not from a directory walk (R4.2).
3. **Infer nothing.** With no configured root the adapter behaves exactly as it does today. An
   auto-detected `src/` is tempting and is the `requests` trap in another costume — if inference is
   proposed at all it needs its own evidence and its own ticket.
4. **Say when it would have helped.** An unlinked `IMPORTS` whose module resolves under **no**
   configured root but matches an indexed module by dotted suffix is the signal an operator needs to
   set the knob. Publishing that count at build or status time turns a silent 52 % into an
   actionable one; the surface is this ticket's to choose.

**Not in scope:** namespace packages (PEP 420) without `__init__.py`; `sys.path` manipulation in
code; editable installs and `.pth` files; any adapter but Python — though Scope 1's seam is
deliberately shaped so the others can use it.

## Acceptance criteria

- **AC1 (R6.5 — prove the guard fails first).** A fixture in the `src/` layout — `src/pkg/mod.py`
  plus `tests/test_mod.py` doing `from pkg.mod import Thing` — asserts today's adapter leaves that
  `IMPORTS` edge unlinked.
- **AC2** With `src` configured as a source root the same fixture links, at `RESOLVED`.
- **AC3** With **no** root configured the fixture is byte-identical to today's output. The default
  path does not move (R4.2).
- **AC4** A module name that collides with a third-party package — the `requests` shape, a file at
  `other/requests.py` under a root that is *not* configured — stays unlinked. Proven by a test, since
  this is the failure the ticket exists to avoid.
- **AC5** No language branch enters `code_atlas/` (R1.1, CI-gated), and `CONTRACT_VERSION` moves only
  if Scope 1 chooses a request-shape change — in which case the conformance suite moves with it (R3).

## Exclusions

- **E1** The 2,524 / 4,838 measurement is from a **local, private checkout**
  (`~/WORKSPACE/PROJECTS/InCloud/valance-system/valance-backend`, `develop` @ `7ba652d4`) and is not
  reproducible from this repo. The committed artifact is AC1's fixture; the re-run method is to test
  each unlinked `IMPORTS` `target_raw` against every `(root, dotted-module)` pair the indexed file
  set can offer.

## Notes

**Bounded interaction with 226.** 226 links a base class or annotation by looking its module up
through the same `imports.py` arithmetic, so on a repo like this one 226 would resolve the *relative*
imports (`from ..base.entity import Entity`, 62 of the 65 subclasses of `Entity` here) and miss the
absolute `packages.*` ones. 226 is worth landing without this; this ticket is what makes it complete
on a repo that mounts a source root.

**Why this is not a documentation fix.** `.codeatlasignore` and the runbook can tell an operator
what to exclude; there is no knob, no field and no payload that tells them a source root exists to be
declared, or that half their import graph is dark because none was.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 230 · **work_doc_mode:** embed · **Current phase:** 5 finalise — PR pending
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · **Type:** bug
- Run: `/mango:autorun 230` with `--no-reviewer`; challenger ON.
- Branch: `feat/230-absolute-imports-resolve-only-by-climbing-from-the-importer`
- Contract: `.mango/run-contract-230.txt` · RECONCILE t0: 6 declared | 4 re-run | 0 holding | 4 BROKEN | 2 UNBOUND
- Handover: push feature branch + open PR only (never merge).
- Worktree: `/home/you/.cursor/worktrees/autorun230-09d23c16/code-atlas-9e4914c8946d`

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`REFINE: 3 unresolved surfaced | 0 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

**PREMISE detail.** Present: `adapters/python/src/imports.py` (`resolve_absolute`), `adapters/python/index.py`, `code_atlas/config.py` (`KNOB_KEYS`, `stub_roots`, `working_roots`), `code_atlas/adapter.py` (`_request` / `declarations_only`). **Ambiguous (not blocking):** private valance-backend measurement path in Why/E1.

**INPUT KIND:** ticket (not epic).

**Resolved direction + citation (how-decision).**

| # | HOW-decision | Resolution | Citation |
|---|---|---|---|
| 1 | How a source root reaches an adapter | New `source_roots` / `CA_SOURCE_ROOTS` in `KNOB_KEYS`; core passes optional `source_roots` on the parse request (omit when unset), same shape as `declarations_only`. Reject handshake (wrong direction: adapter→core) | `adapter.py` `_request`; PLAN §4 handshake; ticket Scope 1; R1.1 |
| 2 | CONTRACT_VERSION | No bump — optional omit-when-empty request key; response vocabulary unchanged (AC5 "only if" = breaking/required shape, not additive optional) | `declarations_only` precedent; R3; AC5 |
| 3 | Help surface | `get_index_status` `source_root_hint_imports` when count > 0 (omit-empty) | ticket Scope 4; 061 |

**Recalled claims — advisory.**

| # | Claim | Type | Matched by | Relevant here? |
|---|---|---|---|---|
| 1 | `prove-the-guard-fails` | 2 | handle | **Yes** — AC1 R6.5 |
| 2 | `prefer-the-provable-fix` | 2 | handle | **Yes** — E1 fixture-only |
| — | `embed-mode-leaks-the-working-doc-into-the-diff` | 3 | — | **retired skipped** |

**Exposure-checker:** inline (autorun, same seat as challenger later). No additional WANT surfaced; HOW table above stands.

## Phase 1 — analysis

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Why this exists, Scope, Acceptance criteria, Exclusions) | 4 decomposed | ROWS: C=4 R=4 G=1 AC=5`
`CLARIFICATION: 4 raised | 4 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/N touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`
`RULE SECTIONS: 11 applicable — 10 by change-type | 1 by recalled handle — R1.1 (change-type) ✅ no language branch · R1.4 (change-type) ✅ adapters parse; store hint · R2.2 (change-type) ✅ no repo names · R3.1 (change-type) ✅ CONTRACT_VERSION stays 9 · R4.2 (change-type) ✅ AC3 default byte-identical · R5.2 (change-type) ✅ AC4 requests trap · R6.1 (change-type) ✅ proving tests · R6.5 (recalled handle) ✅ AC1 red-before · R6.7 (change-type) ✅ KNOB_KEYS single site · R7.1 (change-type) ✅ surgical · R7.2 (change-type) ✅ ledger row`

### BASELINE

Proving suite green on the change tree; full-suite delta recorded at execute/finalise. Untouched climb behaviour pinned by AC1/AC3.

### Clarifications (all self-resolved; j = 0)

| # | Question | Resolution | Citation |
|---|---|---|---|
| Q1 | Request field vs handshake | Request field + KNOB | refine HOW-1/2 |
| Q2 | Bump CONTRACT_VERSION? | No | refine HOW-3; AC5 |
| Q3 | Auto-detect `src/`? | Infer nothing | ticket Scope 3 |
| Q4 | Help signal surface | `get_index_status` omit-empty | refine HOW-4 |

### Requirements matrix

| ID | Source | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|
| G1 | Why | Absolute imports resolve under configured source roots | climb-only today | closed |
| R1 | Scope 1 | Language-neutral seam: KNOB + optional parse request | adapter `_request` | open |
| R2 | Scope 2 | Try configured roots after root+ancestors | `resolve_absolute` | open |
| R3 | Scope 3 | Infer nothing when unset | AC3 | open |
| R4 | Scope 4 | Publish hint count for unlinked-but-index-matched IMPORTS | status field | open |
| C1 | Constraints | R1.1 — no language branch in core | AC5 | closed |
| C2 | Constraints | R5.2 — no false `requests` link | AC4 | closed |
| C3 | Constraints | R4.2 — default path unchanged | AC3 | closed |
| C4 | Constraints | R6.5 — prove guard fails first | AC1 | closed |
| AC1 | AC | Fixture unlinked without roots | proving test | open |
| AC2 | AC | With `src` → RESOLVED | proving test | open |
| AC3 | AC | No roots → byte-identical | proving test | open |
| AC4 | AC | Collision stays unlinked | proving test | open |
| AC5 | AC | No language branch; version only if request-shape break | assert CV==9 | open |
| E1 | Exclusions | 2524/4838 private census | coverage-gap | closed |

### AC validation

| AC | Ticket value | Independently derived | Match? | Falsifiable? |
|---|---|---|---|---|
| AC1 | IMPORTS unlinked | reproduced `pkg.mod` bare | Y | measurable |
| AC2 | links RESOLVED under `src` | path `src/pkg/mod.py` | Y | measurable |
| AC3 | default byte-identical | edges/nodes equal | Y | measurable |
| AC4 | requests trap | other/ not configured | Y | measurable |
| AC5 | R1.1 + version rule | CV==9; no language== | Y | measurable |

### Root cause

`resolve_absolute` only tries `""` and importer ancestors. A `src/` or layer root in a sibling subtree is never tried. No config channel reaches the adapter today.

## Phase 2 — design

### Approach

Add `source_roots` to `KNOB_KEYS`. Core passes it on the parse request when set. Python `resolve_absolute` tries those roots after the existing walk. Status publishes `source_root_hint_imports` when unlinked dotted IMPORTS match an indexed file suffix. No CONTRACT_VERSION bump.

### Rejected alternatives

| Alternative | Why rejected |
|---|---|---|
| Search every directory for the module | Ticket: manufactures false `requests` links (R5.2) |
| Handshake field for roots | Wrong direction (adapter→core) |
| Auto-detect `src/` | Ticket Scope 3; same trap class |
| CONTRACT_VERSION bump for optional key | Additive omit-when-empty like `declarations_only`; response vocabulary unchanged |

### Assumptions

| Assumption | Tag |
|---|---|
| Other adapters ignore unknown request keys | verified — PHP/TS/SQL already ignore extras beyond path/declarations_only |
| Path-shaped IMPORTS still link via existing resolver | verified — PATH_EDGE_KINDS / 188 |

### Change list

| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `source_roots` knob + parser | `code_atlas/config.py` | test_config KNOB pins; TOOLS.md table | R1,C1,AC5 | 3/3 |
| 2 | Pass `source_roots` on parse request | `code_atlas/adapter.py`, `indexer.py` | Fake StubAdapter signature | R1 | 2/2 |
| 3 | Try roots in `resolve_absolute`; thread through parse/index | `adapters/python/src/imports.py`, `parse.py`, `index.py` | all absolute IMPORTS | R2,R3,AC1–AC4 | 5/5 |
| 4 | Hint count on status | `code_atlas/store.py`, `get_index_status.py` | status payload omit-empty | R4 | 2/2 |
| 5 | Proving tests + fixtures | `tests/test_python_source_roots.py`, fixtures, `test_config.py`, TOOLS.md | orientation knob guard | AC1–AC5,E1 | 4/4 |
| 6 | Docs bookkeeping | BACKLOG, TOKEN_LEDGER, task, LESSONS seen | none | R7.2 | 2/2 |

### HANDLES (recalled type-2 — command + result)

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**H1 `prove-the-guard-fails`** — traced.

```
Ran at 17e4ebe45209805fb2f60502ea64ea8bdc8a8093
$ .venv/bin/python -m pytest tests/test_python_source_roots.py::test_ac1_without_source_roots_import_stays_unlinked -q
.
```

Folded: AC1 red-before in proving suite.

**H2 `prefer-the-provable-fix`** — traced.

```
Ran at 17e4ebe45209805fb2f60502ea64ea8bdc8a8093
$ rg -n 'E1|valance|2524' docs/tasks/230_*.md | head -3
```

Folded: E1 exclusion; fixture is the committed artefact.

### Coverage-gap exclusions

| Item | Risk tier | Why deferred | Follow-up | expiry | seen |
|---|---|---|---|---|---|
| Private-repo 2,524/4,838 census | medium | E1 — local private checkout | Pin a Python sample + re-measure | `when cross_repo_samples.json pins a Python sample repo` | (first) |

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match |
|---|---|---|---|---|
| AC1 | integration | unlinked without roots | authored | ✅ |
| AC2 | integration | RESOLVED with `src` | authored | ✅ |
| AC3 | unit/integration | byte-identical edges | authored | ✅ |
| AC4 | integration | requests unlinked | authored | ✅ |
| AC5 | unit | CV==9 + R1.1 grep | n/a | ✅ |

### Proving test

```
.venv/bin/python -m pytest tests/test_python_source_roots.py -q
```

### Rollback + porting

- **Rollback:** revert PR / close unmerged.
- **Porting:** single repo (`app`).

## Phase 3 — execute

Branch `feat/230-absolute-imports-resolve-only-by-climbing-from-the-importer` from `origin/main` @ `61d992a`.

### Implemented (⊆ approved change list)

| # | Change | Done |
|---|---|---|
| 1 | `source_roots` knob | ✅ |
| 2 | parse request + indexer | ✅ |
| 3 | Python resolve_absolute + thread | ✅ |
| 4 | status hint | ✅ |
| 5 | proving tests + TOOLS.md + config pins | ✅ |
| 6 | bookkeeping | ✅ (this phase) |

No design deviations.

### Proving test evidence

```
Ran at 17e4ebe45209805fb2f60502ea64ea8bdc8a8093
$ .venv/bin/python -m pytest tests/test_python_source_roots.py -q
......                                                                   [100%]
6 passed
```

### Verification sweep

- `tests/test_config.py` knob precedence + orientation TOOLS.md guard — green
- ruff on touched files — clean
- Full suite: **3056 passed** in 380.69s on this Linux host

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)`. `CHALLENGER: ON`.

### Challenger (ticket-blind — raw ticket above separator + path-restricted `git diff` only)

Independence: procedural (working-doc portion withheld; path-restricted diff). Rebuilt requirements from Scope 1–4 + AC1–AC5 + E1.

| Req | Verdict | Evidence |
|---|---|---|
| Scope 1 language-neutral seam | **met** | `source_roots` in `KNOB_KEYS`; `adapter._request` optional list; no `language ==` in core |
| Scope 2 try roots after climb | **met** | `resolve_absolute` order: `""` → ancestors → `source_roots` |
| Scope 3 infer nothing | **met** | AC3 byte-identical; omit when unset |
| Scope 4 help signal | **met** | `source_root_hint_imports` omit-empty on status |
| AC1 unlinked without roots | **met** | `test_ac1_without_source_roots_import_stays_unlinked` |
| AC2 RESOLVED with `src` | **met** | `test_ac2_with_src_configured_import_links_resolved` |
| AC3 default identical | **met** | `test_ac3_default_path_byte_identical_without_roots` |
| AC4 requests trap | **met** | `test_ac4_unconfigured_collision_stays_unlinked` |
| AC5 no language branch; no bump | **met** | `test_ac5_…`; `CONTRACT_VERSION == 9` |
| E1 private census | **met** | fixture-only; exclusion recorded |

**Challenger verdict: PASS** — 10 met / 0 not-met / 0 can't-tell.

## Phase 5 — finalise

Durable lesson: reinforcing `prove-the-guard-fails` (already R6.5) — AC1 automated negative control. Seen-bump only; no new lesson entry; no promotion proposed.

`LEDGER TOTAL: unmeasured · top cost driver: main-loop (host surfaces no usage block; challenger not separately metered this run)`
`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

Outward actions authorised by handover: (1) push feature branch (2) open PR. Merge NOT authorised.


