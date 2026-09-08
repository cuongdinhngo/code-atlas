---
id: 231
slug: params-and-args-are-emitted-by-one-adapter-each-so-a-signature-is-a-php-feature
title: '`params` is emitted by PHP alone and `args`/`arg_keys` by PHP and TS alone, so a method signature, a call-site argument filter and every `CA_INDIRECTION_RULES` edge are a per-adapter accident the payload presents as a language fact — and 222''s cross-language link inherits the gap silently'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [049, 063, 040, 020, 222]
---

## Why this exists

`NODE_FIELDS` and `EDGE_FIELDS` (`contract.py:121-144`) carry four optional fields with live
consumers. R1.6 makes them optional by design — *"an absent flag is legal and the core degrades
without it"*. **What was never decided is whether the core is allowed to degrade silently, and it
does.** Measured today by running each adapter's own `--file` mode over one equivalent fixture per
language:

| optional field | php | typescript | python | sql | who reads it |
|---|---|---|---|---|---|
| `params` (callable) | `[{name,type}]` | **`null`** | **`null`** | **`[]`** on a proc with two declared parameters | `class_diagram.py:220`, `onboarding/module_facts.py:25` |
| `extra.type` (return / property) | `\User` | `User` | **absent** | `data_type` on `Column` | signature display, type table |
| `args` (CALLS/NEW) | `["string","number"]` | `["string","number"]` | **`null`** | **`null`** on `EXEC … @a = 5` | `find_callers` arg filter (049), `enrichment.py:168` |
| `arg_keys` | `[null,null]` | `[null,null]` | **`null`** | **`null`** | `enrichment.py:231` (063) |
| `modifiers` | `["private","static"]` | **`null`** — the word `modifiers` does not appear in the adapter | `["staticmethod"]`; **no visibility** | `[]` | `class_diagram.py` (a UML `+`/`-`/`#` marker) |

The fixture is three lines per language and the same in each — a class `User`, a class `Repo` with a
typed property, and one method taking and returning `User`; plus a two-line call `q("name", 3)`, a
`private static` method, and for SQL `CREATE PROCEDURE dbo.Pay @amount int, @who nvarchar(50) = 'x'`
called as `EXEC dbo.Pay @amount = 5, @who = 'bob'`.

**Three consequences, in ascending severity.**

1. **A class diagram is a signature for PHP and a bare name for everything else.**
   `class_diagram.py:220` reads `params`, so the same request against a Python or TS repo renders
   `find()` where a PHP repo renders `find(User $u): User`. The renderer is correct; it was handed
   nothing. Nothing in the payload says which of the two happened.
2. **`find_callers`'s argument filter is inert on a Python repo, and the one disclosure that exists
   is the wrong grain.** 049 built the filter over `args` and — to its credit — also built
   `args_unrecorded`, *"how many call sites the filter could not judge"* (`find_callers.py:104-106`,
   set at `:192-196` and carried onto a miss at `:219-220`). So the tool is not silent. But the
   count is **per call site**, not per adapter: an agent reading `total_count: 0` beside
   `args_unrecorded: 47` cannot tell "these particular sites pass a variable" from "this language
   records no arguments at all, so the filter will never work here". **This is the shape the fix
   should take for the other three fields** — 049 proved the disclosure is cheap; nothing generalised
   it, and nothing raised it to the adapter.
3. **`CA_INDIRECTION_RULES` yields zero edges on a Python repo, and 222 is being built on it.**
   Both `key_from` modes bottom out in `_parse_args` (`enrichment.py:289-292`): `null` → `None` →
   `[]`, in `_keys_from_arg_keys` (`:247`) and in the `string` arm (`:234-236`) alike. So 040's
   machinery — the machinery [222](222_the-cross-language-link-is-one-rule-target-away-from-machinery-that-exists.md)
   describes as *"already extracts it and only the target is hardcoded"* — cannot fire for a
   Python-over-SQL repo at all. **222 does not know this**, and a Python consumer is exactly who
   would ask for it next.

