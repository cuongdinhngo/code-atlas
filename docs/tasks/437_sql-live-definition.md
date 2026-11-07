---
id: 437
slug: sql-live-definition
title: "SQL: which definition of a multiply-defined routine is live, and a hash that ignores formatting"
phase: 2
milestone: "0.11 Verify & Compute"
status: todo
depends_on: [384]
---

## Why this exists

Roadmap R2 (0.11), and the prerequisite for 438's SQL rows and 440/441's `multi_defined` and
absence templates. On the maintainer's anchor (survey 2026-11-07, counts only), **161 of 389 SQL
routines are defined more than once** — migrations re-issue `CREATE OR ALTER`, a snapshot holds a
copy — and nothing says which definition is the one the database runs. Today a reference to one of
them can only resolve `ambiguous`, and a "what does X do" answer may read a superseded body.

`adapters/sql/src/bodyHash.js` (384) drops comments and collapses whitespace per line, so a
keyword-case change, `[bracket]` quoting, `CREATE OR ALTER` vs `CREATE` or a reflowed statement
still moves the hash. Identical routines then look changed, and 438's `body_hash` successor match
misses them.

## Scope

1. **Definition order.** The SQL adapter emits a generic `definition_ordinal` per definition. The
   ordering comes from a per-repo rule, e.g. `sql.definition_order = ["migration:V<n>", "snapshot",
   "other"]` — the adapter parses the version from the path by the rule's pattern; the core only sorts
   (R1.1). The highest ordinal is `live`; the others carry `superseded_by`.
2. **The rule is a non-command `.code-atlas.toml` key** (430): a list of path patterns, never a
   command, validated by `config.py` like every other knob.
3. **Hash normalization** in `bodyHash.js` before digesting: keyword case, `[bracket]` / `"quoted"`
   identifiers that need no quoting, `CREATE OR ALTER` → `CREATE`, and whitespace across line breaks
   (reflow). A literal's text stays as written.
4. **Contract**: a new field or vocabulary is R3 — bump `contract_version`, conformance tests, and
   say in the release note that every stored SQL `body_hash` moves once (a 384 snapshot taken before
   reports SQL symbols changed after the upgrade).

**Decision already taken** (roadmap §4.6, maintainer may override at the gate): ordering by migration
version is a per-repo config rule, not a built-in convention (R2).

## Acceptance

1. Fixtures: a routine defined in three migrations and a snapshot has exactly one `live` definition,
   the highest-versioned migration; the others name it in `superseded_by`.
2. With no rule configured, nothing is `live` and multi-definition stays reported as ambiguous —
   an unknown is never `ok` (R5.6).
3. Formatting-only variants (case, brackets, `OR ALTER`, reflow) keep their hash; a changed predicate
   or column list moves it.
4. A toml value that is not a list of strings fails loud, naming the key.
5. Anchor (privacy rules in 442): each of the 161 multiply-defined routines has exactly one `live`
   definition — counts only, reported to `~/code-atlas-review/`.
