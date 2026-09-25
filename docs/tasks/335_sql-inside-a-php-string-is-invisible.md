---
id: 335
slug: sql-inside-a-php-string-is-invisible
title: "SQL inside a PHP string literal emits no edge — 'who writes this table' and 'who EXECs this proc' still fall back to grep, the most-repeated gap across field retros"
phase: 1.5b
milestone: Coverage
status: in-progress
depends_on: [222, 328]
---

## Why this exists (field retros, 2026-09-24 and 2026-09-25)

Four retros in two days asked the same question and got the same answer:

- `find_references` on a table → `no_matches` with `authoritative: false` / `writes_emitters_only`
  (`find_references.py:251-254`). Grep then found 6, 10 and 1 PHP writers in three of them.
- `find_callers` on a stored procedure missed 2 of 5 entry points: PHP call sites that `EXEC` the
  proc from a string.

328 named this as *"the retro's actual culprit and the larger win"* and set it aside as a separate
ticket. This is that ticket.

## Goal

A PHP string literal whose text is a T-SQL write or `EXEC` yields an edge onto the table or proc it
names, at a tier that says it was read from text.

## Scope / Deliverables

1. **The PHP adapter emits** `WRITES` / `DELETES` / `CALLS` from a string literal (or heredoc) whose
   text begins a T-SQL statement: `INSERT INTO`, `UPDATE`, `MERGE INTO`, `DELETE FROM`, `EXEC`.
   Tier `HEURISTIC`; interpolated segments break the match rather than being guessed.
2. **The link reuses 222's cross-language machinery** — the target is a SQL qname, the source a
   PHP symbol. No second resolver.
3. **`writes_emitters_only` narrows** to what is still unmeasured once PHP emits.

## Constraints

- **R2.2** — keyed on T-SQL statement grammar, never on a wrapper method's name (`query`,
  `querySP`, …). The retro's `querySP('<Name>'` idea is exactly what R2.2 forbids.
- **R1.4** — the PHP adapter recognises statement *shape* only; it does not parse SQL. How far the
  shape goes is a design question for this ticket, answered before code.
- **R4.2** — identical input, identical rows.

## Acceptance criteria

- **AC1** `$sql = "INSERT INTO dbo.T (a) VALUES (1)";` inside a method → `find_references dbo.T`
  lists that method, `HEURISTIC`; red on today's code.
- **AC2** `"EXEC dbo.Gen @x = 1"` → `find_callers dbo.Gen` lists the PHP method.
- **AC3** `"UPDATE {$table} SET …"` emits nothing (interpolated target).
- **AC4** A string that merely mentions a table (`"see dbo.T"`) emits nothing.

## Out of scope

- SQL built by concatenation across statements.
- Column-level `WRITES` from PHP strings, unless AC1's design makes it free.

## References
`adapters/php/src/Visitor.php`; `code_atlas/tools/find_references.py:251-254`; tickets 222, 328.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 335 — SQL at the start of a PHP string is an edge (working doc)

