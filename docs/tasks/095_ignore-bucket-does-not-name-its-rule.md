---
id: 095
slug: ignore-bucket-does-not-name-its-rule
title: '`collection.ignore: 9541` excludes indexable PHP by an unnamed rule'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [082, 003, 068]
---

## Goal
[082](082_claims-nobody-outside-can-check.md) made the denominator auditable and it works: on the
anchor repo both identities close exactly and `collected` matches the evaluator's own
`git ls-files | wc -l` **to the file**. But the census answers *how many* and not *by what rule*, and
one bucket carries **9,541 files that all have an indexed suffix** — they are PHP the index chose not
to hold. Nothing in any payload says which rule excluded them.

The consequence is precise: every absence answer over this repo has an unknown denominator. An agent
that gets `no_matches` cannot tell whether the subject is absent from the codebase or sitting in the
9,541.

## Evidence (field retro round 5, 2026-08-14, probe P2 — 082 verification)
- Verbatim:
  ```json
  "collection":{"collected":55278,"skipped":{"suffix":26811,"ignore":9541},"kept":18926,
                "indexed_suffixes":[".php",".phtml"]}
  ```
  `55278 − 26811 − 9541 = 18926 = kept` ✓ and `18926 + 0 stubs = 18926 = files` ✓.
- The evaluator **probed two guesses with `file_outline` and disproved both** — the legacy tree *is*
  indexed and the test tree *is* indexed — and still could not name what the 9,541 are (§11.5).
- 082's verdict is **FIXED** with this recorded as a semantic gap, not a regression: the arithmetic is
  fully auditable from outside; the semantics are not.
