---
id: 259
slug: one-knob-sets-both-index-size-and-page-truthfulness
title: '`CA_MAX_RESULTS` is both the query-time page cap and the build-time resolver fan-out, so the value an operator picks to keep the index small silently caps how much of an answer a caller page is allowed to show — the anchor pinned it to 10 and thereby pinned every `find_callers` page to ten rows'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [251, 138]
---

## Why this exists

One config value spans two unrelated decisions:

- **Build-time fan-out.** `indexer.py:617` and `:673` pass it as `resolve_edges(..., max_candidates=config.max_results)` — it caps how many candidates a multi-match HEURISTIC link may consider, i.e. **index size**.
- **Query-time page cap.** `config.clamp_limit(limit, max_results)` (`config.py:488`) makes it the ceiling on every nav page.

`get_index_status` already admits the conflation in its own words — *"disk / nav / resolver knob"*.

The anchor repo pinned `max_results = 10` to hold 2.6M heuristic edges. The consequence was not a smaller index; it was that **every caller page on that repo is ten rows long**. [251](251_the-resolved-caller-can-be-off-the-page.md) found the `RESOLVED` caller sitting on page 12 under vendor `build()` noise. An operator tuning disk usage was, without being told, tuning **how much of the truth a page may contain**.

This is the root of the page-1 class. Fixing ordering ([265](265_the-default-page-order-is-the-alphabet.md)) while this knob still caps the page at ten leaves the fix cosmetic on exactly the repo that needs it.

## Scope / Deliverables

- **Two config keys.** A query-time page cap (new default **50**) and a build-time resolver fan-out (keeps today's default and today's meaning). `contract`/`config.py` is the single source; `clamp_limit` reads the page cap only.
- **Changing the fan-out is a build decision** — it must require a rebuild to take effect and say so, exactly as it does today. Changing the page cap must never require a rebuild.
- **Back-compat.** `CA_MAX_RESULTS` set alone keeps working and keeps its build-time meaning; the page cap falls back to its own default rather than inheriting the fan-out value. A repo that pinned 10 for disk reasons gets 50-row pages on upgrade **without** a rebuild — that is the point of the ticket, and it must be stated in the runbook.
- **`get_index_status`** stops describing one knob as three things and names each key with its scope.

## Constraints

- R4.2: identical input → identical rows. Raising the page cap changes page *length*, never row order or row content.
- Do not raise the fan-out default to "fix" 251 — [creator note §1, remaining-improvements §1] name widening the knob as the wrong fix. The page cap is the knob that moves.
- No new tool, no new payload field beyond the status rename.

## Acceptance criteria

- `CA_MAX_RESULTS` no longer reaches `resolve_edges`; a grep for the old symbol in `indexer.py` returns the new fan-out key.
- A test pins: page cap default 50; fan-out default unchanged; setting the fan-out does not change any page length; setting the page cap does not change any edge count in a rebuilt index.
- A test pins the back-compat arm: `CA_MAX_RESULTS=10` alone yields fan-out 10 **and** page cap 50.
- `runbooks/onboarding-a-repo.md` states which key needs a rebuild and which does not.

## References
[251](251_the-resolved-caller-can-be-off-the-page.md) (the `RESOLVED` caller on page 12), `code_atlas/indexer.py:617`, `code_atlas/config.py:488`, `code_atlas/tools/get_index_status.py`.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Session status

- **KEY:** 259 · **work_doc_mode:** embed · **Current phase:** finalise
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · **Type:** enhancement
- Run: `/mango:autorun 259` with `--no-reviewer`; challenger ON
- Branch: `feat/259-one-knob-sets-both-index-size-and-page-truthfulness`
- Contract: `.mango/run-contract-259.txt`
- Handover: push feature branch + open PR only (never merge)

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

**PREMISE detail.** Present: `code_atlas/indexer.py` (`max_results`→`resolve_edges` at :617/:673), `code_atlas/config.py` (`clamp_limit`, `KNOB_KEYS`, `max_results`), `code_atlas/tools/get_index_status.py` ("disk / nav / resolver knob"), `CA_MAX_RESULTS` / `env_name`, `docs/runbooks/onboarding-a-repo.md`, ticket [251](251_the-resolved-caller-can-be-off-the-page.md). Ambiguous (surfaced, not blocking): creator note §1 / remaining-improvements §1 prose (not a resolvable identifier).

