---
id: 253
slug: a-zero-overlap-guess-gets-no-route
title: 'A guessed name sharing no substring with any declared symbol falls through both 245 and 249 and returns a bare `no_matches`, so "this codebase has no such concept" and "you guessed the name wrong" are byte-identical answers — and the field produced both, indistinguishably, in the same session'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [245, 249, 065]
---

## Why this exists (field retro — the anchor repo, 2026-09-11, round 18)

The consuming agent guessed three symbol names from domain vocabulary and got three clean misses:

> **Name-guess misses** (`uploadMemberPhoto`, `savePhoto`, `newMemberTab`) returned `no_matches`.
> Correct — those symbols don't exist under those names (the upload is
> `UploadFiles`/`UploadPhotoController`; the tab is procedural routing). Not a tool failure, but a
> reminder that `search_symbol` only knows declared symbols, so **a guessed name that isn't a real
> symbol tells you nothing about whether the concept exists.**

Its own tally counts these four times as "honest miss, zero signal", and its third suggestion asks
for the nearest declared symbols so it could "distinguish 'the concept doesn't exist' from 'you
guessed the name wrong'."

The session settled it both ways and the payload could not tell them apart. Photo upload **exists**,
under `UploadFiles` / `UploadPhotoController` — a name the reader eventually found through an
unrelated query. `newMemberTab` **does not exist as a symbol at all**; it is a routing action
string in procedural dispatch, and no name would have found it. Two opposite facts, one payload.

## Root cause

245 and 249 built the near-miss route, and both require the guess to *overlap* the real name.
`search_symbol` attaches a route on exactly these conditions
(`code_atlas/tools/search_symbol.py:344-350`, `:356-360`):

```python
def _needs_narrowing_route(hits):
    if hits.reason in (REASON_SUBSTRING_MATCH, REASON_SEPARATOR_NORMALISED):
        return True
    return hits.truncated and hits.total_count > len(hits.results)
```

- `substring_match` (245) needs the query to be a trigram/substring near-miss of something declared —
  there must be a candidate set to attach to.
- `separator_normalised` (249) needs `contract.member_separator_variant(qname)` to be non-`None` and
  to hit **uniquely** — a spelling repair, not a search.
- the truncation arm needs hits.

