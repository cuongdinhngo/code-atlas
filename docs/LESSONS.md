# Lessons — code-atlas

The **claim corpus** the learning loop reads. One atomic claim per record
(`type` · `handle` · `status` · `seen` · `evidence` · `destination`); recall greps `handle:` and
**recurrence is the number of distinct ticket keys in `seen:`**, unioned across every claim sharing a
handle. Newest first.

**The per-ticket narrative was removed.** Every section retold what that ticket's
`docs/tasks/NNN_*.md` and its `TOKEN_LEDGER.md` row already hold, and no machine path read it —
`RECALL:` greps handles, `/mango:promote` reads claims. `git log --follow -- docs/LESSONS.md` is the
history. This is R7.6 applied to this file, the same cut 218 made to `BACKLOG.md`.

**Retired claims are an index, not records.** A claim whose class a rule now carries is listed once
at the bottom — id, handle, rule — because the rule book cites claim **ids** and those citations must
still resolve. `RECALL:` skips them; the rule surfaces the class instead.

**One claim record per handle.** Where a class was filed under several ids the ids are aliased in one
heading and the `seen:` lists unioned — three separate blocks made a recurrence-4 class read as three
recurrence-1 notes.

## Class index — read this before proposing a new rule

Every type-2 handle at recurrence ≥ 2. **Twenty-one are binding rules or brief entries**; the honest
move on a new sighting is to bump `seen:`, not to write a fresh claim. **One is not**:
`one-field-two-questions`, rejected 2026-08-30 because its two sightings point opposite ways.
The 2026-08-30 promotion pass closed the six that were open — two of them by **widening an existing
rule** rather than adding a near-duplicate (P2), and one by finding the rule already there.

| handle | rec | tickets | where it landed |
|---|---|---|---|
| `derived-not-listed-invariant` | 22 | 087–088, 093, 095–097, 099–102, 121, 122, 127, 132, 147, 148, 128, 180, 187, 191, 184, 022 | **R6.7** |
| `prove-the-guard-fails` | 35 | 087–089, 093, 096, 099–101, 121, 122, 132, 147, 148, 128, 019, 185, 186, 174, 170, 175, 181, 182, 188, 189, 190, 187, 191, 184, 192, 022, 194, 195, 224, 228, 229, 230, 250 | **R6.5** — 190 is the *other* side of it: not *was it seen failing?* but *did it fail for the thing it forbids?* |
| `gate-the-disclosure-on-its-condition-not-the-row-count` | 2 | 192, 238 | **proposed** → `docs/ENGINEERING_RULES.md` (238; `/mango:promote`) |
| `do-not-attest-past-the-payloads-resolution` | 13 | 087–089, 100–102, 107, 239, 242, 246, 250, 252, 258 | **R5.6** — promoted 2026-08-27 (re-adjudicated); 239: FK indexed but Column search hit omitted it; 242: `params` indexed (231) but no nav tool returned them |
| `sweep-scope-cannot-attest-the-gate` | 3 | 255, 251, 258 | **proposed** → `docs/AGENT_BRIEF.md` (2026-09-12; three sightings in one merge round, each a pre-PR self-check attesting a check the sweep never ran) |
| `fixture-shape-begs-the-question` | 11 | 084, 086, 103–106, 121, 183, 185, 190, 191 | **R6.3** — widened 2026-08-23, provisional |
| `try-instead-tool-name` | 7 | 092, 093, 100–102, 245, 252 | **R5.4** |
| `count-pin-in-blast-radius` | 11 | 085, 087–089, 175, 184, 022, 194, 196, 199, 237 | **AGENT_BRIEF P5** — promoted 2026-08-27; P5 needs the invariant, not the spelling (022) — 194 adds that a change can move MORE THAN ONE invariant, and 196 that a pin written as a bare LITERAL is invisible to a trace that greps the invariant's name; 237 is the *new-module* dimension — adding `code_atlas/preflight.py` moved the core-module count pinned in `test_core_is_language_agnostic.py` + `test_sql_confinement.py`, and the Gate-2 blast-radius trace did not grep for it |
| `source-the-caveat-from-the-computation` | 6 | 100–102, 122, 127, 189 | **R5.5** |
| `re-verify-the-assumption-on-a-new-path` | 3 | 102, 107, 122 | **AGENT_BRIEF P6** — promoted 2026-08-27 |
| `re-run-the-sweep-after-the-last-edit` | 3 | 100–102 | **AGENT_BRIEF P4** |
| `route-must-answer` | 5 | 093, 101, 102, 188, 245 | folded into **R5.4**'s falsifier — 188 is the first sighting of its *other* direction: a route that became answerable; 245 is shared-hint prose that must stay true at every attach site |
| `rank-before-truncate` | 3 | 067, 126, 180 | **R5.8** — promoted 2026-08-30 |
| `guard-asserts-rendered-not-shipped-bytes` | 2 | 116, 127 | **R6.9** — promoted 2026-08-30 |
| `sibling-meta-non-int` | 3 | 092, 095, 174 | **R1.7** |
| `record-the-deviation-as-a-deviation` | 2 | 101, promote-2026-08-15 | **AGENT_BRIEF P3** |
| `one-rule-for-every-subject-slot` | 6 | 102, 122, 183, 186, 179, 187 | **R1.8** — promoted 2026-08-27 |
| `one-field-two-questions` | 2 | 189, 022 | open — **rejected 2026-08-30**: the two sightings point opposite ways (189: do not add a field when the payload already carries the axis; 022: do not overload one), so the handle may be over-grouping. Re-propose on a third, independent sighting |
| `read-the-syntax-not-the-text` | 4 | 190, 187, 192, 199 | **R6.7** — widened 2026-08-30 (a text sweep is not a derivation); 199 adds that prose SAYING a field is absent trips a scan looking for it |
| `an-aggregate-outlives-the-world-that-named-it` | 2 | 183, 195 | **AGENT_BRIEF P7** — promoted 2026-08-30 |
| `two-syntaxes-two-paths` | 3 | 019, 184, 022 | **R6.2** — it was already there, citing `019-C2`; the 2026-08-30 pass found it by grepping the CLAIM ID, not the slug, and extended the citation |
| `ac-failure-mode-needs-the-right-guard` | 2 | 085, 107 | **R6.8** — promoted 2026-08-27 |
| `own-only-what-you-wrote` | 2 | 088, 089 | **R5.7** — promoted 2026-08-27 |
| `skip-dynamic-means-unlinkable` | 3 | 094, 096, 022 | **R5.2** — re-adjudicated and widened 2026-08-30; the 2026-08-15 rejection reasoned from a sighting that *bound* a design, and the third bound one **wrongly** |
| `deepest-wins-is-not-a-membership-test` | 3 | 130, 131, 197 | **R1.9** — promoted 2026-08-31; 199 *used* it (exact-equality membership, proven by a negative control), which is a use and not a fourth sighting |
| `assert-the-consumer-not-the-field` | 2 | 198, 196 | **R6.9** — widened 2026-08-31 rather than duplicated (P2): the rule already asserted at the renderer, and this moves it one step earlier, to the field |
| `version-the-document-that-moved` | 2 | 197, 196 | **R3.5** — promoted 2026-08-31; it generalises R3.1 to the three versioned documents that rule does not name |

**Ratified 2026-08-30 — all 17, on a condition the brief already stated.** The rule book and the
brief both said a rule stays `PROVISIONAL` *"until a second incident confirms the shape"*, and every
one of the 17 stood at recurrence ≥ 2 in the table above — the lowest at 2 (`own-only-what-you-wrote`,
`ac-failure-mode-needs-the-right-guard`, `guard-asserts-rendered-not-shipped-bytes`,
`an-aggregate-outlives-the-world-that-named-it`), the highest at 22. So the tag was not moved on
anyone's say-so; it was moved because the condition it named had been met, in some cases fifteen days
earlier. `Provisional` stays in both vocabularies for the next promotion.

**Six classes were closed 2026-08-30** — see [[promote-2026-08-30]]. Two were **widenings**
(`skip-dynamic-means-unlinkable` → R5.2, `read-the-syntax-not-the-text` → R6.7), two were new
(`rank-before-truncate` → R5.8, `guard-asserts-rendered-not-shipped-bytes` → R6.9), one was a new
brief entry (`an-aggregate-outlives-the-world-that-named-it` → P7), and one **was already recorded**
(`two-syntaxes-two-paths`, in R6.2 since 019).

**The three overdue classes were promoted 2026-08-27**, once their split-across-ids `seen:` lists were
unioned (the under-count `PROM-C1` names): `do-not-attest-past-the-payloads-resolution` → **R5.6**
(re-adjudicating the stale 2026-08-16 rejection), `count-pin-in-blast-radius` → **P5**,
`re-verify-the-assumption-on-a-new-path` → **P6** — with `one-rule-for-every-subject-slot` → **R1.8**,
`ac-failure-mode-needs-the-right-guard` → **R6.8** and `own-only-what-you-wrote` → **R5.7**.
`fixture-shape-begs-the-question` left this list on 2026-08-23: widened into **R6.3** rather than
proposed as a new rule, because R6.3 already owned cross-repo validation and P2 asks for the widening.

**A second under-count, one level up again (132).** Both rules' own `seen:` lines had fallen behind
this index — R6.7 listed 8 of 13 keys and R6.5 listed 5 of 10. P1 keeps the *claim's* list honest and
nothing kept the *rule's*, so the rule a reader consults under-reported its own recurrence. Both are
now reconciled to this table.

## Live claims

### 251-C1 · 255-C1 · 258-C1 — A verification sweep scoped to the ticket's own tests cannot attest a repo-wide check

- type: 2 (process) · handle: `sweep-scope-cannot-attest-the-gate`
- status: proposed (awaiting human confirm) — **recurrence 3**, all in the 2026-09-12 merge round
- seen: 255, 251, 258
- sharpens `stamp-evidence-with-the-tree-under-review` rather than superseding it: 200/201 learned
  *which tree* the evidence describes; this is *which scope* — the right tree, the wrong breadth.
- evidence: each branch's sweep ran its own proving test file, and each pre-PR self-check then
  reported the repo-wide checks green. 255/#332 merged with three suites red
  (`tests/contract/test_tool_parity.py[sql:find_references]`, two `test_references_construct_agreement.py`
  AC3 cases); 251/#336 shipped `PLAN.md` over its ceiling with `test_doc_size_budget.py` claimed
  green; 258/#337 shipped `mypy` red and `test_build_report_counts.py` red. Actions reports `fail`
  in ~3 s without running, so nothing downstream catches it either (AGENTS.md, *Before a PR*).
- destination: `agent_brief_path` — the sweep names the checks it ran, and a self-check attests only those.

### 251-C2 — A vocabulary that becomes a tool parameter needs a `Literal`, not a tuple beside a `str`

- type: 2 (code) · handle: `literal-publishes-the-choice`
- status: proposed (awaiting human confirm)
- seen: 251
- evidence: `confidence_tier` shipped typed `str | None` with `CONFIDENCE_TIERS` a hand-written
  tuple, so the MCP input schema published no choice and the three spellings were discoverable only
  by triggering the `ValueError`. `contract.ConfidenceTier` is now the typing SSoT and the tuple is
  `get_args` of it — what `NodeKind`/`NODE_KINDS` (056) and `detail_level` already do.
- destination: stays in lessons_path (recurrence 1; R3.2 carries the derivation half already)

