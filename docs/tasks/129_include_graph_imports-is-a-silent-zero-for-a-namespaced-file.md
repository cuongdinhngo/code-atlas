---
id: 129
slug: include_graph_imports-is-a-silent-zero-for-a-namespaced-file
title: include_graph(direction=imports) returns an empty list with zero unresolved for any namespaced file
phase: 2
milestone: Quality
status: done
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

---

## Design decision — the anchor is the **file**

Recorded because the ticket asked for it in writing.

`INCLUDES` is anchored on the **including file's path**, not on the enclosing namespace. Four reasons,
in the order they settle it:

1. **The other end was already the file.** `resolver._relative_to` joins `target_raw` onto
   `PurePosixPath(edge.file_path).parent` — the include's target has always been resolved relative to
   the *file*, never to `source_qname`. The source side was the inconsistent one, so this is a fix to
   an inconsistency rather than a choice between two coherent models.
2. **It is what the language does.** `require_once 'x.php'` splices a file into a file. The namespace
   never took part; it appeared only because the adapter's scope stack happens to sit under
   `namespace X;`, so `container()` returned it.
3. **Both directions already assumed it.** The payload field is `path`, and `imports` means "what
   this file includes". The namespace anchor made one direction empty and mislabelled the other.
4. **`unresolved_includes` becomes honest for free** — no separate mechanism needed for AC2.

**Root cause, one line:** `Visitor::enterInclude` passed `$this->container()` where it needed
`$this->path`.

## Contract version — bumped to **6**, and why, given lesson 075

075 warns that "bump `contract_version`" can name the wrong contract and force a needless reindex for
every user, so the trigger was checked rather than assumed:

- **R3.1's literal trigger does not fire.** `EDGE_KINDS`, the field lists and the qname convention are
  all unchanged; `tests/contract/` needed no new case. By 075's test — *is the changed thing defined
  in `contract.py` and covered by `tests/contract/`?* — this is emission semantics, not vocabulary.
- **The bump is still correct, for the mechanism rather than the letter.** `indexer.py`'s
  `incremental_update` compares the stored `contract_version` and falls back to `full_build` when it
  differs, with the comment *"Vocabulary changed — incremental would mix eras"* (task 030). That is
  exactly this change's hazard: an index built before it and updated incrementally after would hold
  namespace-anchored rows for untouched files and file-anchored rows for changed ones, and
  `include_graph` would answer from a mixture. Without the bump the fix silently does not take effect
  on any existing index.

So the bump is deliberate and its justification is the rebuild gate, not R3.1. Surfaced here and in
the PR rather than complied with or ignored silently.

**Version pins found and made derived (R6.7).** Bumping turned up **7** hand-kept `5`s. Two are
deliberate pins and stay literal — `tests/contract/test_contract_schema.py` and
`test_php_adapter_grammar.py` exist to notice a bump. Five were re-typings of a value they could
import, and now do: the five current-version handshakes in `tests/fixtures/adapter/fake_adapter.py`
(`bad-version: 99` and `stale-version: 1` stay literal, being deliberate mismatches) and the two
handshake assertions in `test_php_adapter_server.py`, which assert *the adapter announces what the
core expects* — a comparison that should never have had a constant in it.

## Outcome

**Done.** All four AC met by the one-line anchor change; no core module changed.

- **AC1** `include_graph("Shop/Bootstrap.php", direction="imports")` → `[{"path": "helpers.php", …}]`.
- **AC2** `unresolved_includes: 1` for the same call — the `require_once $dynamicPath` line — where it
  read `0` before.
- **AC3** `imported_by("helpers.php")` → `path: "Shop/Bootstrap.php"`, a path; asserted no result's
  `path` starts with `\`.
- **AC4** `tests/fixtures/php/include_graph/Shop/Bootstrap.php` (namespaced, one resolvable +
  one dynamic include) and `helpers.php`, asserted in both directions **and** at the store level, so
  the anchor itself is pinned and not only what the tool makes of it.

**Red run recorded (R6.5).** With `Visitor.php` reverted and everything else in place:
`FAILED test_include_graph_answers_for_a_namespaced_file` — *"assert [2 INCLUDES rows on `\Shop`] ==
[]"*. The pre-fix payload, captured directly: `results: []`, `unresolved_includes: 0`,
`imported_by: []`.

**A second defect the same line fixes, measured both ways.** `IMPACT_KIND_WEIGHTS` gives `INCLUDES`
0.8, so the impact walk crossed these edges too. `impact(paths=["helpers.php"])` on the fixture:

| | third result |
|---|---|
| pre-fix | `\Shop` @ 0.56 — a namespace, which nothing can act on |
| post-fix | `Shop/Bootstrap.php` @ 0.56 — the file that actually breaks |

Same score, same walk; the blast radius was naming a container instead of a file. Not in the ticket's
AC and not scope-crept into one — recorded here because it is evidence the anchor was wrong, not only
awkward.

PR [#154](https://github.com/cuongdinhngo/code-atlas/pull/154).

**Delta-green:** `pytest` **1770 passed, 0 failed** on a POSIX host with `php` (1767 before this
branch: +1 new test, +2 from the bump reaching two parametrised adapter cases). `ruff` clean,
`mypy` clean over 68 source files. Full gate re-run at the final commit.
