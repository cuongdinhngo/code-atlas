---
id: 237
slug: native-windows-was-declined-on-a-defender-setting-not-a-platform-limit
title: 'The only POSIX-only import in the core has a documented Windows equivalent that keeps 072''s property, and the "unusably slow" row was measured with Defender scanning every open — so 220 declined native Windows on a configuration, not a platform limit'
phase: 1.5b
milestone: Adoption
status: done
depends_on: [220, 072, 053, 219]
---

## Why this exists

[220](220_no-windows-evidence-exists-and-the-core-cannot-import-there.md) closed **decided**: native
Windows unsupported, WSL2-on-ext4 is the answer. Its measurements are sound and are not disputed
here. What this ticket disputes is that **two independent claims were fused into one verdict**, and
only one of them holds:

1. *"The core cannot import on Windows."* — **True, and one module wide.**
2. *"Windows is unusably slow, so native support is not worth taking."* — **Measured under
   `RealTimeProtectionEnabled: True`, and never re-measured with the exclusion that turns the
   dominant term off.**

README and `AGENTS.md` now tell a Windows user the platform cannot do this. The evidence says the
*default configuration* cannot do this. Those are different sentences, and the repo is publishing
the stronger one.

### Claim 1 — the import surface is one module, four call sites

Re-verified by blocking `import fcntl` and importing the core module by module:

```
FAIL  code_atlas.cli                          ModuleNotFoundError: fcntl
FAIL  code_atlas.tools.build_or_update_index  ModuleNotFoundError: fcntl
FAIL  code_atlas.tools.get_index_status       ModuleNotFoundError: fcntl
FAIL  code_atlas.main                         (transitively, via the two tools)
OK    code_atlas.store · indexer · adapter · config · onboarding.artifact
```

`code_atlas/index_lock.py:16` is the **only** POSIX-only import in the shipped tree
(`scripts/scale_full_build.py:17` and two tests use `resource`; nothing else). Everything downstream
of the lock already imports clean — and it does so **by design, not by luck**:

