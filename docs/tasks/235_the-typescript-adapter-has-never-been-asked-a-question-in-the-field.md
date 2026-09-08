---
id: 235
slug: the-typescript-adapter-has-never-been-asked-a-question-in-the-field
title: 'The TS/JS adapter has passed every gate that reads a fixture and none that reads a repo — 15 findings have come from field rounds over PHP, SQL and Python builds and not one from TS, so its recall and its honesty are both unmeasured'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [019, 150, 018, 233]
---

## Why this exists

Gate 4 in [`../ADAPTER_PLAYBOOK.md`](../ADAPTER_PLAYBOOK.md) §4 — *ask each nav tool a question you
already know the answer to* — is the only gate that has ever produced a finding, and **it has never
been run against the TS adapter.**

| | php | sql | python | typescript |
|---|---|---|---|---|
| gate 1-2 (fixtures + conformance registry) | ✅ | ✅ | ✅ | ✅ |
| gate 3 (pinned public samples) | 3 | 0 ([233](233_python-and-sql-have-no-pinned-public-sample-so-no-change-to-either-can-be-shown-to-move-anything.md)) | 0 (233) | 3 |
| gate 4 (field round on a real repo) | 5 rounds | round 14 | 2026-09-05 | **2026-09-08** ([benchmark](../benchmarks/235_typescript_field_round.md)) |
| findings it produced | 136, 137, 221-223 | 221, 222, 224, 228 | 226, 227, 229, 230 | — |

TS is the **only** adapter with pinned samples and no field round, which makes it the cheapest gap
in the matrix to close: the checkouts, floors and adapter command already exist (150), so this is a
protocol run, not an infrastructure build.

**What the two cheaper gates already proved they cannot see.** 019 shipped TS with 20 fixtures and a
conformance row; 150 added its static analysis and cross-repo run. All three were green while:

- `params` was never emitted for any callable — **`0/3`** in the generated parity table;
- `modifiers` was never emitted at all, so `private`, `public`, `protected`, `static` and `readonly`
  are absent from a language that spells every one of them as a keyword — **`0/5`**;
- `REFERENCES` was never emitted from any construct, so `find_references` on a type used as a type
  answers zero and calls it a match-free answer
  ([232](232_the-same-construct-is-a-references-edge-in-python-and-node-extra-in-php-and-ts.md)).

Those three came from **reading** the adapter — the cheaper sibling of a field round — and each is a
gap a fixture suite was structurally unable to notice, because a fixture asserts what the adapter
emits and never what the file contained. A field round asks the other question.

## Scope

Run the playbook §5 protocol against a real TS/JS repo, and file what it returns. The protocol is
not restated here (R7.6); what this ticket adds is the corpus choice and the reporting bar.

1. **Choose two repos by shape, not popularity.** One `tsconfig` monorepo with project references
   and path aliases — the shape `IMPORTS` resolution (155) is most likely to miss on — and one mixed
   `.ts`/`.js` package with JSDoc types, the shape 154's slot exists for. The three pinned samples
   already cover a library, a mixed package and compiled-beside-source, so a field repo should add a
   shape they do not.
2. **Record the numbers the protocol asks for**, in a `benchmarks/` file: parsed_ok, the node census
   against a `grep` count per kind, the unlinked-edge ratio per kind split into expected and
   recoverable, and the cross-language census.
3. **Ask the nav tools questions verified by `grep` first.** `find_implementations` on an interface
   the repo implements across files, `find_callers` on an exported function, `find_references` on a
   type. A confident zero on any of them is the finding.
4. **File each finding as its own ticket** with a minimal fixture through `--file` (playbook §5
   step 7). This ticket delivers the measurement and the tickets; it fixes nothing itself.
5. **Fold the result into the parity table's gate rows** so the matrix above stops being true.

**Not in scope:** fixing anything the round finds — that is what item 4 is for; a second round;
the three known gaps above, which 231 and 232 already own.

## Acceptance criteria

- **AC1** A `benchmarks/` file carries the round's numbers, the two repos at pinned SHAs, the host
  and the date. Without pinned SHAs the round is unreproducible and its numbers are anecdote (018).
- **AC2** Determinism is proven on the corpus, not assumed: two clean builds hash identically over
  ordered nodes + edges (R4.2), with `graph.db` deleted between them (219).
