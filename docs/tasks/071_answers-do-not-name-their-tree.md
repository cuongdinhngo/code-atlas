---
id: 071
slug: answers-do-not-name-their-tree
title: 'A worktree agent gets the main checkout''s symbols with `reason: "ok"` and no field names the tree'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [033, 061, 065]
---

## Goal
An agent working in a git worktree asked `file_outline` about **its own path** and was handed a symbol
that exists **only in the main checkout**. The payload said `reason: "ok"`. Nothing in it — no field,
no flag, no path — names the tree the answer describes. Make every answer state which root it came
from, so a mismatch with the caller's own working directory is visible instead of invisible.

## Evidence (memory/concurrency field run, 2026-08-09, anchor repo)
The probe was a two-payload experiment, not an inference. A uniquely-named method was injected into
**the same file** in both trees — `atlasProbeMainAb3` into the main checkout's
`src/System/RegionManager.php`, `atlasProbeWorktreeZq7` into the worktree's copy — then a server was
launched with the client's cwd set to the worktree:

```
server /proc cwd: …/anchor-repo                       # not the worktree
search_symbol(atlasProbeWorktreeZq7) -> {"results":[],"reason":"no_matches","total_count":0}
file_outline(src/System/RegionManager.php)
  names=[…, 'atlasProbeMainAb3', 'clearCache', 'dualRoutine']
```

The agent's **own** symbol was reported absent; the **other tree's** symbol was returned as if it were
the file's content. A `RESOLVED` hit from `main` is byte-identical to a correct hit.

Why the payload cannot help today:
- `root = Path.cwd()` (`main.py:113`), and `db_path = root / …` (`config.py:117`). The dispatched
  registration bakes `cd <main repo>` into the server command, so cwd is the main repo no matter where
  the client runs. Config and observed behaviour agree — the live `/proc/<pid>/cwd` of two background
  agents' servers was read directly and both said main repo.
- **Task 061 removed `db_path` from every nav payload** — `nav_result.py:97` and `:124-125` explicitly
  `del db_path` / `extra.pop("db_path")`. So `search_symbol`, `find_callers`, `file_outline`,
  `read_symbol` and friends carry **no path of any kind**. The only surface still reporting a location
  is `get_index_status`, which a caller may never invoke — and it reports a *database* location, not
  the source tree the answers describe.
- The failure is not an error path. It is the success path returning a confident wrong answer, which
  is the worst of the outcomes the run set out to look for.
- **Freshness makes it worse, not better.** `FreshnessGuard.ensure` resolves the path against
  `config.root` (`freshness.py`), which is the main checkout — so a drifted file is reparsed from the
  **wrong tree** and the wrong answer is *freshly computed*, not merely stale. No staleness signal can
  ever catch this: by every check the server can make, the answer is current.

Scope of the exposure, honestly: for a worktree branched off `main` hours earlier, "who calls this /
where is this defined" is answered identically by both trees, which is why the observed fan-out still
produced good work. **The exposure grows with the size of the agent's own diff — it is worst exactly
when the agent is doing the most work.**

The alternative failure is already known and is *better*: with no `cd` in the command, cwd alone
decides, the worktree has no index, and every tool returns `indexed: false` / `reason: "not_indexed"`.
Honest and useless beats confident and wrong — but the fix should deliver neither.

## Scope / Deliverables
- **Emit the root the answer describes.** One field — shape of `index_root` — carrying the tree the
  indexed rows were parsed from, so a caller can compare it with its own working directory. It must be
  the **source root** (`config.root`), not the database location: a caller cares which files the
  answers are about.
- **Reconcile with 061 deliberately, and write the reasoning down.** 061 stripped `db_path` from nav
  payloads for weight, and this ticket adds a path back. Decide between: on every payload; only when
  the server can tell it differs from the caller's cwd (the server does not receive the client's cwd
  today — say so if that rules the option out); or `get_index_status` only. The last option is the
  cheapest and the weakest, because an agent that never calls it never learns.
- **Do not make the server guess the client's tree.** MCP over stdio gives the server no reliable view
  of the caller's cwd; a heuristic that is right most of the time re-creates this defect with extra
  steps. State the root; let the caller compare.
- **Document the isolation route as configuration, not code.** `CA_DB_PATH` already exists
  (`config.py`), so a per-worktree index is available today at the cost of one build (~83 s incremental
  on the anchor repo). Whether that becomes the recommended fan-out recipe is a docs decision; this
  ticket owns making the un-isolated case legible.

## Constraints
- R4 — the field is derived from config, not from the host or the clock; identical config ⇒ identical
  value.
- 061 — one field, and its weight is justified in the working doc against the payloads it lands on.
- R1.1 / R2 — nothing here learns about git, worktrees, or a repo layout; the server reports the root
  it was configured with and says nothing about what that root *is*.
- No behaviour change to which rows are returned. This ticket changes only what the answer says about
  itself.

## Acceptance criteria
- A read tool's payload lets a caller determine, without calling `get_index_status`, which source root
  the answer describes — or the working doc records why `get_index_status` alone was judged sufficient.
- A test launches a server whose configured root differs from the process's cwd and asserts the
  reported root is the configured one.
- `get_index_status` reports the source root alongside the database path.
- Payload weight for the common case is measured before and after, and recorded (061).

## References
Memory/concurrency field run 2026-08-09 §6 (the two-marker probe, both variants), §7 (live `/proc`
corroboration), §9 fix #1. `code_atlas/main.py:113` (`load_config(Path.cwd(), …)`),
`code_atlas/config.py:117` (`db_path = root / …`), `code_atlas/tools/nav_result.py:95-97,122-125`
(where `db_path` is dropped). Related: [061](061_payload-weight.md) (the rule this pushes against),
[065](065_empty-answer-cannot-explain-itself.md) (same family: an answer that cannot describe its own
limits), [033](033_nav-reason-codes.md) (the `reason` vocabulary that says `ok` here).