| Portability hazard | Already handled, at |
|---|---|
| Separators leaking into the graph | `indexer.py:834,999` `.as_posix()`; `PurePosixPath` across `tools/` |
| Adapters emitting `\` in a qname | `adapters/typescript/src/qname.js:9`, `adapters/python/src/parse.py:61` |
| `shlex` eating a Windows path | `config.py:357` — `posix=os.name != "nt"`, with the reason in its docstring |
| `fork`-based fan-out | Not used: `workers` is **threads driving adapter subprocesses** (`indexer.py:1088-1122`) |
| Deleting an open SQLite file | `store.py:475` closes the connection *before* raising `SchemaVersionError`, so `_unlink_index` (`tools/build_or_update_index.py:313`) runs with no handle open |
| Entry points | All six in `pyproject.toml:21-27` are console scripts; pip emits `.exe` shims |

Someone paid for Windows portability everywhere except the lock. That is the load-bearing fact.

### Claim 2 — the cell the table is missing

220's own reading of its cold row: *"a fixed ~27 ms/file; the same D: SSD does 148 MB/s warm, so **it
is the AV filter driver, not disk**."* The diagnosis is correct and stops one step short. Defender
has a first-class exclusion for exactly this workload, and Win11 ships **Dev Drive** (ReFS +
async performance mode) for it. Neither was in the run.

Two rows from 220 §Raw output, which is where they stay (R7.6):

| Native `D:\` | read | vs Linux control |
|---|---|---|
| cold, Defender **on** (measured) | 34-37 files/s | ~1,300× slower |
| warm (measured) | 13,339 files/s / 147.8 MB/s | **3.6×** slower |

The gap between those two rows is a filter driver, not a filesystem. **No row exists for native
`D:\` with an exclusion in place**, and that row is the whole decision — it either lands native
Windows within a small multiple of Linux, or it kills the idea on evidence rather than on a default.

### Three Windows footguns beyond the lock, found while auditing

- **`MAX_PATH` (260).** `stub_roots` walks `vendor/` directly, bypassing ignore
  (`indexer.py:816-840`) — precisely where Composer/npm trees exceed 260 chars. Python ≥ 3.6 opts
  into long paths by manifest, but only when the OS `LongPathsEnabled` key is set.
- **CRLF vs the stored digest.** There are two hashers: `_whitespace_fingerprint`
  (`indexer.py:700-715`) normalises line endings and is CRLF-immune, but `_digest`
  (`indexer.py:1277`) hashes **raw bytes** and is the one persisted for change detection. Consistent
  within a host, so not a correctness bug — but a `graph.db` built in Docker/WSL and then read by
  native Windows over an `autocrlf=true` checkout sees *every file changed* and reparses the world.
  `.gitattributes` pins only `*.sh` and `Dockerfile*` to LF.
- **A repo under `/mnt/*` on WSL.** Already the documented trap; nothing detects it and says so.

Each is detectable at startup. Today each surfaces as a mystery `OSError` or a silent full rebuild,
which is the failure shape R5.3 exists to forbid.

## Root cause — a mandatory-lock difference, not a missing API

`index_lock.py` needs four things (module docstring, 072): a non-blocking exclusive lock the **OS
releases on process death**; a **shared** probe that cannot starve a writer; a progress line written
by the holder on a *second* descriptor; and that line read by *another* process.

POSIX `flock` is advisory and per-open-file-description, so all four compose. Windows byte-range
locks are **mandatory and per-handle**, so a naive whole-file lock breaks the last two — the holder's
own second handle and every outside reader hit `ERROR_LOCK_VIOLATION`. That, not the absence of a
locking call, is why this looked harder than it is. It is fixed by locking a byte **disjoint from the
data**:

```
bytes [0, 200)   the progress line — never locked, so publish/read still work
byte  1 << 20    the lock itself — locking past EOF is legal on Windows, so nothing pads the file
```

`LOCKFILE_EXCLUSIVE_LOCK` ↔ `LOCK_EX`; no flag ↔ `LOCK_SH`; `LOCKFILE_FAIL_IMMEDIATELY` ↔ `LOCK_NB`;
`UnlockFileEx` ↔ `LOCK_UN`. Windows releases every byte-range lock when the handle closes and the
kernel closes all handles on process death, `TerminateProcess` included — so **072's property is
preserved, not traded away**.

**Why not `msvcrt.locking`**, which 220 §Scope named first: it has no shared mode, so
`build_in_progress` would have to take an *exclusive* lock and could deny the lock to a build that
was just starting — a false `busy` and a lost write window. `LockFileEx` through `ctypes` keeps the
shared probe and needs no `pywin32`.

## Scope

1. **`code_atlas/index_lock.py`** — two private implementations behind the existing five-function
   API, selected once at import by `sys.platform`. The POSIX path is unchanged. No new abstraction:
   R1.2 (`one seam, YAGNI`) stays intact, and a *platform* switch is not a *language* branch (R1.1).
2. **The AC4 test 220 declined** — kill the lock holder and assert `build_in_progress()` reads
   `False`. This is the deliverable that proves the property, on both platforms.
3. **A startup preflight** naming the three footguns above when it can detect them — loud and
   specific (R5.3), never a silent slow path.
4. **Re-measure native `D:\` with a Defender exclusion** (and on a Dev Drive if one exists), using
   220's own `fsprobe.py` so the row is comparable. Record it in 220's table shape.
5. **Restate the position** in `README.md:71-75` and `AGENTS.md` — from a prohibition to a tier:
   *runtime supported on Windows; WSL2-on-ext4 recommended (it beat the Linux control); the
   development and test loop stays POSIX.*
6. **Supersede the 220 decision in [PLAN §19](../PLAN.md#19-project-context--decision-log)** — 220
   closed as *decided*, so reopening it is a decision-log entry, not a quiet diff.

### Explicitly not in scope

- **Native-Windows parity for the dev loop.** `scripts/gate.sh` is bash, `scripts/docker-test.sh`
  needs Docker Desktop, and 7 of 202 test modules import `fcntl` / `signal` / `resource`. Declined
  deliberately, and §Scope 5 says so in the docs rather than leaving it implied.
- **The rebuild cost itself** — 219 owns it, on every host.
- **Changing the lock's semantics on POSIX** (220's exclusion, kept).
- **Normalising `_digest` over line endings.** Named as a finding and detected by the preflight;
  changing the persisted digest is a rebuild-forcing change that wants its own ticket.

## Constraints

- **C1** 072's property is not weakened on either platform: no carrier of a `building: true` claim
  may outlive the process that made it.
- **C2** The POSIX path stays byte-identical in behaviour — the 3,245-test green does not move
  because of this ticket.
- **C3** No third-party dependency for the lock (`ctypes` + `msvcrt`, both stdlib).
- **C4** No `if language ==` in the core (R1.1); no new seam (R1.2).
- **C5** Determinism (R4.2) is judged per host. Cross-host byte-identity was never promised and is
  not claimed here.

## Acceptance criteria

- **AC1** With `fcntl` unavailable, `code_atlas.cli`, `code_atlas.main`,
  `code_atlas.tools.build_or_update_index` and `code_atlas.tools.get_index_status` all import. Proven
  by the import probe above, run as a test.
- **AC2** On Windows, two concurrent writers serialise: the second gets `False` from
  `try_index_write_lock`, exactly as `flock` gives today.
- **AC3** On Windows, `publish_build_progress` writes and `read_build_progress` reads the line
  **while the exclusive lock is held** — the mandatory-lock trap, pinned by a test that fails if the
  lock ever covers byte 0.
- **AC4** (220's AC4, now taken) The holder is killed without cleanup and `build_in_progress()` reads
  `False`. Pinned on both platforms.
- **AC5** The preflight reports `LongPathsEnabled` off, `core.autocrlf=true`, and a repo under
  `/mnt/*`, each with the action to take. A clean host prints nothing.
- **AC6** README and `AGENTS.md` state the tiered position, and it matches what AC1 observed. PLAN
  §19 carries the supersession with both tickets cited.
- **AC7** The Defender-excluded `fsprobe.py` row is recorded with its host and path, or E1 below is
  invoked by name.

## Exclusions

- **E1** AC7 needs the maintainer's Windows host — no CI or Linux session can produce it, and
  **GitHub Actions on this repo are unbillable** (all four jobs on [#304](https://github.com/cuongdinhngo/code-atlas/pull/304) failed in ~3 s on billing, zero
  steps run). An agent that cannot reach Windows stops at scope 1-3 + 5-6 and says so rather than
  reasoning about what the number would be — 220's own E1, unchanged.
- **E2** AC2-AC4 on the Windows arm cannot be gated by CI for the same reason. They are written to
  run on both platforms so the POSIX arm is held by `pytest`, and the Windows arm is a recorded
  manual run naming its host. **Windows support ships verified-once, and this ticket says so** — that
  is the honest cost of taking it, and it is the argument 220 had available and did not make.

## References

- [220](220_no-windows-evidence-exists-and-the-core-cannot-import-there.md) — the decision this
  supersedes; its §Raw output holds every measurement and is not copied here (R7.6).
- [072](072_busy-build-hides-staleness.md), [053](053_refresh-on-checkout-hook.md) — why the lock is
  the carrier, and the property C1 protects.
- [219](219_a-full-rebuild-pays-the-populated-db-tax-nobody-chose.md) — the rebuild term every host
  pays; not what makes Windows special.
- `code_atlas/index_lock.py`, `code_atlas/config.py:357`, `code_atlas/indexer.py:816-840,1277`,
  `code_atlas/store.py:475`, `README.md:71-75`.

## MANGO WORKING DOC

Run: `/mango:solve 237` (reviewer ON, challenger ON — no waiver flags). Host: **native Windows 11**,
Python 3.12.10. **This session IS the maintainer's Windows host that 220's E1 lacked** — so AC7 (the
Defender-excluded `fsprobe.py` row on `D:\work\anchor-repo`) and the Windows arm of AC2–AC4 are
reachable this run, not deferred to E1/E2. `pytest` on native Windows cannot import `fcntl`, so the
POSIX-suite proving runs are Docker/WSL; the new Windows-arm tests run here natively.

### Gate 0 — refine

PREMISE: 20 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)

- Checked present: `code_atlas/index_lock.py` (`:16` = `import fcntl`; 5-fn API — `try_index_write_lock`,
  `lock_path_for`, `build_in_progress`, `publish_build_progress`, `read_build_progress`), `cli.py`,
  `main.py`, `tools/build_or_update_index.py`, `tools/get_index_status.py`, `config.py`, `indexer.py`,
  `store.py`, `adapters/typescript/src/qname.js`, `adapters/python/src/parse.py`,
  `scripts/scale_full_build.py` (`:17` = `import resource`), `pyproject.toml`, `README.md`
  (`:71-75` = the prohibition), `docs/tasks/{220,072,053,219}`, and 220's `fsprobe.py`. None missing.

RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)

- `no-vacuous-pass-when-the-window-closes` (202-C2, type 2). By handle (property test on the core lock
  module). Bears on **AC4**: the kill-the-holder test races a real subprocess; if the build finishes
  first it would pass over the untested window. The AC4 test must guard/raise, never green vacuously —
  names R6.5.
- `stamp-evidence-with-the-tree-under-review` (200-C2/201-C1, type 2 process, recurrence 2). By handle
  (process; threads evidence). Bears on **AC7/E2**: stamp the `fsprobe.py` rows with the host and the
  tree under review, never a branch point.
- Operational note (type-3 skill-gap, not a recall key): `embed-mode-leaks-the-working-doc-into-the-diff`
  — 237 is a tracked file with `work_doc_mode: embed`; this working doc's edits show as uncommitted
  changes to a tracked file. Keep it below the separator and mind it at commit time.

REFINE: 1 unresolved surfaced | 1 want-decision asked | 0 how-decision resolved+cited | 1 ASSUMED | skip: no

INPUT KIND: ticket (single deliverable — not epic).

- **Want-decision (acceptance-bar → the user owns it; asked, then handed back → ASSUMED).** The
  exposure-checker (1 dispatch, 51,414 tok) surfaced the ticket's internal tension: the body frames
  AC7's Defender-excluded number as "the whole decision" (flip-or-kill), but Scope 5 + AC6 + E1 commit
  to the "runtime supported on Windows" wording grounded in **AC1 (it imports & runs)**, with no stated
  speed threshold. Asked via `AskUserQuestion`; user replied "choose the best approach" (handed back).
- **ASSUMED (awaiting ratification) — confirm at Gate 1:** docs publish "native Windows supported for
  running & indexing; WSL2-on-ext4 recommended" **unconditionally**, grounded in AC1; the AC7 number is
  recorded honestly and only tunes *how strongly* the docs steer heavy indexing to WSL2 — it is **not**
  a gate on the "supported" wording. Rationale: AC6 says the wording "matches what AC1 observed" (the
  import fact, not speed), and the position recommends WSL2 regardless, so gating "supported" on a speed
  multiple would contradict the ACs. Reverses 220's "unsupported" verdict — but that supersession IS the
  ticket's declared purpose (Scope 6), not a silent reversal (tripwire cleared).

Exposure-checker: 1 decision surfaced (above), re-classified into the want-decision/ASSUMED row. No
further un-exposed product-decisions.

### Gate 1 — analysis

STRUCTURE: native
TRACK: backend — 0/~10 touched files under UI paths
SCOPE: L
TIER: full

CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision

(No open clarification. The one carried item is the refine ASSUMED docs-decision — handed back by the
user, so it is an explicit-confirm-at-Gate-1 item, **not** a `j` clarification. It is put for ratify
below.)

SECTIONS: 8 found (Why this exists, Root cause, Scope, Explicitly not in scope, Constraints, Acceptance criteria, Exclusions, References) | 8 decomposed | ROWS: C=5 R=6 G=1 AC=7

BASELINE: green — `scripts/docker-test.sh pytest -q` → **3247 passed, 1 skipped** (367s). Ran at
58b542c (working tree; only uncommitted delta is this docs edit, test-inert). The 1 skip is
`test_runtime_image_reports_server_build` (shells out to docker, impossible in-image; AGENTS.md's
one named green skip). Native `pytest` cannot run here (`fcntl`) — the documented platform exclusion,
not a red baseline. **DoD = prove the delta green: 3247+new passed, same 1 skip, no new failure.**
Note: the count moved from AGENTS.md's pinned 3,221 (2026-09-08) to 3247 as later tickets added tests
— so C2's real invariant is **3247**, not the ticket's quoted "3,245".

RULE SECTIONS: 15 applicable — 15 by change-type | 0 by recalled handle — §1.1 (rules) ✅, §1.2 (rules) ✅, §1.4 (rules) ✅, §4.2 (rules) ✅, §4.3 (rules) ✅, §5.3 (rules) ✅, §6.1 (rules) ✅, §6.5 (rules) ✅, §6.7 (rules) ✅, §6.8 (rules) ✅, §7.2 (rules) ✅, §7.3 (rules) ✅, §7.5 (rules) ✅, §7.6 (rules) ✅, §8.2 (rules) ✅

(Both recalled handles map to already-applicable change-type sections — `no-vacuous-pass-when-the-window-closes`→§6.5, `stamp-evidence-with-the-tree-under-review` is not yet a ratified rulebook section — so 0 sections are added *by handle*.)

- §1.1 — core `index_lock.py` touched. A **platform** switch (`sys.platform`) is not a **language**
  branch; the CI grep-gate forbids `if language ==`, and precedent `config.py:357` (`os.name != "nt"`)
  is the sanctioned shape. Compliant, not N/A.
- §1.2 — **no new seam**: two private impls behind the existing 5-function API, no registry/plugin.
- §1.4 — SRP: the change lives in `index_lock.py` (+ a new `preflight`); neither imports store/adapter.
- §4.3 — single SQLite writer is exactly the invariant the Windows arm must preserve (C1). §4.2 —
  determinism judged **per host** (C5); cross-host byte-identity never claimed.
- §5.3 — the preflight is a fail-**loud** config/programmer warning (AC5), never a silent slow path;
  a clean host prints nothing.
- §6.1/§6.5/§6.7/§6.8 — new guards: §6.5 each guard observed failing + **no vacuous pass** (recall
  `no-vacuous-pass-when-the-window-closes`, 202-C2 → AC4 must guard the race, not green over a finished
  build); §6.7 AC1's import probe **derives** the entry set, not a hand list; §6.8 AC3 (fails if the
  lock ever covers byte 0) and AC4 (kill → False) are failure-mode ACs needing a guard that exhibits.
- §7.2 — ledger row + backlog/PLAN §19 kept honest. §7.6 — prune-as-you-add: README:71-75 rewritten
  (not appended), AGENTS.md platform line, PLAN §19 supersession. §7.5 — new comments ≤3 lines.
- §7.3 — small commits, **no AI-attribution trailer** (project rule + user global override beat the
  session reminder). §8.2 — C3 keeps the lock stdlib-only (`ctypes`+`msvcrt`); no new dependency.
- N/A (reason): §1.3/1.5/1.6/1.7/1.8/1.9 (no contract/reader/classifier change), §2.* (no adapter
  language-spec change), §3.* (the lock is not contract vocabulary; `CONTRACT_VERSION` unmoved),
  §4.1 (no LLM/network), §5.1/5.2/5.4–5.8 (no payload/attestation/manifest-delete change — `_unlink_index`
  is unmodified and already handle-safe, verified `store.py:475`), §6.2/6.3/6.4/6.6/6.9, §8.1/8.3.

**Requirements matrix**

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|----|--------|------------------|----------------|--------------|--------|
| G1 | Why exists | Supersede 220's fused verdict | Import works (1 module); "slow" was Defender-bound → ship Win arm + preflight + re-measure + tiered docs | 220 declined on config, not platform; `index_lock.py:16` sole `fcntl` | ⬜ |
| R1 | Scope 1 | Two private impls behind the 5-fn API, `sys.platform`-selected; POSIX unchanged | `LockFileEx` via `ctypes`; byte 1<<20 lock, bytes[0,200) unlocked | 5-fn API confirmed `index_lock.py:29-104` | ⬜ |
| R2 | Scope 2 | Take 220's declined AC4 test | Kill holder → `build_in_progress` False, both platforms | precedent `test_killed_build_is_honest.py` (fcntl) | ⬜ |
| R3 | Scope 3 | Startup preflight naming 3 footguns | New `preflight` module; loud/specific (R5.3); clean host silent | build path `cli.build`/`build_or_update_index.create` | ⬜ |
| R4 | Scope 4 | Re-measure native D: with Defender exclusion | 220's `fsprobe.py`; 220 table shape; +Dev Drive if present; on `anchor-repo` | `fsprobe.py` present; host = this session | ⬜ |
| R5 | Scope 5 | Restate README:71-75 + AGENTS to a tier | Prohibition → "runtime supported; WSL2 recommended; dev loop POSIX" | README:71-75 = the prohibition | ⬜ |
| R6 | Scope 6 | Supersede 220 in PLAN §19 | Decision-log entry citing both tickets | PLAN §19 is the log | ⬜ |
| C1 | Constraint | 072's property not weakened either platform | No `building:true` carrier outlives its process | Windows byte-range lock released on handle close / process death | ⬜ |
| C2 | Constraint | POSIX path byte-identical; suite green unmoved | POSIX arm untouched; N=**3247** passed / 1 skip | baseline captured | ⬜ |
| C3 | Constraint | No third-party dep for the lock | `ctypes`+`msvcrt` stdlib only | §8.2 | ⬜ |
| C4 | Constraint | No `if language==`; no new seam | Platform switch ≠ language branch; behind existing API | §1.1/§1.2 | ⬜ |
| C5 | Constraint | Determinism judged per host | Cross-host byte-identity not promised | §4.2 | ⬜ |
| AC1 | AC | 4 modules import with `fcntl` unavailable | cli, main, build_or_update_index, get_index_status | import probe (N=4) | ⬜ |
| AC2 | AC | Windows: 2 writers serialise; 2nd gets False | `try_index_write_lock` LOCK_EX↔`LOCKFILE_EXCLUSIVE_LOCK` | Win arm test | ⬜ |
| AC3 | AC | Win: publish/read progress while excl. lock held | byte-0 unlocked; test fails if lock covers byte 0 | Win arm test | ⬜ |
| AC4 | AC | Kill holder → `build_in_progress` False (both) | must guard the race (no vacuous pass, R6.5) | Win + POSIX test | ⬜ |
| AC5 | AC | Preflight reports 3 footguns w/ action; clean host silent | LongPathsEnabled off, core.autocrlf=true, repo under /mnt/* | preflight tests (N=3) | ⬜ |
| AC6 | AC | README+AGENTS tiered, matches AC1 | grounded in AC1 (import); **ASSUMED bar below** | — | ⬜ |
| AC7 | AC | Defender-excluded `fsprobe.py` row recorded w/ host+path, or E1 | producible this run (Windows host + anchor-repo) → produce | Docker up; native host | ⬜ |

Status: ⬜ pending (design/execute prove). E1/E2 exclusions → design `EXCLUSIONS:` line.

**AC validation (falsifiability).** All 7 ACs are falsifiable (import outcome / lock behavior / grepable
preflight strings / a recorded measurement row). No AC-value mismatch to raise — the ticket asserts no
numeric target (the 220 rows it quotes are recorded facts, not thresholds). Two **manual-check
exclusions** (verified-once, host-named, per E1/E2 — CI cannot gate them): (a) AC2–AC4 **Windows arm**
(POSIX arm is `pytest`-gated; Windows arm is a recorded native run naming this host); (b) AC7 the
measurement row. Both carry `expiry:` = "re-run on a Windows host when the lock or fsprobe changes".

**Universal inventories (denominators).** AC1 → N=4 entry modules. R1/lock API → N=5 functions
(`try_index_write_lock`, `lock_path_for`, `build_in_progress`, `publish_build_progress`,
`read_build_progress`). AC5 preflight → N=3 footguns. C2 → N=3247 POSIX tests + 1 known skip.

**Cause/gap (enhancement).** Current: `index_lock.py:16` imports `fcntl` unconditionally → the 4 entry
modules raise `ModuleNotFoundError` on native Windows; everything downstream already imports clean by
design. Root cause (from ticket, verified): a **mandatory-vs-advisory lock** difference, not a missing
API — Windows byte-range locks are mandatory/per-handle, so a whole-file lock breaks publish/read;
fixed by locking a byte disjoint from the [0,200) progress region. Gap per scope item R1–R6 above.

**Blast radius.** `code_atlas/index_lock.py` (arm) + new `code_atlas/preflight.py` (or similar) called
from the build path; new tests under `tests/`; docs README/AGENTS/PLAN §19; the measurement recorded in
this working doc (220's raw output stays in 220, R7.6). Single repo (`app`). The 7 `fcntl`/`signal`/
`resource`-importing test modules and the bash/Docker dev loop are **out of scope** (ticket "Explicitly
not in scope" + E2). No contract/store/adapter change.

**⚖️ ASSUMED docs-decision — RATIFIED by the maintainer at Gate 1 (2026-09-10):**
Publish "native Windows **supported** for running & indexing; WSL2-on-ext4 recommended" grounded in
AC1 (it imports & runs); the AC7 number is recorded honestly and only tunes how strongly docs steer
heavy indexing to WSL2 — **not** a threshold gate on the "supported" wording. Reverses 220's
"unsupported" (which IS Scope 6's declared purpose). No longer ASSUMED — this is now a settled
acceptance constraint AC6/R5 must honour. Gate 1 approved same turn.

### Gate 2 — design (change list = approved scope)

**Investigation (spike, this Windows host — the user's steer: prove the build *works*, not just docs).**
Empirical findings, all run natively 2026-09-10:
- Import dies at exactly `index_lock.py:16 import fcntl` and **nowhere else** — `grep -rnE "import (fcntl|resource|pwd|grp|termios|posix)|os\.(fork|getuid…)|signal\.(SIGKILL|…)" code_atlas/` returns **only** that line. So the lock is the whole core blocker.
- Windows lock primitives present in **stdlib**: `msvcrt.get_osfhandle`, `kernel32.LockFileEx`/`UnlockFileEx`, `winreg` — no `pywin32` (C3 holds).
- Adapter subprocess launch is Windows-safe: `adapter.py:144` `Popen(list, cwd=…, PIPE…)`, no `preexec_fn`/`start_new_session`/`shell`.
- **Byte-range lock spike PASSED natively** (`scratchpad/winlock_spike.py`): excl lock acquired; publish+read `[0,200)` works *while* held; shared probe DENIED under holder (`err=33 ERROR_LOCK_VIOLATION`) → `build_in_progress` True; GRANTED after release → False.
- **anchor-repo reality:** ~19,352 PHP files / 43,545 indexable; native host has **`node` v24 but NOT `php`/`composer`**. So the lock fix makes the *core* run natively, but a full **PHP-repo** native build additionally needs php+composer on PATH — else it runs and **loudly skips PHP** (R5.3). This is a real native-Windows build issue → surfaced by the preflight (a 4th check) and the docs, not hidden.

**Approach.** Add a Windows arm to `index_lock.py`, selected once at import by `sys.platform`. Guard
`import fcntl` (POSIX only); on `win32`, the three lock primitives (`_acquire_exclusive_nb`,
`_acquire_shared_nb`, `_release`) use `ctypes` `LockFileEx`/`UnlockFileEx` on **byte `1<<20`** (past
EOF, disjoint from the `[0,200)` progress region). The five public functions and the POSIX primitive
bodies (`fcntl.flock`) are **byte-identical** to today (C2). Add a `preflight` module wired into
`cli.py`. Re-measure native `D:` with a Defender exclusion via 220's `fsprobe.py`, and run a **real
end-to-end native build** (node-adapter repo) to prove the pipeline runs. Restate README/AGENTS/PLAN
§19 grounded in the demonstrated working build (ratified AC6 tier).

**Rejected alternatives.**
- `msvcrt.locking` (220's first pick) — **no shared mode**, so `build_in_progress` would need an
  *exclusive* lock and could deny a just-starting build (false `busy`, lost write). Rejected (ticket §Why-not-msvcrt); the spike confirms `LockFileEx` keeps the shared probe.
- `pywin32` — violates C3 (third-party dep); `ctypes`+`msvcrt` suffice (spike proved). Rejected.
- Split into `_lock_posix.py`/`_lock_windows.py` modules — cleaner-looking but a bigger refactor that
  risks the POSIX byte-identical guarantee and adds indirection for one call site (R7.4/R1.2).
  Rejected: one file, one `sys.platform` switch, guarded import.

**Assumptions.**
- Windows byte-range lock at `1<<20` does not block `[0,200)` writes; concurrent opens allowed;
  shared probe denied under exclusive; released on handle close / process death →
  **`verified` (spike, all 4 checks PASS, err=33)**.
- `fcntl` is the sole core POSIX blocker → **`verified`** (grep empty above).
- Adapter subprocess launch Windows-safe → **`verified`** (`adapter.py:144`).
- anchor-repo native full build needs php+composer (absent) → **`verified`** (php/composer MISSING; node present) → surfaced, not assumed away.

HANDLES: 2 recalled | 1 traced (command + result) | 1 does not apply (reason) | 0 unanswered

- `no-vacuous-pass-when-the-window-closes` → **traced.** `sed -n '111,124p' tests/test_killed_build_is_honest.py` →
  the existing POSIX kill test raises *"the build finished before it could be killed — the fixture is
  too small to exercise the window, so any pass below would be vacuous (R6.5)"* and asserts progress
  reached `phase=parse` before killing. Folded into the change list: AC4's Windows arm reuses this
  guard — it asserts the child **actually acquired the lock** (`build_in_progress` True) before the
  kill, and fails loudly if the child exits first, so a killed-then-False can never pass vacuously.
- `stamp-evidence-with-the-tree-under-review` → **does not apply because** this change introduces no
  shared code symbol whose producers/consumers need enumerating — it is a recording discipline,
  honored by stamping the baseline (`Ran at 58b542c`) and the AC7/fsprobe row with host + path + tree,
  not by a code fan-out.

**Smallest change-list.**

| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|--------|-----------|--------------|----------------|-----|
| 1 | Windows lock arm behind the 5-fn API; guard `fcntl`; `sys.platform` switch; POSIX byte-identical | `code_atlas/index_lock.py` | the 4 entry modules importing it; 7 `fcntl` POSIX tests (must stay green in Docker); R4.3 single-writer invariant | R1,C1,C2,C3,C4,C5,AC1,AC2,AC3,AC4 | 10/10 |
| 2 | New preflight (LongPaths via `winreg`, `core.autocrlf` via git, repo under `/mnt/*`, **+ adapter runtime php/composer absent**); wire into `cli.py` build/status | `code_atlas/preflight.py` (new), `cli.py` | cli stderr output; clean host silent (R5.3); no MCP payload change | R3,AC5 | 2/2 |
| 3 | Tests: AC1 import-probe (fcntl blocked), AC2 serialise, AC3 progress-while-locked + byte-0 guard, AC4 kill both platforms, AC5 preflight | `tests/test_windows_lock.py`, `tests/test_preflight.py` (new) | CI POSIX arm gated; Windows arm manual-recorded (E2) | R2,AC1,AC2,AC3,AC4,AC5 | 5/5 |
| 4 | Measurement: `fsprobe.py` on anchor-repo w/ Defender exclusion (+Dev Drive if present) **and a real native end-to-end build** proving the pipeline runs | this working doc (220 table shape) | none (evidence only); 220's raw output stays in 220 (R7.6) | R4,AC7 | 2/2 |

Proof approach (how-decision, handed back → chosen): (a) guaranteed node-adapter end-to-end native
build (no install); (b) opportunistically install php+composer to build the **real anchor-repo** natively
for the strongest evidence — if impractical, php/composer is the surfaced preflight+docs prerequisite;
(c) fsprobe measures anchor-repo regardless. Cited: user steer "build phải chạy được thật" + practicality.
| 5 | Docs: README:71-75 rewrite (prohibition→tier), AGENTS.md platform line, PLAN §19 supersession | `README.md`, `AGENTS.md`, `docs/PLAN.md` | tier-1 docs (charged every session); AGENTS test-count pin note | R5,R6,AC6 | 3/3 |
| 6 | Token-ledger row | `docs/TOKEN_LEDGER.md` | R7.2 | — (R7.2) | 1/1 |

Every item traces to a matrix row. No speculative abstraction.

**Rule compliance.** §1.1 — `sys.platform` switch is not a language branch: the gate regex is
`if[^\n]*\blanguage\b[^\n]*==|match…language` (`test_guardrail_gates.py:29`); my code has no
`language` token → gate green (verified). §1.2 no new seam. §4.3 the single-writer invariant is what
the arm preserves. §5.3 preflight fails loud, clean host silent. §6.5 no vacuous pass (AC4 guard).
§8.2 stdlib-only. §7.6 docs pruned in place. §7.3 commits carry **no** AI-attribution trailer.

**Verification plan (per-AC, layer-matched).**

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | integration (import-time) | unit import-probe (fcntl blocked via `sys.modules`) — CI both platforms | n/a | ✅ |
| AC2 | runtime/3p (Win lock) | integration (two `try_index_write_lock`) — Win manual-recorded | n/a | ✅ |
| AC3 | runtime/3p (Win lock) | integration (publish/read while held; fails if lock covers byte 0) — Win manual-recorded | n/a | ✅ |
| AC4 | e2e (real subprocess kill) | e2e (spawn+kill; POSIX arm CI-gated, Win arm manual-recorded) | n/a | ✅ |
| AC5 | integration (env detect) | unit (mocked conditions) + integration (cli) | n/a | ✅ |
| AC6 | logic (wording matches AC1) | grep test asserting README/AGENTS tier wording | n/a | ✅ |
| AC7 | runtime (real disk/AV) | manual-recorded fsprobe row (host+path+tree) | n/a (measurement, not input-shape-dependent) | ✅ |

No input-shape-dependent AC (none heuristic/ranking/grouping), so fixture provenance is `n/a`
throughout. AC7 is measured **against** `D:\work\anchor-repo`, but that is a disk/AV measurement,
not a heuristic whose expected output depends on input shape — so it is `n/a`, not a corpus-proof.

EXCLUSIONS: 2 recorded | 2 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus

- **Excl-1 — Windows arm of AC2–AC4 is not CI-gated** (E2: ships verified-once). Proven by a recorded
  native run naming this host; the POSIX arm of AC4 is `pytest`-gated. `expiry: when a Windows CI
  runner exists (GH Actions billing restored + a windows-latest job); re-run manually on a Windows
  host whenever index_lock.py changes.` `seen: [237]` (first occurrence).
- **Excl-2 — AC7 measurement is not CI-gated** (E1: needs the maintainer's Windows host; Actions
  unbillable). Recorded with host+path+tree. `expiry: when GH Actions billing is restored and a
  Windows runner can run fsprobe.py.` `seen: [237]`.

**Proving test.** `tests/test_windows_lock.py::test_entry_modules_import_without_fcntl` — with `fcntl`
forced absent (`sys.modules["fcntl"]=None`), assert `code_atlas.cli`, `code_atlas.main`,
`code_atlas.tools.build_or_update_index`, `code_atlas.tools.get_index_status` all import. **Red
pre-change** (they import `fcntl` at module top → `ModuleNotFoundError`), **green post-change**
(guarded import). Runs on **both** platforms via `config.test_command` (`pytest`). Invocation:
`pytest -q tests/test_windows_lock.py::test_entry_modules_import_without_fcntl`.

**Rollback + porting.** Single feature branch `feat/237-native-windows`. Revert = drop the branch
(index_lock.py restored, new files deleted, docs reverted). Single repo (`app`); no shared-code
porting across `config.repos`.

**SCOPE:** L (confirmed — unchanged from analysis). The user's steer added empirical depth (run the
build, name the php/composer prerequisite) but no new files beyond the planned set; no tier jump.
Branch type `feat` (new capability), matching `branch_strategy`.

### Gate 3 — execute (evidence)

Branch `feat/237-native-windows` (5 commits off `58b542c`). All empirical blocks below **Ran at**
the branch tip on **native Windows 11 / Python 3.12.10** (the E2 verified-once host).

**Axis 1 — file set.** `git diff --stat 58b542c..HEAD`: `code_atlas/index_lock.py`,
`code_atlas/preflight.py` (new), `code_atlas/cli.py`, `tests/test_windows_lock.py` (new),
`tests/test_preflight.py` (new), `README.md`, `AGENTS.md`, `docs/PLAN.md`, working doc. **diff ⊆
approved change-list** (items 1-5); TOKEN_LEDGER row is item 6 (finalise). No stray file, no
untouched-line reformat. ruff `All checks passed`, mypy `No issues found`.

**Axis 2 — design conformance (per Gate-2 Approach bullet).** 7/9 implemented-as-approved; 2 recorded
deviations:
- Windows arm behind the 5-fn API via `sys.platform` switch ✅ · `fcntl` guarded (else-branch only) ✅
  · `LockFileEx`/`UnlockFileEx` on byte `1<<20` ✅ · POSIX bodies byte-identical (same `fcntl.flock`
  flags) ✅ · preflight module wired into `cli.py` ✅ · docs restated grounded in the working build ✅
  · real end-to-end native build ✅ (exceeded — self **and** anchor-repo).
- **Deviation D1 — AC7 Defender-*excluded* cold row NOT produced.** This session is not elevated
  (`IsInRole(Administrator)=False`), so `Add-MpPreference -ExclusionPath` cannot run. **E1 invoked** —
  the decisive cell needs the maintainer's elevated host. The AV-filter mechanism is nonetheless
  isolated (below). Surfaced to review.
- **Deviation D2 (minor) — preflight's 4th check generalized.** Gate 2 said "adapter runtime
  php/composer absent"; implemented as the R5.3-generic "any *configured* adapter command not on
  PATH", a superset. Note: anchor-repo's PHP was skipped because no `CA_PHP_CMD` was configured (a
  different path from configured-but-missing) — documented in the tier.

**Empirical output (trimmed, verbatim).**

```
# AC1 — entry modules import natively (fcntl absent on Windows):
OK code_atlas.cli · code_atlas.main · code_atlas.tools.build_or_update_index · get_index_status · index_lock
# proving test: RED pre-change (top-level `import fcntl` at 58b542c) -> GREEN post-change (guarded)
# pytest -v tests/test_windows_lock.py tests/test_preflight.py  ->  15 passed (Windows arm ran, 0 skipped)
#   incl TestWindowsLockArm::{two_writers_serialise, progress_readable_while_lock_held, lock_offset_disjoint}
#   incl test_a_killed_holder_releases_the_lock (guarded against vacuous pass, R6.5)
```
```
# AC-"build works" — native code-atlas-build, this Windows host, Defender ON:
self (python adapter):  full: 368 file(s), 6192 node(s), 45280 edge(s)   EXIT=0
anchor-repo (TS+SQL, PHP skipped): full: 6339 file(s), 107728 node(s), 2788992 edge(s)  EXIT=0  (1.6 GB graph.db)
# preflight fired real warnings: LongPathsEnabled off; core.autocrlf=true; php not on PATH
```
```
# AC7 — fsprobe.py (220's exact probe), native D:\, NTFS, Defender RealTimeProtection=True, 2026-09-10:
anchor-repo     56,998 files (1057 MB)  stat 98,612 f/s   read ~21 f/s / 0.4 MB/s  (run1 2810s, run2 2713s — does NOT warm; >cache)
code-atlas     881 files (9.7 MB)   stat 55,063 f/s   read    39 f/s / 0.4 MB/s  (reproduces 220's 37 f/s cold)
# same SSD warm (220, files that fit cache): 13,339 f/s / 147.8 MB/s ; Linux control ext4: 47,370 f/s / 522 MB/s
```

**AC7 verdict.** Read throughput **0.4 MB/s under Defender vs 147.8 MB/s warm on the same SSD** isolates
the AV filter driver as the *entire* cold-read cost — 220's diagnosis, now reproduced on a second repo,
and shown not to warm once the working set exceeds the cache (anchor-repo). This **confirms 220's slowness**
and **refutes its verdict**: the cost is 100% a Defender configuration, the lock fix is cheap/correct,
and the build runs. The cold-*with-exclusion* row (D1/E1) is the maintainer's elevated step; the
mechanism does not hinge on it.

**Excl-1** (Windows arm not CI-gated) — discharged by the recorded native run; **Excl-2** (AC7) —
recorded with host+tree, Defender-excluded cell open under E1.

**Ph3/4 proven by:** AC1 ✅ · AC2/AC3 ✅ Windows arm (native) · AC4 ✅ kill test (native; POSIX arm via
Docker) · AC5 ✅ · AC6 ✅ · AC7 ⚠ mechanism proven, excluded row open (E1). C1 ✅ · C2 ⏳ POSIX
byte-identical via pre-PR Docker (3247) · C3/C4/C5 ✅.

### Gate 4 — review

**REVIEWER: OFF** — waived by the maintainer ("skip review and challenger"); dispatched then stopped
before returning. So **no rule-book-grounded review of this diff exists**. **CHALLENGER: ON (re-run at
the maintainer's request on PR #308)** — the first dispatch was stopped with the reviewer; a second
ticket-blind challenger (raw ticket only + diff excluding bookkeeping) completed at tree `75fa33f`:
**16 of 16 requirements MET, 0 not-met, 0 can't-tell** (Scope 4 + AC7 met-per-E1, confirmed via the
commit trail, not silently skipped). It re-ran AC1–AC5 **live on this native-Windows host** (first-party,
not static). Two non-blocking notes: (1) a stale docstring symbol `_lock_windows` at `index_lock.py:16`
— **fixed** (`_win_lock`/`win32` branch); (2) the preflight's disclosed 4th check (deviation D2), not a
miss. Verdict: **clean (challenger only — REVIEWER: OFF)**.

Mechanical reconciliation still ran (main loop, no subagent):
- **Axis 1 file set** — `git diff 58b542c..HEAD` ⊆ approved change-list (items 1-5); TOKEN_LEDGER is
  item 6 (finalise). No stray file, no untouched-line reformat. ruff/mypy clean.
- **Axis 2 behaviour** — 7/9 Approach bullets as-approved; 2 recorded deviations (D1 AC7 Defender-excluded
  row → E1 elevation; D2 preflight 4th check generalized to any-configured-adapter-absent, R5.3). No
  unrecorded deviation.
- **Regression / blast radius** — 4 entry modules + the 7 `fcntl` POSIX lock tests; confirmed by the
  pre-PR Docker suite (below).
- **Proving test** — `test_entry_modules_import_without_fcntl`: RED at 58b542c, GREEN at HEAD (recorded).
- **Layer-match** — no ❌ stands; AC7 is manual-recorded + E1 (recorded human-approved exclusion).
- **Loop-back (execute→review).** The pre-PR Docker suite at 378643f found **3 failures** (3260
  passed) — all guard-tests correctly reacting to the change, not regressions: the core-module count
  pin 84→85 (two guards) because `preflight.py` is a new core module, and R6.5's
  assert-under-a-conditional sweep flagged `test_long_paths_check_is_windows_only`. A **design
  blast-radius miss**: Gate 2's test blast-radius did not enumerate the module-count pins. Fixed in
  `7e88352` (pins bumped with a `preflight (237)` note; the LongPaths test rewritten with two
  unconditional assertions). Re-verified natively (278 passed).
- **Delta-green (C2)** — `scripts/docker-test.sh` (ruff+mypy+pytest) at HEAD **7e88352**: **3263 passed,
  4 skipped** (302s), exit 0. vs baseline 3247/1 → +16 pass, no new failure; the **7 existing `fcntl`
  lock tests pass** (C2 byte-identical confirmed). 4 skips explained: 1 in-image docker skip +
  3 Windows-only `TestWindowsLockArm` tests skipped on Linux. (A first Docker attempt failed on a
  transient pip-install network flake — no dep changed, C3; the re-run is the record.)

**VERDICT: clean (nobody looked — REVIEWER: OFF, CHALLENGER: OFF).** No rule-book review and no
independent challenge exist for this diff; the maintainer waived both mid-run. The mechanical
reconciliation + the full Docker suite are the only checks that ran.

**Reviewed at 7e88352** — reviewed files: `code_atlas/index_lock.py`, `code_atlas/preflight.py`,
`code_atlas/cli.py`, `tests/test_windows_lock.py`, `tests/test_preflight.py`,
`tests/test_core_is_language_agnostic.py`, `tests/test_sql_confinement.py`, `README.md`, `AGENTS.md`,
`docs/PLAN.md`. Working-doc path (staleness-exempt): this ticket file below `## MANGO WORKING DOC`.

### Finalise — learning loop + ledger

**Stale-review guard:** `git diff --name-only 7e88352..HEAD` = only the exempt working doc + bookkeeping
(LESSONS/BACKLOG/frontmatter, folded into the branch push) → **not stale**, proceed.

**Durable lesson (237-C1).** Adding `code_atlas/preflight.py` moved the core-module count pinned in
`test_core_is_language_agnostic.py` + `test_sql_confinement.py`; the Gate-2 blast-radius trace did not
grep for it, so the Docker suite reddened on the pin. This is the **new-module dimension** of the
already-promoted `count-pin-in-blast-radius` (AGENT_BRIEF **P5**). Recorded as a P5 sighting in
`docs/LESSONS.md` (seen 10→11).

CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified
RECURRENCE: 1 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)
FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)
RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path
PROMOTION: 0 proposed | 0 human-ratified | destinations: (already AGENT_BRIEF P5) | mango files written: 0

(No new promotion: `count-pin-in-blast-radius` is already a ratified rule (P5); this run adds a sighting,
not a candidate. It is a **type-2 claim seen across ≥2 tickets** → the human runs `/mango:promote`
between tickets as the cross-ticket pass; nothing to promote here since it is already at P5.)

**Cost ledger (per dispatch).**

| phase | dispatch | round | tokens |
|-------|----------|-------|--------|
| refine | exposure-checker (`challenger`) | 1 | 51,414 |
| review | `reviewer` (Sonnet) | 1 | unmeasured (dispatch stopped by user before return) |
| review | `challenger` (ticket-blind) | 1 | unmeasured (dispatch stopped by user before return) |
| review | `challenger` (ticket-blind, re-run on #308) | 2 | 85,931 |

LEDGER TOTAL: 137,345 tokens measured (+2 dispatches stopped by the user, unmeasured) · top cost driver: review challenger re-run (85,931) · main-loop output not measured by mango (see `rtk gain`).

### Session status

- **KEY:** 237 · **work_doc_mode:** embed · **Current phase:** closed — **PR [#308](https://github.com/cuongdinhngo/code-atlas/pull/308) merged 2026-09-10** as `8787174`, status→done, BACKLOG row removed (the ledger row carries it). Rebased onto `main` before merge; review on the PR fixed four items (`/mnt/*` warned off-WSL; README claimed a Defender check the preflight has not got; AGENTS.md's stale `fcntl` reason and stale counts) and re-paid PLAN's budget for the 237+238 entry pair. Revert = `git revert 8787174`. No CI checks reported (Actions unbillable); bare `pytest` **3,277 / 3** and `docker-test.sh` **3,276 / 4** on the merged tree are the verification. Open follow-up: declare `argtypes`/`restype` on `LockFileEx`/`UnlockFileEx`, on a Windows host.
