---
id: 213
slug: a-declaration-fingerprint-so-a-cosmetic-edit-is-not-reparsed
title: "The incremental byte-hash tier catches a file that did not change; nothing catches a file whose *declarations* did not change, so a reformat re-parses the tree"
phase: 1.5b
milestone: Freshness
status: done
depends_on: [212, 052, 080]
---

## Why this exists

This is [212](212_an-incremental-update-escalates-on-correctness-but-never-on-cost.md)'s Scope 3,
split out at its Gate 0 when the ticket was measured against the code and found to be **L**. The
maintainer ratified the split; 212 shipped the upper tier (a cost escalation) and this ticket is the
lower one.

**212's premise needed correcting first, and the correction is this ticket's starting point.** 212
said *"No lower tier… nothing compares what changed inside a file against what the graph stores."*
There **is** one: `incremental_update`'s `hashing` phase (`code_atlas/indexer.py:386-404`) calls
`file_is_current` (`:568-571`), which compares the file's current bytes against the hash the index
stored and skips the parse when they match. A **dependent** is deliberately excluded from that skip,
with the reason in a comment beside it.

So the real gap is one tier up: a file whose **bytes changed** but whose **declarations did not** is
re-parsed. A reformat, a comment edit, a copyright-header bump: every touched file pays a full parse,
re-link and reconcile to produce rows the graph already holds.

### The constraint that shapes the answer, and it is not negotiable

A fingerprint over *declarations* cannot be computed without knowing the language: comments and
string literals are syntax. **R1.1 forbids a language branch in the core**, and the parse is what
produces declarations — so "hash the declarations, then decide whether to parse" is circular for the
run that would benefit.

The maintainer's ratified answer is the honest subset: a **language-agnostic, whitespace-normalised
hash**. Collapse every run of whitespace and hash the remainder.

- It **catches** the case 212's own sentence names first: a reformat, an indentation change, a line
  ending or trailing-whitespace sweep.
- It does **not** catch a comment edit or a string-literal change. Saying so here is the point — an
  implementer should not discover it at review.
- A fingerprint that cannot be computed (unreadable file, decode error) must fail loud into
  **"parse it"**, never into "skip it" (**R5.3**).

Two paths are explicitly rejected up front, so they are not re-litigated:

1. **A comment-aware normaliser in the core** — an R1.1 violation, and the rule has no exception for
   "just a small regex".
2. **A declaration digest in the adapter contract** — each adapter reporting a digest is a contract
   bump (**R3**) across three adapters, and the digest only exists *after* the parse, so it cannot
   save the parse that produced it. It would enable a *next-run* saving, which is a different (and
   larger) design.

## Scope

1. **A whitespace-normalised fingerprint stored per file**, beside the byte hash rather than
   replacing it: the byte hash stays the fast path, and the fingerprint is consulted only when the
   byte hash misses.