- Retro's own suggested shape: name the ignore *sources* — `ignore: {gitignore: N, config: N,
  vendor: N}` — not just the total.

## Scope / Deliverables
- **Attribute each ignore-skip to its source rule** in the same single walk that produces the census
  (`_collect_with_census`, `code_atlas/indexer.py:356-378`) — no second traversal, no rival count.
  The sources are whatever `load_ignore` actually composes (built-in defaults, `.gitignore`,
  configured `CA_*` ignores); enumerate them from the matcher rather than hand-listing them.
- **Report the breakdown** under `collection.skipped.ignore` at `verbose`, keeping the flat total so
  the 082 identities still close by construction and existing consumers do not break.
- **Decide the granularity.** Per-source counts are the ask. Per-*pattern* counts are a different
  cost; if design rejects them, record why and what an agent should do instead when a source's count
  is surprisingly large.
- **Say it once, in the right place.** 061's payload-weight rule applies: this belongs at `verbose`
  on `get_index_status`, not on every nav answer.
- **Record the anchor's actual breakdown in this ticket** when it lands — the number that motivated
  the ticket should end with a name attached.

## Constraints
- R1.1 — ignore rules are config, not language knowledge; the attribution must not learn about PHP.
- R4 — deterministic: the same tree yields the same per-source counts, and a file matched by two
  sources must be attributed by a stated, stable precedence rule (first match wins, in matcher order)
  rather than double-counted. The identities must still close.
- Cost: one pass, no extra stat calls per file beyond what the matcher already does.
- 082 stays authoritative for the census contract; this extends a bucket, it does not restructure it.

## Acceptance criteria
- A fixture repo with files excluded by two different sources reports the correct per-source counts,
  and `sum(sources) == ignore` with the 082 identities still closing — pinned by a test.
- A file matched by two sources is attributed once, under the documented precedence, with a test that
  fixes the precedence.
- `get_index_status(standard)` is byte-identical to today (R4); the breakdown appears only at
  `verbose`.
- The anchor repo's real breakdown for the 9,541 is written into this ticket's resolution.

## References
Field retro round 5 §A.8, §11.5; candidate 4.
Related: [082](082_claims-nobody-outside-can-check.md) (the census), [003](003_config-and-ignore.md)
(the ignore rules), [068](068_rules-bookmark-counted-as-source-file.md) (the last time the denominator
was wrong for an unnamed reason), [061](061_payload-weight.md) (where a field is allowed to live).

## Resolution
Fixture proof (merge gate): `tests/test_ignore_bucket_names_its_rule.py` — two sources
(`builtin` + `codeatlasignore`) report per-source counts that sum to `ignore` with the 082 identities
still closing; overlap attributes once to the last excluding source; `get_index_status(standard)` is
unchanged (no `collection`); `build_or_update_index(standard)` keeps `ignore` as an int and omits
`ignore_sources`.

Anchor 9,541: **not measured in this run** (no private checkout of the field-retro repo). Operator
follow-up — paste `get_index_status(verbose)["collection"]["skipped"]["ignore_sources"]` from that
index into this section. Coverage-gap exclusion, not a merge gate (080/074). On the git path the
breakdown names what **this matcher** dropped from `git ls-files` (tracked+builtin, `.codeatlasignore`,
force-added gitignored files), not what git already dropped.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 095 — ignore bucket does not name its rule (working doc)

- **Ticket:** 095 · local-file `docs/tasks/095_ignore-bucket-does-not-name-its-rule.md`
- **Type:** bug
- **Repo(s) / Porting:** app only
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — `scripts/docker-test.sh pytest -q` on untouched `main`: **1175 passed**.
  Post-change Docker: **1183 passed** (+8 tests, none removed).

---

## Phase 0 — Refine

`PREMISE: 10 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 4 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 7 unresolved surfaced | 0 want-decision asked | 4 how-decision resolved+cited | 7 ASSUMED | skip: no`

Resolved as existing: `_collect_with_census` / `CollectionCensus` (`indexer.py`), `load_ignore` /
`IgnoreMatcher` (`ignore.py`), `collection.skipped.ignore` (`collection.py`), tickets 082/003/068/061,
`.gitignore` / `.codeatlasignore` / `BUILTIN_PATTERNS`. Ambiguous (not blocking): prose “the 9,541”;
ticket’s `CA_*` ignores — `config.py` has no ignore knob; third source is `.codeatlasignore`.

**INPUT KIND:** ticket (single deliverable). **work_doc_mode:** embed (plain tracked local-file ticket).

**Recalled claims (advisory):** 093-C1 `try-instead-tool-name`; 093-C2 `derived-not-listed-invariant`;
093-C3 `prove-the-guard-fails`; 093-C4 `route-must-answer`.

**HOW (cited):**
1. Tag `_Rule` with `source`; `load_ignore` stamps while concatenating. `IgnoreMatcher.ignore_source`
   mirrors `is_ignored` (`ignore.py` last-match + ancestor walk). — `ignore.py:49-105`
2. Persist dict on sibling meta (`IGNORE_SOURCES_KEY`); `collection_census()` int-casts. — `store.py:430-440` (092)
3. Census loop still suffix-then-ignore; attribution only on the ignore slice. — `indexer.py` collect walk
4. Git path: `collected == git ls-files`, so most `.gitignore` hits never enter `found`. Document in PLAN §11.

**ASSUMED (awaiting ratification) — standing “best option”, confirmed at Gate 1:**

| # | Assumed choice | Why | Reverses prior? |
|---|----------------|-----|-----------------|
| A | Keep `skipped.ignore` as int; sibling `skipped.ignore_sources` | 082 tests subtract `ignore` as a number | no |
| B | Keys derived from composition: `builtin`, `gitignore`, `codeatlasignore` — not retro `vendor`/`config` | 082: illustrative list is a hint; `vendor/` is a pattern; no `CA_*` ignore | no |
| C | Last-match-wins, same as `is_ignored` (ticket’s “first match” was an example of a stable rule) | first-match would name a rule a later `!` negated | no (ticket example, not a prior decision) |
| D | Per-source only, not per-pattern | 061 would re-publish the ignore file | no |
| E | Breakdown only on `get_index_status(verbose)`; build standard unchanged | AC3 pins status-standard; 092 already put collection on build | no |
| F | Omit zero-count sources and omit `ignore_sources` when empty / pre-095 | 061 | no |
| G | Anchor 9,541: fixture proof here; operator paste is a confirming follow-up, not a merge gate | 080/074 | no |

**Constraints from scan:** R1.1, R4, R1.2, 082 identity, 061 omit-empty / verbose-only, `collection_census()` stays ints.

**Exposure-checker:** 1 dispatch ([Exposure-checker](99456024-85cf-46a2-9698-0a76c4af8c99)). `UNEXPOSED: 2` — both already ASSUMED and shipped; no new WANT.
1. WANT: JSON shape that keeps `skipped.ignore` as the 082 int — **ASSUMED A** (sibling `ignore_sources`, not nested under `ignore`).
2. WANT: breakdown on `build_or_update_index(standard)` vs `get_index_status(verbose)` only — **ASSUMED E** (verbose status only; build standard unchanged).

---

## Requirements matrix

`SECTIONS: 6 found (Goal, Evidence, Scope / Deliverables, Constraints, Acceptance criteria, References) | 6 decomposed | ROWS: C=4 R=5 G=2 AC=4`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | census answers how many not by what rule; 9541 have indexed suffix | Name the source of each ignore-skip | `collection.py` ignore is a bare int | CL1–CL5 | `test_ignore_bucket_names_its_rule.py` | ✅ |
| G2 | Evidence | identities close; evaluator could not name the 9541 | Arithmetic stays; semantics added | 082 tests subtract ignore as int | CL1 | `test_files_reconciliation.py` still closes | ✅ |
| R1 | Scope | Attribute in `_collect_with_census` same walk; enumerate from matcher | One pass; keys from `load_ignore` | `indexer.py` collect loop | CL1, CL2 | census uses `ignore_source` | ✅ |
| R2 | Scope | Report breakdown under skipped.ignore at verbose; keep flat total | Sibling `ignore_sources`; ignore stays int | 082 consumers | CL1, CL4 | proving test + AC3 | ✅ |
| R3 | Scope | Per-source; if reject per-pattern, record why | Rejected per-pattern (061) | PLAN §11 | CL1 design | PLAN/CONVENTION | ✅ |
| R4 | Scope | 061: verbose status, not every nav answer | `collection_field(..., ignore_sources=True)` only on verbose status | `get_index_status.py` verbose arm | CL4, CL5 | proving test standard has no collection | ✅ |
| R5 | Scope | Record anchor breakdown in this ticket | Coverage-gap: operator follow-up | no private checkout | — | Resolution section | ⚠ |
| C1 | Constraints | R1.1 — ignore is config not language | No PHP branch | `ignore.py` | CL1 | ruff/CI R1.1 | ✅ |
| C2 | Constraints | R4 deterministic; two-source file attributed once | Last-match, no double-count | `is_ignored` last match | CL1 | overlap test | ✅ |
| C3 | Constraints | One pass, no extra stat | `ignore_source` reuses regex walk | `ignore.py` | CL2 | no Path.stat in matcher | ✅ |
| C4 | Constraints | 082 stays authoritative | ignore remains int | `test_files_reconciliation.py` | CL1 | 082 tests still pass | ✅ |
| AC1 | AC | two-source fixture; sum==ignore; 082 closes | Proving test | — | CL6 | `test_two_ignore_sources_…` | ✅ |
| AC2 | AC | two-source overlap attributed once; precedence test | Last excluding source | — | CL6 | `test_overlapping_sources_…` | ✅ |
| AC3 | AC | status standard byte-identical; breakdown verbose only | No collection on standard; no ignore_sources on build standard | `get_index_status.py` | CL4, CL5 | proving test | ✅ |
| AC4 | AC | anchor 9541 written into ticket resolution | Manual-check exclusion | no checkout | coverage-gap | Resolution | ⚠ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? |
|-------|---------------|------------------------|--------|--------------|
| AC1 | two sources, sum==ignore | Y — fixture | Y | measurable |
| AC2 | attributed once under documented precedence | Last-match (ASSUMED C), not ticket’s first-match example | Y (ASSUMED) | measurable |
| AC3 | standard byte-identical | status has no `collection` today; keep that | Y | greppable |
| AC4 | write 9541 breakdown | cannot compute here | N/A | **manual-check exclusion** |

Retro `{gitignore, config, vendor}` is a **hint not schema** (082 lesson): real composition is builtin + gitignore + codeatlasignore.

## Inventory

- **Denominator / total N:** 3 ignore sources `load_ignore` composes
  1. `builtin` (`SOURCE_BUILTIN` beside `BUILTIN_PATTERNS`) — proven
  2. `gitignore` (`source_name(GITIGNORE_FILE)`) — proven (`git add -f`)
  3. `codeatlasignore` (`source_name(ATLAS_IGNORE_FILE)`) — proven

`CLARIFICATION: 7 raised | 7 self-resolved as ASSUMED A–G (standing best-option) | j=0`

---

## Phase 1 — Analysis ✋ Gate 1

- **Root cause:** `data` — census partitions ignore as a single int; `_Rule` carries no source tag, so the 9541 cannot be named.
- **Handler:** `_collect_with_census` + `IgnoreMatcher.ignore_source` + sibling meta + `collection_field(..., ignore_sources=True)` on verbose status.
- `RULE SECTIONS: R1.1 ✅ · R1.2 ✅ · R1.4 ✅ · R4.2 ✅ · R6.1 ✅ · R7.1 ✅ · R7.5 ✅`
- **Gate 1 status:** cleared (standing approval, ASSUMED A–G ratified)

---

## Phase 2 — Design ✋ Gate 2

- **Approach:** Stamp `source` on each `_Rule` as `load_ignore` concatenates. `ignore_source` is the same ancestor walk as `is_ignored` (last match within a path; first ignored ancestor wins). Census ignore arm counts by that source. Persist JSON object on `IGNORE_SOURCES_KEY`. Verbose status publishes `skipped.ignore_sources` when non-empty. `ignore` stays int.
- **Rejected:** replace `ignore` with an object (breaks 082 subtraction); per-pattern (061); first-match (disagrees with matcher); fold dict into census JSON (int-cast); `vendor` as a source (it is a pattern).

**Assumptions**

| Assumption | verified / novel-untested |
|------------|---------------------------|
| `is_ignored` ≡ `ignore_source is not None` | verified — same walk, existing ignore tests |
| gitignore-only untracked never enter `collected` | verified — PLAN §11; gitignore source proven via `git add -f` |
| No 3p/runtime novelty | verified |

**Change-list**

| Change | File | Blast radius | Ph2 | k/N |
|--------|------|--------------|-----|-----|
| CL1 source-tag `_Rule` + `ignore_source` + `composed_source_names` | `ignore.py` | `_STUB_FILE_IGNORE` compile_pattern default; `test_ignore.py` tuple pin | C1–C3, R1 | 8/16 |
| CL2 census counts by source; `_record_meta` stamps sibling key | `indexer.py` | `collect()[0]` unchanged; both build paths unpack 4-tuple | R1, C3, C4 | 8/16 |
| CL3 `IGNORE_SOURCES_KEY` + `ignore_source_counts()` | `store.py` | `META_KEYS` parametrize auto-covers | C4 | 8/16 |
| CL4 `collection_field(..., ignore_sources=)` | `collection.py` | build default False; status verbose True | R2, R4, AC3 | 8/16 |
| CL5 verbose status passes the flag | `get_index_status.py` | standard keyset / `_MINIMAL_KEYS` | AC3, R4 | 8/16 |
| CL6 proving + precedence + gitignore + omit-empty + derived-keys tests | `tests/test_ignore_bucket_names_its_rule.py` + `test_ignore.py` + reconciliation | 082/092 tests keep ignore as int | AC1–AC3 | 8/16 |
| CL7 PLAN §11/§12, CONVENTION, BACKLOG, ticket resolution | docs | none identified beyond listed | R3, R5, AC4 | 8/16 |

**Mechanical blast-radius:** `skipped["ignore"]` stays int at `tests/test_files_reconciliation.py:70-73`, `tests/test_untracked_files_are_invisible.py:37`. `collection_census()` int-cast `store.py:440`. `collection_field` two publishers. `BUILTIN_PATTERNS` tuple pin `test_ignore.py`. `_Rule` slots + `compile_pattern` default.

`HANDLES: 4 recalled | 2 traced | 2 does not apply | 0 unanswered`

| Handle | Answer |
|--------|--------|
| `derived-not-listed-invariant` | **traced** — keys from `COMPOSED_IGNORE_FILES` / `SOURCE_BUILTIN`; test `test_composed_source_names_are_derived_and_exclude_retro_keys` (command: `rg COMPOSED_IGNORE_FILES code_atlas/ignore.py` → `load_ignore` iterates that tuple). |
| `prove-the-guard-fails` | **traced** — `assert "vendor" not in composed_source_names()` fails if retro keys are added as sources. |
| `try-instead-tool-name` | **does not apply because** this change adds no `try_instead` field. |
| `route-must-answer` | **does not apply because** this change adds no route. |

**Proving test:** `pytest tests/test_ignore_bucket_names_its_rule.py::test_two_ignore_sources_report_per_source_counts_that_sum_to_ignore`

| AC | risk layer | proof | layer-match |
|----|------------|-------|-------------|
| AC1 | integration | proving test (build + verbose status) | ✅ |
| AC2 | integration | overlap test | ✅ |
| AC3 | integration | standard vs verbose / build assertions | ✅ |
| AC4 | e2e (anchor) | coverage-gap exclusion | ✅ (excluded) |

**Coverage-gap exclusions:** AC4 anchor 9,541 — no private checkout; operator paste follow-up.

- **Gate 2 status:** cleared (standing approval)

---

## Phase 3 — Execute

- **Branch:** `fix/095-ignore-bucket-does-not-name-its-rule`
- **Proving test added:** `tests/test_ignore_bucket_names_its_rule.py`
- **Verification sweep:** file axis ✅ (diff ⊆ list). Behaviour: implemented-as-approved (sibling `ignore_sources`, last-match, derived keys, verbose-only).
- **Empirical:**

```
$ scripts/docker-test.sh pytest -q
# baseline (main): 1175 passed
# post-change: 1183 passed in 85.57s
```

- **Golden/snapshot:** none
- **Design-invalidation:** none

## Phase 4 — Review ✋

**WAIVED** at solve invocation (`with skipped review`). No `Reviewed at` marker. No reviewer/challenger dispatch this phase.

## Phase 5 — Finalise ✋

- Planned outward actions (standing AGENTS.md + this solve): push branch, open PR via `gh`.
- Durable lesson: written to `docs/LESSONS.md`.
- Revert: revert the PR commit.

### Learning loop

`CLAIMS: 3 claim(s) from 1 lesson entry | T1=0 T2=2 T3=0 T4=0 T5=1 T6=0 | 0 unclassified`
`RECURRENCE: 2 recurring | 0 superseded | 2 promotion candidate(s)`
`FALSIFY: 2 candidate(s) checked | 2 still-true | 0 falsified | 0 not cheaply checkable`
`PROMOTION: 2 proposed | 0 human-ratified (cross-ticket → /mango:promote) | mango files written: 0`

Cross-ticket: `derived-not-listed-invariant` seen 093, 095; sibling-meta-non-int seen 092, 095. Run `/mango:promote` between tickets — this orchestrator does not invoke it.

---

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| 0 refine | exposure-checker (challenger) | 1 | unmeasured (host does not surface usage) | none |

`LEDGER TOTAL: unmeasured (host does not surface usage) · top cost driver: refine exposure-checker`

## Decision log

| When | Decision | Why |
|------|----------|-----|
| Gate 1 | ASSUMED A–G ratified | standing best-option |
| Gate 2 | sibling `ignore_sources`; last-match; derived keys | 082/061/092 |
| Gate 4 | review waived | solve invocation |
| final | commit + push + PR | AGENTS.md standing + this solve |
| post-PR | exposure-checker return: UNEXPOSED 2 ≡ A + E | already shipped; no re-gate |

## Session status

- **Last updated:** 2026-08-14
- **Current phase:** done (PR #105)
- **work_doc_mode:** embed · `docs/tasks/095_ignore-bucket-does-not-name-its-rule.md`
- **Next action:** none
- **Blocked on:** none

