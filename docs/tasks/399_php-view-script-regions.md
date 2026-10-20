---
id: 399
slug: php-view-script-regions
title: "A PHP view's inline <script> is not in the graph"
phase: 2
milestone: Coverage
status: done
depends_on: [395]
---

## Why this exists

Split out of 395, which shipped only its Scope 2: ES5 constructor members as Methods. The anchor's
second field retro (2026-10-10 → 10-17) also asked for:

- F1: handlers in a `.php` view's inline `<script>`.
- Prototype members (395 review): `Ctor.prototype.m = function` and `Ctor.prototype = {…}` are not
  read. A pass for them must share 395's per-constructor `seen` set, or a member is declared twice.

Template references (F2–F4) were split to [406](406_php-template-references.md) on 2026-10-19.

The script half does not fit today's seams. Each suffix has exactly one adapter
(`code_atlas/adapter.py` `extension_index`). Handing a `.php` file's `<script>` regions to the JS
reader therefore needs a new handshake field plus a second `parse` call from the core, which is a
`contract_version` bump (R3). The other route is a JS reader inside the PHP adapter.

**Evidence gate — met 2026-10-19.** 395's Scope 1 count, run by the maintainer with `grep` on the anchor
(no `vendor/`, no `.worktrees/`):

| Metric | Whole repo | `src/` only |
|---|---|---|
| PHP files containing `<script` | 1,122 | 960 |
| Total PHP files | 8,475 | 4,738 |
| `this`/`self.X = function` | 1,947 | 230 |
| `$scope.X =` | 8,387 | 1,230 |

The last two rows count `.php` and `.js` together. 13% of the anchor's PHP files carry a script the
graph cannot see, which the maintainer judged worth a contract bump: core fan-out, not a second JS
reader (2026-10-19).

## Scope

1. The anchor count above, and the route chosen from it: core fan-out with a contract bump, or an
   in-adapter reader.
2. Embedded `<script>` functions become symbols of the `.php` file at their true lines (395 AC2).

## Acceptance criteria