### 258-C2 — Rows the resolver declined to link are candidates, whatever they cost to find

- type: 2 (code) · handle: `do-not-attest-past-the-payloads-resolution`
- status: proposed (recurrence of R5.6 — bump `seen:` only; rule already carries the class)
- seen: 258
- evidence: the proximity expansion returned unresolved same-named CALL sites in `results` under
  `reason: ok`. Same shape as 252's member union, so it takes 252's answer: `proximity_candidates`,
  never `ok`, each row naming `candidate_of`. The ticket's AC2 binds the rows and the true
  `total_count`; only the label was missing.
- destination: docs/ENGINEERING_RULES.md (already R5.6)

### 250-C1 — An edge-attached hit key is not a stored extra key

- type: 2 (code) · handle: `edge-attached-is-not-stored-extra`
- status: proposed (awaiting human confirm)
- seen: 250
- evidence: `search_symbol._hit` attaches `references` / `references_unresolved` from stored
  `REFERENCES` edges; Column.extra does not hold them. AC3 required always-present lists on the
  raw-fields view so empty ≠ "tool does not return FKs".
- destination: stays in lessons_path

### 252-C1 — A member-caller union is not a modelled class-reference

- type: 2 (code) · handle: `do-not-attest-past-the-payloads-resolution`
- status: proposed (recurrence of R5.6 — bump `seen:` only; rule already carries the class)
- seen: 252
- evidence: class-level `find_references` now returns inbound CALLS/NEW on CONTAINS children as
  `reason=via_members`, never `ok`. Empty union is still `via_members`, not `relationship_not_modelled`.
- destination: docs/ENGINEERING_RULES.md (already R5.6)

### 246-C1 — A count of drifted files is not evidence about a named subject's absence

- type: 2 (code) · handle: `do-not-attest-past-the-payloads-resolution`
- status: proposed (recurrence of R5.6 — bump `seen:` only; rule already carries the class)
- seen: 246
- evidence: `ensure_miss` refused every zero-hit when `len(dirty)>1`, including path-named subjects
  whose own file was current. Fix: subject-scoped ensure + `subject_file_checked` reason +
  `other_indexed_files_drifted`. R5.6.
- destination: docs/ENGINEERING_RULES.md (already R5.6)

### 246-C2 — A miss-shaping helper that resets `reason` must run before a weaker-tier finalizer

- type: 2 (heuristic) · handle: `finalize-after-shape`
- status: proposed (awaiting human confirm)
- seen: 246
- evidence: challenger round 2 — `finalize_subject_checked_miss` before `shape_exact_miss` lost
  `subject_file_checked` because shape forced `no_such_symbol`. Fix: finalize last on find_* miss paths.
- destination: stays in lessons_path


### 242-C1 — A field already in the graph is still invisible until a nav tool returns it

- type: 2 (code) · handle: `do-not-attest-past-the-payloads-resolution`
- status: proposed (recurrence of R5.6 — bump `seen:` only; rule already carries the class)
- seen: 242
- evidence: 231 stored `params` and stamped `capabilities_by_language`; only `class_diagram`
  rendered them for class members. Free `Function` / stored-proc signatures stayed unreachable
  by every nav tool. Closed by surfacing `params` on `read_symbol` at `standard` with the same
  honesty predicate. R5.6.
- destination: docs/ENGINEERING_RULES.md (already R5.6)

### 243-C1 — A capability census that only rides `verbose` never reaches the agent that calls `get_index_status` at default `standard`
- type: 2 (heuristic)
- status: proposed (awaiting human confirm)
- evidence: `get_index_status.py` attached `cross_language` only via `_attach_edge_health_by_language` after the standard early return; field retro round 17 called standard as tool #1 and never saw the census. Fix: `_attach_cross_language_summary` before that return (task 243). Recurrence (244): the same first-call channel also omitted the already-stamped `capabilities_by_language` map until `_attach_capabilities_by_language` at standard.
- handle: `capability-signal-on-the-first-call-channel`
- destination: docs/AGENT_BRIEF.md (proposed — capability signals belong on the first-call channel; awaiting `/mango:promote`)
- seen: 243, 244
### 245-C1 — A shared TRY_INSTEAD_HINT_* string must stay true at every tool that attaches it

- type: 2 · handle: `route-must-answer`
- status: proposed (awaiting human confirm)
- seen: 093, 101, 102, 188, 245
- evidence: challenger round 1 NOT CLEAN — attaching `TRY_INSTEAD_HINT_METHOD_QNAME` unchanged on
  `search_symbol` still claimed "re-ask find_references / class-level reference is not modelled".
  Widening the prose to cover both sites was the first answer and maintainer review rejected it:
  it bought reuse by making the hint vaguer at the site that already had it, dropping the re-ask
  tool and calling an unmodelled relation a near-miss. Two findings with two re-ask tools are two
  advices, so the near-miss got `TRY_INSTEAD_HINT_NARROW_BY_QNAME`. 093 bans a second spelling of
  the same advice, not a second advice. R5.4c.
- destination: stays in `lessons_path` (folds into R5.4 falsifier; recurrence bump)


### 221-C1 — A callee reached from another language needs the cross-language census, not 186's within-language predicate

- type: 2 (code) · handle: `cross-language-zero-needs-the-crossing-census`
- status: proposed (awaiting human confirm)
- seen: 221
- evidence: `find_callers` returned `no_matches` on a stored proc whose only callers were PHP
  `querySP('proc')` string calls. 186's `relation_unmodelled_for_language(file_path, CALLER_KINDS)`
  could not catch it — it asks whether the subject's OWN language emits CALLS, and T-SQL emits plenty;
  a language that emits a kind can still be the dark side of an unmodelled crossing. The honest signal
  is the inverse, repo-level question: does any linked edge from another language reach this one?
  Answered from the `cross_language` census 204 already nests in the `edge_health_by_language` stamp
  (no second key to drift), guarded by "another language is indexed" so a single-language zero stays
  honest (AC2). R5.5/R5.6.
- destination: stays in `lessons_path` (recurrence 1)

### 225-C1 — The line a GROUP BY row reports must be aggregated within the tier it reports, not across the whole group

- type: 2 (code) · handle: `aggregate-the-line-with-the-tier-it-reports`
- status: proposed (awaiting human confirm)
- seen: 225
- evidence: `store.flow_edges` collapsed each `(source, target, kind)` group to a winning tier via a
  `CASE` and a bare `MIN(line)`. A RESOLVED edge and a DYNAMIC edge to the same target at different
  lines produced `tier=RESOLVED` carrying the DYNAMIC row's lower line, so the sequence view (225)
  attested call order on a line the winning edge never carried. Fixed by taking `MIN(line)` inside
  the winning tier (`COALESCE` over RESOLVED→HEURISTIC→DYNAMIC). The ticket-blind challenger found it
  untested; regression test `test_flow_edges_takes_the_line_of_the_winning_tier_not_the_lowest`. R5.5.
- destination: stays in `lessons_path` (recurrence 1)

### 217-C1 — When an adapter starts emitting a kind that tool_parity listed as absent, update the parity row in the same change
- type: 2
- status: proposed (awaiting human confirm)
- evidence: challenger 217 round 1; `tests/contract/tool_parity.py` PY_PARITY; 49 python parity tests green after
- handle: `parity-row-tracks-emitted-kinds`
- destination: stays in lessons_path
- seen: 217

### 020-C1 — For a language whose module AST node has no end_lineno, File line_end must be derived from the source text, not from the root node
- type: 2
- status: proposed (awaiting human confirm)
- evidence: challenger 020 round 1; `adapters/python/src/parse.py` before fix stuck at 1; pin `tests/python_adapter_cli.py::test_file_line_end_covers_source`
- handle: `module-ast-span-from-text`
- destination: stays in lessons_path
- seen: 020

### 202-C1 — a repro fixture must be checked against the payload it claims to reproduce, field by field

- type: 2 (process) · handle: `reproduce-the-payload-not-the-story`
- status: proposed (awaiting human confirm)
- seen: 202
- evidence: two fixture versions produced an incomplete index and neither reproduced the reported
  state — the first left `last_commit` absent, the second left the tree dirty so `staleness` read
  `behind` rather than `current`. The ticket quoted the field payload verbatim; comparing against it
  field by field is what found both.
- destination: stays in `lessons_path` (recurrence 1)

### 202-C2 — a guard whose window can close must fail when it does, not pass over an untested window

- type: 2 (code) · handle: `no-vacuous-pass-when-the-window-closes`
- status: proposed (awaiting human confirm)
- seen: 202
- evidence: the kill fixture races a real subprocess. If the build finishes first the test would
  exercise a completed index and pass — green over the scenario it exists to test. It raises
  instead, naming R6.5.
- destination: stays in `lessons_path` (recurrence 1)

*Claim `202-C3` — `compute_staleness` has six consumers, four of them nav tools that sign a payload,
so a staleness fix confined to `get_index_status` leaves `find_callers` and friends reporting
`current` over a gutted graph. type: 5 project-ground-truth · descriptive · area: tools / payload
honesty · proposed · verified-at: 2026-09-01 · stays in lessons.*

*Claim `202-C4` — a payload carrying two independent escalation causes should record BOTH rather
than let check order pick one: disjoint keys cost nothing and remove a precedence the caller cannot
observe. type: 2 · handle: `one-field-two-questions` · seen: 189, 022, 202 — **third sighting**, and
the first that is a defect rather than a use: the shipped code did let order decide, and the
ticket-blind challenger found it. The class index asks for exactly this before re-proposing.
status: proposed · destination: **proposed `rulebook_path`**, awaiting a per-claim human ratify.*

### 201-C1 — a design-time trace and a baseline read the PRE-change tree, and are not evidence for the tree under review

- type: 2 (process) · handle: `stamp-evidence-with-the-tree-under-review`
- status: proposed (awaiting human confirm)
- seen: 200, 201 — **recurrence 2**. The handle is the join between the two records, and recall
  greps the handle.
- sharpens 200-C2 rather than superseding it: 200 learned *stamp the tree under review*; 201 adds
  *and some artifacts are not evidence for that tree at all* — a blast-radius trace made to decide
  what to change, and a baseline, both describe the tree **before** it.
- evidence: three Phase-2 traces stamped at the branch point were refused by
  `check_lines --phase execute --tree <HEAD>`; re-running them at HEAD would have made them describe
  the tree after the change, which is not what a design-time trace is. Written as prose-plus-output
  instead — the same fix 200's baseline took, one ticket earlier.
- cheaply checkable: run `check_lines.py check <doc> --phase review --tree $(git rev-parse HEAD)`
  and read its `evidence :` line.
- destination: **proposed `agent_brief_path`** — a recurring type-2 process claim may not stay in
  lessons. Awaiting a per-claim human ratify.

### 201-C2 — a field that labels what ran must be derived from what ran, not from a side-channel

- type: 2 (code) · handle: `label-what-ran-not-what-was-recorded`
- status: proposed (awaiting human confirm)
- seen: 201
- evidence: `_run` returned `INCREMENTAL` whenever `scope` was empty, so a contract-forced
  `full_build` reported `mode: incremental` for as long as the escalation went unrecorded. The label
  was right exactly when the bookkeeping happened to be written, which is not a guarantee.
- destination: stays in `lessons_path` (recurrence 1)

