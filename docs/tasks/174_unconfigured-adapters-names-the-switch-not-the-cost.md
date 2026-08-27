---
id: 174
slug: unconfigured-adapters-names-the-switch-not-the-cost
title: '`unconfigured_adapters` names the switch but not the cost — four rounds of "adapter contributes zero" and no payload ever said how many files were invisible'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [159, 082]
---

## Why this exists (field episode, 2026-08-27)

159 made the unwired adapter visible. Round 11 then recorded the adapter's **fourth** consecutive zero
contribution, caused by one absent env var — and the maintainer's reading of why the disclosure never
moved anyone:

> *"`unconfigured_adapters` nên nói cái giá, không chỉ nói nó tồn tại. Trước restart nó đọc
> `[{"language":"typescript","enable":"CA_TYPESCRIPT_CMD"}]`. Thiếu đúng con số quyết định: 3.294 file
> trong repo này khớp adapter đó và đang vô hình. Đây có lẽ là thay đổi duy nhất dễ nhất khiến adapter
> được bật từ mấy round trước, thay vì bốn round liền báo zero."*

*"An adapter exists"* is a fact about the product. *"3,294 files in **this** repo are invisible"* is a
fact about the reader's own cost, and it is the one that would have been acted on. Rounds 8–11 all
disclosed the former and all reported zero.

## Root cause, and why the obvious version does not work

- `code_atlas/adapter.py:334-348` — `unconfigured_adapters` knows only the **directory name** of each
  shipped adapter. Extensions come from the handshake (`adapter.py:118`,
  `announced = self._announced()["extensions"]`), and an unwired adapter is never launched — so the
  core cannot ask it what it would have claimed.
- The census cannot be joined either: `skipped.suffix` is a single total
  (`code_atlas/tools/collection.py:24-27`, from `census["skipped_suffix"]`) covering **every**
  unindexed suffix in the tree — `.css`, `.md`, images, lock files. **The 3,244-file figure is not
  derivable from it.** Any per-language split would need a suffix table in the core, which R1.1
  forbids.
- So the honest cheap form inverts the join: **the census reports a bounded histogram of the top
  unindexed suffixes** (`{".js": 2831, ".ts": 460, …}`), computed in the walk that is already
  happening, naming no language. The reader — or the agent — joins it with `unconfigured_adapters`.
  A shipped-adapter manifest read without launching is the alternative, and it is a bigger change.

## Scope

1. The collection census gains a bounded, deterministic histogram of the most common **skipped-by-suffix**
   extensions, with the cap and tie-break recorded. Language-agnostic by construction (R1.1).
2. It rides `get_index_status` where `skipped.suffix` already does, at the same detail levels.
3. Design records whether the histogram is enough on its own, or whether an adapter manifest should
   later let `unconfigured_adapters` state the count directly — and what that would cost.

### Explicitly not in scope

- Reading or launching an unwired adapter to learn its extensions. That is the bigger alternative
  above; this ticket must not smuggle it in.
- A suffix→language table anywhere in `code_atlas/` (R1.1).
- Per-language node/edge counts, and the coverage-note keying
  ([173](173_coverage-claims-key-on-configured-not-indexed.md)).

## Constraints

- **Cost** — counted inside the existing walk; no second pass over the tree, no new query at answer
  time. Bounded output (top-N), so a repo with 400 extensions cannot inflate the payload.
- **082** — the collection identity `collected − skipped_suffix − skipped_ignore == kept` still
  reconciles; the histogram is a breakdown of one term, never a replacement for it.
- **061** — omit when empty; a repo whose every suffix is indexed adds nothing.
- **R1.1** no language named in the core · **R4.2** deterministic order and tie-break · **R3** confirm
  no contract impact.

## Acceptance criteria

1. A build over a fixture tree with several unindexed suffixes reports a histogram whose entries sum
   to no more than `skipped.suffix`, with a recorded cap and a deterministic tie-break.
2. 082's collection identity still reconciles exactly, pinned.
3. The histogram appears on `get_index_status` at the recorded detail levels and is omitted when empty.
4. No new walk, no new answer-time query; the added build cost is measured.
5. `grep` for a suffix→language mapping in `code_atlas/` finds none (R1.1 gate green).
6. Determinism (R4.2), no contract bump (R3).

## References

Field episode 2026-08-27, finding (2) — reframed after checking the source: the maintainer proposed
deriving the count from `skipped.suffix`, which cannot carry it. Round 8 §13, round 9 §13, round 10 §13,
round 11 §13 (four consecutive zeros, all disclosed and none acted on).
`code_atlas/adapter.py:118,334-348`; `code_atlas/tools/collection.py:24-27`. Related:
[159](159_get-index-status-does-not-name-available-but-unconfigured-adapters.md) (what this completes),
[082](082_claims-nobody-outside-can-check.md) (the identity), [160](160_a-zero-answer-never-names-the-index-language-coverage.md).