refine skipped: 0 unresolved product-decisions. INPUT KIND: ticket.

**Recalled claims — advisory.**

| # | Claim | Type | Matched by | Relevant here? |
|---|---|---|---|---|
| 1 | `one-field-two-questions` | 2 | handle | Yes — the ticket IS that class: one knob answering index size and page length; split is the fix (advisory only; does not inject AC) |



## Phase 1 — analysis

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria) | 4 decomposed | ROWS: C=3 R=4 G=2 AC=4`
`CLARIFICATION: 5 raised | 5 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/N touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`
`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ no language branch in config/indexer split · R4.2 (change-type) ✅ page_limit length only never row order/content · R5.3 (change-type) ✅ malformed CA_* still ConfigError · R6.5 (change-type) ✅ proving tests pin defaults+back-compat · R6.9 (change-type) ✅ status fields name scope · R7.2 (change-type) ✅ TOKEN_LEDGER+BACKLOG · R7.6 (change-type) ✅ runbook/TOOLS/README prune superseded conflation`

### BASELINE

```
Ran at 042d955a4b99c5ddf482d7e9adcf703b42cf1f85
$ .venv/bin/python -m pytest -q --tb=no
3765 passed, 3 skipped in 315.09s (0:05:15)
```

Green. No baseline exclusions. Full suite on untouched checkout (adapters present).

### Clarifications (j = 0) — HOW decisions, handover-authorised

| # | Question | Resolution | Citation |
|---|---|---|---|
| Q1 | Page-cap field / env name? | **`page_limit` / `CA_PAGE_LIMIT`** — clear scope; joins `KNOB_KEYS` + `env_name` | CONVENTION env `CA_*` from key; ticket Scope; user product intent |
| Q2 | Fan-out field / env name? | **`max_candidates` / `CA_MAX_CANDIDATES`**; indexer uses `config.max_candidates` only | ticket AC1; `indexer.py:617` already names the resolve_edges kwarg `max_candidates` |
| Q3 | `CA_MAX_RESULTS` alone? | Alias → **`max_candidates` only**; page_limit stays default 50 (does not inherit) | ticket Back-compat + AC3 |
| Q4 | Project-file `max_results`? | Alias → **`max_candidates`** (preserves build-time meaning of pinned repos) | ticket Back-compat; same as env alias |
| Q5 | Identity / rebuild? | **`page_limit` excluded from `config_identity`** (`QUERY_ONLY_KEYS`); `max_candidates` (+ alias env) stays in identity | ticket Scope "page cap must never require rebuild"; `config.py:176` identity from `_config_env_slice` |

### Cause / gap

**Root cause (config):** one `Config.max_results` / `CA_MAX_RESULTS` field is threaded to both `resolve_edges(..., max_candidates=…)` (build) and `clamp_limit(..., config.max_results)` (query). Operator disk pin becomes page pin. Taxonomy: **config**.

**Gap:** no separate query-time ceiling; `get_index_status` admits conflation (`"disk / nav / resolver knob"`).

### Blast radius

- `code_atlas/config.py` — knobs, load, identity, `clamp_limit` callers pass page_limit
- `code_atlas/indexer.py` — two `resolve_edges` sites → `max_candidates`
- `code_atlas/tools/get_index_status.py` — status fields per key+scope
- Every `config.max_results` query site → `config.page_limit` (tools, hooks, onboarding caps that used the same ceiling)
- Tests: `test_config.py` Knob table, provenance identity, new proving test
- Docs: runbook, TOOLS/README as affected, TOKEN_LEDGER, BACKLOG, task frontmatter

### Requirements matrix

| ID | Source | Verbatim (abbrev) | Interpretation | Ph1 evidence | Status |
|----|--------|-------------------|----------------|--------------|--------|
| G1 | Why | one value spans build fan-out and page cap | Split into two knobs | indexer+clamp_limit | open |
| G2 | Why | disk pin silently capped every page | Pinning fan-out must not shrink pages | AC3 + runbook | open |
| R1 | Scope | two config keys; clamp_limit reads page only | `page_limit` + `max_candidates`; clamp on page | config.py | open |
| R2 | Scope | fan-out rebuild; page never rebuild | page_limit out of identity | config_identity | open |
| R3 | Scope | CA_MAX_RESULTS alone keeps build meaning; page→own default | alias→max_candidates; page=50 | load_config | open |
| R4 | Scope | get_index_status names each key with scope | stop triple-knob prose; two fields | get_index_status.py | open |
| C1 | Constraints | R4.2 page length ≠ order/content | page_limit only changes length | R4.2 | open |
| C2 | Constraints | do not raise fan-out default | DEFAULT_MAX_CANDIDATES stays 50 | config defaults | open |
| C3 | Constraints | no new tool; status rename OK | status field rename only | get_index_status | open |
| AC1 | AC | CA_MAX_RESULTS no longer reaches resolve_edges; indexer grep → new key | `max_candidates=config.max_candidates`; no `config.max_results` in indexer | grep + test | open |
| AC2 | AC | defaults + independence: fan-out≠page length; page≠edge count | proving test | test | open |
| AC3 | AC | CA_MAX_RESULTS=10 alone → fan-out 10 and page 50 | proving test back-compat arm | test | open |
| AC4 | AC | runbook states which key needs rebuild | onboarding-a-repo.md | doc | open |

### AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? |
|-------|---------------|------------------------|--------|--------------|
| AC1 | no CA_MAX_RESULTS→resolve_edges; indexer grep new fan-out key | Today: `max_candidates=config.max_results` at indexer:617/:673; target `config.max_candidates` | Y | greppable |
| AC2 | page default 50; fan-out default unchanged; independence | Both defaults currently 50 (`DEFAULT_MAX_RESULTS`); fan-out must stay 50; independence via two env axes | Y | test measurable |
| AC3 | CA_MAX_RESULTS=10 → fan-out 10 + page 50 | Back-compat arm | Y | test measurable |
| AC4 | runbook names rebuild vs not | Doc assertion | Y | greppable in runbook |

### Inventory

No counted "for each of N" requirement with N>1 beyond the two indexer resolve_edges sites (both covered by AC1) and the two status keys (R4). Denominator N for indexer sites = 2 (enumerated in Ph3).



## Phase 2 — design

### Approach

Split the conflated knob into **`max_candidates`** (build-time resolver fan-out; default 50; env `CA_MAX_CANDIDATES`; aliases `CA_MAX_RESULTS` + project-file `max_results` → fan-out only) and **`page_limit`** (query-time page cap; default 50; env `CA_PAGE_LIMIT`). `clamp_limit` callers pass `config.page_limit`. Indexer `resolve_edges` sites use `config.max_candidates` only. Exclude `page_limit` from `config_identity` via `QUERY_ONLY_KEYS` so changing the page cap never forces a rebuild. `get_index_status` exposes two scoped fields (status rename allowed).

### Rejected alternatives

1. **Raise fan-out default to "fix" 251** — ticket Constraints + creator note §1 name this the wrong fix; page length is the knob that moves.
2. **Keep `Config.max_results` as the page field; only add `max_candidates`** — leaves the overloaded name in the API and status; ticket asks for clear scopes and status rename.
3. **Make `CA_MAX_RESULTS` set both** — contradicts Back-compat: page must fall to its own default so a disk pin of 10 yields 50-row pages without rebuild.

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| 1 | Excluding `page_limit` from `_config_env_slice` / identity is sufficient for "no rebuild" (same mechanism as today for knobs not in the hash) | verified — `config_identity` / `_config_env_slice` (`config.py:164-196`) |
| 2 | Alias precedence: explicit `CA_MAX_CANDIDATES` / `max_candidates` wins over `CA_MAX_RESULTS` / `max_results` | verified — ticket Back-compat "set alone"; HOW Q3/Q4 |
| 3 | Mechanical `config.max_results`→`config.page_limit` at query sites preserves behaviour when both defaults are 50 | verified — both defaults 50 today |

No novel-untested 3p/runtime assumption.

### Change list

| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|--------|-----------|--------------|----------------|-----|
| 1 | Add `max_candidates` + `page_limit` to `KNOB_KEYS`; `QUERY_ONLY_KEYS`; aliases; load; identity | `code_atlas/config.py` | all Config consumers; test_config Knob table; provenance identity tests | R1 R2 R3 C2 AC2 AC3 | 6/13 |
| 2 | `resolve_edges(..., max_candidates=config.max_candidates)` at both sites; no `config.max_results` in indexer | `code_atlas/indexer.py` | rebuild-only; AC1 grep | AC1 R2 C2 | 3/13 |
| 3 | Status: two scoped fields; drop "disk/nav/resolver" conflation | `code_atlas/tools/get_index_status.py` | status consumers / docs citing `max_results` field | R4 C3 | 2/13 |
| 4 | `config.max_results` → `config.page_limit` at every query-time consumer | tools/hooks/onboarding listed in blast | payload sizes / clamp | R1 G1 C1 | 3/13 |
| 5 | Proving + config Knob/table/identity retarget | `tests/test_page_limit_max_candidates_split.py` + `tests/test_config.py` (+ hit tests) | suite | AC1–AC3 | 3/13 |
| 6 | Runbook rebuild vs not; README/TOOLS knobs; TOKEN_LEDGER; BACKLOG; task status | docs | operators | AC4 G2 R7.2/7.6 | 2/13 |

**Proof collateral (mechanical consumers of `config.max_results`):** hooks/signal, onboarding/prose, architecture_overview, check_architecture_rules, check_column_defaults, class_diagram, explain_path, file_outline, find_callers, find_implementations, find_orphans, find_references, find_view_data, generate_onboarding, guided_tour, impact, impact_modules, include_graph, read_symbol, search_symbol, subtree_dependencies, trace_capability — all fold into change #4. Tests: test_config, test_onboarding_prose, test_search_read_outline, test_trace_capability, test_generate_onboarding, test_ambiguous_qname, test_list_parse_failures — fold into #5.

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**H1 `one-field-two-questions`** — traced.

```
Ran at 042d955a4b99c5ddf482d7e9adcf703b42cf1f85
$ rg -n 'max_candidates=config\.max_results|governs.*returned_rows|disk / nav / resolver' code_atlas/indexer.py code_atlas/tools/get_index_status.py
code_atlas/indexer.py:617:    siblings = resolve_edges(store, max_candidates=config.max_results, delta=delta)
code_atlas/indexer.py:673:                resolve_edges(store, max_candidates=config.max_results, file_path=path)
code_atlas/tools/get_index_status.py:62: ... disk / nav / resolver knob).
code_atlas/tools/get_index_status.py:137:        "governs": ["returned_rows", "resolver_candidate_fanout"],
```

Folded: change #1–#3 split the one field into two scoped knobs (the handle's remedy).

### Coverage-gap exclusions

none

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match |
|----|------------|----------------|--------------------|-------------|
| AC1 | logic | grep + `test_indexer_uses_max_candidates_not_max_results` | n/a | ✅ |
| AC2 | logic/integration | `test_defaults_and_independence` | authored | ✅ |
| AC3 | logic | `test_ca_max_results_alone_yields_fanout_10_and_page_50` | n/a | ✅ |
| AC4 | logic (doc) | runbook grep in suite or review | n/a | ✅ |

### Proving test

```
.venv/bin/python -m pytest tests/test_page_limit_max_candidates_split.py::test_ca_max_results_alone_yields_fanout_10_and_page_50 -q
```

Fails pre-change (today both become 10); passes post-change (fan-out 10, page 50).

### Rollback

Revert the feature branch / PR. No schema bump; existing indexes remain valid (page_limit is query-only).

### Porting

Single repo (`app`). SCOPE remains **M**.

✋ **Gate 2** — design complete; autorun closes on artifacts.



## Phase 3 — execute

Branch already checked out: `feat/259-one-knob-sets-both-index-size-and-page-truthfulness`.

### Implemented (⊆ approved change list)

| # | Change | Done |
|---|---|---|
| 1 | config split + QUERY_ONLY_KEYS + aliases | ✅ |
| 2 | indexer max_candidates | ✅ |
| 3 | get_index_status scoped fields | ✅ |
| 4 | query sites → page_limit | ✅ |
| 5 | proving + config tests | ✅ |
| 6 | runbook/README/TOOLS/CONVENTION/PLAN/ledger/BACKLOG/task | ✅ |

### Verification sweep

```
Ran at 042d955a4b99c5ddf482d7e9adcf703b42cf1f85
$ .venv/bin/python -m pytest tests/test_page_limit_max_candidates_split.py::test_ca_max_results_alone_yields_fanout_10_and_page_50 -q
.                                                                        [100%]
1 passed in 1.30s
```

```
Ran at 042d955a4b99c5ddf482d7e9adcf703b42cf1f85
$ rg -n 'max_candidates=config.max_candidates|config.max_results' code_atlas/indexer.py
617:    siblings = resolve_edges(store, max_candidates=config.max_candidates, delta=delta)
673:                resolve_edges(store, max_candidates=config.max_candidates, file_path=path)
```

Axis 1: diff ⊆ change list (config/indexer/status/tools/hooks/onboarding/tests/docs). Axis 2: approach bullets implemented-as-approved; no deviation. Naming chosen: `page_limit` / `CA_PAGE_LIMIT` + `max_candidates` / `CA_MAX_CANDIDATES`.


## Phase 4 — Review

**REVIEWER: OFF (--no-reviewer)** — waived; no rule-book-grounded review ran.
**CHALLENGER: ON** — ticket-blind, 1 dispatch (orchestrator-run; Cursor has no mango `Task` challenger agent — same input contract: raw ticket above separator + `git diff main...HEAD` only).

### Challenger reconstructed requirements

| # | Requirement (from raw ticket) | Verdict | Evidence |
|---|---|---|---|
| 1 | Two config keys: page cap default 50 + fan-out keeps today's default/meaning; clamp_limit reads page only | met | `config.py` `page_limit`/`max_candidates`; `clamp_limit(..., page_limit)` |
| 2 | Fan-out change requires rebuild; page cap never | met | `QUERY_ONLY_KEYS`; identity excludes `CA_PAGE_LIMIT`; runbook Rebuild? column |
| 3 | `CA_MAX_RESULTS` alone → build meaning; page → own default; runbook states upgrade | met | `_resolve_max_candidates`; runbook 259 paragraph |
| 4 | get_index_status names each key with scope | met | `page_limit`/`max_candidates` fields + separate `governs` |
| 5 | R4.2: page length ≠ order/content | met | page_limit query-only; indexer unread |
| 6 | Do not raise fan-out default | met | `DEFAULT_MAX_CANDIDATES = 50` |
| 7 | No new tool; status rename OK | met | no new tool; status fields renamed |
| 8 | AC1: indexer uses new fan-out key, not max_results | met | `indexer.py:617,:673` |
| 9 | AC2: defaults + independence | met | proving tests |
| 10 | AC3: CA_MAX_RESULTS=10 → fan-out 10 and page 50 | met | proving test |
| 11 | AC4: runbook which needs rebuild | met | runbook table |

**11 met / 0 not met / 0 can't tell**. Overall **CLEAN** (challenger only — REVIEWER OFF).

```
Ran at 7d550fb07c79f28991152343d45b139e4a739a1a
$ .venv/bin/python -m pytest tests/test_page_limit_max_candidates_split.py -q
.......                                                                  [100%]
7 passed in 0.03s
```

Reviewed at 7d550fb07c79f28991152343d45b139e4a739a1a

- **Gate 4 status:** cleared (challenger CLEAN; reviewer waived)


## Phase 5 — finalise

PR: https://github.com/cuongdinhngo/code-atlas/pull/341
Outward actions taken (handover-authorised): push feature branch · open PR.
Deferred: merge, tracker transition, force-push, deploy.

`scripts/gate.sh` → GATE GREEN (20 passed / 0 failed / 0 skipped).

### Learning loop / cost

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (n/a) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`
`LEDGER TOTAL: unmeasured · top cost driver: challenger (1) + main-loop`

No new lesson entry — `one-field-two-questions` was advisory recall only (already rejected for promotion; no third independent sighting recorded here).

