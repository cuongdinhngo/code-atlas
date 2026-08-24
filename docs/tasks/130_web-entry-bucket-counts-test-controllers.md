---
id: 130
slug: web-entry-bucket-counts-test-controllers
title: The web_entry bucket counts test controllers as web surface — half the count on a canonical repo
phase: 3
milestone: Quality
status: done
depends_on: [113, 119, 121]
---

## Why this exists

Measured on the pinned `symfony/demo` while running **121**'s onboarding class.
`architecture_overview`'s reachability split reports:

```
web_entry  count 8  signals {declared: 0, structure: 0, vocabulary: 8}
  src/Controller/Admin/BlogController.php   src/Controller/BlogController.php
  src/Controller/SecurityController.php     src/Controller/UserController.php
  tests/Controller/Admin/BlogControllerTest.php  tests/Controller/BlogControllerTest.php
  tests/Controller/DefaultControllerTest.php     tests/Controller/UserControllerTest.php
```

Four of the eight are tests. The bucket's own note says *"the web surface a request can actually arrive
at"*, and a request cannot arrive at a PHPUnit test. The `test` bucket is populated (5) at the same
time, so both signals fired and the web-entry one won.

This is 119's family, not a new one: the number is honest about its **signal** (`vocabulary: 8`) and
dishonest about its **population**. 113 chose the bucket order; nothing has re-read that order against
a repo where the two signals collide on the same file.

## Scope

- Decide the precedence between the test-path signal and the request-handling vocabulary signal, and
  say why in the code that owns it (R5.4 — the caveat belongs to the computation).
- Whatever wins, a file counted in `web_entry` must not also match the test signal silently: either it
  moves to `test`, or the bucket states the overlap.
- Keep the arithmetic true: buckets must still sum to `total` (127's guard).
- A fixture with a test path that names a request-handling responsibility. Red first (R6.5).

## Acceptance criteria

1. **AC1.** A file under a test path is not counted as web surface, or the payload names the overlap.
2. **AC2.** Bucket counts still sum to the reported total, and `signals` still sums to each count.
3. **AC3.** A committed fixture reproduces the collision, and asserts the chosen precedence.
4. **AC4.** `docs/benchmarks/121_onboarding-question-class.md`'s finding #2 is struck when this closes.

---

<!-- mango:working-doc -->

## Session status

- **Phase:** finalise (execute complete; review/challenger waived)
- **Branch:** `fix/130-web-entry-bucket-counts-test-controllers`
- **SCOPE:** M
- **TIER:** full
- **CHALLENGER:** OFF (--no-challenger; review waived by run args)
- **work_doc_mode:** embed

## Requirements matrix

| ID | Requirement | Validation | Ph3 | Ph4 |
|---|---|---|---|---|
| C1 | Precedence decided in reachability owner; test-path before request-handling vocabulary | `_names_test_responsibility` + comment in `_bucket_of` | ✅ | waived |
| R1 | No silent overlap: test-path files not in `web_entry` | `test_ac3_test_path_outranks_request_handling_vocabulary` | ✅ | waived |
| R2 | Bucket arithmetic preserved | same test asserts sum | ✅ | waived |
| R3 | Committed fixture + red-first proving test | `tests/fixtures/php/reachability_collision/` | ✅ | waived |
| AC1 | Test path not web surface | placement[collision]==TEST | ✅ | waived |
| AC2 | Counts sum to total; signals sum to count | asserted in AC3 test | ✅ | waived |
| AC3 | Fixture reproduces collision | committed fixture + test | ✅ | waived |
| AC4 | Benchmark finding #2 struck | `121_onboarding-question-class.md` updated | ✅ | waived |

## Design (Gate 2 — approved on standing instruction)

**Approach:** In `_bucket_of`, after declared globs, scan every directory segment with
`responsibility_of_segment` for `LAYER_TESTS` before applying deepest-wins `responsibility_layer`.
Declared `entry_points` still outrank everything (113/119 unchanged).

**Rejected:** Changing `responsibility_layer` deepest-wins globally — would alter layer assignment,
not just reachability split.

**Change list:** `code_atlas/onboarding/reachability.py`; `tests/test_reachability_split.py`;
`tests/fixtures/php/reachability_collision/**`; docs (BACKLOG, benchmark, PLAN, ROADMAP, TOKEN_LEDGER).

**Proving test:** `test_ac3_test_path_outranks_request_handling_vocabulary`

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| execute | — | — | main-loop only |
| review | waived | — | — |
| challenger | waived | — | — |

## Decision log

- **D1:** Test-path signal wins over request-handling vocabulary in reachability only; operator
  declarations unchanged (ASSUMED ratified via standing approval).

## Ph3/4 proven by

- Docker: `scripts/docker-test.sh pytest -q tests/test_reachability_split.py` — 14 passed
- Full gate pending at commit time
