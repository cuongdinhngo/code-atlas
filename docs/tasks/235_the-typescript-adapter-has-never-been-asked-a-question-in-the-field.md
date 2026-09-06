---
id: 235
slug: the-typescript-adapter-has-never-been-asked-a-question-in-the-field
title: 'The TS/JS adapter has passed every gate that reads a fixture and none that reads a repo — 15 findings have come from field rounds over PHP, SQL and Python builds and not one from TS, so its recall and its honesty are both unmeasured'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [019, 150, 018, 233]
---

## Why this exists

Gate 4 in [`../ADAPTER_PLAYBOOK.md`](../ADAPTER_PLAYBOOK.md) §4 — *ask each nav tool a question you
already know the answer to* — is the only gate that has ever produced a finding, and **it has never
been run against the TS adapter.**

| | php | sql | python | typescript |
|---|---|---|---|---|
| gate 1-2 (fixtures + conformance registry) | ✅ | ✅ | ✅ | ✅ |
| gate 3 (pinned public samples) | 3 | 0 ([233](233_python-and-sql-have-no-pinned-public-sample-so-no-change-to-either-can-be-shown-to-move-anything.md)) | 0 (233) | 3 |
| gate 4 (field round on a real repo) | 5 rounds | round 14 | 2026-09-05 | **never** |
| findings it produced | 136, 137, 221-223 | 221, 222, 224, 228 | 226, 227, 229, 230 | — |

TS is the **only** adapter with pinned samples and no field round, which makes it the cheapest gap
in the matrix to close: the checkouts, floors and adapter command already exist (150), so this is a
protocol run, not an infrastructure build.

**What the two cheaper gates already proved they cannot see.** 019 shipped TS with 20 fixtures and a
conformance row; 150 added its static analysis and cross-repo run. All three were green while:

- `params` was never emitted for any callable — **`0/3`** in the generated parity table;
- `modifiers` was never emitted at all, so `private`, `public`, `protected`, `static` and `readonly`
  are absent from a language that spells every one of them as a keyword — **`0/5`**;
- `REFERENCES` was never emitted from any construct, so `find_references` on a type used as a type
  answers zero and calls it a match-free answer
  ([232](232_the-same-construct-is-a-references-edge-in-python-and-node-extra-in-php-and-ts.md)).

Those three came from **reading** the adapter — the cheaper sibling of a field round — and each is a
gap a fixture suite was structurally unable to notice, because a fixture asserts what the adapter
emits and never what the file contained. A field round asks the other question.

## Scope

Run the playbook §5 protocol against a real TS/JS repo, and file what it returns. The protocol is
not restated here (R7.6); what this ticket adds is the corpus choice and the reporting bar.

1. **Choose two repos by shape, not popularity.** One `tsconfig` monorepo with project references
   and path aliases — the shape `IMPORTS` resolution (155) is most likely to miss on — and one mixed
   `.ts`/`.js` package with JSDoc types, the shape 154's slot exists for. The three pinned samples
   already cover a library, a mixed package and compiled-beside-source, so a field repo should add a
   shape they do not.
2. **Record the numbers the protocol asks for**, in a `benchmarks/` file: parsed_ok, the node census
   against a `grep` count per kind, the unlinked-edge ratio per kind split into expected and
   recoverable, and the cross-language census.
3. **Ask the nav tools questions verified by `grep` first.** `find_implementations` on an interface
   the repo implements across files, `find_callers` on an exported function, `find_references` on a
   type. A confident zero on any of them is the finding.
4. **File each finding as its own ticket** with a minimal fixture through `--file` (playbook §5
   step 7). This ticket delivers the measurement and the tickets; it fixes nothing itself.
5. **Fold the result into the parity table's gate rows** so the matrix above stops being true.

**Not in scope:** fixing anything the round finds — that is what item 4 is for; a second round;
the three known gaps above, which 231 and 232 already own.

## Acceptance criteria

- **AC1** A `benchmarks/` file carries the round's numbers, the two repos at pinned SHAs, the host
  and the date. Without pinned SHAs the round is unreproducible and its numbers are anecdote (018).
- **AC2** Determinism is proven on the corpus, not assumed: two clean builds hash identically over
  ordered nodes + edges (R4.2), with `graph.db` deleted between them (219).
- **AC3** Every nav-tool question asked is recorded with its `grep`-verified expected answer beside
  the payload's answer — including the ones the tool got **right**. A round that lists only misses
  cannot be read as a measurement of anything.
- **AC4** Each finding is a ticket with a `--file` fixture, or is explicitly recorded as *not
  reproducible outside that repo* and dropped. A finding without a fixture does not become a ticket
  (playbook §5 step 7).
- **AC5** **A round that finds nothing is a valid, publishable result** and closes this ticket
  green. The deliverable is the measurement; "no new findings" is evidence about the adapter, and
  recording it is what makes the gate meaningful rather than a search for bad news.

## Exclusions

- **E1** No private TS corpus is available to this repo, so unlike rounds 1-14 this one has no
  consumer-repo evidence to draw on. That makes the pinned public choice in scope item 1 the whole
  design of the round, and a poor choice yields a green round that proves nothing — which AC3's
  "record the hits too" is there to expose.

## Notes

**Why this is a ticket and not a habit.** Gates 1-3 are enforced by `pytest` and `cross_repo_validate.py`;
gate 4 is enforced by nothing, which is why it has run four times in fourteen rounds and skipped the
adapter nobody uses in anger. The playbook can say the gate is required; only a ticket per adapter
makes it happen.
