---
id: 020
slug: python-adapter
title: Python adapter (M8)
phase: 2
milestone: M8
status: todo
depends_on: [019]
---

## Goal
Third adapter — cheap once the contract is hardened (§3, §15).

## Scope / Deliverables
- `adapters/python/`: `ast` builtin for parse + `jedi` for import/name resolution.
- Map qnames as `module.Class.method`; emit the standard node/edge vocabulary.
- Runs in-process or a venv (document runtime).
- **CI:** `jedi` becomes a test-time dependency. Keep it out of the core's runtime dependencies (R8.2) — it belongs to the adapter, not to `code_atlas`, even though both are Python.

## Acceptance criteria
- Passes `tests/contract/` with Python fixtures; core unchanged.
- Import/name resolution produces `RESOLVED` edges where jedi can resolve; else `HEURISTIC`.

## References
Plan §3, §15 (M8).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

- **Ticket:** 020 · `docs/tasks/020_python-adapter.md` · **work_doc_mode:** `embed` (this file, below the separator)
- **Type:** enhancement · **Repo(s):** `app` (.) · **SCOPE:** L · **STRUCTURE:** native · **TRACK:** backend · **TIER:** full
- **BASELINE:** green — 2,867 passed / 0 skipped in 271.96s. Ran at `3f6a2b7` + 3 uncommitted doc edits (docs only, zero code). No baseline exclusions.

## Phase 0 — Refine (2026-09-04)

`PREMISE: 14 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`
`REFINE: 11 unresolved surfaced | 4 want-decision asked | 7 how-decision resolved+cited | 0 ASSUMED | skip: no`
`RECALL: 7 claim(s) surfaced | 0 by symbol | 3 by handle | 4 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`

INPUT KIND: **ticket** (not an epic — W2 tiers it rather than splitting it up front).

Ambiguous references, surfaced not blocking: "the standard node/edge vocabulary" (prose noun; the
vocabulary is `contract.py`) and "document runtime" (names no target doc; CONVENTION §5 says the
adapter-local README).

### Recalled claims (ADVISORY — surfaced only, injected nothing)

| # | Claim | Type | Matched by | Relevant here? |
|---|---|---|---|---|
| 1 | `128-C1` emit-do-not-gate-on-resolution | 2 | handle | yes — decides what the adapter emits for an unresolvable import |
| 2 | `128-C3` prove-the-guard-fails | 2 | handle | yes — every new fixture ships with its red run |
| 3 | `128-C4` derived-not-listed-invariant | 2 | handle | yes — the conformance case set is `set(adapter.cases)` |
| 4 | `200-C4` suffixes are a one-line literal in the entry file | 5 | area: adapters | yes |
| 5 | `184-C5` scanner-has-no-parse-phase | 5 | area: adapters | no — Python has a parse phase, so the syntax-error case applies |
| 6 | `128-C2` same-file symbol map scoped per container | 5 | area: adapters | yes — Python nests freely |
| 7 | `019-C3` alias edges when declaring/importing names differ | 5 | area: adapters | yes — `from x import y as z` |

`019-C2` (two-syntaxes-two-paths) is **retired** to R6.2 and skipped by recall; R6.2 is where
`import x` vs `from x import y` gets judged.

### Settled wants (from the maintainer — become AC constraints)

| # | The want | Chosen direction | Becomes AC constraint |
|---|---|---|---|
| W1 | Is this ticket allowed to move? | **Un-deferred 2026-09-04.** The maintainer reversed both their first answer and their own 2026-08-04 ratification; recorded in PLAN §19 | 020 is `todo`. It ships **without** the field-measured demand the 2026-08-30 T-SQL reorder required — a standing risk this ticket carries, not a resolved one |
| W2 | One adapter, or a slice first? | **Tier it like T-SQL** — a tier-1a slice costing zero new contract vocabulary, then a second ticket for depth | 020 is re-scoped to tier 1a; depth is a separate future ticket |
| W3 | Whose installed packages may the adapter see? | **Self-contained, degrade honestly** — the adapter's own runtime only | third-party imports come back at the weaker tier; the adapter never reads the indexed repo's venv (R4.2 holds) |
| W4 | What sets the fixture bar? | **A ratified Python construct inventory**, the way 149 did for TS/JS — folded in as 020's own first gate rather than a separate ticket (2026-09-04) | analysis opens with the inventory; it is ratified at Gate 1 before any fixture is written |

### Resolved direction + citation (how-decisions — refine-resolved, analysis still picks tools)

