# 153 · 227 — HEURISTIC `CALLS` share on the TypeScript and Python samples

**Status:** run, pinned public samples, via `scripts/edge_health_report.py --only <sample>`.
**Tickets:** task 153 and task 227 (phase-1 archive). The README's TypeScript and Python rows quote
these outputs (R6.7); they moved here when phase 1's task files and token ledger left the repo.

## TypeScript — `ky`, 2026-08-27, after 153

```
before (promotion off): all edges=7781  HEURISTIC=4434 (57.0%)  unknown_receiver=4424
after  (promotion on) : all edges=7777  HEURISTIC=4209 (54.1%)  unknown_receiver=4199
```

225 member calls promoted HEURISTIC→RESOLVED (57.0% → 54.1%). The residual is dominated by
return-type-of-call (fluent-chain) receivers — the file-at-a-time limit, not a checker gap.

## Python — `flask` @ d318b683471101618febed18996405ad26462110, 2026-09-08, after 227

CALLS HEURISTIC **83.9% → 82.2%** (5908 → 5709, **−199**).
