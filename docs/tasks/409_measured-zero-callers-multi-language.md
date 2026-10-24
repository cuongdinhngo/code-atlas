---
id: 409
slug: measured-zero-callers-multi-language
title: "`find_callers` on a caller-less PHP method answers `relation_unmodelled_for_language` on any multi-language index — keep a measured zero"
phase: 2
milestone: Honesty
status: todo
depends_on: [221, 238, 393]
---

## Why this exists

Issue [#101](https://github.com/cuongdinhngo/code-atlas/issues/101), 2026-10-24. On the anchor (PHP,
T-SQL, JS/TS) every empty `find_callers` on a PHP method answers `relation_unmodelled_for_language`,
never `no_matches` — five PRs in 19–23 Oct needed a Grep pass to claim "unused".

**Confirmed in code (2026-10-24):** `find_callers` upgrades `no_matches` whenever
`coverage.cross_language_relation_unmodelled` returns a census, i.e. whenever another language is
covered and no `*->L` pair exists. No language links into PHP on the anchor, so the upgrade fires
even when PHP→PHP resolution measured the subject completely (no `unresolved_bare_calls`, no
`unresolved_receivers`, no unlinked same-name sites). The flag meant for an unseen crossing hides a
measured zero.

## Scope

1. Upgrade to `relation_unmodelled_for_language` only when another covered language holds
   **unlinked** edges that could name the subject (same short name), or its stamped capabilities say
   it can call into L.
2. Otherwise answer `no_matches`, carrying the crossing as a field
   (`cross_language_unmeasured: [<lang>, …]`), not as the reason. `authoritative` stays honest (R5.6).
3. Check `find_references` and `impact` for the same census-only upgrade and apply the same rule.

Out of scope: calls from file-scope code in `include`d scripts (anchor #3679).

## Acceptance criteria

- AC1: A PHP method with no callers in a PHP+SQL fixture answers `no_matches` with
  `cross_language_unmeasured` naming SQL.
- AC2: The same method with an unlinked same-name site in the other language still answers
  `relation_unmodelled_for_language`.
- AC3: The 221/238 tests keep their verdicts or are re-decided in this ticket with the reason stated.
- AC4: P8: `cross_repo_validate.py` re-run; any moved reason counts re-floored.