- **Ticket:** 335 · local · **SCOPE:** M · **TIER:** full · **TRACK:** backend
- **REVIEWER:** OFF (`--no-reviewer`) · **CHALLENGER:** ON
- **Current phase:** review
- **Session status:** in-progress — autorun
- **Reviewed at:** —

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 4 unresolved surfaced | 0 want-decision asked | 4 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW1 — **how far the shape goes** (C "answered before code"): a leading keyword (`INSERT INTO`,
`UPDATE`, `MERGE INTO`, `DELETE FROM`, `EXEC`/`EXECUTE`), one T-SQL object name (`[..]`, `".."` or
a regular identifier, dotted), and **the clause T-SQL requires after that name** (`(`/`VALUES`/
`SELECT`/… after INSERT, `SET` after UPDATE, `USING` after MERGE, `WHERE`/`OUTPUT` after DELETE, a
parameter after EXEC). A schema-qualified DELETE / EXEC may instead end the literal. Prose —
"Update settings", "Insert into cart", "Delete from list" — has no clause and reads as nothing.
Citation: R1.4 (shape, not a parse), R2.2 (grammar, never a wrapper name), AC4.
HOW2 — **EXEC is schema-qualified or nothing.** A bare CALLS target from PHP reaches the bare-name
Method fallback, which binds same-language methods by name (204): `EXEC GetUsers @id` would link a
PHP method `GetUsers`. A qualified target links only by FQN. Citation: 204, AC2 (`dbo.Gen`).
HOW3 — **where a name ends.** A literal a concatenation continues, or the text before an
interpolation, does not end the SQL: the name must end inside it (whitespace, `;`, the clause).
`"UPDATE dbo.T" . $sfx . " SET"` emits nothing. Citation: Scope 1 "interpolated segments break the
match rather than being guessed".
HOW4 — **`writes_emitters_only` narrows by 281's own rule**: it keys on the build's emitted-kinds
census, so a PHP index that emits `WRITES` leaves the unmeasured set with no code change; languages
that still emit none keep the caveat. What stays unread (SQL assembled at runtime) is named in
TOOLS / the tool description / PLAN §19, and every PHP-string edge is `HEURISTIC`. Citation: 281.

## Requirements matrix

`SECTIONS: 8 found (Why · Goal · Scope · Constraints · Acceptance · Out of scope · References · title) | 8 decomposed | ROWS: C=3 R=3 G=1 AC=4`

| ID | Source | Interpretation | Ph2 | Status |
|----|--------|----------------|-----|--------|
| G1 | Goal | a PHP literal that is a T-SQL write/EXEC yields an edge, tier says text-read | D1 · D2 | ✅ |
| R1 | Scope 1 | WRITES / DELETES / CALLS from a literal or heredoc beginning the five statements; HEURISTIC; interpolation breaks the match | D1 · D2 | ✅ |
| R2 | Scope 2 | the link is the existing resolver (FQN pass; casefold passes for WRITES) — no second resolver | D2 (no resolver change) | ✅ |
| R3 | Scope 3 | `writes_emitters_only` narrows to what is still unmeasured | HOW4 · D4 | ✅ |
| C1 | R2.2 | statement grammar, no wrapper names | D1 | ✅ |
| C2 | R1.4 | shape only; design question answered (HOW1) | D1 | ✅ |
| C3 | R4.2 | deterministic: regex over the literal, source order | D1 | ✅ |
| AC1–AC4 | AC | proving | D3 | ✅ |

`CLARIFICATION: 4 raised | 4 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: the PHP visitor had no arm for string scalars; SQL written as a PHP literal produced
  no edge, so `find_references` on a table / `find_callers` on a proc missed every PHP site and the
  retros fell back to grep.
- Blast radius: `adapters/php/src/SqlLiteral.php` (new, the reader), `Visitor.php` (three arms +
  one emit). No core change: `CALLS`/`WRITES`/`DELETES` exist; the FQN pass links cross-language
  (no language filter); `WRITES` misses fall to the casefold passes (Table/Column kinds only), so an
  unqualified `INSERT INTO T (…)` links a unique Table and never a PHP symbol. `DELETES` is not in
  the casefold set, so an unqualified `DELETE FROM T WHERE …` stays unlinked — as it does from SQL.
- Residual, recorded: `UPDATE c SET … FROM dbo.T c` names the alias `c` (333's shape); from PHP it
  stays unlinked unless a table is literally named `c`.

`TRACK: backend — 0/N UI`

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R1.4 ✅ (the adapter recognises shape, SqlLiteral parses no SQL) · R2.2 ✅ (no method names) · R6.6 ✅ (phpstan max clean) · R7.6 ✅ (§19 line replaced, not appended)`

`BASELINE: green`

## Phase 2 — Design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | k/N |
|---|--------|------|-----|
| D1 | `SqlLiteral::read(text, closed)` → kind / target / offset, per HOW1–3 | adapters/php/src/SqlLiteral.php | 1/1 |
| D2 | Visitor: `String_` (closed unless a concat continues it), the first part of an `InterpolatedString` (never closed), `Concat` marks its left literal; emit HEURISTIC at the keyword's line (heredoc body +1) | adapters/php/src/Visitor.php | 1/1 |
| D3 | proving | tests/test_sql_in_a_php_string.py · tests/fixtures/php/sql_in_string.php | 1/1 |
| D4 | §19 line superseded · TOOLS · find_references description · bookkeeping | docs · code_atlas/tools/find_references.py | 1/1 |