2. **A file whose fingerprint is unchanged is not parsed** — and the graph is identical to a run
   that did parse it (**R4.2**, and this ticket's central risk).
3. **The skip is reported.** A skipped file must never look like an indexed one (212's Scope 4, and
   202's lesson: a build that did less work must not leave an index that reports as though it did
   more).
4. **Never skip on a correctness route.** The three correctness escalations and 212's cost tier
   outrank the fingerprint; a contract-era change re-parses everything regardless.
5. **Measure what it buys** on the anchor: how many files a reformat-shaped commit skips, and the
   wall-clock difference. If the answer is "almost none on real commits", that is the finding, and
   the tier should not ship on a hope.

### Explicitly not in scope

- **Comment- or string-literal-aware normalisation** (R1.1) and **an adapter-side digest** (R3) —
  both rejected above.
- **Cross-run caching of parse results.** A fingerprint decides whether to parse; it never stores
  what a parse produced.
- **The upper tier**, which is [212](212_an-incremental-update-escalates-on-correctness-but-never-on-cost.md).

## Constraints

- **R1.1** — no language branch in the core. The normaliser sees bytes, never syntax.
- **R4.2** — the graph is identical whichever route was taken. A fingerprint that misses a construct
  silently under-indexes while the index still reports current; guard it directly.
- **R5.3** — a fingerprint that cannot be computed fails loud into "parse it".
- **R6.5** — the guard ships only once observed failing: a file whose text changes and whose
  declarations do not, proven identical either way; then one whose declarations do change, proven
  not skipped.
- **R6.9** — assert at the consumer: the guard reads the resulting graph, not the fingerprint value.

## Acceptance criteria

1. A file whose whitespace-normalised fingerprint is unchanged is not re-parsed, and the resulting
   graph is identical to a run that did re-parse it.
2. A file whose fingerprint changed is never skipped, proven by a fixture that fails without the
   guard.
3. A fingerprint that cannot be computed results in a parse, and a test exhibits that path.
4. The skip is visible in the build report; a skipped file is distinguishable from an indexed one.
5. The correctness escalations and 212's cost tier still take precedence, pinned by a test.
6. Scope 5's measurement is recorded with its method — including the honest answer if the saving is
   negligible on real commits.

---

## Working doc (autorun 2026-09-04)

**KEY:** 213 · **work_doc_mode:** embed · **Current phase:** 5 finalise

### Phase 0 — refine

`PREMISE: 8 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

Refine skipped: ticket already ratifies whitespace-normalised hash (not comment-aware, not adapter digest). Ambiguous: anchor-scale Scope 5 measurement (real_corpus_path unset).

### Phase 1 — analysis

`PREMISE: 8 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Why this exists / Scope, Constraints, Acceptance criteria, References) | 4 decomposed | ROWS: C=5 R=5 G=1 AC=6`
`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`
`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — §R1.1 (bytes-only normaliser) ✅ · §R4.2 (graph identical either route) ✅ · §R5.3 (fail loud into parse) ✅ · §R6.5 (guard observed failing) ✅ · §R6.9 (assert at consumer graph) ✅ · §R3 (schema bump for files.fingerprint) ✅`
`TRACK: backend — 0/N touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

`HANDLES: 6 recalled | 6 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

**E1**: AC6 / Scope 5 anchor measurement. Expiry: `real_corpus_path` set in `.harness.json`. Close-out: **cannot measure on this checkout** — honest deferral, not a fake number.

### Phase 2 — design

`HANDLES: 6 recalled | 6 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Approach:** `files.fingerprint` column + `SCHEMA_VERSION` 4→5. After byte-hash miss, compare whitespace-collapsed SHA-256; on hit, `touch_file_bytes` and skip parse. `BuildReport.fingerprint_skipped` reports the skip. Dependents never fingerprint-skip. Correctness escalations and cost tier remain upstream/downstream as today.

**Proving test:** `tests/test_fingerprint_skip.py::test_whitespace_reformat_is_not_reparsed_and_graph_is_identical`

### Phase 3 — execute

What landed: schema 5 + fingerprint column; `_whitespace_fingerprint` / `_fingerprint_skip`; BuildReport field; tests for AC1–5. Challenger round 1 asked for AC3 fail-into-parse exhibit and AC6 deferral on allowed docs — both landed.

Delta-green: `.venv/bin/python -m pytest -q` — **2865 passed** on this Linux host (pre-AC3 follow-up; fingerprint suite re-green after).

### Phase 4 — review

`reviewer`: OFF (`--no-reviewer`).
`challenger`: round 1 CHANGES REQUESTED (AC3 test too thin; AC6 unrecorded) → fixed → round 2 **LGTM** (8 met / 0 not met).
Verdict: **clean (challenger only — REVIEWER: OFF)**.

`Reviewed at 0f5d597071c0acad412ce4d473880c43e4e3b036`
Reviewed files: `code_atlas/indexer.py`, `code_atlas/store.py`, `docs/BACKLOG.md`, `docs/PLAN.md`, `docs/TOKEN_LEDGER.md`, `docs/tasks/213_a-declaration-fingerprint-so-a-cosmetic-edit-is-not-reparsed.md`, `tests/test_build_report_scale_naming.py`, `tests/test_fingerprint_skip.py`, `tests/test_store.py`
Working-doc path: `docs/tasks/213_a-declaration-fingerprint-so-a-cosmetic-edit-is-not-reparsed.md`

