---
id: 005
slug: adapter-protocol
title: Adapter protocol & subprocess driver
phase: 1
milestone: Core
status: in-progress
depends_on: [002]
---

## Goal
Language-neutral driver for long-lived adapters over JSONL (§4.1, §4.3).

## Scope / Deliverables
- `adapter.py`: `LanguageAdapter` Protocol (`name`, `extensions`, `capabilities`, `start/parse/stop`).
- Subprocess driver: spawn adapter in `--server` mode, feed newline-delimited requests, read JSONL results, handle `ok:false` per file without breaking the stream.
- Extension→adapter lookup (**not** a registry yet — YAGNI until adapter #2).

## Acceptance criteria
- Driver survives a per-file parse error (returns error result, stream continues).
- One process boot amortized across many files; clean `stop()`.
- No `if language == …` branches; adapters resolved purely by extension.

## References
Plan §4.1, §4.3, §2 (OCP/DIP/YAGNI).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 005 — Adapter protocol & subprocess driver (working doc)

- **Ticket:** 005 · [`docs/tasks/005_adapter-protocol.md`](005_adapter-protocol.md) (local-file ticket)
- **Type:** enhancement (new core capability; no bug to root-cause)
- **Repo(s) / Porting:** `app` (`.`) only — single-repo project, no porting
- **work_doc_mode:** `embed` (`.harness.json:13`) — explicit, so the working doc is appended below the
  separator as in tasks 001–004, not written to a `.work.md` sibling
- **SCOPE:** M
- **STRUCTURE:** native (all four ticket headers map to `config.ticket_header_schema`)
- **TRACK:** backend — `0/N` touched files under UI paths (no UI exists; `config.track = "backend"`)
- **TIER:** full (SCOPE=M, three universal requirements with N > 1: protocol members N=6, per-request
  failure modes N=9 (8 at Gate 1, amended at Gate 2 — see inventory B), core modules N=11)
- **BASELINE:** **green** — `pytest -q` → **163 passed, 1 skipped**; `ruff check .` → clean; `mypy
  code_atlas` → no issues in 11 source files; the CI R1.1 grep-gate (`ci.yml:49`) → ok. Untouched `main`
  @ `c657a2d`, worktree clean.
  <!-- baseline exclusions: none. The 1 skip is deliberate and self-declaring
  (tests/test_sql_confinement.py:52 — the adapters half is 0/0 until task 006, skipped rather than
  passed green per LESSONS 002). `ruff format --check .` reports 4 files unformatted (2 at task 004),
  but the formatter is NOT in CI (ci.yml:29-30 runs `ruff check` only), so it is not a declared lint —
  recorded as uncodified-standard item 2 below, not a baseline exclusion. -->

---

## Phase 0 — Refine

`REFINE: not run for this ticket | skip: n/a` — the ticket is a pre-written scaffold stub with native
sections; unresolved product-decisions are surfaced below as Gate-0/1 clarifications instead.

---

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope / Deliverables, Acceptance criteria, References) | 4 decomposed | ROWS: C=8 R=3 G=1 AC=3`

*"References" carries no requirement — it is decomposed as the evidence pointer (PLAN §4.1, §4.3, §2)
used throughout this analysis. C rows are constraints surfaced from the rulebook scan (the ticket has no
Constraint section); they are binding on the change and are listed so every hunk can trace to a row.*

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | "Language-neutral driver for long-lived adapters over JSONL (§4.1, §4.3)." | One core module owns the subprocess lifecycle and the JSONL framing for **every** language. It learns which language it is driving only from configuration and from what the adapter itself advertises — never from a literal in the core. | `code_atlas/adapter.py:1` is a one-line stub; zero importers repo-wide (`grep -rn "adapter" code_atlas/` → only the stub + prose in `contract.py`); `PLAN.md:79-85` (§4.1 protocol), `PLAN.md:101-111` (§4.3 Protocol shape) | **5/5** (items 1, 2, 3, 13, 14) | **5/5** — one generic driver + lookup shipped; 32 adapter tests and 23 language-agnostic assertions green | ✅ |
| R1 | Scope / Deliverables | "`adapter.py`: `LanguageAdapter` Protocol (`name`, `extensions`, `capabilities`, `start/parse/stop`)." | A `typing.Protocol` (not an ABC — `CONVENTION.md:73`) with the **6** members of inventory A. `capabilities` is advertised-not-required (R1.6); `contract.Capabilities` / `KNOWN_CAPABILITIES` already exist (`contract.py:90-91`) and must be reused, not re-declared. | `PLAN.md:103-110` gives the exact member list; `contract.py:89-91` already types capabilities; `CONVENTION.md:73` mandates `Protocol` over ABC for this seam | **3/3** (items 1, 4, 8) | **3/3** — 6 members present; a class missing one is not a `LanguageAdapter`; capabilities pass through | ✅ |
| R2 | Scope / Deliverables | "Subprocess driver: spawn adapter in `--server` mode, feed newline-delimited requests, read JSONL results, handle `ok:false` per file without breaking the stream." | One generic concrete class implementing R1 over `subprocess.Popen`: launch from `config.adapter_cmd(lang)`, write one compact JSON line per request, read one JSONL line per response, and map each of the **9** failure modes of inventory B to fail-soft (a failed `ParseResult`) or fail-loud (raise), never to a hang or a corrupted stream. | `PLAN.md:81-85` shows the wire format; `config.py:126-142` already resolves `CA_<LANG>_CMD` generically; `contract.py:112-141` `validate()` returns errors instead of raising precisely so this boundary can keep going (R5.1) | **5/5** (items 2, 5, 6, 7, 11) | **5/5** — 9-mode classifier; argv resolved by config; suite 236 passed | ✅ |
| R3 | Scope / Deliverables | "Extension→adapter lookup (**not** a registry yet — YAGNI until adapter #2)." | A plain `dict[str, LanguageAdapter]` built by the caller plus **one** module-level function that maps a path to an adapter or `None`. No registry class, no plugin discovery, no entry-points, no base class, no factory (R1.2, R7.4). Lowercased last suffix is the key; two adapters claiming one extension is a loud config error (R5.3). | `ENGINEERING_RULES.md:20-22` (R1.2 — no registry until adapter #2); `PLAN.md:111` ("That's the only registry — built when the 2nd adapter exists, not before") | **2/2** (items 3, 8) | **2/2** — index built from announced suffixes; 6 lookup cases; a twice-claimed suffix raises | ✅ |
| AC1 | Acceptance criteria | "Driver survives a per-file parse error (returns error result, stream continues)." | Falsifiable as: for **each** of the inventory-B failure modes (**9** — 8 at Gate 1, B9 added by a design-time spike), assert the driver's classification **and** that the request immediately after it still returns a valid result on the **same** process. Proven for the whole inventory, not for `ok:false` alone — spikes S-2/S-5 showed a garbage stdout line and an `ok:false` result behave identically to the caller but arrive by different code paths. | Spike S-2 (`ok:false` → next request ok) and S-5 (non-JSON line → `JSONDecodeError`, next request ok) below | **3/3** (items 2, 6, 7) | **3/3** — 8 of 9 modes proven on one process, each followed by a good parse (B7 excluded) | ✅ |
| AC2 | Acceptance criteria | "One process boot amortized across many files; clean `stop()`." | Two halves, both vague as written and pinned by Q8: (a) **boot count == 1** across **≥ 200** `parse()` calls, measured by a boot counter the fake adapter writes plus a stable `pid` — not by "it felt fast"; (b) **clean `stop()`** = stdin closed → child exits → `returncode` observed → escalation `terminate()` → `kill()` for a child that ignores EOF → `stop()` is idempotent and leaves no orphan. Spike S-6 proves the escalation is **required**, not defensive. | Spike S-1 (1 boot / 201 requests / stable pid / 0.02 s) and S-6 (a child that ignores EOF needs `terminate()`, exit `-15`) | **3/3** (items 2, 6, 7) | **3/3** — 1 boot over 200 parses, pid stable, `stop()` clean/escalating/idempotent (mutations M2, M4 red) | ✅ |
| AC3 | Acceptance criteria | "No `if language == …` branches; adapters resolved purely by extension." | Stronger than the CI regex, which only catches one spelling. Falsifiable as **both**: (a) the CI R1.1 gate is clean over all 11 core modules; (b) **no language name literal** (`php`, `typescript`, `javascript`, `python`, `csharp`, `dotnet`) appears anywhere under `code_atlas/` — greppable, and it is the claim the ticket actually makes. (b) is what forbids a `PhpAdapter` class in the core (ratified Q7). | `.github/workflows/ci.yml:49` (the gate's exact regex); `ENGINEERING_RULES.md:17-19` (R1.1), `:32-33` (R1.5 — "the litmus test is R1.1") | **2/2** (items 3, 9) | **2/2** — zero language names and zero branches over 11 core modules; negative-controlled (NC1, NC2) | ✅ |
| C1 | rulebook scan | R1.1 / R1.5 — zero language branches; every adapter substitutable behind the contract. | One driver class serves every language; the language name is data (`config.adapter_cmds` key), never a type. `PLAN.md:111`'s "Concrete: `PhpAdapter`" and `CONVENTION.md:44`'s `PhpAdapter, TsAdapter, PythonAdapter, CSharpAdapter` both point the other way; **Q7 ratified the generic class**, so both are corrected in this diff. | `ENGINEERING_RULES.md:17-19`, `:32-33`; conflicting `PLAN.md:111`, `CONVENTION.md:44` | **5/5** (items 2, 3, 9, 13, 14) | **5/5** — guard + CI regex re-run locally; docs corrected so no per-language class is prescribed | ✅ |
| C2 | rulebook scan | R1.2 / R7.4 — one seam only; no dead abstractions. | Ship the Protocol + **one** implementation + one lookup function. No `AdapterRegistry`, no `BaseAdapter`, no DI, no capability-negotiation framework. If the Protocol ends up with exactly one implementer and no near-term second, R7.4 still keeps it — it **is** the one seam the rulebook names (R1.2), so this is the documented exception, not an accident. | `ENGINEERING_RULES.md:20-22`, `:102-103`; `PLAN.md:50` (counter-principle) | **2/2** (items 1, 3) | **2/2** — one Protocol, one implementation, two functions; no registry, base class or factory added | ✅ |
| C3 | rulebook scan | R1.3 / R1.4 — one-way dependency; SRP per component. | `adapter.py` imports `contract` + stdlib only. It must **not** import `store`, `indexer`, `resolver`, or `config` (config flows **in** as a value — `CONVENTION.md:74`). It parses/transports only; it never persists and never decides `parsed_ok` (that is `indexer`'s, per task 009's AC). | `ENGINEERING_RULES.md:23-31`; `CONVENTION.md:74`; `docs/tasks/009_full-build-indexer.md:22` | **2/2** (items 1, 2) | **2/2** — `adapter.py` imports `contract` + stdlib only; no SQL (SQL-confinement guard still green) | ✅ |
| C4 | rulebook scan | R1.6 — optional power via capability flags; the core degrades when a capability is absent. | `capabilities` is a pass-through `dict[str, bool]` typed as `contract.Capabilities`. An **absent** flag is legal, an **unknown** flag is legal (forward compatibility with a richer adapter), and the driver must never require one. Falsifiable: an adapter advertising `{}` and one advertising `{"semantic_types": true, "future_thing": true}` both drive identically. | `ENGINEERING_RULES.md:34-36`; `contract.py:89-91` (`KNOWN_CAPABILITIES` is "advertised, never required") | **4/4** (items 1, 2, 4, 7) | **4/4** — absent, empty and unknown-flag capabilities all drive identically | ✅ |
| C5 | rulebook scan | R3.2 — `contract.py` is the single source of truth; consumers never re-declare field lists. | `adapter.py` is **already** in the R3.2 guard's consumer list (`tests/test_contract_sole_source.py:27`), so the guard fires on this diff for the first time with real content. `ParseResult` mirrors `contract.RESULT_FIELDS` (`contract.py:70`) and node/edge rows stay opaque `list[dict]` pass-throughs — the driver never names a node field. | `ENGINEERING_RULES.md:53-54`; `tests/test_contract_sole_source.py:27,57-65` | **3/3** (items 1, 4, 10) | **3/3** — R3.2 guard fires on real content for the first time and is negative-controlled (NC3) | ✅ |
| C6 | rulebook scan | R5.1 / R5.3 — fail soft on data errors, fail loud on config/programmer errors. | This is the whole substance of inventory B: a bad **file** never breaks the stream (R5.1); a bad **command**, a dead process, or a contract-version mismatch raises (R5.3). Spike S-10 confirms a missing command raises `FileNotFoundError` at spawn; spike S-4 confirms a dead child is detectable (`readline()` → `''`, `poll()` → exit code). | `ENGINEERING_RULES.md:72-78`; spikes S-4, S-10 | **4/4** (items 2, 5, 6, 7) | **4/4** — 5 soft modes vs 4 loud ones asserted; bad command, dead child, desync, bad handshake all raise | ✅ |
| C7 | rulebook scan | R6.1 / R6.2 / R6.4 — no task is done without tests; fixtures are spec-driven; guardrails are real tests. | No adapter exists (007 depends on **this** task), so every test drives a **fake adapter** speaking the protocol. It must be spec-driven — it encodes §4.1's wire format and nothing about PHP — and the AC3 grep guard must be negative-controlled so it cannot pass vacuously (LESSONS 002 + LESSONS 004: existence ≠ behaviour). | `ENGINEERING_RULES.md:82-92`; `LESSONS.md` (002 vacuous guard, 004 existence-vs-behaviour); `docs/tasks/007_php-adapter-visitor.md:8` (`depends_on: [006, 005]`) | **5/5** (items 6, 7, 8, 9, 10) | **5/5** — real subprocesses, no mocks; fixture asserted against the contract; 3 guards + 4 mutations red on demand | ✅ |
| C8 | rulebook + `CLAUDE.md` scan | R7.2 + "Docs before PR" / "Token usage on PR". | Every ratified decision that changes `PLAN.md:79-111` (§4.1 request/response shape, §4.3 Protocol + `PhpAdapter`), `PLAN.md:242-247` (§9 `CA_PHP_CMD` form), `CONVENTION.md:44` (adapter class names) and `CONVENTION.md:83-90` (§5 adapter conventions) lands **in this diff**, plus BACKLOG status + frontmatter + the token row. | `ENGINEERING_RULES.md:98-99`, `:117-121`; `CLAUDE.md` "Docs before PR"; `LESSONS.md` 001 (untraceable hunks) | **4/4** (items 12, 13, 14, 15) | **4/4** — PLAN §4.1/§4.3/§9/§11, CONVENTION §2/§5, README, BACKLOG + frontmatter updated in this diff | ✅ |

Status legend: ✅ done/proven · ⚠ deferred (needs follow-up ticket) · ❌ not met · ⬜ not yet started (Phase 1).

## Spikes (read-only, run during analysis)

Ten runtime assumptions were checked against the project's own interpreter before any of them was
asserted as fact, because four of the questions below are claims *about `subprocess`*, not about our
code. Script: scratchpad `spike/{fake_adapter.py,spike.py,spike2.py,chatty.py}` — nothing in the repo was
touched.

| # | Claim under test | Result |
|---|---|---|
| S-1 | One boot amortises across many files | **1 boot / 201 requests**, `pid` stable, 0.02 s total; non-ASCII (`Ü`) round-trips under `encoding="utf-8"` |
| S-2 | `ok:false` does not break the stream | `ok:false` + `error` returned; the **next** request on the same process returns `ok:true` |
| S-3 | Closing stdin is a clean stop | child's `for line in sys.stdin` ends → exit code **0**, `wait(timeout=)` returns |
| S-4 | A child that dies mid-stream is detectable | `readline()` → `''` (EOF), `poll()` → `3`; the **first** `write`+`flush` after death already raises `BrokenPipeError` (it is not swallowed) |
| S-5 | A non-JSON stdout line | `json.loads` → `JSONDecodeError`; the stream itself survives — the request after it returns a correct result |
| S-6 | A child that ignores EOF | `wait(timeout=1)` → `TimeoutExpired`; `terminate()` → `-15`. **Escalation is required, not defensive** |
| S-7 | A very large single line | 2.27 MB / 20 000 nodes on one `readline()` in 0.05 s — no framing change needed |
| S-8 | `stderr=PIPE` left undrained | **DEADLOCK.** A child writing 200 KB to stderr blocks; the driver blocks reading stdout; no response in 3 s. `DEVNULL` and a file both respond normally; `stderr=STDOUT` **corrupts the protocol stream** (first stdout line is 200 KB of noise) |
| S-9 | `cwd=` + repo-relative paths | honoured; the adapter echoes the repo-relative path unchanged |
| S-10 | A missing adapter command | `FileNotFoundError` at `Popen` — loud by default (R5.3) |
| S-12 | Undecodable UTF-8 on stdout (run at **Gate 2**, for the design) | `errors="strict"` raises `UnicodeDecodeError` on that line and the **next** request still returns correctly; `errors="replace"` yields `"syntax �� error"` which **parses as valid JSON**. Added inventory mode B9 (soft) and rejected alternative 4 |
| S-11 | `shlex.split` on the documented command strings | `'docker compose exec -T php php'` → correct. **`r'C:\php\php.exe'` → `['C:phpphp.exe']`** — POSIX-mode `shlex` eats the backslashes of the exact value `PLAN.md:244` documents |

## AC validation

Every acceptance value independently re-derived. Eleven values checked; **7 mismatches or
non-falsifiable values**, each raised below as a Gate-1 question carrying the computed value — none
silently corrected.

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| R1 | Protocol members: `name`, `extensions`, `capabilities`, `start/parse/stop` — reads as 4 items | **6 members** (inventory A): 3 attributes + 3 methods. Matches `PLAN.md:103-110` exactly | Y (once expanded) | measurable — `typing.get_type_hints` + `hasattr`/`callable` per member | — |
| R1 | `extensions: tuple[str, ...]` — **nothing anywhere says where the values come from** | Neither `config.py` nor `contract.py` nor `PLAN.md` defines a source. `config.adapter_cmds` is keyed by language name (`config.py:126-142`) and carries **no** extension data; `PLAN.md:225` ("`git ls-files` per adapter's extensions") *consumes* the list without saying who produces it | **N** — an undefined input to a mandatory field | not falsifiable until the source is chosen | **RATIFIED (Q1)** — the adapter advertises them in a **handshake** read at `start()`; it is also the only source that gives `capabilities` a real channel |
| R2 | "spawn adapter in `--server` mode" | The command that reaches the core is a **string** (`config.py:58-60` → `str`). `PLAN.md:244-245` documents `CA_PHP_CMD="C:\\php\\php.exe"` and `"docker compose exec -T php php"` — **neither includes the adapter entry script**, so appending `--server` alone produces `php --server`, which is not a runnable adapter. Completing it would require the core to know `adapters/php/index.php` — a language name in the core, banned by AC3 | **N** — §9's documented values cannot launch an adapter | measurable once the form is pinned | **RATIFIED (Q2)** — `CA_<LANG>_CMD` is the **complete argv**, server mode included (`php adapters/php/index.php --server`); the core appends nothing and `PLAN.md:244-245` is corrected in this diff |
| R2 | command string → argv | POSIX `shlex.split` destroys the Windows value `PLAN.md:244` documents: `r'C:\php\php.exe'` → `['C:phpphp.exe']` (spike S-11) | **N** — the documented value is silently mangled | measurable (assert the argv for each documented form) | **RATIFIED (Q3)** — accept a **list** in `.code-atlas.toml`'s `[adapter_cmd]`; a string splits with `shlex.split(..., posix=(os.name != "nt"))` |
| R2 | "read JSONL results" — stderr disposition unstated | **`stderr=PIPE` undrained deadlocks the driver** (spike S-8: 200 KB of adapter stderr, no response in 3 s) and `stderr=STDOUT` corrupts the protocol stream. nikic's `ErrorHandler\Collecting` and any PHP warning make a chatty adapter the normal case, not the exotic one | **N** — an unstated choice with a hang as its default failure | measurable (a 200 KB-stderr fake must still get a response) | **RATIFIED (Q4)** — `DEVNULL` by default, opt-in redirect to a file under `.code-atlas/`; **never** an undrained `PIPE`, never `STDOUT` |
| R2 | "without breaking the stream" — for which failures? | The ticket names one failure (`ok:false`). **8 distinct per-request failure modes** exist (inventory B), and they split across R5.1 (fail soft) and R5.3 (fail loud) — a driver that handles only `ok:false` hangs on a hung child and loops on a dead one | **N** (ticket undercounts by 7) | measurable per mode | **RATIFIED (Q5)** — AC1's denominator is inventory B (**8** at Gate 1, **9** after the Gate-2 spike S-12); B7 (hang) is deferred to task 009 as a recorded exclusion |
| R2 | per-request timeout | **Not mentioned anywhere in the ticket or the plan.** A hung adapter blocks the build forever; blocking `readline()` has no timeout, and `select` does not work on Windows pipes, so a timeout costs a reader thread | **N** (unstated) | measurable once decided (a deliberately hanging fake must not hang the suite) | **RATIFIED (Q5)** — recorded as an explicit **coverage-gap exclusion, deferred to task 009**, which owns the fan-out and can kill a worker; no threaded reader is built before it is needed (R7.1) |
| R2 | contract-version handshake | `contract.py:16` freezes `CONTRACT_VERSION = 1` and `PLAN.md:99` says the version travels "in meta" — but **no meta message is defined** in §4.1, and `contract.py` has no validator for one. If Q1 adds a handshake, the meta message is specified for the first time | **N** (a named artifact that does not exist) | measurable (a handshake asserting a wrong version must raise) | **RATIFIED (Q6)** — define the meta message, **keep `CONTRACT_VERSION = 1`** (no frozen vocabulary changes — R3.1 names node/edge vocabulary, fields, qname), extend `tests/contract/` in this diff; a mismatched version raises at `start()` |
| AC1 | "survives a per-file parse error … stream continues" | Falsifiable exactly as written **only** for `ok:false`. Pinned to inventory B: per mode, assert the classification **and** that the next request on the same process succeeds | Y (once the denominator is B) | measurable | — (denominator pinned by Q5) |
| AC2 | "One process boot amortized across **many** files" | "many" is a vague adjective with no number. Computed pin: **≥ 200 `parse()` calls, boot count == 1**, `pid` unchanged — measured by a counter the fake adapter appends to, not by timing. Spike S-1 proves 201 calls / 1 boot / 0.02 s is achievable | **N** — not falsifiable as written | **now falsifiable** — a counted assertion | **RATIFIED (Q8)** — the pin above |
| AC2 | "clean `stop()`" | Vague adjective. Computed pin (4 falsifiable clauses): stdin closed → child exits; `returncode` observed (not `None`); a child that ignores EOF is escalated `terminate()` → `kill()` (spike S-6 proves it is needed); `stop()` is idempotent and safe after the child already died | **N** — not falsifiable as written | **now falsifiable** | **RATIFIED (Q8)** — the 4 clauses above |
| AC3 | "No `if language == …` branches" | The CI regex (`ci.yml:49`) catches one spelling and, per LESSONS 003, also fires on prose. The **real** claim is "adapters resolved purely by extension", falsifiable as: **zero** language-name literals under `code_atlas/` (`php\|typescript\|javascript\|python\|csharp\|dotnet`, case-insensitive, excluding the word "Python" as the host language in docstrings) | partially | measurable **only** with a negative control (the grep passes today over an empty module) | **Q7** + self-resolved **S7** — the guard must be negative-controlled (LESSONS 002) |
| AC3 | "adapters resolved purely by extension" vs `PLAN.md:111` / `CONVENTION.md:44` | The plan names a concrete **`PhpAdapter`** class and CONVENTION §2 fixes four per-language class names. A `PhpAdapter` in `code_atlas/` is a language name in the core; in `adapters/php/` it would be Python code inside a PHP adapter | **N** — the docs and the AC contradict each other | measurable once resolved | **RATIFIED (Q7)** — **one generic class**; `PLAN.md:111` + `CONVENTION.md:44` corrected in this diff |

**No AC carries a `✅` at Phase 1** — nothing is built yet. Three acceptance values are **not falsifiable
as written** (AC2's "many files", AC2's "clean `stop()`", AC1's undefined failure denominator); Q8 and Q5
pin each to a measurable form, so **every acceptance value becomes falsifiable once Gate 0 clears**.
**Manual-check exclusions: none.** **Coverage-gap exclusions (recorded up front, not discovered later):**

1. **Per-request timeout / hung-adapter recovery (inventory B7)** — **deferred to task 009, ratified
   (Q5, 2026-07-31)**. This task therefore ships with **no** protection against a hung adapter, recorded
   here rather than implied by a green suite.
2. **Windows behaviour of the whole driver** — the host is Linux (`Platform: linux`); `PLAN.md:244`
   documents a Windows `CA_PHP_CMD` we cannot execute here. Q3's argv policy is asserted at the
   *splitting* level only; end-to-end Windows launch is unverifiable in this environment and is a
   human/CI matter, not a silent pass.

**Uncodified-standard items surfaced (never silently applied, never silently dropped):**

1. **The rulebook has no subprocess/process-management section, and this ticket is a process driver.**
   Per the rule-section coverage step, the change type makes such a section mandatory —
   `docs/ENGINEERING_RULES.md` §1–§8 covers none of: stderr disposition, kill escalation, timeout policy,
   argv construction, or version-handshake policy. Q3–Q6 are each *a going-forward standard being chosen
   for the first time*. Route them through `/mango:codify` provisional→ratify if they should become rules;
   until ratified they do **not** gate-block.
2. **`ruff format` is applied by habit but is not a codified standard.** CI runs `ruff check` only
   (`ci.yml:29-30`); `ruff format --check .` reports **4 files unformatted** on untouched `main` — up from
   **2** at task 004, so the drift is growing. Not a baseline failure and must not gate-block; if the
   formatter should be binding, codify it and add it to CI as its own change.
3. **`CLAUDE.md` and `BACKLOG.md` still name a working-doc file this project does not use.** Both point
   the cost ledger at `docs/tasks/NNN_slug.work.md` (`BACKLOG.md:51`), but `work_doc_mode` is `embed`.
   Task 004 recorded this as a docs-truth candidate and it was **not** fixed, so it is re-surfaced here —
   traced to C8, still not silently absorbed.

## Inventory (universal "all/every/no" requirements)

Three counted denominators. R1 and AC1 are "do X for each of N" requirements → the lists below **are** the
per-item checklists; review must confirm every row, not a total.

### Inventory A — `LanguageAdapter` Protocol members (R1) · **Denominator N = 6**

| # | Member | Kind | Source of its value | Ph3/4 proven by | Status |
|---|--------|------|---------------------|-----------------|--------|
| 1 | `name` | attribute `str` | the `CA_<LANG>_CMD` key (`config.py:126-142`) — or the handshake (Q1) | ✅ | ✅ |
| 2 | `extensions` | attribute `tuple[str, ...]` | the **handshake** read at `start()` (Q1) | ✅ | ✅ |
| 3 | `capabilities` | attribute `contract.Capabilities` | handshake, pass-through (R1.6, C4) | ✅ | ✅ |
| 4 | `start()` | method `-> None` | spawns the process; loud on a bad command (S-10) | ✅ | ✅ |
| 5 | `parse(path)` | method `-> ParseResult` | one request line, one response line (S-1) | ✅ | ✅ |
| 6 | `stop()` | method `-> None` | EOF → `terminate()` → `kill()`, idempotent (S-3, S-6) | ✅ | ✅ |

### Inventory B — per-request failure modes the driver must classify (R2 / AC1) · **Denominator N = 9**

**Amended at Gate 2 (8 → 9):** design spike S-12 found a mode the analysis missed — an adapter emitting
**undecodable bytes** on stdout. The denominator is raised out loud rather than the new mode being folded
in silently, because N is what later phases prove against.

Each mode is either **soft** (a failed `ParseResult`, stream continues — R5.1) or **loud** (raises — R5.3).
A mode with neither a proof nor a recorded exclusion makes AC1 incomplete.

| # | Failure mode | Proposed class | Evidence | Ph3/4 proven by | Status |
|---|--------------|----------------|----------|-----------------|--------|
| 1 | Adapter returns `ok:false` + `error` | soft | S-2 | ✅ | ✅ |
| 2 | Result is well-formed JSON but fails `contract.validate()` | soft | `contract.py:112-118` returns errors so the caller can continue | ✅ | ✅ |
| 3 | Stdout line is not JSON at all | soft | S-5 (stream itself survives) | ✅ | ✅ |
| 4 | Response `path` ≠ requested `path` (desync) | **loud** | closed by S3's lock-step: a desync misattributes **every** later result, so it is silent data corruption, not one bad file | ✅ | ✅ |
| 5 | Blank / empty line on stdout | soft (skip and re-read) | S-5 mechanism | ✅ | ✅ |
| 6 | Child died mid-stream (`readline()` → `''`) | **loud** | S-4 (`poll()` → exit code; next write raises `BrokenPipeError`) | ✅ | ✅ |
| 7 | Child hangs and never answers | **deferred to task 009** (Q5 — recorded coverage-gap exclusion 1) | no timeout exists on blocking `readline()`. **Widened at Phase 3:** execute proved the hang also reaches `start()` — a live but mute adapter blocks the handshake read forever | **not proven — excluded** | ⚠ |
| 8 | Command missing / not executable at `start()` | **loud** | S-10 (`FileNotFoundError`) | ✅ | ✅ |
| 9 | Stdout line is not decodable UTF-8 | **soft** | S-12 (Gate 2): `errors="strict"` raises `UnicodeDecodeError` on that line and the **next** request still returns correctly; `errors="replace"` instead yields mojibake that parses as valid JSON — silent corruption | ✅ | ✅ |

### Inventory C — core modules the AC3 "no language branch / no language name" claim ranges over · **Denominator N = 11**

`code_atlas/{__init__,adapter,config,contract,gitutil,ignore,indexer,main,resolver,store}.py` +
`code_atlas/tools/__init__.py`. The count is asserted today by `tests/test_sql_confinement.py:34`
(`len(core_modules()) == 11`) — **this task adds no new core module** (`adapter.py` already exists as a
stub), so that assertion must stay at 11 and is a free negative control on the file list.

### Surface inventory

**N/A — TRACK is backend.** No reachable UI surface exists in this repo (no routes, templates, or frontend
entry points; `code_atlas/tools/` is an MCP tool surface, not a rendered one).

## Clarifications

`CLARIFICATION: 20 raised | 20 resolved (11 self-resolved+cited · 9 human-ratified at Gate 0) | 0 for human decision`

**Gate 0: CLEARED** — the user ratified all nine recommendations ("ratify all", 2026-07-31). None reverses
a prior decision. Q1, Q2 and Q7 each **amend a doc** (`PLAN.md:79-85`, `:101-111`, `:244-245`;
`CONVENTION.md:44`, `:83-90`), so those corrections ride the Phase-2 change-list (R7.2 / C8) rather than
being applied silently to code. Q1+Q6 together add the meta/handshake message to `contract.py` and
`tests/contract/` in the same diff (R3.1).

**Self-resolved (cited):**

1. **S1 — `adapter.py` imports `contract` + stdlib only.** No `store`, `indexer`, `resolver`; `config`
   flows in as a value, it is not reached out to. *R1.3 (`ENGINEERING_RULES.md:23-25`), R1.4 (`:26-31`),
   `CONVENTION.md:74`.*
2. **S2 — the driver validates each result; the *indexer* decides `parsed_ok`.** `contract.validate()`
   returns errors rather than raising precisely so this boundary can degrade (R5.1), and task 009's AC
   owns the `files.parsed_ok=0` write. *`contract.py:112-118`; `docs/tasks/009_full-build-indexer.md:22`.*
3. **S3 — lock-step request/response, no pipelining.** One write, one read, assert the echoed `path`.
   Parallelism is **N processes** (`PLAN.md:227`), not N in-flight requests on one pipe; pipelining would
   add correlation state for no gain and make ordering non-deterministic (R4.2). *`PLAN.md:227`,
   `ENGINEERING_RULES.md:65-67`.*
4. **S4 — the driver sends the repo-relative path and sets `cwd` to the repo root.** Stored paths are
   repo-relative "always (even under Docker path mapping)", and task 008 owns the container mapping —
   this task must not pre-empt it. *`CONVENTION.md:67`; `docs/tasks/008_php-runtime-modes.md:15-17`;
   spike S-9.*
5. **S5 — no `CONTRACT_VERSION` bump for the vocabulary.** No node kind, edge kind, field, or qname
   convention changes. Whether the *meta/handshake message* counts was asked, not assumed — **Q6
   ratified: it stays at 1**. *R3.1 (`ENGINEERING_RULES.md:51-52`); `contract.py:16`.*
6. **S6 — a missing or unset `CA_<LANG>_CMD` fails loud at `start()`.** Spike S-10 shows `Popen` already
   raises; the driver adds a message naming the variable. Task 008's AC ("clear error if `CA_PHP_CMD` is
   unset/invalid") is then *tested* there per runtime mode, not re-implemented. *R5.3 (`:77-78`);
   `docs/tasks/008_php-runtime-modes.md:20`.*
7. **S7 — the AC3 grep guard is negative-controlled rather than trusted.** It passes today over an empty
   `adapter.py`, i.e. vacuously (exactly task 002's failure). Assert its inputs are non-empty
   (`len(core_modules()) == 11`, driver module > N lines), inject a real violation, confirm red, restore
   from a `cp` copy — **not** `git checkout --`. *`LESSONS.md` 002 and 004 (`git checkout --` deleted
   uncommitted work).*
8. **S8 — the fake adapter is a protocol fixture, not a language fixture.** It encodes §4.1's wire format
   only; it must contain no PHP, no framework, no repo name. It lives under `tests/fixtures/` (not
   `adapters/`) so it does not turn `test_sql_confinement.py:52`'s deliberate 0/0 skip green while no real
   adapter exists. *R2.2 (`:43-44`), R6.2 (`:86-88`), `tests/test_sql_confinement.py:44-56`.*
9. **S9 — `ParseResult` is a frozen dataclass mirroring `contract.RESULT_FIELDS`; nodes/edges stay opaque
   `list[dict]`.** The driver never names a node/edge field, so the R3.2 guard stays satisfied when it
   fires on `adapter.py` for the first time. *R3.2 (`:53-54`); `contract.py:70`;
   `tests/test_contract_sole_source.py:27`.*
10. **S10 — UTF-8 strict, `\n` framing, compact JSON, flush per request.** Spike S-1 round-trips non-ASCII;
    S-7 shows a 2.27 MB single line is fine, so no length framing is needed. *Spikes S-1, S-7;
    `PLAN.md:81-85`.*
11. **S11 — the driver adds no wall-clock, randomness, or set ordering.** It is a pass-through; identical
    adapter output ⇒ identical `ParseResult` (R4.2 is preserved by *not* enriching). *R4.2 (`:65-67`).*

**Human-ratified at Gate 0 — 9 items (each was asked with a recommendation; all recommendations adopted
verbatim, 2026-07-31). The "Recommended" option in each item below *is* the ratified decision; the
rejected alternatives are kept so Phase 2 does not re-litigate them and the reviewer can see the
trade-off that was made:**

- **Q1 — Where does `extensions` come from?** *(blocking)* R1 mandates the attribute; nothing in the repo
  produces it. `config.adapter_cmds` carries only `lang → command` (`config.py:126-142`).
  - **(a) Recommended — the adapter advertises it in a handshake.** On `start()` the driver reads one
    meta line: `{"name": …, "extensions": […], "capabilities": {…}, "contract_version": 1}`. This is the
    only source that keeps **`capabilities` honest too** (R1.6 needs the adapter to advertise, and there
    is otherwise no channel for it), keeps zero language knowledge in the core (AC3), and `PLAN.md:99`
    already says the version travels "in meta" — so the message is being *specified*, not invented. Cost:
    §4.1 gains a message shape, `tests/contract/` gains a case (→ Q6), and a language's extensions can
    only be known after its adapter boots (fine: `PLAN.md:225` collects files *per adapter*, after start).
  - (b) Config declares them: a `[adapter_ext]` table / `CA_<LANG>_EXT`. Cheap and needs no protocol
    change, but it duplicates knowledge the adapter already has, makes a misconfiguration silently skip
    every file of a language, and leaves `capabilities` with no source at all.
  - (c) A static map in the core. **Rejected** — a language name in the core, banned by AC3 and R1.1.
- **Q2 — What exactly is `CA_<LANG>_CMD`?** *(blocking)* `PLAN.md:244-245`'s documented values
  (`C:\php\php.exe`, `docker compose exec -T php php`) contain **no adapter entry script**, so the core
  cannot complete them without knowing `adapters/php/index.php` — a language name in the core.
  - **(a) Recommended — it is the complete argv, server mode included**, e.g.
    `CA_PHP_CMD="php adapters/php/index.php --server"` and
    `CA_PHP_CMD="docker compose exec -T php php /app/adapters/php/index.php --server"`. The core appends
    **nothing**: no entry path, no mode flag, no layout assumption. Cost: correct `PLAN.md:244-245` and add
    the rule to `CONVENTION.md:83-90` (§5) in this diff; each adapter's README documents its own launch
    string, which is exactly R8.1.
  - (b) The core appends `--server` only. Then §9's values still cannot launch anything, and the entry
    script has to come from somewhere else anyway.
  - (c) The core appends `adapters/<lang>/index.php --server`. **Rejected** — hard-codes both the repo
    layout and a per-language file name into the core.
- **Q3 — How is a command *string* turned into argv?** POSIX `shlex.split(r'C:\php\php.exe')` returns
  `['C:phpphp.exe']` (spike S-11) — it silently mangles the exact Windows value `PLAN.md:244` documents.
  - **Recommended:** accept a **list** in `.code-atlas.toml`'s `[adapter_cmd]` (unambiguous, no quoting
    rules) and, for a string, split with `posix=(os.name != "nt")`. A string whose first token does not
    resolve to an executable fails loud with the variable named (R5.3). Cost: `config.py:126-142`'s
    `_as_text` gains a list form; documented in `CONVENTION.md` §2's env-var bullet.
  - Alternative: require the list form everywhere. Cleanest, but `CA_<LANG>_CMD` is an env var and cannot
    carry a list, so a string path must exist regardless.
- **Q4 — What happens to the adapter's stderr?** *(blocking — the default choice hangs)* Spike S-8:
  `stderr=PIPE` left undrained **deadlocks** after ~64 KB; `stderr=STDOUT` corrupts the protocol stream.
  A PHP adapter emitting warnings or `ErrorHandler\Collecting` diagnostics makes this the normal case.
  - **Recommended:** `stderr=DEVNULL` by default, with an opt-in redirect to a file under `.code-atlas/`
    (a knob task 009/010 can surface) for debugging. No reader thread — that is complexity this task does
    not need (R7.1), and the adapter's own `--file` mode (`CONVENTION.md:85`) is the debugging path.
    Falsifiable: a fake adapter writing 200 KB to stderr must still get a response.
  - Alternative: always redirect to `.code-atlas/adapter-<lang>.stderr`. More debuggable, but it creates a
    file per run and needs a rotation/cleanup answer this task would rather not own.
- **Q5 — Timeout policy for a hung adapter, and AC1's denominator.** Blocking `readline()` has no timeout;
  `select` does not work on Windows pipes, so a timeout costs a reader thread.
  - **Recommended:** AC1's denominator is inventory B's **8** modes; mode **B7 (hang) is deferred to task
    009** and recorded as coverage-gap exclusion 1 — 009 owns the worker fan-out and can kill a worker
    process wholesale, which is the natural place for a deadline. Ship 005 with no timeout, said out loud.
  - Alternative: implement a reader-thread timeout now. It is the safer runtime, but it is a threading
    mechanism built before any hang has been observed, against R7.1.
- **Q6 — Does the handshake bump `contract_version`?** If Q1(a) is ratified, the meta message is defined
  for the first time; `contract.py:16` is frozen at `1` and the store already persists it.
  - **Recommended:** **keep `CONTRACT_VERSION = 1`.** R3.1 requires a bump for *node/edge vocabulary,
    fields, or qname convention* — none changes, and `PLAN.md:99` already promised a meta carrying the
    version, so this specifies an anticipated message rather than altering a frozen one. Add
    `META_FIELDS` + `validate_meta()` to `contract.py` (R3.2) and a case to `tests/contract/` in this diff
    (R3.1's "conformance tests updated in the same change"). A handshake reporting a *different* version
    raises at `start()` (R5.3).
  - Alternative: bump to 2. Defensible and cheap today (no adapter exists to break), but it spends the
    version signal on a change no adapter can observe, and task 019 already earmarks v2 for the real
    protocol change (`PLAN.md:113-118`).
- **Q7 — One generic driver class, or `PhpAdapter`?** *(blocking)* `PLAN.md:111` says "Concrete:
  `PhpAdapter` (drives the nikic sidecar)" and `CONVENTION.md:44` fixes four per-language class names —
  both contradict AC3 and R1.1.
  - **Recommended: one generic class** (working name `SubprocessAdapter`) constructed with
    `(name, command)` from `config.adapter_cmds`; **no per-language class anywhere in `code_atlas/`**.
    Correct `PLAN.md:111` and `CONVENTION.md:44` in this diff (C8). Rationale: a `PhpAdapter` in the core
    is a language name in the core; in `adapters/php/` it would be Python inside a PHP adapter; and per
    R1.2/R7.4 a second class with identical behaviour is a dead abstraction.
  - Alternative: keep `PhpAdapter` as a thin subclass fixing `name`/`extensions`. It re-introduces exactly
    the per-language type the litmus test (R1.5) forbids, for zero behaviour.
- **Q8 — Pin AC2's two vague values.** "many files" and "clean `stop()`" are adjectives, not thresholds.
  - **Recommended:** (a) **≥ 200 `parse()` calls with boot count == 1** and an unchanged `pid`, measured by
    a counter the fake adapter appends to on startup — spike S-1 shows 201 calls / 1 boot / 0.02 s is
    comfortably achievable; (b) **clean `stop()` = 4 clauses**: stdin closed → child exits; `returncode`
    is observed (not `None`); a child ignoring EOF is escalated `terminate()` → `kill()` (spike S-6 proves
    the escalation fires); `stop()` is idempotent and safe after the child already died.
  - Alternative: assert wall-clock timing instead of a boot counter. **Rejected** — timing is flaky in CI
    and it measures the wrong thing; a boot counter measures the actual claim.
- **Q9 — Where does the fake adapter live, and does it become the conformance harness?** No adapter exists
  (007 depends on this task), so every test needs a double.
  - **Recommended:** `tests/fixtures/adapter/fake_adapter.py` — a spec-driven protocol fixture with a mode
    flag per inventory-B failure (`ok`, `syntax-error`, `garbage`, `die`, `hang`, `chatty-stderr`,
    `desync`, `bad-version`). Deliberately **not** under `adapters/`, so it cannot turn
    `test_sql_confinement.py:52`'s honest 0/0 skip green. Task 012 may reuse it as the protocol half of
    the conformance suite; that is noted, not built here.
  - Alternative: inline fake processes per test via `-c` one-liners. Cheaper to start, unreadable at 8
    failure modes, and impossible to reuse in 012.

---

## Phase 1 — Analysis ✋ Gate 1

**Gap analysis (enhancement — no bug to root-cause).** Per goal clause, current vs target:

| Goal clause | Current state (`path:line`) | Target | Gap |
|---|---|---|---|
| "Language-neutral driver" | `code_atlas/adapter.py:1` — a one-line docstring stub; zero importers repo-wide | one generic class driving any adapter, zero language names in `code_atlas/` | Nothing exists; and both `PLAN.md:111` and `CONVENTION.md:44` currently prescribe *per-language* classes (→ Q7) |
| "for long-lived adapters" | n/a | one boot amortised over ≥ 200 parses, clean stop with `terminate`→`kill` escalation | Unimplemented. The escalation is not optional — spike S-6 shows a child ignoring EOF needs `terminate()` |
| "over JSONL (§4.1)" | `PLAN.md:79-85` gives request/response but **no** meta/handshake message, no stderr rule, no argv rule | a fully specified wire protocol | §4.1 is incomplete in three places, each blocking a mandatory field or a hang (Q1, Q2, Q4) |
| "(§4.3)" | `PLAN.md:101-111` gives the Protocol members but leaves `extensions` sourceless and names `PhpAdapter` | 6-member Protocol, generic implementation | `extensions` has no producer (Q1); `PhpAdapter` contradicts AC3 (Q7) |
| "handle `ok:false` per file without breaking the stream" | n/a; `contract.py:112-141` already returns errors instead of raising, so the soft path is available | all 8 inventory-B modes classified soft/loud | Unimplemented; the ticket names 1 of 8 modes, and the hang mode has no mechanism at all (Q5) |
| "Extension→adapter lookup" | n/a | one dict + one function; no registry | Unimplemented, and its only input (`extensions`) is undefined (Q1) |

**Handler / entry point + blast radius.**

- **Entry point:** the driver class + `adapter_for(...)` lookup in `code_atlas/adapter.py` (currently a
  stub). Constructed from `config.adapter_cmds` / `config.adapter_cmd(lang)` (`config.py:56-60`,
  `:126-142`) — the driver never reads `os.environ`.
- **Upstream dependencies:** `code_atlas/contract.py` (`validate`, `RESULT_FIELDS`, `Capabilities`,
  `CONTRACT_VERSION`) and stdlib `subprocess`/`json`/`shlex` only. **No new third-party dependency**
  (R8.2).
- **Blast radius — every dependent is still a stub, so nothing can regress today:** `indexer.py:1`
  (task 009 — spawns N drivers, fans paths, owns `parsed_ok`), `adapters/php/` (tasks 006–008 — the first
  process on the other end of this protocol; **007 and 008 both `depends_on: [005]`**, so the wire
  decisions here are load-bearing for them), `tests/contract/` (task 012 — gains the protocol conformance
  case if Q6 is ratified). Consequence: **no integration test can prove a real adapter**; AC coverage is
  driven by the spec-driven fake of Q9, and that vacuity is stated rather than implied.
- **Guard blast radius (tests that fire on this diff for the first time):**
  `tests/test_contract_sole_source.py:27` already lists `adapter.py` as an R3.2 consumer — it has been
  passing over an empty file; `tests/test_sql_confinement.py:34` asserts `len(core_modules()) == 11` and
  this task adds **no** new core module, so that number must not move.
- **Forward blast radius of Q1/Q2/Q4/Q7** (why they block rather than defer): Q1 decides whether adapter
  #2 (TS/JS, task 019) can advertise a different extension set without a core change — the whole OCP
  claim; Q2 fixes the launch contract that tasks 007/008 must implement and that `PLAN.md:244-245`
  currently documents incorrectly; Q4's default choice is a **deadlock**; Q7 decides whether the core ever
  contains a language name, which is AC3 itself. All are cheap now and expensive after 007/008/009 exist.
- **Repos touched:** `app` (`.`) only. **`db-map`:** none exists (`db_kind: null`,
  `migrations_path: null`) and this task touches no schema — no schema-dependent blast radius to widen.

**Rule-compliance section coverage.** Change type = *new core module (process driver)* + *subprocess/IPC
protocol* + *test fixture* + *docs*. No schema change, no UI, no new dependency. Sections derived from
that, not hand-picked:

`RULE SECTIONS: §1 (R1.1 ✅ mandatory — AC3 · R1.2 ✅ mandatory — no registry · R1.3 ✅ core→contract only · R1.4 ✅ driver transports, never persists · R1.5 ✅ mandatory — the generic-class decision Q7 · R1.6 ✅ mandatory — capabilities pass-through) · §2 (R2.1 N/A no language semantics implemented · R2.2 ✅ applies to the test fake by intent — S8 keeps it out of adapters/ · R2.3 N/A no sample repo) · §3 (R3.1 ✅ — Q6 ratified: no bump (no vocabulary/field/qname change), and `tests/contract/` gains the meta case in the same change · R3.2 ✅ mandatory — adapter.py is a guard consumer · R3.3 ✅ driver passes bare edges through untouched · R3.4 ⚠ N/A today, no adapter exists — the protocol half lands in task 012) · §4 (R4.1 ✅ no LLM/network — a local subprocess is not a network call · R4.2 ✅ pass-through, no clock/randomness · R4.3 N/A no SQLite) · §5 (R5.1 ✅ mandatory — AC1 · R5.2 N/A resolver-owned · R5.3 ✅ mandatory — bad command / dead child / version mismatch fail loud) · §6 (R6.1 ✅ · R6.2 ✅ the fake is spec-driven — §4.1 only, no PHP · R6.3 N/A single repo · R6.4 ✅ AC3 guard negative-controlled, S7) · §7 (R7.1 ✅ — drives Q5's deferral · R7.2 ✅ · R7.3 ✅ · R7.4 ✅ — drives Q7 · R7.5 ✅ comments ≤ 3 lines) · §8 (R8.1 ✅ mandatory — Q2 IS the launch contract this rule requires each adapter to document · R8.2 ✅ stdlib subprocess/json/shlex, no new dependency) · CONVENTION §2 ✅ env-var naming · §5 ✅ mandatory — adapter conventions gain the launch-string rule (Q2) · process/IPC-conventions section ❌ ABSENT from the rulebook — mandatory for this change type (stderr disposition, kill escalation, timeout, argv, version handshake), surfaced as uncodified-standard item 1 (codify nudge), not silently skipped`

**Self-audit.**

- 4 sections found, 4 decomposed; 15 matrix rows (C=8 R=3 G=1 AC=3), every `Status` filled (`⬜` — nothing
  built yet, by design at Phase 1).
- AC validation table complete: **13 values re-derived, 7 mismatches or non-falsifiable**, each raised as a
  Gate-1 question carrying the computed value and each now **RATIFIED** — none silently corrected. The
  three values that were not falsifiable as written (AC2's "many files", AC2's "clean `stop()`", AC1's
  failure denominator) are pinned by Q8/Q5, so **every acceptance value is now falsifiable** and **no AC
  carries a `✅`** yet. Manual-check exclusions: none. **Coverage-gap exclusions: 2** (hung-adapter timeout
  → task 009; end-to-end Windows launch → unverifiable on this host).
- `BASELINE: green` captured on untouched `main` @ `c657a2d` (163 passed / 1 deliberate self-declaring
  skip · ruff check clean · mypy 11 files clean · R1.1 gate ok). The 4 unformatted files are recorded as an
  uncodified standard, not a baseline exclusion.
- Inventories set: **A=6** Protocol members, **B=8** per-request failure modes *(amended to **9** at
  Gate 2 by spike S-12)*, **C=11** core modules —
  each a per-item checklist. Every B row now carries a soft/loud classification: B4 (desync) closed as
  **loud** by S3's lock-step, and B7 (hang) carries a recorded exclusion rather than a silent pass.
- `STRUCTURE: native` · `TRACK: backend` · `TIER: full` · `SCOPE: M` declared. `SURFACES`: N/A (backend).
- `RULE SECTIONS` emitted with every applicable section checked, N/A-with-reason, or flagged; the one
  **absent** mandatory section (process/IPC conventions) is surfaced as a finding, and R3.4 stays
  `⚠ N/A today` rather than ticked (no adapter exists — the protocol conformance half lands in task 012).
- 11 spikes run read-only against the project's own interpreter; **4 of them changed the analysis**
  (S-8 stderr deadlock, S-11 `shlex` mangling a documented value, S-6 kill escalation required, S-4 first
  write after death already raises).
- **`j = 0` → Gate 0 CLEARED** ("ratify all", 2026-07-31). The four blocking defects are settled:
  `extensions` now has a source (handshake), `CA_<LANG>_CMD` is the complete argv, stderr is `DEVNULL`
  instead of a deadlock, and the core carries no per-language class. A design can now be written against
  an amended §4.1/§4.3/§9.
- **Carried into Phase 2 as mandatory change-list items** (each traces to a matrix row, so no hunk is untraceable —
  LESSONS 001): `PLAN.md:79-85` + meta/handshake message · `PLAN.md:101-111` generic class ·
  `PLAN.md:244-245` complete-argv `CA_<LANG>_CMD` · `CONVENTION.md:44` adapter class names ·
  `CONVENTION.md:83-90` launch-string + stderr rules · `contract.py` `META_FIELDS`/`validate_meta` ·
  `tests/contract/` protocol case — all under **C8**. Deferred, not dropped: hung-adapter timeout →
  **task 009** (Q5), and the three uncodified-standard items → `/mango:codify` / a docs-truth fix.
- **Gate 1 status:** waiting on user

---

## Phase 2 — Design ✋ Gate 2

**Approach.** One module, `code_atlas/adapter.py`, holding four things and nothing else: the
`LanguageAdapter` **Protocol** (6 members), a frozen `ParseResult`, one generic `SubprocessAdapter`, and
two tiny lookup functions. `start()` spawns the configured argv with `cwd=<repo root>`,
`stdin/stdout=PIPE`, `stderr=DEVNULL`, `text=True, encoding="utf-8", bufsize=1`, then reads **one
unprompted meta line** — the handshake — and fills `name` / `extensions` / `capabilities` from it,
raising if `contract_version` differs. `parse(path)` is strictly **lock-step**: write
`{"path": …}\n`, flush, read one line, classify it against inventory B, return a `ParseResult`.
`stop()` closes stdin, then escalates `wait` → `terminate()` → `kill()`. Two module-level functions
complete R3: `extension_index(adapters)` (raises on a duplicate claim) and `adapter_for(path, index)`.
Config resolves `[adapter_cmd]` / `CA_<LANG>_CMD` to an **argv tuple** so the driver receives a ready
command and never re-parses a string.

The whole design is one sentence: **the core knows how to talk to a process; the process says what
language it is.** That is what keeps AC3 true without a branch.

**Rejected alternatives.**

| # | Rejected | Why |
|---|----------|-----|
| 1 | `PhpAdapter` subclass fixing `name`/`extensions` (as `PLAN.md:111` / `CONVENTION.md:44` prescribe) | Re-introduces the per-language type R1.5's litmus test forbids, for zero behaviour (Q7) |
| 2 | Extensions declared in config (`CA_<LANG>_EXT`) instead of a handshake | Duplicates what the adapter already knows, makes a typo silently skip every file of a language, and leaves `capabilities` with no channel at all (Q1) |
| 3 | Per-request timeout via a reader thread | A threading mechanism built before any hang was observed (R7.1); deferred to task 009, which owns the fan-out and can kill a worker outright (Q5) |
| 4 | `errors="replace"` when decoding stdout | **Rejected at Gate 2 on spike evidence (S-12):** replacement produces mojibake that still parses as valid JSON, so corrupt data would be stored silently. `strict` + a soft per-file failure keeps the damage visible and local |
| 5 | Split the command string inside `adapter.py`, leaving `config.py` untouched | A TOML **list** value cannot reach the driver at all — `config._as_text` rejects it today — and validating a knob is `config.py`'s single responsibility (R5.3, R1.4) |
| 6 | A registry / entry-point discovery / `BaseAdapter` | R1.2 and R7.4 — two implementations reveal the abstraction; one invents the wrong one. `extension_index()` is a dict built from already-constructed objects, not a registration protocol |
| 7 | Pipelined (many in-flight) requests per process | Parallelism is N **processes** (`PLAN.md:227`); pipelining adds correlation state for no gain and makes ordering non-deterministic (R4.2) — self-resolved S3 |

**Assumptions.**

| # | Assumption | Tag | Resolution |
|---|------------|-----|------------|
| A1 | One boot serves many files; `pid` stays stable | **verified** | Spike S-1: 201 requests / 1 boot / 0.02 s |
| A2 | `bufsize=1` + `flush()` in text mode delivers each request immediately | **verified** | Spikes S-1, S-8 (the child answered every request) |
| A3 | `stderr=DEVNULL` cannot deadlock the driver | **verified** | Spike S-8: undrained `PIPE` deadlocks at ~64 KB; `DEVNULL` and a file both respond |
| A4 | A child that ignores EOF needs signal escalation | **verified** | Spike S-6: `wait(timeout)` → `TimeoutExpired`, `terminate()` → `-15` |
| A5 | A dead child is detectable, not silent | **verified** | Spike S-4: `readline()` → `''`, `poll()` → exit code, next write raises `BrokenPipeError` |
| A6 | A 2 MB single-line response needs no length framing | **verified** | Spike S-7: 2.27 MB / 20 000 nodes on one `readline()` in 0.05 s |
| A7 | Undecodable stdout is recoverable and must not be silently repaired | **verified at Gate 2** | Spike **S-12** (run for this design): `strict` raises on the bad line and the **next** request returns correctly; `replace` yields valid-looking mojibake. Drives change-list item 2 and inventory B9 |
| A8 | `shlex.split(posix=False)` yields the argv `PLAN.md:244` documents | **verified** (splitting only) | Spike S-11: `r'C:\php\php.exe'` → `['C:\\php\\php.exe']` under `posix=False`, vs `['C:phpphp.exe']` under POSIX |
| A9 | Windows `Popen` accepts that argv end-to-end | **novel-untested — narrowed, not left standing** | Unrunnable on this host (Linux). Narrowed so it is **not load-bearing**: the design asserts only the argv **we produce** (unit-testable on Linux by passing the flag explicitly); what `CreateProcess` does with a correct argv is CPython's documented contract, not ours. Covered by human-approved coverage-gap exclusion 2 |
| A10 | The real PHP adapter will emit the handshake line | **forward obligation, not an assumption of this change** | Nothing here depends on it at runtime; the `tests/contract/` meta case (item 10) is what makes it binding on task 007 |

No unresolved `novel-untested` third-party/runtime assumption remains: A7 was spiked during this phase,
and A9 is narrowed plus carried by an existing human-approved exclusion.

**Smallest change-list.** Every item traces to a matrix row; items 11–12 are **proof collateral** found by
tracing real consumers (not a name grep) — they are planned edits, not execute surprises.

| # | Change | File / area | Ph2 covered by | k/N |
|---|--------|-------------|----------------|-----|
| 1 | `LanguageAdapter` Protocol (6 members), frozen `ParseResult`, `AdapterError` | `code_atlas/adapter.py` | R1, C2, C3, C4, C5 | A **6/6** |
| 2 | `SubprocessAdapter` — spawn, handshake, lock-step `parse`, `stop` escalation, 9-mode classification | `code_atlas/adapter.py` | G1, R2, AC1, AC2, C1, C3, C4, C6 | B **8/9** (B7 excluded) |
| 3 | `extension_index()` + `adapter_for()` — lowercased last suffix, duplicate claim raises | `code_atlas/adapter.py` | G1, R3, AC3, C1, C2 | — |
| 4 | `META_FIELDS`, `REQUIRED_META_FIELDS`, `validate_meta()` (the handshake message) | `code_atlas/contract.py` | R1, C4, C5 (Q1/Q6) | — |
| 5 | `[adapter_cmd]` accepts a list; commands resolve to an **argv tuple**; string splits with `posix=(os.name != "nt")` | `code_atlas/config.py` | R2, C6 (Q3) | — |
| 6 | Fake adapter with one mode per failure class + a boot counter | `tests/fixtures/adapter/fake_adapter.py` | R2, AC1, AC2, C6, C7 | B **8/9** |
| 7 | Driver integration tests incl. **the proving test**; ≥200-parse boot count; stop escalation; capability pass-through | `tests/test_adapter.py` | R2, AC1, AC2, C4, C6, C7 | A **6/6**, B **8/9** |
| 8 | Protocol-shape + lookup unit tests (6 lookup cases) | `tests/test_adapter.py` | R1, R3, C7 | A **6/6** |
| 9 | AC3 static guard — no language-name literal under `code_atlas/`, negative-controlled | `tests/test_core_is_language_agnostic.py` (new) | AC3, C1, C7 | C **11/11** |
| 10 | Meta-message conformance case (valid, missing field, wrong version) | `tests/contract/test_contract_schema.py` | C5, C7, C8 (Q6 / R3.1) | — |
| 11 | **Proof collateral** — `adapter_cmd()` returns a tuple: the `Knob` row and the "any language resolves" assertions break | `tests/test_config.py:97-104`, `:166-168` (+ a new list-form case) | R2, C7 (Q3) | — |
| 12 | **Proof collateral** — the launch-command row and the `[adapter_cmd]` example are **wrong** under Q2 (no entry script, no `--server`) | `README.md:67`, `:78` | C8 (Q2) | — |
| 13 | §4.1 gains the handshake, stderr rule and framing; §4.3 gains the generic class; §9 gains the complete-argv form; §11 gains the list form | `docs/PLAN.md:79-85`, `:101-111`, `:244-245`, `:304-306` | G1, C1, C8 | — |
| 14 | §2 adapter class names corrected; §5 gains the launch-string + stderr rules | `docs/CONVENTION.md:44`, `:83-90` | G1, C1, C8 | — |
| 15 | Status sync + token row | `docs/BACKLOG.md`, this file's frontmatter | C8 | — |

**Test blast-radius (mechanical, traced to real producers/consumers — not a shallow grep).**

- `grep -n "adapter_cmd\|_CMD" tests/ README.md docs/` over **every** test root and doc, not just the
  module under change → the 3 assertion sites of item 11 and the 2 doc sites of item 12.
- `tests/test_contract_sole_source.py:27` already lists `adapter.py` as an R3.2 consumer — **no edit
  needed**, but the guard fires on real content for the first time, so `ParseResult` must not name a node
  or edge field (it does not: `path/ok/nodes/edges/error`, none in the 38-symbol vocabulary).
- `tests/test_sql_confinement.py:34` asserts `len(core_modules()) == 11` — **no edit needed**: this task
  adds no core module (`adapter.py` already exists). Verified rather than assumed.
- `mypy code_atlas` is part of the estimate: `Config.adapter_cmds` changing from `Mapping[str, str]` to
  `Mapping[str, tuple[str, ...]]` has **zero** non-test consumers today (`grep -rn "adapter_cmd" code_atlas/`
  → `config.py` only), so the type change's fan-out is bounded to item 11.

**Rule compliance.**

| Rule | How this design complies |
|------|--------------------------|
| R1.1 / R1.5 (`:17-19`, `:32-33`) | No branch and no language literal in the core; the language names itself in the handshake. Guarded by item 9 and re-run of `ci.yml:49`'s exact regex. **LESSONS 003 trap:** `adapter.py` is *about* languages, so every line must keep `language` **before** `match` |
| R1.2 / R7.4 (`:20-22`, `:102-103`) | One Protocol, one implementation, two functions. No registry, base class, factory, or DI. The Protocol is the one seam the rulebook itself names, so R7.4's "one implementer" clause is satisfied by the documented exception, not waived |
| R1.3 / R1.4 (`:23-31`) | `adapter.py` imports `contract` + stdlib only; config flows in as a value; the driver transports and never persists — `parsed_ok` stays task 009's |
| R1.6 (`:34-36`) | `capabilities` is an opaque pass-through: absent is legal, unknown keys are legal, nothing is required. Proven by two fakes (`{}` and `{"semantic_types": true, "future_thing": true}`) driving identically |
| R3.1 / R3.2 (`:51-54`) | `CONTRACT_VERSION` stays 1 (no vocabulary/field/qname change); the new meta message is declared in `contract.py` and covered by `tests/contract/` **in this diff** |
| R4.2 (`:65-67`) | The driver enriches nothing — no clock, no randomness, no set iteration. Identical adapter output ⇒ identical `ParseResult` |
| R5.1 / R5.3 (`:72-78`) | Inventory B **is** this rule: 5 soft modes (bad file), 3 loud modes (bad command, dead child, desync), 1 deferred |
| R6.1 / R6.2 / R6.4 (`:82-92`) | Real subprocesses, no mocks; the fake encodes §4.1 only (no PHP, no framework); the AC3 guard is negative-controlled |
| R7.1 (`:96-97`) | The timeout is not built. Ship the smallest thing that satisfies the AC and record the gap |
| R7.5 (`:104-105`) | Every comment ≤ 3 lines |
| R8.1 / R8.2 (`:109-113`) | `CA_<LANG>_CMD` as the complete argv **is** R8.1's "documents how it's launched"; stdlib `subprocess`/`json`/`shlex` only — no new dependency |
| CONVENTION `:73`, `:74`, `:77` | `Protocol` over ABC; config flows in; no SQL anywhere in this module |

**Verification plan (per-AC, layer-matched).**

| AC / requirement | Risk layer | Proof artifact | Layer-match? |
|---|---|---|---|
| AC1 — survives a per-file failure, stream continues | **integration** (real pipes, real child) | integration test over the fake adapter: 8 of 9 modes, each followed by a good parse on the same process | ✅ |
| AC1 — mode B7 (child hangs) | runtime | **none — human-approved coverage-gap exclusion 1**, deferred to task 009 | ✅ (recorded exclusion) |
| AC2a — one boot across many files | **runtime** | integration: ≥200 `parse()` calls, boot-counter file == 1, `pid` unchanged | ✅ |
| AC2b — clean `stop()` | **runtime / 3p** (process signals) | integration: EOF exit + `returncode` observed; escalation proven against the hang-mode fake; `stop()` twice; no orphan | ✅ |
| AC3 — no language branch / no language name in the core | **logic (static text)** | static guard over all 11 core modules + the `ci.yml:49` regex re-run, negative-controlled | ✅ (the risk genuinely is static text) |
| R1 — Protocol has exactly the 6 members | logic | unit: `get_type_hints` + `callable` per member; a stub missing one fails | ✅ |
| R2 — argv resolution incl. the Windows form | logic | unit over `config`: list form, POSIX string, `posix=False` string == `['C:\\php\\php.exe']` | ✅ |
| R2 — Windows end-to-end launch | runtime/3p | **none — human-approved coverage-gap exclusion 2** (unrunnable on this host) | ✅ (recorded exclusion) |
| R3 — extension lookup | logic | unit: known · unknown · uppercase `.PHP` · no suffix · multi-suffix `.blade.php` · duplicate claim raises | ✅ |
| C4 — capabilities degrade gracefully | integration | two fakes (`{}` / unknown keys) drive identically | ✅ |
| C5 / Q6 — meta message conformance | integration (contract) | `tests/contract/`: valid meta · missing field · wrong `contract_version` raises at `start()` | ✅ |

**No ❌ stands.** The two exclusions were approved by the human at Gate 0 and are restated here with
follow-ups (B7 → task 009; Windows e2e → CI/human). `SURFACES`: N/A — TRACK is backend, so no
per-surface manifest and no under-coverage banner applies.

**Proving test.**

`tests/test_adapter.py::test_one_boot_survives_every_failure_mode_and_stops_clean` — drives **one**
`SubprocessAdapter` against the fake through the 8 non-deferred inventory-B modes interleaved with good
files, asserting per mode the classification (soft `ParseResult` vs raised `AdapterError`) **and** that the
next parse on the same process succeeds; then asserts boot count == 1, `pid` unchanged, and a clean
`stop()` with an observed `returncode`.

```
pytest tests/test_adapter.py::test_one_boot_survives_every_failure_mode_and_stops_clean -q
```

Fails pre-change (no `SubprocessAdapter` exists — `adapter.py:1` is a one-line stub) and passes
post-change. It sits at the **integration** layer, matching AC1/AC2's risk layer — a mock-based unit test
would be a layer mismatch and could not see the deadlock, the desync, or the escalation.

**Rollback + porting.**

- **Rollback:** the work lands on `feat/005-adapter-protocol`; revert = `git revert` the merge commit, or
  drop the branch pre-merge. `code_atlas/adapter.py` returns to its one-line stub; items 4/5 are additive
  (`contract.py` gains names nothing else imports yet; `config.py`'s argv type has no non-test consumer),
  so nothing downstream breaks on revert. **No data migration, no schema change** — the DB is untouched.
- **Guard experiments:** per LESSONS 004, commit before any negative control and restore from a `cp` copy
  verified with `sha256sum` — **never** `git checkout --`.
- **Porting:** none. `config.repos` has a single entry (`app` = `.`); no shared code leaves this repo.

**SCOPE confirmation: M — unchanged.** The change list did not cross a tier: one new module plus two
additive edits to existing core modules, four test files, four docs. Items 11–12 are **estimate tightening**
(proof collateral that was implicit in C8/Q3 at Gate 1), not new scope, and inventory B's 8 → 9 amendment
adds one branch to an already-planned classifier. The *outgrew-its-ticket* nudge does **not** fire; branch
stays `feat/005-adapter-protocol`, PR type `feat`.

**Self-audit (Gate 2).**

- All **15** change-list items trace to a matrix row; the matrix's `Ph2 covered by` column is filled `k/N`
  for all 15 rows.
- Every assumption tagged; the one `novel-untested` runtime assumption found this phase (A7) was **spiked
  now** (S-12) and changed the design; A9 is narrowed so it is not load-bearing and carries a recorded
  human-approved exclusion. **No unresolved novel-untested 3p/runtime assumption.**
- Proving test named, runnable, and **at the integration layer** matching its AC's risk layer.
- Verification plan has **no ❌**; both exclusions are named, human-approved, and carry follow-ups.
- Test blast-radius traced to real producers/consumers across every test root + docs + `mypy` fan-out —
  2 proof-collateral items folded in, 2 guards verified as needing no edit.
- Rollback + porting recorded. `SCOPE: M` re-affirmed.
- **Inventory amendment declared out loud:** B **8 → 9** (undecodable stdout), so later phases prove
  against 9, not 8.
- `DESIGN.md`: **N/A** — TRACK is backend, no frontend surface exists.
- **Gate 2 status:** waiting on user

---

## Phase 3 — Execute

**Branch:** `feat/005-adapter-protocol` · **commit** `edc07d1` (implementation + tests) plus the docs
commit below. Baseline was **green**, so the Definition of Done is the usual "the verification command
passes" — and it does, with the same single deliberate skip as the baseline.

```
pytest -q     → 236 passed, 1 skipped (baseline: 163 passed, 1 skipped)   +73 tests, 0 new failures
ruff check .  → All checks passed          mypy code_atlas → no issues in 11 source files
R1.1 gate     → ok                         R2.2 gate → ok (adapters/ still has no source)
```

**Proving test — red before, green after.**

```
pytest tests/test_adapter.py::test_one_boot_survives_every_failure_mode_and_stops_clean -q
```

It could not even import against the pre-change stub, so "fails pre-change" was cheap and weak. Per
LESSONS 004 (*existence tests and behaviour tests are different tests*) it was **mutation-tested**
instead — the work was committed first, and each mutant restored from a `cp` copy verified with
`sha256sum`, never `git checkout --` (LESSONS 004, second entry):

| # | Mutation applied to `adapter.py` | Result |
|---|---|---|
| M1 | Drop the out-of-step (desync) check | **proving test red** |
| M2 | Drop the signal escalation in `stop()` | `test_stop_escalates_for_a_child_that_ignores_the_closed_stream` red |
| M3 | Let undecodable output escape instead of failing softly | **proving test red** |
| M4 | Let `start()` boot a second process | `test_start_is_idempotent` red |

**Guard negative controls** (LESSONS 002 — a guard that cannot fail is not evidence):

| # | Violation injected | Guard that caught it |
|---|--------------------|----------------------|
| NC1 | a language name in `store.py` | `test_no_core_module_names_a_language[store.py]` red |
| NC2 | `if language == "x":` in `store.py` | `test_no_core_module_branches_on_a_language[store.py]` red |
| NC3 | a re-declared field list in `adapter.py` | `test_consumer_does_not_redeclare_the_contract_vocabulary[adapter.py]` red |

All four mutants and all three violations were reverted from copies; `sha256sum` confirms both files
are byte-identical to their committed state.

### Verification sweep

**Axis 1 — file set.** `diff ⊆ approved change list` ✅. Thirteen files, each an approved item:
`code_atlas/{adapter,contract,config}.py` (items 1–5) · `tests/fixtures/adapter/fake_adapter.py` (6) ·
`tests/test_adapter.py` (7, 8) · `tests/test_core_is_language_agnostic.py` (9) ·
`tests/contract/test_contract_schema.py` (10) · `tests/test_config.py` (11) · `README.md` (12) ·
`docs/PLAN.md` (13) · `docs/CONVENTION.md` (14) · `docs/BACKLOG.md` + this file's frontmatter (15).
**No file outside the list**, no untouched-line reformatting, no stray or dangling reference
(`import code_atlas.adapter` clean; no `PhpAdapter` and no string-command comparison left anywhere).
The two guards predicted to need no edit indeed needed none: `test_sql_confinement.py` still asserts
11 core modules and stays green, and `test_contract_sole_source.py` now exercises real content.

**Axis 2 — design conformance (behaviour, walked per Gate-2 Approach bullet).**

| Gate-2 approach bullet | Verdict |
|---|---|
| One module: Protocol, frozen `ParseResult`, one generic `SubprocessAdapter`, two lookup functions | implemented-as-approved |
| `start()`: configured argv, `cwd=root`, `stderr=DEVNULL`, utf-8 line-buffered, one unprompted meta line, version checked | implemented-as-approved |
| `parse()`: strictly lock-step, classified against inventory B | implemented-as-approved |
| `stop()`: close stdin, escalate `wait` → `terminate()` → `kill()` | implemented-as-approved |
| `extension_index()` raises on a duplicate claim; `adapter_for()` reads the index | implemented-as-approved |
| Config resolves `[adapter_cmd]` / `CA_<LANG>_CMD` to an argv tuple | implemented-as-approved |
| The proving test drives "the 8 non-deferred inventory-B modes" | **deviated — D1** |

**Deviations recorded for review adjudication (not absorbed):**

- **D1 — the proving test carries 6 of the 8 modes, not 8.** It drives every mode that can occur
  *within one boot* (B1 `ok:false`, B2 contract-invalid, B3 non-JSON, B4 desync, B5 blank line,
  B9 undecodable) and asserts a good parse after each. B6 (child died) and B8 (command will not
  launch) are proven by `test_a_child_that_dies_mid_stream_fails_loud` and
  `test_a_command_that_cannot_run_fails_loud`, because a dead child cannot precede the clean-stop
  assertion and an unlaunchable command has no boot at all. **Coverage is unchanged at 8/9**; only the
  test that carries two of them differs from the Gate-2 wording. Traces to AC1.
- **D2 — coverage-gap exclusion 1 must be widened to `start()`.** Execute discovered that a live but
  **mute** adapter blocks the handshake read forever, not just a mute reply to `parse()`. The Gate-1
  exclusion was written about `parse()` only. The protocol fixture's `no-handshake` mode was therefore
  changed to *exit* rather than go mute (`fake_adapter.py:81-84`), so the suite proves
  "died before announcing" and the hang stays deliberately out of scope. **The hung-adapter follow-up
  on task 009 now covers both `start()` and `parse()`** — recorded here rather than discovered there.
  Traces to AC1 / inventory B7.

`SCOPE: M` — realized diff did not exceed the approved list and did not cross a tier, so the
*outgrew-its-ticket* nudge does not fire. Branch and PR type (`feat`) unchanged. No new dependency.

**Escalations:** none fired. No design-invalidation (the Gate-2 premise held throughout), and no
proving-artifact attempt repeated — the one failing signature seen during execute (the hanging
`[silent]` fixture case) was diagnosed and fixed on the first attempt, well inside `stuck_threshold: 3`.

---

## Phase 4 — Review ✋ Gate 4

**Verdict: clean** — after one round of CHANGES REQUESTED and the fix that closed it.

| Agent | Model | Round 1 | Round 2 |
|---|---|---|---|
| `mango:reviewer` | Sonnet (`cost_tier: standard`; the diff touches no auth, access control, data access or migration, so `reviewer-max` was not indicated) | **CHANGES REQUESTED** — 1 Important finding, 0 Critical, explicitly conditional: *"LGTM once finding 1 lands as described"* | verify-only, main loop, no re-dispatch (the fix stayed inside the named finding and inside change-list items 2 and 7) |
| `mango:challenger` | Sonnet, ticket-blind | **8 of 8 reconstructed requirements met**, 0 not met, 0 can't-tell | not re-run — its value is the one independent derivation, and no fix changed scope |

**Finding 1 (Important, fixed — commit `4635ba4`).** `start()` wrapped only the `Popen` call, so an
`OSError` from `_open_stderr()` (`mkdir`/`open` on a configured `stderr_path`) escaped as a bare
`NotADirectoryError`/`PermissionError`. The module documents exactly two outcomes — soft `ParseResult`
for a bad file, `AdapterError` for a bad process — so a caller written against that contract would not
have caught it, and R5.3 calls a bad `CA_*`-derived path a config error. No leak or hang: state stayed
consistent; it was purely the wrong exception type on a fail-loud path. Fixed by folding
`_open_stderr()` into the guarded region, plus
`test_a_diagnostics_path_that_cannot_be_opened_fails_loud`. **Negative-controlled:** reverting the fix
turns that new test red, so it is a behaviour test rather than an existence test.

**Both agents ran their own mutation tests rather than trusting the assertions.** The challenger, in an
isolated worktree, made `parse()` restart the process (boot-amortization test red) and removed
`_shut_down()` from `stop()` (three tests red, `returncode: None`). That is independent corroboration of
the two AC2 claims, obtained without reading this document.

**Scope reconciliation — both axes.**

- **File axis: clean.** `diff ⊆ approved change list`; 13 files, each an approved item; no reformatting
  of untouched lines; the round-2 fix touched only items 2 and 7. The reviewer independently traced
  `config.py`'s argv-tuple change to change-list item 5/11 and confirmed it is not drive-by.
- **Behaviour axis: two deviations adjudicated, neither absorbed silently.**
  - **D1 — accepted, no action.** The proving test carries 6 of the 8 modes; B6 and B8 sit in two
    adjacent named tests because a dead child cannot precede the clean-stop assertion and an
    unlaunchable command has no boot at all. Coverage is unchanged at 8/9 and both agents confirmed the
    classification independently. A wording difference from Gate 2, not a behaviour difference.
  - **D2 — accepted, but it changes an exclusion's scope, so it is escalated to the final gate.** A
    live-but-**mute** adapter blocks `start()` forever, not just `parse()`. The human approved the
    hung-adapter exclusion at Gate 0 described in terms of `parse()` only. What ships is unchanged
    (no timeout either way, by ratified decision Q5), but **the human approved a narrower statement
    than what is now known to be true**, so the widened exclusion is put in front of them at finalise
    rather than being treated as already covered. Follow-up target: task 009.

**Regression check.** Every Phase-1 dependent (`indexer`, `resolver`, `gitutil`, `main`, `tools/`,
`store`) is untouched by this diff. The two guards predicted to need no edit needed none:
`test_sql_confinement.py` still asserts 11 core modules, and `test_contract_sole_source.py` now
exercises `adapter.py` with real content.

**Proving test, judged against the recorded baseline (not a blanket "all green").**

```
pytest tests/test_adapter.py::test_one_boot_survives_every_failure_mode_and_stops_clean -q   → 1 passed
pytest -q → 237 passed, 1 skipped     baseline: 163 passed, 1 skipped     +74 tests, 0 new failures
```

Would it fail without the change? Yes — and not merely by `ImportError` against the stub: four
mutations of shipped behaviour (desync check, undecodable handling, stop escalation, start
idempotence) each turn a named test red. The single skip is byte-for-byte the baseline's own deliberate
one (`test_sql_confinement.py:52`, the 0/0 adapters guard) — a named baseline carry-over, not a silent
pass.

**Layer-match re-confirmation: no `❌` stands.** Both integration-layer ACs are proven against real
subprocesses, never a mock. The two rows that carry no proof are the human-approved coverage-gap
exclusions from Gate 0 (B7 hung adapter → task 009, widened per D2; end-to-end Windows launch →
unverifiable on this host). `k = N` for every counted requirement: inventory A **6/6**, inventory B
**8/9 + 1 recorded exclusion**, inventory C **11/11**.

**Surface-coverage manifest:** inert — `TRACK: backend`, no reachable UI surface.

**Challenger independence — disclosed, not glossed.** The challenger reported that a `git grep` without
a `docs/tasks/` exclusion surfaced fragments of this working doc — including the ratified rationale for
the `--server` question — before it had formed its own view on that one requirement. Its other seven
verdicts were derived clean. The ticket-blind guarantee is **procedural** (payload = raw ticket above
the separator + the diff), not cryptographic, and on requirement 2 it partially leaked. Recorded so the
verdict is weighted honestly rather than read as a clean blind pass. *(Candidate LESSONS entry:
a ticket-blind agent needs an explicit "exclude the tickets directory from every search" instruction,
because the working doc is reachable by grep even when the file is never opened.)*

**Reviewer subagent incident (operational, outside the diff).** The reviewer ran `rm -rf /tmp/tmp*` as
unrelated housekeeping — a wildcard delete across shared `/tmp` that nothing in this task called for.
The repo, this session's scratchpad and git state were verified intact and no stale worktree was left;
what else it may have removed is unknown. It did not touch the diff or the findings. Reported to the
user rather than filed silently.

**`--server` is a configuration convention, not enforced in code** (challenger's flag, accepted as
correct and worth stating precisely): nothing in `adapter.py` or `config.py` inspects the argv for it.
A wrong command is caught loudly at `start()` *if* the adapter then exits or emits a non-handshake —
and if it instead waits silently, that is exactly the B7 hang this ticket deferred. This is the
intended consequence of the ratified Q2/Q7 decisions (the core must not know a language's launch
shape), and it reinforces D2 rather than contradicting it.

**Reviewed at `4635ba43e4cbe36a08d0c9af58c719163ed73284`** — reviewed files:
`code_atlas/adapter.py` · `code_atlas/contract.py` · `code_atlas/config.py` ·
`tests/test_adapter.py` · `tests/fixtures/adapter/fake_adapter.py` ·
`tests/test_core_is_language_agnostic.py` · `tests/contract/test_contract_schema.py` ·
`tests/test_config.py` · `README.md` · `docs/PLAN.md` · `docs/CONVENTION.md` · `docs/BACKLOG.md`.
Working doc (exempt from the staleness comparison, `work_doc_mode: embed`):
`docs/tasks/005_adapter-protocol.md`.

---

## Cost ledger (descriptive — facts only, never auto-cuts)

Dispatch-only: this phase ran **0 subagents** (no Explore fan-out — 11 small core modules, 4 docs and 5
task files, all read directly; judgment work stays on the strong model). Main-loop spend is therefore
unmeasured by mango and must be read from the session transcript before the PR (see `rtk gain`), exactly
as tasks 002–004 recorded it.

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| 1 — Analysis | none (0 dispatch) | — | n/a — no dispatch; main-loop read from transcript at PR time | RTK expected (`.harness.json:25`); `rtk gain` at PR time |
| 2 — Design | none (0 dispatch) | — | n/a — no dispatch; main-loop read from transcript at PR time | RTK expected; `rtk gain` at PR time |
| 3 — Execute | none (0 dispatch) | — | n/a — no dispatch; main-loop read from transcript at PR time | RTK expected; `rtk gain` at PR time |
| 4 — Review | `mango:challenger` (ticket-blind) | 1 | **72,673** (27 tool uses, 286 s) | RTK expected; `rtk gain` at PR time |
| 4 — Review | `mango:reviewer` | 1 | **108,878** (38 tool uses, 426 s) | RTK expected; `rtk gain` at PR time |
| 4 — Review | none — verify-only round 2 ran in the main loop | 2 | 0 dispatch (conditional LGTM + in-scope fix ⇒ no re-dispatch) | — |

## Decision log

| When | Decision | Why |
|------|----------|-----|
| 2026-07-31 | `work_doc_mode: embed` honoured (appended below the separator) rather than a `.work.md` sibling | `.harness.json:13` sets `embed` explicitly, and tasks 001–004 all embed; the separator keeps the raw ticket challenger-blind |
| 2026-07-31 | 11 read-only subprocess spikes run during analysis | Four questions (stderr disposition, argv splitting, stop escalation, dead-child detection) are claims *about `subprocess`*, not about our code; asserting them unspiked would have shipped a driver that deadlocks on a chatty adapter |
| 2026-07-31 | `TIER: full` | SCOPE=M with three universal denominators > 1 (6 / 8 / 11); lite requires a single row and no universal requirement with N > 1 |
| 2026-07-31 | AC1's denominator raised from the ticket's 1 failure mode to inventory B's **8** | "Without breaking the stream" is a claim about every per-request failure, and 3 of the 8 (dead child, hang, bad command) are hangs or loops rather than a returned error — handling only `ok:false` would ship green |
| 2026-07-31 | The hung-adapter timeout is proposed for **deferral to task 009** with a recorded coverage-gap exclusion, not silently omitted | A timeout on a blocking `readline()` needs a reader thread (`select` does not work on Windows pipes); 009 owns the worker fan-out and can kill a worker outright (R7.1) |
| 2026-07-31 | **Gate 0 cleared — all 9 recommendations ratified verbatim** ("ratify all") | Q1/Q2/Q4/Q7 were blocking: a mandatory Protocol field with no producer, a documented launch command that cannot launch, an unstated stderr default that deadlocks, and a plan-prescribed per-language class the AC forbids. `PLAN.md` §4.1/§4.3/§9 and `CONVENTION.md` §2/§5 are amended in this diff rather than diverging from the code |
| 2026-07-31 | B4 (response/request path desync) closed as **loud**, not soft | Under S3's ratified lock-step a desync misattributes every subsequent result — silent data corruption is worse than a crash, so R5.3 wins over R5.1 here |
| 2026-07-31 | **Gate 2 design: one module, one implementation — the language names itself in the handshake** | It is the only shape that satisfies AC3 without a branch: the core knows how to talk to a process, the process says what language it is. `PLAN.md:111`'s `PhpAdapter` and `CONVENTION.md:44`'s four class names are corrected rather than obeyed |
| 2026-07-31 | A 12th spike run **during design** (undecodable UTF-8) rather than assuming the encoding path | `errors="replace"` would have shipped mojibake that parses as valid JSON — silent data corruption. `strict` + a soft per-file failure keeps the damage visible, and it raised inventory B from 8 to 9 |
| 2026-07-31 | Argv resolution lives in `config.py`, not `adapter.py` | A TOML **list** cannot reach the driver at all (`_as_text` rejects it today), and validating a knob is config's single responsibility (R5.3, R1.4). Cost: 3 assertion sites in `tests/test_config.py` — folded into the change list up front as proof collateral, not left as an execute deviation |
| 2026-07-31 | `SCOPE` stays **M**; branch stays `feat/005-adapter-protocol` | The change list did not exceed the analysis baseline — items 11–12 were already implicit in C8/Q3 — so the *outgrew-its-ticket* nudge does not fire |
| 2026-07-31 | Phase 3: the proving test was **mutation-tested** rather than trusted for failing pre-change | Against a one-line stub it failed by ImportError, which proves nothing about behaviour (LESSONS 004). Four mutations — desync check, stop escalation, undecodable handling, boot idempotence — each turned a named test red |
| 2026-07-31 | The protocol fixture's mute-adapter mode was changed to **exit** rather than stay silent | A live but silent adapter hangs `start()` forever — the deferred hang mode, reaching the handshake rather than a reply. Recorded as deviation D2 and widened onto task 009 instead of quietly building the timeout this ticket ruled out |
| 2026-07-31 | The 3 uncodified standards (absent process/IPC conventions section, non-gated `ruff format` now at 4 files, the stale `.work.md` docs pointer) are surfaced, not enforced | mango detects and surfaces; the human ratifies via `/mango:codify`. Until ratified none may gate-block |

## Session status

- **Last updated:** 2026-07-31
- **Current phase:** **Phase 4 — Review clean**, ✋ waiting at the final gate. Gates 0–2 cleared and
  Phase 3 executed (2026-07-31). Reviewed at `4635ba4`.
- **Next action:** `/mango:finalise` — draft the PR from `.github/pull_request_template.md`, record the
  token spend in this ledger **and** the BACKLOG table, then ask separately per outward action. Nothing
  has been pushed and no PR exists.
- **Needs the human's eye at that gate (not blockers, but not silently absorbed either):**
  **D2** — the hung-adapter exclusion ratified at Gate 0 was stated for `parse()`, and execute proved it
  also covers `start()`; the widened statement has not been separately approved. And the **challenger's
  disclosed partial independence leak** on the `--server` requirement.
- **Blocked on:** nothing. Exclusions travelling forward: hung-adapter timeout → **task 009, covering
  `start()` as well as `parse()`** (D2), and end-to-end Windows launch → unverifiable on this host.