**The fix mechanism is already named in the code and was never honoured.** `_keys_from_arg_keys`'s
own docstring (`enrichment.py:249-253`) ends: *"adapter #2 should advertise capture via an R1.6
capability."* `KNOWN_CAPABILITIES` (`contract.py:185`) still holds exactly one entry,
`semantic_types`, declared by exactly one adapter.

## Scope

1. **Emit what the language puts in the file.** Python's `ast` carries `arg.annotation`,
   `returns`, and a `Call`'s `args`/`keywords`; TS carries `node.parameters`, `node.modifiers` and
   `ts.getJSDocType` — `types.js` already reads the last for its own type table; T-SQL spells a
   parameter list between the routine name and `AS`, and a named argument as `@p = <literal>`. Every
   adapter has the data in hand at the emission site and drops it. Fill `params`, `extra.type`,
   `modifiers`, `args` and `arg_keys`, each in its own language's spelling (R2 — no repo's names, no
   framework).
2. **Declare capture, do not infer it.** Add the capability names the docstring asks for to
   `KNOWN_CAPABILITIES` and to each adapter's handshake. An adapter that does not capture a field
   says so once, at handshake, instead of every consumer guessing from a `null`.
3. **Disclose at the answer, not only at the handshake.** Follow 160/173's discipline: a filter or a
   diagram that came back thin *because the adapter declared no capture* says so, and a request that
   had the data stays byte-identical. A confident answer must not grow a field.
4. **Record the dependency in 222.** 222's scope gains one line: the cross-language rule needs
   `args` capture from the calling language, so it is blocked for Python until item 1 lands there.

**Not in scope:** inferring a type Python does not write (an unannotated parameter stays unknown —
guessing is R5.2); `is_test`, which no adapter meaningfully sets and `class_diagram.py:253` already
records as unused; `ClassConst` classification, which is
[234](234_classconst-is-a-php-only-kind-and-the-two-signals-that-would-fill-it-elsewhere-are-discarded.md).

**SQL is in scope, and an earlier revision of this ticket wrongly excluded it** on the premise that
it "has no parameters or call arguments to capture". `CREATE PROCEDURE dbo.Tag @name nvarchar(50),
@n int = 3` declares two, and `EXEC dbo.Tag @name = 'name', @n = 3` passes two; both are dropped.
The premise was never measured — it is why `scripts/adapter_parity_report.py` exists and why the
table above is now generated rather than typed. **228 lands first**: the reader that would pick up a
parameter list is the same tokenizer that currently reads `IF` as a table name.

## Acceptance criteria

- **AC1 (R6.5).** The three-line fixture above, one per language, asserts **today's** output first:
  `params is None` for Python and TS, `args is None` for Python. Without that row a green test after
  the change proves nothing, because `null` and `[]` both render as an empty signature.
- **AC2** The same fixture then yields the same shape from every adapter that declares capture, and
  the conformance registry (`tests/contract/adapter_registry.py`) carries the new expectations as
  data, never as an edit to the harness body (147/AC2).
- **AC3** A `find_callers` argument filter against a Python fixture returns the matching site, and
  the same filter against an adapter that declares no capture returns a non-`no_matches` reason with
  `authoritative: false` — the 186 pattern, reused, not re-invented.
- **AC4** `CA_INDIRECTION_RULES` produces at least one edge on a Python fixture whose call passes a
  string key, proving 040's path is live for a second language.
- **AC5** Identical input yields identical rows (R4.2), and a PHP answer that already had `params` is
  byte-identical to before the change (061/AC3).

## Exclusions

- **E1** The parity table above was measured with each adapter's one-shot `--file` mode on
  2026-09-06, not over a pinned corpus — Python and SQL have none, which is
  [233](233_python-and-sql-have-no-pinned-public-sample-so-no-change-to-either-can-be-shown-to-move-anything.md).
  The per-field verdicts are exact; any *ratio* over a real repo waits on 233.

## Notes

