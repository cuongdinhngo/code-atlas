---
id: 217
slug: python-tier-2-framework-visibility
title: Python tier 2 — decorators and annotations are where the relationships are
phase: 2
milestone: M8
status: todo
depends_on: [020, 137]
---

## Goal
Tier 1a (020) indexes Python but cannot see how a Python framework wires itself. A decorator and a
type annotation are not decoration in Flask/Django/FastAPI/pytest — they *are* the edge. Until they
reach the graph, `find_callers` and `impact` under-report on a Python repo in a way they do not on
PHP or TS/JS, and Pillar 2's layers read a framework app as a pile of unrelated functions.

## Scope / Deliverables
Four constructs, **zero new contract vocabulary** — every kind below already exists at v9:
- `typing.Protocol` / `abc.ABC` → `Interface` (+ `IMPLEMENTS` from the implementor)
- `enum.Enum` and its subclasses → `Enum`
- decorators → `REFERENCES` from the decorated symbol to the decorator
- type annotations (params, returns, class attributes) → `REFERENCES` to the named type
- `PY_R62_CASES` extended per construct (R6.2 — data, never re-listed in prose)
- a mid-size Python OSS repo as a validation sample (R6.3), sizing perf and coverage only

## Acceptance criteria
- AC1 — `tests/contract/` green with the extended inventory; `code_atlas/` unchanged (R1.1).
- AC2 — the validation repo indexes with sane counts and a recorded wall-clock; no crash.
- AC3 — the adapter asserts the grammar version it parses (see C2); a file using newer syntax
  returns `ok: false`, never a silently partial parse.

## Constraints
- **C1 — demand is measured, not assumed. DISCHARGED 2026-09-05.** PLAN §19 (2026-08-30) requires
  field-measured demand before a deferred adapter is implemented; 020 was un-deferred without it and
  §19 records that as a standing risk. This ticket does not repeat that — see *Demand measurement*
  below. Honest counter-case: `n = 1` repo, the same one the T-SQL reorder carried.
- **C2 — grammar version is an R4.2 concern, not a packaging detail.** `ast.parse` is bound to the
  running interpreter's grammar, unlike php-parser (`docs/PLAN.md:271`). The same repo under a
  different `CA_PYTHON_CMD` interpreter would otherwise yield different rows.
- **C3 — no BACKLOG row until the budget is pruned.** Tier 1 measures 25,899/25,900 and
  `BACKLOG.md` 8,797/8,800.
- **C4 — jedi is not in scope and is not assumed.** See H4.

## References
PLAN §3, §6.1, §15 (M8), §19. Tier 1a: `docs/tasks/020_python-adapter.md`.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 217 · **work_doc_mode:** embed · **Current phase:** 0 refine complete; C1 discharged by the
  measurement below. Ready for analysis on the maintainer's word.
- **Next action:** Gate 1 — ratify the construct inventory, then analysis.
- **Blocked on:** nothing. C3 (BACKLOG budget) is discharged by 218; C1 by the measurement below.

## Phase 0 — Refine (2026-09-05)