*Claim `201-C3` — `code-atlas-build` runs the MCP tool itself (`cli.py:81`), so a refusal added to
that tool becomes a shell-route refusal unless the CLI opts out; here the refusal *names* the shell
route, so sharing it would have been a loop. type: 5 project-ground-truth · descriptive · area: cli /
tools · proposed · verified-at: 2026-09-01 · stays in lessons.*

### 200-C1 — the counted-line checker parses an enumerated tail from the line's LAST backtick

- type: 1 · handle: `symbol:check_lines.py`
- status: proposed (awaiting human confirm)
- seen: 200
- evidence: a `RULE SECTIONS:` line enumerating eight sections FAILED with *"the count of sections
  enumerated on the line does not match `<n> applicable`"* while `parse_line` on the same body
  returned `n=8, k=8, m=0` and `_count_sections` returned 8. The only difference was a nested
  `` `contract.py` `` inside one section's N/A reason; removing the inner backticks made the line
  pass unchanged in every other respect.
- destination: stays in `lessons_path`; also filed as a signal in `SKILL_GAP_CANDIDATES.md`

### 200-C2 — stamp test evidence with the tree under review, never the branch point

- type: 2 (process) · handle: `stamp-evidence-with-the-tree-under-review`
- status: proposed (awaiting human confirm)
- seen: 200
- evidence: eight `Ran at <branch point>` blocks, all refused at review against `HEAD`; re-running
  them at the reviewed SHA cleared seven, and the eighth is the baseline, which must not move.
- destination: stays in `lessons_path` (recurrence 1); `agent_brief_path` on a second sighting

### 200-C3 — between two correct fixes, take the one whose guard can be observed failing

- type: 2 (code) · handle: `prefer-the-provable-fix`
- status: proposed (awaiting human confirm)
- seen: 200
- evidence: deleting the snippet's `"if"` filter is correct — `poke.py` exits 0 on a suffix no
  adapter owns — and leaves nothing a fourth-adapter fixture could turn red. R6.5 asks for the
  observed failure, so the design that can produce one wins over the shorter diff.
- destination: stays in `lessons_path` (recurrence 1)

*Claim `200-C4` — every shipped adapter declares its announced suffixes as a one-line literal in its
own entry file (`adapters/php/index.php:27`, `adapters/typescript/index.js:12`,
`adapters/sql/index.js:12`), so a guard can read the handshake's own string without starting a
subprocess. type: 5 project-ground-truth · descriptive · area: adapters · proposed · verified-at:
2026-09-01 · stays in lessons.*

*Claim `PROM-C2` — an idempotency grep must search the destination for the **claim IDs** as well as
the handle slug, because a rule cites the claim that earned it and not the class it belongs to. type:
2 · handle: `grep-both-the-slug-and-the-claim-id` · status: proposed · seen: promote-2026-08-30 ·
evidence: `two-syntaxes-two-paths` reported `0 matches` on the slug while `ENGINEERING_RULES.md:154`
carried it under `019-C2` · destination: open — recurrence 1; the substance belongs in **P2**, which
already says the grep is not the check.*

*Claim `PROM-C3` — reading the destination before proposing changed three of six verdicts from "new
rule" to "widen an existing one"; the count of proposals that survive that read is the pass's own
health check. **Second sighting of P2's class.** type: 2 · handle:
`read-the-destination-not-just-the-grep` · status: proposed · seen: promote-2026-08-15,
promote-2026-08-30 · destination: **AGENT_BRIEF P2** — already binding; this is a `seen:` bump.*

*Claim `PROM-C4` — R7.6's "prune as you add" has no purchase on a promotion: what a promoted rule
supersedes is a claim's recall weight in `lessons_path`, which is tier 2, so the payment must come
from unrelated tier-1 retelling or the rule book can never grow. type: 5 · handle:
`a-promotion-pays-from-elsewhere-in-tier-1` · status: confirmed · seen: promote-2026-08-30 · area:
docs / budget · destination: stays in lessons_path.*

*Claim `199-C1` — a blast-radius trace that greps a PRIOR EXAMPLE is blind to every registry that
example is not in; grep the invariant's shape (a list of tool names, a dict keyed by tool) as well
as a known member of it. type: 2 · handle: `count-pin-in-blast-radius` · seen: 085, 087, 088, 089,
175, 184, 022, 194, 196, 199 · evidence: `git grep -ln check_column_defaults` -> 15 files; the gate
found 7 more, three of them lists 194's tool had never been added to · destination: AGENT_BRIEF P5.*

*Claim `199-C2` — listing a blast-radius site and then judging it N/A is worse than missing it: the
judgement is recorded as coverage and nothing re-checks it. Two of this ticket's three count-pin
failures were sites the trace had already named. type: 2 · handle:
`a-dismissed-site-reads-as-a-covered-one` · status: proposed · seen: 199 · evidence:
`test_sql_confinement`, `test_core_is_language_agnostic` and `test_total_count_semantics` were all
in the trace output and all dismissed · destination: open — recurrence 1.*

*Claim `199-C3` — a fixture can make a defect UNREPRODUCIBLE while looking like the right fixture:
199's stated over-answering could not be shown on the fixture the ticket names, because all four of
its flow seeds are the same controller, so "every flow" and "this subject's flows" are one set.
Build the smallest input where the defect is VISIBLE before asserting its absence. type: 2 · handle:
`the-fixture-can-hide-the-defect-it-was-chosen-for` · status: proposed · seen: 199 · evidence: the
mutation `matched = list(built.flows)` left the first proving test green; a two-entry seeded repo
reddens it · destination: open — recurrence 1.*

*Claim `199-C4` — derive the acceptance measurement's arithmetic BEFORE building, when the metric is
an aggregate: the gate ratio is a sum, so the pass condition is `g >= 0.63a - 116`, which explains
197's failure and predicts this ticket's result. A metric read as per-question would have made both
inexplicable. type: 2 · handle: `derive-the-aggregate-before-you-move-it` · status: proposed · seen:
199 · evidence: predicted `a ~ 250` needs `g >= 41`; measured 0.665 -> 0.829 · destination: open —
recurrence 1.*

*Claim `199-C6` — a cap that binds at SELECTION is invisible to a count of what was CUT: `flows_cut`
stayed 0 while flows went missing, because the cap dropped seeds before any flow was built. The
result was not a silent partial but a REFUSAL THAT WAS CONFIDENTLY WRONG — a subject with a real
flow answered `no_matches`. Check the input the cap ate, not only the output it trimmed. type: 2 ·
handle: `a-cap-at-selection-leaves-no-trace-in-the-output` · status: proposed · seen: 199 ·
evidence: `max_results=1` on a two-entry repo -> `\App\ReportController: reason=no_matches
truncated=False`, while its flow exists · destination: open — recurrence 1.*

*Claim `199-C7` — when a ticket's acceptance test is a MEASUREMENT the author also authors the
question for, the honest artifact is a sensitivity table, not a green number: this question passes
at 0.830 with the shipped grep pattern and at 0.604 — below the floor — with a narrower one that is
just as defensible. Disclose the range; do not tune the input to widen the margin. type: 2 · handle:
`disclose-the-measurement-s-sensitivity-not-only-its-value` · status: proposed · seen: 199 ·
evidence: challenger's sweep over four patterns, 0.604 / 0.630 / 0.630 / 0.830 · destination: open —
recurrence 1.*

*Claim `199-C8` — second sighting: `work_doc_mode: embed` makes challenger blindness a MANUAL
construction, and the mitigation leaked again — this run's challenger reported reading
`LESSONS.md` and `TOKEN_LEDGER.md` after being told not to. A guarantee that depends on the prompt
holding is not a guarantee. type: 3 · handle: `embed-mode-leaks-the-working-doc-into-the-diff` ·
seen: 197, 199 · evidence: the challenger's own independence statement · destination:
`skill_gap_path` — mango's maintainer, not this repo.*

*Claim `199-C5` — third sighting: a guard that scans source as TEXT fires on prose. A comment saying
a field is deliberately ABSENT names the field, and the emitter scan declared the tool an emitter.
type: 2 · handle: `read-the-syntax-not-the-text` · seen: 190, 187, 192, 199 · evidence: the
docstring explaining the missing paging denominator reddened its own guard, twice — the second time
because the guard's FILE NAME contains the field name · destination: R6.7.*

*Claim `196-C1` — gate a disclosure on the invariant it depends on, not on the presence of its
source: a source that exists can still be wrong, and presence-gating renders it anyway. type: 2 ·
handle: `gate-on-the-invariant-not-on-presence` · status: proposed · seen: 196 · evidence:
`stamped_edge_health_by_language()` returns a dict for a stale, thin or empty stamp;
`_confidence_split` refuses all three on the tier sum · destination: open — recurrence 1.*

*Claim `196-C2` — to find every place a figure reaches a reader, grep the DERIVED name the renderer
computes, not only the source field it came from. type: 2 · handle:
`grep-the-derived-name-not-the-source-name` · status: proposed · seen: 196 · evidence:
`git grep D.confidence` → 2 sites; `git grep HEUR` → 3, the third being the caveats card the
exposure-checker named · destination: open — recurrence 1.*

*Claim `196-C3` — restore a negative control from a BACKUP, never `git checkout <file>`: the control
runs on an uncommitted tree, so the restore that undoes it deletes the change it was controlling.
type: 2 · handle: `back-up-before-a-destructive-negative-control` · status: proposed · seen: 196 ·
evidence: `git checkout code_atlas/onboarding/dataset.py` after control 2 reverted all seven edits
to HEAD; rebuilt from the edit script · destination: open — recurrence 1.*

