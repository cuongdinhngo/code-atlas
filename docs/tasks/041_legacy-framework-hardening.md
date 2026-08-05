---
id: 041
slug: legacy-framework-hardening
title: Legacy/framework hardening — encoding, .blade.php, extra extensions
phase: 1.5
milestone: Robustness
status: in-progress
depends_on: [009]
---

## Goal
Stop silent losses on real-world PHP trees. Three concrete leaks: non-UTF8 legacy files soft-fail and
vanish from the graph with no signal; `.blade.php` views match the `.php` suffix and get sent to the
adapter as symbol-less HTML; and non-`.php` sources (Drupal `.module`/`.inc`, `.phtml` views) index
as nothing. None is an architecture limit — they are robustness gaps that make coverage look complete
when it isn't (§19 agent-first pivot).

## Scope / Deliverables
- **Encoding hardening:** a file that isn't valid UTF-8 is decoded via a defined fallback or counted
  in `parse_failures` — never silently dropped with `parsed_ok=0` and no signal.
- **Blade ignore rule:** exclude `.blade.php` so those files aren't routed to the PHP adapter
  (they currently match via last-segment `.php` suffix — `code_atlas/indexer.py:161`).
- **Extra extensions:** let the PHP adapter announce additional extensions (`.phtml`, `.module`,
  `.inc`) so they index; extension routing already flows from the adapter handshake
  (`code_atlas/indexer.py:247`), so this is an adapter-announce change, not a core change.

## Constraints
- The extension set stays **configurable via the adapter handshake**, never hardcoded in the core
  (R1.1); the core adds no language branches.
- Any file that cannot be decoded/parsed must surface in `parse_failures` (visible via task 028's
  `edge_health`), never a silent absence.
- Blade exclusion is an ignore rule, consistent with the existing built-in ignore patterns
  (`code_atlas/ignore.py:17-24`).

## Acceptance criteria
- A non-UTF8 fixture is either indexed or counted in `parse_failures` — never silently absent
  (asserted).
- `.blade.php` files are ignored (not sent to the adapter), proven on a fixture tree.
- A `.phtml`/`.module` fixture indexes when the adapter announces that extension; unchanged when it
  doesn't.

