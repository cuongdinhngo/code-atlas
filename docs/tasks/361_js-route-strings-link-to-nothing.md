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

This comes from field feedback on the anchor project (evaran-care/rac-anz, 2026-09-30 → 10-07).
It is the gap reported most often: in 8 of the 49 scored PRs the agent fell back to Grep, because
the real caller of a PHP action is a JS string.

- #3100: `find_callers` on `deleteAssessmentAction` → `relation_unmodelled_for_language`. The
  caller is `$.post('…action=deleteAssessment')`.
- #3087, #2779: `main.php?module=…&control=…&action=…` URLs in JS.
- #3104, #3105: SMCP `{module, action}` JSON and AngularJS `$http.post` calls to
  `ServicesInternal.php`.
- #2826: `$j.ajax` URL literals in views.
- #2839, #2831: `onclick` attributes, and DOM ids in PHP `echo` strings, that name `public/js`
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
   `public/js` (`path_excluded`), so prove this on a fixture, not on rac-anz.
3. With no rule, the graph is unchanged.

## Acceptance criteria

- **AC1:** On a fixture with `$.post('main.php?action=deleteAssessment')`, `find_callers` on
  `…::deleteAssessmentAction` returns the JS caller at `HEURISTIC`, with `rule: true`.
- **AC2:** A `{module, action}` object literal passed to a declared callee resolves the same way.
- **AC3:** A route string that names no action stays unlinked and is counted in
  `rule_keys_unresolved`. No edge is invented.
- **AC4:** An index with no rule of this kind is byte-identical.