*Claim `196-C7` — a requirement stated as *"read X, do not recompute X"* is unfalsifiable in any
test that builds once, because the read and the recomputation agree; make them DISAGREE (doctor the
stored value's labels, keep its arithmetic) or the rule is enforced by nobody. type: 2 · handle:
`make-the-two-sources-disagree-to-test-which-one-is-read` · status: proposed · seen: 196 · evidence:
challenger's mutation `stamped_edge_health_by_language()` -> `edge_health_by_language()` left 15
tests green; it would also have silently disabled `MISMATCH_NOTE`, since a live fold cannot drift ·
destination: open — recurrence 1.*

*Claim `196-C6` — a count pin the trace cannot see is a pin written as a LITERAL where the
invariant has a name: `git grep DATASET_VERSION` found four pins and the gate found a fifth,
`assert payload["version"] == 9`, which no grep for the constant could reach. Its docstring still
said "at DATASET_VERSION 8" — it had gone stale twice. type: 2 · handle: `count-pin-in-blast-radius`
· seen: 085, 087, 088, 089, 175, 184, 022, 194, 196 · evidence: gate RED on
`test_flows_ride_with_the_dataset_and_absent_is_not_a_false_zero` after a trace that had reported
every pin folded in; fixed by pinning against the constant, not by bumping a second copy of the
number · destination: AGENT_BRIEF P5.*

*Claim `198-C2` — a guard driven to its limit must inspect the RESULT, not only the counter: the
ceiling test called the builder and discarded the table, so a seam dropping declined rows passed
every test. type: 2 · handle: `prove-the-guard-fails` · seen: 093, 019, 147, 184, 192, 194, 195,
022, 128, 198 · evidence: mutation "drop a declined row" → 5 original tests green, count-arm test
red · destination: R6.5.*

*Claim `198-C3` — a requirement can be WRONG, not merely unmet; three of this ticket's own asked for
things that cannot exist (a derived ceiling with no constant, a rename-stable key for an identity
that is a path, a slot for a name that already reads). type: 2 · handle:
`a-requirement-can-be-impossible` · seen: 198 · evidence: Scope 1b, AC4 and Scope 4 corrected in the
ticket rather than silently unmet · destination: open — recurrence 1.*

*Claim `197-C3` — a named subset exported by the contract is a spend every consumer inherits; the
kind set a consumer walks belongs to the consumer. type: 2 · handle:
`the-consumer-owns-its-kind-set` · seen: 197 · evidence: `FLOW_KINDS` in `contract.py` tripped 022
AC3's named-subset sweep; moved to `flows.py`, mirroring 138's `rule.kinds` · destination: open —
recurrence 1.*

*Claim `197-C4` — under `work_doc_mode: embed` the ticket-blind guarantee cannot hold for a change
that touches its own ticket: the working doc ships inside the diff, and a separator stops an honest
reader, not a grep. type: 3 · handle: `embed-mode-leaks-the-working-doc-into-the-diff` · seen: 197 ·
evidence: the challenger self-disclosed reading rationale via an unscoped `grep` over
`git diff` · destination: `SKILL_GAP_CANDIDATES.md` — mango-level, not this repo's to fix.*

*Claim `197-C5` — the tokens-to-answer floor is a real gate, not a report: a surface that cannot
beat `grep` on its own question fails it. type: 5 · area: benchmarks · verified-at: 2026-08-31 ·
evidence: `summary.flows` on `architecture_overview` took ratio to 0.53 against a 0.63 floor; the
surface was reverted rather than the floor lowered · destination: stays in lessons.*

*Claim `195-C2` — when an aggregate becomes unattributable, ATTRIBUTE it, do not replace it: for an
answer whose own scope spans the dimension, the aggregate is still the right denominator and swapping
in a slice turns an uninformative caveat into a false one. type: 2 · handle:
`attribute-the-aggregate-do-not-replace-it` · status: proposed · seen: 195 · destination: open —
recurrence 1.*

*Claim `195-C3` — a red-run count must exclude assertions that pin an ABSENCE: they hold under both
versions, so counting them inflates what the guard was shown to catch. 8 of 12 here, not 12.
type: 2 · handle: `prove-the-guard-fails` · seen: 195 · destination: R6.5.*

*Claim `195-C4` — the tier-1 token budget is paid by finding what another tier-1 file already says
verbatim, not by raising it: `docs/BACKLOG.md` carried "M10–M12 are complete" and "shipped for daily
use at task 014", both already in `AGENTS.md`. type: 5 · handle: `tier-1-pays-from-its-duplicates` ·
status: confirmed · seen: 195 · area: docs · destination: stays in lessons_path.*

*Claim `194-C1` — a blast-radius trace is complete only once the invariants the change MOVES are
enumerated; grepping one invariant well still misses the others. This change moved two — the tool
surface and the core-module count — and the trace named one, so 5 of 11 authored touchpoints were
predicted. type: 2 · handle: `count-pin-in-blast-radius` · seen: 184, 022, 194 · destination:
AGENT_BRIEF P5.*

*Claim `194-C2` — a ratio's denominator is the whole population, not the subset the query filtered
to; computing it over the filter empties the numerator and the answer fails silently in the
false-negative direction. type: 2 · handle: `denominator-is-the-population-not-the-subset` · status:
proposed · seen: 194 · evidence: `writers_total` over defaulted columns only returned
`omitted_by: []` for a table where two of four writers omit the column · destination: open —
recurrence 1.*

*Claim `194-C3` — a ticket's proposed implementation site is a hypothesis, not a requirement; check
it against the target engine's actual vocabulary before fitting the work in, because a predicate
forced into the wrong engine becomes a second shape inside one dataclass. type: 2 · handle:
`the-ticket-may-name-the-wrong-home` · status: proposed · seen: 194 · destination: open —
recurrence 1.*

*Claim `194-C4` — the tool list in `docs/PLAN.md` is NOT the tool surface: it omitted 4 of 22 before
this ticket. `docs/TOOLS.md` is the surface and `tests/test_documented_tool_count.py` pins its count;
do not spend PLAN's budget keeping up a list nothing maintains. type: 5 · handle:
`plan-tool-list-is-not-the-surface` · status: confirmed · seen: 194 · area: docs · destination:
stays in lessons_path.*

*Claim `194-C5` — the proving test shipped red: it failed on the empty `omitted_by` above before the
denominator was fixed. type: 2 · handle: `prove-the-guard-fails` · seen: 194 · destination: R6.5.*

*Claim `022-C1` — `confidence_tier` answers how sure the adapter is of the TARGET; encoding a second
question in it (how complete the statement was) silently changes whether the edge resolves at all.
type: 2 · handle: `one-field-two-questions` · seen: 189, 022 · evidence: WRITES onto a table at
`DYNAMIC` never linked (`resolver.py:104` `skip_dynamic=True`); RESOLVED onto the Table, with the
target KIND as the discriminator, links · destination: open — recurrence 2.*

*Claim `022-C3` — a count pin need not name what it counts, so a blast-radius grep written from the
expected spelling under-scopes: 6 of 8 pins found, `len(VOCABULARY) == 42` and a doc size budget
missed. type: 2 · handle: `count-pin-in-blast-radius` · seen: 184, 022 · destination: AGENT_BRIEF P5.*

*Claim `022-C5` — `CONVENTION.md` published the kind vocabulary as a hand-kept copy with no test
deriving it from `contract.py`, and it was stale the moment the contract moved. type: 2 · handle:
`derived-not-listed-invariant` · seen: 184, 022 · destination: R6.7.*

*Claim `022-C6` — both guards shipped with a recorded red run: the CONVENTION-derivation test failed
on the stale doc, and the integration proving test failed on the unlinked DYNAMIC edge. type: 2 ·
handle: `prove-the-guard-fails` · seen: 184, 192, 022 · destination: R6.5.*

*Claim `022-C7` — a gate that names a capability is discharged when the ticket sheds that capability;
widening the gate's condition to admit the case in front of it destroys the gate for every later
ticket, while the gate's stated PREMISE may still bind and is answerable by proof. type: 2 · handle:
`discharge-the-gate-do-not-widen-it` · status: proposed · seen: 022 · evidence: 022's §1 is scoped to
schema state, closed permanently in PLAN §18.4; the preamble was answered by
`test_sql_tier2_vocabulary_is_opt_in.py` instead · destination: open — AGENT_BRIEF if it recurs.*

*Claim `192-C1` — a disclosure gated on emptiness cannot describe a partial answer, and a partial
answer is the one a reader trusts; gate the disclosure on the CONDITION it describes, never on the
size of the result. type: 2 · handle: `gate-the-disclosure-on-its-condition-not-the-row-count` ·
status: proposed · seen: 192, 238 · evidence: `coverage.py` returned early on `results`; 8-A's 1-vs-281 and
round 12's 6-C; 238's `find_callers.py` gated `cross_language_relation_unmodelled` on `total_count == 0`
so a hits-bearing answer presented as `reason: ok` · destination: docs/ENGINEERING_RULES.md (proposed;
human-unratified — `/mango:promote`).*

*Claim `192-C2` — the widening shipped only once the old carve-out was restored and the new assertion
shown to fail on it (`KeyError: 'unconfigured_adapters'`). type: 2 · handle: `prove-the-guard-fails` ·
seen: 192 · destination: R6.5.*

*Claim `192-C5` — two tickets incrementing one shared counter are reconciled by a merge that keeps
one: 184 took `prove-the-guard-fails` 25→26, so 192's identical edit had nothing to apply to and its
sighting vanished. `seen:` is the ONLY gate on promotion (P1), so a lost sighting is a rule that never
ripens, and no test fails when it happens. Re-read the counter after any rebase that touched the same
table. type: 2 · handle: `two-tickets-one-counter` · status: proposed · seen: 192 · evidence: the
rebase of this branch onto a main carrying 184 · destination: open.*

*Claim `192-C4` — a gitignored build artefact survives `git checkout`, so a branch can be tested
against a directory that is not in it: `adapters/sql/node_modules` left over from 184 made
`shipped_adapters` report a third adapter on a branch that has none. Check the tree matches the branch
before trusting a payload pin. **Second sighting, other axis (258):** the `graph-N.db` files
`tokens_to_answer.py` leaves in `artifacts/` outlived the `schema_version` 258 bumped, so the gate
read a refused open as a ratio regression — an artefact outlives a schema era the same way it
outlives a branch. type: 5 · handle: `ignored-artefact-outlives-the-branch` · status:
confirmed · seen: 192, 258 · area: process · destination: stays in lessons_path.*

*Claim `184-C1` — an AC that names a growth axis must name the axis the defect lives on; where a
protocol imposes growth of its own, measure the other axis and pin the imposed one as bounded rather
than deleting it. type: 2 · handle: `measure-the-axis-the-defect-lives-on` · status: proposed · seen:
184 · evidence: AC5's first wording unsatisfiable by construction (§4.1 one-object-per-file); byte
axis <1.25x, red run 2.44x · destination: open — folds into R6.8 if it recurs.*

*Claim `184-C2` — the streaming requirement shipped only once `readFileSync` was shown to fail the
assertion that names it. type: 2 · handle: `prove-the-guard-fails` · seen: 184 · destination: R6.5.*

*Claim `184-C4` — a blast-radius trace that follows the registry misses the readers of a list DERIVED
from it: `test_batched_subject_sweep.py` pins a payload carrying `unconfigured_adapters`, so adapter
#3 reddened a test with nothing to do with SQL. type: 2 · handle: `count-pin-in-blast-radius` · seen:
184 · destination: AGENT_BRIEF P5.*

*Claim `184-C5` — a streaming scanner has no parse phase, so it has no syntax-error conformance case;
its `ok:false` path is a missing-file test and the difference belongs in the adapter README. type: 5 ·
handle: `scanner-has-no-parse-phase` · status: confirmed · seen: 184 · area: adapters · destination:
stays in lessons_path.*

*Claim `184-C6` — R6.2 was re-listing in prose three construct inventories `adapter_registry.py`
already holds as data; that copy was itself the drift R6.7 forbids. type: 2 · handle:
`derived-not-listed-invariant` · seen: 184 · destination: R6.7.*

### 191-C1 — Count what a repaired guard was hiding before believing the ticket's cause
- type: 2 generalisable-heuristic
- handle: a-guard-fails-for-more-reasons-than-it-was-filed-for
- status: proposed (awaiting human confirm)
- seen: 191
- evidence: the ticket named one cause (a stale index). Removing the conditional and fixing that
  cause left the test red on two more: the wrong tool for the subject's kind, and a fixture one site
  below the threshold that produces the field. All three were invisible while the `if` stood,
  because a conditional assertion reports every one of them identically.
- area: tests / guards
- destination: stays in `lessons_path` (recurrence 1) — sharpens [[prove-the-guard-fails]] (R6.5):
  not only *was it seen failing*, but *how many distinct failures did the guard's absence hide?*

### 190-C1 — Construct the premise; do not race for it. And check which LINE fails.
Two halves.

**(a)** When a guard needs a *state* to exist, build the state and assert it. A guard that arranges
its premise through timing is a guard whose red means *"either the hazard is present or the host was
busy"* — and a maintainer reading it at 03:00 cannot separate those. Read the premise from the
artifact under test wherever the artifact records it; a constant the test invents can drift from what
the code compares.

**(b)** The diagnostic that made this legible is *which assertion fails*. Before: the premise broke
and the **conclusion's** assertion fired, carrying a message about CPython. After: the premise's own
two assertions fire, naming which half went. **Assert the premise separately from the claim, or every
premise failure arrives wearing the claim's explanation.**

type: 2 · seen: 1 · handle: `construct-the-premise-do-not-race-for-it` · tickets: 190

### 189-C1 — One field, two questions: name the predicate that decided, or the reader cannot tell
When a disclosure serves two questions, ranking cannot be *made* right — one of the two callers will
always read position 1 wrong. What can be right is the **basis**, and the rule that makes it right is
180's: **name the one predicate the order was actually decided by, and only when it decided
something.** If the discriminating predicate is uniform across the list, it decided nothing and
naming it misstates the order; fall back and say so. `0 < matched < total` is that test, and it is a
structural question rather than a tuned number (161 AC1), so it holds identically at 2 rows and 93.

**Corollary, and the cheaper half of the lesson:** before pricing a new published field to support a
basis, check whether the payload *already* carries a datum on the same axis. The ticket's three
options all cost bytes; the fourth cost two.

type: 2 · seen: 1 · handle: `one-field-two-questions` · tickets: 189

### 188-C1 — Link on the graph, not on the string; and a tier measures the producer, not the consumer
Two halves of one claim, both learned here.

**(a)** When one edge kind carries two shapes across languages, the discriminator that keeps R1.1 is
**the graph itself**: perform the lookup and let a miss be the answer. Sniffing the raw's shape needs a
per-language idea of what a path looks like; asking the graph needs none, is sourced from the
computation (R5.2), and degrades into honest off-graph evidence instead of a wrong link.

**(b)** A `confidence_tier` records how sure the **producer** was. It says nothing about whether any
consumer read the value, so a health metric built on tiers reports *fine* while the answer is
discarded. A resolved-but-unlinked row is the shape to look for: **`RESOLVED` and `target_qname IS
NULL` together is a consumer gap, and nothing in this repo was watching for it.**

type: 2 · seen: 1 · handle: `link-on-the-graph-not-on-the-string` · tickets: 188

### 182-C1 — A complement is unreadable without the premise it was taken against
- type: 2 generalisable-heuristic
- handle: publish-the-premise-not-only-the-complement
- status: proposed (awaiting human confirm)
- seen: 182
- evidence: 215,177 orphans of 216,664 nodes is unreadable — it is consistent with a dead repo and
  with three misconfigured globs. *"Three root files reached a handful of nodes"* is the same fact and
  immediately actionable. Any tool answering with a complement (orphans, unreachable, unused, missing)
  owes the reader what the premise reached, not only what it excluded. Corollary from the same ticket:
  **a flag that is the OR of several causes cannot become a refusal until it is split** — one cause
  here was the caller's own request.
- area: tools / payload honesty / config
- destination: stays in `lessons_path` (recurrence 1)

### 181-C1 — A fallback branch must differ in shape, not in a value the caller must interpret
- type: 2 generalisable-heuristic
- handle: a-fallback-must-not-wear-the-shape-it-falls-back-from
- status: proposed (awaiting human confirm)
- seen: 181
- evidence: `ranked_by: "path"` was deterministic, lossless and documented, and still read as a
  ranking. Two payloads with the same keys meant two different things. The falsifier is the reader's
  test: can they branch correctly **without** knowing the value vocabulary? If not, the fallback needs
  its own field, not its own value. Corollary from the same ticket: an available basis is not therefore
  a right one — `ranked: true` on a bad basis is worse than `ranked: false`.
- area: tools / payload honesty
- destination: stays in `lessons_path` (recurrence 1) — close to [[170-C1]]
  (`never-cache-a-verdict-with-a-fact`): both separate a verdict from a value.

### 175-C1 — Re-derive a provenance identity against the same inputs that produced it
- type: 2 generalisable-heuristic
- handle: an-identity-must-be-comparable-against-what-produced-it
- status: proposed (awaiting human confirm)
- seen: 175
- evidence: the identity hashed (file bytes + explicit env); the staleness check re-hashed (file bytes
  + `os.environ`). Every caller that passed an env read as stale with nothing changed. The general
  form: ask which of an identity's inputs can actually change under a running process, freeze the
  rest, and compare only the mutable axis.
- area: config / provenance
- destination: stays in `lessons_path` (recurrence 1) — sibling of [[170-C1]]
  (`never-cache-a-verdict-with-a-fact`): both are about what a provenance answer is allowed to claim.

### 170-C1 — Never cache a verdict together with a fact
- type: 2 generalisable-heuristic
- handle: never-cache-a-verdict-with-a-fact
- status: proposed (awaiting human confirm)
- seen: 170
- evidence: `server_identity` returned a permanent property of the process and a perishable verdict
  about the world from one memoised call. The permanent half made the cache look obviously correct;
  the verdict froze silently and stayed frozen for the process's life. Its mirror is the 061 half:
  omit-when-empty is right for a value and wrong for a verdict, because absence and "checked, all
  clear" are different claims.
- area: tools / caching / payload honesty
- destination: stays in `lessons_path` (recurrence 1)

### 174-C1 — Disclose the reader's cost, not the product's fact
- type: 2 generalisable-heuristic
- handle: disclose-the-readers-cost-not-the-products-fact
- status: proposed (awaiting human confirm)
- seen: 174
- evidence: four rounds disclosed *"an adapter exists and is unwired"* — true, complete, and about the
  product — and reported zero contribution each time. The number that would have been acted on is a
  count of the reader's own files. When a disclosure is correct and inert, check whose fact it states.
- area: tools / payload honesty / adoption
- destination: stays in `lessons_path` (recurrence 1)

### 179-C1 — Ask whether a decision is a callable or a paragraph before expecting inheritance
- type: 2 generalisable-heuristic
- handle: a-decision-is-only-shared-as-far-as-it-is-factored
- status: proposed (awaiting human confirm)
- seen: 179
- evidence: `resolve_seeds` (shared) sat *inside* the seed decision, and the two splits that completed
  it sat in one tool's body. Both tools "shared the seed logic", and one of them silently walked twins
  for two tickets. A shared helper inside a decision is the strongest disguise the class has.
- area: tools / shared decisions
- destination: stays in `lessons_path` (recurrence 1) — sharpens [[one-rule-for-every-subject-slot]]
  (R1.8) rather than competing with it: R1.8 forbids two implementations, this asks whether there is
  one *reachable* implementation.

### 186-C1 — An evidence-keyed caveat is unreachable for a producer that emits none of the vocabulary
- type: 2 generalisable-heuristic
- handle: evidence-shaped-honesty-inverts-on-a-second-instance
- status: proposed (awaiting human confirm)
- seen: 186
- evidence: `relationship_not_modelled` fires on unlinked `INCLUDES`; the TS adapter emits no
  `INCLUDES`, so the arm is structurally unreachable and the fall-through is a confident zero. No code
  changed for this to become wrong. When adding producer #2 (adapter, tenant, source), ask of every
  evidence-keyed caveat whether the new producer can generate the evidence at all.
- area: tools / payload honesty / roll-out
- destination: stays in `lessons_path` (recurrence 1) — closely related to [[183-C1]]
  (`an-aggregate-outlives-the-world-that-named-it`); if a second sighting lands, consider unioning.

### 185-C1 — A declared state needs an obligation derived from the world, not a label
- type: 2 generalisable-heuristic
- handle: a-declared-state-needs-a-checkable-obligation
- status: proposed (awaiting human confirm)
- seen: 185
- evidence: `answers_without` began as a label meaning "narrower for this language". Nothing checked
  the claim, so any cell could have named any missing kind and stayed green. Deriving the obligation
  from the graph's actual edge kinds turned it into an assertion; the red run confirms a false claim
  now fails. Generalises to any expectation table: state, then the obligation that state implies.
- area: tests / contract harness
- destination: stays in `lessons_path` (recurrence 1)

### 180-C1 — A predicate needed both inside a query and outside it is registered, never re-spelled
- type: 2 generalisable-heuristic
- handle: one-predicate-two-layers-is-the-drift
- status: proposed (awaiting human confirm)
- seen: 180
- evidence: the exactness band had to run inside `ORDER BY` while `reason` ran over the returned
  rows. A SQL spelling of `is_direct_match` is a second definition site that no test compares, so the
  order and the label could disagree — which is the defect 180 exists to fix, moved down a layer.
  `sqlite3.Connection.create_function(..., deterministic=True)` makes the predicate the same object
  in both places.
- area: store / tools / ranking
- destination: stays in `lessons_path` (recurrence 1)

*Claim `150-C1` — a static-analysis gate for an intentionally-untyped source should run the type
checker at its strictest *clean* setting and defer exactly the flags whose findings another scheduled
ticket owns, with a written pointer — never suppress. type: 2 · handle:
`analyser-choice-for-an-untyped-adapter` · status: proposed · seen: 150 · evidence:
`adapters/typescript/tsconfig.json` (`noImplicitAny:false` + 154 pointer); `tsc -p` clean, red-run
`TS2322` exit 2 · destination: open — folds into a convention if it recurs (relates to 105-C2, 148).*

*Claim `167-C1` — a search answer's `reason` must encode *how* results matched (exact/prefix vs
substring/trigram), not just whether any came back; a count-only reason lets a near-miss pass as a hit
and suppresses any note gated on the genuine-absence reasons. type: 2 · handle:
`label-how-it-matched-not-just-how-many` · status: proposed · seen: 167 · evidence:
`search_symbol.py:195` reason = ok if total_count>0; closed by `REASON_SUBSTRING_MATCH` +
`test_substring_near_miss_is_labelled_and_carries_the_gap` · destination: open — folds into a
convention if it recurs (relates to 160, 065).*

