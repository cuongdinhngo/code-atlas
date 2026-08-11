---
id: 075
slug: read-symbol-confident-zero-on-unnormalised-qname
title: '`read_symbol` answers `found: false` with `reason: "ok"` for a class the index holds — one leading backslash apart'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [065, 070, 014]
---

## Goal
`read_symbol` looks a qname up verbatim. The index stores namespaced PHP qnames with a **leading
backslash**; an agent that writes the same name without it gets
`{"found": false, "stale": false, "source": "", "reason": "ok"}` for a class that exists. No
`try_instead`, no hint that a normalisation exists, and `reason: "ok"` — the vocabulary's strongest
"this answer is fine". This is the confident zero the project has spent three field rounds hunting,
and it is reachable by a one-character typo rather than by a modelling gap.

## Evidence (field retro round 4, 2026-08-10, contract v5 / schema 4, post-reconnect build)
- In the work — not a probe — the evaluator asked for a base class as `Ns\Sub\Enum` (no leading `\`)
  and received verbatim:
  ```json
  {"indexed":true,"qname":"Ns\\Sub\\Enum","found":false,"stale":false,
   "source":"","index_root":"<REPO>","reason":"ok"}
  ```
  The class exists at `…/Enum.php:17`, with `__construct` at 26–30 and `get()` at 94–97. The index
  holds it as `\Ns\Sub\Enum`, **with** the backslash — `file_outline` on the same path returned all
  10 symbols and their exact lines, which is how the false negative was caught.
- **What believing it would have cost.** The evaluator was reviewing a dispatched agent's PR that
  added `extends Enum` and justified it by that base class supplying `__construct` and `get()`. The
  next action on `found: false` was to report that the agent had invented a base class — a **false
  CRITICAL on a correct PR**, in a repo whose `CLAUDE.md` instructs agents to trust the graph over
  `grep`. One extra `file_outline` call was the entire margin.
- Round 4's §9 ("if you could change exactly one thing") is this defect, and the two most valuable
  findings in that retro were both found **outside** the fix-verification section — this is one of
  them.
- Counted context: 1 wrong of 8 hand-verified results that session; the only *wrong* one, and the
  only one that arose inside real work rather than a probe.

## Why `reason: "ok"` is the defect, not the missing normalisation
Normalisation is the fix an agent cannot perform for itself; honesty is the fix that keeps the tool
trustworthy even when the lookup legitimately misses. 065 gave the `find_*` family a usable three-way
distinction (`no_such_symbol` / `index_stale` / `ok` + `try_instead`), and round 4 confirmed it works
— including following `try_instead: "file_outline"` to a brand-new symbol. `read_symbol` was never
brought into that vocabulary: it has a `found` boolean and a `reason` that is always `ok`.

## Scope / Deliverables
- **Normalise the subject qname before lookup.** A leading `\` is optional, everywhere a qname is
  accepted, for every tool that takes one — not only `read_symbol`. State the normalisation in one
  place; do not re-derive it per tool.
- **Forbid `reason: "ok"` on a not-found answer.** `found: false` must carry a reason that says
  *which* kind of nothing this is. Pick and pin the vocabulary: at minimum `no_such_symbol`; add a
  distinct value when the miss is explained by the *question's* form rather than the index's contents.
- **Name the route out.** When the lookup misses but a candidate exists under normalisation or a
  suffix match, attach `try_instead: "search_symbol"` (or the tool that would find it) — 065's
  mechanism, reused rather than reinvented.
- **Decide and record the sibling surface.** `read_symbol`, `file_outline`'s symbol arguments,
  `find_*` subjects, `impact`, `explain_path` — each gets an explicit verdict on whether it accepts
  an unnormalised qname today and what it will do after this change.
- **This is the same class of defect as [076](076_bare-name-subject-reads-as-absence.md)** (a bare,
  unqualified subject answering `no_such_symbol`). Design them together; ship one reason-vocabulary
  change if that is the smaller diff, and say so in the design.

## Constraints
- R3 — a new `reason` value is contract vocabulary: bump `contract_version` and extend the
  conformance tests, or reuse an existing value and justify it.
- R4 — normalisation must be deterministic and total: the same input always resolves to the same
  stored form, and a qname that is already normalised is byte-identical to today.
- 061 — attach `try_instead` only when it names a real route; no unconditional field.
- Do not paper over a genuine absence: a symbol that truly is not indexed must still be reported
  absent, with the reason that says so.

## Acceptance criteria
- `read_symbol("Ns\Sub\Enum")` and `read_symbol("\Ns\Sub\Enum")` return the **same** answer for a
  class stored with the backslash; a test pins both forms.
- No payload in the tool surface can carry `found: false` (or an empty result) together with
  `reason: "ok"` — proven by a test that asserts the combination is unreachable.
- A miss that normalisation or suffix-matching could explain carries a `try_instead` naming a tool
  that then finds the symbol, and the test follows that route to a hit.
- Every tool accepting a qname has a recorded verdict, and the ones that normalise are covered.

## References
Field retro round 4 §1 call 4, §3 row 1, §4 row 1, §9, §A.1 (`IMPROVED, not fixed` — the `find_*`
family is honest, `read_symbol` is not). Related:
[065](065_empty-answer-cannot-explain-itself.md) (the reason/`try_instead` mechanism this extends),
[070](070_ambiguous-qname-no-scoping.md) (the other qname-shape ticket),
[076](076_bare-name-subject-reads-as-absence.md) (same class, subject side),
[014](014_search-read-outline.md) (`read_symbol`), [033](033_nav-reason-codes.md) (empty ≠ unknown).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Working doc — 075 (+076 folded) · qname-subject honesty

**Combined run.** This working doc anchors the shared design for **075 + 076** (maintainer chose
"anchor 075, 076 follow", 2026-08-11). Both raw tickets self-declare joint design and a possible
single reason-vocabulary change. 076 keeps its own file and will point at this design; implementation
may split into two commits/PRs — decided at design, not here.

## Session status
- Phase: **1 (analysis) — at Gate 1, awaiting approval.**
- `work_doc_mode`: embed · `TRACK: backend` · `TIER: full` · `SCOPE: L`.
- Branch (proposed): `fix/075-qname-subject-honesty`.
- Next: on Gate-1 approval → design (Gate 2).

## Requirements matrix

`ID | Source | Verbatim (short) | Interpretation | Ph1 evidence (path:line) | Status`

**075 — read_symbol confident zero / normalisation**
- `G75 | G | read_symbol returns found:false+reason:ok for a class one backslash apart` | the confident zero is reachable by a typo | `read_symbol.py:74-82,101-110` return `reason=REASON_OK` on a not-found; lookup is verbatim `nodes_by_qualified_name` (`:53`), no normalisation exists (grep: none) | ✅
- `R75.1 | R | normalise subject qname before lookup, leading \ optional, everywhere, one place` | add `contract.normalize_qname`; call at every qname tool entry | seam site `contract.py:154 split_qname`; per-tool entry points enumerated in inventory | ✅
- `R75.2 | R | forbid reason:ok on a not-found answer` | not-found must carry a reason naming the kind of nothing | `read_symbol.py:81,109` are the offending sites | ✅
- `R75.3 | R | name the route out (try_instead) when a candidate exists under normalisation/suffix` | reuse 065 mechanism; add TRY_INSTEAD_SEARCH_SYMBOL | `nav_result.py:48-52,191-195 attach_try_instead` | ✅
- `R75.4 | R | decide+record the sibling surface per tool` | per-tool verdict table (see inventory N=7) | inventory below | ✅
- `R75.5 | R | same defect class as 076; ship one reason-vocab change if smaller` | this run does exactly that | 076 matrix below | ✅

**076 — bare-name subject reads as absence**
- `G76 | G | find_callers("isEnabled")=no_such_symbol while qualified form=82` | bare subject reads as absence | `find_callers.py:129-155` bare handling only fires when container≠None (`split_qname` → None for a bare name), so a truly bare name falls to `relation_reason(...,symbol_indexed=False)`→`no_such_symbol` (`nav_result.py:182-188`) | ✅
- `R76.1 | R | classify a bare subject before answering: branch on 0/1/many` | count `qname`s ending with the bare name | `store.count_nodes_by_name` (`store.py:658-666`) already counts by `name` column | ✅
- `R76.2 | R | "many" gets its own reason + candidate count + try_instead:search_symbol` | new reason `name_not_qualified` | `nav_result.py:16-46` vocab list (no such value yet) | ✅
- `R76.3 | R | decide the "exactly one" case explicitly (answer+echo qname, or refuse); record why` | design decision | — | ✅ (deferred to design, recorded)
- `R76.4 | R | cover every single-subject tool` | same N=7 inventory | inventory below | ✅
- `R76.5 | R | re-verify 054 Part B against a live index; write verdict into 054` | live-index check | `find_callers.py:131-137,170-171 unresolved_bare_calls` | ✅
- `R76.6 | R | coordinate with 075; one reason-vocab change may serve both` | this combined run | — | ✅

**Shared constraints (075 C1-4 + 076 C1-4)**
- `C1 | C | R3 — new reason value bumps contract_version + extends conformance` | v5→v6, update `tests/contract` | R3 (ENGINEERING_RULES) | ✅
- `C2 | C | R4 — normalisation deterministic+total; already-normalised byte-identical` | pure string op, no I/O | R4.1/4.2 | ✅
- `C3 | C | 061 — try_instead only when it names a real route; no unconditional field` | conditional attach | `nav_result.py:191-195` | ✅
- `C4 | C | do not paper over genuine absence; bound the bare-name scan + disclose (066)` | 0-candidate stays no_such_symbol; count is a bounded COUNT(*) | `store.py:658-666` | ✅

## AC validation table (falsifiable? / computed value)
- `AC75.1` read_symbol of `Ns\Sub\Enum` == `\Ns\Sub\Enum` for a stored-with-backslash class — **falsifiable** (pinned test, both forms).
- `AC75.2` no payload in the tool surface carries `found:false`/empty **and** `reason:ok` — **falsifiable** (surface-wide test asserts combination unreachable). *Computed note:* today `read_symbol` and any tool defaulting to `REASON_OK` on empty must be swept; `file_outline` returns `REASON_OK` (`file_outline.py:73`) — its not-found path must be checked in design.
- `AC75.3` a normalisation/suffix-explained miss carries `try_instead` that then finds it — **falsifiable** (test follows the route to a hit).
- `AC75.4` every qname-accepting tool has a recorded verdict; normalising ones covered — **falsifiable** (inventory N=7, one test each).
- `AC76.1` bare name w/ candidates → reason ≠ `no_such_symbol`, carries count + try_instead; whole payload pinned — **falsifiable**.
- `AC76.2` bare name w/ zero candidates → still `no_such_symbol` — **falsifiable**.
- `AC76.3` qualified form byte-identical to today (R4) — **falsifiable** (golden payload).
- `AC76.4` every single-subject tool has a bare-name test or a recorded reason it cannot — **falsifiable** (inventory).
- `AC76.5` 054 Part B has a live-index verdict written into ticket 054 — **manual-recorded** (a written verdict, not a code assertion → recorded manual-check, not a bare ✅).

All AC values falsifiable except AC76.5 (recorded manual-check exclusion — a doc verdict).

## SECTIONS / CLARIFICATION
`SECTIONS: 14 found (075: Goal, Evidence, Why-reason-ok, Scope, Constraints, AC, Refs; 076: Goal, Evidence, What-honest, Scope, Constraints, AC, Refs) | 14 decomposed | ROWS: G=2 R=11 C=4 AC=9`

`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
1. New reason value: propose **`name_not_qualified`** (076's name), distinct from existing
   `bare_name_truncated` (054 = "resolution capped", not "you under-qualified") — self-resolved,
   cited `nav_result.py:32`. Ratify at Gate 2 (contract bump).
2. "Exactly one" bare-name case → propose **answer it and echo `resolved_qname`** (max signal, and
   065 already normalises the "say what it resolved to" habit) — self-resolved, decide at design.
3. Normalisation seam location → **`contract.py`** (single source of qname vocabulary, R3;
   `split_qname` already lives there) — self-resolved, cited `contract.py:154`.

`j = 0` → Gate 0 not required.

## Universal inventory — qname-accepting tools (N = 7)
`tool | qname arg | today | verdict after change`
1. `read_symbol` | `qname` | verbatim lookup, `reason:ok` on miss | normalise; miss → `no_such_symbol`/`name_not_qualified` + `try_instead`
2. `find_callers` | `qname` | partial bare handling (container≠None only) | normalise; bare → classify 0/1/many
3. `find_references` | `qname` (`:40,93,116`) | `relation_reason` → no_such_symbol on bare | normalise; bare classify
4. `find_implementations` | `qname` (`:33,73,97`) | same | normalise; bare classify
5. `impact` | `qname` (`:20,86`) | `nodes_by_qualified_name` gate | normalise; bare classify
6. `explain_path` | `from_qname`,`to_qname` (`:21-22`) | two subjects, `not_indexed` | normalise both; bare classify each
7. `find_view_data` | `qname` (`:37,77,90`) | `relation_reason` | normalise; bare classify
- **Not qname-subject (recorded N/A):** `file_outline` (takes a path, `:22`), `search_symbol` (fuzzy name — the escape hatch `try_instead` points to). Freshness `ensure_qname` (`freshness.py:54-56`) also looks up by qname → must receive the normalised form.

## Cause / gap (taxonomy: logic)
- **075** — `logic`: `read_symbol` maps a legitimate miss to the strongest "fine" token (`reason:ok`),
  and never normalises the optional leading `\`. Two independent gaps: honesty (reason) + normalisation.
- **076** — `logic`: the subject-side classifier (`relation_reason`) only knows indexed/not-indexed;
  it never asks "is this a bare name that N indexed symbols end with", so an under-qualified question
  reads as absence. 054 fixed the resolver (edge) side only.

## Blast radius
- Core, no adapter/store schema change. New: `contract.normalize_qname`, `nav_result` reason
  `name_not_qualified` + `TRY_INSTEAD_SEARCH_SYMBOL` + a bare-subject classify helper. Edits at 7 tool
  entries + `freshness.ensure_qname`. Contract bump v5→v6 + `tests/contract` conformance. Repos: `app` only.
- Test blast-radius (mechanical, to finish at design): existing assertions on `read_symbol` not-found
  `reason:ok` and on bare-name `no_such_symbol` will invalidate — candidate specs: `test_nav_reason_codes.py`,
  `test_empty_answer_cannot_explain_itself.py`, `test_bare_name_callers_silent_drop.py`,
  `test_nav_tools.py`, contract conformance. Each folds in as **proof collateral** in the design change-list.

## BASELINE
`BASELINE: unconfirmed-this-session (Windows host)` — bare `pytest` is red at collection here (`fcntl`
import), the **known platform exclusion** documented in AGENTS.md, not a regression. Green expected
**~1081 passed** via `scripts/docker-test.sh`. Delta-green will be proven in Docker at execute before
any PR (AGENTS.md ship-discipline). No baseline red is being masked.

`TRACK: backend — 0/N touched files under UI paths` · `SCOPE: L` (two tickets, 7-tool surface, contract bump) · `TIER: full`.

## Phase 2 — Design (Gate 2)

### Approach
One **language-agnostic subject resolver** serves both tickets: 076's 0/1/many bare-subject classifier
**subsumes** 075's leading-`\` case (`Ns\Sub\Enum` is just a boundary-suffix match with exactly one
candidate, `\Ns\Sub\Enum`). No `\` is hardcoded in the core — the leading backslash is PHP-adapter
canon (`adapters/php/src/Visitor.php:1087` `'\\' . ltrim($name,'\\')`), and `code_atlas/` knows only
`MEMBER_SEPARATOR`. The resolver keys off the **generic identifier-character class** `[A-Za-z0-9_]`
(lexical, not a language branch — same tolerance the `_COMMENT` regex already relies on).

`resolve_subject(store, qname, *, limit) -> SubjectResolution` (new, in `nav_result.py` — the shared
nav module, no new seam per R1.2):
1. exact `nodes_by_qualified_name(qname)` hit → `status=exact`, unchanged.
2. miss → trailing identifier of `qname` (chars after the last non-identifier run); fetch candidates
   whose `name == trailing` **and** whose `qualified_name` ends with `qname` at a component boundary
   (prefix empty or ending in a non-identifier char), capped `limit+1`.
3. branch on the boundary-filtered candidate count: **0 → `absent`** (`no_such_symbol`, unchanged);
   **1 → `resolved_unique`** (re-point to the stored qname); **many → `ambiguous`**
   (`name_not_qualified` + `candidate_count` floor + `try_instead: search_symbol`).

Per tool, on the miss path only (C4 — a hit never pays): `read_symbol` reads the `resolved_unique`
node and echoes the **stored** qname, so `read_symbol("Ns\Sub\Enum")` is **byte-identical** to
`read_symbol("\Ns\Sub\Enum")` (AC75.1); the `find_*`/`impact`/`explain_path` family re-points a
`resolved_unique` subject and adds `resolved_qname`, or returns `name_not_qualified` for `ambiguous`.

### Rejected alternatives
- **Hardcode leading-`\` normalisation in `contract.normalize_qname`.** Smallest diff, matches 075's
  literal wording — but leaks PHP canon into the language-agnostic core (R1.1 risk) and only fixes 075,
  leaving 076 a separate mechanism. Rejected: violates "one change serves both" and the seam rule.
- **Carry the namespace anchor as adapter meta + core strips it.** Architecturally purest (data-driven,
  R1.1-clean) but forces a real adapter-contract change + reindex for every user. Rejected: over-built
  for a tool-output concern; YAGNI until a second adapter needs it (R1.2).
- **New `store.count_nodes_by_name`-only bare classify (076) + separate `\`-variant lookup (075).**
  Two mechanisms for one defect class; more code, misses the unification the tickets asked for.

### Assumptions
- `verified` — PHP stores symbol qnames as `\`+ltrim, files by path (`Visitor.php:80,1087`; README:108). Spike = code read.
- `verified` — nav reason codes are **not** gated by adapter `CONTRACT_VERSION`: it is still `5`
  (`contract.py:21`) though 054/065/069 all added reasons. Adding `name_not_qualified` therefore needs
  **no** adapter bump / reindex — it extends `NAV_REASONS` + `tests/test_nav_reason_codes.py` only.
  **This corrects ticket constraint C1** (surfaced, not silently applied).
- `verified` — `name` column holds the unqualified short name and is indexed (`store.py:68,658`), so the
  candidate prefilter is index-seekable; the boundary suffix runs only over the small `name`-matched set.
- `verified` — the `total_count>0 & not-indexed` case (vendor targets, `test_nav_reason_codes.py:163`)
  never reaches the resolver: it runs strictly on the `total_count==0 & not-indexed` branch, so that
  test stays green.

### Smallest change-list  (change | file | Ph2 covers | k/N)
1. reason `name_not_qualified` + `TRY_INSTEAD_SEARCH_SYMBOL` + `NAV_REASONS`/Literal | `nav_result.py` | R76.2,C1 | 1/6
2. `resolve_subject` + `SubjectResolution` + boundary-suffix helper | `nav_result.py` | R75.1,R76.1,R76.3 | 2/6
3. store `nodes_by_qname_endswith(trailing, suffix, *, limit)` (SQL-only, `name=?` prefilter + endswith) | `store.py` | R76.1,C4 | 3/6
4. wire resolver on miss path (read_symbol resolve+byte-identical; find_callers/refs/impls/view_data/impact/explain_path re-point or `name_not_qualified`) | 7 tool files | R75.2,R75.4,R76.4 | 4/6
5. attach `candidate_count`/`resolved_qname`/`try_instead` conditionally (061) | `nav_result.py` | R75.3,C3 | 5/6
6. contract vocab test + new `tests/test_qname_subject_honesty.py` + 054 Part-B verdict | tests + `tasks/054` | AC*,R76.5 | 6/6
- **Proof collateral (test blast-radius, folded in):** `test_nav_reason_codes.py:151` pins the exact
  `NAV_REASONS` tuple → extend it. Sweep for existing `reason:ok`-on-miss / bare-`no_such_symbol`
  assertions in `test_empty_answer_cannot_explain_itself.py`, `test_bare_name_callers_silent_drop.py`,
  `test_nav_tools.py`, contract conformance — adjust any that pin the old behaviour.

### Rule compliance
R1.1 no language branch (identifier class is generic lexing) · R1.2 no new seam (helper in existing
`nav_result`) · R1.4 all SQL stays in `store.py` · R3 tool-vocab extended in its single source
(`NAV_REASONS`), adapter contract untouched · R4.1/4.2 pure/deterministic (`_NODE_ORDER`, no I/O) ·
R4.3 bounded (`limit+1`, name-prefiltered) · 061 conditional fields · 066 disclose the count floor.

### Verification plan (per-AC · risk layer · proof · layer-match)
- AC75.1 read_symbol both forms identical | logic | unit (golden payload both forms) | ✅
- AC75.2 no `found:false`+`reason:ok` anywhere | logic | unit — enumerate tool surface, assert unreachable | ✅
- AC75.3 miss→`try_instead` then finds it | logic | unit — follow route to a hit | ✅
- AC75.4 every qname tool has a recorded verdict | logic | unit per tool (N=7) + inventory | ✅
- AC76.1 bare+candidates→`name_not_qualified`+count+try_instead | logic | unit (whole payload pinned) | ✅
- AC76.2 bare+zero→`no_such_symbol` | logic | unit | ✅
- AC76.3 qualified byte-identical | logic | unit (golden) | ✅
- AC76.4 every single-subject tool bare-name test | logic | unit per tool | ✅
- AC76.5 054 Part-B live verdict written into 054 | doc | **manual-recorded** (coverage-gap exclusion — a written verdict) | recorded
No ❌. AC76.5 is the one recorded manual-check exclusion (a doc verdict, not a code assertion).

### Proving test
`pytest -q tests/test_qname_subject_honesty.py::test_read_symbol_normalises_leading_anchor` — asserts
`read_symbol("Ns\\Sub\\Enum")` returns `found:true` with source byte-identical to the `\\`-form.
**Fails pre-change** (`found:false`, `reason:ok`), **passes post-change**. Risk layer = logic → unit proof matches.
Companion: `::test_bare_name_subject_is_name_not_qualified` (find_callers bare `isEnabled`, many candidates).

### Rollback + porting
Revert the branch — no schema/index/contract change, so **no reindex**; clean revert. Single repo `app`.

### SCOPE re-affirm
`SCOPE: L` holds (unchanged from analysis). The unified mechanism means **one PR (anchor 075) delivers
both 075 and 076** — no artificial split; 076's ticket is closed by this change + its own Part-B verdict
and per-tool tests. (Supersedes the analysis note "may split into two PRs".)

### Decision log
- D1: unified `resolve_subject`, not `\`-hardcode — R1.1-clean, one mechanism for both tickets.
- D2: **no adapter `CONTRACT_VERSION` bump** — reason codes are tool-output vocab, not adapter contract; corrects C1.
- D3: `resolved_unique` → answer + echo `resolved_qname` (076 R76.3 "exactly-one" case); read_symbol stays byte-identical.

**Session status:** Phase 2 (design) complete — Gate 2.

## Phase 3 — Execute

Branch `fix/075-qname-subject-honesty`. Change-list delivered exactly as designed:
- `store.py` — `nodes_by_qname_endswith(name, suffix, *, limit)` (indexed `name=?` prefilter + suffix LIKE).
- `nav_result.py` — `REASON_NAME_NOT_QUALIFIED` + `NAV_REASONS`/`NavReason`; `TRY_INSTEAD_SEARCH_SYMBOL`;
  `SubjectResolution` + `classify_missing_subject` (0/1/many boundary-suffix, generic `[A-Za-z0-9_]`);
  `_ends_at_boundary`; `attach_name_not_qualified`.
- Wired on the miss path of all 7 qname tools: `read_symbol` (re-point + byte-identical, `_resolve_miss`),
  `find_callers`/`find_references`/`find_implementations`/`find_view_data` (`name_not_qualified` on the
  not-indexed empty branch — disjoint from 054's indexed-empty `bare_name_truncated`), `impact`
  (`_resolve_seed` re-points unique seeds), `explain_path` (`_resolve_endpoint` re-points unique endpoints).
- Tests: new `tests/test_qname_subject_honesty.py` (13 tests — proving test + AC75.1-4 / AC76.1-4 +
  surface sweep + multi-subject re-point); `NAV_REASONS` pins updated in `test_nav_reason_codes.py` and
  `test_empty_answer_cannot_explain_itself.py` (proof collateral, as designed). 054 Part-B live verdict
  written into `tasks/054`. 076 points at this shared design.
- **No adapter `CONTRACT_VERSION` bump** (D2) — reason vocab is tool-output, not adapter contract.

**Local (Windows):** ruff ✅ · mypy ✅ on changed code (the 5 `index_lock` `fcntl` errors are the known
Windows-only mypy noise, Linux-clean); targeted pytest for the touched tools green except the documented
adapter-subprocess exclusion. **Delta-green proof: `scripts/docker-test.sh` (Linux + PHP) — pending.**

## Phase 4 — Review — SKIPPED (maintainer instruction 2026-08-11; waived gate, not reintroduced).

## Cost ledger
| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| — | none (whole run on the main loop; review skipped, no fan-out) | — | 0 dispatch |

`LEDGER TOTAL: 0 dispatch rows.` Main-loop spend unmeasured (mango measures dispatch only; `rtk gain`
is a global all-time figure not attributable to one task) — as for 024/032/034/044-053.

## Decision log
- D1 unified `resolve_subject` (not `\`-hardcode) — R1.1-clean, one mechanism for both tickets.
- D2 no adapter `CONTRACT_VERSION` bump — reason codes are tool-output vocab; corrects ticket C1.
- D3 `find_*` treat the exactly-one case as `name_not_qualified` (count 1) — 076 R76.3 "refuse uniformly";
  `read_symbol`/`impact`/`explain_path` re-point (AC75.1 forces read_symbol to).
