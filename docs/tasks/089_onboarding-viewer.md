---
id: 089
slug: onboarding-viewer
title: Onboarding — static HTML viewer (M11)
phase: 3
milestone: M11
status: done
depends_on: [088]
---

## Goal
A small, offline viewer so a human can read the onboarding artifact without a server or toolchain.

## Scope / Deliverables
- A single self-contained, theme-aware HTML file that reads `manifest.json` and renders layers, the
  tour, and per-module pages. No server, no external deps (CSP-safe: inline CSS/JS, no CDNs).
- Emitted as an optional output of `generate_onboarding` (088).

## Acceptance criteria
- Opens offline from the filesystem; fully self-contained.
- Renders the manifest's layers + tour + module pages; legible in light and dark.
- Deterministic output for identical input.

## References
[`../phase3-onboarding/PHASE3_ONBOARDING.md`](../phase3-onboarding/PHASE3_ONBOARDING.md) §4 (M11);
PLAN §14, §15 (M11).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 089 — Onboarding — static HTML viewer (M11) (working doc)

- **Ticket:** 089 · local file `docs/tasks/089_onboarding-viewer.md`
- **Type:** enhancement
- **Repo(s) / Porting:** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/N touched files under UI paths
- **TIER:** full
- **BASELINE:** green — `.venv/bin/pytest -q` → **1377 passed, 0 failed** (untouched `main` `ddb31b6`, 2026-08-18). baseline exclusions: none.
- **CHALLENGER:** OFF (`--no-challenger` / operator: skipped Review + Challenger)
- **REVIEW:** SKIPPED (operator argument). Do not reintroduce.

---

## Session status

- **Runner:** `/mango:solve 089 with skipped Review + Challenger`. Standing approval: suggest and take the best option, pass all gates; after the task, commit + push + open PR.
- **work_doc_mode:** embed. **Path:** `docs/tasks/089_onboarding-viewer.md` (below this separator).
- **Phase:** 5 finalise — review waived; proceeding to PR under standing approval.
- **Branch:** `feat/089-onboarding-viewer`.
- **Gate 0:** j = 0.
- **Gate 1 / Gate 2 / final gate:** cleared on standing approval.
- **Gate 4:** **waived** (REVIEW: SKIPPED, CHALLENGER: OFF).

---

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous | skip: yes`
`RECALL: 4 claim(s) | 0 by symbol | 3 by handle | 1 by area`
`REFINE: 0 unresolved | skip: yes`

**refine skipped: 0 unresolved product-decisions**

**Premise (all resolve):** 088 `generate_onboarding` + `manifest.json` (done, `ddb31b6`); PHASE3 §4 M11; PLAN §14/§15; R4.2; 088-C1 own-only write. To-be-created: viewer HTML.

**Skip rationale.** The ticket names one self-contained HTML file, theme-aware, no server/CDN, emitted by `generate_onboarding`. AC "opens offline from the filesystem" uniquely forces **embed at generate time** (`file://` cannot fetch `manifest.json`). "Optional" = 089's addition to 088's output, not a new flag or 18th tool. Exposure-checker does not run on skip.

**HANDLES:** count-pin-in-blast-radius (yes — +`viewer.py`); own-only-what-you-wrote (yes — `index.html` in refuse list, not rmtree); do-not-attest (yes — truncated banner); bound-the-recursion (does not apply).

**INPUT KIND:** ticket (single deliverable).

---

## Requirements matrix

`SECTIONS: 4 | ROWS: G=1 R=2 C=1 AC=3`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | A small, offline viewer so a human can read the onboarding artifact without a server or toolchain. | `docs/onboarding/index.html` written by `generate_onboarding`; opens via `file://`. | 088 writes markdown+manifest only. | change-list 1–2 | proving test | ✅ |
| R1 | Scope | A single self-contained, theme-aware HTML file that reads `manifest.json` and renders layers, the tour, and per-module pages. No server, no external deps (CSP-safe: inline CSS/JS, no CDNs). | Generator **embeds** the artifact (HOW: `file://` cannot fetch). `prefers-color-scheme`. Inline only; `connect-src 'none'`. | 088 `manifest_dict`. | change-list 1 | proving test: no http/cdn/fetch; payload has layers/stops/pages | ✅ |
| R2 | Scope | Emitted as an optional output of `generate_onboarding` (088). | Same tool, extra file. No 18th tool, no new MCP arg (YAGNI). | 17 tools on `main`. | change-list 2 | `VIEWER_NAME` in `results` | ✅ |
| C1 | implied / 088-C1 | Do not destroy files this tool did not write. | `index.html` joins `overview.md`/`tour.md` in `_refuse_foreign_tree`. | 088 `_refuse_foreign_tree`. | change-list 2 | `test_viewer_is_refused_when_the_tree_is_not_ours` | ✅ |
| AC1 | AC | Opens offline from the filesystem; fully self-contained. | No fetch, no CDN, payload in the file. | unbuilt | change-list 1 | proving test | ✅ |
| AC2 | AC | Renders the manifest's layers + tour + module pages; legible in light and dark. | Embedded payload + two tabs; `color-scheme` + `prefers-color-scheme`. | unbuilt | change-list 1 | proving test | ✅ |
| AC3 | AC | Deterministic output for identical input. | No timestamps; two runs byte-identical HTML. | R4.2 | change-list 1–2 | proving test second call | ✅ |