| # | HOW-decision | Resolution | Citation |
|---|---|---|---|
| H1 | in-process or venv? | **Long-lived subprocess**, own manifest + runtime, whole argv in `CA_PYTHON_CMD`. In-process is not available and would need a core seam that does not exist | `docs/CONVENTION.md:131,142`; R1.3 `docs/ENGINEERING_RULES.md:34`; `code_atlas/adapter.py:134` |
| H2 | qname separator | `module.Class::method` — the ticket's `module.Class.method` is wrong | `docs/CONVENTION.md:107` |
| H3 | where `jedi` lives | An **adapter** dependency in `adapters/python/`'s own manifest — not a "test-time dependency" as Scope says | R8.2 `docs/ENGINEERING_RULES.md:276`; CONVENTION §5 self-contained |
| H4 | who sets the tier | The adapter emits **bare edges with a ceiling**; the core's `_weaker_tier` decides. AC2's "produces RESOLVED edges" mis-states the boundary | `code_atlas/resolver.py:130,496`; CONVENTION §5; claim `128-C1` |
| H5 | static analyser | `adapters/python/` ships its **own** at strictest clean — not an entry in the core's mypy `files` | R6.6; CONVENTION §5; `pyproject.toml:41` |
| H6 | suffix declaration | One-line literal in the adapter's own entry file, readable without a subprocess | claim `200-C4`; `adapters/typescript/index.js:12` |
| H7 | conformance shape | A registry row beside `PHP_CASES`/`TS_CASES`/`SQL_CASES`; the valid set is derived, never re-listed | `tests/contract/adapter_registry.py:160,440,627`; claim `128-C4`; R6.7 |

**ASSUMED (awaiting ratification): none.** All four want-decisions were answered by the maintainer;
none was handed back, so nothing here needs a next-gate confirm.

### Constraints surfaced from the scan

- **Budget headroom is single-digit.** Tier 1 measures 25,896 against `TIER1_BUDGET = 25_900`, and
  `BACKLOG.md` 8,797 against 8,800. This is why W1's "stay deferred" costs nothing and why the W4
  inventory ticket cannot be filed as a BACKLOG row without pruning first.
- **`PLAN.md:344` still reads "in-process or a venv"**, which `CONVENTION.md:131` has since overruled.
  H1 resolves the ticket; the plan line is stale independently of this ticket.
- **"Cheap once the contract is hardened" is contradicted by both prior adapters** — 019 was reopened
  into 150–157, T-SQL took 184 + 022. It is the ticket's premise, and no evidence supports it.
- **`CONTRACT_VERSION` is 9**, not the "contract v2" era this ticket was written in.

### Exposure-checker (ticket-blind challenger, 1 dispatch — 83,783 tokens)

Three decisions surfaced. #1 (in-process vs subprocess) **re-classified to a how-decision** — settled
by CONVENTION §5 + R1.3, so it was cited rather than asked. #2 became **W3**, #3 became **W4**.

---

## Phase 1 — Analysis (2026-09-04)

`PREMISE: 14 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)` — carried forward from refine.
`RECALL: 7 claim(s) surfaced | 0 by symbol | 3 by handle | 4 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)` — carried forward from refine.
`SECTIONS: 4 found (Goal · Scope / Deliverables · Acceptance criteria · References) | 4 decomposed | ROWS: C=4 R=5 G=1 AC=3`
`BASELINE: green — 2,867 passed / 0 skipped. Ran at 3f6a2b7 + 3 uncommitted doc edits (docs only).`
`CLARIFICATION: 9 raised | 6 self-resolved (cited) | 3 for human decision — all 3 ANSWERED at Gate 1, 2026-09-04`
`TRACK: backend — 0/N touched files under UI paths; the change lives in adapters/ and tests/`
`RULE SECTIONS: 14 applicable — 11 by change-type | 3 by recalled handle`
`SCOPE: L` · `TIER: full`