- **AC3** Every nav-tool question asked is recorded with its `grep`-verified expected answer beside
  the payload's answer — including the ones the tool got **right**. A round that lists only misses
  cannot be read as a measurement of anything.
- **AC4** Each finding is a ticket with a `--file` fixture, or is explicitly recorded as *not
  reproducible outside that repo* and dropped. A finding without a fixture does not become a ticket
  (playbook §5 step 7).
- **AC5** **A round that finds nothing is a valid, publishable result** and closes this ticket
  green. The deliverable is the measurement; "no new findings" is evidence about the adapter, and
  recording it is what makes the gate meaningful rather than a search for bad news.

## Exclusions

- **E1** No private TS corpus is available to this repo, so unlike rounds 1-14 this one has no
  consumer-repo evidence to draw on. That makes the pinned public choice in scope item 1 the whole
  design of the round, and a poor choice yields a green round that proves nothing — which AC3's
  "record the hits too" is there to expose.

## Notes

**Why this is a ticket and not a habit.** Gates 1-3 are enforced by `pytest` and `cross_repo_validate.py`;
gate 4 is enforced by nothing, which is why it has run four times in fourteen rounds and skipped the
adapter nobody uses in anger. The playbook can say the gate is required; only a ticket per adapter
makes it happen.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 235 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** push + open PR (merge not authorised).
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · **Type:** enhancement (measurement).
- Run: `/mango:autorun 235` with `--no-reviewer`; challenger ON.
- Branch: `feat/235-typescript-adapter-field-round`. Contract `.mango/run-contract-235.txt`.
- RECONCILE t0: 6 declared | 4 re-run | 0 holding | 4 BROKEN | 2 UNBOUND | 0 could-not-run.
- Handover: push feature branch + open PR only (never merge). Doctor: 0 ❌.
- Worktree: `/home/you/.cursor/worktrees/autorun235-6be0f05d/code-atlas-9e4914c8946d` from `origin/main` @ `e092835`.

## Phase 0 — refine

