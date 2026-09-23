# 324 — Field claim ledger: facts the index produced that text search structurally cannot

**Status:** first pass, 2026-09-22. **Corpus:** 43 field retros, 2026-08-07 → 2026-09-22, written
against the anchor repo (PHP + T-SQL, ~13.4k files). **Verdict: 7 confirmed · 2 plausible · 1 struck.**

This measures the claim [PLAN §19](../PLAN.md#19-project-context--decision-log) named on 2026-08-08
and never quantified: *"What survives is relationships, not locations."* The entry that refuted the
founding premise carries hard numbers; the claim that replaced it carried none. This file is that
number, and it does not touch the 2026-08-08 entry — a measurement is answered by another
measurement, never by deleting the first.

## What counts as a row

Retro self-ratings are **not** evidence here. This corpus already contains one case of a retro
scoring itself a win that an audit voided (see [Struck](#struck)), which is the whole reason the bar
below exists. A row is admitted only if all three hold, and the third is the one most candidates
fail:

1. **The fact** — what the index returned, concretely.
2. **The mechanism** — *why* text search cannot return it, stated so a reader can check the
   reasoning without trusting the retro. "Grep was slower" is not a mechanism; "the name never
   appears as literal text" is.
3. **The consequence** — what changed in a shipped artifact: the fix, the PR, the migration, the
   recommendation. A row that stops at "this was useful" is marked *plausible*, not confirmed.

Identifying names are replaced by their shape throughout; the mechanism is what carries the claim,
and the client's vocabulary is not needed to state it.

## Confirmed

| # | The fact the index returned | Why text search cannot | What changed |
|---|---|---|---|
| 1 | An **in-class caller** of a handler reached through a dispatcher's `case` label | A grep of the dispatch file sees the `case` label; the call sits inside the class, not at the dispatch site | A security fix went from "gate the three named handlers" to "gate the three **plus the wrapper**" — without it the fix shipped false |
| 2 | **0 `INCLUDES` edges** where the text held four `require_once` lines | All four were `//require_once` — commented out. Grep matches text; the parse knows whether the text is code | A platform-upgrade recommendation flipped from **two steps to one** |
| 3 | A 508-line method read **whole**, exposing a three-site interaction on one superglobal key | Symbol bounds come from the parse, not `sed`/`grep -A` arithmetic; no line window bounds a 508-line body | **Two prior attempts had shipped incomplete fixes** without it |
| 4 | A **second** stored procedure writing a table, via that table's inbound `WRITES` | The author had grepped, found the first procedure, and stopped; grep offers no "what else writes this object" closure | The migration's header claim went from an observation to a property of the design — it would otherwise have shipped "weaker and slightly wrong" |
| 5 | 29 resolved callers of a global access check, among them a **protected wrapper existing so tests can mock the gate** | Reading 29 *resolved* callers at once — grep neither resolves nor groups them | The existing idiom was copied verbatim instead of a new seam being invented |
| 6 | `production_count: 1`, `test_count: 17` on a save path | Grep yields one undifferentiated count and cannot separate production from test | Proved one gate covered the whole path, and let the PR say so |
| 7 | `production_count: 0`, `test_count: 2` on the last reader of a SQL expression | *"Zero production callers"* is a claim text search cannot make at all | It was the claim that ticket's analysis needed |

Rows 1 and 2 are the strongest: in both, text search does not merely fail to answer — it returns a
**confidently wrong** answer. Row 2 is the sharper of the two, because grep's four textual hits look
exactly like four real includes.

## Plausible — mechanism holds, consequence not recorded

| # | The fact | Why text search cannot | Why not confirmed |
|---|---|---|---|
| 8 | A column found by a `kind=Column` sweep although the porting query selects it under an alias | The column's name never appears as literal text at the reading site | The retro records the find, not what it changed |
| 9 | One call returning a unified port plus both legacy twins, each twin annotated with its counterpart | Grep returns hits with no relation between them; the annotation *is* a resolved relation | Recorded as decisive for the author's understanding; no artifact change stated |

These stay listed rather than dropped: the mechanism is checkable, and a later retro may supply the
consequence. They are not counted in the headline.

## Struck

**Round 5 (2026-08-11) claimed `search_symbol` prevented a latent fatal, and scored the tool "WON,
decisively".** A field interview on 2026-08-14 audited the claim and found it did not hold; the retro
now carries its own correction — *"That justification is **void** — see §8"*. The session's overall
verdict survived the correction on a different and narrower ground.

It is kept here because it is the calibration: one in ten candidate wins in this corpus, written up
persuasively by the person best placed to know, was wrong. Any future row is one audit away from the
same fate, and a ledger that has never struck anything has not been audited.

## What this does and does not establish

**Does:** on real defect work, the index repeatedly produced facts text search cannot produce, and in
seven recorded cases that changed what shipped. Two of the seven are cases where grep would have
answered *confidently and wrongly*, which is worse than not answering.

**Does not:** say the index is cheaper, faster, or more accurate than native tools on an arbitrary
question. The 2026-08-08 benchmark measured that and refuted it, and nothing here revisits it. Every
row above sits **after** discovery — the question is not *"where is it"* but *"is this change correct
and complete"*, and that is the division of labour the server's own instructions state.

**Threats, recorded rather than hidden.** Author and tool operator are the same person in every
retro, and the corpus is one repo in one domain; n = 43 sessions, not 43 independent observers. Row
selection was not blind — these are the cases that read as strongest on a full pass, and a reader
who disagrees with a row's *consequence* column should strike it rather than argue the count. The
headline is the aggregate; no single row carries it.

## References
Corpus: the field retro set, 2026-08-07 → 2026-09-22. [PLAN §19](../PLAN.md#19-project-context--decision-log)
(2026-08-08 founding-premise benchmark and its adopted consequences);
[074](074_mechanism-question.md) (why a granted arm cannot be bought);
[`LESSONS.md`](../LESSONS.md) (claim corpus and the `seen:` gate, P1).