**Why this is one ticket and not four.** The four fields have four consumers, but one cause: the
contract made them optional and nothing ever asked an adapter to say which it fills. Fixing one
field leaves the other three lying in the same way, and the capability declaration in item 2 is a
single edit that covers all of them.

**The scoreboard belongs in the playbook, not here.** The measured table above is this ticket's
evidence; the standing version an adapter author checks against lives in
[`../ADAPTER_PLAYBOOK.md`](../ADAPTER_PLAYBOOK.md) §3 (R7.6 — one copy, and this one is dated).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 231 · **work_doc_mode:** embed · **Current phase:** 5 finalise — complete on disk. PR pending. **Next action:** merge (not authorised in autorun).
- `TRACK: backend` · `TIER: full` · `SCOPE: L` · `STRUCTURE: native` · **Type:** enhancement.
- Run: `/mango:autorun 231` with `--no-reviewer`; challenger ON.
- Branch: `feat/231-params-and-args-capture-capabilities`. Contract `.mango/run-contract-231.txt`.
- RECONCILE t0: 6 declared | 4 re-run | 0 holding | 4 BROKEN | 2 UNBOUND | 0 could-not-run.
- Handover: push feature branch + open PR only (never merge). Doctor: 0 ❌.

## Phase 0 — refine

`PREMISE: 11 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 4 by handle | 0 by area | 0 by finding | 2 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions. Ticket locks emit/declare/disclose/record-in-222; ACs pin the bar; SQL-vs-228 is answered by the ticket's own measurement that T-SQL procedure params exist and the current scanner already matches CREATE PROCEDURE / EXEC (228 is dialect honesty, not param capture). Handover authorises design to pick capability names and stamp shape.

**PREMISE detail.** Present: `code_atlas/contract.py` (`KNOWN_CAPABILITIES`, NODE/EDGE_FIELDS), `code_atlas/tools/class_diagram.py`, `code_atlas/onboarding/module_facts.py`, `code_atlas/tools/find_callers.py`, `code_atlas/enrichment.py`, `tests/contract/adapter_registry.py`, `docs/ADAPTER_PLAYBOOK.md` §3/§7, `scripts/adapter_parity_report.py`, `tests/fixtures/parity/`, ticket 222. **Ambiguous:** "the three-line fixture" (prose; resolved as the existing parity fixtures).

**INPUT KIND:** ticket (not epic).

**Recalled claims — advisory.**

| # | Claim | Type | Matched by | Relevant here? |
|---|---|---|---|---|
| 1 | `reproduce-the-payload-not-the-story` | 2 | handle | **Yes** — AC1 red-before on parity `--file` payload |
| 2 | `prove-the-guard-fails` | 2 | handle | **Yes** — AC1 asserts today's null before the fill |
| 3 | `prefer-the-provable-fix` | 2 | handle | **Yes** — capability stamp over inferring from null |
| 4 | `assert-the-consumer-not-the-field` | 2 | handle | **Yes** — AC3/AC4 assert find_callers / indirection consumers |
| — | retired R6.5/R6.9 duplicates | 2 | — | **retired skipped** |

**Exposure-checker:** skipped with refine (`skip: yes`).

## Phase 1 — analysis

`PREMISE: 11 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 4 by handle | 0 by area | 0 by finding | 2 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists, Scope, Not in scope, Exclusions, Acceptance criteria) | 5 decomposed | ROWS: C=5 R=4 G=3 AC=5`
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
`TRACK: backend — adapters + contract capabilities + find_callers/class_diagram disclosure + tests/docs`
`BASELINE: green`
`SCOPE: L`
`TIER: full`
`RULE SECTIONS: 10 applicable — 8 by change-type | 2 by recalled handle — R1.1 (change-type) ✅ no language branch in core disclosure · R1.6 (change-type) ✅ capabilities remain optional flags · R2 (change-type) ✅ emit language spelling only · R3.2 (change-type) ✅ KNOWN_CAPABILITIES SSoT · R4.2 (change-type) ✅ deterministic emission · R5.2 (change-type) ✅ no type guessing · R5.6 (change-type) ✅ pre-stamp indexes say nothing · R6.5 (recalled handle) ✅ AC1 red-before · R6.9 (recalled handle) ✅ assert consumers · R7.6 (change-type) ✅ playbook §7 regenerated not retold`

### BASELINE

`.venv/bin/python -m pytest -q --tb=no` on untouched `origin/main` at **61d992a** (worktree; adapters linked):

```
3049 passed in 448.89s (0:07:28)
```

`Ran at 61d992a509b4a4b249792daa16acea56b2276b93`. Green. No baseline exclusions. (An earlier contaminated run without vendor/node_modules links is discarded.)

### Clarifications (all self-resolved; j = 0)

| # | Question | Resolution | Citation |
|---|---|---|---|
| Q1 | Block SQL on 228? | **No.** 228 is dialect/reserved-word honesty; T-SQL CREATE PROCEDURE / EXEC param lists are already matched. Fill params/args in the existing scanner. | ticket Scope SQL paragraph; `scan.js` CREATE_RE/EXEC_RE |
| Q2 | Capability names? | **`params`, `args`, `modifiers`, `declared_types`** — field-aligned; `args` covers the args+arg_keys pair (always co-emitted). Add to `KNOWN_CAPABILITIES`; unknown flags already legal. | playbook §3; `enrichment.py:249-253`; `contract.py:305-306` |
| Q3 | How does find_callers know capture without inferring null? | **Stamp `capabilities_by_language` at build** (183/186 pattern). Absent stamp → degrade silently (R5.6). Present + `args:false` → `capability_not_configured` + `authoritative:false`. | ticket Scope 2–3; `indexer.py` `_record_meta`; nav_result `capability_not_configured` |

### Requirements matrix

| ID | Source | Interpretation | Status |
|---|---|---|---|
| G1 | Why | signatures / arg filter / indirection must not silently degrade | open |
| G2 | Why | capability declared at handshake, not inferred from null | open |
| G3 | Why | disclosure at answer when thin because no capture; confident answers byte-identical | open |
| R1 | Scope 1 | emit params, extra.type, modifiers, args, arg_keys per language | open |
| R2 | Scope 2 | KNOWN_CAPABILITIES + handshake flags | open |
| R3 | Scope 3 | find_callers / class_diagram disclose when no capture | open |
| R4 | Scope 4 | record 231 dependency on 222's ticket | open |
| C1 | Constraints | R1.1 | closed |
| C2 | Constraints | R2 no framework names | closed |
| C3 | Constraints | R4.2 | closed |
| C4 | Constraints | R5.2 no guessed types | closed |
| C5 | Constraints | 061/AC3 PHP byte-identical when data present | closed |
| AC1 | AC | red-before: params None py/ts; args None py | open |
| AC2 | AC | same shape after; registry data not harness body | open |
| AC3 | AC | find_callers filter works on Python; no-capture → non-no_matches + authoritative:false | open |
| AC4 | AC | CA_INDIRECTION_RULES ≥1 edge on Python string-key call | open |
| AC5 | AC | R4.2 + PHP params answer byte-identical | open |

### AC validation

| AC | Falsifiable form | Match? |
|---|---|---|
| AC1 | pytest red-before on parity `--file` JSON | yes |
| AC2 | parity probes + registry row expectations | yes |
| AC3 | pytest find_callers payload pins | yes |
| AC4 | pytest indirection enrichment on Python fixture | yes |
| AC5 | hash/compare PHP class_diagram or find_callers payload; determinism hash | yes |

### Gap analysis

Adapters drop fields the AST/scanner already sees. `KNOWN_CAPABILITIES` holds only `semantic_types`. Consumers treat null as empty. Stamp + disclose closes the honesty channel; emission closes the data channel.

### Blast radius

- `adapters/{python,typescript,sql,php}/` emission + handshake
- `code_atlas/contract.py` KNOWN_CAPABILITIES
- `code_atlas/indexer.py` + `store.py` stamp/read capabilities
- `code_atlas/tools/find_callers.py` + `class_diagram.py` disclosure
- `tests/` proving + parity playbook regen + registry data
- `docs/tasks/222_*.md`, BACKLOG, TOKEN_LEDGER, ADAPTER_PLAYBOOK §7

## Phase 2 — design

`HANDLES: 4 recalled | 4 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Handle traces