- **AC1:** 395's AC2, as written there.
- **AC2:** An index with no such files is byte-identical.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 399 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies A1–A3, merges (after #95 if it lands first: BACKLOG rows are adjacent), tags `v0.7.0`, runs E1. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: L` · Run mode: `autorun 399 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/399-php-view-script-regions` off `main` (c92aba84). Contract `.mango/run-contract-399.txt`.

## Phase 0 — refine

`PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 28 unresolved surfaced | 5 want-decision asked | 23 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise.** `code_atlas/adapter.py` `extension_index`, 395's AC2 and `file_outline` (`code_atlas/tools/file_outline.py`) resolve.
**Recall.** `keep-first-hides-the-later-declaration` (384-C1): a guest row merged into a host file meets keep-first dedupe, so
merge order is fixed (H15). `read-a-literal-by-its-structure-not-a-regex` (361-C1): regions come from the PHP tokens, not a regex
over the file (H2).

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 53,455 tokens) raised twelve. They are H12–H21 and A3 below.

| # | Decision | Class | Resolution |
|---|---|---|---|
| W1 | route | want | **asked, settled by the maintainer (2026-10-19):** core fan-out with a contract bump |
| W2 | template references | want | **asked, settled by the maintainer (2026-10-19):** split to 406 |
| H1 | who finds a region | how | the host adapter, from its own tokens: only it knows which bytes are PHP (R1.4) |
| H2 | how | how | `T_INLINE_HTML` tokens of nikic/php-parser 5 (`Parser::getTokens`); PHP between them is a hole (361-C1) |
| H3 | which `<script>` | how | HTML spec: `type` absent, empty or a JavaScript MIME essence (or legacy `language`) is classic → `.js`; `module` → `.mjs`; any other type is a data block; with `src` the content is ignored (R2) |
| H4 | how the guest is named | how | by suffix, found with `extension_index` — no language name in the core (R1.1) |
| H5 | a guest that cannot take spans | how | only an adapter announcing capability `spans` is sent one (R1.6) |
| H6 | the request | how | `{path, spans, suffix}`; one request per suffix per file, spans in source order (R4.2) |
| H7 | a hole's bytes | how | blanked to spaces, `\n`/`\r` kept, so every line is the file's own (AC1) |
| H8 | offsets | how | bytes of the file as read; the TS adapter blanks a `Buffer`, never a UTF-16 string |
| H9 | syntax errors around holes | how | span mode keeps TypeScript's recovered tree (`parse.js:260` fails a whole file otherwise) |
| H10 | the guest's File node | how | dropped; the host's File (qname = path, CONTRACT §3) owns the path, so guest edges sourced at the file stay attached |
| H11 | guest qnames | how | path-shaped `view.php::onPick` (CONVENTION §3), never `\ns\fn`, so no collision with PHP's |
| H12 | per-row language | how | the resolver's same-language gate (`resolver.py:345,388`, 204) and the store's language filters key on `files.language`; a guest row carries its own: nullable `language` on `nodes` and `edges`, NULL = the file's (SCHEMA 8 → 9) |
| H13 | contract or store | how | a store column the core stamps, not a contract field: adapters never emit it (R3.2, R1.4) |
| H14 | readers of a row's language | how | census (`edge_language_census`, `_cross_language_edges`) and the node/edge filters read `COALESCE(row, file)`; `indexed_languages` stays file-based — a language is indexed when it owns files |
| H15 | merge order | how | host rows first, then guest; keep-first dedupe (384-C1) keeps the host on a clash (R4.2) |
| H16 | concurrency | how | each worker starts its own guest process lazily, on the first region; no shared pipe, no writer-thread parse |
| H17 | paths | how | build, incremental (`_parse_all`), read-through reparse and overlay (`parse_files`) all go through `_work` / `_parse_one` |
| H18 | a guest unavailable or failed | how | host `File.extra.embedded_unread: [suffix]`; `parsed_ok` stays the host's (R5.6) |
| H19 | stub roots | how | `declarations_only` passes to the guest (039) |
| H20 | Docker | how | the guest request rides the same wire-path rebase (`adapter.py` `_rebase_reply`) |
| H21 | an old index | how | SCHEMA 9 refuses an 8 database (`SchemaVersionError`); the next build rebuilds (356) |
| H22 | release | how | contract 18 · schema 9 cut 0.7.0 (R3.1) |
| H23 | two scripts, one name | how | one guest parse per suffix, so the TS adapter's own same-file rules apply, as for one `.js` file |
| A1 | scope widened past "a contract bump" | want | **ASSUMED (awaiting ratification):** H12's schema bump, owed to keep 204's language gate true |
| A2 | prototype members (Why lists them) | want | **ASSUMED (awaiting ratification):** out — not in Scope |
| A3 | recovered-parse precision | want | **ASSUMED (awaiting ratification):** kept unflagged; a PHP hole breaks a statement, not a declaration |

Out of scope: inline `on*=` attributes (361), `.html` files, template references (406).

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=2 R=2 G=1 AC=3`
`CLARIFICATION: 28 raised | 28 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/14 touched files under UI paths`
`BASELINE: green`
`SCOPE: L`
`TIER: full`

### BASELINE

`.venv/bin/pytest -q` at aa93972f with this run's first three untracked files present: `2 failed, 4853 passed, 4 skipped,
1 xfailed in 634.25s`. Both reds (`test_sql_confinement`, `test_server_build_on_payloads`) pass on the clean tree
(`git stash -u`: `15 passed`) — `embedded.py` imported a name not yet written. Baseline green.

### Gap analysis (enhancement)

| Goal | Current | Target |
|---|---|---|
| F1 view handlers | a `.php` file's `<script>` is invisible; 1,122 anchor files | its functions are symbols of the `.php` file, at their lines |
| the language gate (204) | a row's language is its file's | a guest row keeps its own, so no PHP call links to a view's JS and back |

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "handlers in a `.php` view's inline `<script>`" | F1 answers without Grep | ⏳ |
| C1 | AC2 | "byte-identical" | rows change only for files with a script region | ⏳ |
| C2 | R3.1 | contract bump | v18 · schema 9 · release 0.7.0 · conformance updated | ⏳ |
| R1 | Scope 1 | "the route chosen from it" | W1: core fan-out | ⏳ |
| R2 | Scope 2 | "symbols of the `.php` file at their true lines" | H1–H23 | ⏳ |
| AC1 | AC | 395's AC2: `file_outline` lists `onPick` at its true line | | ⏳ |
| AC2 | AC | an index with no such files is byte-identical | | ⏳ |
| AC-field | 395 | the anchor replay | E1 | ⏳ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — one outline row, its qname and `line_start` | |
| AC2 | yes — every existing adapter suite and the conformance suite unchanged, and a no-script `.php` result carries no `embedded` | rows, not database bytes (H21 forces a rebuild) |
| AC-field | no — the anchor is not on this machine | E1 |

### Rule sections

`RULE SECTIONS: 7 applicable — 5 by change-type | 2 by recalled handle — §R1.1 (change-type) ✅ the guest is found by suffix and capability, never by name · §R1.4 (change-type) ✅ the PHP adapter only reports byte spans; store.py alone owns the new column · §R1.6 (change-type) ✅ spans is an optional capability; an adapter without it is never sent one · §R3.1 (change-type) ✅ contract 18, schema 9, a release · §R5.6 (change-type) ✅ embedded_unread names a region nothing read · §R4.2 (handle keep-first-hides-the-later-declaration) ✅ host first, spans in source order · §R2 (handle read-a-literal-by-its-structure-not-a-regex) ✅ tokens, not a regex over the file; the HTML spec's script types, no framework`

## Phase 2 — design

### Approach

1. **Contract 18.** A result may carry `embedded: [{suffix, spans}]` (byte `[start, end)` pairs, ascending, disjoint);
   a request may carry `spans` + `suffix`; capability `spans` says an adapter takes one. `File.extra.embedded_unread`
   names a suffix nothing read.
2. **PHP adapter.** `ScriptRegions` walks the parse's tokens, reads `<script>` start tags in `T_INLINE_HTML` only, and
   returns each classic / module script's content minus PHP holes, grouped per suffix (H2, H3).
3. **TS adapter.** Announces `spans`; on a span request it blanks every other byte of the file (newlines kept), parses
   with the suffix's script kind, and keeps the recovered tree (H7–H9).
4. **Core.** `code_atlas/embedded.py` sends each region to the suffix's owner, drops the guest File, stamps the guest's
   announced name as each row's `language`, and appends host-first (H10, H15). `_work` (one lazily started guest per
   worker) and `_parse_one` call it (H16, H17).
