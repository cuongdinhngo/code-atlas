---
id: 395
slug: js-in-php-views
title: 'JavaScript inside a PHP view and AngularJS controller members are not symbols, so a template-to-controller question is Grep only'
phase: 2
milestone: Coverage
status: todo
depends_on: [361]
---

## Why this exists

This comes from the anchor project's second field retro (2026-10-10 → 10-17). 361 links a JS
route string to its PHP action. The front-end code that the PHP views carry or call is still
outside the graph. 4 PRs:

- F1 (1 PR): handlers defined in an inline `<script>` block of a `.php` view are not indexed, so
  the handlers were found with Grep. (361 left inline `on*=` attributes out for the same reason.)
- F2 (1 PR, scored 4/10): the whole question was "which `ctrl.X(` calls in the region's template
  name no member of its AngularJS controller". Members declared as `self.X = function` /
  `$scope.X = …` inside the controller function are not symbols.
- F3 (1 PR): `ng-model="filters.x"` bindings in PHP templates are the consumers of a model key.
  Finding them took `git grep`.
- F4 (1 PR): a PHP `loadScripts(['js/x.js'])` list names the asset, but nothing links the
  page to the file, so "who loads this script" was Grep.

## Scope

1. Measure first: on the anchor index, count the PHP files with inline `<script>` blocks, and the
   `this.X = function` / `self.X = function` / `$scope.X =` member assignments. Order the items
   below by those counts.
2. The TS adapter emits members assigned on `this`, or on a local bound to `this`
   (`var self = this`), inside a plain function as Methods of that function — the ES5 constructor
   pattern, language spec only. Registration (`.controller(…)`) and `$scope` are framework
   semantics and stay out of the adapter (R2.2); `$scope` members get a count, not a rule.
3. Embedded `<script>` regions of a PHP file are handed to the JS reader with their offsets, so
   their functions are symbols of that file.
4. Template references (`ctrl.X(`, `ng-model`, an asset path in a declared include-list call) are
   declarative, through the existing `keyed_calls` rule file. No new rule kind (R1.2).

## Acceptance criteria

- **AC1:** `function EditCtrl(){ var self = this; self.save = function(){}; }`: `search_symbol save`
  finds it as a Method of `EditCtrl`.
- **AC2:** A `.php` view with `<script>function onPick(){}</script>`: `file_outline` lists `onPick`
  at its true line.
- **AC3:** With a rule, `ctrl.save(` in a template is a `HEURISTIC` caller of that member. A
  `ctrl.missing(` stays unlinked and is counted.
- **AC4:** An index with no such files is byte-identical.

- **AC-field:** the F-cases' query shapes, replayed on the anchor index after the build, answer
  without a Grep fallback; record the before/after counts in the working doc.
