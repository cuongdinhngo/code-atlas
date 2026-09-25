---
id: 336
slug: a-static-property-read-answers-a-confident-zero
title: "find_references on a PHP static property answers a bare no_matches — the adapter emits no edge for Class::$prop, and the honesty check is per language, so the zero passes as measured"
phase: 1.5b
milestone: Agent-trust
status: in-progress
depends_on: [186, 232]
---

## Why this exists (field retro, 2026-09-25)

`find_references` on a config class's static property returned `no_matches` with no caveat. Grep
found the declaration and a real read. The retro called it *"the one place this session where a
zero looked authoritative and wasn't measured"*.

Probed on `main` (`927aeb9`):

```php
class Cfg { public static $flag = false; }
class Db { public function init() { if (Cfg::$flag) { return 2; } } }
class Use1 { public function f(Cfg $c) { return 1; } }
```

`find_references \App\Cfg::$flag` → `reason: no_matches`, no `authoritative` field. Two causes:

- The PHP visitor has no arm for `Expr\StaticPropertyFetch` (`Visitor.php:274-290` handles
  `StaticCall` and `ClassConstFetch` only), so the read emits nothing.
- `relation_unmodelled_for_language` (`coverage.py:41`) asks whether the *language* emits any of
  the kinds. `Use1`'s type hint emits a `REFERENCES` (232), so PHP "models" it and the zero stands.
  Without `Use1` the same subject honestly answers `relation_unmodelled_for_language`.

## Goal

A static property read or write is a reference to the property — or, until it is, the answer does
not claim a zero.

## Scope / Deliverables

1. **The PHP adapter emits `REFERENCES`** from a `StaticPropertyFetch` whose class resolves
   (`self`/`static`/`parent` through the enclosing class, as `ClassConstFetch` already does).
2. **Instance property reads (`$this->x`) are stated** — either in scope with the same shape, or
   recorded here as out of scope with the reason. Decided before code.

## Constraints

- **R3** — `REFERENCES` already exists; if a new kind is wanted instead, that is a contract bump.
- **061** — every other subject's answer is byte-identical.

## Acceptance criteria

- **AC1** The probe above: `find_references \App\Cfg::$flag` lists `\App\Db::init` at line 8; red
  on today's code.
- **AC2** `self::$flag` inside `Cfg` resolves to the same qname.
- **AC3** `$cls::$flag` (dynamic class) emits nothing, or emits `DYNAMIC` — never a guessed class.

## References
`adapters/php/src/Visitor.php:274-290`; `code_atlas/tools/coverage.py:41-54`;
`code_atlas/tools/find_references.py:564-600`; tickets 186, 232.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 336 — a static property read is a reference to the property (working doc)

- **Ticket:** 336 · local · **SCOPE:** S · **TIER:** full · **TRACK:** backend
- **REVIEWER:** OFF (`--no-reviewer`) · **CHALLENGER:** ON
- **Current phase:** execute
- **Session status:** in-progress — autorun
- **Reviewed at:** —

## Phase 0 — Refine

`PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW1 (Scope 2, decided before code): **instance property reads (`$this->x`, `$obj->x`) are out of
scope.** `$obj->x` needs the receiver's type (the MemberTypes/TypeTable machinery, per call site),
and `$this->x` on an inherited property has the same problem as `self::$x` below; one shape done
right beats three done by guess. Recorded as a BACKLOG follow-up so the residual zero stays visible.
Citation: Scope 2 ("or recorded here as out of scope with the reason").
HOW2: tiers follow `enterStaticCall` — a named class or `self`/`parent` is the default tier;
`static::` binds late, so `HEURISTIC`. Citation: C2/030's rule for `static::` calls; R3 (no new kind).

## Requirements matrix

`SECTIONS: 7 found (Why · Goal · Scope · Constraints · Acceptance · References · title) | 7 decomposed | ROWS: C=2 R=2 G=1 AC=3`

| ID | Source | Interpretation | Ph2 | Status |
|----|--------|----------------|-----|--------|
| G1 | Goal | a static property fetch is a reference to the property | D1 | ✅ |
| R1 | Scope 1 | PHP emits `REFERENCES` for a resolvable `StaticPropertyFetch`; self/static/parent via the enclosing class | D1 | ✅ |
| R2 | Scope 2 | instance property reads stated | HOW1 · D3 (follow-up line) | ✅ |
| C1 | R3 | existing `REFERENCES`, no contract bump | D1 | ✅ |
| C2 | 061 | every other subject byte-identical — the arm adds edges only onto `Class::$prop` targets | D1 | ✅ |
| AC1–AC3 | AC | proving | D2 | ✅ |

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: `enterReference` (`Visitor.php`) has arms for `StaticCall` and `ClassConstFetch` only;
  a `StaticPropertyFetch` reached no arm and emitted nothing, and PHP's other `REFERENCES` (232) made
  the per-language honesty check (`coverage.py:41`) accept the zero.
- Blast radius: `adapters/php/src/Visitor.php` only. The resolver already links `REFERENCES` by FQN
  (`contract.FQN_EDGE_KINDS`); an inherited property (`self::$x` declared in a parent) keeps its
  subclass qname and stays unlinked — the resolver's inherited-member path is CALLS-only (137).

`TRACK: backend — 0/N UI`

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R2.1 ✅ (PHP grammar only, no repo names) · R3 ✅ (no new kind) · R6.6 ✅ (phpstan level max clean)`

`BASELINE: green`

## Phase 2 — Design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | k/N |
|---|--------|------|-----|
| D1 | `enterStaticPropertyFetch`: Name class + VarLikeIdentifier name → `REFERENCES` onto `<class>::$<name>` via `mentionTarget`; `static::` HEURISTIC; dynamic class/name → nothing | adapters/php/src/Visitor.php | 1/1 |
| D2 | proving | tests/test_static_property_fetch_references.py · tests/fixtures/php/static_property_fetch.php | 1/1 |
| D3 | TOOLS line · BACKLOG follow-up · bookkeeping | docs | 1/1 |

| AC | risk | proof | provenance | match |
|----|------|-------|------------|-------|
| AC1 | integration (PHP build → resolver → find_references) | pytest over a real build | authored | ✅ |
| AC2–3 | adapter emit | parse-level pytest | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_static_property_fetch_references.py -q`

Rejected alternatives: a new `READS` kind (a contract bump for a relation `REFERENCES` already
names — R3); resolving `self::$x` through the parent chain in the adapter (a single file cannot see
another file's declarations — the resolver's job, 137).

`SCOPE: S`

## Phase 3 — Execute

**Branch:** fix/336-static-property-read-references

Ran at bf15c68481232aea37c63b75e49177f439580a5a

```
$ .venv/bin/python -m pytest tests/test_static_property_fetch_references.py -q
3 passed
```

Red arm on `main` (`54dafed`): AC1 and AC2 fail, AC3 passes (nothing emitted before either).
`phpstan level max`: no errors. Probe: `self::` → `\App\Cfg::$flag`, `parent::` → the parent's
qname, `static::` → HEURISTIC, `$cls::$flag` / `Cfg::$$n` → nothing.

Design conformance: D1–D3 implemented-as-approved.