5. **Store / resolver.** Schema 9: nullable `language` on `nodes` and `edges`; every language filter and the census read
   the row's before the file's; the resolver's call-site language does the same (H12–H14).
6. Every adapter announces 18; release 0.7.0; docs (adapter READMEs, CONVENTION handshake, CHANGELOG).

### Rejected alternatives

- **A JS reader inside the PHP adapter** — a second JS parser; W1 settled it.
- **The TS adapter claiming `.php`** — `extension_index` refuses a suffix two adapters claim, and only PHP knows which bytes are PHP.
- **Guest rows labelled with the file's language** — a PHP bare call named like a view's JS function would lose its
  unique link, and an unknown-receiver `->x()` would link to a JS method (204's gate).
- **A synthetic `files` row per region** — `_reconcile` deletes a path git does not yield, and `file_outline` reads one path.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| php-parser 5 tokens carry byte `pos` | verified | `PhpParser\Token extends \PhpToken`; `ParserAbstract::getTokens` |
| TypeScript's parser always returns a tree | verified | `parse.js:256`; diagnostics are read, never thrown |
| a guest edge sourced at the file links to the host File | verified | File qname = path in every adapter (CONVENTION §3) |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | contract 18 | `code_atlas/contract.py` | every adapter's handshake | C2, R2 | 1/1 |
| 2 | span request, `embedded` result | `code_atlas/adapter.py` | every parse | R2 | 1/1 |
| 3 | region fan-out and merge | `code_atlas/embedded.py` (new), `code_atlas/indexer.py` | build, incremental, reparse, overlay | R2, AC1 | 2/2 |
| 4 | row language | `code_atlas/store.py`, `code_atlas/resolver.py` | schema 9; language filters, census, bare-name gate | R2, C2 | 2/2 |
| 5 | regions | `adapters/php/src/ScriptRegions.php` (new), `adapters/php/src/Parser.php`, `adapters/php/index.php` | PHP results with a script | R2, AC1 | 3/3 |
| 6 | span mode | `adapters/typescript/index.js`, `adapters/typescript/src/parse.js` | TS requests with spans only | R2, AC1 | 2/2 |
| 7 | version 18 | `adapters/python/index.py`, `adapters/sql/index.js` | handshake | C2 | 2/2 |
| 8 | tests | `tests/test_php_script_regions.py` (new), `tests/contract/test_contract_schema.py`, the version pins | — | AC1, AC2, C1 | 3/3 |
| 9 | release | `pyproject.toml`, `CHANGELOG.md`, plugin / marketplace / hooks / settings snippet | install | C2 | 6/6 |
| 10 | docs | adapter READMEs, `docs/CONVENTION.md` | doc budgets | G1 | 3/3 |
| 11 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

Traced: 384-C1 — `_dedupe_nodes` (`store.py:4786`) keeps first, so host rows go first. 361-C1 — `ScriptRegions` reads tokens.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — PHP + TS adapters + build + tool | real build, `file_outline` | authored | ✅ |
| R2 language gate | integration — resolver | real build, `find_callers` both ways | authored | ✅ |
| AC2 | integration | every adapter suite and conformance unchanged; a no-script `.php` carries no `embedded` | existing | ✅ |
| AC-field | runtime — anchor | manual-recorded (E1) | n/a | ❌ → E1 |

**E1 (coverage-gap exclusion, escalated).** AC-field · risk: low · why: the anchor index is not on this machine · follow-up:
after 0.7.0, rebuild the anchor and replay F1's question, then `file_outline` one view with a script ·
`expiry: when the anchor index is available to a maintainer run` · `seen: 378, 384, 388, 389, 394, 390, 391, 393, 395, 399`.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 1 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/pytest -q tests/test_php_script_regions.py` — red on `aa93972f`, green after.

### Rollback

`git revert`; the next build after a revert rebuilds (schema 8).

## Phase 3 — execute

Commits `35ca4ea8` (code + tests), `bb51599a` (release 0.7.0), `53a8d41c` (docs).

**Red first.** The proving test with the code stashed (`aa93972f`'s adapters and core): `3 failed, 1 passed in 1.56s` —
the passing one is AC2's no-region case, which holds before and after.

**Green after.** `tests/test_php_script_regions.py` `5 passed`; the full suite then read `43 failed, 4823 passed, 4
skipped, 1 xfailed` — every red a pin the bump owes: 17 → 18, schema 8 → 9 (and the "newer" fixture 9 → 10), 103 → 104
core modules, the store's two column lists, the TS handshake's `spans`, and two core comments naming a language (R1.1).
After those: the 7 affected files `487 passed`. `ruff`, `mypy` (104 files), `tsc` clean. Ran at 53a8d41c.

**Docs.** A region paragraph in PLAN §4.1 and CONVENTION overran both budgets (20,081 / 7,179), so the protocol lives in
`contract.py`, both adapter READMEs and one ADAPTER_PLAYBOOK row (R7.6); PLAN's handshake example names 18.

**Axis 1.** Change-list rows 1–10; row 10 lands as the READMEs + playbook, not CONVENTION. **Axis 2.** Approach bullets
1–6 implemented as approved; bullet 6's CONVENTION line deviated to the playbook (budget), recorded here.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON` — verdict **clean (challenger only — REVIEWER: OFF)** after the review commit.

**Challenger** (ticket-blind: raw ticket, 395's AC, `git diff aa93972f..53a8d41c` without this file; 1 dispatch, 106,883
tokens): 10 met · 1 not met · 0 can't tell. It ran real builds: true lines through a BOM + CRLF `.phtml`, a `<?= ?>` hole and
a heredoc; same row hash at 1 and 4 workers; an incremental rename; AC2's 69-file PHP fixture tree row-identical to base.

| # | Finding | Resolution |
|---|---|---|
| M1 | `ruff` E501 on four lines — the gate could not read green | rewrapped (9432b764) |
| m2 | `<style>` / `<textarea>` content read as markup, so a `<script>` inside became code | raw-text elements skipped, `test_challenger_a_script_inside_raw_text_is_text` (9432b764) |
| m3 | a real syntax error in a script is recovered silently | kept — A3 |
| m4 | a span past the file's end errored as "cannot read file" | clipped to blank (9432b764) |
| m5 | every `.php` tokenized twice | a file with no `<script` returns before tokenizing (9432b764) |
| m6 | guest processes scale with `workers` | kept and stated: one per worker, only once a region is met (H16) |
| m7 | `read_symbol`'s capability lookups read the file's language | kept: PHP and TS announce the same flags today; latent only |

**Red first.** The raw-text test against 53a8d41c's `ScriptRegions.php`: `1 failed`; after: `1 passed`.
**Gate.** `scripts/gate.sh` at 9432b764: `21 passed · 0 failed · 0 skipped` — `GATE GREEN`.

| Row | Ph3/4 proven by | k/N |
|---|---|---|
| G1 / R2 / AC1 | `test_ac1_…`, `test_the_js_adapter_reads_only_the_spans_…`, `test_challenger_…raw_text…` | 3/3 |
| R2 language gate | `test_a_script_call_links_in_its_own_language_…` | 1/1 |
| C1 / AC2 | `test_ac2_…`, every adapter suite and conformance unchanged, challenger's row diff | 3/3 |
| C2 | `tests/contract`, `test_release_discipline.py`, `test_schema_version_recovery.py` | 3/3 |
| R1 | W1 | 1/1 |
| AC-field | E1 | 0/1 (excluded) |

Reviewed at 9432b764 — files: change-list rows 1–10. Working doc: `docs/tasks/399_php-view-script-regions.md`.

## Phase 5 — finalise

**Durable lesson.** A guest row inside a host file inherits the file's language everywhere `files.language` is joined; the
resolver's same-language gate (204) made that a correctness bug, not a label, so the row carries its own.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`

**Deferred to the maintainer:** merge, tag `v0.7.0`, E1 on the anchor, ratify A1–A3.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 53,455 |
| 4 review | ticket-blind `challenger` | 1 | 106,883 |

`LEDGER TOTAL: 160,338 · top cost driver: 4 review / challenger` — main loop unmeasured.
