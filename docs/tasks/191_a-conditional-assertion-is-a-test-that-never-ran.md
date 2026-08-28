---
id: 191
slug: a-conditional-assertion-is-a-test-that-never-ran
title: '`test_a_qname_subject_still_ranks_as_it_did` asserts under an `if` on a payload that answers `index_stale`, so it has never run — and nothing in the suite can tell that apart from a pass'
phase: 1.5b
milestone: Coverage
status: todo
depends_on: [189, 181]
---

## Why this exists

Found by **189** by accident: my own first end-to-end sibling test failed with
`KeyError: 'sibling_definitions_ranked_by'`, and the payload turned out to say
`reason: "index_stale"`. Tracing why led to 181's own test:

```python
def test_a_qname_subject_still_ranks_as_it_did(tmp_path, store):
    plant_case_a(store)
    payload = find_callers.create(config_for(tmp_path))("\\Alpha\\ModelMember")
    if SIBLING_DEFINITIONS in payload:          # <- never true
        assert payload[SIBLING_RANKED] is True
        assert payload[SIBLING_RANKED_BY] == RANK_SHARED_SUBTREE
```

`tests/test_impact.seed_file` plants rows **without matching on-disk bytes**, so `FreshnessGuard`
answers `index_stale` before the sibling disclosure is ever built. The `if` then swallows it, and
the test reports **green while asserting nothing**. It is 181's AC5/061 guard for case A, so the
thing 181 claimed was pinned is not.

`tests/test_nav_tools.seed_file` writes the bytes and is the helper that works here — 171's ranking
tests use it, which is why they do exercise the payload.

## Scope

1. Give the test a fresh index (`tests/test_nav_tools.seed_file`) so the payload it builds is
   `reason: "ok"`, and drop the `if` — the assertion must be unconditional or the test is not one.
2. Confirm what it then asserts is still true: after 189, case A's uniform file-name band reports
   `shared_subtree_with_subject`, so the original expectation stands unchanged.
3. **Sweep for the same shape.** `if <key> in payload:` guarding the only assertions in a test is a
   mechanically findable pattern; count the occurrences before deciding whether a guard is wanted.

### Explicitly not in scope

- Changing `tests/test_impact.seed_file` — other tests depend on its cheapness, and `impact` does
  not gate on freshness the way the nav tools do.
- Any production change. Nothing here is a defect in `code_atlas/`.

## Constraints

- **R6.5** — a test that cannot fail is not a guard. The fix must be shown failing against the
  shape it forbids.
- **R6.3** — do not swap one begged question for another: the new fixture must make the payload
  answer, not make the assertion trivially true.

## Acceptance criteria

1. The test asserts unconditionally and its payload answers `reason: "ok"` — pinned.
2. It is shown red against a deliberately wrong basis value, so it is observably a guard.
3. The sweep's count is recorded, and every other conditional-assertion site is either fixed or
   named with a reason it is legitimately conditional.

## References
Found by [189](189_a-twin-is-a-container-fact-not-a-path-fact.md) while replacing the basis 181
declined to ship. `tests/test_sibling_disclosure_is_a_ranking_or_says_not.py` (the test);
`tests/test_impact.py` / `tests/test_nav_tools.py` (the two `seed_file` helpers). Related:
[181](181_sibling-definitions-fallback-is-a-dump-not-a-ranking.md).
