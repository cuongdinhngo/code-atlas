---
id: 162
slug: a-build-swap-is-invisible-on-every-payload-but-get-index-status
title: 'A build swap is invisible on every payload but get_index_status — carry a cheap server_build stamp, without forcing the signing git read onto the hot path'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [125, 077, 100]
---

## Why this exists (field retro rounds 8–9, 2026-08-25/26)

Task 125 put `server_version` / `server_build` on `get_index_status`, and the retros confirm it works —
but only there. Every other answer is still unattributable to a binary, and both rounds hit the cost:

> Round 8 (**8-D** / 7-G): the server build was swapped mid-session (`6a8ae85` → `cec2938`), the only
> signal a bare `Connection closed`. *"Every cross-boundary regression verdict in a session is void,
> silently."*
>
> Round 9 (**9-D**): *"I know the build did not change only because I sampled twice by hand."* `sign`
> already carries `build=cec2938`, but it is opt-in and off, so the **default** answer stays
> unattributable.

The project's evaluation loop is its most valuable instrument (the reasoning that justified 125). A
regression verdict that cannot name which binary produced each answer is not reproducible.

## Root cause, and why the retro's proposed fix is the wrong size

The retro's headline fix was *"flip `sign: true` to default on every tool."* That is more expensive
than it looks:

- The full signed line needs `revision_fields()` (`claim.py:59-78`), which needs a staleness dict,
  which needs `compute_staleness()` — **a git HEAD read plus a dirty scan per call**
  (`staleness.py:63-73`). `impact.py:91` guards `compute_staleness` behind `sign=True` **precisely so
  the hot path pays no git**. Flipping the default would put a git read on every mechanism answer,
  against 061 / the cheap-path discipline.

But the build id itself is cheap:

- `server_identity()` is `@lru_cache(maxsize=1)` and touches git **only on the first call of the
  process** (`build_info.py:62-66`); every later call is a dict lookup. `server_fields()`
  (`claim.py:81-84`) is therefore ~free after warm-up.

So the fix is to carry the **cheap** half (`server_build`) always, and leave the **expensive** half
(the revision-bearing `claim` line) opt-in.

## Scope

- **Stamp `server_build` (and `server_version`) on the payload of the read/nav/mechanism tools**, drawn
  from the lru-cached `server_identity()` — no git on the hot path. This closes 8-D/7-G: a build swap
  becomes visible on any answer, not only on a `get_index_status` call.
- **Do not flip `sign` default.** The full `claim` line stays opt-in; this ticket adds only the build
  identity, not the revision fields that cost a git read.
- **Reuse `get_index_status`'s existing shape** (`get_index_status.py:105`, `_server_fields`) as the one
  source, so two tools do not spell the field differently.
- **Measure the byte cost** and record it (061): the field is ~2 short strings; confirm `minimal` and
  the common answer grow only by that.

### Explicitly not in scope

- Making the revision (`rev`/`ref`/`index`) ride the default payload — that needs the git read `sign`
  guards, and is a separate cost decision.
- 9-E (`dirty_indexed_files`): assessed as a **non-finding** — the field measures uncommitted
  working-tree drift by design (047); after the retro's files were committed, `0` was correct and the
  index-vs-disk drift was reported by `staleness: behind`. No change.

## Constraints

- **061 / R7.1** — additive; the increment is one build id, measured, not a git read.
- **R4.2** — deterministic: `server_identity()` is a pure function of the installed artifact (no
  timestamps), already asserted by 125's tests.
- **R4.1 / R1.4** — the stamp is a formatter read of package identity; it opens no store and, after the
  cache is warm, spawns no git. No language branch (R1.1).
- **R3** — `server_build` is a tool-payload field, not contract vocabulary; no `contract_version` bump.

## Acceptance criteria

1. The default (`sign=false`, `standard`) payload of the read/nav/mechanism tools carries
   `server_build` (and `server_version`), pinned by a test; two builds of the same version are
   distinguishable from any such payload alone.
2. No new git subprocess is spawned on the hot path — proven, e.g. by asserting `server_identity` is
   consulted from cache and `compute_staleness` is **not** called when `sign=false` (contrast
   `impact.py:91`).
3. The field spelling matches `get_index_status`'s existing `server_build` / `server_version` exactly
   (one source of truth).
4. The byte growth on `minimal` / the common answer is measured and stated (061).
5. Determinism holds (R4.2); the R1.1 grep-gate stays green.