**Gate 1 CLEARED 2026-09-04** — Q1/Q2/Q3 answered by the maintainer; `j` is now 0.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | Goal | "Third adapter — cheap once the contract is hardened (§3, §15)" | **Narrative, and its "cheap" is false.** 019 was reopened into 150–157; T-SQL took 184 + 022. Not falsifiable, carries no AC | `docs/BACKLOG.md:172` | ⚠ premise corrected |
| R1a | Scope | "`ast` builtin for parse" | stdlib `ast` is the parse front end | ticket line | ✅ |
| R1b | Scope | "`jedi` for import/name resolution" | **Q1 ratified: `jedi` is NOT in tier 1a.** Imports resolve by path arithmetic over the package layout, as TS does (155); `jedi` moves wholly to tier 2 | `contract.py:PATH_TARGET_BASIS` | ✅ deferred |
| R2a | Scope | "Map qnames as `module.Class.method`" | **Wrong separator.** It is `module.Class::method` (H2) | `docs/CONVENTION.md:107` | ✅ corrected |
| R2b | Scope | "emit the standard node/edge vocabulary" | Tier 1a costs **zero** new vocabulary — see the inventory | `contract.py:28-90` | ✅ |
| R3 | Scope | "Runs in-process or a venv (document runtime)" | **Not a choice.** Long-lived subprocess, own runtime, `CA_PYTHON_CMD` (H1) | `CONVENTION.md:131,142`; R1.3 | ✅ resolved |
| R4 | Scope | "`jedi` becomes a test-time dependency … keep it out of the core (R8.2)" | Half right: out of the core ✅, but it is an **adapter** dependency in the adapter's own manifest, not test-time (H3) | R8.2 `:276`; CONVENTION §5 | ✅ corrected |
| AC1a | AC | "Passes `tests/contract/` with Python fixtures" | Unfalsifiable until N is set. Restated: `PY_CASES` holds one `Case` per ratified tier-1a row and `test_adapter_conformance.py` is green for `python` . **Q3 ratified: N = 16** | `adapter_registry.py:78,348,534` | ✅ falsifiable |
| AC1b | AC | "core unchanged" | `git diff --quiet <base> HEAD -- code_atlas/` exits 0 — the `CORE-BYTE-UNCHANGED` condition 200 already used | R1.1 grep-gate | ✅ falsifiable |
| AC2 | AC | "Import/name resolution produces `RESOLVED` edges where jedi can resolve; else `HEURISTIC`" | **Mis-states the boundary.** The adapter emits bare edges with a *ceiling*; `_weaker_tier` in the core decides (H4, R3.3, claim `128-C1`) | `resolver.py:130,496` | ✅ restated |
| C1 | refine W1 | un-deferred by maintainer decision | Ships **without** the field-measured demand the 2026-08-30 reorder required — a recorded standing risk | PLAN §19 | ✅ |
| C2 | refine W2 | tier 1a first, depth second | Tier 1a = zero new contract vocabulary, the T-SQL 184 shape | `contract.py:28-90` | ✅ |
| C3 | refine W3 | self-contained resolution | The adapter never reads the indexed repo's venv; R4.2 determinism holds | R4.2 | ✅ |
| C4 | refine W4 | construct inventory ratified before any fixture | **Ratified at Gate 1, 2026-09-04: N = 16.** No fixture may be written outside it | refine W4 row | ✅ |

### AC validation — every value falsifiable or an explicit exclusion

| AC | Ticket value | Re-derived value | Falsifiable? |
|---|---|---|---|
| AC1a | "Python fixtures" (no count) | **N = 16** (PHP 11, TS 15, SQL 23) | ✅ ratified at Gate 1 |
| AC1b | "core unchanged" | `git diff --quiet … -- code_atlas/` | ✅ greppable |
| AC2 | "produces RESOLVED … else HEURISTIC" | adapter sets a ceiling; core's `_weaker_tier` decides | ✅ once restated |

No manual-check exclusions are needed: all three ACs reduce to a test or a grep.

### Universal inventory — the Python construct inventory (`N = 16`, tier 1a)

Spec-driven, per R2: this encodes the Python language, never a sample repo. **Every row costs zero
new contract vocabulary** — the tier-1a test C2 sets.

| # | Case key | Python construct | Vocabulary used (all existing) |
|---|---|---|---|
| 1 | `module` | module-level `def` and `class` in a plain `.py` | File · Function · Class · Method · CONTAINS |
| 2 | `package-init` | `__init__.py` making a directory a package | File · Namespace · CONTAINS |
| 3 | `class-inheritance` | single base class | Class · EXTENDS |
| 4 | `class-multiple-inheritance` | two bases (MRO) | Class · EXTENDS ×2 |
| 5 | `method-kinds` | instance · `@staticmethod` · `@classmethod` · `@property` | Method + `modifiers` |
| 6 | `async-def` | `async def` at module and class level | Function/Method + `async` modifier |
| 7 | `nested-function` | closure inside a function — claim `128-C2`, scope the name map per container | Function · CONTAINS |
| 8 | `import-plain` | `import a.b` | IMPORTS |
| 9 | `import-from` | `from a import b` | IMPORTS |
| 10 | `import-alias` | `import a as x`, `from a import b as y` — claim `019-C3` | IMPORTS · ALIASES |
| 11 | `import-relative` | `from . import x`, `from ..pkg import y` | IMPORTS, resolved against package layout |
| 12 | `call-function` | module-level `f()` | CALLS |
| 13 | `call-method` | `obj.m()`, `self.m()`, `super().m()` | CALLS |
| 14 | `instantiation` | `C()` where `C` is a class — **Q2 ratified: always CALLS in tier 1a**; tier 2 may promote to NEW | CALLS |
| 15 | `module-const` | `UPPER = 1` at module scope; class-body assignment | Const · Property |
| 16 | `syntax-error` | unparseable file → `ok:false`. Python **has** a parse phase, so claim `184-C5` does **not** exempt it | RESULT_FIELDS |

