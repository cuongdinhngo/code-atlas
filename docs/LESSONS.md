# Lessons — code-atlas

Durable lessons from shipping tasks: constraints found, wrong assumptions, process gaps. Two shapes,
read by two different readers:

- `## <task> — <lesson>` — the narrative, for a human. Newest first.
- `### <CLAIM-ID> — <one falsifiable sentence>` — an atomic claim in mango's learning-loop shape
  (`type` · `handle` · `status` · `seen` · `evidence` · `destination`). Recall greps these by
  `handle:`; **recurrence is the number of distinct ticket keys in `seen:`**, unioned across every
  claim that shares a handle.

**Two record forms, one meaning.** A claim that is still live — every type-2 heuristic, and
anything with a destination outside this file — keeps the full field block above. A claim that is
`type: 5` and `destination: stays in lessons_path` (confirmed, recurrence 1, and already stated by
the narrative it sits under) is written as a compact `*Claim `NNN-Cx` — …*` line carrying the same
fields inline, including its `area:` recall key.

**One claim record per handle.** Where a class was filed under several ids, the ids are aliased in a
single heading and the `seen:` lists are unioned — the recurrence is identical either way, and three
separate blocks made a recurrence-4 class read as three recurrence-1 notes. Two ids had been used
twice for different claims; inside this file each now heads exactly one block — `088-C1` is
`own-only-what-you-wrote` and `089-C1` is `embed-what-file-cannot-fetch`, the meanings their external
citations use. The other two sightings are aliased under `085-C1` and `093-C3`.

## Class index — read this before proposing a new rule

Every type-2 handle at recurrence ≥ 2. Six are already binding rules: re-deriving one is wasted work,
and the honest move on a new sighting is to bump `seen:`, not to write a fresh claim.

| handle | rec | tickets | where it landed |
|---|---|---|---|
| `derived-not-listed-invariant` | 14 | 087–088, 093, 095–097, 099–102, 121, 122, 127, 132 | **R6.7** |
| `prove-the-guard-fails` | 11 | 087–089, 093, 096, 099–101, 121, 122, 132 | **R6.5** |
| `do-not-attest-past-the-payloads-resolution` | 7 | 087–089, 100–102, 107 | open — **rejected at rec 3; that verdict is stale** |
| `fixture-shape-begs-the-question` | 7 | 084, 086, 103–106, 121 | **R6.3** — widened 2026-08-23, provisional |
| `try-instead-tool-name` | 5 | 092, 093, 100–102 | **R5.4** |
| `count-pin-in-blast-radius` | 4 | 085, 087–089 | open — never proposed |
| `source-the-caveat-from-the-computation` | 5 | 100–102, 122, 127 | **R5.5** |
| `re-verify-the-assumption-on-a-new-path` | 3 | 102, 107, 122 | open — never proposed |
| `re-run-the-sweep-after-the-last-edit` | 3 | 100–102 | **AGENT_BRIEF P4** |
| `route-must-answer` | 3 | 093, 101, 102 | folded into **R5.4**'s falsifier |
| `rank-before-truncate` | 2 | 067, 126 | open — proposed 2026-08-23, awaiting ratify |
| `guard-asserts-rendered-not-shipped-bytes` | 2 | 116, 127 | open — proposed 2026-08-23, awaiting ratify |
| `sibling-meta-non-int` | 2 | 092, 095 | **R1.7** |
| `record-the-deviation-as-a-deviation` | 2 | 101, promote-2026-08-15 | **AGENT_BRIEF P3** |
| `one-rule-for-every-subject-slot` | 2 | 102, 122 | open — never proposed |
| `ac-failure-mode-needs-the-right-guard` | 2 | 085, 107 | open |
| `own-only-what-you-wrote` | 2 | 088, 089 | open |
| `skip-dynamic-means-unlinkable` | 2 | 094, 096 | open — rejected 2026-08-15 (2nd sighting bound a design) |

**Three classes are overdue.** `do-not-attest-past-the-payloads-resolution` (7),
`count-pin-in-blast-radius` (4) and `re-verify-the-assumption-on-a-new-path` (3) all clear the
recurrence gate and none has ever been proposed — because their sightings were split across ids,
which is `PROM-C1`'s under-count recurring one level up.
`fixture-shape-begs-the-question` left this list on 2026-08-23: widened into **R6.3** rather than
proposed as a new rule, because R6.3 already owned cross-repo validation and P2 asks for the widening.

**A second under-count, one level up again (132).** Both rules' own `seen:` lines had fallen behind
this index — R6.7 listed 8 of 13 keys and R6.5 listed 5 of 10. P1 keeps the *claim's* list honest and
nothing kept the *rule's*, so the rule a reader consults under-reported its own recurrence. Both are
now reconciled to this table.

## 133 — A per-file ceiling cannot bound what the caller actually pays

134 gave every standing doc a ceiling and each one held, yet the sum an agent read before it knew
what bound it was still **49,572 tokens** — six files each comfortably under their own number. A
budget expressed only per-file is unbounded in the dimension that matters, because the count of files
is free. **Fix:** cap the *sum* (`tests/test_agent_chain_budget.py`, 25,000) and derive the member
set from the chain's own list, so adding a file to `AGENTS.md`'s binding list is what trips the
guard. Generalises: whenever a cost is paid over a set, bound the set's total, not its elements —
and check the arithmetic before committing to a fix, because this ticket's two *named* moves (PLAN
§19 + the token ledger, 11,795 tokens) fell 12,777 short of its own stated goal.

*Claim `133-C1` — a per-element ceiling on a cost paid over a set leaves the total unbounded, because
the element count is free.* · type: 2 · handle: `per-element-ceiling-leaves-total-unbounded` ·
status: confirmed · seen: 133 · area: docs/budgets · evidence:
`tests/test_doc_size_budget.py` all-green at a 49,572-token tier 1 · destination: stays in
lessons_path until a second key.

*Claim `133-C2` — a demotion is only real if returning the demoted item breaches the budget; assert
that, or the boundary is decoration.* · type: 2 · handle: `demotion-needs-a-breach-test` · status:
confirmed · seen: 133 · area: tests/guards · evidence:
`tests/test_agent_chain_budget.py::test_returning_a_consult_only_doc_to_the_binding_list_breaches` ·
destination: stays in lessons_path until a second key.

## 132 — A guard that keeps passing while its inputs move under it

`test_backlog_bookkeeping.py` bounded BACKLOG's Token-usage table by partitioning the tail on
`## Suggested order` — a heading the file had stopped having, so the ledger ran to end of file and any
three-cell `| NNN | … | … |` row in a later section counted as a recorded spend. Nothing under
`## Conventions` is row-shaped today, which is the only reason it never fired. The same reader found
`Status` at a hard-coded column index and defended itself with floors of 24 tasks / 7 done / 7 token
rows against a tree holding 130 / 116 / 118.

The audit that found it also over-claimed it, and that is the more useful half. Task 132 stated that a
fifth `Pillar` column would move `status` out of the capture group and leave the guard passing while
comparing nothing. Measured before fixing: it fails either way — the row drops and set-equality
catches it, or the status reads `graph` and the per-task assertion catches it. The positional parse was
unclear and brittle; it was not vacuous. A defect argued from reading the regex, not from running it,
was wrong in the direction that would have justified more change than the evidence supported.

### 132-C1 — new sightings of existing classes, recorded as `seen:` bumps
`derived-not-listed-invariant` (rec 13 → **14**, already **R6.7**) gains 132: the reader now finds the
`Status` column by reading the table's own header row and bounds each section at the next heading,
instead of hard-coding an index and a successor heading. A column position is the same hand-kept
member list one level up — the structure, not the vocabulary.
`prove-the-guard-fails` (rec 10 → **11**, already **R6.5**) gains 132: four red runs recorded before
the fix shipped — a stray row below the ledger (old reader ingests it, new one does not), a stray row
inside it (fails the new subset assertion), the `Status` header renamed to `State` (fails the derived
lookup), and a `Pillar` column added (passes, by design, which is what makes the tolerance a claim
rather than a hope).

### 132-C2 — A rule's own `seen:` list drifts even when the claim's does not
- type: 2 generalisable-heuristic
- handle: rule-seen-list-drifts-from-the-index
- status: proposed (awaiting human confirm)
- seen: 132
- evidence: R6.7's provenance line listed 8 of the class index's 13 ticket keys and R6.5's listed 5 of
  10, both behind by every sighting recorded as an index bump rather than a fresh claim; P1 keeps the
  claim's list honest and no rule kept the rule's