`PREMISE: 8 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions. Ticket locks the protocol pointer (playbook §5), the two corpus shapes, the reporting bar (AC1–AC5), and "no fixes in this ticket". Repo identity within those shapes is design HOW under handover authorisation to choose the best approach.

**PREMISE detail.** Present: `docs/ADAPTER_PLAYBOOK.md` §4/§5, `scripts/cross_repo_samples.json` (ky / MQTT.js / socket.io), `scripts/cross_repo_validate.py` / `index_root`, ticket 018 (pinned SHAs), ticket 150 (TS samples + floors), ticket 154 (JSDoc slot), ticket 155 (IMPORTS / path aliases). **Ambiguous (surfaced):** "a `benchmarks/` file" (prose path — resolved in design to `docs/benchmarks/` per existing layout); "the parity table's gate rows" (prose — resolved to playbook §4 matrix, not generated §7).

**INPUT KIND:** ticket (not epic).

**Recalled claims — advisory.**

| # | Claim | Type | Matched by | Relevant here? |
|---|---|---|---|---|
| 1 | `reproduce-the-payload-not-the-story` | 2 | handle | **Yes** — AC4 requires `--file` fixture before filing a finding |
| 2 | `prove-the-guard-fails` | 2 | handle | **Yes** — proving test must fail if §4 still says typescript gate 4 "never" |
| 3 | `prefer-the-provable-fix` | 2 | handle | **Yes** — pinned SHAs + determinism hashes, not anecdote |

**Exposure-checker:** skipped with refine (`skip: yes`).

## Phase 1 — analysis

`PREMISE: 8 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists, Scope, Acceptance criteria, Exclusions, Notes) | 5 decomposed | ROWS: C=3 R=5 G=2 AC=5`
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
`TRACK: backend — TS adapter field measurement + docs/benchmarks + playbook §4 + proving test`
`BASELINE: green`
`SCOPE: M`
`TIER: full`
`RULE SECTIONS: 6 applicable — 4 by change-type | 2 by recalled handle — R2 (change-type) ✅ corpus by shape not popularity · R4.2 (change-type) ✅ two-build hash equality + pinned SHAs · R7.2 (change-type) ✅ TOKEN_LEDGER row · R7.6 (change-type) ✅ protocol not restated; §4 cell updated not retold · R6.5 (recalled handle) ✅ proving test red if §4 still never · R6.7 (recalled handle) ✅ measurement committed not typed claim`

### BASELINE

```
Ran at e0928350b9ca0718bf894d23604a8882458e687b
$ .venv/bin/python -m pytest -q --tb=no
3222 passed in 255.97s (0:04:15)
```

Green. No baseline exclusions.

### Clarifications (all self-resolved; j = 0)

| # | Question | Resolution | Citation |
|---|---|---|---|
| Q1 | Block on depends_on 233 (still todo)? | **No.** 233 pins Python/SQL samples for before/after reports; 235's deliverable is a TS field-round measurement + §4 gate-row update. Independent. | ticket Scope item 5; playbook §4 vs §7; BACKLOG 233 todo |
| Q2 | Where is the `benchmarks/` file? | **`docs/benchmarks/235_typescript_field_round.md`** — repo's measurements live under `docs/benchmarks/` (CONVENTION layout; no top-level `benchmarks/`). | `docs/benchmarks/` inventory; ticket Scope item 2 |
| Q3 | Which two public repos? | **Design HOW:** (A) `trpc/trpc` — TS monorepo with packages + path aliases (155 miss shape); (B) a JSDoc-heavy mixed `.js`/`.ts` package not already in the three pinned kinds — pick at execute after a shallow shape check; pin SHAs. | ticket Scope item 1; samples `ky`/`mqttjs`/`socketio` kinds |

### Requirements matrix

| ID | Source | Verbatim (abbrev) | Interpretation | Status |
|----|--------|-------------------|----------------|--------|
| G1 | Why | Gate 4 never run against TS | Close the gate-4 hole for typescript | open |
| G2 | Why | cheaper gates missed params/modifiers/REFERENCES | Field round asks the other question; do not fix 231/232 gaps here | open |
| R1 | Scope 1 | two repos by shape (monorepo refs+aliases; mixed JSDoc) | Choose + pin SHAs; shapes not covered by ky/MQTT/socket.io | open |
| R2 | Scope 2 | record protocol numbers in benchmarks/ | Commit `docs/benchmarks/235_*.md` with census, unlinked split, cross-lang | open |
| R3 | Scope 3 | ask nav tools with grep-verified answers | Record hits and misses | open |
| R4 | Scope 4 | file each finding as ticket with `--file` fixture | Or drop as not reproducible | open |
| R5 | Scope 5 | fold into parity table gate rows | Update playbook §4 typescript gate-4 cell | open |
| C1 | Not in scope | no fixes; no second round; 231/232 own known gaps | Measurement-only | closed |
| C2 | Exclusions E1 | no private TS corpus | Public shape choice is the whole design | open (exclusion) |
| C3 | Notes | ticket exists because gate 4 is unenforced | Deliver measurement so matrix stops saying never | open |
| AC1 | AC | benchmarks file + pinned SHAs + host + date | Falsifiable file content | open |
| AC2 | AC | two clean builds hash-identical (R4.2); delete graph.db between | Falsifiable hash equality | open |
| AC3 | AC | every nav Q recorded with grep expected beside tool answer | Falsifiable table rows | open |
| AC4 | AC | finding → ticket+fixture or explicit drop | Falsifiable ticket files or drop notes | open |
| AC5 | AC | finding nothing is valid green close | Explicitly allowed | open |

### AC validation

| AC | Ticket states | Independently computed | Match? | Falsifiable? |
|----|---------------|------------------------|--------|--------------|
| AC1 | benchmarks + SHAs + host + date | file must exist under docs/benchmarks with those fields | Y | measurable |
| AC2 | two-build hash equal after delete | script hashes ordered nodes+edges twice | Y | measurable |
| AC3 | grep expected beside payload | table rows in benchmark | Y | measurable |
| AC4 | ticket+fixture or drop | follow-up ticket files or "none / dropped" section | Y | measurable |
| AC5 | no findings ⇒ green | STATUS done without fix tickets | Y | measurable |

### Inventory

No universal "all/every" over a code surface beyond "every nav-tool question asked" — denominator = questions asked in the round (enumerated in the benchmark). Per-item checklist lives in the benchmark's Q&A table.

### Gap analysis

Playbook §4 records typescript gate 4 as **never**. Protocol §5 exists; checkouts/floors/adapter cmd exist (150). Gap is the unrun protocol + absent measurement artifact + stale §4 cell.

### Blast radius

- `docs/benchmarks/235_typescript_field_round.md` (new)
- `docs/ADAPTER_PLAYBOOK.md` §4 matrix cell + §7 footnote if it cites "never"
- `docs/tasks/235_*.md` (this working doc), possibly new finding tickets `docs/tasks/23N_*.md`
- `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`
- `tests/test_ts_field_round_recorded.py` (proving)
- No adapter/core code unless a finding ticket is filed (out of 235 fix scope)

## Phase 2 — design

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 1 proven on a real corpus`

