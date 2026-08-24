---
id: 131
slug: tour-ranks-configuration-ahead-of-the-front-controller
title: guided_tour's first five stops are lint and bootstrap config, not the front controller
phase: 3
milestone: Quality
status: done
depends_on: [111, 121]
---

## Why this exists

This is **121**'s negative finding, and the one §5 promised to write down if the phase lost.

On the pinned `symfony/demo`, `guided_tour`'s first five stops are:

```
.php-cs-fixer.dist.php   config/bundles.php   config/preload.php   importmap.php   public/index.php
```

The hand answer to *"what are the first five things to read"* on a canonical layout is the front
controller, the kernel, a controller, an entity, and its repository. The tour gets **1 of 5**, and
spends the first four on lint and bootstrap configuration. A newcomer following it reads a code-style
config file first.

The mechanism is not a bug in the walk: roots are *"entry point (zero inbound)"*, ranked by out-degree,
and a lint config with zero inbound and zero outbound ties with everything else, so path order decides.
The walk is correct; the **claim** — a reading order — is what fails. 111 made the tour narrative
steps; nothing has asked whether the seed set deserves to be a reading order's first page.

Related but distinct: 108-117 fixed a 500-stop tour's *size*. This is its *ordering*.

## Scope

- Rank the seeds by something a reader would recognise: out-degree already exists but does not
  discriminate here; the responsibility layer of the root (110's vocabulary) does — `HTTP / Entry`
  before `Config / Migration`.
- A root with no outbound edge is not a place to start reading. Decide whether it is a seed at all.
- Derive the ordering from what the graph and the layer assignment already carry — no per-repo list of
  filenames to demote (R2.2), no framework knowledge in the core (R1.1).
- Prove it red first against a fixture holding a config file, a lint file and a front controller
  (R6.5), then re-measure `symfony/demo` and record the new first five in
  `docs/benchmarks/121_onboarding-question-class.md`.

## Acceptance criteria

1. **AC1.** On the pinned `symfony/demo`, the front controller appears in the tour's first five stops.
2. **AC2.** The ordering rule is derived from the layer/degree data already computed, with no repo,
   framework or filename literals added to the core.
3. **AC3.** A committed fixture asserts the rule and was observed failing before the change.
4. **AC4.** 121's finding #1 is struck, with the re-measured first five recorded in its place.

---

<!-- mango:working-doc -->

## Session status

- **Phase:** finalise (execute complete; review/challenger waived)
- **Branch:** `fix/131-tour-ranks-configuration-ahead-of-front-controller`
- **SCOPE:** M
- **TIER:** full
- **CHALLENGER:** OFF (--no-challenger; review waived by run args)
- **work_doc_mode:** embed

## Requirements matrix

| ID | Requirement | Validation | Ph3 | Ph4 |
|---|---|---|---|---|
| C1 | Ordering from graph + layer data; no filename/framework literals in core | `reading_seed_rank` + web-root segments only | ✅ | waived |
| R1 | Prefer roots that lead somewhere | `_tour_entry_seeds` out_degree > 0 | ✅ | waived |
| R2 | Layer-aware reading order among ready SCCs | `_ready_key` in `tour.py` | ✅ | waived |
| AC1 | Front controller in first five on symfony/demo | Remeasured: `public/index.php` is stop 4 | ✅ | waived |
| AC2 | No repo/framework/filename literals | vocabulary + web-root dirs | ✅ | waived |
| AC3 | Committed fixture asserts rule | `tour_reading_order/` + proving test | ✅ | waived |
| AC4 | Finding #1 struck with new first five | benchmark updated | ✅ | waived |

## Design (Gate 2 — standing approval)

**Approach:** (1) Entry seeds prefer out_degree > 0. (2) Kahn ready-set orders by proven entry, leads-somewhere, `reading_seed_rank`, out-degree, path. (3) `reading_seed_rank` sinks test paths and Config/Vendor; web-root dirs (`public`/`www`/`htdocs`) rank with HTTP / Entry for seeds only.

**Rejected:** Layer semantics inside `store.py` (R1.4, rejected in 106). Global vocabulary add of `public` (would pollute layer assignment).

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| execute | — | — | main-loop only |
| review | waived | — | — |
| challenger | waived | — | — |

## Decision log

- **D1:** Web-root directory names boost reading-seed rank only, not `responsibility_layer`.
- **D2:** Test-path any-segment check in `reading_seed_rank` (same family as 130).
- **D3 (review of #165):** vendor joins tests in the any-segment sink — under deepest-wins
  `vendor/x/lib/` read as `Shared Library` and could open a tour on third-party code, contradicting
  D2's own stated intent. `_SINK_SEED_LAYERS` is the one list; `_LATE_SEED_LAYERS` is now pinned
  against the vocabulary (R6.7), because a layer rename would otherwise silently reopen 131.
- **Test gap closed in the same review:** the original proving test passes with
  `reading_seed_rank` stubbed to a constant — its fixture's leads-somewhere term alone decides the
  order. `test_ac3_layer_rank_sinks_config_when_it_also_leads_somewhere` ties that term so only the
  rank can order, plus four unit tests on `reading_seed_rank` itself.
