---
id: 095
slug: ignore-bucket-does-not-name-its-rule
title: '`collection.ignore: 9541` excludes indexable PHP by an unnamed rule'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [082, 003, 068]
---

## Goal
[082](082_claims-nobody-outside-can-check.md) made the denominator auditable and it works: on the
anchor repo both identities close exactly and `collected` matches the evaluator's own
`git ls-files | wc -l` **to the file**. But the census answers *how many* and not *by what rule*, and
one bucket carries **9,541 files that all have an indexed suffix** — they are PHP the index chose not
to hold. Nothing in any payload says which rule excluded them.

The consequence is precise: every absence answer over this repo has an unknown denominator. An agent
that gets `no_matches` cannot tell whether the subject is absent from the codebase or sitting in the
9,541.

## Evidence (field retro round 5, 2026-08-14, probe P2 — 082 verification)
- Verbatim:
  ```json
  "collection":{"collected":55278,"skipped":{"suffix":26811,"ignore":9541},"kept":18926,
                "indexed_suffixes":[".php",".phtml"]}
  ```
  `55278 − 26811 − 9541 = 18926 = kept` ✓ and `18926 + 0 stubs = 18926 = files` ✓.
- The evaluator **probed two guesses with `file_outline` and disproved both** — the legacy tree *is*
  indexed and the test tree *is* indexed — and still could not name what the 9,541 are (§11.5).
- 082's verdict is **FIXED** with this recorded as a semantic gap, not a regression: the arithmetic is
  fully auditable from outside; the semantics are not.
- Retro's own suggested shape: name the ignore *sources* — `ignore: {gitignore: N, config: N,
  vendor: N}` — not just the total.

## Scope / Deliverables
- **Attribute each ignore-skip to its source rule** in the same single walk that produces the census
  (`_collect_with_census`, `code_atlas/indexer.py:356-378`) — no second traversal, no rival count.
  The sources are whatever `load_ignore` actually composes (built-in defaults, `.gitignore`,
  configured `CA_*` ignores); enumerate them from the matcher rather than hand-listing them.
- **Report the breakdown** under `collection.skipped.ignore` at `verbose`, keeping the flat total so
  the 082 identities still close by construction and existing consumers do not break.
- **Decide the granularity.** Per-source counts are the ask. Per-*pattern* counts are a different
  cost; if design rejects them, record why and what an agent should do instead when a source's count
  is surprisingly large.
- **Say it once, in the right place.** 061's payload-weight rule applies: this belongs at `verbose`
  on `get_index_status`, not on every nav answer.
- **Record the anchor's actual breakdown in this ticket** when it lands — the number that motivated
  the ticket should end with a name attached.

## Constraints
- R1.1 — ignore rules are config, not language knowledge; the attribution must not learn about PHP.
- R4 — deterministic: the same tree yields the same per-source counts, and a file matched by two
  sources must be attributed by a stated, stable precedence rule (first match wins, in matcher order)
  rather than double-counted. The identities must still close.
- Cost: one pass, no extra stat calls per file beyond what the matcher already does.
- 082 stays authoritative for the census contract; this extends a bucket, it does not restructure it.

## Acceptance criteria
- A fixture repo with files excluded by two different sources reports the correct per-source counts,
  and `sum(sources) == ignore` with the 082 identities still closing — pinned by a test.
- A file matched by two sources is attributed once, under the documented precedence, with a test that
  fixes the precedence.
- `get_index_status(standard)` is byte-identical to today (R4); the breakdown appears only at
  `verbose`.
- The anchor repo's real breakdown for the 9,541 is written into this ticket's resolution.

## References
Field retro round 5 §A.8, §11.5; candidate 4.
Related: [082](082_claims-nobody-outside-can-check.md) (the census), [003](003_config-and-ignore.md)
(the ignore rules), [068](068_rules-bookmark-counted-as-source-file.md) (the last time the denominator
was wrong for an unnamed reason), [061](061_payload-weight.md) (where a field is allowed to live).
