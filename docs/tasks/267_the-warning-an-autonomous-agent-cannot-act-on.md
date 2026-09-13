---
id: 267
slug: the-warning-an-autonomous-agent-cannot-act-on
title: 'The question an agent most wants to ask — "what did I just break" — is the one the index refuses, and the remedy it prints for a stale server process is a human typing `/mcp`: an autonomous run sees both, can act on neither, and learns to ignore the honesty layer'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [257, 096, 035]
---

## Why this exists

Two operational cliffs, both recorded in field round 18:

1. **The whole session ran with `server_stale_process: true`.** The documented remedy is a `/mcp` reconnect — an interactive human action. An autonomous run can read the warning and cannot act on it; after the first call it is noise. A warning with no available action is a defect in the honesty layer, the same class as a zero with no `reason`.
2. **A commit touching indexed files flips `index_stale` and symbol queries refuse.** That refusal is correct, and it lands exactly when the agent wants to ask *"did I just break a caller?"* — the moment [096](096_edit-then-ask-tax-two-files-cost-a-minute.md) named as the cliff.

[257](257_the-index-goes-blind-at-the-moment-it-is-most-wanted.md) shipped the honest half: `label_serve_behind` (`tools/freshness.py:173`) serves an answer from the last built revision and stamps rows with `index_revision`. But it is opt-in **and restricted to subjects that did not change** — and the subject an agent asks about after an edit is precisely the one that did.

A silent stale answer is forbidden. A **loud** stale answer is a product.

## Scope / Deliverables

- **Extend labelled serve-behind to the changed subject.** Opt-in stays; the default stays refuse-when-stale. When served, the row carries `index_commit` / `index_revision` and the reason names the subject as changed since that revision — the agent is told exactly what it is holding.
- **Make `server_stale_process` actionable.** Either the server re-execs itself once, or the payload states which capabilities actually differ between the running process and its disk. A warning must name an action its reader can take.
- **The distinction stays visible**: unchanged-subject-behind (257's arm) and changed-subject-behind (this ticket) are different reasons, not one blurred label.

## Constraints

- **Never a silent stale answer.** If the labelling cannot be attached, the tool refuses — that is the existing default and it does not move.
- Read-through repair (035) stays first; this ticket only governs what happens after a non-stale freshness result declines.
- R4.2 unaffected: served rows are rows of the last built revision, byte-identical to what that revision produced.

## Acceptance criteria

- With the opt-in on, a query about a symbol in a file dirty since the last build returns rows stamped with the built revision and a reason naming the subject as changed; with it off, the refusal is unchanged.
- A test pins that no code path can emit a behind-index row without a revision stamp.
- `server_stale_process: true` payloads name either a performed re-exec or the differing capabilities; a test pins that the field never appears with an action the reader cannot take.
- 257's unchanged-subject arm keeps its own reason and its existing tests.

## References
[257](257_the-index-goes-blind-at-the-moment-it-is-most-wanted.md), `code_atlas/tools/freshness.py:173`, [096](096_edit-then-ask-tax-two-files-cost-a-minute.md), `code_atlas/build_info.py:160`, field retro round 18 (ask #4).
