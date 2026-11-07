---
id: 442
slug: validation-0-11
title: "0.11 validation: a 7-day control-vs-treatment run on the anchor decides what continues"
phase: 2
milestone: "0.11 Verify & Compute"
status: todo
depends_on: [437, 438, 439, 440, 441]
---

## Why this exists

Roadmap R4 (0.11). A precedence sentence in `CLAUDE.md` ("when this file conflicts with the code,
follow the code") already shifts agents toward the code once they notice a conflict (arXiv
2610.30571). `verify_refs` earns its place only if it gets conflicts **nobody noticed** fixed; `compute`
only if an agent picks it unprompted and it is cheaper. This run measures both against a control arm,
and its day-7 result decides 0.12 and 0.13. It starts when 437–441 are merged and gate-green; build
time does not count.

## Protocol

- **Day 0:** run `verify_refs` report-only and save the full finding list privately, outside both
  repos — agents never see it. The maintainer adds the precedence sentence to the anchor's
  `CLAUDE.md`. `verify_refs`, its SessionStart line and `compute` stay **off**.
- **Days 1–3 (control):** normal work. Day 3: re-run privately, diff against the baseline —
  `control_fix_rate` = baseline findings fixed ÷ baseline findings, per priority class.
- **Day 4 (static checks):** R1 precision ≥ 80% on 50 hand-checked `moved` + `gone` rows; ≥ 80% of 20
  `moved` patches correct; R3: 10 answers checked against hand counts or bounded grep, **zero** wrong
  for a missing caveat; p95 ≤ 3 s. A failed check stops that component; re-run only if the cause is a
  bug, not the design.
- **Days 4–7 (treatment):** tools on. Normal work plus 5–10 real tasks phrased without naming a tool:
  2–3 doc cleanups, 3–5 aggregate questions the maintainer needs. Measure `treatment_fix_rate`,
  unprompted choice per task, and tokens/time per aggregate question vs the control or the survey's
  "today" route.
- **Per-PR feedback**, both arms: the anchor's `code-atlas feedback` block gains `Stale doc hit:
  yes/no (class)`, `verify_refs: unprompted/prompted/not used — shown, fixed, patches applied N/M,
  wrong rows` and `compute: unprompted/prompted/not used — template, correct, calls replaced`. The two
  tool lines read `n/a` while off. Extra day-7 signal: stale-doc hits per PR in treatment ≤ half of
  control.

## Day-7 decision

| Component | Continue if | Stop if |
|---|---|---|
| R1 `verify_refs` | static checks passed, `treatment_fix_rate` ≥ 50% on findings surfaced in cleanup tasks, and ≥ 30 points above control | static checks failed, or < 10 points above control |
| R3 `compute` | static checks passed, chosen unprompted in ≥ 3 aggregate questions, ≥ 10× fewer tokens than the today route | static checks failed, or unprompted in < 2 |

A grey-zone result allows **one** 7-day extension, only near a threshold with a small sample.
Long-term adoption is logged, not gated. The decision goes to PLAN §19.

## Privacy (anchor runs — binding)

Structure, counts, ratios and timings only; placeholders for business identifiers; never quote anchor
docs; never connect to a database or read `.env`; business identifiers stay inside the anchor's own
PRs. Run the survey's privacy self-check before saving. Report:
`~/code-atlas-review/validation-0.11.md` — control, treatment and running total per priority class.

## After the decision (not ticketed until then)

0.12: R5 file-level history store feeding `compute` (if R3 continued); R6 typed output schemas and R7
a Roots-deprecation spike for `CallerRoots` (366, spec 2026-07-28) ship regardless. 0.13: R8
symbol-anchored notes, only if R1 continued and the maintainer has chosen where notes live. R9 README
first screen with test-held numbers once R1 or R3 passed. Distribution stays deferred.

## Acceptance

1. `validation-0.11.md` exists, passes the privacy self-check, and holds both arms per class.
2. A per-component continue / stop / extend decision is recorded in PLAN §19 with its numbers.
3. The 0.12 tickets are opened, or not, as that decision says.
