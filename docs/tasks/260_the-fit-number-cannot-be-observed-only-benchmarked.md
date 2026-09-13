---
id: 260
slug: the-fit-number-cannot-be-observed-only-benchmarked
title: 'Fit — the binding constraint on this product — is a number that only exists when someone re-runs a benchmark; the server holds no local record of which tools were actually asked, so every decision about cutting or keeping the surface is taken blind'
phase: 1.5b
milestone: Adoption
status: todo
depends_on: [081]
---

## Why this exists

PLAN §19 records the founding benchmark's adoption figure: the agent reached for the index in **22 of 117 tool calls (19%)**. Every subsequent decision about the tool surface — keep 24, cut to six, write a better skill — is argued against that one number, taken once, on one session, on one repo.

Two live decisions wait on it:

- [200](200_the-recognition-map-is-a-prompt-no-agent-can-read.md) is `blocked` on AC5, a blind recognition round that costs a human session.
- Several feedback notes propose cutting the offered surface to six tools. `CA_TOOLS` already exists (`main.py:160`), so *offering* a preset is nearly free — but **changing the default** without a number repeats the mistake the notes spend pages refusing.

A local counter turns fit from a benchmark someone must re-run into a number that accrues while the server is used normally.

**This ticket does not wait on 200; 200 waits on it** (dependency inverted 2026-09-13). 200's code has landed and it is open on AC5 alone. The counter does **not** satisfy AC5 — that round is blind and before/after, this is passive and one-armed — but it removes the hand-tally of 117 calls that made the round expensive, so the round is cheaper after this lands than before.

## Scope / Deliverables

- **One meta row per `(tool, reason, authoritative, truncated)`**, in `graph.db` meta. Counts only.
- **Spec before counting.** *No* qname, *no* path, *no* argument values, nothing repo-identifying. A counter that could leak a codebase is a reason to turn the server off, and this project does not ship telemetry (R4).
- **Fit is defined narrowly and written down before the first count:** the share of *relationship* questions (caller / impact / path) that reached the graph, against a search/grep proxy — **not** "every tool call, divided". The 19% figure was measured over all calls in one mixed session; a counter that aggregates differently produces a number that cannot be compared to it, and the ticket must say which comparison it supports.
- **Read path**: surfaced through `get_index_status` at `verbose`, and resettable. Off is not required — local counts are not telemetry — but the field must be documented where a user will find it before they find it by surprise.

## Constraints

- **R4:** no network, ever. This is a local row in a local file.
- **R4.2:** the counter must not enter any payload a determinism test compares, and must not change row order or content anywhere.
- Not a ranking signal. This ticket produces a number a human reads; it must not feed retrieval.

## Acceptance criteria

- A test pins the recorded tuple shape and asserts no qname/path/argument value can reach the meta row.
- A test pins determinism: two identical builds + identical queries produce byte-identical payloads with the counter on.
- `docs/` states the fit definition (relationship questions vs search/grep proxy) **before** any number from this counter is quoted anywhere.
- `get_index_status --verbose` shows the counts; a documented reset exists.

## References
PLAN §19 (22/117), [200](200_the-recognition-map-is-a-prompt-no-agent-can-read.md), `docs/runbooks/tool-recognition-probe.md`, `code_atlas/main.py:160` (`CA_TOOLS`).
