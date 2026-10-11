---
id: 384
slug: symbol-changed-since-revision
title: 'Nothing answers "has this method''s body changed since revision X" — a file diff is the finest grain'
phase: 2
milestone: Trust
status: done
depends_on: []
---

**Reopened 2026-10-11 by the maintainer:** the anchor project runs this as soon as it ships; that consumer is the evidence the 2026-10-10 deferral waited for.

## Why this exists

Anything written about code goes stale when the code changes, and the reader cannot tell. A
consuming repo that records "this behaviour was verified at revision X" and anchors the record to
a handful of methods needs to ask "did any of those methods change since X" — not "did any of
their files change". In legacy trees where a page script runs to thousands of lines, a file-level
diff flags nearly every record on every release and the signal drowns.

The index records build identity (`code_atlas/build_info.py`, `BUILD_KIND_CONTENT_HASH`) but no
per-symbol fingerprint, so the finest answer available is `git diff --name-only` plus `impact`.

The same question serves review ("which of the methods this PR claims to leave alone actually
changed?") and signed claims (383: a claim can still `hold` on its count while the body under it
changed). The records themselves stay in the consuming repo; code-atlas answers only about symbols.

## Scope

1. At build, store a normalised body fingerprint per symbol (whitespace- and comment-insensitive,
   decide at design), carried through incremental builds.
2. A way to ask, for a list of qnames or paths and a base revision: `unchanged | body_changed |
   signature_changed | moved | removed | unknown_at_base`. Exposed on 382's CLI; whether it is also
   a parameter on an existing tool (e.g. `impact`) is a design decision — the tool count stays 24.
3. The base revision's fingerprints come from a snapshot the consumer exports and keeps (one
   command, written where the consumer says) — the index is not required to keep history.

## Assumptions to prove at design

- Build-time cost on the anchor index is recorded; ship only if the full build slows by less than
  an agreed bound.
- Every adapter (PHP, TS/JS, Python, T-SQL) supplies a body range the hash can cover; an adapter
  that cannot answers `unknown`, never `unchanged`.

## Acceptance criteria

- **AC1:** a comment-only or whitespace-only edit answers `unchanged`; a one-token body edit
  answers `body_changed`; a parameter change answers `signature_changed`.
- **AC2:** a method moved to another file with an identical body answers `moved`, not
  `removed` + new.
- **AC3:** the build-time overhead on the anchor index is recorded in the task.
- **AC4:** a symbol absent from the base snapshot answers `unknown_at_base`, never `unchanged`.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 384 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W1, W2 and runs E1 on the anchor, then merges. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: L` · `STRUCTURE: native` · Run mode: `autorun 383 - 384 - 385 with skipped reviewer` —
  `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`. The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/384-symbol-changed-since-revision`, stacked on 383 (`ce5e4f73`). Contract `.mango/run-contract-384.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 17 unresolved surfaced | 2 want-decision asked | 15 how-decision resolved+cited | 2 ASSUMED | skip: no`