## References

Field retro rounds 8–9, findings **8-D** / **7-G** (build swap invisible) and **9-D** (sign is opt-in,
so the default is unattributable). `code_atlas/build_info.py:62-66` (`server_identity`, lru-cached),
`code_atlas/tools/claim.py:59-84` (`revision_fields` needs staleness; `server_fields` is cheap),
`code_atlas/tools/staleness.py:63-73` (the git read `sign` guards), `code_atlas/tools/impact.py:91`
(the guard this ticket must not undo), `code_atlas/tools/get_index_status.py:105` (`_server_fields`,
the source of truth). Builds on [125](125_no-payload-names-the-server-build.md),
[100](100_claim-signing-output-mode.md) (the opt-in claim line), [077](077_index-cannot-name-the-revision-it-describes.md).

---
MANGO WORKING DOC (below this line is NOT part of the raw ticket)

## Session status
- Phase: finalise (complete). TIER: full. SCOPE: S. CHALLENGER: ON.
- work_doc_mode: embed (plain local-file ticket).
- Reviewed at: challenger-only (reviewer waived by run args "skipped review and challenger"→challenger ON, reviewer OFF).

## refine
PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)
RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)
REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes

## analysis
CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision
RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §R1.1 (rulebook) ✅, §R3 (rulebook) ✅, §R4.2 (rulebook) ✅, §061 (task) ✅, §R7.1 (rulebook) ✅
SECTIONS: 3 found (Scope, Constraints, Acceptance criteria) | 3 decomposed | ROWS: C=4 R=4 G=1 AC=5

## design
One source of truth: `build_info.server_provenance()` returns `{server_version, server_build}` from the
lru-cached `server_identity()`; `get_index_status` now delegates to it (same spelling). Stamped on the
Pillar-1 read/nav/mechanism payload builders: `nav_result`/`empty_nav`/`list_result`/`batch_result`/
`batch_not_indexed`, `read_symbol`, `file_outline`, `explain_path`, `impact_modules`,
`subtree_dependencies`, and `reach_shared.no_roots()` — never per-subject (061). The revision-bearing
`claim` line stays sign-gated (no git on the hot path).

EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor
HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (n/a) | 0 unanswered

- **Scope boundary (not a coverage exclusion):** the six Pillar-2 onboarding/rendering tools (`architecture_overview`,
  `guided_tour`, `generate_onboarding`, `check_architecture_rules`, `diff_architecture`,
  `class_diagram`) are **not** stamped. The ticket scopes to "read/nav/**mechanism** tools" = Pillar 1
  in this repo's two-pillar vocabulary (AGENTS.md); Pillar-2 artifacts are committable and must stay
  build-independent (R4.2), so a per-build stamp does not belong on that surface. Session-level build
  attribution for those answers is available from `get_index_status`.

## execute
No design-invalidated escalation; no stuck-detector trips. All ACs met (AC4 added a measured,
test-pinned byte bound after the challenger flagged it missing).

## review (challenger-only — reviewer waived)
CHALLENGER: ON. Ticket-blind challenger reconstructed the 5 ACs + constraints from the raw ticket.
Verdict on the final tree: AC2/AC3/AC5 MET; AC1 MET after `reach_shared.no_roots()` was stamped in
response; AC4 MET after a measured byte-bound test was added. The challenger's "6 onboarding tools
unstamped" is dispositioned as the recorded design Exclusion (Pillar-2 ≠ mechanism). No contract bump,
no sign-flip, no scope creep. Result: clean (reviewer only — CHALLENGER: ON).

### Cost-ledger
| phase | dispatch | round | tokens |
|---|---|---|---|
| review | challenger (ticket-blind) | 1 | 78,854 |

main-loop: unmeasured (host surfaces no usage block).

## finalise
Delta-green in Docker (`scripts/docker-test.sh`, linux): pytest 2079 passed / 1 skipped / 0 failed;
`scripts/gate.sh` in-container — ruff · mypy · pytest · tokens-to-answer (ratio ≥ 0.63) · R1.1/R2.2/R4.1
grep-gates · php -l · composer validate all PASS; phpstan `[OK] No errors` (dev deps installed);
doc-size budget restored (BACKLOG 9496/9500, PLAN 24000/24000).

CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified
FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)
RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)
RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (none) | 0 left in lessons_path
PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0
LEDGER TOTAL: 78854 · top cost driver: review/challenger