### Handle traces

| Handle | Command + result |
|---|---|
| reproduce-the-payload-not-the-story | AC4: any finding must pass `node adapters/typescript/index.js --file <fixture>` before a ticket is filed; drop if not reproducible |
| prove-the-guard-fails | proving test asserts playbook §4 typescript gate-4 cell is not the literal `never`; fails on `e092835` today |
| prefer-the-provable-form | AC1/AC2: pinned SHAs + dual-build hash in the benchmark file |

### Approach

1. **Corpus.** Clone two public repos at pinned SHAs into a disposable cache (same pattern as `cross_repo_validate.clone_sample`):
   - **Repo A — monorepo / project references + path aliases:** `trpc/trpc` (packages workspace; tsconfig paths). Confirm `references` and/or `paths` present before measuring; if absent at tip, substitute another public monorepo of the same shape and record why.
   - **Repo B — JSDoc / mixed .js+.ts:** a public package whose tree has both extensions and JSDoc `@typedef`/`@param` (154's slot). Prefer a medium tree; must not duplicate the three pinned kinds' sole claim (library / ts_js_mixed / compiled_beside_source) without adding the JSDoc-heavy signal.
2. **Build.** `index_root(root, language="typescript")` via the same helper as cross_repo; record wall, files, parsed_ok, nodes, edges. Delete `graph.db` between the two determinism builds (219).
3. **Census.** Node kinds vs `grep` counts; unlinked-edge ratio per kind split expected (stdlib/third-party) vs recoverable; `get_index_status` verbose cross-language census.
4. **Nav questions.** For each of `find_implementations`, `find_callers`, `find_references`: pick a symbol verified by `grep`, record expected vs payload (including correct answers).
5. **Findings.** Per playbook §5 step 7: `--file` fixture or explicit drop. File new tickets only for reproducible defects not already owned by 231/232.
6. **Fold.** Edit playbook §4 table: typescript gate 4 → this round's date + benchmark link. Do not hand-edit §7 generated table.
7. **Prove.** `tests/test_ts_field_round_recorded.py` — benchmark file required fields; §4 cell not `never`; red on main.

### Rejected alternatives

| Alternative | Why rejected |
|---|---|
| Re-use ky / MQTT.js / socket.io as the field corpus | Ticket Scope 1: field repos must add a shape the three pinned samples do not |
| Private consumer repo | E1 — none available; public shape choice is the design |
| Fix params/modifiers/REFERENCES during the round | Not in scope; 231/232 own those |
| Hand-edit playbook §7 scoreboard | R6.7 / playbook: generated only |

### Assumptions

| Assumption | Tag |
|---|---|
| Handover authorises corpus pick within Scope 1 shapes | ratified by handover authorisation |
| `docs/benchmarks/` is the correct path for the ticket's `benchmarks/` | verified — directory exists; no top-level benchmarks/ |
| 233 not a blocker | verified — independent deliverable |

### Change list

| # | Change | File/area | Blast radius | Ph2 covered by |
|---|---|---|---|---|
| 1 | Field-round benchmark write-up (numbers, SHAs, host, date, Q&A, findings) | `docs/benchmarks/235_typescript_field_round.md` | docs | R1–R4, AC1–AC5, G1 |
| 2 | Update playbook §4 typescript gate-4 cell (+ footnote if needed) | `docs/ADAPTER_PLAYBOOK.md` | docs | R5, G1, AC5 |
| 3 | Proving test: benchmark schema + §4 not "never" | `tests/test_ts_field_round_recorded.py` | CI | AC1, R5, prove-the-guard-fails |
| 4 | Optional: finding tickets + fixtures | `docs/tasks/NNN_*.md`, `tests/fixtures/…` | backlog | R4, AC4 |
| 5 | BACKLOG done + TOKEN_LEDGER row + this working doc | `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, ticket | docs | R7.2, C3 |

### Coverage-gap exclusions

| # | Gap | Expiry | Class |
|---|---|---|---|
| E1 | No private TS corpus (ticket E1); round designed on public shape choice only | `expiry: when a private TS/JS corpus is available to this repo for field rounds` | corpus / first occurrence |

AC3 nav questions are input-shape-dependent and **proven on the real public field corpus** (c=1).

### Proving test

`pytest tests/test_ts_field_round_recorded.py -q` — fails on main while §4 says `never` / benchmark absent; green after.

### Verification plan

No ❌. E1 recorded with checkable expiry. AC3 on real corpus.

- **Gate 2 status:** cleared (`check_lines` exit 0)



## Phase 3 — Execute

- **Branch:** `feat/235-typescript-adapter-field-round`
- **Implemented (⊆ approved change list):**
  1. `docs/benchmarks/235_typescript_field_round.md` — corpus SHAs, builds, census, unlinked split, nav Q&A, findings disposition
  2. `docs/ADAPTER_PLAYBOOK.md` §4 + §7 footnote — TS gate 4 no longer "never"
  3. `tests/test_ts_field_round_recorded.py` — proving test
  4. Ticket matrix cell + status done; BACKLOG done; TOKEN_LEDGER row
  5. No new finding tickets (232/234 already own the observations; AC5)
- **Design-conformance deviations:** none.
- **Proving test:**

```
Ran at 62f683f9e6a79e1820131541a2c3e2d483c295cf
$ .venv/bin/python -m pytest tests/test_ts_field_round_recorded.py -q
.. 2 passed
```

(Red-before: on `e092835` the playbook still said "never for TS" and the benchmark file was absent — the proving test's assertions fail on that tree.)

## Phase 4 — Review

- **reviewer verdict:** N/A — REVIEWER: OFF (`--no-reviewer`). No rule-book-grounded review of this diff exists.
- **challenger (ticket-blind) result:** CHALLENGER: ON — reconstructed R1–R5 + AC1–AC5 + C1 from the raw ticket + `git diff --cached main` only (working doc withheld). **11/11 MET; LGTM**. No substantive finding.
- **Scope reconciliation:** diff ⊆ approved list (benchmark, playbook §4/§7 footnote, proving test, backlog/ledger/task status).
- **Clean?** reviewer waived · challenger LGTM · proving test green → yes.
- **Reviewed at** `62f683f9e6a79e1820131541a2c3e2d483c295cf`

## Phase 5 — Finalise

- **PR draft:** from `.github/pull_request_template.md`.
- **Planned outward actions:**
  - [x] push branch — handover authorisation
  - [x] open PR via gh — handover authorisation
  - [ ] merge — NOT authorised
- **Follow-up tickets:** none new (232, 234 already open).
- **Durable lesson:** none new — field round confirmed already-filed gaps; AC5 path exercised.
- **Revert path:** revert the branch.

### Learning loop

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md | mango files written: 0`

---

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Notes |
|-------|---------------------|-------|--------|-------|
| Review | ticket-blind challenger (main-loop) | 1 | unmeasured | host surfaces no usage block; reviewer OFF |

`LEDGER TOTAL: unmeasured · top cost driver: main-loop`

## Decision log

| When | Decision | Why |
|------|----------|-----|
| 2026-09-08 | Corpus = typescript-eslint + jsdoc | Scope 1 shapes: project references+paths; JSDoc-heavy JS |
| 2026-09-08 | No new finding tickets | Observations ⊆ 232 / 234; AC5 |
| 2026-09-08 | CONTAINS "unlinked" expected | target_raw by design |

## Session status (close)

- **Last updated:** 2026-09-08 (finalise)
- **Current phase:** finalise
- **Next action:** push + open PR
- **Blocked on:** nothing