| AC | risk | proof | provenance | match |
|----|------|-------|------------|-------|
| AC1–2 | integration (PHP + SQL build → resolver → tool) | pytest over a real two-adapter build | authored | ✅ |
| AC3–4 | adapter emit | parse-level pytest | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_sql_in_a_php_string.py -q`

Rejected alternatives: keying on a wrapper's method name (`querySP('…')`) — R2.2; any leading
keyword without its clause — "Update settings" becomes a writer of table `settings`; a bare EXEC
target — HOW2; a SQL parser in the PHP adapter — R1.4.

`SCOPE: M`

## Phase 3 — Execute

**Branch:** fix/335-sql-in-a-php-string-emits-edges

Ran at eea87956909b70ef58521c01d30c1bae9aae1120

```
$ .venv/bin/python -m pytest tests/test_sql_in_a_php_string.py -q
4 passed
```

Red arm on `main` (`54dafed` visitor, `SqlLiteral` absent): 4 of 4 fail — AC3/AC4 are pinned in the
same line set as the positive sites, so they fail with them. `phpstan level max`: no errors. A 23-case
probe of `SqlLiteral::read` (prose, temp tables, `EXEC('…')`, open literals) matches HOW1–3.

Design conformance: D1–D4 implemented-as-approved.

## Phase 4 — Review

REVIEWER: OFF (`--no-reviewer`) · CHALLENGER: ON.

**Round 1** on `8ed0376` (pre-rebase; same patch as `c380e76`): **NOT-CLEAN 13 met / 1 not met / 0
can't tell.** The same tree's full suite also showed two failures the challenger did not name. All are
fixed in `f82330a`:

| # | Finding | Fix |
|---|---|---|
| 1 | HIGH — the fixture sat in `tests/fixtures/php/`, which the tool-parity corpus globs; `test_tool_parity[php:check_column_defaults]` expects PHP to emit no `WRITES` | fixture moved to `tests/fixtures/php_sql_literal/repo.php` |
| 2 | MEDIUM — `EXEC @rc = dbo.P …` (return-code capture) emitted nothing | `SqlLiteral` skips an `@name =` after EXEC; arm `test_the_return_code_exec_form_is_a_call` |
| 3 | LOW-MED — `"Delete from dbo.Orders after archiving"` emitted `DELETES` | a qualified DELETE/EXEC ends only at the literal's close or `;` (whitespace alone before an open end); arm in the emit-nothing line set |
| 4 | LOW — temp tables / table variables skipped | kept: no persistent node to link |
| 5 | LOW — can a `DELETES`/`CALLS` link a PHP symbol? | traced: `DELETES` links by exact FQN only (not in `_SCHEMA_OBJECT_KINDS`); a qualified `CALLS` miss reaches the bare-name Method fallback as `dbo.P`, which no PHP method name can equal |
| suite | `test_no_core_module_names_a_language[find_references.py]` — the description named "PHP" (R1.1) | reworded language-neutral |
| suite | `test_a_standing_doc_stays_under_its_budget[PLAN.md]` — `main` sat 1 token under | §19 entry rewritten to cost what it replaced (24,149 / 24,150) |

**Round 2 — verify-only, main loop** (every fix inside a named finding and the approved file set —
review's re-dispatch trigger did not fire): each fix present as described; the affected proofs
re-run — `tests/test_sql_in_a_php_string.py`, `tests/contract/test_tool_parity.py`,
`tests/test_core_is_language_agnostic.py`, `tests/test_doc_size_budget.py` → 498 passed; regression
scan = the full suite (Phase 3). Verdict: `clean (challenger only — REVIEWER: OFF)`, the round-2
confirmation made by the implementer, not the challenger.

