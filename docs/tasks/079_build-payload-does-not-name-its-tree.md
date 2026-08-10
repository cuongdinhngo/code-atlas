---
id: 079
slug: build-payload-does-not-name-its-tree
title: '`build_or_update_index` is the one payload with no `index_root` — and building is when the tree matters most'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [071, 060]
---

## Goal
071 added `index_root` so an answer names the tree it describes. Round 4 verified it on **8 of 8**
distinct nav payloads and found it **absent on all 4** `build_or_update_index` payloads, which carry
`db_path` instead. A build is a *write*, and the question "which tree am I writing about?" is more
consequential there than on any read: a parallel agent that builds from the wrong cwd corrupts the
index every later answer is drawn from.

## Evidence (field retro round 4, 2026-08-10, §0.a / §A.7 / §11 item 4)
- `index_root` present on `get_index_status`, `search_symbol`, `file_outline`, `read_symbol`,
  `find_callers`, `find_references`, `find_view_data` — every nav payload the session touched.
- Absent on 4 of 4 `build_or_update_index` calls, which instead carry `db_path` — the field 061
  deliberately stripped from nav payloads, so the build path is now the *only* place `db_path` still
  appears and the *only* place the source root does not.
- The evaluator, who was in the main checkout, could confirm the match by hand; the three agents it
  dispatched each ran in a `.worktrees/<slug>` where it would **not** have matched. The retro records
  that the mitigation was a hand-written warning in each agent's prompt.
- Round 4 also used `index_root` as its **process fingerprint** (§0.a): a payload without it proves a
  server older than the 071 batch. The build tool cannot serve that check today.

## Scope / Deliverables
- **Attach `index_root` to every `build_or_update_index` payload** — success, `busy` refusal, and every
  refusal path (no adapter, empty suffixes, schema mismatch), so the field is a reliable fingerprint
  rather than a per-branch accident.
- **Decide `db_path`'s fate on this payload.** 061 removed it from nav answers as dead weight; on a
  build it is arguably the one place it earns its bytes (an operator setting `CA_DB_PATH` for
  isolation reads it there). Keep or drop with a stated reason — do not leave it as the accident it is
  today.
- **Sweep for the remaining payload shapes.** Enumerate every tool response and state, per shape,
  whether it carries `index_root`; the audit is the deliverable, not just the two-line fix.
- **Fold in [077](077_index-cannot-name-the-revision-it-describes.md)'s field if that lands first** —
  a build payload that names the directory but not the revision only half-answers the question.

## Constraints
- R4 — same input, same payload; the field is read from config, not derived per call (071 collapsed 38
  re-derivations into `Config.index_root` — do not reintroduce one).
- 060 — the build payload's field names are load-bearing (`wrote` vs `graph`); add beside them without
  disturbing either group.
- R5.3 — a refusal path must not be able to raise while attaching the field.
- 061 — no field that means nothing; `index_root` always means something.

## Acceptance criteria
- All `build_or_update_index` outcomes (full, incremental, no-op, `busy`, each refusal) carry
  `index_root`; a test enumerates the outcomes rather than sampling one.
- A recorded, tested verdict on `db_path` on this payload.
- An audit table in the ticket or plan listing every payload shape and whether it names its tree, with
  no "unknown" rows.

## References
Field retro round 4 §0.a (fingerprint use), §A.7 (verified nav / absent on build), §11 item 4.
Related: [071](071_answers-do-not-name-their-tree.md) (the field and its `Config.index_root` source),
[061](061_payload-weight.md) (why `db_path` left the nav payloads),
[060](060_build-report-scale-naming.md) (the build payload's field groups),
[064](064_build-without-adapter-silent.md) (the refusal paths this must also cover),
[077](077_index-cannot-name-the-revision-it-describes.md) (the revision half).