A name invented from the domain satisfies none of them: `total_count` is 0, `truncated` is `False`,
there is no separator variant. The answer is a bare `no_matches` with no `try_instead` — the one miss
shape on the surface with no route, which is precisely the gap 245 was filed to close, one step
further out. 249 already found the first such step (a separator spelling scores 0 exact and 0
substring, so 245's route had no candidate set); this is the same discovery for a guess that shares
no characters at all.

## Scope

A candidate route for a zero-overlap miss: when a query matches nothing, decompose it into name
tokens (`uploadMemberPhoto` → `upload` / `member` / `photo`) and offer declared symbols matching
the tokens as **explicitly labelled candidates**.

What this must establish, and the reason it is worth a ticket rather than a nicety: on the evidence
above, a reader can tell the two cases apart. `upload` + `photo` reaches `UploadPhotoController`;
`newMemberTab` reaches nothing, and a route that returns nothing *after looking* is a different and
much stronger answer than one that never looked.

## Constraints

- **R5.6 — candidates are not hits.** They never enter `results`, never count in `total_count`, and
  `reason` is never `ok`. The 249 precedent (`separator_normalised`, never `ok`) is the model.
- **R1.1 — no language branch.** camelCase / snake_case / PascalCase are naming conventions, not
  language facts; the splitter is keyed by the convention, and lives in the core without naming a
  language (R2: the standard, never a sample's vocabulary).
- **R4.2** — deterministic candidate set and order for a given index and query.
- **Bounded** — a fixed small `k`; a token like `get` must not drag the whole index back.
- **061** — nothing is added to an answer that has hits; this rides the empty-answer path only.
- **Not a text search.** This ranges over *declared symbol names*, not file contents. Literal strings
  and default parameter values are a different gap (BACKLOG follow-up), deliberately out of scope.

## Acceptance criteria

- **AC1** A zero-overlap guess whose tokens match declared symbols returns labelled candidates plus a
  `reason` distinct from a genuine zero. The proving pair is this session's: a query on the token
  shape of `uploadMemberPhoto` reaches the upload controller.
- **AC2** A guess whose tokens match nothing returns an empty answer that **says the candidate search
  ran and found none**, so AC1's case and this one are distinguishable — the whole point of the
  ticket.
- **AC3** Candidates are excluded from `results` and `total_count`; an existing `no_matches` consumer
  reading those two fields sees no change.
- **AC4** Deterministic across runs on a fixed index; bounded by a stated `k` on the widest token.
- **AC5** Every answer that has hits today is byte-identical (022 AC3).

## References

- `code_atlas/tools/search_symbol.py:344-360` — the three route conditions and `_needs_narrowing_route`.
- `code_atlas/contract.py` — `member_separator_variant` (249's repair), and where a name splitter
  would sit to stay language-agnostic.
- [245](245_the-truncated-substring-answer-is-the-one-search-shape-with-no-route.md) — the route this
  extends; its design note that *"the route must MAKE PROGRESS"* is the standard applied here.
- [249](249_a-miss-whose-only-defect-is-the-separator-spelling-gets-no-route.md) — the first miss shape
  found outside 245's reach; this is the second, and the pair suggests the rule is *every* miss needs
  a route, not every *near* miss.
- [065](065_empty-answer-cannot-explain-itself.md) — the rule the bare `no_matches` still breaks.


<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **Ticket:** 253
- **Type:** bug
- **Repo(s):** app
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green
- **work_doc_mode:** embed
- **working-doc path:** docs/tasks/253_a-zero-overlap-guess-gets-no-route.md
- **branch:** feat/253-a-zero-overlap-guess-gets-no-route
- **plugin:** mango 1.16.1 @ /home/you/.claude/plugins/cache/mango-plugins/mango/1.16.1 (candidates: 10)
- **reviewer:** off · **challenger:** on
- **Current phase:** finalise
- **autorun:** yes (`--no-reviewer`)

---

## Phase 0 — Refine

`PREMISE: 5 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 4 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions

**PREMISE detail.** Present: `code_atlas/tools/search_symbol.py` (`_needs_narrowing_route`), `code_atlas/contract.py` (`member_separator_variant`), tickets 245/249/065. **Ambiguous:** field names `uploadMemberPhoto` / `UploadPhotoController` — private-field evidence; ACs pin the *shape*, not the sample names (R2).

**INPUT KIND:** ticket (not epic).

**ASSUMED under handover (want-bar decisions — recorded in DISCLOSURE):**
1. Bound `k = TOKEN_CANDIDATE_K = 5` (ticket: fixed small k).
2. Reason `token_candidates` for both nonempty and empty candidate lists (AC1/AC2 distinguishable by `candidates` emptiness; both ≠ bare `no_matches`).
3. Significant tokens: length ≥ 4 and not in a small stop set (`get`/`set`/`new`/…).
4. Route tool = `search_symbol` (progress = retry with a declared qname), not `file_outline`.

**Recalled claims (ADVISORY).**

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | `try-instead-tool-name` | 2 | handle | Yes — two-register; new HINT siblings |
| 2 | `route-must-answer` | 2 | handle | Yes — every miss needs a route |
| 3 | `prove-the-guard-fails` | 2 | handle | Yes — red-before bare no_matches |
| 4 | `do-not-attest-past-the-payloads-resolution` | 2 | handle | Yes — R5.6 candidates ≠ hits |

**Exposure-checker:** skipped (refine skip: yes).

---

## Requirements matrix

`SECTIONS: 6 found (Why this exists · Root cause · Scope · Constraints · Acceptance criteria · References) | 6 decomposed | ROWS: C=6 R=3 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Why/Root | zero-overlap miss is bare no_matches | 245/249 need overlap or separator repair | search_symbol:344-360 | D1 | proving AC1/AC2 | ⬜ |
| C1 | Constraints | R5.6 candidates not hits | never in results/total_count; reason ≠ ok | ticket | D1 | AC3 | ⬜ |
| C2 | Constraints | R1.1 no language branch | convention splitter in contract | ticket | D1 | name_tokens + R1.1 suite | ⬜ |
| C3 | Constraints | R4.2 deterministic | fixed order + k | ticket | D1 | AC4 | ⬜ |
| C4 | Constraints | Bounded k; get must not flood | TOKEN_CANDIDATE_K + stop/min-len | ticket | D1 | AC4 + unit | ⬜ |
| C5 | Constraints | 061 — only empty-answer path | token arm only on no_matches offset0 | ticket | D1 | AC5 | ⬜ |
| C6 | Constraints | Not a text search | declared symbol names only | ticket | D1 | File kind dropped | ⬜ |
| R1 | Scope | Decompose guess into tokens | name_tokens | ticket Scope | D1 | unit | ⬜ |
| R2 | Scope | Offer labelled candidates | candidates[] side field | ticket Scope | D1 | AC1 | ⬜ |
| R3 | Scope | Empty-after-look ≠ never-looked | same reason, empty candidates + hint | ticket Scope | D1 | AC2 | ⬜ |
| AC1 | AC | tokens match → labelled candidates + distinct reason | uploadMemberPhoto shape | | D1,D2 | proving | ⬜ |
| AC2 | AC | tokens match nothing → says search ran | empty candidates | | D1,D2 | proving | ⬜ |
| AC3 | AC | candidates excluded from results/total_count | | | D1 | proving | ⬜ |
| AC4 | AC | deterministic; bounded k | | | D1 | proving | ⬜ |
| AC5 | AC | hits today byte-identical | | | D1 | proving | ⬜ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------|
| AC1 | labelled candidates + distinct reason | token arm after empty primary | Y | greppable reason + candidates | — |
| AC2 | search ran, found none | empty candidates + token_candidates | Y | candidates==[] + reason | — |
| AC3 | not in results/total_count | side field only | Y | assert | — |
| AC4 | deterministic + k | sorted score + TOKEN_CANDIDATE_K | Y | equality + len | — |
| AC5 | hits unchanged | token arm only on no_matches | Y | no candidates key on ok | — |

## Inventory (universal "all/every/no")

- **Denominator / total N:** 0 — shape pins, no closed inventory.
- Numbered list: (none)

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

---

## Phase 1 — Analysis

- Root cause (bug, `logic`): `_needs_narrowing_route` fires only on substring/separator/truncation; a domain guess with total_count=0 never attaches a route (`search_symbol.py` empty arm → bare `no_matches`).
- Handler / blast radius: `_search_one` / `_single_payload` / `_batch_answer`; `contract.name_tokens`; `nav_result` reason + HINT pins; 245/249 tests that assumed bare no_matches on zero-overlap empties.
- `TRACK: backend — 0/0 touched files under UI paths`
- `SCOPE: S`
- `TIER: full`

`RULE SECTIONS: 8 applicable — 7 by change-type | 1 by recalled handle — R1.1 (change-type) ✅ convention splitter, no language name · R2 (change-type) ✅ no sample vocabulary in core · R4.2 (change-type) ✅ deterministic candidate order · R5.2 (change-type) ✅ reason ≠ ok · R5.6 (recalled handle) ✅ candidates not hits · R5.4 (change-type) ✅ route makes progress · R6.1 (change-type) ✅ proving fixture · R7.5 (change-type) ✅ comments ≤3 lines`

### BASELINE

Related suite on untouched checkout:

```
Ran at 8303edb00205ecd15ae88686cc14b263dd2fe4da
$ .venv/bin/python -m pytest tests/test_search_symbol_truncated_substring_route.py tests/test_separator_spelling_near_miss.py tests/test_nav_reason_codes.py tests/test_empty_answer_cannot_explain_itself.py -q --tb=no
25 passed in 2.67s
```

`BASELINE: green` for the change-adjacent suite. No baseline exclusions.

- Self-audit: sections 6=6; AC falsifiable; j=0; RULE SECTIONS named; TRACK/TIER/SCOPE declared.
- **Gate 1 status:** cleared (autorun closes on artifacts) ✋

---

## Phase 2 — Design

- **Approach.** Add `contract.name_tokens` (camel/Pascal/snake/kebab; min length 4; stop set). On empty `no_matches` at `offset==0` after the 249 separator arm, if any significant tokens remain, search each token over declared symbols, rank by token-overlap count, take top `TOKEN_CANDIDATE_K=5`, return `reason=token_candidates` with `candidates` side field (never in `results`/`total_count`). Empty candidate list keeps the same reason and a distinct NONE hint so AC1≠AC2≠bare no_matches. Attach `try_instead=search_symbol`.

- **Rejected alternatives.**
  1. Reuse `substring_match` — rejected: no substring candidate set exists.
  2. Put candidates in `results` — rejected: R5.6 / AC3.
  3. Text search over file bodies — rejected: ticket out of scope.
  4. Language-specific tokenisers — rejected: R1.1.

**Assumptions**

| Assumption | verified / novel-untested | If novel-untested → spike / proving test |
|------------|---------------------------|------------------------------------------|
| FTS token search finds substrings of declared names for tokens ≥3 | verified | store.search_nodes trigram path + proving seed |
| Stopping short tokens prevents `get` flood | verified | name_tokens unit + AC4 |

**Smallest change-list**

| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|--------|-----------|--------------|----------------|-----|
| D1 | name_tokens + token arm + reason/hints | `contract.py`, `search_symbol.py`, `nav_result.py` | NAV_REASONS pins; 245/249 empty-miss tests | G1,C1–C6,R1–R3,AC1–AC5 | 3/3 |
| D2 | Proving tests + pin updates | `tests/test_zero_overlap_token_candidates.py` + pin/collateral tests | none beyond named | AC1–AC5 | — |

`HANDLES: 4 recalled | 4 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| Handle | Answer | Command + result (trimmed) |
|--------|--------|----------------------------|
| try-instead-tool-name | traced | `rg -n 'TRY_INSTEAD_HINT_TOKEN' code_atlas/tools/nav_result.py` → HINT_TOKEN_CANDIDATES + _NONE siblings |
| route-must-answer | traced | `rg -n 'REASON_TOKEN_CANDIDATES' code_atlas/tools/search_symbol.py` → attach_try_instead search_symbol |
| prove-the-guard-fails | traced | proving test seeds UploadPhotoController; query uploadMemberPhoto |
| do-not-attest-past-the-payloads-resolution | traced | `rg -n 'candidates' code_atlas/tools/search_symbol.py` → side field; results stay [] |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Verification plan**

| AC | Proof layer | Named command / assertion | ❌? |
|----|-------------|---------------------------|-----|
| AC1 | unit | proving test uploadMemberPhoto → token_candidates | — |
| AC2 | unit | nonsense tokens → empty candidates | — |
| AC3 | unit | results=[] total_count=0 | — |
| AC4 | unit | equality + len≤k | — |
| AC5 | unit | exact hit has no candidates key | — |

**Proving test (named, runnable):**
`.venv/bin/python -m pytest tests/test_zero_overlap_token_candidates.py::test_zero_overlap_guess_returns_labelled_token_candidates -q`

- **Gate 2 status:** cleared (autorun closes on artifacts) ✋

---

## Phase 3 — Execute

**Branch:** `feat/253-a-zero-overlap-guess-gets-no-route`

**Implemented (approved list only):**
- D1: `contract.name_tokens` / `TOKEN_CANDIDATE_K`; search token arm → `REASON_TOKEN_CANDIDATES` + candidates + HINT pair; NAV_REASONS pin.
- D2: `tests/test_zero_overlap_token_candidates.py` + collateral pin/route tests.

**Verification sweep**

```
diff ⊆ approved list: code_atlas/contract.py, code_atlas/tools/search_symbol.py, code_atlas/tools/nav_result.py, tests/test_zero_overlap_token_candidates.py, tests/test_nav_reason_codes.py, tests/test_separator_spelling_near_miss.py, tests/test_empty_answer_cannot_explain_itself.py, tests/test_relation_unmodelled_for_language.py, tests/test_search_symbol_truncated_substring_route.py, docs/tasks/253_*.md, docs/BACKLOG.md, docs/TOKEN_LEDGER.md, docs/LESSONS.md
Ran at 462c02571200de6dc14be9b4d8c99769ec4de563
$ .venv/bin/python -m pytest tests/test_zero_overlap_token_candidates.py -q --tb=line
6 passed in 0.61s
```

**Design-conformance self-check:** matches D1–D2; no language branch; candidates not in results; hits unchanged.

- **Gate 3 status:** cleared (autorun) ✋

---

## Phase 4 — Review

**REVIEWER: OFF (--no-reviewer)** — waived; no rule-book-grounded review ran.
**CHALLENGER: ON** — ticket-blind, 1 dispatch.

Challenger reconstructed 7 requirements from the raw ticket; **7 met / 0 not met / 0 can't tell**. Overall **CLEAN** (challenger only — REVIEWER OFF). Mild notes: empty tokenisation still bare no_matches; field newMemberTab is not the AC2 proving query (stop/min-len).

Proving evidence on reviewed tree:
```
Ran at 532c6e68ca2ae1d224e00608f1b543a9d1b35dbc
$ .venv/bin/python -m pytest tests/test_zero_overlap_token_candidates.py -q --tb=line
6 passed in 0.63s
```

Reviewed at 532c6e68ca2ae1d224e00608f1b543a9d1b35dbc

- **Gate 4 status:** cleared (challenger CLEAN; reviewer waived)

---

## Phase 5 — Finalise

Durable lesson: none beyond the ticket ACs — recalled handles already cover the route/advice pattern; token_candidates is the ticket vocabulary.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (n/a) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`
`LEDGER TOTAL: unmeasured · top cost driver: challenger (1) + main-loop`

### Token usage (working doc)

| Phase | Tokens |
|---|---|
| autorun main-loop | unmeasured (host surfaces no usage block) |
| challenger ×1 | unmeasured |
| reviewer | waived (--no-reviewer) |

### Outward actions
1. push feature branch — authorised by handover
2. open PR — authorised by handover
3. merge — authorised by the maintainer; merged 2026-09-12 — `67e7e42` ([#330](https://github.com/cuongdinhngo/code-atlas/pull/330)).