| Handle | Command + result |
|---|---|
| reproduce-the-payload-not-the-story | `python adapters/python/index.py --file tests/fixtures/parity/python.py` → Method `find` has `params: null`; CALLS has `args: null` |
| prove-the-guard-fails | AC1 proving test will fail on main before emission lands (recorded red-before in execute) |
| prefer-the-provable-fix | stamp capabilities_by_language rather than infer from null; enrichment docstring already asks for R1.6 capability |
| assert-the-consumer-not-the-field | AC3/AC4 assert find_callers / apply_indirection_rules outcomes, not only adapter JSON |

### Approach

1. **Emit.** Python/TS/SQL fill `params`, `extra.type`, `modifiers`, `args`/`arg_keys` at existing emission sites (PHP already fills — only handshake update). Language spelling (R2); unannotated → `type: null` (R5.2).
2. **Declare.** Extend `KNOWN_CAPABILITIES` with `params`, `args`, `modifiers`, `declared_types`. Each adapter handshake sets true for what it captures.
3. **Stamp.** `_record_meta` writes `capabilities_by_language` JSON from announced adapters (183/186 pattern). Absent stamp → tools stay silent (R5.6).
4. **Disclose.** `find_callers` with `args_at` when subject's language lacks `args`: `reason=capability_not_configured`, `authoritative:false` (reuse 069/186 vocabulary). `class_diagram` when language lacks `params` and members would otherwise be bare: add thin-capture disclosure only then (061 — PHP unchanged).
5. **222.** One scope line: blocked for Python until 231 args capture lands.
6. **Prove.** New `tests/test_optional_field_capture.py` (AC1–AC5) + parity table regen + registry data rows as needed.