Proving test at review: `.venv/bin/python -m pytest tests/test_fingerprint_skip.py -q` → **7 passed** (Ran at e536b1dd447b44aafc7e83c3d77ecca75496834f (proving suite); bookkeeping commit 0f5d597).

### Phase 5 — finalise

PR [#262](https://github.com/cuongdinhngo/code-atlas/pull/262) opened. Merge deferred (not authorised by handover).

### Phase 6 — post-PR review round (maintainer-directed, 2026-09-04)

The maintainer asked for a review of the open PR. It found **AC1 / R4.2 broken by the shipped
normaliser**, and the finding is the reason the tier's reach is now smaller than the ticket assumed.

**The defect.** `_whitespace_fingerprint` collapsed *every* whitespace run, newlines included, so
two files whose declarations sit on different lines shared a fingerprint. A reformat that inserted
a blank line was skipped, `nodes.line_start` / `line_end` / `edges.line` kept their pre-reformat
values, and `touch_file_bytes` refreshed the byte hash — so 035's read-through repair could never
fire and the index reported current. Reproduced two ways:

- **PHP adapter**, blank lines inserted: skip left `Alpha` at line 2 and `run` at line 3; a parse
  produces line 4 and line 6.
- **Fixture adapter**, `# symbol:` marker re-indented: skip left `['Alpha', 'Thing']`; a parse
  produces `['Thing']`. Leading whitespace is syntax the core is not allowed to reason about (R1.1),
  and the conformance fixture is itself column-sensitive.

Neither is inside the ticket's ratified exclusion, which names comment and string-literal edits only.
The proving test missed both because its reformat kept the sole declaration on line 1, and
`fake_adapter.py` hard-codes `line_start: 1`.

**The fix (maintainer chose the line-preserving option).** The normaliser now normalises line endings
(`\r\n`, `\r` → `\n`) and strips per-line trailing whitespace, keeping every newline and all leading
whitespace. A fingerprint hit is therefore also a guarantee that no line moved, and the only edits it
can equate are trailing whitespace, line endings and a missing final newline — none of which any
parser turns into a node, an edge or a line. `bytes.splitlines()` breaks on `\r` / `\n` / `\r\n` and
nothing else, so the fingerprint's line boundaries are the parser's.

Two guards added, each observed red against the old normaliser (R6.5):
`test_a_line_shift_is_never_fingerprint_skipped`, `test_an_indentation_change_is_never_fingerprint_skipped`.
`test_whitespace_collapse_is_deterministic` became `test_the_normaliser_equates_only_line_preserving_edits`,
which pins both what is equated and what must not be.

Also in this round: the per-byte Python loop became `splitlines` + `rstrip` + `join`, cutting the
full-build cost it adds on the 24.6k anchor from **17.3 s to 2.8 s** (measured on this host at 28 KB
per file); the duplicate `fingerprint_skipped = 0` in the hashing branch was dropped.

**What the tier now buys, honestly.** Line-ending and trailing-whitespace sweeps — a `.editorconfig`
trim, a CRLF normalisation. It no longer catches the indentation reformat the ticket's own Scope
names first, because catching it soundly needs a language fact the core may not hold (R1.1). With
AC6 / Scope 5 still unmeasured (E1, `real_corpus_path` null), **whether that residue is worth a
schema bump is unproven** — Scope 5's "the tier should not ship on a hope" now applies to a narrower
tier than the one it was written for, and this is the open question at merge.

Not fixed, deliberately outside the approved change list: `_whitespace_fingerprint` re-reads bytes
that `_digest` already read, so every parsed file is read twice. Worth a follow-up, not a widening
of this diff.

Durable lesson: none new — AC6 E1 is the known `real_corpus_path` null class already escalated.

---

## References

[212](212_an-incremental-update-escalates-on-correctness-but-never-on-cost.md) (the ticket this was
split from, and the upper tier), [052](052_incremental-noop-cost.md) (the phase timings and the
profiler that measures them), [080](080_noop-incremental-cost-and-uninterpretable-writes.md) (the
no-op floor), [202](202_a-killed-build-leaves-an-index-that-reports-current.md) (a build that did
less work must not report as though it did more).