**Deferred to tier 2** (needs judgment or new vocabulary, out of this ticket): `typing.Protocol`/`abc.ABC`
→ Interface · `enum.Enum` → Enum · decorators as REFERENCES · type annotations as REFERENCES ·
`__all__` / re-export barrels · dataclass fields · conditional and `try:` imports · dynamic
(`getattr`, `importlib`) at the DYNAMIC tier · generators/`yield` · lambda and comprehension scopes ·
`match`/`case` · `TypeVar` and type aliases.

### Gap analysis (enhancement)

| Goal | Current | Target | Gap |
|---|---|---|---|
| Index Python source | `shipped_adapters()` returns `('php','sql','typescript')`; no `.py` suffix is announced by any handshake | a 4th adapter directory announcing `.py` | whole adapter |
| Conformance | `PY_CASES` does not exist | one `Case` per inventory row | `adapter_registry.py` |
| CI | no Python-adapter analyser job | own strictest-clean analyser (R6.6) | `ci.yml` + `scripts/gate.sh` |

### Blast radius

- **`adapters/python/`** — net new; self-contained (own manifest, runtime, README, analyser).
- **`tests/contract/adapter_registry.py`** — one new registry row beside `PHP_CASES`/`TS_CASES`/`SQL_CASES`. The valid set is derived, never re-listed (claim `128-C4`, R6.7).
- **`tests/contract/` fixtures** — 16 new `.py` fixture files.
- **`.github/workflows/ci.yml` + `scripts/gate.sh`** — must move together or one of them lies about what was verified (AGENTS.md).
- **`code_atlas/`** — **zero bytes** (AC1b). `shipped_adapters()` picks the directory up with no code change; `unconfigured_adapters()` surfaces `CA_PYTHON_CMD` automatically.
- **Repos touched:** `app` only. No `db-map` exists (`config.db_kind` is null), so there is no schema blast radius.
- **Second-order:** adding `adapters/python/` grows `shipped_adapters()` from 3 to 4, which changes any assertion pinning that count — claim `184-C4` count-pin-in-blast-radius. `contrib/claude-code/settings.snippet.json` (task 200) filters on shipped adapters and gains `.py`.

### Rule-compliance coverage

`RULE SECTIONS: 14 applicable — 11 by change-type | 3 by recalled handle`

| § | Source | Answer |
|---|---|---|
| R1.1 | change-type (new language) | ✅ no `if language ==` — the adapter is a subprocess; `shipped_adapters()` reads the directory |
| R1.2 | change-type | ✅ adapter #4 introduces no new abstraction; 156 already returned the registry verdict |
| R1.3 | change-type | ✅ the seam is the JSON contract + subprocess, not a base class — this is H1's citation |
| R1.4 | change-type | ✅ the adapter parses only; it never imports `store.py` |
| R2.1/R2.2/R2.3 | change-type | ✅ the 16-row inventory is spec-driven; zero repo/framework names (grep-gated) |
| R3.1 | change-type (contract) | ✅ **`CONTRACT_VERSION` stays 9** — tier 1a adds no vocabulary (C2) |
| R3.3 | **recalled handle** `emit-do-not-gate-on-resolution` | ✅ the adapter emits every reference it sees and declines only to *resolve* — this is what corrects AC2 |
| R4.2 | change-type | ✅ C3's self-contained resolution is what keeps identical input → identical rows |
| R6.5 | **recalled handle** `prove-the-guard-fails` | ✅ each of the 16 cases ships with its observed red run |
| R6.6 | change-type (new language in CI) | ✅ own analyser at strictest clean, in `adapters/python/` |
| R6.7 | **recalled handle** `derived-not-listed-invariant` | ✅ the valid case set is `set(adapter.cases)`, never re-listed |
| R7.2 | change-type | ✅ token-ledger row on close |
| R7.6 | change-type | ✅ prune-as-you-add; PLAN §15 M8 and §9 already pruned this run |
| R8.2/R8.3 | change-type | ✅ nothing enters core deps; the adapter's manifest ships a committed lock file |