## References
`code_atlas/indexer.py:161` (suffix match), `:247` (extension_index from handshake);
`code_atlas/ignore.py:17-24` (built-in ignores); `adapters/php/index.php:27` (`extensions => ['.php']`);
task 028 (`parse_failures` / `edge_health`). PLAN §1, §19. Feedback origin:
[`FEEDBACK.md`](../FEEDBACK.md) rounds 1 & 2 ("configurable extensions + encoding hardening;
non-UTF8 files vanish silently; Blade matches .php").

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 041 — Legacy/framework hardening (working doc)

- **Ticket:** 041 · local `docs/tasks/041_legacy-framework-hardening.md`
- **Type:** enhancement
- **Repo(s) / Porting:** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — `749 passed` (`.venv/bin/pytest -q`), main @ post-040
  <!-- baseline exclusions: none -->
- **work_doc_mode:** embed (plain local-file ticket)

---

## Phase 0 — Refine

`REFINE: 1 unresolved surfaced | 1 want-decision ASSUMED | 3 how-decision resolved+cited | skip: no`

**INPUT KIND:** ticket

Exposure-checker ([challenger](90ec33c8-6102-470c-83a7-88cbcfa2d982)): **1 WANT** (encoding recover vs fail-visible).

**Settled wants (ASSUMED under standing approval “suggest and do the best option, and pass all gates” — awaiting Gate 1 ratification):**

| # | Want | Chosen direction | Becomes |
|---|------|------------------|---------|
| W1 | Non-UTF8: recover into graph vs fail-visible only? | **Fail-visible** — `parsed_ok=0` + count in `parse_failures`; never lossy/mojibake fallback (PLAN §4.1). Prove with fixture: file present in `files`, `parse_failures ≥ 1`, not silently absent. | AC1 = fail-visible bar |

**Resolved HOW + citation:**

| # | How | Resolution | Cite |
|---|-----|------------|------|
| H1 | Blade drop | Builtin ignore `*.blade.php` (gitignore subset; last-match-wins) | ticket Constraints; `ignore.py:17-24`; FEEDBACK blade note |
| H2 | Extra suffixes | Announce `.phtml`, `.module`, `.inc` on PHP handshake only (R1.1) | ticket Scope/AC; `adapters/php/index.php:27` |
| H3 | Core stays agnostic | No core hardcoding of those suffixes; routing via `extension_index` | R1.1; ticket Constraints |

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| 0 refine | extractor (code facts) | 1 | unmeasured (blocking retrieval) |
| 0 refine | mango:challenger (exposure-checker) | 1 | unmeasured (blocking retrieval) |
| 4 review | mango:reviewer | 1 | unmeasured (blocking retrieval) |
| 4 review | mango:challenger | 1 | unmeasured (blocking retrieval) |

**Roll-up:** **4 dispatch**; all **unmeasured (blocking retrieval)**. Phases 1–3/5: 0 dispatch.

---

## Phase 1 — Analysis

`SECTIONS: 5 found (Goal, Scope / Deliverables, Constraints, Acceptance criteria, References) | 5 decomposed`
`ROWS: G=1 R=3 C=3 AC=3 W=1`

| ID | Source | Verbatim (short) | Interpretation | Ph1 | Ph2 | Ph3/4 | Status |
|----|--------|------------------|---------------|-----|-----|-------|--------|
| G1 | Goal | stop silent losses: encoding, blade, extra ext | Three robustness fixes | ticket | Approach | proving | ✅ |
| R1 | Scope | encoding → fallback OR parse_failures; never silent | W1: fail-visible only | W1 | CL | AC1 | ✅ |
| R2 | Scope | Blade ignore so not routed to PHP adapter | builtin `*.blade.php` | H1 | CL | AC2 | ✅ |
| R3 | Scope | PHP announces .phtml/.module/.inc | handshake extensions list | H2 | CL | AC3 | ✅ |
| C1 | Constraints | extensions via handshake; no core lang branch | R1.1 | rulebook | — | CI | ✅ |
| C2 | Constraints | undecodable → parse_failures | files row + failed count | 028 | — | AC1 | ✅ |
| C3 | Constraints | Blade = ignore rule like builtins | ignore.py BUILTIN | H1 | — | AC2 | ✅ |
| AC1 | AC | non-UTF8 fixture indexed OR parse_failures — not absent | W1: assert parse_failures + files row | W1 | proving | test | ✅ |
| AC2 | AC | .blade.php ignored; not sent to adapter | fixture tree; no parse attempt / ignored | H1 | — | test | ✅ |
| AC3 | AC | .phtml/.module index when announced; not when not | announce change + routing proof | H2 | — | test | ✅ |
| W1 | refine | fail-visible encoding bar | no mojibake fallback | Phase 0 | — | AC1 | ✅ |

## AC validation

| AC | Ticket | Computed | Match | Falsifiable |
|----|--------|----------|-------|-------------|
| AC1 | non-UTF8 not silently absent | `files` has path · `parsed_ok=0` · `parse_failures≥1` | Y (under W1) | measurable |
| AC2 | blade ignored | `is_ignored("x.blade.php")` · not in collect set | Y | measurable |
| AC3 | extra ext when announced | collect includes `.phtml` after announce; control without | Y | measurable |

`CLARIFICATION: 1 raised | 1 ASSUMED standing | j=0 (pending Gate 1 ratify of ASSUMED)`
`TRACK: backend` · `SCOPE: M` · `TIER: full`
`RULE SECTIONS: §1 ✅ R1.1 · §2 N/A (ignore+announce, no framework names in adapters) · §4 ✅ no mojibake · §5 ✅ soft fail · §6 ✅ tests · §7 ✅ docs`

### Gap

| Current | Target |
|---------|--------|
| Blade matches as `.php` | builtin ignore `*.blade.php` |
| Only `.php` announced | `.php` + `.phtml` + `.module` + `.inc` |
| Encoding soft-fail may lack AC proof | Fixture asserts fail-visible (W1) |

### Gate 1

Standing approval clears Gate 1; W1 fail-visible ratified. **cleared.**

---

## Phase 2 — Design

### Approach

1. **Encoding (W1):** Keep soft-fail / no mojibake (already adapter+driver). Add an **indexer-level proving test**: plant non-UTF8 `.php` in a git tree → `full_build` → `files` row present, `parsed_ok=0`, `BuildReport.failed` / `get_index_status.parse_failures ≥ 1`. Fix only if that path is silently absent today.
2. **Blade:** Add `*.blade.php` to `BUILTIN_PATTERNS` (`ignore.py`). Update the exact-tuple guard in `test_ignore.py`. Fixture tree proves collect skips blade paths that would otherwise match as `.php`.
3. **Extra extensions:** Expand PHP handshake `extensions` to `['.php', '.phtml', '.module', '.inc']`. Update adapter README + `test_php_adapter_server` handshake assert. Proving: plant `.phtml`/`.module` with a class → indexed when announced; unit/fake-adapter proof that without the suffix in `owners`, collect omits them.

### Rejected alternatives

| Rejected | Why |
|----------|-----|
| Lossy latin1/iconv fallback into the graph | W1 + PLAN §4.1 never mojibake |
| Core hardcodes extra suffixes | Violates R1.1 / ticket Constraints |
| Blade handled in adapter (skip if path contains `.blade.`) | Language/path heuristic in adapter; ignore is the ticketed seam |
| Only document existing encoding soft-fail without indexer AC | Ticket AC requires asserted non-absence |

### Assumptions

| Assumption | Tag |
|------------|-----|
| `*.blade.php` matches via ignore glob subset (same as `*.log`) | verified (`test_ignore` glob-at-any-depth) |
| `PurePosixPath("a.blade.php").suffix == ".php"` so ignore is required | verified (FEEDBACK; Python pathlib) |
| Undecodable UTF-8 already soft-fails at adapter; indexer upserts `parsed_ok=0` | verified (adapter test + `_write`) — prove end-to-end |

### Change list

| # | Change | File | Ph2 rows | k/N |
|---|--------|------|----------|-----|
| 1 | builtin `*.blade.php` | `code_atlas/ignore.py` | R2,C3,AC2 | 1/1 |
| 2 | PHP extensions announce | `adapters/php/index.php` (+ README) | R3,C1,AC3 | 1/1 |
| 3 | proving tests (encoding + blade + ext) | `tests/test_legacy_hardening.py` (+ ignore/php handshake collateral) | AC1–3 | 1/1 |
| 4 | Docs | PLAN §11 builtins; BACKLOG/task | §7 | 1/1 |

**Blast-radius collateral:** `tests/test_ignore.py` exact `BUILTIN_PATTERNS` tuple; `tests/test_php_adapter_server.py` `extensions == (".php",)`.

### Verification plan

| AC | Risk layer | Proof | Match |
|----|------------|-------|-------|
| AC1 | integration | full_build non-UTF8 fixture → parse_failures | ✅ |
| AC2 | integration | blade on tree not collected / ignored | ✅ |
| AC3 | integration | .phtml/.module indexed after announce | ✅ |

**Proving test:** `tests/test_legacy_hardening.py::test_non_utf8_file_surfaces_in_parse_failures`
**Invocation:** `.venv/bin/pytest tests/test_legacy_hardening.py -q`

### Gate 2

Standing approval clears Gate 2. **cleared.**

---

## Phase 3 — Execute

- Branch: `feat/041-legacy-framework-hardening`
- Commits: `ce03a31` feat(041): harden legacy PHP trees — encoding signal, Blade ignore, extra extensions.
- Proving test: `tests/test_legacy_hardening.py::test_non_utf8_file_surfaces_in_parse_failures` ✅
- Suite: **753 passed**
- **Verification sweep:** file axis ⊆ list ✅ · behaviour axis implemented-as-approved ✅
- Deviations: none

## Phase 4 — Review

- reviewer: **LGTM** ([reviewer](6fc25343-4def-43c9-b961-f658fe664d5e))
- challenger: **9 met · 0 not met · 0 can't tell** ([challenger](f3a33aab-30f4-42bf-8ee2-b59825749fb3))
- Scope: ⊆ list ✅ · proving green ✅ · k=N ✅
- **Clean?** yes
- **Reviewed at:** `ce03a3143db7e93f5c286bfd1988446ed8a91baa` · reviewed files: full `main...HEAD` set; working doc `docs/tasks/041_legacy-framework-hardening.md` exempt for bookkeeping

## Phase 5 — Finalise (dry-run)

### Outward actions (each needs separate explicit yes)

| # | Action | Status |
|---|--------|--------|
| 1 | Push branch | ⏳ |
| 2 | Open PR | ⏳ |

## Session status

| Field | Value |
|-------|-------|
| Phase | 5 finalise dry-run — awaiting push/PR |
| Gates | 1 ✅ · 2 ✅ · review ✅ |
| Blocked on | push / PR |
