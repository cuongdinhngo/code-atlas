# 074 — Does the index harm mechanism (control-flow) questions? — pre-registered protocol

**Status:** **protocol refreshed 2026-09-19 — still no verdict.** The 2026-08-27 abort (below)
stands. A new run must measure the **post-265 product** (this file's "Product under test"), and the
two rules that abort earned are now executable rather than advisory: `scripts/arm_preflight.py`
([Arm preflight](#arm-preflight--the-granted-arm-is-proven-not-assumed-r1--abort-finding-3)) and the
[key freeze procedure](#the-key--freeze-procedure-r1-step-2--abort-finding-2). Pre-registered
consequences are unchanged. **Ticket:**
[`../tasks/074_does-the-index-harm-mechanism-questions.md`](../tasks/074_does-the-index-harm-mechanism-questions.md).

This file is committed **before any run** so the result cannot be argued after the fact. It measures
**agent behaviour**, not server determinism — a granted-vs-denied difference here is not an R4 defect
(say so in the write-up). Nothing repo-identifying from the anchor repo enters this file: question
*shape*, verdicts, and aggregate counts only.

## Product under test (2026-09-18)

The August payload is gone. A cell that does not record the following is not comparable to this
ticket:

| Must be true / recorded | Why |
|---|---|
| Arm preflight passes — see [Arm preflight](#arm-preflight--the-granted-arm-is-proven-not-assumed-r1--abort-finding-3) | 2026-08-27 abort: 0 index calls in 68 |
| `staleness: current`, `dirty_indexed_files: 0`, `server_build` — `arm_preflight.py audit` prints all three from the cell | answers must be this binary |
| Default **24-tool** surface (`CA_TOOLS` unset). Six-tool preset is opt-in — if used, say so | [268](../tasks/268_twenty-four-descriptions-are-a-tax-paid-before-the-first-question.md) |
| Indexed-repo five-occasion brief **present or absent** (266). Experimenter still does not hint | the brief is product, not coaching |
| Key frozen per [The key](#the-key--freeze-procedure-r1-step-2--abort-finding-2) — dynamically probed, hashed, git-timestamped | the aborted key was falsified |

Shipped since the abort that can change a mechanism cell (do not assume 067 still dominates):
tier-first inbound pages (265), honesty empty-inbound (264), `production_count` / `exclude_tests`
(262), test-only partition not `ok` (272), `behind_refuses` (274), Table `WRITES` via
`find_references` (278).

## The question

One **mechanism (control-flow) question** — the shape *"how does X reach Y"* / *"what happens when Z
fires"* / *"what actually drives this behaviour"* — with **no file, class, or method named** in the
prompt. Reuse the **exact** mechanism question from the original 2026-08-08 founding-premise benchmark
(private notes); do not reword it. Establish its **ground-truth cause by hand first**, written down
before any session runs.

## Arms (two only — C2)

| Arm | Configuration |
|---|---|
| **granted** | code-atlas MCP server registered, **schemas callable**, index current — today's install (see Product under test). |
| **denied**  | native tools only — code-atlas absent (server not registered, or `CA_TOOLS=""`). |

No resident-LSP arm: it scored 0 invocations in 84 calls in the original run — there is no
answer-quality comparison to be had.

## Protocol (R1)

1. Freeze the key first — the five steps in [The key](#the-key--freeze-procedure-r1-step-2--abort-finding-2),
   not a paragraph written the morning of the run.
2. For **each arm**, run **n ≥ 3** cells. Each cell is a **fresh headless session**, **identical
   prompt**, **no experimenter coaching**, no reuse of a prior session's context.
3. Keep the index fresh for the granted arm exactly as a normal session would (build once before
   dispatch; do not hand-feed tool calls). Pass the [preflight](#arm-preflight--the-granted-arm-is-proven-not-assumed-r1--abort-finding-3)
   before the first granted cell, and save every cell's transcript (`--output-format stream-json`)
   so `audit` can rule on it afterwards.
4. Record per cell: the answer's **stated cause**, the **verdict** (rubric below), token count
   (secondary), and — for every wrong/partial **granted** cell — the **mechanism capture** below.
5. Extend to a **second** mechanism-shaped question **only if the first replicates** (R5). One
   question at n ≥ 3 beats five at n = 1.

## Arm preflight — the granted arm is proven, not assumed (R1 / abort finding 3)

`scripts/arm_preflight.py` is the gate. No cell is believable until it passes.

```
# once, before the first counted granted cell — a throwaway coached session
python scripts/arm_preflight.py probe --mcp-config granted.json --repo <anchor> --save probe.jsonl

# the one that gates the spend — an ordinary question, no coaching
python scripts/arm_preflight.py probe --uncoached --mcp-config granted.json --repo <anchor> --save reach.jsonl

# a held-out question — the same uncoached run, in wording the product has not seen (300)
python scripts/arm_preflight.py probe --question-file q.txt --mcp-config granted.json --repo <anchor>

# after every counted cell, both arms
python scripts/arm_preflight.py audit cell-N.jsonl --arm granted
```

`probe` is a **delivery** test, not a cell: it names the tool and permits `ToolSearch`, which is
coaching and would void a real cell. It answers one question — can a code-atlas tool be called at
all from this config — for a fraction of a cell's $5.58. `probe --uncoached` answers the other
half: asked an ordinary navigation question, with no tool named and no escape hatch offered, does
the session reach the index on its own? That is the arm the benchmark actually buys.

| Exit | Coached `probe` | `probe --uncoached` |
|---|---|---|
| 0 | schemas resident; the first index call needed no `ToolSearch` | the arm was reached with no prompting — the run may proceed, recording *how* it was reached |
| 1 | **deferred delivery** — `ToolSearch` had to load the schemas | not produced: reaching the tools unprompted is the pass, however it happened |
| 2 | no code-atlas tool reachable at all | **0 index calls unprompted — there is no granted arm to buy** |

Run the coached probe first: it is cheap and it separates "cannot be called" from "was not chosen".
**`--uncoached` is the one that gates the spend**, because a cell is uncoached by definition. A
coached exit 1 is a fact to record, not by itself a reason to stop — 2026-09-19 found a host where
coached probes reported deferred delivery while the session header listed every tool as present.

**`--question-file` is `--uncoached` on a question of your choosing**, reporting the question's
sha256 and never its text, so it stays outside the tree. Use it: REACH_PROMPT's sentence is now a
`which_tool` line, so passing *it* no longer separates "the brief covers this shape" from "the brief
contains this string" ([300](../tasks/300_the-index-is-registered-permitted-and-never-chosen.md) holds
the register). The 074 frozen question is itself a held-out question — point `--question-file` at the
private notes file and no text enters this repo.

`audit` applies the two arm rules to a counted cell's saved transcript:

- **a granted cell with 0 index calls is `void`, not a datapoint** — without this rule, n ≥ 3 buys
  six native-tools sessions and calls one of them an arm;
- **a denied cell with any index call is contaminated** — the arms leaked.

It also prints `server_build` / `server_version` / `staleness` out of the cell's own
`get_index_status` payload, so the Product-under-test rows are recorded from the run rather than
retyped from memory. Held by `tests/test_arm_preflight.py`.

### If the probe says 1 — the three candidates, cheapest first

Exit 1 is where the run stands on 2026-09-19. Each candidate is one `probe`, so the whole triage
costs a fraction of one cell. Record the exit code for each; a negative result is a finding.

| # | Hypothesis | Probe variant |
|---|---|---|
| 1 | Deferral is driven by the **session's total** tool count, not code-atlas's 24 — the 2026-09-19 probe saw `total_deferred_tools: 41` against a 24-tool server | re-probe with `--allowed-tools` cut to `mcp__code-atlas__get_index_status` alone (no `ToolSearch`): if a code-atlas call lands, the surface was never the cause |
| 2 | The 24-tool surface is itself over the threshold | set `CA_TOOLS` to the six-name [268](../tasks/268_twenty-four-descriptions-are-a-tax-paid-before-the-first-question.md) keep-list (`main.FIELD18_TOOLS`) in the granted config's `env`, re-probe |
| 3 | Delivery is a client-version behaviour | re-probe on a different CLI build, same config |

**Candidate 2 changes what the ticket measures, and that is not a free move.** Scope pins the granted
arm to the default 24-tool surface with the 268 preset opt-in. If only `CA_TOOLS` reaches exit 0, the
honest reading is that the shipped default does not deliver its tools to an uncoached session — a
product finding that belongs to 268/200, not a verdict on the index — and a run on the six-tool
surface must say on every row that it measured the preset, not the default.

## The key — freeze procedure (R1 step 2 / abort finding 2)

The 2026-08-27 key asserted *no live cause in this tree* and was falsified by the one cell it was
meant to score: the cell reproduced the fatal and named a mechanism the key did not contain. Scored
mechanically that cell reads `wrong-cause`; in truth it was more correct than the key. A key that can
do that to a run is not a scoring instrument, so freezing one has steps.

1. **Write** the cause as one paragraph, before any session runs.
2. **Classify it.** A *presence* key names a live cause; an **absence** key asserts that no live path
   reaches the failure. The absence key is the one that failed.
3. **Probe it dynamically.** Reading the guards that closed a defect does not establish that no other
   shape reaches the same failure. Execute the live path with the triggering input — runtime, not
   review — and record what was *observed*, not what should happen. An absence key with no dynamic
   probe is not frozen, and the run does not start.
4. **Commit the card**, so git timestamps it before the cells. C1 keeps the anchor repo out of this
   file, so what is committed is the shape plus a commitment to the text:

   | Field | Value |
   |---|---|
   | Key class | `presence` / `absence` |
   | `sha256` of the frozen key text | `<hex>` — `sha256sum key.txt` in the private notes |
   | Dynamic probe | what was executed, with what input (shape only) |
   | Observed | what the probe actually did |
   | Anchor tree | commit sha at freeze time |

5. **Re-freeze if the tree moves.** A cell run against a different anchor commit than the key records
   is not scored against that key.

**Falsification rule.** If a counted cell names a mechanism the key does not contain *and that
mechanism reproduces under step 3*, **the key is wrong, not the cell.** Stop the run; every cell
already scored against the old key is `void`, not data; freeze a new card (new hash, new timestamp)
and record the falsification below. Without this rule an honest cell is indistinguishable from a
`wrong-cause` tally — which is precisely what 2026-08-27 could not resolve.

## Scoring rubric (R2 — cause-correctness decides; tokens do not, per 055)

| Verdict | Meaning |
|---|---|
| `correct` | The answer's stated cause matches the hand-established ground-truth cause. |
| `partial` | Right region, incomplete or hedged cause; would mislead a reader acting on it. |
| `wrong-cause` | Confident wrong cause (the failure this ticket exists to catch). |

Tokens are recorded but **must not decide the verdict** — 055 established the cost metric cannot see
the worst failures. Report the arm verdict as the count of `correct` / `partial` / `wrong-cause`
across its n cells.

## Mechanism capture (R3/AC2 — required for every wrong or partial granted cell)

For each such cell, record:

- **Preceding tool call:** the code-atlas call that immediately preceded the wrong turn (tool + the
  answer's shape, not repo-identifying content).
- **Payload classification (pick one):**
  - `correct-but-unrepresentative` — the 067 shape: a correct but partial page that terminated the
    reasoning which would have reached the truth. *Less likely after 265; still legal.*
  - `confidently-empty` — the 065 shape: empty / `no_matches` / `ok` with `production_count: 0`
    read as proof of absence.
  - `false-zero-ok` — `reason: ok`, some callers (often tests), live production callers dropped
    (untyped dispatch). Field 20.
  - `wrong-chain` — resolved callers of a *related* path; the cause lives on an unmodelled path
    (e.g. SQL proc/trigger while PHP `generate` looked perfect).
  - `correct-code-wrong-inference` — the index proved the code is fine; the agent inferred the
    wrong non-code cause (seed, data, "must be the other region").
  - `dispatch-mismatch` — `read_symbol` (or callers) of a symbol that is not what the URL/runtime
    actually runs (legacy twin, include order).
  - `ignored` — the payload was correct and the agent did not use it.
  - `other` — describe.
- Or, explicitly: **"mechanism not identified"** — a verdict without a mechanism is not actionable,
  so this must be a deliberate, recorded choice, never a blank.

## Pre-registered consequences (R4/AC1 — committed before the runs)

| Outcome | Pre-committed consequence |
|---|---|
| **granted ≈ denied** | The original cell was session variance. **Delete** the "Threats" repeat from PLAN §19 and stop spending on it. |
| **granted worse, mechanism identified** | The mechanism becomes a ticket; the named tool's **description or ordering changes** (067 is likely already that ticket). PLAN §19 records the resolved mechanism. |
| **granted worse, no mechanism** | **Narrow the recommended scope in writing**: PLAN §19 **and** the README state which question types the index is for and which to keep it out of. Scope narrowing is an acceptable, expected outcome. |

"granted worse" means the granted arm produces materially more `partial`/`wrong-cause` verdicts than
the denied arm across the n cells; "≈" means the arms' verdict distributions do not differ in a way
that survives n ≥ 3 (no consistent granted disadvantage on cause-correctness).

## Results — to be filled from the maintainer's runs (paste back, then I score)

Ground-truth cause (frozen before runs): _<one paragraph, non-identifying>_

Key card (filled at freeze time, per [The key](#the-key--freeze-procedure-r1-step-2--abort-finding-2)): _<class · sha256 · probe · observed · anchor sha>_

| Cell | Arm | `audit` | Verdict | Stated cause (shape) | Preceding tool call | Payload class | Tokens |
|---|---|---|---|---|---|---|---|
| 1 | granted | | | | | | |
| 2 | granted | | | | | | |
| 3 | granted | | | | | | |
| 4 | denied | | | | | | |
| 5 | denied | | | | | | |
| 6 | denied | | | | | | |

The `audit` column is `scripts/arm_preflight.py audit`'s verdict for that cell. A `void` or
`CONTAMINATED` cell does not enter the tally and does not count toward n.

**Arm tallies:** granted `_c / _p / _w` · denied `_c / _p / _w`.
**Selected outcome (from the pre-registered table):** _<one of the three>_.
**Mechanism (if granted worse):** _<named, or "not identified">_.

Once these rows are filled, the analysis turn applies the selected pre-registered consequence: edits
PLAN §19 (delete the threat, or replace it with the resolved mechanism / a scope statement) and the
README value claim **in the same change** (AC3/AC4), and records whether R5's second question is
warranted. **This never happened — see below.**

## Preflight findings — 2026-09-19. Delivery is not the blocker; selection is

Two rounds of probes, none of them a benchmark cell and none a measurement of the anchor's code.
The second round **corrects the first**, which is why the first is not restated as fact.

**Round 1 — the delivery triage, on the anchor (maintainer).** Four coached probes, all exit **1**.
Each falsifies one candidate:

| Probe | Exit | Session tools / deferred / code-atlas | What it rules out |
|---|---|---|---|
| B — default surface | 1 | 52 / 41 / 24 | — (baseline) |
| V1 — `ToolSearch` withheld from `--allowed-tools` | 1 | 52 / 41 / 24 | the probe's own allow-list: the client permits `ToolSearch` regardless |
| V2 — `CA_TOOLS` cut to the six-name 268 keep-list | 1 | 34 / 23 / 6 | **the server's surface.** 24 → 6 still defers; deferral tracks the *session* total, which code-atlas does not control |
| V3 — client 2.1.273 instead of 2.1.278 | 1 | 53 / 42 / 24 | the client build |

So there is no knob in this repository that buys resident schemas, and shrinking `CA_TOOLS` is not a
fix. Index state was identical and current across all four.

**Round 2 — the reachability probe, on *this* repo.** Round 1 measured whether a *coached* session
can reach the tools. It cannot answer the question the run actually rests on, which is whether an
*uncoached* one does. `probe --uncoached` asks an ordinary navigation question, names no tool and
offers no escape hatch. Result: **exit 2 — 0 code-atlas calls in 10 tool calls** (2 `Glob`, 3 `Grep`,
5 `Read`), and `ToolSearch` was never called.

The same transcript's session header lists **52 tools with all 24 code-atlas tools present**, the
server `connected`, and `permission_denials: []`. Re-running the coached probe on the same repo
minutes later still reported deferred delivery. **Round 1's framing was therefore too narrow:** the
tools are registered and permitted, and the uncoached session still did not choose them. Treat the
`total_deferred_tools: 41` figure as round 1's telemetry, not as the explanation.

**Round 3 — the same probe on the anchor, where the question fits.** Exit **2** again: **0
code-atlas calls in 25 tool calls** (4 `Glob`, 10 `Grep`, 11 `Read`), `ToolSearch` never called,
26 turns, $1.73. Header: 52 resident tools of which 24 code-atlas, server `connected`, `ToolSearch`
resident, `permission_denials: []`. The poor-fit objection round 2 had to carry does not apply here.

**Verdict for this protocol (pre-300): there is no granted arm to buy under bare registration, and
delivery is not why.**

| Session | Repo | Client | Tool calls | code-atlas calls |
|---|---|---|---|---|
| 2026-08-27 cell (granted) | anchor | Aug build | 68 | 0 |
| 2026-09-19 `--uncoached` | this repo | 2.1.278 | 10 | 0 |
| 2026-09-19 `--uncoached` | anchor | 2.1.278 | 25 | 0 |

n = 3, two repos, two clients, full availability every time. Buying six cells under *bare*
registration would buy six native-tools sessions and label three of them an arm — the abort's
mistake, repeated with a bigger bill.

**300 closed (2026-09-19) with the blocker named, not lifted.** Every code-atlas tool reaches
Claude Code 2.1.278 as a **deferred name with no schema** — at 24 tools and at the six-tool preset
alike — while `Grep` is resident, so an index call costs a deliberate step the alternative does not.
The server now ships MCP `instructions` (index state + the map + that load step), which is the one
channel 081 missed. Across six held-out cells it deepened use where it had started (anchor H4,
2 → 12 calls in 43) and started none: H3 and H5 stayed at 0 on the anchor, and all three stayed at 0
on this 592-file repo. **Uptake tracks whether `Grep` hurts, not what the tools say.** Instrument
additions: `probe --append-system-prompt-file`, `probe --question-file`. Tables:
[300](../tasks/300_the-index-is-registered-permitted-and-never-chosen.md).

**So 074 resumes per question, never per repo.** The granted arm exists only where the frozen
question actually reaches the index. Precondition, before any cell is bought: run
`probe --question-file` on the frozen question against the anchor **twice**; buy cells only if both
are exit 0. That is ~$3.50 against $5.58 per cell and it is the whole difference between a granted
arm and a native-tools session wearing its label. On the current evidence a routing-shaped frozen
question on a 23k-file tree is the case most likely to clear it.

**The boundary this evidence does not cross.** All cells are **headless one-shot**. The August
interactive 19 % (22/117) is not a controlled comparison — different questions, different session
mode — so whether the harness or the surface owns that gap is still open, in 300.

## Run record — 2026-08-27, aborted after 1 of 6 cells; ticket closed `deferred`

The maintainer ran the protocol on the anchor repo and stopped it. Harness: one `--strict-mcp-config`
config per arm as the only difference, `Edit`/`Write` disallowed, fresh headless session per cell,
interleaved g/d/g/d/g/d. Three things came out of it, and **none of them is a verdict**:

1. **One granted cell ran (rc=0, 985 s, 68 tool calls, $5.58); an earlier attempt was voided** because
   the session listed the harness directory and could see both arms' configs — the harness was moved
   outside the repo before the counted attempt. Cells 2–6 were never run: ~$5.58 × 6 for a result the
   tree's own comments had largely pre-determined.
2. **The frozen key was falsified by the cell it was meant to score.** The key asserted *no live cause
   in this tree*; the cell reproduced the fatal and named a mechanism the key did not contain (a loop
   cursor that **cycles** rather than sticks, because an out-of-range date makes the parse return
   `false` and the cursor resets to the epoch while the `while` condition stays true — so the
   cursor-unchanged backstop cannot fire). Scored mechanically the cell reads `wrong-cause`; in truth
   it is more correct than the key. No verdict recorded, and correctly so.
3. **The granted arm was not a granted arm.** All 22 code-atlas tools arrived as a `deferred_tools_delta`
   attachment — **names without schemas** — and the session never called `ToolSearch`, so it made
   **0 index calls in 68** with no callable tool available. Adoption was structurally zero, which is a
   fact about tool delivery, not about the index's answer quality.

**Both rules this earned are now procedure, not advice** — findings (3) and (1) became
[Arm preflight](#arm-preflight--the-granted-arm-is-proven-not-assumed-r1--abort-finding-3), and
finding (2) became [The key](#the-key--freeze-procedure-r1-step-2--abort-finding-2). Neither is
restated here.

**Why the ticket is closed rather than re-run:** the value is not established. Each cell costs ~$5.58,
finding (3) means the arm needs rebuilding before a cell means anything, and finding (2) means the
question needs a fresh key. Re-opening is a deliberate decision with a rebuilt arm, not a resumption.