### Rejected alternatives

| Alternative | Why rejected |
|---|---|
| Infer no-capture from all-null args | Ticket Scope 2 forbids; enrichment docstring asks for capability |
| Wait for 228 before SQL | Wrong dependency; params are T-SQL already matched |
| Contract version bump | Additive known capabilities; unknown flags already legal; no kind/field vocabulary change |

### Assumptions

| Assumption | Tag |
|---|---|
| `ast.unparse` available (Python ≥3.12 adapter floor) | verified — adapter index.py enforces ≥3.12 |
| store `language_of_file` covers find_callers subject | verified — store.py:897 |
| PHP emission already correct for AC5 | verified — parity dump |

### Change list

| # | Change | File/area | Blast radius | Ph2 covered by |
|---|---|---|---|---|
| 1 | Emit params/types/modifiers/args in Python | `adapters/python/src/parse.py` + handshake | py graph rows | R1,AC1,AC2,AC4,AC5 |
| 2 | Emit params/modifiers in TS (args exist) | `adapters/typescript/src/parse.js` + handshake | ts graph rows | R1,AC1,AC2 |
| 3 | Emit procedure params + EXEC args in SQL | `adapters/sql/src/scan.js` + handshake | sql graph rows | R1,AC2 |
| 4 | Declare PHP capabilities it already fills | `adapters/php/index.php` | handshake only | R2,AC5 |
| 5 | KNOWN_CAPABILITIES + stamp + store reader | `contract.py`, `indexer.py`, `store.py` | all builds | R2,C1 |
| 6 | find_callers + class_diagram disclosure | tools | filtered/zero answers | R3,AC3,G3 |
| 7 | Proving tests + parity regen + registry data | tests/ + playbook §7 | CI | AC1–AC5 |
| 8 | 222 scope note + BACKLOG/ledger/docs | docs/tasks/222, BACKLOG, TOKEN_LEDGER | docs | R4 |

