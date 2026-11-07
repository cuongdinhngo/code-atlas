---
id: 438
slug: verify-refs-core
title: "`verify_refs`: find which references in agent docs no longer resolve — extraction, classes, states, CLI"
phase: 2
milestone: "0.11 Verify & Compute"
status: in-progress
depends_on: [384, 429, 430]
---

## Why this exists

Roadmap R1 (0.11). An agent loads `CLAUDE.md`, skills and docs as authoritative, and nothing checks
them against the code. arXiv 2610.30571 ("Stale Code Inconsistencies in Coding Agents") found agents
followed a stale instruction file in **90.1%** of convention choices, and Claude Code noticed the
conflict in 79 of 80 runs and still followed the file. On the anchor (survey 2026-11-07, counts
only): 177 agent-facing knowledge files hold 6,003 code references; **196 referenced paths existed
and are gone, 21 methods are missing on live classes, ~3.6% verifiably stale**.

The positioning: code-atlas tells the agent which of the things it was told are still true. This
ticket is the finder; 439 adds the fix (patches) and the surfaces an agent sees.

## Scope

1. **Corpus and priority classes**, default globs overridable by non-command `.code-atlas.toml`
   keys (430): `instruction` (`CLAUDE.md`, `AGENTS.md`, `.claude/rules/**`, `.claude/skills/**`,
   `.cursor/rules/**`, `.github/copilot-instructions.md`), `memory` (configured path), `reference`
   (`docs/**/*.md`, wiki folders), `archive` (maintainer globs — report-only, excluded from the
   counts 439's SessionStart line uses). Default for any corpus is maintained (roadmap §4.6).
2. **Extraction, language-free core** (R1.1). Candidates: file paths, qualified symbols, bare names in
   code spans, SQL object names in code spans, commands (counted, never executed). Symbol shapes are
   **adapter-declared reference shapes** (PHP `::`, Python dotted, SQL `schema.object`) carried by the
   handshake — a contract addition, so R3 applies. Code spans and fences are strong candidates; a
   prose word counts only on an exact indexed match.
3. **Exactly one state per reference, each with a `reason`:** `ok`, `moved` (successor via git
   rename detection `-M` or a `body_hash` match — 384, 437), `gone` (`last_seen_rev`, day-granularity
   date), `never_existed` (not in the index nor any branch's history), `ambiguous` (capped candidate
   list), `unknown` (never folded into `ok`, R5.6).
4. **Output is reference strings, never surrounding prose** (429): file, line, class, surrounding
   *kind* (list item, table cell, prose); doc-derived fields listed in `untrusted_fields`.
5. **CLI:** `code-atlas query --verify-refs [globs…] [--class …] [--format json|md]
   [--fail-on moved,gone]`, exit 0 by default; `--fail-on` is opt-in for pre-commit.
6. code-atlas **never writes** to the repo; git is read through `gitutil.py`.

## Acceptance

1. A fixture repo with known `ok`, `moved` (a rename and a body move), `gone`, `never_existed` and
   `ambiguous` references: each state asserted exactly, with its reason.
2. **429:** a doc holding instruction-like text yields reference rows only — no prose in the payload.
3. **430:** a toml cannot add a command through any key this ticket adds.
4. An `unknown` row is counted as unknown in every summary, never as `ok`.
5. `total_count` / `truncated` are truthful; an empty corpus explains itself (no file matched the
   globs ≠ every reference resolved).
6. Anchor: a full run over the 177 files in ≤ 30 s warm, reported privacy-safe (rules in 442).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 438 · **work_doc_mode:** embed · **Current phase:** 5 finalise — the PR is open; merging is the maintainer's.
- `TRACK: backend` · Run mode: `autorun 437 - 438 - 440`, second — `REVIEWER: ON` · `CHALLENGER: ON` · `cost_tier: standard`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/438-verify-refs-core`, stacked on 437 (#164, uses its `definition_states`). Contract
  `.mango/run-contract-438.txt` (mango 1.21.0). RECONCILE t0: `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND |
  0 could-not-run | 0 pending-merge`. Budget: unknown.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 0 by handle | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 5 unresolved surfaced | 2 want-decision asked | 3 how-decision resolved+cited | 2 ASSUMED | skip: no`

`gitutil.py`, `config.py`, `contract.py` (`symbol_shapes`, 345), 384's `body_hash`, 429's `untrusted_fields` and 430's
toml rules resolve. Recalled by area: 345 (the handshake already carries per-adapter grep shapes, stored in meta) and
437-C1 (a fingerprint is taken over the span the scanner names).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where symbol shapes come from | how | a `qualified` kind in the existing `symbol_shapes` (345), stored at build; the grep nudge reads `GREP_SHAPE_KINDS` only, so it is unchanged |
| H2 | a symbol `moved` by `body_hash` | how | the doc's own last commit fixes when the reference was true: the old file is found by `git grep -w` at that commit, parsed by its adapter in a temp dir, and its hash compared with the one same-name definition now (384) |
| H3 | git cost on a large repo | how | one history pass (renames, deletions, every branch's added paths) per run; `-S` and `grep` share a 12 s budget, and a row past it is `unknown`, counted (R5.6) |
| W1 | the contract addition (scope 2: "R3 applies") | want | **ASSUMED:** no bump here — the same one 0.11 bump 437 deferred (BACKLOG *Follow-ups* already names it for 437 + 438) |
| W2 | where a doc names paths from | want | **ASSUMED:** root, then the doc's folder, then a unique tracked path ending so (a monorepo doc writes from its subproject); several endings are `ambiguous` |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance) | 3 decomposed | ROWS: C=3 R=6 G=1 AC=6`
`CLARIFICATION: 5 raised | 5 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/14 touched files under UI paths`
`SCOPE: L`
`TIER: full`
`STRUCTURE: native`

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "This ticket is the finder" | every reference, one state, a reason | ⚠ |
| C1 | Scope 2 | "language-free core (R1.1)" | shapes from adapters | ⚠ |
| C2 | Scope 4 | "never surrounding prose (429)" | strings + `context` only | ⚠ |
| C3 | Scope 6 | "code-atlas never writes to the repo" | temp dir outside it | ⚠ |
| R1 | Scope 1 | "default globs overridable by non-command toml keys" | `refs_*` knobs | ⚠ |
| R2 | Scope 2 | "file paths, qualified symbols, bare names in code spans, SQL object names …, commands" | `extract` + `kind_of` | ⚠ |
| R3 | Scope 3 | "Exactly one state per reference, each with a `reason`" | `Resolver` | ⚠ |
| R4 | Scope 4 | "file, line, class, surrounding *kind*" | row fields | ⚠ |
| R5 | Scope 5 | "`--verify-refs [globs…] [--class …] [--format json|md] [--fail-on moved,gone]`" | `query.py` | ⚠ |
| R6 | Scope 6 | "git is read through `gitutil.py`" | new read-only helpers | ⚠ |
| AC1–AC6 | Acc 1–6 | as written | AC1–AC5 fixture, AC6 anchor | ⚠ |

`BASELINE: green — tests/test_config.py, tests/contract/test_symbol_shapes.py, test_security_standard.py on the 437 branch at 3e138aec: green before the change`

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §1 (change-type) ✅ R1.1 shapes from adapters, R1.4 SQL only in store.py · §2 (change-type) ✅ each shape is its language's own syntax · §3 (change-type) ✅ R3.1 owed at the 0.11 bump (W1) · §6 (change-type) ✅ R6.5 seen red · §7 (change-type) ✅ R7.2, R7.5, R7.6`

## Phase 2 — design

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

437-C1 traced: the Python adapter's span for a function after a class began with that class's DEDENT tokens, so a
function moved unchanged to another file hashed apart (`lib.a.compute_total` `ba8f…` vs `lib.b` `d6a5…`); the fix drops
a span's leading DEDENTs (`adapters/python/src/body_hash.py`), after which both hash `d6a5987fcfe7ea80`.

**Approach.** `code_atlas/doc_refs.py` (corpus → extract → kind → resolve → summarise); `gitutil` history helpers;
`store.qname_prefix_exists` (a range seek, so `os.path` is no reference when nothing indexed starts `os.`); four `refs_*`
knobs; `qualified` shapes for php, python, sql; `--verify-refs` in `query.py`; docs (README, TOOLS, SECURITY's git list,
ADAPTER_PLAYBOOK, CHANGELOG).
**Rejected:** a separate handshake field for doc shapes — `symbol_shapes` is the one place a language says what its
symbols look like; resolving each reference with its own git pass — 86k references on the anchor.
**Proving test:** `tests/test_verify_refs.py`.

`EXCLUSIONS: 2 recorded | 2 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 1 proven on a real corpus`

- E1 — AC6 on the anchor; **expiry:** `~/code-atlas-review/438-anchor.md` is written before the PR opens.
- E2 — W1, the contract bump deferred to the 0.11 release; approved under the handover; **expiry:** ratified on the PR.

## Phase 3 — execute

Main loop, no `implementer`. **Verification sweep:** the diff names the files of the Approach plus `SECURITY.md` (its git
command list is test-held), `tests/test_config.py` (knob pins), `tests/contract/test_symbol_shapes.py` (vocabulary pin),
`code_atlas/hooks/nudge.py` (reads `GREP_SHAPE_KINDS`) and `tests/test_untrusted_output.py` is untouched.
**R6.5:** on 437's tree the test cannot import `doc_refs`; with `doc_refs` but without the Python DEDENT fix,
`lib.a.compute_total` answered `gone / removed_since_the_doc` instead of `moved / body_hash`.

**AC6 (E1 discharged)** — `~/code-atlas-review/438-anchor.md`: 1,884 files, 86,814 references, **24.1 s warm**; three
anchor fixes came from it — a directory index built once (the first run passed 15 min), no case-folded full-scan fallback,
and subproject-relative paths.

## Phase 4 — review

`REVIEWER: ON` · `CHALLENGER: ON`. Review step: mango `reviewer` (Sonnet), round 1, at `887f7022`.

- **`reviewer` round 1** (77,276 tokens): CHANGES REQUESTED → conditional LGTM on 1–4. Security clean: needles are word
  runs behind `-e` / an attached `-S`, revisions checked, the temp dir only parses.
  - **1 (bump), taken as an owner:** W1 stays `ASSUMED`; the 0.11 bump line in BACKLOG names 437 + 438, and the
    CHANGELOG says stored Python hashes move once too.
  - **2, taken:** the history passes and each doc's own commit read through the git budget, clocked.
  - **3, taken:** an external-looking dotted name is counted (`skipped_as_external`), never silently dropped.
  - **4, taken:** one same-name definition with another body is `ambiguous` (`same_name_elsewhere_body_changed`),
    never `gone`. **Minors taken:** merges diffed against their first parent; a non-text old blob skipped.
- **`challenger` round 1** (77,669 tokens, ticket-blind): 14 met · 2 not met (inline commands uncounted; `gone` rows
  without a date) · 1 can't tell. **Taken:** I1 an unbuilt index answers `symbols_unchecked_no_index`; I2 a path only
  another branch holds is `unknown`, a rename-then-removed path carries the rename's day; M1–M5 (inline command spans,
  a class filter that empties the corpus, a 512-char cap, `|` escaped, `limit` fails loud).
- **`challenger` round 2** (87,007 tokens, verify-only at `adc01b7c`): rows 4 and 7 met; its final table, transcribed:

`CHALLENGER VERDICT: 17 requirement(s) rebuilt | 16 met | 0 not met | 1 can't tell | 0 not-met covered by a recorded exclusion`

**Not taken:** a `missing_on_live_container` row stays `gone` with a null date when git cannot answer — the container is
live and the member is not, so `gone` is proven; only its date is unknown. The can't-tell is AC6 (off-diff), held by
E1's report: `m + g = 16 ≠ 17`, so **Gate 4 does not close by the harness's arithmetic** — the same structural gap as
437; the PR opens as a draft. `Ph3/4 proven by`: AC1–AC5 → `tests/test_verify_refs.py` (26); AC6 →
`~/code-atlas-review/438-anchor.md`.

## Phase 5 — finalise

**Durable lesson.** 438-C1 `a-lookup-per-reference-over-history-needs-an-index-built-once` (new, type 2).

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `feat/438-verify-refs-core`; open its PR (base: 437's branch). Deferred: ratify W1/W2; merge.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 4 review | rule-book `reviewer` | 1 | 77,276 |
| 4 review | ticket-blind `challenger` | 1 | 77,669 |
| 4 review | ticket-blind `challenger` | 2 | 87,007 |

`LEDGER TOTAL: 241,952 · top cost driver: 4 review / challenger` — main loop unmeasured.