- area: rule-book provenance / promotion bookkeeping
- destination: stays in `lessons_path` until a second sighting — one occurrence, and the check it
  implies (reconcile a rule's `seen:` against the class index whenever either moves) is cheap enough
  to state without a rule
- resolved: 134 removed the surface instead of adding the check. The rule book's `seen:` lists had no
  reader — P1 binds the list in **this** file, and `/mango:promote` greps the destination only for the
  handle slug and the claim IDs — so every provenance line is now `handle (claim-ids)` and the
  sightings live in the class index alone. There is nothing left to reconcile, which is a better
  answer than reconciling it on a schedule. The class cannot recur while that holds; reopen it if a
  ticket count is ever copied out of this file again.

## 121 — A gate nobody could run reads exactly like a gate nobody got round to
`ROADMAP.md` §5 gated the whole onboarding phase on an onboarding question-class in the
tokens-to-answer harness. Three milestones shipped and the file held zero of them, which the backlog
recorded as *not yet done*. The actual blocker was one line: `bind_tools` never bound
`architecture_overview`, `guided_tour` or `generate_onboarding`, so **no onboarding question could have
been written and run at all** — the recipe vocabulary had no word for the subject. "Unmeasured" was
carrying "unmeasurable with what we built", and nothing in the plan distinguished them.

The second half is the same shape one layer in. Once the questions ran, the recall gate scored **0**
on every onboarding answer, because `found_expected_members` read identities from `results` and an
onboarding answer keys its members on `layer` / `module` / `pattern`, under `modules` or nested in
`summary`. With a shorter `expected_set` that would have been a **green gate that measured nothing** —
the 127 lesson (assert the rendered output, not the shipped bytes) with a scorer in place of a renderer.

And the verdict itself is the useful artifact, in the direction nobody plans for: the class is cheap and
correct where the question is a lookup, and **wrong** where it is a reading order — `guided_tour`'s
first five stops on `symfony/demo` are a lint config, two bootstrap configs and an importmap. §5 had
promised, in writing, to narrow the scope if that happened, and that promise is the only reason the
narrowing was cheap to make.

### 121-C1 — A measurement deferred may be a measurement whose instrument cannot address its subject
- type: 2 generalisable-heuristic
- handle: instrument-cannot-address-its-subject
- status: proposed (awaiting human confirm)
- seen: 121
- evidence: §5 named this gate for three milestones and the harness could not bind any of the three
  tools it was meant to measure; the backlog read this as unfinished work, not as an unrunnable gate
- area: benchmarks / harness / planning
- destination: stays in `lessons_path` until a second sighting — one occurrence, and the check it
  implies (before scheduling a measurement, confirm the harness can address the subject) is cheap
  enough to state without a rule

### 121-C2 — Recall and cost cannot see precision: an over-inclusive answer scores 1.0
- type: 2 generalisable-heuristic
- handle: recall-and-cost-cannot-see-precision
- status: proposed (awaiting human confirm)
- seen: 121
- evidence: the `web_entry` bucket calls 8 files the web surface on `symfony/demo` when 4 are
  `tests/Controller/*Test.php` (ticket 130). Every hand-established member is present, so recall is
  1.0, `confidently_wrong` is 0 and the cost ratio is unaffected — the harness scores a wrong answer
  as a perfect one, by construction
- area: benchmarks / payload honesty
- destination: stays in `lessons_path` — recorded as a **named gap in the instrument** in
  `docs/benchmarks/121_onboarding-question-class.md`; a precision metric is a ticket, not a rule

### 121-C3 — new sightings of existing classes, recorded as `seen:` bumps
`derived-not-listed-invariant` (rec 12 → **13**, already **R6.7**) gains 121: the recall scorer now
recurses the payload and derives the collection its members live in instead of naming `results`.
`prove-the-guard-fails` (rec 9 → **10**, already **R6.5**) gains 121: the guard was run at `HEAD` in a
scratch worktree first and failed **4 of 7** — no class, three tools unexercised, no stated exclusions,
and the recall scorer returning `[]`. `fixture-shape-begs-the-question` (rec 6 → **7**, still never
proposed) gains its sharpest sighting yet: the committed fixtures are 2–4 flat files, so an onboarding
question asked against them gets a degenerate answer — one layer, no hub, no declaration — and the
measurement would have flattered the tool while locking in nothing. That handle is now at recurrence 7
with no rule proposed.

## 126/127 — A guard that reads the shipped file instead of the rendered output is green forever
The onboarding page embeds its whole dataset as a JSON block, so `caveat in html` is true for every
caveat the dataset carries **whether or not the page ever renders it**. The first formulation of 127's
guard would have passed on day one and every day after. Rewritten to run the page under `node` and
read the rendered sections, it failed immediately on the real drop (`['reachability']`). Same shape as
116's own finding: a grep over an HTML page whose content is built in the browser sees zero rendered
figures.

### 127-C1 — A guard over a generated artifact asserts the RENDERED output, never the artifact bytes
- type: 2 generalisable-heuristic
- handle: guard-asserts-rendered-not-shipped-bytes
- status: proposed (awaiting human confirm)
- seen: 116, 127
- evidence: 116 made `node` a test dependency because a grep over the HTML would be a false green;
  127's file-level formulation of the caveat guard is green by construction, the rendered one caught
  the drop on its first run
- area: onboarding / artifact / guards
- destination: `rulebook_path` (code subject) — recurrence 2 across 116 and 127, **promotable**: run
  `/mango:promote` for the handle above

### 127-C2 — new sighting of an existing class, recorded as a `seen:` bump, not a fresh claim
`derived-not-listed-invariant` (rec 11 → **12**, already **R6.7**) gains 127: the caveat set the guard
iterates is derived from the dataset payload, so caveat N+1 is covered the moment it exists. The class
index's own instruction is that a new sighting bumps `seen:` rather than re-deriving the rule.
`source-the-caveat-from-the-computation` (rec 4 → **5**, already **R5.5**) gains 127 as well: the
declaration caveat now rides on the split that computes the declared counts, and `path_index.caveat` is
sourced where the cap is decided rather than re-worded by the renderer.

### 126-C1 — Ranking must precede truncation wherever a page is cut, tool payload or artifact
- type: 2 generalisable-heuristic
- handle: rank-before-truncate
- status: proposed (awaiting human confirm)
- seen: 067, 126
- evidence: 067 fixed it for `find_callers` and added `result_subtrees`; 126 found the same defect
  unmitigated in the map's search palette, beside the mirror panel that exists to prevent the failure
  it caused. (123 is *not* counted here — its claim is `total_count` semantics, not ranking.)
- area: tools / onboarding / payload honesty
- destination: `rulebook_path` (code subject) — recurrence 2 across 067 and 126, **promotable**: run
  `/mango:promote` for the handle above

## 125 — Schema version names the index, not the server that read it
``get_index_status`` reported ``contract_version`` and ``schema_version`` — both describe the
database shape, unchanged since task 063 — while round 6 identified the running build by reading
task numbers out of tool docstrings. The fix adds ``server_version`` + ``server_build`` on status
(standard/verbose) and ``server``/``build`` on signed claims, derived from git or package content.

### 125-C1 — Server identity is orthogonal to contract/schema version
- type: 2 generalisable-heuristic
- handle: server-identity-orthogonal-to-schema-version
- status: proposed (awaiting human confirm)
- seen: 125
- evidence: round-6 retro could not answer §0.a; closed by ``build_info.server_identity`` +
  ``field-retro.md`` §0.a
- area: tools / evaluation / provenance
- destination: `rulebook_path` (code subject) — recurrence 1, not yet promotable

## 124 — A walk budget named for another tool is a cap on what you can ever see
`find_orphans` passed `impact_max_nodes` into the reachability walk, so changing impact's knob changed
which orphans existed in the answer — and the 500-row cap decided visibility with no `offset` to look
further. At 19k files the `standard` payload blew the transport limit (154k chars). The fix splits
concerns: page rows with `limit`/`offset`, walk with `CA_ORPHANS_MAX_NODES`, and `minimal` that omits
`unproven` rows while `unproven_total` carries the count. Review added the corollary: once rows
page, `truncated` must describe the page alone — the walk's own budget is `walk_truncated`, or the
pager never stops on the very repo the ticket is about.

### 124-C1 — A tool's walk budget must be named for that tool, not borrowed from a sibling
- type: 2 generalisable-heuristic
- handle: walk-budget-named-for-the-tool-that-walks
- status: proposed (awaiting human confirm)
- seen: 124
- evidence: `find_orphans.py` used `config.impact_max_nodes`; closed by `CA_ORPHANS_MAX_NODES` +
  AC3 tests proving impact knob independence
- area: tools / config / reachability
- destination: `rulebook_path` (code subject) — recurrence 1, not yet promotable

## 123 — When `total_count` names the page, a truncated symbol map reads as complete
`file_outline` set `total_count=len(results)`, so a 12-symbol file at cap 10 returned
`total_count: 10` beside `truncated: true` — the worst shape for a tool whose docstring calls
itself "the symbol map". The fix is the same contract the other list tools already carry: store-side
count, `limit`/`offset`, and a spread field when the page hides part of the answer.

### 123-C1 — `total_count` is the true total everywhere it appears, never the page length
- type: 2 generalisable-heuristic
- handle: total-count-is-the-true-total-not-the-page
- status: proposed (awaiting human confirm)
- seen: 123
- evidence: `file_outline.py` used `total_count=len(results)`; closed by `count_nodes_by_file` +
  `tests/test_total_count_semantics.py` enumerating every emitter
- area: tools / payload honesty
- destination: `rulebook_path` (code subject) — recurrence 1, not yet promotable

## 122 — A shaper that keys on a count two statuses share will mis-file the one it was meant to honour
`classify_missing_subject` returns `resolved_unique` with `candidate_count: 1` and `ambiguous` with
`candidate_count > 1`. `shape_exact_miss` treated any positive count as `name_not_qualified`, so the
unique case — the one the classifier had already resolved — was discarded and the stored qname never
reached the four `find_*` tools. 075 had recorded a sibling-surface verdict in prose while those four
callers still hit the fall-through; the enumerating test is what actually closes it.

### 122-C1 — Branch a miss-shaper on classifier status, never on a count several statuses share
- type: 2 generalisable-heuristic
- handle: branch-on-status-not-shared-count
- status: proposed (awaiting human confirm)
- seen: 122
- evidence: `shape_exact_miss` (`nav_result.py`) fell through `if resolution.candidate_count` for
  `resolved_unique` (which carries count 1) and emitted `name_not_qualified`. Fixed by branching on
  `status == "resolved_unique"` first; `unique_repoint` is the one predicate the four `find_*`
  retries share
- area: tools / subject resolution
- destination: `rulebook_path` (code subject) — recurrence 1, not yet promotable

### 122-C2 — A sibling-surface verdict is closed by an enumerating test, not by a scope bullet
- type: 2 generalisable-heuristic
- handle: enumerating-test-closes-the-sibling-surface
- status: proposed (awaiting human confirm)
- seen: 122
- evidence: 075's scope bullet "decide and record the sibling surface" was marked done while
  3/7 classifier callers honoured `resolved_unique`. The defect survived two field rounds. Closed
  by `test_every_classifier_caller_honours_resolved_unique`, which derives the caller set from
  `classify_missing_subject(`
- area: process / inventory close
- destination: `agent_brief_path` (process subject) — recurrence 1, not yet promotable

## 117 — Three lessons about seams and bounds
**A seam can be live code and still fire on nothing, because a later ticket moved the ground.**
091 built a `LayerRefiner` that renames the **weak** layers 084 falls back to
(`source`/`sink`/`mixed`/`isolated`/`(root)`). 110 then made `responsibility` the primary layer
method, naming every layer from a path vocabulary — measured on all three pinned repos, **zero weak
layers**, so the rename seam matches nothing on a normally-shaped repo. Nothing broke and no test
failed; the gate for a seam's *usefulness* was never a test. 117 then proposed routing per-layer
descriptions through it, which would have delivered prose for zero layers. **Fix:** before extending
a seam, measure how often the existing one fires — reachability is a property of the whole pipeline,
so it decays silently when an earlier stage changes. Same class as 107's stale evidence, one level
up: there the *evidence* decayed, here the *mechanism* did.

**Where a guard lives decides how many copies of it you own.** The ticket asked for prose in three
slots (layer, tour step, headline) and named two routes. Each slot needs the same four guards —
reject filler, degrade on failure, memoise, stay under a call ceiling — and the ceiling in
particular is **wrong** when duplicated: two half-budgets are not one budget. One `ProseWriter`
Protocol with one method put each guard in exactly one place. **Fix:** count the guards before
choosing the seam count; if N routes need the same guard, the guard is telling you how many
abstractions there should be. A shared *budget* is the strongest such signal.

**A cap you cannot show biting is not evidence that it works.** The 33-call prose ceiling is derived
from existing caps and every realistic repo lands under it — the three pins cost 12–25, an
18,929-file synthetic cost 24 — so the whole cost report was green **without the ceiling ever
engaging**: it proved the arithmetic, not the enforcement. One row whose paths name no
responsibility (084 falls back to unbounded per-directory layers) produced the number that matters:
**1,176 requested, 12 served, 1,164 refused.** **Fix:** a bound needs a case on each side of it.

## 116 — Two lessons about assertions over a generated page
**"No literal numbers" cannot mean "every displayed figure moves".** AC4 asked for a test that
mutates the dataset and checks every displayed figure moved. Written literally it fails on correct
code: the layer count, node-kind count, bucket count and prune threshold are read from the dataset
yet **scale-invariant**, and a percentage is a ratio. Weakening it to "most figures moved" would
have made it unfalsifiable. **Fix:** split where the semantics split — a **static** half that strips
style and script and asserts no digit survives in the template's visible text, and a **behavioural**
half scoped to figures of four digits or more, where the scoping is what makes it exact: at four
digits a figure *is* a count, so it must move. The same reading deleted the prototype's numbered
section badges.

**A fixture that exercises a threshold must sit on the realistic side of it.** Two size measurements
of the same page disagreed by 2×, both "correct". The hand measurement used 12 symbols per file; the
fixture used 199, putting **every** directory over `DIR_SYMBOL_THRESHOLD` and growing the directory
tree from 167 rows to ~5,399. A second fixture named no responsibility in its paths, so layer
assignment fell through to structural grouping and produced **102 layers and a 10,404-cell matrix** —
no real repo's shape — leaving the size budget passing by **1,490 bytes**. **Fix:** derive the
fixture's shape from a measured repo, not round numbers, and keep one definition of it: the test now
imports the generator from the committed report script, so the number asserted is the number the
script prints. A pass by luck and a pass by construction look identical in the output.

*(116's own headline — a 31 MB page that measured 921,746 B by the time it was worked — is the
`re-verify-the-assumption-on-a-new-path` class; see 107, where it is recorded.)*

## 115 — Two lessons about prose and examples in a ticket
**Explaining an R2-tainted prototype in a comment reintroduces the taint the code avoided.** Twice
running, the R2.2 grep-gate fired on my own prose rather than on code: 114's docstring named a pinned
public repo to explain a measurement, and 115's module docstring explained the mockup by
**reproducing its regex, its tree prefix and its region names** — the exact literals the
implementation had gone to trouble to avoid. Both times the code was clean and the comment was the
violation. The mechanism is counter-intuitive: the more carefully a module avoids a tainted pattern,
the more its author wants to explain what it avoided, and the natural way to do that is to quote it.
**Fix:** describe a rejected pattern by its **shape** — "one hardcoded tree prefix and two region
names" carries the whole lesson and trips nothing. *Falsifier:* a comment containing a string that
would fail the gate if it appeared in code. This is 003 recurring at a new site (a grep-gate reads
prose as input), now across two ticket keys.

The corollary: **widening a gate pays off on the ticket after it lands, not eventually.** 113 widened
R2.2 from `adapters/` to `code_atlas/` because 113 put a path-shape classifier in the core. It then
caught 114 and 115 — both mine, both in comments, neither suspected. Widen a gate the moment its
subject moves into scope; the first violation it catches is likely to be the one you are writing.

**An acceptance criterion's example fixture can contradict the sentence it illustrates.** AC1 read "a
fixture with `a/x`, `a/y`, `b/x` reports one shared path and one on each side". Those three paths
cannot: they give one shared, one on the left, and **none** on the right. Compare 114, where AC1's
two-module fixture could not clear the threshold AC5 required on a real repo. Twice the prose stated
the requirement correctly and the illustration under-specified it. *Fix:* treat the **sentence** as
the requirement and the example as a sketch, then assert both. *Falsifier:* a test whose fixture
matches an AC's listing while asserting something weaker than the AC's sentence.

## 114 — Measure the real trees before choosing a threshold, and put the accessor where the check needs it
The three pinned repos are already cloned under `artifacts/cross-repo-cache/`, so the candidate-module
rule was measured against real directory shapes **before** the design was written. That ordering
changed the design twice: a file-count floor (the prototype's `files >= 8`) cannot separate a
library's 10-file `Exception` directory from a business module, so the decision moved to a **peer
count**; and one pin's widest container turned out to be organised by *responsibility* (4 of 7
children are role words), so a table built from it would have listed `Controller`, `Entity` and
`Form` as business capabilities. *Fix:* when a rule is a threshold over path shape, run it over every
real tree available before writing the design — a fixture authored afterwards agrees with whatever
threshold you picked. Generalises `fixture-shape-begs-the-question` from "add a real-repo check" to
"let the real repos choose the constant".

**Where an accessor lives.** 113 added `responsibility_layer(module)`; 114 needed the same question
about a **bare directory name** and got `None` for every one, because the accessor treats its
argument as a module path and drops the final segment as a filename. Every role-organised container
would have passed the new gate and shipped its role directories as business modules. The accessor was
correct for its own caller and wrong for the next. *Fix:* when a check needs a different **grain**
(segment vs path, row vs table, node vs file), add an accessor at that grain beside the first — do
not reshape the argument and do not reach into the private it wraps. *Falsifier:* a call site that
massages its input into the shape an accessor expects (`f"{name}/x"`).

*(114's third finding — the widened R2.2 gate catching its own docstring — is recorded with 115.)*

## 113 — A field the contract declares but no adapter emits is a false-zero source, not a signal
Three traps, all avoided by checking producers rather than declarations.

**A declared field with no writer.** `nodes.is_test` is a contract field (`contract.py:86`), exactly
semantically right, with a store column — and **no adapter emits it**. Every row is the DDL default
`0`, so a test bucket keyed on it would render **0** on the anchor's 1,776 test files and push all of
them into the dead-code-suspect bucket: a false accusation produced by a field that "exists".
*Fix:* grep for a contract field's **producers** before keying behaviour off it. Generalises to every
optional field — the DDL default and "not applicable here" are indistinguishable downstream.

**Keying off a name a later seam may rewrite.** Reading `LayerAssignment.layers` for `"Tests"` would
have been silently emptied by the 091 `LayerRefiner`, whose whole job is renaming layers — and since
it is off by default, CI would stay green forever. *Fix:* key off the **pure input**
(`responsibility_layer(path)`), never the post-seam output. When a seam exists to transform X, no
other consumer may treat X's pre-transform values as stable.

**A ratified judgment is reusable inventory.** 113 expected to need a new vendor signal (Composer
autoload parsing) or an honest three-bucket fallback. 110 had already ratified a 36-word
responsibility vocabulary as an **R2.2 standard**, containing every word 113 needed. *Fix:* before
building a signal to satisfy a constraint, search for a previously ratified answer to that same
constraint.

## 107 — Re-measure a ticket's evidence before designing from it; a sibling may have already moved it
107 was filed from the same run as 106 and claimed **500/500** onboarding pages had empty neighbour
lists. By the time it was worked, 106 had shipped and the true figure was **0/500** — and its AC2,
which named that repo as the proving ground, would have passed with no code change at all. Re-measuring
first both saved the false-green and relocated the defect: `laravel/laravel` still emitted a
contentless page for **20 of its 26** modules, `symfony/demo` for **7 of 51**. The fix suppresses a page
only where the module is *provably* contentless (full-graph degree 0 **and** no summary) and keeps the
page where the **budget** hid the neighbours, stating the count it cannot show.

No new claim — three `seen:` bumps, recorded in the claims themselves:
`ac-failure-mode-needs-the-right-guard`, `re-verify-the-assumption-on-a-new-path`,
`do-not-attest-past-the-payloads-resolution`.

## 106 — A budget whose intake is unranked buys the alphabet, and a pinned-repo suite can be blind to the ratio that breaks it
`tour_subgraph` seeded with `ORDER BY file_path LIMIT <whole budget>`. On a repo with 8,477
zero-inbound files against a 500-node budget the seed list *was* the budget: `_tour_expand` never
traversed one edge, so every tour stop read `entry point (zero inbound)`, every generated module page
had empty neighbour lists, and the admitted 500 were whatever sorted first in ASCII — a vendored
framework and legacy view templates, while the two trees holding 10k modules never appeared. Two
selection rules fixed it: rank intake by **out-degree**, and cap seed intake at **a quarter** of the
budget so the second phase has room. The three pinned public repos could not have caught this: their
entry counts (23/30/9) sit under the cap, so their tours came back **byte-identical**.

No new claim — three recurrences recorded where they already live: the unranked cap is **067** one
layer down (third instance); the pinned suite being green on both sides of a real defect bumps
`fixture-shape-begs-the-question` (**105-C2**) — a cross-repo suite can be blind to a *ratio* (entry
points ≫ budget), not only to a path shape; and measuring the costlier design before keeping it
(6.125 s of a 10.096 s call for an inbound half that fed nothing, against a byte-identical subgraph
at 5.969 s from one out-degree signal) is 067's kill gate earning its place again.

### 106-C1 — `ruff format` over a whole file is scope, not compliance, when CI only runs `ruff check`
- type: 1 technical-fact
- handle: format-churn-is-scope
- status: proposed (awaiting human confirm)
- seen: 106
- evidence: `.github/workflows/ci.yml` runs `ruff check .` and `mypy`, never `ruff format --check`.
  A `ruff format code_atlas/store.py` pass to settle two long lines reformatted **204 unrelated
  lines**, inflating a +67/−26 diff past the approved change list; the file was restored and the
  change re-applied by hand.
- falsifier: a diff carrying formatter-only hunks in files the ticket did not otherwise touch, in a
  repo whose CI does not enforce the formatter
- area: change discipline / diff scope
- destination: `gotchas_path` — **note: `docs/gotchas.md` does not exist yet**; ratifying this
  claim creates it rather than adding to it (not created unilaterally)

## 105 — Elect "the main subtree" by graph mass, not file count; make the real-repo check committed
104's dominant-subtree heuristic elected the top-level directory holding the most **files**. On the
`laravel/laravel` skeleton `config/` (10 flat settings files) out-counted `app/` (3 connected source
files), collapsing the whole application into one layer — the very F1 shape 104 existed to fix. Elect
by **graph mass** (Σ fan_in+fan_out) instead, so a populous-but-disconnected directory cannot
out-vote a small connected core: no directory stop-list (R2.2), no language branch (R1.1), still
deterministic. Separately, this is the 5th time an authored fixture mirroring the code's own
assumption hid a path-shape defect; the durable countermeasure is a **committed, re-runnable
real-repo reporter** (`scripts/layer_report.py`), not an ad-hoc session action.

### 105-C1 — Elect a "dominant" group by connectivity mass, not by member count
- type: 1 technical-fact
- handle: elect-by-graph-mass-not-file-count
- status: proposed (awaiting human confirm)
- seen: 105
- evidence: `code_atlas/onboarding/layers.py::_dominant_subtree` sums `fan_in + fan_out`;
  `tests/test_onboarding_layers.py::test_dominant_subtree_survives_a_config_dir_with_more_files` is
  red on the count rule, green on mass; three real repos in 105's working doc (AC2)
- area: onboarding layer assignment / graph heuristics
- destination: `gotchas_path` (a design fact about this heuristic, not a build rule)

### 105-C2 — When AC needs a real-repo judgement, ship a committed reporter, not an ad-hoc run
- type: 2 generalisable-heuristic
- handle: fixture-shape-begs-the-question
- status: proposed (awaiting human confirm)
- seen: 084, 103, 104, 086, 105, 106
- evidence: authored fixtures hid the same class of path-shape defect across 084/103/104/086; 105 adds
  `scripts/layer_report.py` (clones+indexes the pinned repos, prints `assign_layers`) as the committed
  real-repo check
- area: test design / heuristics judged on real inputs
- note: `seen:` crosses ≥2 ticket keys → this is a **cross-ticket promotion candidate**
  (`/mango:promote`, run by the maintainer between tickets), not a within-ticket write
- destination: `rulebook_path` (a heuristic over path/graph shape must be proven on a real indexed
  repo, via a committed re-runnable check — a fixture that shares the code's assumption cannot)


## 091 — Constrain a seam's return type so a bad implementer can't break a core invariant
091 lets an LLM rename architectural layers. The obvious seam shape — `refine(assignment) -> new
assignment` — would let a hallucinating impl drop modules, invent layers, or scramble ranks, and the
core would have to defensively re-validate everything downstream. Instead the `LayerRefiner` seam
returns a **rename map** `{old_layer: new_layer}`; the core applies it. The narrow return type makes
the dangerous outcomes *unrepresentable* — coverage, module→layer membership, and dependency order are
preserved by construction, no matter what the LLM says. The applier only renames and renormalises
ranks; an empty/inapplicable map returns the input object unchanged (the off path is byte-identical to
the heuristic — AC3, proven with `to_json()` equality).

### 091-C1 — Make a seam return the delta, not a rebuilt whole, when a bad impl could corrupt invariants
- type: 2 generalisable-heuristic
- handle: seam-returns-constrained-delta-not-rebuilt-whole
- status: proposed (awaiting human confirm)
- seen: 091
- evidence: `code_atlas/onboarding/layers.py::refine_layers` applies a `{old: new}` map from
  `LayerRefiner.refine_names`; `tests/test_onboarding_llm_layers.py::test_llm_renames_weak_layers`
  asserts coverage is intact and `::test_off_by_default_is_byte_identical_to_084` pins AC3
- area: seam design / untrusted (LLM) implementers behind a Protocol
- destination: `rulebook_path` (R1.2/R7.4-adjacent — a seam whose impl may be an LLM should make
  invariant-violating outputs unrepresentable rather than re-validating them)


## 090 — "The core must never import X" is honoured most strongly by an entry point outside the core
R4.1 says the core must never import an LLM. A config-gated deferred `import onboarding_llm` inside
`main.py` would satisfy CI (the import never fires) but still *names* the LLM package in core source.
090 instead widened the core seam to `build_server(config, summarizer=None)` — the core names only the
085 `Summarizer` *type* — and put the injection in a **separate `code-atlas-llm` entry point outside
`code_atlas/`**, so the core→LLM edge is literally absent. A filesystem confinement test greps
`code_atlas/**` for any `import anthropic`/`onboarding_llm` and finds none. Mirrors how adapters live
outside the core with their own launch.

### 090-C1 — A "never import X" rule wants an out-of-core entry point, not a deferred in-core import
- type: 2 generalisable-heuristic
- handle: plugin-entry-point-keeps-the-core-import-clean
- status: proposed (awaiting human confirm)
- seen: 090
- evidence: `build_server(config, summarizer=None)` threads the seam; `onboarding_llm/server.py:run`
  injects the LLM impl; `tests/test_onboarding_llm.py::test_no_core_module_imports_an_llm` proves
  `code_atlas/**` names neither `anthropic` nor `onboarding_llm`
- area: seam placement / optional plugins
- destination: `rulebook_path` (R4.1-adjacent — where the injection of an out-of-core impl lives)


## 089 — An HTML file that must open from `file://` cannot fetch a sibling JSON
`generate_onboarding` already wrote `manifest.json`. A viewer that `fetch`ed it would pass in a
dev server and fail the moment a human double-clicked the file — the AC is "opens offline from
the filesystem". The HTML therefore **embeds** the artifact at generate time. `connect-src 'none'`
makes a later fetch a CSP violation rather than a silent `file://` miss.

### 089-C1 — Offline HTML cannot treat a sibling JSON as a runtime input
- type: 2 generalisable-heuristic
- handle: embed-what-file-cannot-fetch
- status: proposed (awaiting human confirm)
- seen: 089
- evidence: browsers block `fetch('./manifest.json')` on `file://`; 089 bakes `viewer_payload` into
  a `<script type="application/json">` tag and forbids connect
- area: generated static HTML
- destination: `rulebook_path` (R4.2/R1.2 adjacent — a generated artifact must actually be usable
  in the environment the ticket named)


## 088 — A listed `CALLS` tuple is a tool-surface pin even when `TOOL_NAMES` already grew
`test_mcp_server.CALLS` is the argument list that drives the per-tool `detail_level` contract tests.
087 registered `guided_tour` in `TOOL_NAMES` but left it off `CALLS`. 088 had to add
`generate_onboarding`
there and folded `guided_tour` in as proof collateral. Same class as 085-C1 / 087-C1 (a listed integer
or listed subset that is the live surface).

## 089 (review round) — The one line standing between a repo's filenames and a script breakout had no test
`render_viewer` escapes `<` in the embedded JSON, and it is right to: a directory named `a<` holding a
file `script>x.aa` makes the *path string* carry `</script>`, which ends the payload block and leaves
the rest of the artifact as live markup in a committed HTML file. The page's CSP does not save it —
`script-src 'unsafe-inline'` permits inline handlers, and `img-src 'none'` guarantees an
`<img onerror>` fires. Deleting the line kept the whole suite green, so nothing but reviewer memory
stopped a future edit from removing it. Also: with scripting off the "offline viewer" rendered a blank
page and never mentioned the markdown beside it.

### 089-C2 — A page that builds every element in script must say what to read when script is off
- type: 2 generalisable-heuristic
- handle: degrade-to-the-artifact-beside-you
- status: proposed (awaiting human confirm)
- seen: 089
- evidence: the AC says "opens offline from the filesystem"; with scripting disabled the viewer showed
  nothing, while `overview.md` and `tour.md` sat in the same directory. Fix: a `<noscript>` block naming
  them — and the project's no-language pin rejected the first wording, which said "JavaScript"
- area: onboarding artifacts
- destination: `rulebook_path` (alongside R5's degradation rules)

## 088 (review round) — A generator that owns a directory must delete only what it recorded writing
`_write` cleared its output with `shutil.rmtree(docs/onboarding/modules)`. That is correct for the
pages it wrote and destructive for everything else: a hand-authored page in the same tree vanished, and
a pre-existing `docs/onboarding/overview.md` was overwritten, from any agent call. The fix makes
ownership explicit and *recorded* — the previous `manifest.json` is the delete list, and a tree holding
these filenames without that manifest is refused. Second finding, same shape as 087's: the committed
`overview.md` counted every module while only the budgeted stops had pages, and said nothing about it.

### 088-C1 — A tool that writes into a repo may only remove paths its own last manifest recorded
- type: 2 generalisable-heuristic
- handle: own-only-what-you-wrote
- status: proposed (awaiting human confirm)
- seen: 088, 089
- evidence: `shutil.rmtree(out / "modules")` deleted `modules/HAND_WRITTEN.md`; a foreign
  `docs/onboarding/overview.md` was replaced by generated bytes. Fix: `recorded_pages()` +
  `_remove_recorded_pages` + `_refuse_foreign_tree`; hostile recorded paths (`..`, absolute, outside
  `modules/*.md`) are dropped rather than unlinked. Same rule 050 applied to the index database
- area: tools that write to disk
- destination: `rulebook_path` (R5's degradation section says nothing yet about *destructive* writes;
  `/mango:promote` is the cross-ticket pass)

## 087 (review round) — A bounded walk from entry points is not the codebase, and `truncated: false` claimed it was
Four defects, all found on the PR, all reproduced before the fix. The two that matter are one class:
a payload that cannot distinguish *complete* from *cut short*. A component no zero-inbound file
reaches (it must hold a cycle) was silently absent with `truncated: false` and a `total_count` of only
the reachable part — a 3-file index answered with 1 stop; and the surviving member of a budget-cut
cycle was labelled `entry point (zero inbound)` when the store had proved no such thing. The other two
are robustness: recursive Tarjan died with `RecursionError` once `CA_IMPACT_MAX_NODES` admitted a chain
deeper than the interpreter limit (~1200), and a capped `results` page had no `offset`, so the tail of
a reading order was unreachable — the convention 086 had established one ticket earlier.

### 087-C3 — A recursive graph walk inherits the interpreter's depth limit as a silent input bound
- type: 2 generalisable-heuristic
- handle: bound-the-recursion-or-make-it-iterative
- status: proposed (awaiting human confirm)
- seen: 087
- evidence: recursive Tarjan in `onboarding/tour.py` raised `RecursionError` at 1200 nodes; the tool's
  own budget knob `CA_IMPACT_MAX_NODES` is user-settable with no ceiling, so raising it turned a
  bounded answer into a crash. Rewritten with an explicit work-stack; probe at 1500 nodes
- area: core graph algorithms
- destination: `rulebook_path` (near R4.3 — the sibling of "never load the whole graph" is "never
  recurse per node")

## 087 — A listed `len(descriptions) == N` is a surface count-pin even when it never names `TOOL_NAMES`
Design grepped `TOOL_NAMES ==` and `all 15 tools` and still missed `tests/test_tool_descriptions.py:50`
(`assert len(descriptions) == 15`). Execute folded it as proof collateral of registering the 16th
tool and derived the pin (`set(descriptions) == set(TOOL_NAMES)`). Same class as 085-C1 (count-pin)
and R6.7 (derive the set).

## 085 — A count-pinned guard is a blast-radius hit, and an AC phrased as a failure mode needs a guard that can exhibit it
The Gate-2 blast-radius trace confirmed the two grep-gates *glob* the new module
(`CORE.rglob("*.py")`) but missed that they also **count-pin** the module total
(`len(core_modules()) == 44`); execute caught the 44→45 bump as a 2-file deviation. Separately, AC2
was phrased as a failure mode ("would fail if presentation read the graph directly") while the
presentation function structurally *cannot* reach the graph — so the fake-summarizer test actually
guards a different boundary (enrichment routes through the seam), and R6.5 still wanted the guard
*observed* failing rather than argued.

### 085-C1 (also filed as 087-C1, and as 088-C1 in the 088 ticket) — A count-pin or listed subset of a live surface is a blast-radius hit for anything added to that surface
- type: 2 generalisable-heuristic
- handle: count-pin-in-blast-radius
- status: proposed (awaiting human confirm)
- seen: 085, 087, 088, 089
- evidence: the Gate-2 trace saw `test_core_is_language_agnostic` / `test_sql_confinement` glob
  `CORE.rglob("*.py")` — auto-covering the new module — but missed their
  `assert len(core_modules()) == 44`; the 44→45 bump landed as a recorded 2-file deviation rather
  than in the approved change list (085). A design grep for `TOOL_NAMES ==` and `all 15 tools` still
  missed `tests/test_tool_descriptions.py:50`'s `len(descriptions) == 15`; execute derived the pin
  as `set(descriptions) == set(TOOL_NAMES)` (087). `test_mcp_server.CALLS`, a listed *subset* of
  `TOOL_NAMES` that drives the per-tool `detail_level` contract tests, omitted `guided_tour` after
  087 registered it (088)
- area: analysis/design blast-radius tracing
- destination: `agent_brief_path` (process subject). Recurrence 4, never proposed — three of the
  four sightings were filed under separate ids, which is exactly the under-count `PROM-C1` names

### 085-C2 — An AC phrased as a failure mode needs the guard that can actually exhibit that failure
- type: 2 generalisable-heuristic
- handle: ac-failure-mode-needs-the-right-guard
- status: proposed (awaiting human confirm)
- seen: 085, 107
- evidence: 085's AC2 read "would fail if presentation read the graph directly", but
  `summaries_as_dict(summaries)` has no parameter reaching the graph — that failure mode is guarded
  *structurally* by a different test, while the fake-summarizer test guards that enrichment routes
  through the seam. Reviewer (PR #124) flagged the framing mismatch and the absent R6.5 red run;
  fixed by splitting the claim into two named guards and recording a sabotage run. 107 extends it
  from the *test* to the *repo*: its AC2 named the anchor monorepo, where 106 had already removed
  every contentless page, so the AC would have passed with **zero** code change — amended at Gate 1
  to the repos that still exhibit it (`laravel/laravel` 20 of 26, `symfony/demo` 7 of 51).
- area: tests / AC decomposition / R6.5 (prove-the-guard-fails)
- destination: `rulebook_path` (if it recurs — code subject; seen once, stays in lessons)

## 084 — Piping the Docker gate through `tail` reports the pipe's exit, masking a ruff/mypy failure
The gate `docker-test.sh` runs `ruff check . && mypy code_atlas && pytest -q`, which fails correctly on
a ruff error. But run as `bash scripts/docker-test.sh 2>&1 | tail -N`, the shell reports the exit status
of `tail` (0), not of the gate — so a run with `ruff … Found 10 errors` still surfaced as
`[exited with code 0]`. The green was only visible because the run was judged by its **output content**,
not the pipeline exit code. In an unattended run this is a false-green hazard: a red gate can read as
passed. Judge a piped gate by its content (`Success: no issues …`, `N passed`, ruff silent-on-success),
or drop the pipe so the real exit code propagates.

*Claim `084-C1` — Judge a piped command's result by its output, not the pipeline's exit status. type
4 gotcha · area: workflow / running the Docker gate on a non-Linux host · seen 084 · proposed ·
`gotchas_path` (recurrence 1 — recorded, not yet promotable).*
*Evidence: `bash scripts/docker-test.sh 2>&1 | tail -20` printed ruff's `Found 10 errors` then
`[exited with code 0]` (tail's exit). The ruff failure was caught by reading the content, not the
status. `&&`-chained gate → ruff failing stops the chain, but the pipe hides that..*

## 102 — The fix for "a resolvable subject reported as absent" reintroduced it, one argument over
`seeds_dropped` was documented as the field separating a modelled zero from a failed query, but was
**assigned in exactly one place** — the store's budget prune. A subject the tool could not resolve
was never counted, so the ticket's named root cause (the empty-seed early return) was only the
second half of the hole. **Then the fix repeated the bug in miniature:** the new `qnames` loop
guarded `classify_missing_subject`'s `resolved_unique` and the new `paths` loop did not, so a
path-slot subject that re-pointed to a real qname was counted **lost** and labelled
`name_not_qualified` with `candidate_count: 1`. Gate 2 had recorded that exact hazard as
**assumption 3 — verified**; it was verified for the path that existed and asserted for the path the
same change added. **Found by the reviewer, not by me**, and confirmed by measurement before it was
accepted: `qnames=["App\Nope"] → results=2 seeds_dropped=0` beside
`paths=["App\Nope"] → results=0 seeds_dropped=1 reason=name_not_qualified`.
### 102-C1 — An assumption is verified for the paths that existed when it was checked
- type: 2 generalisable-heuristic
- handle: re-verify-the-assumption-on-a-new-path
- status: proposed (awaiting human confirm)
- seen: 102, 107, 122
- evidence: Gate 2 assumption 3 (*"a `resolved_unique` resolution can never reach
  `_explain_lost_subject`"*) was true of the `qnames` loop it was read against and false of the
  `paths` loop the same change introduced; a spike confirmed the mislabelling
  (`classify('Nope') -> resolved_unique … shape={'reason': 'name_not_qualified'}`) and the design
  cited it as the reason the branch keys on `status` — for one caller (102). 107 generalises it from
  *paths* to *time*: its counted evidence ("500/500 pages have both neighbour lists empty") was
  measured before its sibling 106 landed and read **0/500** at `f3d48a9`, so refine re-measures a
  ticket's numbers rather than inheriting them
- area: process / design assumptions
- destination: `agent_brief_path` (process subject) — **recurrence 3** (102, 107, 122), promotable;
  never proposed

### 102-C2 — Two call sites consuming one classifier need one shared rule, not two copies
- type: 2 generalisable-heuristic
- handle: one-rule-for-every-subject-slot
- status: proposed (awaiting human confirm)
- seen: 102, 122
- evidence: `impact._seeds` grew a second subject slot; the guard was written twice and one copy was
  wrong. Fixed by a single `take()` both slots call, so they cannot drift apart again. The same
  shape exists in `read_symbol.py:189` and `find_callers.py:168`, which each branch on
  `resolution.status == "resolved_unique"` independently
- area: tools / subject resolution
- destination: `rulebook_path` (code subject) — **recurrence 2** (102, 122), promotable

*Claim `102-C3` — `seeds_dropped` has two producers, and an unknown path has no reason of its own.
type 5 project-ground-truth · area: impact / store / tool payloads · seen 102 · proposed ·
destination unset.*
*Evidence: the field now sums `store.impact_radius`'s budget prune (`store.py:1051`) with the tool's
lost-subject count (`impact.py`), and the two can never overlap because a dropped subject never
enters `ordered_seeds`. A truly unknown **path** reports `no_such_symbol` — true at the class level,
not path-specific; `file_outline` has the same gap (`found: false`, no reason), so a path-shaped
reason is a surface-wide follow-up, not an impact-only one.*

## 100 — A caveat is only as reachable as the payload shape you read it from
The signed line gave each caveat its own key so none could be dropped — then dropped one:
`get_index_status` sourced `parse_failures` **from the payload**, a key that exists only at
`standard`/`verbose`. At `minimal` the same index, with the same real parse failure, produced a
signed, quotable claim with the caveat missing — the exact harm the mechanism exists to prevent,
inside the mechanism. The data was in scope throughout (`counts["failed"]` is computed
unconditionally); only the **source** was wrong. **Found by the reviewer, not by me**, and untested:
no test exercised that signer's line content, so the AC was green on inspection. **Second finding,
same round:** an embedded `"` was quote-wrapped but never escaped, corrupting the line's own grammar.
Folding `"` to `'` was rejected — it silently rewrites the subject of a claim whose whole purpose is
to be re-checked; doubling the quote is lossless and adds no escape character, so separator
backslashes still survive. (`100-C1` is now **R5.5**, `100-C3` is **AGENT_BRIEF P4**.)
### 100-C1 — A value read from a payload inherits that payload's most minimal shape
- type: 2 generalisable-heuristic
- handle: source-the-caveat-from-the-computation
- status: confirmed
- seen: 100, 101, 102, 122
- evidence: `CLAIM_CARRY = ("parse_failures",)` read the key off the payload, which carries it only
  at `standard`/`verbose`, so the `minimal` line shipped without the caveat while `counts["failed"]`
  was 1. Fixed by sourcing from the computation. 102: the same principle diagnosed `seeds_dropped`,
  assigned in one place while documented as naming every dropped seed
- area: tool payloads / claim signing
- destination: **promoted 2026-08-16 → R5.5** (`PROVISIONAL`), widened at promotion to cover both
  breaks (narrow by detail level, narrow by case). **Not retired**, so recall keeps surfacing the
  handle and R5.5 stays reachable by the recalled-handle route. `/mango:promote` skips this class.

### 100-C2 — When an artifact exists to be re-checked, a lossy repair is worse than the corruption
- type: 2 generalisable-heuristic
- handle: lossless-repair-for-a-checkable-artifact
- status: proposed (awaiting human confirm)
- seen: 100
- evidence: review proposed folding an inner `"` to `'`; that would have silently renamed the path a
  reader is meant to verify. Quote-doubling round-trips exactly and keeps the no-escape-character
  grammar the backslash-separated qualified names depend on
- area: tool payloads / claim signing

### 100-C3 — A grep-gate sweep is per-commit, not per-ticket
- type: 2 generalisable-heuristic
- handle: re-run-the-sweep-after-the-last-edit
- status: confirmed
- seen: 100, 101, 102
- evidence: the Phase-3 R1.1 sweep was clean; a later commit's **docstring** reintroduced a language
  name in a core module and the gate failed the build. The sweep was honest when run and stale when
  quoted — review round 1 could not see it either, since the text post-dated it
- area: process / verification sweep
- destination: **promoted 2026-08-16 → `AGENT_BRIEF.md` P4** (`PROVISIONAL`). Two real failures
  (100, 101) against one binding (102); in 101 it had been recalled, judged *"does not apply"*, and
  was the one that fired. **Not retired.** `/mango:promote` skips this class.

### 100-C4 (also filed as 087-C2, 088-C2) — Do not attest past what the payload can distinguish
- type: 2 generalisable-heuristic
- handle: do-not-attest-past-the-payloads-resolution
- status: proposed (awaiting human confirm)
- seen: 087, 088, 089, 100, 101, 102, 107
- evidence: `impact_radius` returns `seeds_dropped = 0` for an empty seed set, so an absent subject
  and a genuine modelled zero are indistinguishable in the payload — rather than fix the count
  in-flight or sign over it, the answer gets **no line** (100). `tour_subgraph` seeded only from
  zero-inbound files answered a 3-file index with 1 stop, `truncated: false`, `total_count: 1`;
  fixed by re-seeding the lowest unseen file until the budget binds and deriving `truncated` from
  *an indexed file is not in the tour* rather than from seed/prune bookkeeping (087). `overview.md`
  printed `- modules: 4` with one page on disk and no truncation line while `tour.md` and
  `manifest.json` both carried `truncated` — and the overview is the file a human opens first (088).
  107 is the same shape one level down: an empty neighbour list could not separate "no edge in the
  graph" from "the budget could not afford the neighbour", so a page now states its full-graph
  degree instead of a flat `(none)`
- area: tool payloads / bounded walks / onboarding artifacts / claim signing
- destination: `rulebook_path` — **promotion rejected 2026-08-16** at recurrence 3, on the ground
  that all three sightings were the class *binding a design* rather than the defect recurring (the
  same reason as `094-C1`'s rejection of 2026-08-15), and that 102 had removed the cited evidence by
  making the payload distinguish the two cases. **That verdict is stale — the list now stands at 7
  tickets, and 087/088 are defects the class caught, not designs it bound.** Re-adjudicate.

*Claim `100-C5` — impact seeds are returned inside `results`, so a bare count is ambiguous. type 5
project-ground-truth · area: impact / store · seen 100 · proposed · destination unset.*
*Evidence: `store.impact_radius` includes the seeds themselves, so `answer=N` conflates *N
dependents* with *N seeds and zero dependents*. The line carries `seeds=` beside `answer=`; `answer
== seeds` is the modelled zero.*

## promote-2026-08-15 — Recurrence that only grows when someone writes a lesson under-counts the rules worth having
`/mango:promote`'s first real run proposed **nothing**; the same corpus corrected proposed two
candidates. The corpus was wrong, not the pass: `seen:` grew only when a **new lesson** was written,
never when an existing handle was recalled and answered at design. `prove-the-guard-fails` read as
recurrence 1 while it had bound 093, 096 and 099; `derived-not-listed-invariant` had two uncredited
sightings and R6.7 already cited two of its three claims. **The bias has a direction:** a class that
keeps being *honoured* rather than re-broken never accrues sightings — which is the class most worth
promoting. **Second finding:** the ratified candidate was a near-duplicate of an existing rule (R6.5
already carried its special case), and promotion's idempotency grep — handle slug plus claim IDs —
structurally cannot catch that. **Fix:** `AGENT_BRIEF.md` P1 and P2; the mango half is a type-3
signal in `SKILL_GAP_CANDIDATES.md`, since no lesson edits a mango skill. *(The same under-count
recurs one level up: see the class index — four classes clear the gate because their sightings were
filed under separate ids.)*

### PROM-C1 — A counter that only increments on the rare path measures the rare path
- type: 2 generalisable-heuristic
- handle: increment-on-the-common-path
- status: proposed (awaiting human confirm)
- seen: promote-2026-08-15
- evidence: `seen:` grew on lesson-write (rare) not on handle-answer (common), so recurrence
  under-counted every honoured class; corrected in PR #112
- area: process / learning loop
- destination: `agent_brief_path` — **written 2026-08-15** as `docs/AGENT_BRIEF.md` **P1**

### PROM-C2 — An idempotency check keyed on identity cannot detect duplication of substance
- type: 2 generalisable-heuristic
- handle: identity-check-misses-substance
- status: proposed (awaiting human confirm)
- seen: promote-2026-08-15
- evidence: promote greps handle slug + claim IDs; R6.5 already carried the candidate's substance
  under a different handle, so the grep was a clean miss that looked like a verified negative
- area: process / learning loop
- destination: `agent_brief_path` — **written 2026-08-15** as `docs/AGENT_BRIEF.md` **P2**;
  the harness half is `docs/SKILL_GAP_CANDIDATES.md` **SG-1** (type 3, out of promotion scope)

### PROM-C3 — A ticket is written at a point in time; the code moves under it
- type: 2 generalisable-heuristic
- handle: record-the-deviation-as-a-deviation
- status: proposed (awaiting human confirm)
- seen: promote-2026-08-15, 101
- evidence: 099's evidence table asked for a `no_such_symbol` warning that 092 had already replaced
  with `not_indexed`; shipped the current form with a test asserting the superseded string is absent
- area: process / lifecycle
- destination: `agent_brief_path` — **written 2026-08-15** as `docs/AGENT_BRIEF.md` **P3**

## 099 — A channel that only answers when asked cannot carry information the asker never requests
Four rounds treated low adoption as routing (069, 081) then as cost (080, 096). The interview said
**position**: all three decisions made without the graph wanted one line at a `Read` or a `Write`,
and **none wanted a tool call** — and both top uncalled queries needed no rebuild, so cost cannot
explain it. **Fix:** `code-atlas-signal`, a hook-shaped entry point (the third of 036/053's kind),
offered and never wired. **What settled it:** `next_tool_suggestions` reaches the agent *after it
asks*, and the core cannot observe a `Read`, so the rider channel is **structurally** incapable, not
merely expensive. **Bound:** no description reaches an agent that never opens the tool list — the
ceiling on all 069/081-style work, and 097 is the same finding from the recognition side.
**Falsifier (retro §0.6):** if the next round reports the signal *tuned out* at the shipped cap, the
finding was session-specific.
### 099-C1 — Where a signal is delivered can be a capability question, not a cost question
- type: 2 generalisable-heuristic
- handle: channel-cannot-carry-unasked-information
- status: proposed (awaiting human confirm)
- seen: 099
- evidence: `next_tool_suggestions` rides answers to questions; the finding is that the question is
  never asked, so no token budget on that channel would have helped
- area: agent-fit / product position
- destination: `rulebook_path` (if it recurs)

### 099-C2 — A silence rule keyed to structure needs no state; one keyed to history does
- type: 2 generalisable-heuristic
- handle: structural-silence-over-stateful-latch
- status: proposed (awaiting human confirm)
- seen: 099
- evidence: every occasion the field named as costly (probe output, CI shells, authoring writes) is
  excludable by tool name or by "the path already exists"; a fire-once-per-session latch would need
  persistence and would still be wrong on the second session
- area: hooks
- destination: `rulebook_path` (if it recurs)

### 099-C3 — When a create-vs-edit test reads the filesystem, the hook event is part of the contract
- type: 2 generalisable-heuristic
- handle: hook-event-is-part-of-the-contract
- status: proposed (awaiting human confirm)
- seen: 099
- evidence: the untracked signal is silent by construction at `PostToolUse` because the file exists
  by then; `tests/test_write_time_signal.py::test_the_write_signal_is_a_pre_tool_use_signal` pins it
  so the silence cannot be misread as a bug
- area: hooks
- destination: `rulebook_path` (if it recurs)

## 096 — A cost fix whose correctness argument is "the delta is what changed" needs the case where it isn't
`resolve_edges` re-scanned the **whole** unresolved residue on every incremental — flat across delta
size at two scales (20k residue: 0.074 s at 2 files vs 0.078 s at 14; 60k: 0.408 vs 0.405), so the
cost was O(residue) and the 0→1-file cliff was the entire tax. **Fix:** an optional delta scope
streams only edges the delta could have changed the answer for. **The trap:** file A holds an
unresolved edge to `\X` and the delta adds `\X` in file B; A is *not* a dependent, because
`file_paths_targeting` matches `target_qname`, still NULL — so a file-scoped resolve leaves it
unlinked forever while a full resolve links it. The **key** set, not the file set, is what makes the
scope equivalent. **Bound:** equivalence holds only while the alias map is fixed, so the map is
snapshotted before the parse and a change falls back to a full pass — and pinning it is not enough,
because `_lookup_raw` also *reaches* a key through it, so the key set must carry each key's aliases
(096-C4, found in review). **No schema change** — the ticket assumed one; `idx_edges_raw` already
indexed the lookup.
### 096-C1 — A scoped scan is equivalent only for the keys the scope can name
- type: 2 generalisable-heuristic
- handle: scope-by-key-not-by-file
- status: proposed (awaiting human confirm)
- seen: 096
- evidence: `tests/test_delta_resolve.py::test_delta_resolve_links_residue_a_new_file_satisfies`;
  stubbing the key set to `set()` fails 5 of 8 tests
- area: resolver / store
- destination: `rulebook_path` (if it recurs)

### 096-C2 — A purity argument that depends on a lookup table must pin that table, not assume it
- type: 2 generalisable-heuristic
- handle: pin-the-table-a-purity-claim-rests-on
- status: proposed (awaiting human confirm)
- seen: 096
- evidence: `indexer.py` snapshots `alias_targets()` **before the parse** and falls back to a full
  resolve when it moved; a snapshot taken after the parse would already contain the new rows and
  silently miss the change
- area: resolver / indexer
- destination: `rulebook_path` (if it recurs)

### 096-C3 — A writer that runs after the delta is computed must be added to the delta
- type: 2 generalisable-heuristic
- handle: late-writer-outside-the-delta
- status: proposed (awaiting human confirm)
- seen: 096
- evidence: `apply_indirection_rules` rewrites every rule row bare under `INDIRECTION_FILE` *after*
  the parse, so a scope built from `to_parse` never covered it and the fresh `ALIASES` row stayed
  unresolved; `tests/test_delta_resolve.py::test_enrichment_rows_resolve_under_a_delta_scope`
- area: indexer / enrichment
- destination: `rulebook_path` (if it recurs)

### 096-C4 — A scope keyed on raw text must invert every rewrite the lookup applies to that text
- type: 2 generalisable-heuristic
- handle: invert-the-rewrite-the-lookup-applies
- status: proposed (awaiting human confirm)
- seen: 096
- evidence: `_lookup_raw` maps a raw through the alias map (whole name *and* container), so an edge
  naming `\Ns\Aka` resolves to the delta's `\Ns\Real` — comparing `target_raw` against the key set
  alone skipped it in a file no delta lists, while a full resolve linked it. `delta_scope` now adds
  each key's alias pre-images;
`tests/test_delta_resolve.py::test_delta_scope_covers_an_edge_naming_an_alias`
  and `::test_delta_scope_covers_an_aliased_container` — reverting the expansion fails both, and
  only those two
- area: resolver
- destination: `rulebook_path` (if it recurs)

## 094 — A mention the resolver skips is indistinguishable from a relationship it refused
`Foo::class` in an array was a textual, unambiguous class name, and `find_references` still answered
`relationship_not_modelled`, because (1) the PHP adapter never emitted `REFERENCES` and (2)
`skip_dynamic` dropped every `DYNAMIC` row — including ones whose `target_raw` is an FQN. **Fix:**
emit `REFERENCES`/`DYNAMIC` for `Name::class`; opt the kind into `FQN_EDGE_KINDS`; keep `skip_dynamic`
from hiding `REFERENCES`; leave the linked tier `DYNAMIC`. An all-`DYNAMIC` page sets
`authoritative: false` so it reads as a candidate list. Variable-method dispatch stays unmodelled, no
new `edge_kind` (R3), and the anchor edge-count delta is an operator paste, not a merge gate.

### 094-C1 — skip_dynamic must not drop a DYNAMIC row whose target is an FQN
- type: 2 generalisable-heuristic
- handle: skip-dynamic-means-unlinkable
- status: proposed (awaiting human confirm)
- seen: 094, 096
- evidence: `store.py` `iter_unresolved_edges`;
`tests/test_class_const_mention.py::test_skip_dynamic_still_yields_reference_mentions`
- area: resolver / store
- destination: `rulebook_path` — **promotion rejected 2026-08-15**: the second sighting (096) was
the rule *binding a design*, not the defect recurring, so the class is load-bearing twice but has
failed only once. Re-propose on a real second failure

*Claim `094-C2` — A ::class mention is a REFERENCES edge, not a CALLS or a new kind. type 5 project-
ground-truth · descriptive · area: adapter / contract · proposed · stays in lessons.*
*Evidence: ticket 094; `Visitor.php` `enterClassConstFetch`; PLAN §8.2.*

## 097 — A recognition score off names cannot measure descriptions, and recognition is not recall
Round 5 scored 14/14 on the blind probe while 7 of 14 descriptions were never loaded, then named
`file_outline` at Q4 and did not call it when a 1,196-line port needed the symbol map. **Fix:** the
probe records resident `K/14`, marks each answer name-only or description-backed, and reports two
rates. The 081 proxy is the description-backed rate (or `NOT OBSERVED` when `K = 0`). Q4 is
occasion-worded so a name list can miss it. Retro §2 gained a fourth bucket — *knew it, it fit, did
not think of it* — whose opposite fix is a workflow trigger, not a better description. The
`file_outline` occasion lives in the tool description and the onboarding runbook, not in
`next_tool_suggestions` (061 / R4). **Bound:** descriptions can name the occasion; they cannot make
the agent notice. 074’s n = 1 for *legacy→unified port* is unchanged.

*Claim `097-C2` — Descriptions can name an occasion; they cannot make the agent notice it. type 5
project-ground-truth · descriptive · area: routing surface / recognition vs recall · proposed ·
stays in lessons.*
*Evidence: field retro round 5 §11.3; `file_outline` named at Q4, description loaded, unused on the
1,196-line port; trigger placed in description + onboarding, not `next_tool_suggestions`.*

## 095 — An ignore total that does not name its source is an unauditable denominator
082 made `skipped.ignore` an outsider-checkable int and the identities close, but the 9,541 files in
that bucket all have an indexed suffix — PHP the index chose not to hold — and nothing named the
rule. The retro's suggested `{gitignore, config, vendor}` is a **hint, not the schema**: `load_ignore`
composes built-ins + `.gitignore` + `.codeatlasignore`, `vendor/` is a pattern *inside* the builtin
source, and there is no `CA_*` ignore knob. **Fix:** stamp each `_Rule` with its source as the matcher
concatenates; attribute by the same last-excluding-rule walk `is_ignored` already uses (the ticket's
"first match wins" was an example of a stable rule, not the matcher); keep `ignore` as the int;
publish `skipped.ignore_sources` at verbose only, omitted when empty; persist the dict on a
**sibling** meta key, because `collection_census()` int-casts every value (092). On the git path most
`.gitignore` hits never enter `collected`, so the breakdown names what **this matcher** dropped.
Per-pattern counts would re-publish the ignore file (061), and the absolute 9,541 is an operator
paste, not a merge gate (080/074).

### 095-C2 — A JSON meta reader that int-casts cannot hold a dict; use a sibling key
- type: 2 generalisable-heuristic
- handle: sibling-meta-non-int
- status: proposed (awaiting human confirm)
- seen: 092, 095
- evidence: `store.py` `collection_census()` int-casts; `IGNORE_SOURCES_KEY` beside
  `UNTRACKED_INDEXABLE_KEY`
- area: store / census
- destination: **promoted 2026-08-14 → R1.7** (`PROVISIONAL`). `/mango:promote` skips this class.

*Claim `095-C3` — On the git collect path, ignore_sources names matcher leftovers, not git’s drops.
type 5 project-ground-truth · descriptive · area: collection census / ignore · proposed · stays in
lessons.*
*Evidence: PLAN §11; `git ls-files` already applies `.gitignore`; proving test uses
`.codeatlasignore` + builtin, and `git add -f` for a gitignore source.*

## 093 — A field whose values are usually callable trains the reader to call all of them
Three of five `try_instead` values were real tools; two were instructions shaped like identifiers
(`find_references_on_method_qname`, `path_basename_search`). The routing was right both times — an
evaluator who followed one got a better answer — but it first had to try the string as a tool, find
nothing, and infer. **One prose value makes the whole field ambiguous**, not just itself. **Fix:**
one register per field, the qualifier in the sibling `try_instead_hint`, and the split carried into
the source as a naming rule (`TRY_INSTEAD_*` vs `TRY_INSTEAD_HINT_*`) so a test derives both sets
instead of keeping a list. Proved against the pre-fix shape: 4 of 6 failed there, 6 pass after.

**Review addendum — "callable" is not "useful", and a guard needs its own guard.** (1) The dead-route
guard scanned every module *including the one defining the constants*, so each name was found by its
own definition line and the test **could never fail**. (2) A route must **make progress**: the
class-level miss self-routed `find_references` → `find_references`, which loops for exactly the
mechanical reader the field targets — route to the enumerator instead. (3) A route must **be able to
answer**: the unlinked-include miss routed to `search_symbol`, whose `nodes_fts` does not cover
`edges.target_raw`, so following it returned `reason: ok` and no includer. Making a bad route
*callable* turns an unfollowable string into a followable trap. All four claims below are now rules
(**R5.4**, **R6.5**, **R6.7**) — the rules, not this entry, are the binding text.
### 093-C1 — A machine-readable field holds one register; prose gets its own field
- type: 2 generalisable-heuristic
- handle: try-instead-tool-name
- status: confirmed
- seen: 092, 093, 100, 101, 102
- evidence: `nav_result.py:58-76` (the naming rule);
  `tests/test_try_instead_is_a_callable_tool_name.py` (4 failed / 2 passed pre-fix, 6 after); field
  retro round 5 §4
- area: tool payloads / R1.1 / R4
- destination: **promoted 2026-08-14 → R5.4** (`PROVISIONAL`). `/mango:promote` skips this class.

### 093-C2 (also filed as 095-C1, 097-C1) — An enumeration guard derives its sets; it never lists them
- type: 2 generalisable-heuristic
- handle: derived-not-listed-invariant
- status: confirmed
- seen: 087, 088, 093, 095, 096, 097, 099, 100, 101, 102, 122
- evidence: `tests/test_try_instead_is_a_callable_tool_name.py` reads `vars(nav_result)` +
  `main.TOOL_NAMES`, and `test_the_dead_route_guard_can_actually_fail` injects a dead constant (093);
  `composed_source_names()` derived from `COMPOSED_IGNORE_FILES` (095);
  `tests/test_recognition_probe_protocol.py` parses the probe table and compares it to
  `main.TOOL_NAMES`, with `test_the_probe_surface_guard_can_actually_fail` injecting a name the
  table does not have (097)
- area: tests / R1.1
- destination: `rulebook_path` — **promoted 2026-08-14** to `docs/ENGINEERING_RULES.md` **R6.7**,
  tagged `PROVISIONAL (awaiting ratification)`. Re-runs of `/mango:promote` skip this class.

### 093-C3 (also filed as 089-C1 in the 089 review round) — A guard is not a guard until it has been made to fail
- type: 2 generalisable-heuristic
- handle: prove-the-guard-fails
- status: confirmed
- seen: 087, 088, 089, 093, 096, 099, 100, 101, 122
- evidence: the dead-route guard scanned its own definition site, so every name was found by its own
  definition line and the test could never fail — yet it shipped in PR #103 advertised as "the audit
  cannot go stale", and review caught it, not the suite (093). 089 is the narrower case where the
  guard is one expression inside a renderer: deleting `blob.replace("<", "\\u003c")` left `tests/`
  green, and only a mutant whose *path* is `a</script><img ...>.aa` produced the unterminated JSON
  block and a live `<img src=x onerror=...>` in the generated page
- area: tests / R1.1
- destination: `rulebook_path` — **promoted 2026-08-15** into `docs/ENGINEERING_RULES.md` **R6.5**,
  which already carried the special case (a sweep guarded against emptying itself); this widened it
  to every guard rather than adding a near-duplicate rule

### 093-C4 — A route the reader cannot use is worse callable than not
- type: 2 generalisable-heuristic
- handle: route-must-answer
- status: confirmed
- seen: 093, 101, 102
- evidence: `include_graph` → `search_symbol` returned `reason: ok`, `total_count: 2`, includer
  absent (`store.py:701-714` vs `store.py:90-92`); now hint-only, no route. 102: an all-dropped
  `impact` answer routes through `shape_exact_miss`, so its route can answer and is never `impact`
- area: tool payloads / 065 / 075 / 076
- destination: **folded into R5.4's falsifier 2026-08-16** rather than promoted as a new rule — per
  `AGENT_BRIEF.md` P2 the substance was already in R5.4 clause (c), but the falsifier tested only
  (a) and (b), so the class was stated and unenforceable. **Not retired** (declined 2026-08-16, as
  for `100-C1` / `100-C3`), so recall keeps surfacing the handle.

## 092 — A partition cannot count what never entered the walked set
`collect()` partitions `git ls-files`. Untracked files are not skipped-by-rule; they are never in
`found`, so 082's identity stayed green while four new classes answered `no_such_symbol`. **Fix:**
sit `skipped.untracked` *beside* the partition (a second git spawn, not a second filesystem walk —
folding them into `collected` would break `collected == git ls-files`). Stamp the int on the census
JSON and the path list on a **sibling** meta key — `collection_census()` int-casts every value.
Classify the miss by matching stored stems, reuse `not_indexed` (`indexed: true` vs unbuilt's
`indexed: false`), and put git-add prose in `try_instead_hint` so `try_instead` stays a real tool
(093). Do not index the file.
**Review addendum.** An early return that replaces a fall-through inherits its whole payload
contract: 092's exact-miss shortcut silently dropped `subject_refreshed_only` (073) and
`args_unrecorded` (049) because both were attached below it. And match an untracked file on the
**stem** — a path-shaped qname's trailing ident is its extension, so `Missing.aa` matched `aa.aa`.

## 080 — A "delta" count that is non-zero on an empty delta means the work isn't gated on the delta
080's no-op reported `edges:6071` for 0 files parsed and cost ~56s because `incremental_update` ran
the late writers (enrichment + full-graph `resolve_edges`) unconditionally — even when nothing
changed, where they only re-derive rows already in the store. The unreadable *number* and the *cost*
had one cause: work not gated on the delta. **Fix:** gate it — skip the late writers when
`to_parse` and `removed` are both empty (idempotent on an unchanged graph, so state-equivalent); the
count then means the delta and the floor drops. Guard on the **empty delta**, never on the count
itself (circular) and never by skipping when there *is* a delta (that's the 068 anti-pattern the
ticket names). Two corollaries: (1) when a cost ticket's real number is on an environment you don't
have (the anchor repo), ship the fix + fixture proof and record the absolute seconds as an
operator-confirmed follow-up, not a merge gate (cf. 074) — don't let it stall like 052→053 did;
(2) a mechanical blast-radius grep of the changed *symbol* misses callers that pass it differently —
here a profiler test drove `incremental_update` with `phase_times=` and asserted every phase is
present; grep the phase/inventory constant too, and prefer a fix that keeps the invariant (record the
skipped phases as 0.0) over weakening the other ticket's assertion.

## 081 — A capability on a channel the consumer never sees is unshipped, however well it works
081's four MCP prompts worked perfectly and were never once invoked in four field rounds — because
the agent's client surfaces only tools to the model; prompts are human-invoked entries the model
cannot see. The defect was a **category error** (counting a human-facing channel as agent-facing), not
a bug. **Fix:** for any capability, verify the *consumer's actual surface* reaches it before counting
it as delivered — reachability is a property of the delivery channel, not of the feature's
correctness. The smallest honest fix is often to relabel and re-home, not to rebuild: here, keep the
prompts as operator recipes, route agents via the surface they do see (tool descriptions, 069), and
add no 15th tool (a scanned surface has a budget). Generalises: when a ticket hands you a design choice
"with the field evidence in hand", let the evidence of what the consumer *reached* — not what was
*built* — pick the design.

## 082 — A ticket's illustrative cause-list is a hint, not the schema; count what the code actually does
082 asked to publish `files` skip counts "by cause (ignore rule, suffix, size, unreadable)". Only two
of the four are real collect-time skips (`suffix`, `ignore`); "unreadable" is the existing parse-time
`failed` bucket (`parsed_ok=0`, already on verbose via 058) and code-atlas applies no size limit at
all. Implementing all four literally would have invented a size-filter (new inclusion policy that
changes what gets indexed) and double-counted unreadable. **Fix:** at analysis, re-derive every
enumerated acceptance value against the code before treating it as the schema — an AC's parenthetical
list is a Gate-1 falsifiability check, not a spec. Publish the causes that exist, map the rest to where
they already live, and never add a filter just to satisfy a list. Generalises: a reconciliation that
"closes by construction" (a partition of one walk) is the honest shape — R4's "one walk, not two ways
to count" — so design the census as a partition and let the arithmetic close, rather than reconciling
two independently-derived numbers.

## 079 — A "refusal path" the ticket wants to carry a field may not return a payload at all
079 asked for `index_root` on "every refusal path (no adapter, empty suffixes, schema mismatch)".
Two of those (`no_adapter`, `empty_suffixes`) did not *return* a payload — they `raise AdapterError`
(064's deliberate fail-loud). An exception carries no payload field, so satisfying the AC required
converting the raise to a returned `mode: refused` payload at the tool boundary (the `schema_guard`
pattern) — a real contract change to the *other* ticket's tests. **Fix:** at analysis, for any
"attach field X to every <shape>" requirement, verify each named shape actually *returns* that shape
vs. *raises*; surface the raise→payload conversion (and the test it breaks) as an explicit Gate-1
decision and a proof-collateral change-list item, not an execute surprise. Generalises: "every
refusal" is not a given set of payloads until you confirm each refusal is a payload.

## 078 — A warning field next to a body is ignorable; refuse the body
`ambiguous_definitions` named every site and still shipped one region's `source`/`file`/`line_*`.
Agents read the body and skip the list — the exact failure 070's caveat predicted. **Marking the
chosen site (option 2) still relies on a second field; a disambiguator arg (option 3) is a large
surface.** Prefer **refuse the body** when N>1: empty `source`, omit site keys, keep the list,
`reason=subject_ambiguous` + `found=false` + `try_instead` (never `reason=ok` with an empty answer —
075/076). Refuse **before** freshness and probe multiplicity with `max_results+1`. Unique payloads
stay byte-identical (061). Re-ask via existing `search_symbol` / `file_outline`, not a new parameter.

## 077 — Name the revision with dual refs; do not invent a third staleness word
`staleness: "current"` after an out-of-band branch switch + rebuild is *true* and still useless —
agents reason in branch names, not SHAs. The temptation is a new word (`switched` / `diverged`).
Resist it: 047 owns which files move the signal, and a third word forces every consumer to relearn
the vocabulary. **Ship `last_ref` (meta, stamped at build) + `head_ref` (live) beside the SHA
pair**, keep `current`/`behind`/`unknown`, and put the pair on the shared status↔busy vocabulary
(072) — not on nav (061; directory mismatch stays `index_root`). Detached HEAD is the value
`HEAD`, not an omission.

PR review follow-ups that belong with the feature: (1) clear `last_commit`/`last_ref` on rebuild
when git cannot name them — skip-write inherits a prior branch onto an unversioned snapshot;
(2) omit `last_ref` when the key is absent but `last_commit` is present (pre-077), so `null` is
not overloaded as "non-git"; (3) one `rev-parse HEAD --abbrev-ref HEAD` for an atomic SHA+ref
pair and one fewer spawn on the cheap status path; (4) unbuilt/mismatched stay git-free.

## 075 — "Bump `contract_version`" can name the wrong contract — verify before you force a reindex
Tickets 075/076 constrained the change with "R3 — a new `reason` value is contract vocabulary: bump
`contract_version`." Taken literally that bumps the **adapter** JSONL contract
(`contract.CONTRACT_VERSION`),
whose bump makes every existing index schema-incompatible → **a full reindex for all users**. But nav
`reason` codes are **tool-output** vocabulary: defined in `nav_result.NAV_REASONS`, tested in
`test_nav_reason_codes.py`, and — the decisive evidence — `CONTRACT_VERSION` was still `5` after 054, 065
and 069 each added a reason. Two vocabularies both called "the contract"; only one gates reindexing.
**Fix:** before honoring a "bump the contract" constraint, locate where the vocabulary is *defined* and
which *conformance suite* tests it; if that is not `contract.py` / `tests/contract/`, it is not the
adapter contract and must not bump `CONTRACT_VERSION`. Surface the correction in the design + PR
(detect-and-surface, per the uncodified-standard rule), never silently comply or silently ignore.

## 074 — A measurement ticket that needs an external environment splits into prep → run → analyze
074's core is an n≥3 headless benchmark on the anchor repo — data this session cannot produce, and
must never fabricate ("every claim is a counted artifact"; "do not change any tool to make the number
come out"). The wrong move is to run a local toy-repo substitute (it cannot reproduce a confident
*partial* answer terminating correct reasoning) or to invent verdicts. The right move: **split the
ticket** — commit a **pre-registration** (outcomes → consequences, protocol, rubric, capture template)
that is **git-timestamped before any run**, hand the runs to the maintainer's environment, then score
and decide in a later cycle. Pre-registering in git is what makes the result unarguable after the
fact. A benchmark ticket has **no proving test**; its proving artifact is the pre-registration plus the
recorded per-run verdicts. Shipping the prep half alone is a legitimate stopping point — but the PR and
status must say so plainly (measurement ACs still open), never imply the threat was resolved.

## 069 — Adding a member to a pinned vocabulary breaks its pin tests AND every consumer's allow-set
Adding `REASON_CAPABILITY_NOT_CONFIGURED` to `NAV_REASONS` broke **four** tests, and the design's
test-blast-radius grep found only one (the prompt-registration test — which in fact needed no edit).
The real collateral: two tests that **pin** the vocabulary (`NAV_REASONS == (...)`,
`NAV_REASONS[-1] == …`) and two freshness tests that **consume** it via a per-tool reason **allow-set**
(`assert reason in {no_matches, ok}`). **Fix pattern:** when adding a member to a shared enum/vocabulary
tuple, grep for the collection name (`NAV_REASONS`) **and** for set/`in` **memberships** of its
constants across tests — not just the constant's definition. A new member is invalidated both where the
set is pinned and where any consumer enumerates the values it will accept. (Generalizes 070's
pinned-count
lesson from counts to vocabulary + consumer allow-sets.)

Second, smaller lesson from the same run: an "inert vs empty" signal belongs **on the existing
empty-answer branch** (override `no_matches`), not as an **early return before the shared
freshness/clamp path** — the early return silently dropped `find_view_data` out of the six-consumer
freshness invariant and the clamp-uniformity guard. Reclassify the reason; keep the tool on every
shared code path.

## 070 — A wall-clock-tolerance test can fail under load; isolate before calling it a regression
`test_phase_times_cover_named_phases_and_sum_near_wall` asserts `within_tolerance`, so it is
**load-sensitive**. It failed twice during 070's delta validation — only while two `@needs_php`
fixture builds and back-to-back Docker image builds loaded the host — and passed both in isolation
with the change and on clean `main`, in a ticket that touches nothing in the incremental path.
**Fix pattern:** on a timing failure during delta validation, re-run it in isolation with your change
and on the stashed clean base before treating it as a regression; do not chase it, and do not weaken
your delta to "fix" it.

**Recurred on CI `main` after #108 — and the cause is structural, not merely load.** py3.12 red,
py3.13 green on one commit. The slack is `max(0.15 × wall, floor)`, and on the sub-second scenarios
the **floor** binds — it was `0.05` s, covering work no phase times (adapter teardown, store open,
the profiler's two count snapshots). That cost is **spiky**, not proportional: throttled to 0.4 CPU,
40 noops gave p50 **8 ms**, p90 **65 ms**, max **115 ms** — **8 of 40 over the old floor**, 0 over
`0.20`. At ~20 % per scenario and three scenarios a run, a red run is a coin flip, which is the
one-runner-red signature. **Method note:** the first hypothesis (the profiler's own snapshots
dominate) was *refuted by measuring*, and that refutation is what located the rest of the glue inside
`incremental_update` — do not ship a timing fix whose mechanism you have not reproduced. **Fix:**
floor raised to `0.20` s and named (`WALL_FLOOR_SECONDS`), ~1.7× the worst tail produced; the report
now carries `unattributed_seconds` so the glue is a watchable number, and the test also asserts the
load-independent half (the gap is never negative). **General shape:** a `max(relative, absolute)`
tolerance is only as portable as its absolute term — size that term against the *tail* on a contended
host, never the steady state on a fast dev box.

## 072 — A change that adds/removes a core module must grep pinned counts, not just moved symbols
The design's test-blast-radius grep matched the **symbols** being moved (the staleness constants,
which stayed importable via re-export) and concluded "no existing assertion is invalidated". But two
guardrail tests pin the **core-module count** (`assert len(core_modules()) == 36` in
`test_sql_confinement.py` and `test_core_is_language_agnostic.py`), and a *new* module `staleness.py`
broke both — surfacing only at the full-suite run, as an execute deviation. **Fix pattern:** when a
change adds or removes a file under a swept tree, the blast-radius step must also grep for **pinned
file/module counts and parametrize sources** (`len(... ) == N`, `rglob`, `parametrize(... modules())`),
not only the renamed/moved symbols — a count guard is invalidated by the file *existing*, with no
symbol match to find it by.

## 066 — Report an argument the server honoured only partially, and enumerate limit-takers from code

`cap = min(limit, max_results)` silently discarded the excess: `truncated`/`total_count` said *more
exist* but never *the tool honoured fewer than you asked* — different questions. A previous reader was
burned and hand-patched a caveat into the anchor repo's `CLAUDE.md`, i.e. the server was exporting a
caveat into every consumer's docs. **Fix pattern:** surface the honoured-vs-requested gap at the point
of use — one conditional field (`limit_capped_to`, the effective value) via a shared helper, present
only when a clamp occurred (061) — and state the knob's *full* meaning in the server's own answer
(`max_results` + `governs`: rows **and** resolver candidate fan-out — a hidden double duty makes a
caller mis-read `total_count`). **Uniformity guard:** a "holds for five tools, not the sixth" caveat is
worse than none, so guard it with a **source-scan test** that fails if any `tools/*.py` declaring a user
`limit` skips the helper — a new tool can't silently opt out. **Inventory from code, not prose:** the
ticket said "…and friends" but the code showed exactly five user-`limit` tools (`file_outline` uses
`max_results` directly, no user param) — the denominator came from `limit: int | None`, not the ticket.

## 067 — A storage sort reused for presentation makes correct results mislead

`_EDGE_ORDER` leads with `source_qname`, which *is* the file path for file-scope call sites, so a
truncated page 1 clusters into whichever top-level subtree sorts first — a fully correct, honest
payload (`truncated`, `total_count`) that still points a one-page reader away from the answer.
Correctness and usefulness diverge when the visible sample is unrepresentative, and no honesty field
repairs the sample. **Fix pattern:** prefer a cheap structural *representativeness signal* over a
reorder — an additive `result_subtrees` (top-level path segment → count over the full set) tells the
reader what the page hides while leaving row order, `offset` paging (057), determinism (R4), and every
golden payload untouched. The "measure before designing" kill gate earned its place: quantifying the
skew first showed it was **structural and guaranteed**, not rare — which justified building the fix
but chose the additive signal over an expensive total-order change.

## 068 — Synthetic anchors are edges, not source files

A rules bookmark that is a real `files` row with `parsed_ok=True` makes two honest counters disagree
by one. Keep the edge `file_path` for provenance; do not upsert a `files` row or File node. Purge
legacy bookmark rows on every apply so upgrades self-heal.

## 071 — Answers must name the tree they describe

`db_path` on status is a database location; agents need the **source root**. Emit `index_root` =
`config.root` on every answer (not status-only — agents skip status). Never guess the client's cwd.
Recommend `CA_DB_PATH` per worktree for isolation; the field only makes the un-isolated case legible.
Recalibrate the tokens-to-answer floor when every payload grows (`0.8 × observed`).

## 064 — Empty adapter map is misconfiguration, not an empty repo

`_announce` looping zero times looks like "nothing to do". Fail before meta when
`adapter_cmds` is empty. A successful build over zero matching files still stamps
non-empty `indexed_suffixes` so callers can tell the two apart. The empty-suffix-union
half needed no code: the handshake validator already rejects `extensions: []`. A guard
added for it was unreachable, and its test matched a regex the *handshake* error also
satisfied — a proving test must name the mechanism it proves, or it proves nothing.

## 063 follow-up — Cap the match set, not the CALLS table

`view_data` enrichment must look up CALLS by setter (`idx_edges_raw`), not scan a
`source_qname` prefix of *all* CALLS. A 10k cap on the whole table silently missed
~99% of anchor `setData` sites. Bound = O(matching sites); report truncation only if
a match-set cap returns.

## 063 — Count-first ACs need an Outcome above the mango separator

A “count before code” AC cannot be proven from a single squash commit. Put the table + kill/proceed
in the ticket **Outcome** (above the working-doc separator) and pin it with a small test that reads
that section — otherwise a ticket-blind challenger marks AC1 `can't tell` and Gate 4 fails.

## 062 — `key_arg` is an argument index, not a string-literal ordinal

`view_data` rules name which **argument** holds the key. Store `args` only record categories, so
enrichment must map `key_arg` through those categories to the Nth quoted literal on the call line
(e.g. `put($bag, 'extra', 1)` with `key_arg: 2`). Treating `key_arg` as a raw literal ordinal fails
as soon as a non-string arg precedes the key.

## 061 — Payload fields that earn nothing should leave nav/search

Keep `db_path` on `get_index_status` only. Make `next_tool_suggestions` state-reactive (empty when
current). Suppress redundant File∩Class search hits. Emit `subject_refreshed_only` only when the
subject was actually reparsed — a constant `true` is dead weight.

## 053 — Git refresh hooks must stay opt-in and out of band

When field evidence says an incremental can cost ~a minute, contrib git hooks must spawn
`code-atlas-refresh` in the background and always `exit 0`. Never auto-write `.git/hooks`.
Use a non-blocking lock beside the DB so overlapping hooks skip cleanly (R4.3) instead of
racing the MCP writer.

## 052 — Measure-only tickets still need an Outcome defect decision

When AC demands “is this a defect?” but the host has no repo-sized sample, record **suspected /
unconfirmed** with the field evidence and the profiler command — do not invent a phase split, and do
not close as honest price without one. Ship the profiler; leave 053 gated. Fixture-scale
confirm/refute + a stated pull_shaped wall still belong in Outcome even when the scale sample is unset.

A local-tier profiler that rebuilds `Config` from process env must **fail loud** when
`adapter_cmds` is empty — otherwise reconcile can wipe the index. After touch+restore scenarios,
re-run an untimed incremental so hashes match the restored tree.

## 060 — Record scale re-measures in ticket Outcome with a commit SHA

When an AC requires re-measuring full-build vs status on a clean server, land an `## Outcome`
section (with the tip SHA, and an honest “scale sample unset” if the anchor was not remounted) in
the same card as the code — reviewer and ticket-blind challenger both treat a missing Outcome as
not-met even when fixture tests already prove agreement.

## 058 — A status-only `detail_level` value must update CONVENTION §6

When one tool gains a third `detail_level` (here `verbose` on `get_index_status`), PLAN and the
MCP schema tests are not enough: CONVENTION §6 still said every tool is `{minimal, standard}` and
review correctly blocked on R7.2. Update CONVENTION in the same card as the Literal change.

## 057 — Scope "enumerate every result set" to store-ordered pages

When a ticket AC says every oversized answer must be fully enumerable, pin which
tools/depths use a total store ``ORDER BY … LIMIT/OFFSET`` versus a BFS with a
count floor. Otherwise review correctly rejects depth>1 callers as incomplete
against the letter of the AC. Record the scope in Outcome + PLAN in the same card.

## 056 — Spell `NodeKind` as `Literal[…]` and derive `NODE_KINDS` with `get_args`

`Literal[*NODE_KINDS]` fails mypy (`valid-type`) even when the tuple looks like string literals.
Spelling the `Literal` out (`NodeKind = Literal["File", …]`) and setting
`NODE_KINDS = get_args(NodeKind)` keeps one vocabulary, types MCP `kind: NodeKind | None` cleanly,
and publishes `anyOf: [{enum…, type:string}, {type:null}]` — coherent with a null default.
Do **not** bolt `enum` on via `json_schema_extra` as a sibling of `anyOf`: sibling keywords are
ANDed, so `null` satisfies `anyOf` but fails `enum` and the schema rejects its own default.

## 043 — A per-file dedupe keys on the full UNIQUE key, and a core guard never names `sqlite3`
Two constraints surfaced while making a duplicate-declaration file soft-fail instead of aborting the
build:
- **Dedupe by `(qualified_name, file_path)`, not `qualified_name` alone.** `replace_file_rows` is
  legitimately called with same-qname nodes for **different** files in one call (multi-candidate
  resolver siblings — `tests/test_resolver.py`). A qname-only key silently collapsed them; the design's
  own C1 already said the key is the full UNIQUE key. Match the constraint you are de-duping against.
- **A writer guard must catch a store-owned type, never `sqlite3` directly.** Adding `except
  sqlite3.Error` to `indexer.py` tripped `test_sql_confinement.py` (R1.4/R4.3 — only `store.py` may
  reference SQLite). Export a `WRITE_ERRORS = (sqlite3.Error,)` tuple from the store and catch that, so
  SQLite stays confined. Generalises: when the core must react to a boundary module's failure, the
  boundary owns the exception vocabulary.
Both were caught only by the **existing** regression suite, not the new tests — the delta-green
baseline diff (byte-comparing failure sets) is what exposed them; a bare pass/fail count would not have.
- **Baseline-set diffing has a blind spot: a test that fails-at-launch locally hides a regression in
  the code it would run post-launch.** A widened `replace_file_rows` return (`None`→`int`) broke the
  `RecordingStore` test double (it dropped the `super()` return), but `test_every_write_...` fails on
  the Windows dev host at fake-adapter subprocess launch, so it sat in **both** baseline and after
  failure-sets → the name-diff scored it "not new." CI (Linux) launched the adapter and hit the real
  `TypeError`. **Fix:** when a change alters a signature/return that a subprocess-only test path
  consumes, exercise that consumer **without** the subprocess (drive the store subclass / `_write`
  directly) rather than trusting the failure-set diff. Also: a store subclass override must propagate
  the base return value, and `tests/` is not mypy-checked so an incompatible override annotation there
  won't be caught by the `type` job.

*Claim `043-C1` — Full-UNIQUE-key dedupe + store-owned WRITE_ERRORS. type 5 project-ground-truth ·
area: store / indexer / R1.4 / R5.1 · confirmed · stays in lessons.*
*Evidence: `test_resolver.py` multi-file siblings; `test_sql_confinement.py`; Gate-4 clean.*

## 042 — A ticket's "References" can be stale; verify claimed wiring before scoping
Task 042's References said the `source: sample` path was "already wired via `cross_repo_validate`". It
was **not** — `tokens_to_answer.py` skipped every non-fixture row and only listed sample IDs as
skipped. Taking the claim at face value would have under-scoped the task to a JSON edit; it actually
needed a new clone→build→evaluate code path plus a scheduled workflow (SCOPE S→L at Gate 0). **Fix:**
at analysis, grep for the symbol/path a ticket claims exists and confirm it before sizing; a stale
"References" line is a requirement to rebuild, not a freebie. Generalises: treat a ticket's factual
claims about the current codebase as hypotheses to verify, not givens.

### 042 — Env prerequisites are satisfiable locally, don't defer on their absence
The sample tier needs PHP+clone, absent on the Windows dev box (`php: not found`, no
`adapters/php/vendor`). Rather than defer the value claim to an operator run, a **portable PHP 8.3.33 +
Composer** env was stood up in scratchpad and the adapter ran end to end (fixtures 10/10, then samples
5/5, ratio 98.2). **Fix:** when a task is gated on a missing runtime, try provisioning a throwaway one
before falling back to a deferral — the fuller deliverable often beats the split. The earlier
`WinError 2` in tests was the *fake* test adapter's subprocess quoting, not the real adapter.

## 041 — Prefer language-free ignore globs over splitting a guarded token
Builtin Blade exclusion is `*.blade.*` (compound template suffix, any trailing extension) — not a
concatenated `*.blade.php` that defeats the R1.1 language-name guard. File-level builtins also apply
inside `collect_stubs` so `CA_STUB_ROOTS=vendor` cannot re-route ignored templates.

*Claim `041-C1` — R1.1-honest Blade ignore + stub-walk coverage. type 5 project-ground-truth ·
normative · area: ignore / indexer / R1.1 · confirmed · stays in lessons.*
*Evidence: PR #47 review — split-token dodge rejected; `*.blade.*` + `_STUB_FILE_IGNORE`.*

## 040 — Shipping enrichment requires PLAN §1 / R1.4 honesty in the same card
When an “optional enrichment layer” moves from non-goal into `code_atlas/`, update PLAN §1,
CONVENTION layout, and R1.4’s SRP inventory in the same PR — otherwise review blocks on R7.2
even when the runtime is correct.

*Claim `040-C1` — Doc inventory lags new core module. type 5 project-ground-truth · normative ·
area: docs / R7.2 / R1.4 · confirmed · stays in lessons.*
*Evidence: reviewer findings 1–3 on `5926e2d`; fixed in `794b55d`.*

## 039 — Stub roots must bypass ignore *and* hash-gate on incremental
`vendor/` is a built-in directory exclusion, so `.codeatlasignore` negation cannot re-include it —
stub indexing needs a separate filesystem walk (`collect_stubs`). Those paths are also outside
`git ls-files`, so incremental must hash-gate the whole stub set (not only `changed ∩ stubs`), or
disk edits never refresh and enabling stubs mid-life never indexes new files (R4.2).

*Claim `039-C1` — Incremental stub refresh is hash-gated, not git-named. type 5 project-ground-truth
· normative · area: indexer / R4.2 · seen 039 · confirmed · stays in lessons.*
*Evidence: reviewer finding on `changed_set & stub_set`; fixed in `ddcfe77` +
`test_incremental_hash_gates_stub_edits`.*

## 038 — Edge-shaped hop dicts trip R3.2 unless keys are assigned one-by-one
Building a hop `{source_qname, target_qname, kind, confidence_tier, line}` as one dict literal
fails `test_contract_sole_source` (≤1 EDGE_FIELDS string per collection). Assign each key in its
own statement (or concatenate single-field key tuples), matching the impact/reachability pattern.

*Claim `038-C1` — Path hop shaping must not multi-key EDGE_FIELDS in one literal. type 5 project-
ground-truth · normative · area: store / tools / R3.2 · seen 038 · confirmed · stays in lessons.*
*Evidence: sole-source fail on store.py / explain_path.py; fixed via per-statement hop keys.*

## 037 — A guard that checks a formula against itself cannot catch a unit error in its input
037's A/B summed `call_delta` over **4** measured questions, then `verdict()` multiplied that
aggregate by a call count — so the published break-even was in *4-call batches*, wrong by ~4× (8.9 vs
35.7). The existing guard fed `verdict()` hand-picked deltas and asserted its algebra, which was
self-consistent and stayed green. **Normalize where the number is produced** (`measure()` publishes
`call_delta_per_call`) and write the guard against the **unit**, not the arithmetic. The tell was in
the prose, not the code: one sentence read "~7 tokens per call" and "break-even 8.9", and 241/7 ≈ 34.
When a derived figure and its own stated rate disagree, the figure is wrong — divide it out by hand
before publishing it.

*Claim `037-C1` — Aggregate-vs-per-unit must be normalized at the producer, not the consumer. type 5
project-ground-truth · normative · area: benchmark / tokens-to-answer / A-B measurement · seen 037 ·
confirmed · stays in lessons.*
*Evidence: reviewer round 1 finding 1; `call_delta 27` over 4 questions; corrected 8.9 → 35.7 calls;
regression guard `test_break_even_is_in_calls_not_in_measured_batches` fails `10.0 vs 40.0` when the
defect is reinstated (re-mutated by the round-2 reviewer).*

*Claim `037-C2` — A decision's argument must be withdrawn when its number moves, not re-fitted. type
5 project-ground-truth · normative · area: mango / review / recorded decisions · seen 037 ·
confirmed · stays in lessons.*
*Evidence: Decision §1 ("crossover ~9, an agent passes it inside one task") no longer held at ~36
calls and was struck rather than re-argued; the verdict was re-grounded on "no net win at all"
(−234…+434 tokens) plus C3 and R1.2, and the round-2 reviewer judged the result honest.*

## 033 — Split vocab-vs-emit when a later ticket owns emission
When Scope lists an enum member (e.g. `index_stale`) that a dependent ticket (035) will emit, refine
must record **W1 vocab present** and **W2 no emit-proof this card**. Otherwise a ticket-blind
challenger scores emission as **not met** against the raw ticket and looks like a Gate-4 miss.

*Claim `033-C1` — Enum members deferred to a paired ticket need W1/W2 at refine. type 5 project-
ground-truth · normative · area: mango / refine / reason-codes · seen 033 · confirmed · stays in
lessons.*
*Evidence: challenger 7cf518c3 row 1b; ASSUMED Option 1; task 035 pairs with 033.*

## 030 — Alias remap must rewrite `Class::method`, not only class FQNs
`alias_targets` maps alias class → real class. CALLS/NEW often carry `\Alias::method`. Remapping
only exact class keys leaves method edges dangling; rewrite the class portion before `::` so
`find_callers`/`find_references` under Real see Alias users.

*Claim `030-C1` — Alias remap rewrites the class portion of member qnames. type 5 project-ground-
truth · normative · area: resolver / aliases · seen 030 · confirmed · stays in lessons.*
*Evidence: resolver `_lookup_raw` rpartition; proving test Aka::ping → Real::ping.*

## 029 — Innermost class owns `parent::`, not an outer ancestor
`enclosingParentQname` must stop at the first `Class_` in the scope stack. Walking past a
null-`extends` class (e.g. anonymous nested inside `Outer extends Base`) falsely attributes
`Outer`'s parent to the inner class — a RESOLVED-eligible lie (R5.2). Return null when the
innermost class has no extends and leave `\parent::…` as today.

*Claim `029-C1` — parent:: resolution must not walk past an innermost Class_ with null extends. type
5 project-ground-truth · normative · area: php-adapter / receiver-resolution · seen 029 · confirmed
· stays in lessons.*
*Evidence: review finding on feat/029; NestedOuter fixture; Visitor.php enclosingParentQname.*

## 028 — Prefer `parsed_ok` over a parallel meta parse-failure counter
When a ticket asks for `parse_failures` "if the build does not already persist this", check existing
aggregates first. `files.parsed_ok` already feeds `GraphStore.counts()["failed"]`; a second `meta`
counter can drift from the file rows (R4). Alias the status field (`parse_failures`) to that count
on `standard` and keep the existing `failed` key for minimal byte-identity.

*Claim `028-C1` — Parse-failure status reads `files.parsed_ok` via `counts()["failed"]`, not a
parallel meta counter. type 5 project-ground-truth · normative · area: index-status / parse-health ·
seen 028 · confirmed · stays in lessons.*
*Evidence: ticket 028 R3 conditional; `code_atlas/store.py` counts(); indexer marks `parsed_ok=0`.*

## 016 — Dependents must be reparsed, not reconstructed
Hash-skipping dependents made `file_paths_targeting` dead work: a dependent is unchanged by
construction, so its hash always matches and it never reached the adapter. Reconstructing its edges
via `unlink_targets` (and collapsing HEURISTIC siblings) then lost adapter confidence tiers and
legitimately duplicated keys — diverging from a full rebuild (R4.2). **Always reparse dependents**;
hash-skip only unchanged *changed* paths. `replace_file_rows` restores adapter output verbatim.

Also: fold paths leaving `collect` (rename sources, newly ignored) into affected qnames *before*
reconcile — `git diff --name-only` names only the rename destination — and union the working tree
vs `HEAD` into the incremental path set so uncommitted edits are not a silent no-op.

## 014 — `code-atlas --help` is not an install smoke test
FastMCP's entry point always calls `.run()` (stdio). Passing `--help` still starts the MCP transport
and will hang CI waiting on stdin. Prove a non-editable install with `importlib.metadata` (version +
console_scripts entry) and an import of `TOOL_NAMES`, never by invoking the server binary.

## 014 — `LIKE ESCAPE '\\'` breaks PHP qnames
Namespace filters that use SQL `LIKE` with backslash as the escape character mis-parse every `\` in
a PHP FQN (`\App\Models\…`). Use a rare escape character that does not appear in qnames (e.g. `!`)
and escape only `!`, `%`, and `_`.

## 012 — Planted tmp_path negative controls must not use relative_to(ROOT)
AC2 plants live under pytest `tmp_path`, which is outside the repo. Calling
`path.relative_to(ROOT)` on those plants raises `ValueError` and breaks the proof that the
grep-gate fails on a planted hit. Assert on `Path` identity (or root the plant under the repo).

## 025 — NEW must peek anonymous qnames without registering them
`enterNew` and `enterAnonymousClass` both need the same H1 qname. If both call a registering
`anonymousQname()`, the Class_ node gets a spurious collision suffix even when it is the only
anonymous class on that line. Peek (`register: false`) on the NEW edge; register only when declaring
the Class_ node. Same-line *true* collisions append `:col` from `getStartFilePos()` (ticket C1) —
not an ordinal, which would rename later same-line declarations when one is inserted earlier.

## 008 — Proving-test names must not overclaim the path shape they assert
Review caught that `…_results_stay_repo_relative` asserted host-**absolute** `ParseResult.path` after
wire rebase (Approach §3 keeps the **caller** path). The relative half was the real repo-relative
proof; the name lied about the absolute half. Rename (or split asserts) so the test title matches
what each half actually checks — R6.1 proofs and CONVENTION “repo-relative” claims stay honest.

## 011 — Never promote HEURISTIC to RESOLVED just because a name is unique
PR review caught that `_resolve_symbol` set the tier from hit count alone. An adapter-emitted
`HEURISTIC` edge whose `target_raw` matched one qname became `RESOLVED`. A unique name does not make
a guess certain — M6 impact will trust these tiers. Fix: take the weaker of (incoming, computed).

**Also deferred to M4 (task 015):** per-edge SQLite commits + materializing all unresolved edges, and
top-N name-match fan-out on common method names (`get`/`save`) exploding edge counts.

## 011 — A clean `Reviewed at` does not survive tip commits landed after it
Task 011's review was clean at `cf445e4` (resolver change-list only). Teammate commits for
`AGENTS.md` / `.mailmap` then landed on the same branch. Finalise's stale-review guard correctly
refused: the marker is a **file-set** claim, not a "we reviewed this ticket once" claim. Keeping the
tip without a new `Reviewed at` covering HEAD is a **human override**, not a cleared gate.

**Fix:** either (a) re-review the full tip and rewrite the marker, or (b) land teammate docs/chore
work on a separate branch/PR so the feature marker stays valid.

## 010 — The same thread rule that enforced a design in 009 dictated the design in 010
Task 009 found that `sqlite3` binds a connection to its creating thread, and treated it as a free
guarantee: R4.3's single writer could not be broken by accident. Task 010 met the same fact from the
other side. FastMCP registers a synchronous tool with `run_in_thread=True` by default, so **every**
tool call runs on a worker thread — a `GraphStore` opened when the server was built raises
`ProgrammingError: SQLite objects created in a thread can only be used in that same thread` on its
first use, in every call, forever. The obvious shape (build the server, hold the store, serve) does
not work at all.

So each tool opens its own store inside the call, and `get_index_status` opens none when there is no
database file. The lesson is not "sqlite is thread-affine" — 009 already recorded that. It is that a
constraint discovered as a *guarantee* in one task can be the thing that *rules out* the natural
design in the next, and only a spike against the real library says which. This one was tagged
`novel-untested` at design and spiked before Gate 2; it came back **false**, and the ten-line spike
that killed it cost less than the rewrite would have.

**Fix:** when a task hands work to a third-party runtime, spike *where that runtime runs your code*
before designing what your code holds on to.

## 009 — The runtime may already enforce the rule you were about to prove by convention
R4.3's "single SQLite writer" read like a discipline the indexer had to keep. It is not: `sqlite3`
binds a connection to the thread that created it, so a worker thread that tried to write through the
build's store raises `ProgrammingError` — loudly, before a single row is touched. The design was
better for finding out: the fan-out needs no lock, no write queue, and no review vigilance, because
the failure mode it was guarding against cannot compile past the first call.

The general lesson is about **when** to check. This was a `novel-untested` assumption tagged at
design and spiked *before* Gate 2, not discovered at execute. Two of the five spikes changed the
design, and this one changed it by coming back **false** — which is the whole point of tagging an
assumption instead of asserting it.

## 009 — A negative control can indict the code instead of the test
Five mutation controls ran against `full_build`; two came back green, and they meant opposite things.
Deleting the `sorted()` from collection broke nothing because the fixture tree happened to be
discovered in order — a **test** too weak to see its own subject, fixed by shaping a tree the walk
provably reaches out of order. Deleting the per-build `rebuild_search_index()` also broke nothing,
but no test could ever have caught it: the schema's triggers already keep `nodes_fts` current, so the
call was a full re-index that changed nothing. That one indicted the **code**, and it was removed.

So a green negative control is a question, not a verdict: *can* a test see this, or is the line
unreachable by construction? The first answer costs a better fixture; the second costs a deletion —
and on a 112k-file repo, that particular deletion is a whole FTS rebuild per build.

## 007 — A stream protocol inherits the host's `php.ini`, so "it works here" proves nothing
Two ini settings silently corrupt a JSONL protocol, and neither shows up on a developer machine.
`display_errors` defaults to **stdout** on many builds, so a PHP notice lands *between two protocol
lines* and the driver reads it as a reply; `output_buffering` holds `echo` output until the process
exits, deadlocking a lock-step reader. Both are host state, so the same file yields different results
on two machines — exactly what R4.2 forbids. **Fix:** force `display_errors` to `stderr` before
anything is written, and write replies with `fwrite(STDOUT, …)`. Note the trap: the design approved
`fflush(STDOUT)` as "immune to any host ini" and that was **false** — `echo` has already entered PHP's
*output buffer*, which neither `fflush()` nor `flush()` releases. Only bypassing `echo` works. Prove a
buffering fix by reading **while the child still runs**; at exit every buffer flushes, so a
post-mortem read passes no matter what.

## 007 — A language's natural empty value may not be the contract's
`json_encode(['capabilities' => []])` yields `{"capabilities":[]}` — a JSON **array**. The contract
requires an object, so the core rejected the handshake with a loud startup error naming
`meta.capabilities`, pointing the reader at the core rather than at the one adapter line responsible.
PHP has one array type for both shapes; `new stdClass()` is needed to get `{}`. **Fix:** spike the
handshake against the real validator before writing the loop — the design phase caught this, and had
it slipped to execute it would have read as a driver bug. Generalises to every adapter: an empty map,
an empty list, and a null are three different wire values, and a language that conflates any two of
them will encode the wrong one by default.

## 024 — A rule enforced only by a lifecycle gate is unenforced for work that skips the lifecycle
`AGENTS.md` says no PR opens without the task's token spend in **both** the working-doc ledger and
the BACKLOG table. Tasks 001–006 complied — because mango's `finalise` has a ledger-completeness
gate. Task 024 was done outside the five-phase lifecycle, so nothing checked, and PR #14 opened with
no token row and a status left at `in-progress`. The rule was never *disagreed* with; it had no
enforcement outside one tool's happy path. **Fix:** `tests/test_backlog_bookkeeping.py` asserts both
rules from the repo itself, negative-controlled three ways (delete the row, desync a status, write a
spend cell with no number). Generalises: a process rule whose only enforcement is a step inside one
workflow is **optional by construction** — put the check where the artifact lives, not where the
process happens to run.

## 006 — An `instanceof` narrow that falls through to null erases the difference between "absent" and "unhandled"
The PHP visitor read a parameter's type as `$param->type instanceof Node\Name ? fqn(...) : null`. That
looked right and passed both fixtures, because both typed parameters happened to use *class* types. But
`string`, `int`, `bool` and every other scalar hint arrive as `Node\Identifier`, so they fell through to
`null` — and in the emitted JSON, `"type": null` is exactly what an **untyped** parameter looks like. The
adapter was not deferring the case; it was reporting the wrong answer, and nothing could tell. A
ticket-blind challenger found it by writing its own probe file with a scalar hint. **Fix:** when mapping
a foreign AST or schema into your own vocabulary, an `instanceof` chain whose fallback is `null` needs
either exhaustive arms or a loud fallback — never a silent one that collides with a legitimate value.
Generalises: a partial mapping is only safe when "I did not handle this" is **distinguishable in the
output** from "this was not there". Ask of every `?:` default whether some real input already produces
that same value; if so, the branch cannot be audited from the data.

## 006 — The first vendored dependency turns a repo-wide grep-gate into a false positive
`ci.yml`'s R2.2 gate greps `adapters/` for framework names. It was green for five tasks because
`adapters/` was empty; the first `composer install` put 280 files there, and **Composer's own
`vendor/composer/ClassLoader.php` documents itself with a `Symfony\Component` example** — so a
guardrail about *our* source failed on a dependency nobody here wrote. The same run had
`test_sql_confinement.py` sweeping all 280 dependency files for the string `code_atlas`. **Fix:**
scope every guardrail grep to authored source (`--exclude-dir=vendor --exclude-dir=node_modules`)
and then guard the scoping (see 002 and **R6.5**), in the change that introduces the first
dependency — that is the change that creates the collision. Generalises: a text-grep guardrail's
blast radius is a **directory**, and directories grow third-party content the moment a package
manager runs.

## 005 — A subprocess seam fails by silence and by chatter, not by errors
Two failure modes of a long-lived adapter process are invisible in the happy path and neither raises.
**Chatter:** with `stderr=PIPE` left undrained, a child that writes more than a pipe buffer (~64 KB)
blocks writing while the driver blocks reading stdout — a spike reproduced it with 200 KB and got no
reply in 3 s. `stderr=STDOUT` is worse: it corrupts the protocol stream. Only `DEVNULL` or a real file
is safe, and a PHP adapter emitting warnings makes this the *normal* case, not an exotic one.
**Silence:** a child that stays alive and simply never answers hangs a blocking `readline()` forever —
and it does so at `start()` (waiting for the handshake), not only at `parse()`. The analysis had
recorded the hang as a `parse()`-only exclusion; execute found the wider truth when a fixture mode that
went mute wedged the whole suite. **Fix:** never leave a subprocess pipe undrained; treat *silence* as
a first-class failure mode with its own deadline, and when deferring it say which calls it can strike,
not just the obvious one. Generalises: for any IPC seam, enumerate what happens when the peer says
**too much** and when it says **nothing** — those are the two that hang rather than throw, and a test
suite that only feeds well-formed errors will never meet either.

## 005 — A ticket-blind agent can read the working doc without opening it
The challenger is kept honest by *withholding* the working doc: it is handed the raw ticket text plus
the diff and told not to read `docs/tasks/`. It obeyed — and still saw the design. A `git grep` for
`--server` across the repo returned matching lines *from* the working doc, including a "RATIFIED (Q2)"
rationale, so the author's reasoning landed in front of it before it had formed its own view on that
requirement. It disclosed this itself; six of its seven other verdicts were unaffected. **Fix:** the
blind-agent brief must exclude the tickets directory from **every search**, not just from direct reads
(`git grep ... -- ':!docs/tasks/'`, `grep --exclude-dir`), and the agent should be told to report a
leak rather than quietly continue. Generalises: an information barrier enforced as "don't open that
file" leaks through every tool that reads files *without opening* them — grep, search indexes, IDE
symbol lookup. Scope the barrier to the **content**, not to the act of opening; and since the guarantee
is procedural, report it as procedural rather than as proof.

## 004 — A schema object that exists is not a schema object that runs
`tests/test_store.py` asserted every DDL object was registered in `sqlite_master`, and that assertion was
read as if it also proved each object *works*. It does not. The ticket-blind challenger replaced the body
of the `nodes_au` FTS trigger with a reference to a nonexistent column and **the whole suite still
passed**
— because `GraphStore.replace_file_rows` only ever DELETEs then INSERTs, so nothing in the codebase fires
an UPDATE on `nodes`. A broken trigger would have shipped green. **Fix:** for any schema object no code
path currently exercises (trigger, `DEFAULT`, `CHECK`, `ON DELETE`), write a test that *fires* it
directly
in SQL, and keep the object rather than deleting it as dead code when it closes an invariant — a mirror
with a hole desyncs silently the first time a later task takes that path. Generalises: **existence tests
and behaviour tests are different tests**, and mutation is the cheap way to tell which one you actually
wrote — break the thing on a copy and see whether anything goes red. The same run also caught a related
self-report: the task's own matrix claimed `busy_timeout` was asserted when nothing asserted it.

## 036 — Distribution hooks that promise exit 0 must wrap config load too
A Claude Code PostToolUse script documented as "always exits 0" still raised when
`load_config` saw an unpaired `CA_HOST_ROOT`. Soft-fail only around `reparse_file` is not
enough — wrap imports + config + reparse. Relative path containment must `resolve()` under
the project root (``../`` escapes are not no-ops).

## 035 — Missing on-disk paths are stale; planted fixtures must write matching bytes
`FreshnessGuard.ensure` returns `"stale"` when `(root/path).is_file()` is false so production
never asserts `reason=ok` for a deleted indexed file. Planted-store nav tests therefore write real
bytes (and the matching content hash) in `seed_file(..., root=)` — a shared short-circuit that
trusted the index for missing paths caused the trust bug 033 closed. Adapter/DB failures during
`reparse_file` also degrade to `"stale"` instead of crashing the read tool.

## 073 — Zero-hit freshness cannot invent a subject path
Read-through (035) only repaired paths already on the answer. A brand-new symbol in a drifted file
matched nothing, so `ensure_qname` / `search_symbol` returned a confident empty without reparsing.
**Fix:** miss-repair spends `READ_THROUGH_CAP=1` on the sole dirty indexed tracked file; multiple dirty
files emit `index_stale` + `try_instead=file_outline` instead of guessing. Requires git
`dirty_paths`. Generalises: result-driven repair is incomplete without a documented miss path.

## 065 — Inbound includes cannot be counted by target_qname
`include_graph(direction="imported_by")` used to emit `unresolved_includes: 0` because the outbound
counter is skipped for that direction — a confident zero that is structurally always zero. Unlinked
inbound edges have empty `target_qname`, so they are invisible to `edges_by_target`. **Fix:** omit the
field for `imported_by`, and only claim `relationship_not_modelled` when a cheaper basename
`instr(target_raw, …)` proxy finds evidence. Generalises: a counter that is unanswerable in one
query direction must not print zero; absent beats a structural lie.

## 004 — `git checkout -- <file>` restores the committed state, so it deletes uncommitted work
While negative-controlling the R3.2 guard, a violating literal was appended to `code_atlas/store.py` and
then reverted with `git checkout -- code_atlas/store.py`. The implementation was **not yet
committed**, so
the checkout restored the one-line stub from `main` and the whole module was gone; it had to be
rewritten.
The first negative control had worked only because the file it mutated (`config.py`) was unmodified
in the
working tree. **Fix:** commit the work **before** running any guard experiment that mutates tracked
files,
and restore from a `cp` copy (verify with `sha256sum`) rather than from git. Generalises: `git
checkout --`
is not an undo for *your* edit — it is a reset to the index/HEAD, and its blast radius is every
uncommitted
change in that file.

## 003 — The R1.1 grep-gate fires on ordinary English, not just on code
The CI guardrail for "no language branches in the core" is
`grep -rEn 'if[^\n]*\blanguage\b[^\n]*==|match[^\n]*\blanguage\b' code_atlas/`
(`.github/workflows/ci.yml:49`). Its second alternative has **no code anchor**: any line under
`code_atlas/` where the token `match` appears *before* the word `language` fails the build — including
a plain comment or docstring like `# match the language name to its env var`. The reverse order
(`language … match`) is safe. **Fix:** when touching the core, phrase prose so `language` precedes
`match` (or avoid one word), and run the gate's exact regex locally before opening the PR — a green
`pytest`/`ruff`/`mypy` says nothing about it. Generalises: a guardrail expressed as a text grep over
source will also match the *prose* in that source, so treat comments and docstrings as inputs to
every grep-gate, not just the code.

## 002 — A guard written before its consumers exist must be negative-controlled
Task 002's AC2(b) ("no field lists duplicated in store/indexer") was **vacuously true**: all five
schema-consuming modules were one-line stubs, so any guard passed while proving nothing. **Fix:**
inject a real violation (`COLUMNS = ["kind", "name", …]` appended to `store.py`), confirm the guard
fails, remove it, confirm the file is byte-identical — and assert the guard's own inputs are
non-empty (`len(VOCABULARY) == 38`, `len(consumers()) >= 5`) so it cannot silently degrade later.
Generalises (now **R6.5**): when an AC is satisfied only because the thing it constrains does not
exist yet, say so and either negative-control the guard or record the vacuity.

## 001 — Fold a mid-task governance request into the ticket's scope, don't ride it on the branch
When a user asks for a repo-wide rule change mid-task (here: the "Token usage on PR" rule in
`AGENTS.md` + `docs/BACKLOG.md`), the ticket-blind challenger and the reviewer both read it as
untraceable scope creep — it maps to no ticket requirement. **Fix:** add it to the task's
Scope/Deliverables + a matrix row (task 001 → R6 + change-list item 8) with a one-line rationale, so
every hunk still traces to a requirement. Splitting it into its own docs ticket is the alternative;
either way, never let a change ride the branch untraceable to a row.
