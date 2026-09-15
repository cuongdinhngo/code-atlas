---
id: 282
slug: a-mirror-hit-names-a-counterpart-that-is-not-in-the-index
title: 'A mirror-ordered search hit names its `mirror_counterpart` by prefix-substituting the pair, so a file whose sibling was deleted or never indexed still gets a confident counterpart path that does not exist — the exact divergence `no_counterpart` was built to mark — while `attach_mirror_search_fields`, the function that was meant to carry these fields, ships unused'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [277, 115]
---

## Why this exists

277 (#361) ranks search hits inside their exactness band by stamped mirror pairs and puts a
`mirror_counterpart` on each mirrored hit. The decoration is `decorate_mirror_hits`
(`code_atlas/mirror_search.py:120`):

```python
known = {str(hit.get("file", "")) for hit in results if hit.get("file")}
...
answer = resolve_counterpart(path, pairs, known | _counterpart_candidates(path, pairs))
```

`_counterpart_candidates` (`:141`) **synthesizes** the counterpart path by prefix substitution
(`src/x.php` → `legacy/x.php`) and unions it into the known set — so `resolve_counterpart` answers
`COUNTERPART` for a path that may not be in the index at all. A file whose mirror sibling was deleted,
renamed, or never indexed (a genuinely *diverged* file) therefore gets a confident `mirror_counterpart`
pointing at a file that does not exist. That is precisely the case `NO_COUNTERPART`
(`code_atlas/onboarding/mirrors.py:46`) exists to mark — the honest "the pair diverged here" answer — and
this path routes around it. It is the empty-vs-unmeasured shape again (272/238): naming a sibling that
is not there reads to an agent as "the counterpart is `legacy/x.php`", not "there is no counterpart".

Separately, `attach_mirror_search_fields` (`code_atlas/mirror_search.py:109`, exported at `:37`) has no
caller in `code_atlas/` or `tests/` — `search_symbol` calls `decorate_mirror_hits` directly. It is dead
surface that either should carry the counterpart/order fields (one attach point, tested) or be removed.

## Scope / Deliverables

- **A counterpart is named only when it is in the index.** Restrict `decorate_mirror_hits` to
  counterparts that actually exist among indexed files; a synthesized-but-absent sibling yields no
  `mirror_counterpart` (and, where the payload should say so, a `no_counterpart`-style marker rather
  than silence — decide per 061).
- **Resolve `attach_mirror_search_fields`.** Either route the fields through it (single tested attach
  point) or delete it and its export.

## Constraints

- R5.6: the counterpart is a stored fact (an indexed file), never a string the pair rule can spell.
- 061: no new field on a hit that has no counterpart, unless the payload's honesty needs the marker;
  a single-tree repo (no pairs) stays byte-identical (277's AC2).
- R4.2: deterministic — same index, same counterpart decision.
- Do not change 277's ordering; this ticket is about the counterpart *value*, not the band order.

## Acceptance criteria

- A hit on a file whose synthesized sibling is **not** in the index gets **no** `mirror_counterpart`
  (was: a fabricated path).
- A hit whose sibling **is** indexed still gets the correct `mirror_counterpart` (unchanged from 277).
- `attach_mirror_search_fields` is either covered by a test through a real caller or removed with its
  export.
- 277's mirror-order and single-tree byte-identical tests still pass.

## References
`code_atlas/mirror_search.py:109,120,133,141`, `code_atlas/onboarding/mirrors.py:46` (`NO_COUNTERPART`),
`code_atlas/tools/search_symbol.py:327-329`, [277](277_page-one-ranks-the-tree-that-cannot-run.md),
115 (mirror subtrees / `find_mirror_subtrees`). Origin: review of #361, 2026-09-15 (non-blocking follow-up).
