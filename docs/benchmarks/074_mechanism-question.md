# 074 — Does the index harm mechanism (control-flow) questions? — pre-registered protocol

**Status:** pre-registered, runs pending (maintainer environment). **Ticket:**
[`../tasks/074_does-the-index-harm-mechanism-questions.md`](../tasks/074_does-the-index-harm-mechanism-questions.md).

This file is committed **before any run** so the result cannot be argued after the fact. It measures
**agent behaviour**, not server determinism — a granted-vs-denied difference here is not an R4 defect
(say so in the write-up). Nothing repo-identifying from the anchor repo enters this file: question
*shape*, verdicts, and aggregate counts only.

## The question

One **mechanism (control-flow) question** — the shape *"how does X reach Y"* / *"what happens when Z
fires"* / *"what actually drives this behaviour"* — with **no file, class, or method named** in the
prompt. Reuse the **exact** mechanism question from the original 2026-08-08 founding-premise benchmark
(private notes); do not reword it. Establish its **ground-truth cause by hand first**, written down
before any session runs.

## Arms (two only — C2)

| Arm | Configuration |
|---|---|
| **granted** | code-atlas MCP server registered and reachable (the indexed arm's config, server allowed). |
| **denied**  | native tools only — code-atlas absent (server not registered, or `CA_TOOLS=""`). |

No resident-LSP arm: it scored 0 invocations in 84 calls in the original run — there is no
answer-quality comparison to be had.

## Protocol (R1)

1. Write the ground-truth cause by hand (one paragraph), before running. Freeze it.
2. For **each arm**, run **n ≥ 3** cells. Each cell is a **fresh headless session**, **identical
   prompt**, **no coaching**, no reuse of a prior session's context.
3. Keep the index fresh for the granted arm exactly as a normal session would (build once before
   dispatch; do not hand-feed tool calls).
4. Record per cell: the answer's **stated cause**, the **verdict** (rubric below), token count
   (secondary), and — for every wrong/partial **granted** cell — the **mechanism capture** below.
5. Extend to a **second** mechanism-shaped question **only if the first replicates** (R5). One
   question at n ≥ 3 beats five at n = 1.

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
  - `correct-but-unrepresentative` — the 067 shape: a correct but partial answer (e.g. page 1 =
    100 % of one subtree) that terminated the reasoning which would have reached the truth.
  - `confidently-empty` — the 065 shape: an empty/`no_matches` answer read as proof of absence.
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

| Cell | Arm | Verdict | Stated cause (shape) | Preceding tool call | Payload class | Tokens |
|---|---|---|---|---|---|---|
| 1 | granted | | | | | |
| 2 | granted | | | | | |
| 3 | granted | | | | | |
| 4 | denied | | | | | |
| 5 | denied | | | | | |
| 6 | denied | | | | | |

**Arm tallies:** granted `_c / _p / _w` · denied `_c / _p / _w`.
**Selected outcome (from the pre-registered table):** _<one of the three>_.
**Mechanism (if granted worse):** _<named, or "not identified">_.

Once these rows are filled, the analysis turn applies the selected pre-registered consequence: edits
PLAN §19 (delete the threat, or replace it with the resolved mechanism / a scope statement) and the
README value claim **in the same change** (AC3/AC4), and records whether R5's second question is
warranted.