*Claim `166-C1` — read-through freshness must measure drift against the **indexed commit**, not the
working tree: a committed change is not working-tree-dirty yet still leaves the index behind, so a
working-tree-only signal produces a false `no_such_symbol` for a symbol a `git pull` added. type: 2 ·
handle: `drift-is-vs-the-index-commit-not-the-working-tree` · status: proposed · seen: 166 · evidence:
`dirty_indexed_paths` used `dirty_paths`; `test_read_symbol_miss_repairs_committed_drift` red pre-fix ·
destination: open — folds into a convention if it recurs (relates to 073, 047).*

*Claim `165-C1` — a tool answer scoped to one qname is a *partition* when the subject shares its
identity slot (trailing name) with definitions under other qnames; disclose the siblings and mark the
answer `authoritative: false` rather than presenting the partition as the whole. type: 2 · handle:
`disclose-a-partition-as-a-partition` · status: proposed · seen: 165 · evidence:
`find_callers.py:255` disclosed only exact-qname twins (`nodes_by_qualified_name`); closed by a
`nodes_by_name` sibling query + `test_find_callers_discloses_sibling_definitions_on_a_twin` ·
destination: open — folds into a convention if it recurs (relates to [[161]], 070, R5.5).*

*Claim `164-C1` — a build/provenance stamp for a long-lived process must be derived from the code the
process LOADED (captured at import/start), not from the mutable source on disk; disclose any
process-vs-disk divergence in-band rather than reporting the disk's state as the process's. type: 2 ·
handle: `identity-names-the-loaded-process-not-the-disk` · status: proposed · seen: 164 · evidence:
`build_info._git_build_id()` returned git HEAD for an lru-cached-at-first-call identity; closed by
`_LOADED_BUILD_ID` + the divergence branch + `test_stale_process_when_loaded_differs_from_disk` ·
destination: open — folds into a convention if it recurs (relates to [[125]] server-identity).*