**Premise.** `code_atlas/build_info.py` (`BUILD_KIND_CONTENT_HASH`), 382's `code_atlas/query.py`, the four adapters and
383's claim resolve. Recall: no live claim names a class this change touches.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 43,896 tokens) added H11–H15.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | who fingerprints | how | each adapter, from its own tokenizer — the core has no comment grammar and may name no language (R1.1); "every adapter supplies…" (ticket assumption 2) |
| H2 | where it lives | how | `Node.extra.body_hash`, 16 hex — an advertised optional key, not a bump (`contract.py`: `constructor`, `unmodelled_resolution`); rows are re-emitted per file, so incremental builds carry it (Scope 1) |
| H3 | which nodes | how | every node but File/Namespace — they span unrelated symbols |
| H4 | the normalisation | how | the tokens whose first line is in `[line_start, line_end]`, comments and whitespace dropped; Python keeps INDENT/DEDENT/NEWLINE as markers (structure); a docstring is code; SQL per line (its scanner streams, task 184) |
| H5 | signature | how | params + modifiers + `extra.type`, checked before the body (AC1's parameter case) |
| H6 | moved | how | the same fingerprint in another file: same qname, else same name and kind (`qname_now`) — AC2 |
| H7 | the two commands | how | `query --snapshot-symbols <out>` (Scope 3, "written where the consumer says"), `--changed-since <out> --qname/--path` (Scope 2); CLI only, 24 tools |
| H8 | no fingerprint, or an edit the index has not seen | how | `unknown` (`no_body_hash`, `file_changed_since_index`) — ticket assumption 2, R5.6 |
| H9 | exit | how | `3` unless all unchanged — 383's verdict code |
| H10 | snapshot shape | how | `code-atlas-symbols/1`, rev + ref, symbols in `_NODE_ORDER` (R4.2) |
| H11 | several move candidates | how | `unknown`, `ambiguous_move` — R5.2, a pick is a guess |
| H12 | `--path` | how | every symbol the snapshot held in the file, plus each it gained (`unknown_at_base`) |
| H13 | rename | how | the tokens include the name, so a rename is `removed`; documented |
| H14 | a tokenizer change in an adapter | how | errs to `body_changed`, never `unchanged`; CHANGELOG names it; documented |
| H15 | 64-bit width | how | collision odds 2⁻⁶⁴ per pair; documented |
| W1 | AC3's anchor index is not on this machine | want | **ASSUMED (awaiting ratification):** measured on four public pinned samples, one per adapter; the anchor is exclusion E1 |
| W2 | the "agreed bound" | want | **ASSUMED (awaiting ratification):** ≤ 10 % per sample, on the median of three full builds |

## Phase 1 — analysis

`SECTIONS: 4 found (Why this exists · Scope · Assumptions to prove at design · Acceptance criteria) | 4 decomposed | ROWS: C=2 R=3 G=1 AC=4`
`CLARIFICATION: 17 raised | 17 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/19 touched files under UI paths`
`BASELINE: green`
`SCOPE: L`
`TIER: full`

### BASELINE

383's head `ce5e4f73`, this branch's base: `scripts/gate.sh` 21/21 green (383's working doc). Ran at ce5e4f73.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "did any of those methods change since X" | per-symbol change since a revision | ✅ |
| C1 | Why | "The records themselves stay in the consuming repo" | the snapshot is the consumer's file | ✅ |
| C2 | Assumptions | "an adapter that cannot answers `unknown`, never `unchanged`" | H8 | ✅ |
| R1 | Scope 1 | a normalised fingerprint per symbol, through incremental builds | H1–H4 | ✅ |
| R2 | Scope 2 | the six statuses for qnames or paths, on 382's CLI | H5–H7 | ✅ |
| R3 | Scope 3 | one export command, written where the consumer says | H7, H10 | ✅ |
| AC1 | AC | layout `unchanged`, one token `body_changed`, a parameter `signature_changed` | per adapter | ✅ |
| AC2 | AC | moved, not removed + new | | ✅ |
| AC3 | AC | build-time overhead on the anchor index recorded | public samples; anchor E1 | ⚠ E1 |
| AC4 | AC | absent from the base → `unknown_at_base` | | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — four statuses per adapter, base re-run as the positive control | PHP, TS, Python, SQL through real builds |
| AC2 | yes — `moved`, `file_base`/`file_now` | PHP keeps the qname; Python's follows the module |
| AC3 | yes — medians recorded below; anchor excluded (E1) | |
| AC4 | yes — by qname and by path | |

### Rule sections

`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the core reads an opaque key; each tokenizer lives in its adapter · §R1.6 (change-type) ✅ body_hash is advertised, never required: absent answers unknown · §R2.1 (change-type) ✅ each adapter uses its language's own tokenizer · §R3.1 (change-type) ✅ an optional extra key, the contract.py precedent — no vocabulary moved · §R4.2 (change-type) ✅ a digest of tokens, snapshot in _NODE_ORDER; test_the_snapshot_is_the_same_bytes_for_the_same_tree · §R5.6 (change-type) ✅ unknown_at_base, no_body_hash, file_changed_since_index, ambiguous_move never read unchanged · §R6.6 (change-type) ✅ PHPStan max, tsc ×2, mypy clean`

## Phase 2 — design

### Approach

1. Each adapter stamps `extra.body_hash` after its walk: PHP `BodyHash::stamp` (PhpToken), TS `src/bodyHash.js` (AST
   leaves, JSDoc skipped), Python `src/body_hash.py` (tokenize), SQL `src/bodyHash.js` (a per-line digest fed by the scan).
2. `contract.BODY_HASH`; `GraphStore.iter_nodes` streams the node table.
3. `code_atlas/symbol_changes.py`: `snapshot`, `read_snapshot`, `compare`.
4. `query.py`: `--snapshot-symbols OUT`, `--changed-since SNAPSHOT --qname --path`, against `dirty_indexed_paths`.
5. Docs: design record, ADAPTER_PLAYBOOK's field table, README, CHANGELOG.

### Rejected alternatives

- **Hash in the core over a line range** — the core has no comment grammar; a generic lexer reads a `//` in a JS regex or
  a PHP heredoc as a comment, and a change after it would read `unchanged`.
- **A contract bump for the key** — a bump cuts a release, a release is a pushed tag, and a tag is the maintainer's;
  the optional-key precedent carries it.
- **A parameter on `impact`** — the question is about a stored snapshot no tool holds.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| every adapter's tokens drop comments and layout | verified | AC1 per adapter |
| the stamp costs under W2's bound | verified | the medians below |
| every symbol gets a stamp | verified | 16,980/16,980 · 3,157/3,157 · 357/357 · 635/635 on the four samples |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | stamp | four adapters (`Parser.php`+`BodyHash.php`, `parse.js`+`bodyHash.js`, `parse.py`+`body_hash.py`, `scan.js`+`bodyHash.js`) | every node row's `extra` (read_symbol lists extra keys) | R1, C2 | 4/4 |
| 2 | key, stream | `code_atlas/contract.py`, `code_atlas/store.py` | — | R1, R3 | 2/2 |
| 3 | compare | `code_atlas/symbol_changes.py` (new core module) | core-module pins 99 → 100 (P5) | R2 | 1/1 |
| 4 | CLI | `code_atlas/query.py` | 383's modes (shared exit 3) | R2, R3 | 1/1 |
| 5 | tests | `tests/test_symbol_changed_since.py`, the two module pins | — | AC1–AC4 | 3/3 |
| 6 | docs | `docs/design/impact-and-claims.md`, `docs/ADAPTER_PLAYBOOK.md`, `README.md`, `CHANGELOG.md` | doc budgets | G1 | 4/4 |
| 7 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — adapter + build + CLI | four real builds, edit, rebuild, `--changed-since` | authored | ✅ |
| AC2 | integration | a move across files, PHP and Python | authored | ✅ |
| AC3 | runtime | full-build medians on public samples | real-corpus (pinned samples) | ✅ — anchor E1 |
| AC4 | integration | a symbol added after the snapshot | authored | ✅ |

**E1 (coverage-gap exclusion).** AC3's anchor index · risk: low (four public corpora within bound) · why: the anchor is
a private repo not on this machine · follow-up: the maintainer runs `code-atlas-build --full` with and without the
branch on the anchor · `expiry: when the anchor index is available to the run` · `seen: 384`.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_symbol_changed_since.py`.

### Rollback

`git revert`; an index built with the stamps reads the same to older code, which ignores the key.

## Phase 3 — execute

Commits `29e40be1` (adapters, core, tests), `0514c8ee` (docs), `acbc366b` (ambiguous move), `5e8c3912` (challenger). **Red first** (R6.5): on
`main` (`f1112a6c`) the new file fails at collection — `code_atlas.symbol_changes` does not exist; the positive
controls (`base` re-run, the stamped snapshot) pin each negative.

**AC3 — full-build medians of three runs** (`CA_WORKERS=4`, temp DB, this host), base `f1112a6c` → branch:

| sample (adapter) | files | nodes | base | branch |
|---|---|---|---|---|
| pydantic (python) | 447 | 17,444 | 9.08 s | 9.07 s |
| socketio (typescript) | 371 | 3,535 | 5.11 s | 4.48 s |
| symfony_demo (php) | 60 | 461 | 0.83 s | 0.83 s |
| adventureworks_oltp (sql) | 1 | 636 | 0.44 s | 0.46 s |

Noise exceeds the effect on the two larger samples; the worst measured slowdown is +4.5 % (SQL), inside W2.

**Verification sweep.** File axis: the diff is the change list; `ruff`, `mypy` (100 files), PHPStan max, `tsc` (TS,
SQL) clean. Behaviour axis: Approach 1–5 implemented as approved; H11 landed after the exposure-checker.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`. Reviewed at 5e8c3912 — files: the four adapters' stamp and entry
files, `code_atlas/{contract,store,symbol_changes,query}.py`, `tests/test_symbol_changed_since.py`, the two module pins,
`docs/design/impact-and-claims.md`, `docs/ADAPTER_PLAYBOOK.md`, `README.md`, `CHANGELOG.md`; working doc: this file.

- **`challenger` round 1** (ticket-blind, 73,465 tokens): 7 met · 0 not met · 1 can't tell (AC3 — E1). It drove every
  adapter on comment-shaped strings, regexes, heredocs and SQL `--` in literals: all data. Findings: **a Python decorator
  edit read `unchanged`** (the span began at `def`); a non-git tree sees no drift; same-file twins; a class hash moves
  with its members (undocumented); a snapshot of a drifted index carried the indexed `rev`; moves tested on two adapters.
  Fixed in `5e8c3912`: the Python span starts at the first decorator; twins cannot reach the store (`UNIQUE(qname, file)`,
  keep-first), which hid a sharper case — an edit to a TS overload's implementation read `unchanged` — so every adapter
  now hashes the union span of a qname's declarations; a snapshot records `drifted` and those symbols answer
  `unknown` (`snapshot_file_drifted`); moves tested on all four; git dependence and class spans documented. Each
  with a test; the decorator and overload cases were seen `unchanged` before the fix.

Verdict: clean (challenger only — REVIEWER: OFF). Matrix `Ph3/4 proven by`: R1–R3, C2, AC1, AC2, AC4 →
`tests/test_symbol_changed_since.py`; AC3 → the medians above + E1; G1, C1 → the diff and the design record.

## Phase 5 — finalise

**Durable lesson.** One claim, 384-C1 in `docs/LESSONS.md`: a store that de-dupes keep-first hides every later
declaration from a per-row fingerprint.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `feat/384-symbol-changed-since-revision`; open the PR against `main` (stacked on #67).
Deferred to the maintainer: ratify W1, W2; run E1 on the anchor; merge after #67.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 43,896 |
| 4 review | `challenger` (ticket-blind) | 1 | 73,465 |

`LEDGER TOTAL: 117,361 · top cost driver: challenger`
