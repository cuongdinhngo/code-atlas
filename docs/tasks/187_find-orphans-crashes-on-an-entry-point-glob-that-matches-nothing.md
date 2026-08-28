---
id: 187
slug: find-orphans-crashes-on-an-entry-point-glob-that-matches-nothing
title: '`find_orphans` raises `OperationalError: no such table: temp.reach_seen` when `CA_ENTRY_POINTS` matches no indexed file — a typo in a glob crashes the tool instead of answering'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [185, 031, 124]
---

## Why this exists

Found by **185**'s cross-language tool-parity matrix on its first real run, on **both** languages —
so it is not a language fault, it is the first time any test asked `find_orphans` a question over a
real indexed graph with entry points configured.

```
CA_ENTRY_POINTS="\App\Calls\Service::run"        # a QNAME, but entry points are PATH GLOBS
find_orphans() -> OperationalError: no such table: temp.reach_seen
```

Reproduced in a fresh process, with no prior tool call, on a PHP graph and a TS graph.

## The defect, at source

`entry_seeds()` (`reach_shared.py:19`) resolves `config.entry_points` as **path globs**. A glob that
matches no indexed file returns `[]` — a legitimate outcome (a typo, a renamed directory, a
not-yet-indexed tree).

`store.reachable_from()` handles that correctly and cheaply:

```python
# store.py:1662-1663
if not ordered_seeds:
    return ReachabilityResult([], [], 0, False, False)      # returns BEFORE creating the temps
```

`store.find_orphans()` then calls it with `retain_temps=True` and reads the temp tables that early
return never created:

```python
# store.py:1851-1861
reach = self.reachable_from(seeds, depth=depth, max_nodes=max_nodes, retain_temps=True)
...
conn.execute("INSERT OR IGNORE INTO temp.reach_excluded (qname) SELECT qname FROM temp.reach_seen")
```

So `reachable_from` returns an honest empty answer and `find_orphans` raises. **Two consumers of one
walk disagree about whether the empty case is reachable** — R1.8's shape, one layer down.

## Why it matters more than the crash

`find_orphans`' own docstring promises the opposite behaviour: *"unset entry points yield
`status=no_roots_configured`"* — and unset really does (`find_orphans.py` returns `no_roots` before
opening the store). **Configured-but-matching-nothing is the case nobody wrote**, and it is the more
likely misconfiguration of the two: an unset variable is obvious, a stale glob is not. A raise also
crosses the tool boundary as a stack trace rather than an answer with a next action, which is what
050 exists to prevent.

## Scope

1. An entry-point set that resolves to **zero** seeds returns an answer, not a raise. Design records
   which answer: `no_roots_configured` is taken, so the honest report is a distinct state — the roots
   were configured and matched nothing, which is a fact about the *config*, not about orphans.
2. **One walk, one empty-case contract (R1.8).** Fix it where the disagreement is — either
   `reachable_from` creates its temps before the early return, or `find_orphans` handles the empty
   result without reading them. Design says which and why, and the other consumer of
   `retain_temps=True`, if any, is enumerated by grep.
3. The answer names what was configured and that it matched nothing, so the caller can fix the glob
   without reading source (082).

### Explicitly not in scope

- Changing what an entry point *is* (a path glob, PLAN §11). Accepting qnames is a separate ticket
  and arguably a mistake — a qname-shaped entry point is what produced this report.
- `reachable_from`'s behaviour, which is already correct.
- The orphan definition, the walk budget, or 124's reliability flags.

## Constraints

- **050** — a schema/config problem arrives as an answer with a next action, never a stack trace.
- **R5.6** — the answer must not claim "no orphans" for a walk that never ran; those are different.
- **061** — a resolving entry-point set is byte-identical to today.
- **R6.5** — the guard ships only once observed failing: the red run is the `OperationalError` above.

## Acceptance criteria

1. `CA_ENTRY_POINTS` matching no indexed file returns a payload, not a raise — pinned by a test that
   fails on today's code with `OperationalError`.
2. The payload distinguishes *"no roots configured"* from *"roots configured, matched nothing"*, and
   neither reads as *"no orphans"* — pinned.
3. The empty-case contract lives in one place; every `retain_temps=True` consumer is enumerated and
   covered — pinned.
4. A resolving entry-point set is byte-identical (061), pinned.
5. `reachable_from` untouched, pinned by its existing tests.

## References
Found by [185](185_no-tool-is-ever-asked-a-question-over-a-second-languages-graph.md)'s parity matrix.
`code_atlas/store.py:1662-1663` (the early return), `:1851-1861` (the temp read);
`code_atlas/tools/reach_shared.py:19` (`entry_seeds`); `code_atlas/tools/find_orphans.py`
(`no_roots`). Related: [031](031_reachability-and-orphans.md) (the walk),
[124](124_find-orphans-reliability.md), [050](050_schema-mismatch-is-an-answer.md).