*Claim `161-C1` — before implementing a resolution spec, check whether the graph can actually answer
it; a qname-keyed edge cannot be attributed to a specific same-named node, so "which twin's callers"
is unanswerable — refuse (subject_ambiguous) rather than fabricate. type: 2 · handle:
`honest-endpoint-when-model-cannot-answer` · status: proposed · seen: 161 · evidence: edges carry
target_qname not a node id; impact_radius joins on target_qname · destination: open — folds into a
convention if it recurs.*

*Claim `158-C1` — put the next-step routing on the successful answer (keyed to its shape), on the
payload channel the agent already reads — not only on a miss/stale path and never on a human-only
prompt. type: 2 · handle: `route-on-the-successful-answer` · status: proposed · seen: 158 · evidence:
next_tool_suggestions fired only on staleness; the which_tool prompt was never called in four rounds ·
destination: open — folds into a convention if it recurs.*

*Claim `160-C1` — to add a cross-cutting field to a tool with several early returns, make the attach
self-gating and idempotent so it is safe at every exit; then audit every ENTRY point too (scalar vs
batch build answers differently). type: 2 · handle: `self-gating-attach-audit-every-entry` · status:
proposed · seen: 160 · evidence: single-subject paths were covered; the queries=[...] sweep envelope
was missed until the challenger flagged it · destination: open — folds into a convention if it recurs.*

*Claim `159-C1` — surface a shipped-but-unconfigured capability proactively by enumerating what ships
and diffing against config; presence of a config value is evidence of the past, not of what is
available. type: 2 · handle: `discoverability-enumerate-and-diff` · status: proposed · seen: 159 ·
evidence: `indexed_suffixes` described only what was indexed; nothing named the unwired TS/JS adapter ·
destination: open — folds into a convention if it recurs.*

*Claim `163-C1` — before removing a documented-but-inert knob, check for an invariant test that
asserts its presence across the surface; removing it there trades a no-op for a broken contract, so
prefer giving the knob real behaviour. type: 2 · handle: `check-the-invariant-before-removing` ·
status: proposed · seen: 163 · evidence: `test_mcp_server.py` `set(declared) == set(TOOL_NAMES)` would
fail on read_symbol losing `detail_level` · destination: open — folds into a convention if it recurs.*

*Claim `162-C1` — a cross-cutting payload field must be stamped where the payload is built, not in the
transport wrapper, because tests (and any non-MCP caller) reach tools below the wrapper; a wrapper-only
stamp splits the payload shape by call path. type: 2 · handle: `stamp-at-the-builder-not-the-wrapper` ·
status: proposed · seen: 162 · evidence: every `tests/test_*` nav/read assertion calls `create(config)`
directly, never `guard` · destination: open — folds into a convention if it recurs.*

*Claim `019-C1` — a frozen test shape that omits a field cannot fail on it, so the omitted field is
where two implementations of one contract diverge. Pin every field whose value is a claim, not just
the ones that differ today. type: 2 · handle: `prove-the-guard-fails` · status: confirmed · seen: 019
· evidence: `edge_shapes` had no `source_qname`; red run fails `typescript:jsx` +
`typescript:module-esm` only · destination: R6.5 (already binding — sighting only).*

*Claim `019-C3` — a name that differs between the declaring and the importing side needs an explicit
alias edge, not a matching convention: `export default class Foo` declares `::Foo` and is imported as
`::default`. type 5 project-ground-truth · area: TS adapter / resolution · seen 019 · confirmed ·
stays in lessons_path*

*Claim `142-C1` — the tokens-to-answer recall/precision scorer only sees members under its
identity/free-text keys, so a tool answering under other field names needs `precision_note`, not
`expected_set`. type 5 project-ground-truth · descriptive · area: tokens-to-answer harness · seen 142
· proposed · stays in lessons_path*

*Claim `128-C1` — an adapter emits every reference it sees and only declines to *resolve*; gating
edge emission on whether the target is locally known drops what the core was meant to link. type: 2 ·
handle: `emit-do-not-gate-on-resolution` · status: confirmed · seen: 128 · evidence:
`adapters/typescript/src/parse.js` CALLS branch, fixture `log()` red-run · destination: open — folds
into R3.3 if it recurs.*

*Claim `128-C2` — a same-file name→qname map keyed on the bare simple name collides across
containers; scope it per container before a later ticket earns `RESOLVED` from it. type: 5 · handle:
`same-file-symbol-map-scope-per-container` · status: confirmed · seen: 128 · area: adapters ·
destination: stays in lessons_path.*

*Claim `128-C3` — the CALLS fix shipped only once a fixture was shown to fail without it. type: 2 ·
handle: `prove-the-guard-fails` · seen: 128 · destination: R6.5.*

*Claim `128-C4` — the TS conformance is a registry row; the valid set is `set(adapter.cases)`, never
re-listed. type: 2 · handle: `derived-not-listed-invariant` · seen: 128 · destination: R6.7.*

*Claim `149-C1` — a cross-ticket reference to a symbol at file:line goes stale when a prior ticket
relocates it (147 moved `R62_CASES` → `adapter_registry.py`); verify a citation still resolves at
pickup. type: 5 · handle: `verify-cited-reference-at-pickup` · status: confirmed · seen: 149 · area:
process · destination: stays in lessons_path.*

*Claim `148-C1` — a denylist/guard must be proven to fire on every shape it forbids AND not fire on
the look-alikes it must ignore; ship both controls. type: 2 · handle: `prove-the-guard-fails` · seen:
148 · destination: R6.5.*

*Claim `148-C2` — a value hand-copied into N gates drifts; derive all N from one committed source.
type: 2 · handle: `derived-not-listed-invariant` · seen: 148 · destination: R6.7.*

*Claim `147-C1` — a guard/harness proven only against the shape it was written for cannot fail for
the next; ship it with a recorded red run. type: 2 · handle: `prove-the-guard-fails` · seen: 147 ·
destination: R6.5.*

*Claim `147-C2` — where a test needs "every valid adapter", derive the set from the registry, never
re-list it. type: 2 · handle: `derived-not-listed-invariant` · seen: 147 · destination: R6.7.*

*Claim `118-C1` — hardcoded empty strings at a consumer seam masquerade as missing source data in
every repository.* · type: 2 · handle: `empty-seam-inputs-masquerade-as-missing-data` · status:
confirmed · seen: 118 · area: onboarding/artifact · evidence: `artifact.py:325` before fix ·
destination: stays in lessons_path until a second key.

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

### 127-C2 — new sighting of an existing class, recorded as a `seen:` bump, not a fresh claim
`derived-not-listed-invariant` (rec 11 → **12**, already **R6.7**) gains 127: the caveat set the guard
iterates is derived from the dataset payload, so caveat N+1 is covered the moment it exists. The class
index's own instruction is that a new sighting bumps `seen:` rather than re-deriving the rule.
`source-the-caveat-from-the-computation` (rec 4 → **5**, already **R5.5**) gains 127 as well: the
declaration caveat now rides on the split that computes the declared counts, and `path_index.caveat` is
sourced where the cap is decided rather than re-worded by the renderer.

### 125-C1 — Server identity is orthogonal to contract/schema version
- type: 2 generalisable-heuristic
- handle: server-identity-orthogonal-to-schema-version
- status: proposed (awaiting human confirm)
- seen: 125
- evidence: round-6 retro could not answer §0.a; closed by ``build_info.server_identity`` +
  ``field-retro.md`` §0.a
- area: tools / evaluation / provenance
- destination: `rulebook_path` (code subject) — recurrence 1, not yet promotable

### 124-C1 — A tool's walk budget must be named for that tool, not borrowed from a sibling
- type: 2 generalisable-heuristic
- handle: walk-budget-named-for-the-tool-that-walks
- status: proposed (awaiting human confirm)
- seen: 124
- evidence: `find_orphans.py` used `config.impact_max_nodes`; closed by `CA_ORPHANS_MAX_NODES` +
  AC3 tests proving impact knob independence
- area: tools / config / reachability
- destination: `rulebook_path` (code subject) — recurrence 1, not yet promotable

### 123-C1 — `total_count` is the true total everywhere it appears, never the page length
- type: 2 generalisable-heuristic
- handle: total-count-is-the-true-total-not-the-page
- status: proposed (awaiting human confirm)
- seen: 123
- evidence: `file_outline.py` used `total_count=len(results)`; closed by `count_nodes_by_file` +
  `tests/test_total_count_semantics.py` enumerating every emitter
- area: tools / payload honesty
- destination: `rulebook_path` (code subject) — recurrence 1, not yet promotable

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

