---
id: 182
slug: find-orphans-answers-with-rows-it-has-flagged-unreliable
title: '`find_orphans` returns 215,177 rows it has already flagged unreliable — 99.31 % of the graph, from entry points that reach almost nothing'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [124, 031, 119]
---

## Why this exists (field retro rounds 7–12; fired as a probe every round, never filed)

Carve-out **(e)** — *"`find_orphans` unavailable above ~10k files"* — has been HOLD for five rounds.
Round 12 fired it again and produced the number that makes it a defect rather than a limit:

```
find_orphans → 215,177 orphans of 216,664 nodes = 99.31 %
               walk_truncated: true
               authoritative: false
               entry_points: ["public/*.php"]
```

**The tool flagged its own answer unreliable and then returned 215,177 rows anyway.** Round 12's
verdict: *"a tool that returns 215,177 rows it has already flagged as unreliable is worse than one
that returns `status: roots_unreachable`."*

### The root cause is the roots, not the walk

`entry_points: ["public/*.php"]` is the configured start set. In the anchor, `public/main.php`
`chdir()`s into `legacy/*/web` and dispatches from there, so **the configured roots reach almost
nothing and nearly every node is correctly unreachable from them.** 99.31 % is not a bad algorithm
meeting a big repo — **it is a correct algorithm with the wrong roots**, and nothing in the payload
distinguishes those two readings. 124 fixed the *transport* limit; it did not touch this.

**Corollary from round 12 §12.e:** the top orphan rows were `.claude/skills/legacy-compare/probe.js`
— agent tooling newly indexed by adapter #2, now in the orphan population. A second language widened
the numerator of a fraction whose denominator was already wrong.

## Scope

1. **`walk_truncated` becomes a refusal, not a caveat.** A truncated walk cannot support a
   reachability claim, so the answer is a named refusal carrying what it *can* say (nodes visited,
   budget hit, the roots used) — never a row list. Design records the vocabulary and how 102's
   *"absent subject ≠ modelled zero"* distinction is preserved.
2. **An implausible orphan share is itself a refusal condition.** A share above a stated threshold is
   evidence the roots are wrong, not that the code is dead. Design picks the discriminator and
   **records why a bare threshold is or is not a claim the graph can support** (161 AC1 — a threshold
   is a claim; say what makes this one different, or reject it and find another discriminator).
3. **The roots become visible and correctable.** The payload names the entry points it used and how
   many nodes they reached; a root pattern that matched zero files is named. Whether the default set
   should be derived rather than configured is a design question this ticket delegates — **deriving
   dispatch roots from a `chdir()` is exactly the kind of fact §2.b says is not in the graph, so
   "configurable, and honest about what was configured" may be the correct endpoint.**

### Explicitly not in scope

- The transport/scale fix — [124](124_find-orphans-cannot-answer-at-scale.md), done.
- Reading the anchor's dispatch table. R2: the core encodes no repo's routing.
- Changing the reachability relation set or `IMPACT_KINDS`.
- Excluding agent tooling from the index. That is a consumer `.codeatlasignore` decision, recorded
  here only because it explains one row of the field output.

## Constraints

- **102** — a refusal must stay distinguishable from *"nothing is orphaned"*, which is a real and
  useful answer.
- **061** — a repo whose walk completes within budget and returns a plausible share is byte-identical.
- **Cost** — the walk is already budgeted by `config.orphans_max_nodes` (124); this adds no walk and
  no per-node query.
- **R5.2** — the refusal is sourced from the computation (budget hit, roots reached), never from a
  table of known-bad repos.
- **R5.6** — an index that cannot establish the condition says nothing rather than guessing.
- **R1.1** no language branch · **R3** confirm whether a refusal reason is nav or contract vocabulary
  · **R4.2** deterministic.

## Acceptance criteria

1. A fixture whose walk exceeds the node budget returns a **refusal with no row list** — pinned by a
   test that fails on today's code.
2. A fixture whose roots match no files names that, and refuses — pinned.
3. A genuine, complete, plausible orphan answer is byte-identical to today (061), pinned.
4. *"Nothing is orphaned"* remains distinguishable from *"cannot tell"* (102), pinned on both.
5. Scope 2's verdict is recorded: the discriminator chosen, or the reason a threshold was rejected.
6. The payload names the entry points used and the nodes they reached; a zero-match root is named.
7. No added walk, no per-node query — measured.
8. Determinism (R4.2), no language branch (R1.1), contract impact confirmed (R3).

## References

Field retro round 12 §9.b, §12.e (the 99.31 % measurement and the root-cause diagnosis), §14.a
carve-out (e) — **HOLD for five rounds with no ticket, which is why this one exists**; round 11
measured the same shape at 99.2 %. `code_atlas/tools/get_index_status.py:135-140`
(`orphans_max_nodes` / `orphans_reachability_walk`). Related:
[124](124_find-orphans-cannot-answer-at-scale.md) (the transport half, done),
[031](031_reachability-orphans.md) (the walk),
[119](119_reachability-signal-provenance.md) (signal provenance).