`PREMISE: 11 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`
`RECALL: 6 claim(s) surfaced | 0 by symbol | 3 by handle | 2 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`REFINE: 8 unresolved surfaced | 4 want-decision asked | 4 how-decision resolved+cited | 0 ASSUMED | skip: no`

INPUT KIND: **ticket**, not an epic. The bar W2 settled is four constructs sharing one walk and one
inventory — a single execute-able deliverable. It would have been an epic at the full 12-item bar.

Ambiguous references, surfaced not blocking: "usable like PHP/TS/SQL" and "a real Python repo at
scale" are both prose nouns; W2 and W3 turned them into a bar.

### Recalled claims (ADVISORY — surfaced only, injected nothing)

| # | Claim | Type | Matched by | Relevant here? |
|---|---|---|---|---|
| 1 | `020-C1` module-ast-span-from-text | 2 | handle | yes — any new File-level span repeats it |
| 2 | `128-C1` emit-do-not-gate-on-resolution | 2 | handle | yes — an unresolvable annotation still emits |
| 3 | `128-C4` derived-not-listed-invariant | 2 | handle | yes — `PY_R62_CASES` stays derived |
| 4 | `200-C4` suffixes are a one-line literal in the entry file | 5 | area: adapters | no — no suffix moves |
| 5 | `184-C5` scanner-has-no-parse-phase | 5 | area: adapters | no — Python has a parse phase |
| 6 | `137` PHP local type table | — | area | yes — the precedent if annotations need a type table |

`019-C2` two-syntaxes-two-paths is **retired** to R6.2 and skipped by recall.

### Settled wants (from the maintainer — become AC constraints)

| # | The want | Chosen direction | Becomes AC constraint |
|---|---|---|---|
| W1 | May tier 2 run, and on what warrant? | **Measure demand first** — a field retro round on a real Python repo, counting decisive-facts-in-graph the way round 12 did for T-SQL | C1. Tier 2 opens only if the number justifies it; §19's standard is honoured rather than waived twice |
| W2 | Where is the bar for "usable like PHP/TS/SQL"? | **Framework visibility** — decorators + annotations → REFERENCES, Protocol/ABC → Interface, `enum.Enum` → Enum. Not edge-kind parity, not the full 12 | Scope is those four. `NEW` promotion and the other eight tier-1a deferrals are out |
| W3 | Is real-repo validation required, or deferred again? | **Required, mid-size** — one Python OSS repo of a few thousand files, sizing perf and coverage as §6.1 did for PHP | AC2. Not a private monorepo; R6.3 becomes real for Python |
| W4 | What gets pruned for the budget? | **Collapse the `done` rows** in the two Open-work sections to a count plus a git-history pointer | C3. ~4,000 tokens; R7.6 — those rows retell what each ticket file already holds |

### Resolved direction + citation (how-decisions — refine-resolved, analysis still picks tools)

| # | HOW-decision | Resolution | Citation |
|---|---|---|---|
| H1 | Does tier 2 bump `contract_version`? | **No.** `Interface`, `Enum`, `IMPLEMENTS`, `REFERENCES`, `NEW` and the `DYNAMIC` tier all exist at v9; R3.1 fires on vocabulary, and none moves | `code_atlas/contract.py` NodeKind/EDGE_KINDS/tier tuple; R3.1 |
| H2 | How is the tier-2 inventory declared? | Extend `PY_R62_CASES` as **data**; re-listing it in a doc is the drift R6.7 forbids | R6.2 `docs/ENGINEERING_RULES.md:177`; `tests/contract/adapter_registry.py:635`; claim `128-C4` |
| H3 | Which Python grammar does the adapter commit to? | **Floor `>=3.12`, and the adapter asserts the grammar it parses.** `ast.parse` is bound to the running interpreter, unlike php-parser on 8.1+; leaving it implicit means the same repo yields different rows per host — an R4.2 break. Newer syntax degrades to `ok:false`, never a partial parse | `adapters/python/pyproject.toml:9`; `docs/PLAN.md:271`; R4.2; claim `128-C1` |
| H4 | Is `jedi` adopted? | **Not assumed — analysis must prove its marginal delta first.** 020's W3 confines it to the adapter's own runtime, where third-party imports come back at the weaker tier *anyway* — the same outcome path arithmetic already produces. If the delta is zero, the bar is met by a local type table (137's precedent), not by jedi | `docs/tasks/020_python-adapter.md` W3 + R1b; Step 3 direction-not-tool; `docs/tasks/137_php-local-type-table.md` |

**ASSUMED (awaiting ratification): none.** All four want-decisions were answered.

### Constraints surfaced from the scan

- **The budget is the binding constraint, not the work.** Tier 1 measures 25,899 against
  `TIER1_BUDGET = 25_900` and `BACKLOG.md` 8,797 against 8,800 (`scripts/agent_chain_cost.py`,
  2026-09-05). No row can be filed for C1 or for this ticket until W4's prune lands.
- **`capabilities` is not a parity axis.** `semantic_types` is the only known flag
  (`code_atlas/contract.py:185`), advertised-never-required under R1.6, with no core consumer beyond
  validation. Python's `{}` costs nothing.
- **W1 and W3 can share one repo** — the demand measurement and the validation sample are different
  questions, but a single mid-size Python repo can answer both, one before the build and one after.

### Exposure-checker (ticket-blind challenger, 1 dispatch — 67,519 tokens)

Four decisions surfaced beyond the seven already exposed. #1 (real-repo validation) became **W3**.
#3 (are jedi and `C()`→NEW mandatory for "done"?) folded into **W2**, which answered no to both.
#2 (Python grammar version) and #4 (jedi's marginal value under W3) were **re-classified to
how-decisions** — H3 and H4 — because R4.2 and 020's own W3 text settle them by citation.


## Demand measurement (C1) — 2026-09-05

**Sample.** `valance-system/valance-backend`, a private AWS-Lambda Python service. Indexed at tier 1a
with `CA_PYTHON_CMD` alone: **1,173 first-party files · 17,304 nodes · 96,028 edges** (vendored
`venv/ .build/ .aws-sam/ _layers/` excluded by the repo's own `.gitignore`). Mid-size, which is what
W3 asked for; the DB was written outside the sample repo.

### What the graph does not contain

| Vocabulary | In graph | In source |
|---|---|---|
| `Interface` nodes | **0** | 7 `Protocol` / `abc.ABC` classes, typed as plain `Class` |
| `Enum` nodes | **0** | 5 `enum.Enum` subclasses, typed as plain `Class` |
| `REFERENCES` edges | **0** | 536 decorator applications naming a first-party symbol; 928 annotation sites naming a first-party class |
| `IMPLEMENTS` edges | **0** | every `Protocol`/`ABC` implementor |
| `NEW` edges | **0** | folded into `CALLS` by design (020 Q2) |

10,942 annotation sites exist; 928 (8.5 %) name a first-party class, and those are the decisive ones
— `TenantEntity` 89, `MatchRecord` 48, `FilesystemItemEntity` 45, `EvidenceMetaEntity` 37. 2,165
non-modifier decorators exist; 536 (25 %) name a first-party function.

### The decisive result — six guards the index says nobody uses

Each of these is a node in the graph. Each has **zero incoming edges**. The source applies them 431
times, all as decorators:

| Guard | Applications in source | Incoming edges in graph |
|---|---|---|
| `is_authorized` | 191 | **0** |
| `request_validator` | 99 | **0** |
| `tenant_guard` | 77 | **0** |
| `with_request_context` | 71 | **0** |
| `is_authorized_or_has_action` | 24 | **0** |
| `entity_load` | 19 | **0** |

Ask this index *"which handlers enforce tenant isolation?"* and it returns an empty array — the same
failure shape ticket 214 just fixed for a bare `EXEC`, in a different language. An empty array reads
as proof, which is the risk 099/122 exist to close. The authorization and multi-tenancy layer of this
service is invisible to every navigation tool.

### Verdict against §19's standard

**Demand is measured and it is decisive, not volumetric.** The ~1,476 edges tier 2 would add are only
1.5 % of the graph by count — but they are the entire auth, tenancy and validation layer, and today
`find_callers` on any of it answers zero.

**One finding that argues *against* part of the scope, recorded because it is evidence:** 72 % of
`CALLS` are `HEURISTIC` and 40 % resolve to no node at all — but that mass is third-party
(`boto3`, `pydantic`), which tier 2 does not reach and which `jedi` would not reach either under
020's W3. It **strengthens H4**: the HEURISTIC rate is not the thing to buy, and jedi is not what buys
it. The 536 + 928 first-party edges are.
