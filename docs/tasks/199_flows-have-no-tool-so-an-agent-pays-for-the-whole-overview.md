---
id: 199
slug: flows-have-no-tool-so-an-agent-pays-for-the-whole-overview
title: "Capability flows have no tool of their own, so an agent asking about one request pays for the whole overview"
phase: 3
milestone: M11
status: todo
depends_on: [197]
---

## Why this exists

[197](197_no-surface-follows-one-request-from-entry-to-the-data-it-writes.md) shipped capability
flows to the surfaces a **reader** uses — the 112 dataset, the viewer, and a committed `flows.md`.
It deliberately shipped **no agent-facing surface**, and that was not a preference: it was measured.

197 tried one (`summary.flows` on `architecture_overview`) and the repo's own gate rejected it:

```
GATE FAILED: tokens-to-answer ratio 0.53 is below the floor 0.63 (grep 3065 / atlas 5786 tokens)
precision 0.944 | unexpected 6
```

Two distinct defects, both properties of the surface rather than of the flows:

1. **Cost.** To read one 4-file trace an agent bought the entire overview payload — layer table,
   layer×layer matrix, hubs, reachability split, capability table, mirrors — ~2,400 tokens against
   `grep`'s 852.
2. **Over-answering.** `summary.flows` returns **every** flow, so a question about **one** request
   claimed 6 files belonging to other requests. Those files are not wrong; the *question* cannot be
   asked of that surface.

197 reverted it and recorded AC8 as exclusion **E3** with `expiry: when 199 lands`. This ticket is
that expiry.

## Scope

1. A tool that answers **one** capability question — an entry symbol, a file, or a business module —
   and returns only the flows that subject participates in.
2. Payload sized like the other nav tools: the trace, its hops with layer and confidence tier, its
   ending, its attribution. Not the dataset, not the layer table.
3. A `tier: onboarding` question in the 121 harness of the shape *"what happens when a user does
   X?"*, ground truth **hand-read before the tool runs** — the criterion 197 could not meet.

### Explicitly not in scope

- Re-deriving flows. `code_atlas/onboarding/flows.py` already builds them; this is a query surface
  over the same derivation, never a second notion of a flow (PLAN §1).
- Widening `architecture_overview`. Measured and rejected above.

## Constraints

- **The gate is the acceptance test, not a report:** `--min-ratio 0.63 --min-recall 1.0
  --min-precision 1.0` must stay green **with the new question in the registry**. A tool that cannot
  beat `grep` on its own question has not earned its payload, and saying so in writing is what
  [121](121_onboarding-question-class-never-measured.md) and `ROADMAP.md` §5 require.
- **R4.3** — bounded like every nav tool; **R4.2** — byte-identical output; **R1.1/R1.4**.
- The tool surface is an invariant with many readers (`TOOL_NAMES`, `TOOLS.md`, PLAN, the MCP
  conformance tests) — 194's blast-radius lesson applies.

## Acceptance criteria

1. One tool answers one subject's flows; a subject that matches nothing **refuses with a reason**
   rather than returning an empty list (182).
2. Its payload carries no aggregate the question did not ask for.
3. The 121 harness gains the behaviour question, and the **gate stays green at the existing floors**
   — no floor is lowered to accommodate it.
4. `flows.py` is unchanged except where the query genuinely needs it.

## References

[197](197_no-surface-follows-one-request-from-entry-to-the-data-it-writes.md) (the flows, the
measurement, and E3), [121](121_onboarding-question-class-never-measured.md) (the question class and
its narrowing), [182](182_find-orphans-answers-with-rows-it-has-flagged-unreliable.md) (refuse rather
than dump), [194](194_default-filled-column-defect-class-query.md) (the tool-surface blast radius).
