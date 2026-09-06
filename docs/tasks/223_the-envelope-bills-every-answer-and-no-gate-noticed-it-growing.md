---
id: 223
slug: the-envelope-bills-every-answer-and-no-gate-noticed-it-growing
title: 'The sample tokens-to-answer ratio fell 69.06 to 65.48 with the grep side byte-identical, every atlas payload growing +56…+94 tokens — an envelope-shaped, constant regression that CI cannot see because the gate floors only the fixture tier and `artifacts/` is gitignored, and the field named `unconfigured_adapters` riding 4 of 11 in-work payloads as one of the terms'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [042, 173, 160, 020]
---

## Why this exists

**The regression, measured 2026-09-06.** Two `scripts/tokens_to_answer.py --samples` runs over the
pinned public repos:

| | earlier run | later run |
|---|---:|---:|
| grep-and-read side | 441,650 tokens | **441,650 tokens — byte-identical** |
| ratio | **69.06×** | **65.48×** |

The denominator did not move, so the whole −5.2 % is on the atlas side, and it is **not**
question-shaped: every question grew, by **+56 to +94 tokens**, median ~+68. That is the profile of a
constant added to the envelope, not of an answer getting bigger.

**Why no gate caught it.** The tokens-to-answer gate floors the **fixture** tier (floor 0.63), not
the sample tier that carries the product claim; and `artifacts/` is gitignored, so no run is diffed
against the last. A number the README quotes has no regression gate at all.

**One term is already named, by the field rather than by us.** Round 14 measured
`unconfigured_adapters` riding **4 of its 11 in-work payloads** — `get_index_status`,
`search_symbol`, `find_references`, `find_callers` — carrying
`[{"language":"python","enable":"CA_PYTHON_CMD"}]`, ~20 tokens, unrequested, in a repo with **no
Python file on any critical path**. Their reading: *"the fourth adapter is charging rent on every
question in a repo that has no use for it."* 020 landing inside the regression window makes it
candidate #1 — **a hypothesis with a mechanism, not a diagnosis**; the other per-call constants
(`server_version`, `server_build`, `server_stale_process`, `index_root`) sit in the same envelope and
have not been audited either.

**And the cheapest tier has the economy backwards.** `get_index_status` at
`detail_level: "minimal"` **drops `server_version`, `server_build` and `server_stale_process`** — the
three fields the retro protocol exists to check — while **keeping `next_tool_suggestions: []`**, a
field the field agent read zero times all session.

## Scope

1. **Attribute the +68, field by field.** Bisect the atlas payload across the window, not the commit
   log: diff the recorded payloads of two runs and name which keys account for the delta. The answer
   is a list of fields with token counts, not a commit.
2. **Decide each named field on its evidence**, one of: keep (it earns its tokens), demote to a
   `detail_level` that asks for it, or gate it on the answer being low-confidence — the discipline
   160/173 already wrote down and which `get_index_status` does **not** follow (it attaches
   unconditionally at `standard`, `get_index_status.py:207` and `:289`).
3. **Fix the `minimal` inversion.** The cheapest tier must keep the identity fields and drop the
   empty array, not the reverse.
4. **Give the sample tier a regression gate.** A ratio the README quotes must fail CI when it falls.
   Pin the last measured value with a tolerance, or record the run so two runs can be diffed — the
   current state is that neither is possible.

**Not in scope:** removing the Python adapter (020/217 shipped; the finding is about what its
*absence of configuration* costs a payload); the `parse_failure_paths` dump and the eight never-read
fields (Notes — same subject, separable work).

## Acceptance criteria

- **AC1** The +56…+94 delta is attributed to named fields with a token count each, summing to within
  ~10 % of the measured gap. *"Probably the envelope"* is not an attribution.
- **AC2** The sample-tier ratio is measurably recovered, **or** each field's tokens are justified in
  writing and the ratio's new floor is recorded as intentional. Either close is acceptable; an
  unexplained ratio is not.
- **AC3** A gate exists that fails when the **sample** ratio falls below its recorded value.
  **R6.5: prove it fails** — run it against the 65.48 state with the floor set at 69.06 and show red.
- **AC4** `minimal` carries `server_version` / `server_build` / `server_stale_process`; an empty
  `next_tool_suggestions` is omitted rather than shipped.
- **AC5** No answer loses a field that a documented protocol depends on. R-23's process-identity check
  and 214's `reason` / `try_instead_hint` are both load-bearing and stay.

## Exclusions

- **E1** The sample tier needs the pinned public repos and a rebuild; stale cached sample DBs raise
  `SchemaVersionError` after a schema bump — clear `artifacts/tokens-to-answer-samples/*.db` before
  measuring, and say which corpus state produced each row.

## Notes

Two smaller findings from the same round, same subject, deliberately not in the ACs so this ticket
stays measurable:

- **`get_index_status` at `verbose` returns all 34 `parse_failure_paths`** — every one a vendored
  legacy PDF/barcode/Excel library, zero app code, zero actionable. A `parse_failures_by_top_dir`
  rollup carries the same signal in one line.
- **Fields read zero times across a whole field session:** `orphans_max_nodes`, `config_build`,
  `config_stale_process`, `index_config_build` (three build-identity fields, none used — the agent
  used `server_build` plus a `/proc` scan), `next_tool_suggestions`, `stubs`, `claimed_suffixes`,
  `dir_symbol_threshold`.

And the one field that earned every token, recorded so no audit strips it: `sign: true` → `claim`.
*"It is the only field in the surface designed to be cited rather than read, and it is the one I
would protect first."*
