---
id: 361
slug: js-route-strings-link-to-nothing
title: 'A route string in JavaScript links to nothing, so a PHP action called only from the front end reads as uncalled'
phase: 2
milestone: Coverage
status: todo
depends_on: [352, 221]
---

## Why this exists

This comes from a field retro on an anchor PHP + SQL Server project (2026-09-30 → 10-07, 49
scored PRs). It is the gap reported most often: in 8 PRs the agent fell back to Grep, because the
real caller of a PHP action is a JS string.

- F1 (1 PR): `find_callers` on `deleteItemAction` → `relation_unmodelled_for_language`. The caller
  is `$.post('…action=deleteItem')`.
- F2 (2 PRs): `main.php?module=…&control=…&action=…` URLs in JS.
- F3 (2 PRs): a `{module, action}` JSON envelope, and AngularJS `$http.post` calls to one service
  endpoint script.
- F4 (1 PR): jQuery `ajax` URL literals in views.
- F5 (2 PRs): `onclick` attributes, and DOM ids in PHP `echo` strings, that name `public/js`
  functions.

The answer is honest, since 221 marks the zero as unmeasured. The gap is that the edge the agent
needs is never built.

## Scope

1. 352 shipped as the existing `keyed_calls` rule (222), which links only when the argument *is*
   the whole key (TOOLS.md *Configuration reference*). A route string is not: the key sits inside
   a URL. Extend `keyed_calls` with an optional key pattern whose capture fills `{key}` in
   `target_template`, so the rule file declares the project's route grammar (`action=X` →
   `XAction`, a `{module, action}` pair → a service method). Edges stay `HEURISTIC`,
   `rule: true`; nothing is hard-coded. No new rule kind (R1.2).
2. An inline `on*="fn(…)"` attribute string in a PHP view links to the JS function it names. When
   no definition matches, it stays unlinked and is counted. The anchor project excludes
   `public/js` (`path_excluded`), so prove this on a fixture, not on the anchor.
3. With no rule, the graph is unchanged.

## Acceptance criteria

- **AC1:** On a fixture with `$.post('main.php?action=deleteItem')`, `find_callers` on
  `…::deleteItemAction` returns the JS caller at `HEURISTIC`, with `rule: true`.
- **AC2:** A `{module, action}` object literal passed to a declared callee resolves the same way.
- **AC3:** A route string that names no action stays unlinked and is counted in
  `rule_keys_unresolved`. No edge is invented.
- **AC4:** An index with no rule of this kind is byte-identical.