No `PROVISIONAL` section is applicable, so nothing provisional is gate-blocking.

### Clarifications

**Self-resolved (6, cited):** R2a's separator (`CONVENTION.md:107`) · R3's runtime (`CONVENTION.md:131,142`) ·
R4's dependency home (R8.2 `:276`) · AC2's tier boundary (`resolver.py:130,496`, R3.3) · G1's "cheap"
premise (`BACKLOG.md:172`) · `depends_on: [019]` is satisfied (019 is `done`).

**⛔ For human decision (3) — Gate 1:**

**All three answered by the maintainer at Gate 1, 2026-09-04 — the recommended option taken in each case.**

**Q1 — Does tier 1a need `jedi` at all?** → **ANSWERED: no.** `PATH_TARGET_BASIS["IMPORTS"]` says an adapter resolves a
module specifier against the **filesystem** and hands the core a repo-relative path — which is what
the TS adapter does (155). For all four Python import cases (#8–#11) that is pure path arithmetic over
the package layout; `ast` alone does it. **My computed answer: tier 1a ships `ast` only, and `jedi`
moves wholly to tier 2** — which also makes W3's environment question tier 2's problem, not this
ticket's, and removes the adapter's only third-party dependency. Confirm or reject.

**Q2 — Does `C()` emit `NEW` or `CALLS`?** → **ANSWERED: always `CALLS` in tier 1a.** PHP and TS have a `new` keyword; Python does not —
instantiation and a call are the same syntax, so telling them apart needs resolution. **My computed
answer: emit `CALLS` always in tier 1a**, and let tier 2 promote to `NEW` once a class is resolvable.
`CALLER_KINDS` is `("CALLS","NEW")`, so `find_callers` is correct either way; a wrong `NEW` would not
be. Confirm or reject.

**Q3 — Ratify the 16-row construct inventory above.** → **ANSWERED: ratified as listed, N = 16.** It is AC1a's denominator (C4). Add, remove, or
move rows between tier 1a and tier 2 now — after this it is the fixed N that review counts against.

### Findings raised, outside this ticket's change list

- **`README.md:283` is stale.** It states bare `pytest` gives **2,739 passed / 0 skipped**, "verified
  2026-09-01", and calls itself the one place the number is kept. Today's baseline is **2,867 / 0
  skipped** — the skip count matches, the total is 128 low. Not this ticket's to fix; filed here so it
  is not re-discovered.

## Phase 2 — Design (2026-09-04)

Gate 1 confirmed clear: matrix and AC table filled, `j = 0`.

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`
`SCOPE: L` (unchanged from analysis — no tier crossing, no split needed)

### Approach

A fourth adapter directory, `adapters/python/`, self-contained exactly as the other three are: a
long-lived subprocess launched by `CA_PYTHON_CMD`, announcing `.py` in its handshake as a one-line
literal, walking the file with the **stdlib `ast` module only**, and emitting the 16 ratified
constructs using vocabulary that already exists. `code_atlas/` gains zero bytes — `shipped_adapters()`
reads the directory, so the adapter is picked up by existing code the moment it exists.

**Imports resolve by path arithmetic, not by a resolver library.** `ast.ImportFrom` carries `level`
(relative depth) and `names[].asname` (aliases); the adapter turns a module specifier into a
repo-relative path against the package layout and hands the core a bare edge, which is exactly what
`PATH_TARGET_BASIS["IMPORTS"]` declares and what the TS adapter does (155).

### Rejected alternatives

| # | Alternative | Why rejected |
|---|---|---|
| 1 | Use `jedi` for import/name resolution, as the ticket wrote | Gate 1 Q1. Spike B (below) shows stdlib `ast` covers all 16 rows including relative-import depth and aliases. `jedi` would add the adapter's only third-party dependency, a lock file, and W3's whole environment question — for capability that is entirely tier 2 |
| 2 | Run the adapter in-process (same language as the core) | H1. `CONVENTION.md:131,142` + R1.3 make the seam the subprocess protocol, not a Python base class; no in-process seam exists in `adapter.py`, and adding one would break AC1b |
| 3 | Ship all ~28 constructs in one ticket | C2/W2. This is precisely what reopened 019 into 150–157 |
| 4 | Infer `NEW` from PEP 8 capitalisation | Gate 1 Q2, and R2 — a naming convention is not the language spec, and it is wrong for any capitalised factory function |

### Assumptions

| # | Assumption | Tag | Evidence |
|---|---|---|---|
| A1 | stdlib `ast` exposes every construct in the 16-row inventory | **verified** | Spike B, output below |
| A2 | Creating `adapters/python/` reddens 6 existing tests before any adapter code exists | **verified** | Spike A, output below |
| A3 | A Python subprocess speaking JSONL behaves like the PHP/TS ones | **verified** | `adapter.py:134` `subprocess.Popen` is language-agnostic; `CA_PYTHON_CMD` is the whole argv (CONVENTION §5) |
| A4 | `CONTRACT_VERSION` stays 9 | **verified** | every kind in the inventory is already in `NODE_KINDS`/`EDGE_KINDS` (`contract.py:28-90`) |

**No `novel-untested` assumption remains**, so Gate 2 is not held on one.

**Spike A — `mkdir adapters/python && touch adapters/python/index.py`, then `pytest -q`:**

```
FAILED tests/test_batched_subject_sweep.py::test_the_whole_batched_payload_is_pinned
FAILED tests/test_batched_subject_sweep.py::test_a_single_subject_payload_is_unchanged
FAILED tests/test_index_root.py::test_index_root_weight_before_after_recorded
FAILED tests/test_payload_weight.py::test_payload_size_before_after_recorded_shape
FAILED tests/test_poke_snippet_covers_every_adapter.py::test_every_shipped_adapter_has_a_suffix_in_the_poke_snippet
FAILED tests/test_poke_snippet_covers_every_adapter.py::test_the_declaration_reader_is_not_vacuous
```
```
E  AssertionError: assert ['python'] == []
E  AssertionError: an adapter declares no suffix, so its coverage is unfalsifiable:
     {'php': ('.php','.phtml'), 'python': (), 'sql': ('.sql',), 'typescript': (…)}
E  AssertionError: {'unconfigured_adapters': [… 'php' …, 'python' …, 'sql' …, 'typescript' …]}
                != {'unconfigured_adapters': [… 'php' …, 'sql' …, 'typescript' …]}
E  assert 531 < 500      # tests/test_index_root.py:123 — the find_callers soft ceiling
```
The spike tree was removed; `git status --porcelain -uall` shows only the three doc files this run touched.

**Spike B — stdlib `ast` over a file exercising the riskiest inventory rows:**

```
node kinds: {'Import': 2, 'ImportFrom': 2, 'Assign': 2, 'ClassDef': 2, 'FunctionDef': 7,
             'AsyncFunctionDef': 2, 'Call': 2}
  Import names=[('a.b', None)]
  Import names=[('a.b', 'ab')]
  ImportFrom level=1 module=pkg names=[('x', None)]
  ImportFrom level=2 module=up names=[('y', 'z')]
line spans present: True
decorators seen: [('s', ['staticmethod']), ('c', ['classmethod']), ('p', ['property'])]
syntax-error path: SyntaxError ->  ok:false
```
`level` gives relative-import depth (row 11), `asname` gives the alias edge (row 10, claim `019-C3`),
`decorator_list` gives the method kinds (row 5), `end_lineno` gives the spans, and `SyntaxError` gives
row 16. **Q1's answer is discharged empirically, not by argument.**

### Recalled type-2 handles — every one answered

| Handle | Answer | Command + result |
|---|---|---|
| `derived-not-listed-invariant` | **traced** | `grep -rn "php.*sql.*typescript\|len(shipped_adapters" --include=*.py .` → **no live code pin**; every hit is a historical task doc. `grep -rn "shipped_adapters\|unconfigured_adapters" --include=*.py .` → the real consumers: `test_poke_snippet_covers_every_adapter.py:42`, `scripts/gen_skill.py:70`, `tools/coverage.py:61`, `tools/get_index_status.py:168`. All four derive; none re-lists. Folded into the change list as rows 8–11 |
| `prove-the-guard-fails` | **traced** | Spike A above **is** the observed red run — 6 named tests, verbatim output. Each of the 16 conformance cases ships the same way |
| `emit-do-not-gate-on-resolution` | **traced** | `grep -n "confidence_tier\|HEURISTIC" adapters/typescript/src/*.js` → `parse.js:415` `addEdge("CALLS", scope, callee.name.text, …, "HEURISTIC", node)` with the comment *"it caps the edge so a unique name can never be promoted to RESOLVED (R5.2)"*. The Python adapter emits `obj.m()` the same way: an edge with a ceiling, never a suppression |

### Smallest change list

| # | Change | File / area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | Entry file: handshake declaring `.py` as a one-line literal; `--server` + `--file` | `adapters/python/index.py` | `shipped_adapters()` → 4; rows 8–11 below | R1a, R3, C2, claim `200-C4` | 1/1 |
| 2 | The `ast` walk emitting the 16 constructs | `adapters/python/src/parse.py` | none identified — no core import (R1.4) | R1a, R2a, R2b, AC2 | 16/16 |
| 3 | Manifest with **zero** runtime dependencies | `adapters/python/pyproject.toml` | R8.3 lock file becomes moot — nothing to pin | R4, C3 | 1/1 |
| 4 | README: runtime + complete launch argv | `adapters/python/README.md` | none identified | R3 | 1/1 |
| 5 | Own analyser at strictest clean | `adapters/python/` ruff+mypy config | `scripts/gate.sh`, `ci.yml` (row 12) | rule R6.6 | 1/1 |
| 6 | 16 fixtures, one per inventory row | `tests/fixtures/python/` | none identified | AC1a | 16/16 |
| 7 | `PY_R62_CASES` (R6.2 named inventory) + `PY_CASES` + registry row, **and** the launch binding `tests/python_adapter_cli.py` that every adapter has | `tests/contract/adapter_registry.py`, `tests/python_adapter_cli.py` | the harness body is **not** edited — adding an adapter is a row (`test_adapter_conformance.py:3-6`) | AC1a, claim `128-C4` | 1/1 |
| 8 | **proof collateral** — `.py` in the poke snippets | `contrib/claude-code/`, `contrib/codex/`, `contrib/opencode/` | measured red: `test_poke_snippet…:37` `assert ['python'] == []` | AC1a blast radius | 1/1 |
| 9 | **proof collateral** — regenerate the skill | `contrib/skill/SKILL.md` via `scripts/gen_skill.py` | drift guard from task 200 | AC1a blast radius | 1/1 |
| 10 | **proof collateral** — 4th `unconfigured_adapters` row in two pinned payloads | `tests/test_batched_subject_sweep.py:124,244` | measured red, output above | AC1a blast radius, claim `184-C4` | 2/2 |
| 11 | **proof collateral** — the `find_callers` soft ceiling, **measured 531 against 500** | `tests/test_index_root.py:123`, `tests/test_payload_weight.py` | see the Gate-2 item below | AC1a blast radius | 2/2 |
| 12 | Python-adapter analyser job, in **both** files or one of them lies | `.github/workflows/ci.yml`, `scripts/gate.sh` | CI wall-clock on the shared runner | rule R6.6, AGENTS.md | 1/1 |
| 13 | Docs: CONVENTION §1 map row, TOKEN_LEDGER spend row, BACKLOG status on close | `docs/` | tier-1 budget has **5 tokens** free — prune first | R7.2, R7.6 | 1/1 |

Every row traces to a matrix row. Rows 8–11 are the mechanically-traced collateral: they are planned
edits, not execute surprises.

### Gate-2 decision inside row 11 — APPROVED 2026-09-04: raise 500 → 560

`tests/test_index_root.py:123` asserts `sizes["find_callers"] < 500`; a 4th shipped adapter measures
**531**. The row is `unconfigured_adapters`, which rides on every `find_callers`/`search_symbol`
payload and grows linearly with shipped adapters. Two honest options: **raise the soft ceiling to 560
with the reason recorded** (it is commented "soft ceiling after 071"), or trim the payload. **I
propose the raise** — trimming the payload is task 061/071's surface, not this ticket's, and doing it
here would exceed the approved change list. **The maintainer approved the raise at Gate 2 on
2026-09-04**, with the reason recorded here: one more shipped adapter is one more
`unconfigured_adapters` row, and the ceiling was already commented soft.

### Rule compliance

R1.1 ✅ no language branch — the directory is read, not listed · R1.2 ✅ no new abstraction ·
R1.3 ✅ the seam is the subprocess protocol · R1.4 ✅ the adapter never imports `store.py` ·
R2.1–R2.3 ✅ spec-driven inventory, zero repo/framework names · R3.1 ✅ `CONTRACT_VERSION` stays 9 ·
R3.3 ✅ bare edges with a ceiling · R4.2 ✅ no third-party dependency, so no environment variance ·
R6.5 ✅ Spike A is the observed red run · R6.6 ✅ own analyser · R6.7 ✅ the case set is derived ·
R7.2/R7.6 ✅ row 13 · R8.2/R8.3 ✅ nothing enters core deps, and there is nothing to lock.

### Verification plan (per AC, layer-matched)

| AC | risk layer | proof artifact | fixture provenance | layer-match |
|---|---|---|---|---|
| AC1a — 16 conformance cases | integration (real subprocess + core reader) | integration — `test_adapter_conformance.py`, ids `python:<case>` | authored | ✅ |
| AC1b — core unchanged | logic | unit — `git diff --quiet <base> HEAD -- code_atlas/` exits 0 | n/a | ✅ |
| AC2 — bare edges with a ceiling | integration (adapter emits → core resolver links) | integration — a fixture whose import target is indexed links; one outside the index stays bare | authored | ✅ |
| C2 — zero new vocabulary | logic | unit — `CONTRACT_VERSION == 9`; every emitted kind ∈ `NODE_KINDS`/`EDGE_KINDS` | n/a | ✅ |
| C3 — self-contained resolution | logic (Q1 removed the third-party dependency, so this no longer has a runtime risk layer) | unit — the manifest declares zero runtime dependencies | n/a | ✅ |
| Rows 8–11 collateral | integration | the existing suite, seen red in Spike A and green after | n/a | ✅ |

**No ❌, so no coverage-gap exclusion is needed.** No AC is input-shape-dependent — every one names its
own expected value (a count, a byte-identical diff, a version integer), so none turns on the shape of
real input. `config.real_corpus_path` is unset; that costs nothing here because no row wanted a corpus.

### Proving test

`tests/contract/test_adapter_conformance.py::test_adapter_case[python:import-relative]` — and its 15
siblings. **Fails pre-change** (no `python` key in `REGISTRY`, so the parametrisation does not even
generate the id); **passes post-change**. Invocation:

```sh
.venv/bin/python -m pytest tests/contract/test_adapter_conformance.py -q -k python
```

Whole-gate invocation before the PR: `scripts/gate.sh` — only `GATE GREEN` counts.

### Rollback + porting

**Rollback:** `git revert` the feature branch. `code_atlas/` is byte-unchanged (AC1b), so nothing in
the core can be left half-migrated; deleting `adapters/python/` alone restores `shipped_adapters()` to
3 and un-reddens rows 8–11. **Porting:** `config.repos` holds one repo (`app`), so there is no
cross-repo porting order.

## Session status

- **Last updated:** 2026-09-04
- **Current phase:** Phase 2 — Design (complete); **Gate 2 CLEARED 2026-09-04** (13-row change list
  approved; ceiling 500 → 560 approved)
- **Next action:** `/mango:execute 020` on a fresh branch `feat/020-python-adapter`.
- **Blocked on:** nothing. The absent demand evidence (C1) is a recorded standing risk, not a block.

## Corrections applied 2026-09-04, before any code was written

A read-through of the citations found three errors in Phases 0–2. All three are fixed above; none
changes a decision, and no code had been written when they were found.

1. **`CONVENTION.md:97` was the wrong line for the qname rule** — it is **`:107`** (`- C#:
   `Namespace.Type::Member`. Python: `module.Class::method`.`). The line number came from the
   exposure-checker's report and was repeated in H2 and the design without being opened. The
   *substance* of H2 is unaffected and now verified twice over: `contract.py:11` carries
   `module.Class::method` as its worked example.
2. **The fixtures path was wrong.** Change-list row 6 said `tests/contract/fixtures/python/`; the
   convention is `tests/fixtures/python/` (`tests/fixtures/{php,sql,typescript}`).
3. **Two change-list items were missing.** Every adapter ships a launch binding
   (`tests/php_adapter_cli.py`, `sql_`, `ts_`) — `tests/python_adapter_cli.py` was not listed. And
   R6.2 requires `PY_R62_CASES` as data, which the row did not name.

R6.2 also settles a fixture question the inventory already anticipated: *"a construct with two
spellings reaching the walk by different paths needs both as cases"* (claim `019-C2`, retired into
R6.2). For Python that is `import x` vs `from x import y` — inventory rows 8 and 9, already separate.

## Cost ledger (R7.2)

| Seat | Spend | What it bought |
|---|---|---|
| ticket-blind `challenger` as refine's exposure-checker | **83,783** (22 tool-uses) | 3 un-exposed decisions; 1 re-classified to a how-decision, 2 became want-decisions Q-W3/W4 |
| `reviewer` | **not dispatched** | this PR carries no code, so there is no diff to review against the rule book |
| review-phase `challenger` | **not dispatched** | same — review has not run |
| main loop | **unmeasured** | the harness does not report it |

**One dispatch total.** The run stopped at Gate 2 by the maintainer's instruction before execute
wrote anything, so the two review seats were never opened; a later PR carrying the implementation
pays for them.