**Clarifications:** j = 0. **TIER: full.**

---

## Phase 2 — Design

**Approach.** New pure `onboarding/viewer.py` (`render_viewer` / `viewer_payload`). `generate_onboarding._write` adds `index.html`. Payload JSON in `<script type="application/json">` with `<` → `\u003c`. DOM APIs + `textContent` (no `innerHTML` of graph strings). Always emit (no flag).

**Rejected.** Runtime `fetch(manifest.json)` — fails on `file://`. New MCP tool — ticket says emit from 088. Theme-toggle JS — `prefers-color-scheme` meets AC. CDN/font — forbidden.

**Change list:** (1) `code_atlas/onboarding/viewer.py` (2) wire `_write` + refuse list + `VIEWER_NAME` on manifest (3) tests (4) docs + count-pin 50→51.

**Proving test:** `tests/test_onboarding_viewer.py::test_generate_onboarding_writes_a_self_contained_offline_viewer`. Fails pre (no `index.html`).

---

## Phase 3 — Execute

- **Branch:** `feat/089-onboarding-viewer` from `main` `ddb31b6`.
- **Deviation:** none.
- **Delta-green:** baseline **1377** → **1382 passed, 0 failed** (+5: 3 authored in `test_onboarding_viewer.py` + 2 per-module R1.1/SQL count-pin cases; none removed). `.venv/bin/ruff check code_atlas tests` clean. `.venv/bin/mypy code_atlas` → **51 source files**. Host `.venv/bin/pytest -q` (Linux + PHP) at feature commit `9ff28b4`. Token-usage / `done` bookkeeping is a follow-up commit; re-run the gate there (P4).

## Phase 4 — Review ✋ (waived)

- reviewer: **not run**. challenger: **OFF**. **Reviewed at:** n/a.

### Review round on PR #128 (maintainer asked for a direct review; 0 dispatch, in-session)

CI red for the same **four billing-blocked jobs** as #126/#127 — no job started. Gate proven in Docker.

The escaping in `render_viewer` is **correct**: a hostile repo path (`app/<img src=x onerror=alert(1)>.aa`)
round-trips into the payload as text and the page stays intact. What was missing was the *guard on the
guard*, plus two degradation gaps:

| # | Finding | Evidence | Fix |
|---|---------|----------|-----|
| 1 | The `<`-escape that stops a script-tag breakout had **no test** — deleting the line kept the suite green (13 passed). And the breakout is reachable: a directory `a<` holding `script>x.aa` makes the *path string* carry `</script>`, which ends the JSON block early and leaves the rest of the payload as live markup. The page's own CSP does not save it — `script-src 'unsafe-inline'` permits inline handlers and `img-src 'none'` guarantees an `<img onerror>` fires | mutant run: `</script>` count 2 → **5**, JSON block `Unterminated string`, `<img src=x onerror` literal in the file | `test_a_repo_path_cannot_break_out_of_the_payload_script_tag` — a fixture with that exact path shape, asserting the page has exactly the two template closers, no live `<img`, and the path still readable as data. Red on the mutant, green on the fix |
| 2 | Scripting off → **blank page**. Every element is built in JS, so the "offline viewer" showed nothing and never mentioned the markdown sitting beside it | opened the generated file with scripting disabled | `<noscript>` block pointing at `overview.md` / `tour.md`. Their own no-language pin caught the first wording ("inline JavaScript" → "the inline script") — the artifact must name no language |
| 3 | `<html>` carried no `lang`, so the AC's "legible" page declared no language to a screen reader | `'<html lang=' in html` → False | `<html lang="en">` |

**Delta-green after the fixes:** `1382 → 1384 passed, 0 failed` (+2 authored tests; none removed),
ruff clean, mypy **51 files**; confirmed in Docker (`scripts/docker-test.sh`).

Observations left as-is: the page grants `script-src 'unsafe-inline'`, which a sha256 hash of the
inline script could replace for defence-in-depth (the template is a constant, so the hash is
deterministic) — worth a ticket, not a review edit; and every module page's markdown is embedded a
second time inside `index.html`, bounded by the same tour budget as the pages themselves.

## Phase 5 — Finalise ✋

- Outward: push + open PR (`gh`). Tracker N/A.
- Durable lesson: 089-C1 embed-what-file-cannot-fetch. `seen:` on 085-C1, 088-C1 (own-only), 088-C2.
- Follow-up: 090.

### Learning loop

`CLAIMS: 1 | T2=1 | PROMOTION: 1 proposed (new handle, seen 1 — stays in lessons)`

| # | Claim | Type | Handle | Recurred? | Destination |
|---|-------|------|--------|-----------|-------------|
| 1 | 089-C1 | 2 | embed-what-file-cannot-fetch | 089 only | lessons (not yet 2 tickets) |

---

## Cost ledger

`COST-LEDGER: 0 dispatch row(s) | complete`

| phase | dispatch | round | tokens |
|-------|----------|-------|--------|
| (none) | — | — | unmeasured (host does not surface usage) |