*Claim `084-C1` — Judge a piped command's result by its output, not the pipeline's exit status. type
4 gotcha · area: workflow / running the Docker gate on a non-Linux host · seen 084 · proposed ·
`gotchas_path` (recurrence 1 — recorded, not yet promotable).*
*Evidence: `bash scripts/docker-test.sh 2>&1 | tail -20` printed ruff's `Found 10 errors` then
`[exited with code 0]` (tail's exit). The ruff failure was caught by reading the content, not the
status. `&&`-chained gate → ruff failing stops the chain, but the pipe hides that..*

*Claim `102-C3` — `seeds_dropped` has two producers, and an unknown path has no reason of its own.
type 5 project-ground-truth · area: impact / store / tool payloads · seen 102 · proposed ·
destination unset.*
*Evidence: the field now sums `store.impact_radius`'s budget prune (`store.py:1051`) with the tool's
lost-subject count (`impact.py`), and the two can never overlap because a dropped subject never
enters `ordered_seeds`. A truly unknown **path** reports `no_such_symbol` — true at the class level,
not path-specific; `file_outline` has the same gap (`found: false`, no reason), so a path-shaped
reason is a surface-wide follow-up, not an impact-only one.*

### 100-C2 — When an artifact exists to be re-checked, a lossy repair is worse than the corruption
- type: 2 generalisable-heuristic
- handle: lossless-repair-for-a-checkable-artifact
- status: proposed (awaiting human confirm)
- seen: 100
- evidence: review proposed folding an inner `"` to `'`; that would have silently renamed the path a
  reader is meant to verify. Quote-doubling round-trips exactly and keeps the no-escape-character
  grammar the backslash-separated qualified names depend on
- area: tool payloads / claim signing

*Claim `100-C5` — impact seeds are returned inside `results`, so a bare count is ambiguous. type 5
project-ground-truth · area: impact / store · seen 100 · proposed · destination unset.*
*Evidence: `store.impact_radius` includes the seeds themselves, so `answer=N` conflates *N
dependents* with *N seeds and zero dependents*. The line carries `seeds=` beside `answer=`; `answer
== seeds` is the modelled zero.*

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

*Claim `094-C2` — A ::class mention is a REFERENCES edge, not a CALLS or a new kind. type 5 project-
ground-truth · descriptive · area: adapter / contract · proposed · stays in lessons.*
*Evidence: ticket 094; `Visitor.php` `enterClassConstFetch`; PLAN §8.2.*

*Claim `097-C2` — Descriptions can name an occasion; they cannot make the agent notice it. type 5
project-ground-truth · descriptive · area: routing surface / recognition vs recall · proposed ·
stays in lessons.*
*Evidence: field retro round 5 §11.3; `file_outline` named at Q4, description loaded, unused on the
1,196-line port; trigger placed in description + onboarding, not `next_tool_suggestions`.*

*Claim `095-C3` — On the git collect path, ignore_sources names matcher leftovers, not git’s drops.
type 5 project-ground-truth · descriptive · area: collection census / ignore · proposed · stays in
lessons.*
*Evidence: PLAN §11; `git ls-files` already applies `.gitignore`; proving test uses
`.codeatlasignore` + builtin, and `git add -f` for a gitignore source.*

*Claim `043-C1` — Full-UNIQUE-key dedupe + store-owned WRITE_ERRORS. type 5 project-ground-truth ·
area: store / indexer / R1.4 / R5.1 · confirmed · stays in lessons.*
*Evidence: `test_resolver.py` multi-file siblings; `test_sql_confinement.py`; Gate-4 clean.*

*Claim `041-C1` — R1.1-honest Blade ignore + stub-walk coverage. type 5 project-ground-truth ·
normative · area: ignore / indexer / R1.1 · confirmed · stays in lessons.*
*Evidence: PR #47 review — split-token dodge rejected; `*.blade.*` + `_STUB_FILE_IGNORE`.*

*Claim `040-C1` — Doc inventory lags new core module. type 5 project-ground-truth · normative ·
area: docs / R7.2 / R1.4 · confirmed · stays in lessons.*
*Evidence: reviewer findings 1–3 on `5926e2d`; fixed in `794b55d`.*

*Claim `039-C1` — Incremental stub refresh is hash-gated, not git-named. type 5 project-ground-truth
· normative · area: indexer / R4.2 · seen 039 · confirmed · stays in lessons.*
*Evidence: reviewer finding on `changed_set & stub_set`; fixed in `ddcfe77` +
`test_incremental_hash_gates_stub_edits`.*

*Claim `038-C1` — Path hop shaping must not multi-key EDGE_FIELDS in one literal. type 5 project-
ground-truth · normative · area: store / tools / R3.2 · seen 038 · confirmed · stays in lessons.*
*Evidence: sole-source fail on store.py / explain_path.py; fixed via per-statement hop keys.*

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

*Claim `033-C1` — Enum members deferred to a paired ticket need W1/W2 at refine. type 5 project-
ground-truth · normative · area: mango / refine / reason-codes · seen 033 · confirmed · stays in
lessons.*
*Evidence: challenger 7cf518c3 row 1b; ASSUMED Option 1; task 035 pairs with 033.*

*Claim `030-C1` — Alias remap rewrites the class portion of member qnames. type 5 project-ground-
truth · normative · area: resolver / aliases · seen 030 · confirmed · stays in lessons.*
*Evidence: resolver `_lookup_raw` rpartition; proving test Aka::ping → Real::ping.*

*Claim `029-C1` — parent:: resolution must not walk past an innermost Class_ with null extends. type
5 project-ground-truth · normative · area: php-adapter / receiver-resolution · seen 029 · confirmed
· stays in lessons.*
*Evidence: review finding on feat/029; NestedOuter fixture; Visitor.php enclosingParentQname.*

*Claim `028-C1` — Parse-failure status reads `files.parsed_ok` via `counts()["failed"]`, not a
parallel meta counter. type 5 project-ground-truth · normative · area: index-status / parse-health ·
seen 028 · confirmed · stays in lessons.*
*Evidence: ticket 028 R3 conditional; `code_atlas/store.py` counts(); indexer marks `parsed_ok=0`.*

*Claim `205-C1` — a blast-radius trace searching an ATTRIBUTE shape (`\.pages\b`) or a string key
(`"pages"`) does not find the same symbol used as a **keyword argument** (`pages=(…)`) at a
constructor call site. type: 2 · handle: `grep-the-keyword-argument-too` · status: proposed
(awaiting human confirm) · seen: 205 · area: analysis/design blast-radius tracing · evidence: the
Gate-2 trace enumerated seven test files and missed `tests/test_layer_diagram.py:122`
(`pages=()`) and two of the three `check_artifact(…, max_results=50)` call sites in
`tests/test_onboarding_prose.py`; the suite found them, not the trace. Neighbour of
`count-pin-in-blast-radius` (085-C1) but a different mechanism: pattern shape, not pin awareness ·
destination: `agent_brief_path` (process subject) — recurrence 1, stays in lessons_path until a
second key.*

*Claim `205-C2` — a search piped through `head` (or any cap) is not a search: its visible rows read
as the result set, and the rows beyond the cap are exactly where the miss lives. type: 2 · handle:
`a-capped-search-is-not-a-search` · status: proposed · seen: 203, 205 — **second sighting** · area:
process / evidence gathering · evidence: `grep -n "modules/\|render_module\|page"
code_atlas/onboarding/viewer.py | head -10` returned 10 rows and a *"23 matches in 5 files"* header;
`viewer.py:774` — which promised *"one page per module under `modules/`"* inside every emitted
`index.html` — sat beyond the cap, so `viewer.py` never entered the change list and the ticket-blind
challenger found the false claim instead. 203's ledger row records the first sighting as *"misreading
filtered `ps` output twice, which left three concurrent builds on one database"*. **Count the matches
before you read them, or drop the cap.** destination: **proposed `agent_brief_path`** (process
subject), awaiting a per-claim human ratify.*

*Claim `205-C3` — before removing a key from a set of key names, read which DIRECTION the set
filters: removing it from a **strip**-list has the opposite effect to removing it from an emit-list.
type: 2 · handle: `strip-list-is-not-an-emit-list` · status: proposed · seen: 205 · area: code /
set-shaped config · evidence: the design said to drop `"pages"` from
`architecture_diff._MANIFEST_KEYS`; that set is stripped from a snapshot **on load**
(`architecture_diff.py:115`), so dropping it would have made a pre-205 snapshot diff its 500 page
paths as architectural drift — the precise opposite of the intent · destination: `rulebook_path`
(code subject) — recurrence 1, stays in lessons_path until a second key.*

*Claim `202-C4` **fourth sighting** — `one-field-two-questions` again, and this time the resolution
was **deletion** rather than a second key: `truncated` folded *"a page's neighbour list was capped"*
into *"the walk left an indexed file out"*, and removing the page half narrowed the field to one
question. The narrowing changes committed bytes on an index whose page lists would have been cut,
which is why it is declared and pinned rather than claimed. type: 2 · handle:
`one-field-two-questions` · seen: 189, 022, 202, 205 · status: proposed · destination: **proposed
`rulebook_path`**, awaiting the per-claim human ratify it has been waiting for since 202.*

*Claim `208-C1` — a test that pins a version with a bare literal (`== 10`) also asserts *"the
current version is 10"*, which is not the claim it owns; pin the version the key **arrived at**
(`>= 10`) and leave the current-number pin to the one place that exists to be edited on every bump.
type: 2 · handle: `pin-the-arrival-not-the-current-number` · status: proposed (awaiting human
confirm) · seen: 208 · area: test design / versioned shapes · evidence: 196's
`test_ac3_the_dataset_version_moved_with_the_shape` asserted `DATASET_VERSION == 10` and went red on
208's bump without 196's claim being wrong; `tests/test_onboarding_dataset.py:330`
(`== DATASET_VERSION == 11`) is the deliberate double-pin, and a repo-wide grep found no third ·
destination: `rulebook_path` (code subject) — recurrence 1, stays in lessons_path until a second key.*

*Claim `208-C2` — when adding a field, name it into a contract the project ALREADY derives over, and
its guards cover the new field for free. type: 2 · handle: `name-into-the-existing-contract` ·
status: proposed · seen: 208 · area: code / schema design · evidence: calling the new per-bucket
field `caveat` rather than `unmeasured` made `dataset.derive_caveats` collect it with no edit (it
walks every non-empty `caveat` key at any depth), turned 127's *"every dataset caveat is rendered in
the map"* guard into this ticket's AC3 proof — verified by mutating the viewer and watching that
**unmodified, pre-dating** test go red — and gave `architecture_diff` the bucket's epistemic flip,
which its equal before/after counts (`0 → 0`) cannot show. Three mechanisms inherited for one word ·
destination: `rulebook_path` (code subject) — recurrence 1, stays in lessons_path until a second key.*

*Claim `208-C3` — a suite result taken while another process is mutating the tree is not evidence,
and the only honest use of one is to discard it. type: 2 · handle:
`no-suite-while-a-mutating-reviewer-is-live` · status: proposed · seen: 208 · area: process /
evidence gathering · evidence: the review brief asks the ticket-blind challenger to mutate production
code to prove the guards bite, and I launched the full suite alongside it **twice** in one ticket.
The first run returned `4 failed, 2775 passed` with failures in `test_answer_pagination`,
`test_index_root`, `test_payload_weight` and `test_server_build_on_payloads` — none of which touch
this ticket's subject; the second I killed rather than read. The clean run afterwards was
`2780 passed`. Nothing was corrupted (the challenger's restores were byte-exact both times), but two
suite runs' wall time bought nothing · destination: **proposed `agent_brief_path`** (process
subject), and see the type-3 signal below — nothing in the harness sequences the two.*

*Claim `208-C4` — a guard that goes red proves it bites only if it is red for the reason you think:
check which BRANCH the fixture reached. type: 2 · handle: `red-for-the-right-reason` · status:
proposed · seen: 208 · area: test design · evidence: the first headline fixture closed a cycle over
`app/A.aa`-style paths, which name no responsibility — so `vocabulary` was `False`, the three
vocabulary buckets were **dropped** (the pre-existing AC5 path), and only structural buckets
remained, which can never carry the caveat. The assertion failed with the message I expected while
the fixture never reached the case; closing the cycle over the fixture's own
`app/controller`/`app/service` paths is what made it real · destination: `rulebook_path` — recurrence
1, stays in lessons_path until a second key. Sharpens [[prove-the-guard-fails]] (**R6.5**), which
asks for the red run but not for which branch produced it.*

*Claim `208-C5` — on the anchor monorepo, the `stub_roots` roots its own config file proposes
(`vendor`, `lib/saml/vendor`) match **0** of its 24,535 indexed files: its third-party code lives
under `Zend/`, `legacy/alpha/web/include/pdf/` and `.../adodb/`. Declaring them changes no
count, no bucket and no tour file. type: 5 project-ground-truth · descriptive · handle:
`the-anchors-vendor-code-is-not-under-vendor` · status: proposed · verified-at: 2026-09-02 · area:
onboarding / reachability · evidence: the two-way measurement recorded in
`tasks/208_*.md` (AC6) · destination: stays in lessons_path — the numbers live in the task file and
R7.6 forbids retelling them here.*

*Claim `196-C2` **second sighting** — `grep-the-derived-name-not-the-source-name` earned its keep:
greping the rendered name over the whole tree, rather than the dataclass field, is what found the
**fourth** renderer of the reachability split (`headlines.py:132`) and the **fifth** consumer
(`architecture_diff.py:336`) that the ticket's own *"three renderers"* undercounts. type: 2 ·
handle: `grep-the-derived-name-not-the-source-name` · seen: 196, 208 · status: proposed ·
destination: **proposed `agent_brief_path`** (process subject), awaiting a per-claim human ratify.*

*Claim `205-C2` **third sighting** — `a-capped-search-is-not-a-search` again, one ticket later: a
compacted `grep` printed *"3 matches in 3 files:"* with no rows and hid `LESSONS.md`'s own class
index (`:42-54`), which settles the promotion status of three handles. Every search in 208's refine
and design phases then went through `rtk proxy`. type: 2 · handle:
`a-capped-search-is-not-a-search` · seen: 203, 205, 208 — **third sighting** · status: proposed ·
destination: **proposed `agent_brief_path`**, awaiting the per-claim ratify it has been waiting for
since 205.*

*Claim `212-C1` — a marginal cost fitted from two points is a line, not a curve: measure a third
point NEAR the threshold you are about to set, because the slope that matters is the one there.
type: 2 · handle: `two-points-do-not-fix-a-curve` · status: proposed (awaiting human confirm) ·
seen: 212 · area: measurement / thresholds · evidence: N=1 and N=1,000 gave 0.135 s/file and put the
crossover at 3,616 files, and the number was nearly recorded. N=3,000 measured **213.6 s** where the
line predicted **466 s** — the slope between 1,000 and 3,000 is 0.0088 s/file, 15× flatter, because
the resolve phase saturates. The extrapolation would have shipped a default that traded a ~220 s
delta for a 550 s build · destination: `rulebook_path` (code subject) — recurrence 1, stays in
lessons_path until a second key.*

*Claim `212-C2` — write the field that NAMES a route inside the handler that TAKES the route, never
at the decision that precedes it. type: 2 · handle: `the-key-rides-the-route-not-the-decision` ·
status: proposed · seen: 212 · area: payload honesty · evidence: `scope[DELTA_TOO_LARGE]` was
written at the decision with `raise _TooLarge` after it; the ticket-blind challenger replaced the
raise with `pass` and all six tests stayed green while the payload reported `mode: full` and named a
route for a build that had actually run as a delta — 202's lesson inverted. Moving the numbers onto
the exception and the key into the `except` makes the two inseparable, and the same mutation now
fails two tests · destination: `rulebook_path` (code subject) — recurrence 1, and it sharpens
[[do-not-attest-past-the-payloads-resolution]] (**R5.6**) at a different seam: not what the payload
can distinguish, but *where* the claim is written.*

*Claim `212-C3` — a measurement that says "the mechanism you were asked for would never fire here"
is the deliverable, not a failed ticket; the honest shipment is the mechanism with its threshold
disabled and the numbers recorded beside the constant. type: 2 · handle:
`a-negative-measurement-is-the-answer` · status: proposed · seen: 212 · area: process / R2.3 ·
evidence: Scope 1 measured no crossover below the repo's own size, which falsified Scope 2's premise
(*"a branch touching 5,000 files… certainly is not [cheaper]"* — it is: ~231 s against 550 s). The
maintainer was asked and chose to ship it off; a 3,600 default would have been a number the data
contradicts · destination: `agent_brief_path` (process subject) — recurrence 1, stays in
lessons_path until a second key.*

*Claim `212-C4` — the anchor's incremental cost curve, as of today: noop **7.8 s**, one file
**60.9 s** (resolve 52.5 s), 1,000 files **196.1 s** (resolve 135.1 s), 3,000 files **213.6 s**
(resolve 130.8 s), against a **550 s** full build of 24,569 files / 2.08 M edges. Resolve saturates
by ~1,000 files; a delta is cheaper at every size the repo can reach. 052's 62.296 s no-op is now
7.8 s (080 landed) and the "about an hour" rebuild is 550 s (203 landed). type: 5
project-ground-truth · environment · handle: `the-anchors-incremental-is-cheaper-at-every-size` ·
status: proposed · verified-at: 2026-09-02 · area: indexer / incremental cost · evidence: the task's
CROSSOVER MEASUREMENT block carries every command · destination: stays in lessons_path; it rots when
the resolver or the store's write path changes.*
*(Update, 219, 2026-09-07: the write path changed — `full_build` now truncates before writing, so the
**populated** full-build figure above no longer holds; re-measure the pair when `real_corpus_path` is
configured.)*

*Claim `085-C1` **eighth sighting** — `count-pin-in-blast-radius` again, and this session alone
supplied three of the eight: 205 (a `pages=` keyword argument in a constructor call), 208 (a bare
`DATASET_VERSION == 10`), and 212 (a `KNOBS` precedence table plus an enumerated env-name list with
`len(KNOB_KEYS) == 16`). Every time, the design's blast-radius trace named the production consumers
and missed a hand-listed pin in a test. type: 2 · handle: `count-pin-in-blast-radius` · seen: 085,
087, 088, 089, 184, 022, 194, 212 · status: proposed · destination: **proposed `agent_brief_path`**,
and at eight sightings it is the strongest promotion candidate in this corpus.*

*Claim `208-C3` **second sighting, by avoidance** — `no-suite-while-a-mutating-reviewer-is-live`
held: on 212 the suite ran to completion BEFORE the review seat was dispatched, and no suite result
had to be discarded. The sighting is the application, which is the only evidence a preventive claim
can produce. type: 2 · handle: `no-suite-while-a-mutating-reviewer-is-live` · seen: 208, 212 ·
status: proposed · destination: **proposed `agent_brief_path`**.*

*Claim `ENV-C1` — `205-C4`'s two failures had **two different causes**, and only one of them was the
shebang. Rewriting the first line of the 22 wrong-case console scripts under `.venv/bin` (plus the 5
`activate*` scripts, which export `VIRTUAL_ENV`) fixed every python launcher. **PHPStan was never a
shebang fault at all** — no wrong-case string appears anywhere under `adapters/php`; the failure was
a stale `/tmp/phpstan` tmpDir whose `cache/PHPStan/**` entries were keyed to the wrong-case *phar*
path from an earlier run, which is why `phpstan clear-result-cache` did not clear it: that command
rewrites `resultCache.php` only, not the container/stub cache. Moving the tmpDir aside gave
`[OK] No errors`. `scripts/gate.sh` now reports **`GATE GREEN — all 17 checks passed`** on `main` at
`96dd982`, so **R6.6 is proven** where 205, 208 and 212 each had to disclose it UNPROVEN. type: 5
project-ground-truth · environment · handle: `wrong-case-venv-breaks-the-gate-launcher` · status:
proposed · verified-at: 2026-09-02 · area: environment / gate · supersedes: `205-C4` · evidence:
`bash scripts/gate.sh` → `17 passed · 0 failed · 0 skipped`; `grep -rl "WORKSPACE/Projects"
.venv/bin adapters/php` → no match · destination: stays in lessons_path; it rots the next time the
venv or the PHPStan tmpDir is rebuilt from a wrong-cased cwd.*

- type: 2 (code) · handle: `docstring-knob-must-be-on-the-schema` · seen: 216 · status: proposed
  · destination: open — promote if a second tool repeats the 177/216 shape.

- type: 2 (code) · handle: `partial-count-must-say-partial` · seen: 215 · status: proposed
  · destination: open — promote if a second consumer presents a partial set as complete.

- type: 2 (code) · handle: `resolved-bare-never-enters-heuristic-fallback` · seen: 214 · status: proposed
  · destination: open — promote if a second language hits the same gate.

## Retired — the rule carries the class now

`RECALL:` skips these. The rule named is the one that cites the id.

| claim | handle | rule |
|---|---|---|
| `187-C1` | `read-the-syntax-not-the-text` | R6.7 |
| `PROM-C5` | `ratify-and-retire-are-two-gates` | ? |
| `196-C4` | `assert-the-consumer-not-the-field` | R6.9 |
| `196-C8` | `assert-the-consumer-not-the-field` | R6.9 |
| `196-C5` | `version-the-document-that-moved` | R3.5 |
| `198-C1` | `assert-the-consumer-not-the-field` | ? |
| `197-C1` | `—` | R1.9 |
| `197-C2` | `—` | R3.5 |
| `195-C1` · `183-C1` | `—` | P7 |
| `022-C2` | `skip-dynamic-means-unlinkable` | R5.2 |
| `022-C4` | `two-syntaxes-two-paths` | R6.2 |
| `192-C3` | `read-the-syntax-not-the-text` | R6.7 |
| `184-C3` · `019-C2` | `two-syntaxes-two-paths` | R6.2 |
| `183-C1` · `195-C1` | `an-aggregate-outlives-the-world-that-named-it` | P7 |
| `019-C2` | `two-syntaxes-two-paths` | R6.2 |
| `127-C1` | `guard-asserts-rendered-not-shipped-bytes` | R6.9 |
| `126-C1` | `rank-before-truncate` | R5.8 |
| `105-C2` | `fixture-shape-begs-the-question` | R6.3 |
| `088-C1` | `own-only-what-you-wrote` | R5.7 |
| `085-C1` · `087-C1` · `088-C1` · `PROM-C1` | `count-pin-in-blast-radius` | P5 |
| `085-C2` | `ac-failure-mode-needs-the-right-guard` | R6.8 |
| `102-C1` | `re-verify-the-assumption-on-a-new-path` | P6 |
| `102-C2` | `one-rule-for-every-subject-slot` | R1.8 |
| `100-C1` | `source-the-caveat-from-the-computation` | R5.5 |
| `100-C3` | `re-run-the-sweep-after-the-last-edit` | P4 |
| `100-C4` · `087-C2` · `088-C2` · `094-C1` | `do-not-attest-past-the-payloads-resolution` | R5.6 |
| `094-C1` | `skip-dynamic-means-unlinkable` | R5.2 |
| `095-C2` | `sibling-meta-non-int` | R1.7 |
| `093-C1` | `try-instead-tool-name` | R5.4 |
| `093-C2` · `095-C1` · `097-C1` | `derived-not-listed-invariant` | R6.7 |
| `093-C3` · `089-C1` | `prove-the-guard-fails` | R6.5 |
| `093-C4` · `100-C1` · `100-C3` | `route-must-answer` | R5.4 |
| `205-C4` | `wrong-case-venv-breaks-the-gate-launcher` | ? |

## 248 — filter CONTAINS by member kind before paging

- type: 2 (code) · handle: `filter-contains-by-member-kind-before-page`
- status: proposed · seen: 248
- evidence: Table CONTAINS both Column and ForeignKey (scan.js / 236). Paging all CONTAINS
  targets inflated `total_count` and could fake empty column pages (challenger round 1). Filter
  to `COLUMN_KIND` before `offset`/`cap`.
- destination: docs/LESSONS.md (first sighting; promote when seen ≥ 2)


## 271 — a captured-pipe subprocess with a timeout is not bounded on Windows

- type: 2 (code) · handle: `bound-the-drain-and-kill-the-tree-on-a-captured-pipe`
- status: proposed · seen: 271
- evidence: `subprocess.run(capture_output, timeout)` on Windows, on `TimeoutExpired`, does an
  UNBOUNDED `communicate()` after `kill()` (`Lib/subprocess.py`, `if _mswindows:`), so a grandchild
  holding the pipe wedges the reader past the timeout; POSIX takes `wait()` and does not. Bound with
  a tree kill (`taskkill /F /T`) + a bounded post-kill drain; the tree kill must itself not raise/hang.
- destination: docs/LESSONS.md (first sighting; promote when seen ≥ 2)