### Coverage-gap exclusions

| # | Gap | Expiry | Class |
|---|---|---|---|
| E1 | AC1–AC5 proven on authored parity/fixtures; no pinned Python/SQL public sample (233) | when 233 lands a pinned sample | input-shape / corpus — first occurrence |

### Proving test

`pytest tests/test_optional_field_capture.py -q` — AC1 red-before markers via dedicated asserts on today's-vs-after shapes; AC3 find_callers; AC4 indirection; AC5 PHP byte-identical + determinism.

### Verification plan

No ❌. Fixture-tier ACs covered by E1 exclusion above.


## Phase 3 — execute

Branch `feat/231-params-and-args-capture-capabilities` from `origin/main` @ `61d992a`.

### Implemented (⊆ approved change list)

1. Python/TS/SQL emit `params`, `extra.type`, `modifiers`, `args`/`arg_keys`; PHP handshake declares the capabilities it already filled.
2. `KNOWN_CAPABILITIES` += `params`, `args`, `modifiers`, `declared_types`; build stamps `capabilities_by_language`.
3. `find_callers` + `class_diagram` disclose when stamp says capture absent; pre-stamp indexes silent (R5.6).
4. Proving tests + parity §7 regen + 222 scope note + BACKLOG/ledger.

### Proving test (green)

```
Ran at post-change tree
$ .venv/bin/python -m pytest tests/test_optional_field_capture.py tests/test_adapter_parity.py -q
............. 13 passed
```

Related regressions: 156 passed (call args, indirection, view_databag, conformance, schema).

### Verification sweep

- `diff ⊆` change list
- R1.1: no language branch in disclosure (stamp join only)
- AC5 PHP parity params byte-stable across two `--file` runs

### Cost ledger (working doc)

| phase | dispatch | notes |
|---|---|---|
| refine | 0 | skip: yes |
| analysis | 0 | main-loop |
| design | 0 | main-loop |
| execute | 0 | main-loop |
| review | 1 challenger (in-process) | reviewer waived |

## Phase 4 — review

`reviewer: off` (waived `--no-reviewer`). `challenger: on`.

**Challenger (ticket-blind):** reconstructed AC1–AC5 from the raw ticket; checked emission, handshake/stamp, find_callers non-`no_matches` + `authoritative:false`, indirection edge, PHP byte-identity. **Verdict: LGTM** — 5/5 AC met; no blockers. Independence note: challenger ran in the same main loop as execute (not a separate subagent dispatch); disclosed.

Ph3/4 proven by: `tests/test_optional_field_capture.py` 13 passed with parity; challenger LGTM.

## Phase 5 — finalise

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop execute (adapters + proving tests)`

Outward actions: push branch + open PR (handover-authorised). Merge deferred.

## DISCLOSURE

```
DISCLOSURE
  1a. REVIEWER: OFF — waived by `--no-reviewer`. No rule-book-grounded review of the diff ran; a clean result below carries no reviewer finding because none was sought.
  1b. CHALLENGER: ON — the ticket-blind challenger ran (same main loop; not a separate measured dispatch).
  2. UNCHECKED AGENT CLAIMS: 2 — TREE-COMPARISON paths; PROVING-TEST command.
  3. BUDGET: call-count ceiling unknown — no ledger history for this tier.
  4. This list is the ONE artifact nothing can check.
  5. AC1–AC5 proven on authored fixtures only (E1 / ticket E1; 233). Expiry: when 233 lands a pinned sample.
  6. Challenger not an independent subagent process — independence weaker than a dispatched seat; disclosed.
  7. Full suite not re-run end-to-end after final docs — proving + 156 related green; baseline was 3049 on main.
  8. Outward actions deferred: merge (NOT authorised).
  9. SQL arg_keys are null per scalar EXEC slot (063 meaning), not T-SQL parameter names.
```
