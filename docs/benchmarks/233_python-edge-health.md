# 233 — Python edge-health baseline (before further type-table work)

**Status:** run, pinned public Python samples, 2026-09-08 (Linux host `dev-host`).
**Ticket:** task 233 (phase-1 archive).
**Protocol:** same columns as [137](137_type-table.md) / `scripts/edge_health_report.py --only <id>`.
**Verdict:** this is the **before** 227/229/230 measure against. Flask already carries 227's local type table; pydantic and requests are the shapes those tickets cannot move without this pin.

```bash
python scripts/edge_health_report.py --only flask
python scripts/edge_health_report.py --only pydantic
python scripts/edge_health_report.py --only requests
```

## flask @ `d318b68` (decorator-heavy framework)

Its manifest floors **drop** (1544n/8942e → 1406n/8635e). 227's note recorded the smoke at
83f/1931n/11178e; that number does not reproduce. Re-built twice at the same pin — once against
227's own merge commit `2835273`, once against `e092835` — and both give **83f/1758n/10794e**,
byte-identical node histograms. The old floor was slack over an unreproducible figure, not a
regression this ticket is pinning as the baseline.


| metric | value |
|---|---|
| all edges | 10 794 |
| HEURISTIC | **5 707 (52.9%)** |
| linked / unlinked | 5 491 / 5 303 |
| unknown_receiver | 5 033 (88.2%) |
| inherited_or_trait_receiver | 674 (11.8%) |
| local-type-info share of HEURISTIC | 5 707/5 707 (100%) |
| of those, target INDEXED | 4 600/5 707 (80.6% of HEURISTIC, 42.6% of all edges) |

## pydantic @ `2261ae1` (`src/`-layout)

| metric | value |
|---|---|
| all edges | 90 199 |
| HEURISTIC | **30 844 (34.2%)** |
| local-type-info share of HEURISTIC | ~100% |
| of those, target INDEXED | 22 320/30 844 (72.4% of HEURISTIC, 24.7% of all edges) |

## requests @ `dae7ef6` (flat package + deep member calls)

| metric | value |
|---|---|
| all edges | 5 220 |
| HEURISTIC | **2 095 (40.1%)** |
| local-type-info share of HEURISTIC | ~99.9% |
| of those, target INDEXED | 1 362/2 095 (65.0% of HEURISTIC, 26.1% of all edges) |

