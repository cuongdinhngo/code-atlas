---
id: 129
slug: include_graph_imports-is-a-silent-zero-for-a-namespaced-file
title: include_graph(direction=imports) returns an empty list with zero unresolved for any namespaced file
phase: 2
milestone: Quality
status: todo
depends_on: [121]
---

## Why this exists

Found while establishing ground truth for **121**'s onboarding question-class, not by a failing test.

The INCLUDES edge is stored with the **namespace** as its source, not the file. On the fixture
`tests/fixtures/php/onboarding`, every row reads like this:

| source_qname | target_raw | target_qname | file_path |
|---|---|---|---|
| `\Shop\Controllers` | `../services/InvoiceService.php` | `services/InvoiceService.php` | `controllers/InvoiceController.php` |

Two consequences:

1. **`direction: imports` is a silent zero.** Asking what `controllers/InvoiceController.php` includes
   returns `results: []` **and `unresolved_includes: 0`** — the payload states that the file includes
   nothing and that nothing failed to resolve, while two `require_once` lines resolved fine. In a PSR-4
   repo every file declares a namespace, so this is every file.
2. **`imported_by` reports a namespace in a field named `path`.** The answer is right but mislabelled:
   `{"path": "\\Shop\\Legacy", "file": "legacy/RetiredExporter.php", …}`.

The existing fixture `tests/fixtures/php/include_graph/app.php` declares **no namespace**, which is
exactly why the conformance suite and the tokens-to-answer harness both stayed green. That is the
coverage gap, not just the defect.

A silent zero is the failure this project treats as worst: R5.3's "a missing index must never read as a
zero-token answer", one layer down. `unresolved_includes: 0` is an affirmative claim that nothing was
dropped.

## Scope

- Decide the anchor deliberately and write down which it is: the **file** node (so `imports` works and
  `path` means a path), or the namespace (so the field is renamed and `imports` resolves through it).
  The first is what both directions already imply.
- Whatever the choice, `unresolved_includes` must stop reading `0` when includes exist that this
  direction cannot answer.
- A fixture with a **namespaced** file that includes another file, in `tests/fixtures/php/include_graph`
  or beside it. Prove the guard red first (R6.5).
- If the edge's source changes, check whether the contract vocabulary is affected (R3 — a
  `contract_version` bump plus conformance updates in the same change if it is).

## Acceptance criteria

1. **AC1.** `include_graph(path=<namespaced file>, direction="imports")` returns the files it includes.
2. **AC2.** No payload reports `unresolved_includes: 0` while an include it could not answer exists.
3. **AC3.** `imported_by`'s `path` field carries a path, or is renamed to what it carries.
4. **AC4.** A namespaced include is covered by a committed fixture and asserted in both directions.
