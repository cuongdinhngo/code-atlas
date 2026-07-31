---
id: 007
slug: php-adapter-visitor
title: PHP adapter — server mode & streaming
phase: 1
milestone: M0
status: in-progress
depends_on: [006, 005]
---

## Goal
Complete the PHP adapter to the language standard and add streaming `--server` mode (§6, §7).

## Scope / Deliverables
- Nodes: `Namespace_, Class_ (abstract/final/readonly), Interface_, Trait_, Enum_ (pure/backed), anon classes, ClassMethod, Property (incl. promoted/typed/readonly), ClassConst, enum cases, Function_, closures, arrow fns, first-class callables`.
- Edges: `extends/implements`, `TraitUse`, `MethodCall/StaticCall/FuncCall`, `New_`, `Use_` (incl. group-use, function/const imports, aliases), `Include_`.
- Attributes captured raw on declarations.
- `ErrorHandler\Collecting` → bad file returns `ok:false`, stream continues.
- `--server` stdin loop matching the subprocess protocol; emits **bare** edges (targets as FQNs/names).

## Acceptance criteria
- Emits correct nodes/edges for each construct above (asserted in fixtures — task 012).
- No repo/framework names in adapter source (grep-gate clean).

## References
Plan §6, §7, §2 (standard over sample).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 007 — PHP adapter: full language coverage & server mode (working doc)

- **Ticket:** 007 · `docs/tasks/007_php-adapter-visitor.md` (local-file ticket)
- **Type:** enhancement
- **Repo(s) / Porting:** `app` (`.`) — single repo, no porting
- **SCOPE:** **M** (re-scoped at Gate 0 from L — see H2: the grammar half splits out to task 025)
- **STRUCTURE:** native
- **TRACK:** backend — 0/N touched files under UI paths (this repo has no UI surface)
- **TIER:** full
- **BASELINE:** green — `pytest` 300 passed; `ruff check .` clean; `mypy code_atlas` clean (untouched `fc85dc6`)
  <!-- baseline exclusions: none -->
- **work_doc_mode:** `embed` → this doc lives below the separator in the ticket file itself.

---

## Phase 0 — Refine

`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: the ticket is a structured, pre-written backlog card with native headers. Product
decisions it left open are raised as Gate-0 questions below rather than re-opened as a refine pass.

---

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope / Deliverables, Acceptance criteria, References) | 4 decomposed | ROWS: C=5, R=6, G=1, AC=2`

*References* is decomposed to **0 requirement rows** by design: it is a pointer to PLAN §6/§7/§2, and
those sections are consumed as Ph1 evidence throughout this matrix rather than restated as rows.
C rows carry no ticket header (the card has no *Constraint* section); they are sourced from the
binding rulebook for this change type, per the step-11 rule-section coverage.

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | "Complete the PHP adapter to the language standard and add streaming `--server` mode (§6, §7)." | **Two goals in one card, split at Gate 0 (H2):** (a) close the construct gap → **task 025**; (b) make the adapter drivable by `SubprocessAdapter` → **007, this card**. 007 is proven against clause (b) only. | `adapters/php/src/Visitor.php` covers 18 of the 42 inventory items; `adapters/php/index.php:19` accepts `--file` only | | | ❌ |
| R1 | Scope / Deliverables | "Nodes: `Namespace_, Class_ (abstract/final/readonly), Interface_, Trait_, Enum_ (pure/backed), anon classes, ClassMethod, Property (incl. promoted/typed/readonly), ClassConst, enum cases, Function_, closures, arrow fns, first-class callables`." | A counted **"for each of N"** requirement → per-item inventory rows 1–21. The ticket list is a *hint, not the denominator*: R2.1 binds the adapter to the full 8.5 grammar, which adds nullsafe calls, property hooks and global `const` (self-resolved S2–S4). | Empirically: `\App\Models\Status::Active` emits **no node** today; `kinds = [Class, ClassConst, Enum, File, Function, Interface, Method, Namespace, Property, Trait]` | — | — | ⚠ 025 |
| R2 | Scope / Deliverables | "Edges: `extends/implements`, `TraitUse`, `MethodCall/StaticCall/FuncCall`, `New_`, `Use_` (incl. group-use, function/const imports, aliases), `Include_`." | Counted "for each of N" → inventory rows 22–38. `USES_TRAIT` and `GroupUse` have no code path at all today. | `USES_TRAIT` edges on the fixture: `[]`. `Visitor.php:106` handles `Stmt\Use_` only; `Stmt\GroupUse` is a separate class (`vendor/.../Node/Stmt/GroupUse.php`) | — | — | ⚠ 025 |
| R3 | Scope / Deliverables | "Attributes captured raw on declarations." | `attrGroups` on every declaration node → serialised into the node's `extra` field (the only contract field that can carry them; `contract.NODE_FIELDS` has no `attributes`). "Raw" = name + args source, no framework interpretation (R2.3). | `grep -c attrGroups adapters/php/src/Visitor.php` → 0. `Node\AttributeGroup` / `Node\Attribute` confirmed present in the vendored parser | — | — | ⚠ 025 |
| R4 | Scope / Deliverables | "`ErrorHandler\Collecting` → bad file returns `ok:false`, stream continues." | Replace `index.php`'s catch-all with `ErrorHandler\Collecting`, so a recoverable parse error is *collected* rather than thrown — and one bad file never ends the process (R5.1). | `adapters/php/index.php:44` uses `catch (Throwable)`; its own comment defers Collecting to 007. `vendor/.../ErrorHandler/Collecting.php` exists | | | ❌ |
| R5 | Scope / Deliverables (clause 1 of 2) | "`--server` stdin loop matching the subprocess protocol" | Handshake line first, then lock-step read-one-request/write-one-reply until EOF. Must satisfy `contract.validate_meta` and every wire rule in PLAN §4.1. | `SubprocessAdapter._read_handshake` (`code_atlas/adapter.py:190`) rejects a missing/invalid/version-mismatched handshake loudly; nothing in `adapters/php/` emits one | | | ❌ |
| R6 | Scope / Deliverables (clause 2 of 2) | "emits **bare** edges (targets as FQNs/names)" | Already true and must *stay* true as new edge kinds land: never set `target_qname` in the adapter (R3.3). | `Visitor.php:194` writes `target_raw` only, never `target_qname` | | | ✅ |
| AC1 | Acceptance criteria | "Emits correct nodes/edges for each construct above (asserted in fixtures — task 012)." | Correctness is asserted **in this task** over spec-driven fixtures; task 012 then adds the cross-adapter conformance matrix. See S1 — rulebook precedence, surfaced not silent. After H2, 007's denominator is the **protocol inventory N=18** (P1–P18); the 42-construct denominator moves to task 025. | R6.1 "adapter change → a fixture + conformance assertion"; R6.2 spec-driven fixtures; R3.4 is what 012 owns | | | ❌ |
| AC2 | Acceptance criteria | "No repo/framework names in adapter source (grep-gate clean)." | The named gate is `.github/workflows/ci.yml:112` over `adapters/` with `vendor/`+`node_modules/` excluded (R6.5). "Clean" = that grep matches nothing in authored source. | Gate is live and currently passing; `tests/test_sql_confinement.py` guards the sweep against emptying itself | | | ✅ |
| C1 | rulebook §1 (R1.1/R1.3/R1.4) | "Zero language branches in the core… Adapters depend on nothing in the core." | Everything this ticket adds lives under `adapters/php/`; no `code_atlas/` file may gain a PHP-shaped branch, and the adapter may not import from the core. | CI grep-gate `ci.yml:91`; `code_atlas/adapter.py:83` takes the language only as an opaque config key | | | ✅ |
| C2 | rulebook §2 (R2.2/R2.3) | "Adapters must never encode a specific repo's directory names, class-naming habits, or framework." | New fixtures use neutral names; no framework name enters adapter source. Restates AC2 from the rulebook side. | LESSONS: task 006's first `composer install` tripped this gate on Composer's own `ClassLoader.php` | | | ✅ |
| C3 | rulebook §3 (R3.1/R3.2/R3.3) | "Changes to node/edge vocabulary… require a `contract_version` bump and an update to the conformance tests." | **N/A for 007:** H3 resolved to reuse `ClassConst`, so no vocabulary change — and enum cases moved to 025 regardless. R3.3 still binds and is carried by R6/P17. | `contract.py:19` `CONTRACT_VERSION = 1` stays; PLAN §4.4 keeps v2 reserved for task 019 | | | ✅ |
| C4 | rulebook §4 (R4.2) | "Identical input → identical output." | For 007: the same file must yield the same reply on any host — which is exactly what the `display_errors` leak (S6/P7) breaks. H1's line-anchored qnames satisfy this for 025. | verified: `php -d display_errors=1` injects a `Warning:` into stdout, so the reply becomes host-dependent | | | ❌ |
| C5 | CLAUDE.md + rulebook §7 (R7.5) | "Every code comment is at most three lines." | Binding on the ~24 new code paths; the PR self-check gates it. | `Visitor.php` comments are all ≤ 3 lines today | | | ✅ |

Status legend: ✅ done/proven · ⚠ deferred (needs follow-up ticket) · ❌ not met.

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| AC1 (assertion site) | assertions live in **task 012** | R6.1 requires *this* task to ship "a fixture + conformance assertion"; 012 owns the cross-adapter suite (R3.4) | **N** | measurable — per-construct assertions run by `pytest` | **Self-resolved S1** by rulebook precedence, surfaced here rather than silently corrected. Contest at Gate 1 if the intent really was to ship 007 unasserted. |
| AC1 (denominator) | "each construct above" ≈ 21 named items | **N = 42** once the ticket's two list-bullets are expanded per-construct and R2.1's full-grammar duty adds nullsafe calls, property hooks and global `const` | **N** | measurable — one inventory row per construct, each with a `path:line`/test | Split at Gate 0 (H2): 007 proves the **protocol** denominator **N=18** (P1–P18); the 42-construct denominator moves to task 025. |
| AC1 ("correct") | "correct nodes/edges" | Unmeasurable as an adjective. Pinned to: for each inventory item, the emitted rows match an expected `(kind, qualified_name, [modifiers/params/extra])` tuple asserted in a test, and `contract.validate()` returns `[]` with `ok is True` and non-empty `nodes` | **N** | measurable **after pinning** | Pinned definition proposed above; carried into design's verification plan. Reuses task 006's non-vacuity bar (`validate()` alone accepts an `ok:false` result). |
| AC2 | "grep-gate clean" | `ci.yml:112` — `grep -rEin --exclude-dir=vendor --exclude-dir=node_modules 'laravel\|symfony\|wordpress\|drupal\|magento' adapters/` matches nothing | **Y** | greppable, already CI-gated | none — but note the denylist is acknowledged-partial; `docs/tasks/024_ci-hardening.md` records that the authoritative gate lands with task 012. |

**Uncodified-standard items** (detect-and-surface; not silently enforced, not silently dropped —
route through `/mango:codify` provisional→ratify if they should become rules):

1. **Qualified-name spelling for anonymous declarations.** CONVENTION §3 fixes the qname convention
   for *named* symbols and is silent on anonymous classes, closures and arrow functions. → **H1**.
2. **Node kind for enum cases.** The vocabulary is fixed (CONVENTION §3) but does not say which kind
   an enum case takes. → **H3**.

## Inventory (universal "all/every/no" requirements)

### 007's active denominator — the protocol half

**`N = 18`.** After H2 the ticket's universal requirement is R4+R5 ("`--server` stdin loop matching
the subprocess protocol" + "`ErrorHandler\Collecting` → bad file returns `ok:false`, stream
continues"). The denominator comes from **PLAN §4.1's wire rules and `SubprocessAdapter`'s actual
failure modes**, not from the two ticket bullets — the same "examples are a hint, never the
denominator" discipline applied to the protocol. Review confirms **every** row, not a total.

| # | Item | Ph3/4 proven by (`path:line` / test) | Status |
|---|------|--------------------------------------|--------|
| P1 | Handshake is the **first** line, before any result, and passes `contract.validate_meta` | `adapter.py:190` `_read_handshake` | ❌ |
| P2 | Handshake declares `name`, `extensions: [".php"]`, `contract_version: 1` | `adapter.py:202` rejects a version mismatch loudly | ❌ |
| P3 | Handshake declares `capabilities` — `{}` is legal and the core degrades (R1.6) | `adapter.py:111`, `contract.py:95` | ❌ |
| P4 | Lock-step: one request line → **exactly one** reply line, correlated by `path` | `adapter.py:239` raises on a mismatched `path` (desync is loud) | ❌ |
| P5 | Loop exits cleanly on EOF, so `stop()` completes at `wait()` without escalating to terminate/kill | `adapter.py:282` `_shut_down` | ❌ |
| P6 | A blank or non-JSON **request** line does not desync the stream | PLAN §4.1 wire rules (`PLAN.md:91`) | ❌ |
| P7 | **stdout is protocol-only** — `display_errors` forced to `stderr` so a PHP warning can never land between two protocol lines (S6) | verified: `php -d display_errors=1` prints `Warning:` on stdout | ❌ |
| P8 | stderr output stays bounded; the driver may send it to `DEVNULL` or a file without deadlocking | `adapter.py:178` `_open_stderr` | ❌ |
| P9 | UTF-8, `\n`-framed, one line per message however large (a 2 MB line is normal) | `PLAN.md:93` | ❌ |
| P10 | An unencodable result fails **that file** softly, never repaired into mojibake | already: `index.php:50` — must survive the rewrite | ✅ |
| P11 | `ErrorHandler\Collecting`: a **recoverable** parse error → `ok:false` + error string, stream continues (R5.1) | `index.php:44` is a `catch (Throwable)` today | ❌ |
| P12 | An **unreadable** file → `ok:false`, stream continues | already: `index.php:26` — must survive the rewrite | ✅ |
| P13 | An **unrecoverable** parse error → `ok:false`, process still alive for the next request | — | ❌ |
| P14 | Missing `vendor/` still fails **loud**: stderr, exit 2, never as a parse result (R5.3) | already: `index.php:11`, covered by a 006 test | ✅ |
| P15 | Bad/unknown argv still fails loud with usage, exit 2 | already: `index.php:19` — must still reject unknown modes | ✅ |
| P16 | `--file` preserved unchanged — 12 spike tests and `README.md:24` depend on it | `tests/test_php_adapter_spike.py:37` | ✅ |
| P17 | Edges stay **bare** — `target_qname` never set by the adapter (R3.3 / matrix R6) | `Visitor.php:194` | ✅ |
| P18 | **End-to-end:** a real `SubprocessAdapter` drives the real PHP adapter and returns valid `ParseResult`s — the first live integration of task 005 and task 006 | no such test exists | ❌ |

**Tally: 7 already satisfied and must survive the rewrite · 11 unbuilt.** P10/P12/P14/P15/P16/P17 are
regression rows, not free passes: the `--server` rewrite touches the same entry point, so review
re-confirms each.

### Deferred to task 025 — the grammar half (recorded, not dropped)

The 42-item construct inventory below was built at Gate 1 and **moves wholesale to task 025**
(created in Phase 3 with its BACKLOG row). It is kept here as the evidence base for that ticket's
own analysis; **007 does not prove these rows**. H1 governs rows 9/19/20 and H3 governs row 17.

- **Denominator / total N: 42** — every construct R1+R2 name, expanded per-construct, plus the three
  full-grammar items R2.1 adds and the three protocol items (rows 42 → superseded by P1–P18 above).
- Current state measured on `fc85dc6` by running the adapter, not by reading it.

| # | Item | Ph3/4 proven by (`path:line` / test) | Status |
|---|------|--------------------------------------|--------|
| 1 | `Namespace_` named → `Namespace` node | already: `Visitor.php:56` | ✅ |
| 2 | Braced / global namespace (`name === null`) emits **no** `Namespace` node, and does not corrupt the scope stack | already: `Visitor.php:57`, `leaveNode` marker `Visitor.php:84` | ✅ |
| 3 | `Class_` → `Class` node | already: `Visitor.php:129` | ✅ |
| 4 | `abstract` / `final` / `readonly` class modifiers | already: `Visitor.php:242` | ✅ |
| 5 | `Interface_` → `Interface` node | already | ✅ |
| 6 | `Trait_` → `Trait` node | already | ✅ |
| 7 | `Enum_` pure → `Enum` node | already | ✅ |
| 8 | `Enum_` **backed** — backing scalar type captured (`Enum_::$scalarType`) | — | ❌ |
| 9 | **Anonymous class** → node with a deterministic qname (H1) | `NameResolver.php:79` sets `namespacedName = null`; `Visitor.php:61` skips it | ❌ |
| 10 | `ClassMethod` → `Method` node + modifiers + params | already: `Visitor.php:70` | ✅ |
| 11 | `Property` → `Property` node, visibility/static/readonly modifiers | already: `Visitor.php:94` | ✅ |
| 12 | Property **declared type** captured (`Stmt\Property::$type`) | type is read for params only (`Visitor.php:234`) | ❌ |
| 13 | **Promoted** constructor property (`Node\Param::$flags != 0`) → `Property` node | — | ❌ |
| 14 | **Property hooks** (PHP 8.4 `Node\PropertyHook`) — S3 | — | ❌ |
| 15 | `ClassConst` → `ClassConst` node | already: `Visitor.php:101` | ✅ |
| 16 | `ClassConst` modifiers (`final`/visibility) and typed constants | not captured | ❌ |
| 17 | **Enum case** (`Stmt\EnumCase`) → node (kind per H3) | measured: `Status::Active` emits nothing | ❌ |
| 18 | `Function_` → `Function` node | already: `Visitor.php:64` | ✅ |
| 19 | **Closure** (`Expr\Closure`) → `Function` node, qname per H1 | — | ❌ |
| 20 | **Arrow function** (`Expr\ArrowFunction`) → `Function` node, qname per H1 | — | ❌ |
| 21 | **Global `const`** (`Stmt\Const_`) → `Const` node — S4 | `contract.py:33` reserves `Const`; nothing emits it | ❌ |
| 22 | `File` node with correct `line_end` | already: `Visitor.php:44` | ✅ |
| 23 | `EXTENDS` — class single parent | already: `Visitor.php:145` | ✅ |
| 24 | `EXTENDS` — interface **multiple** parents | already: `Visitor.php:151` | ✅ |
| 25 | `IMPLEMENTS` — class and enum | already: `Visitor.php:155` | ✅ |
| 26 | `USES_TRAIT` from `Stmt\TraitUse` | measured: `[]` — no code path | ❌ |
| 27 | Trait **adaptations** (`insteadof` / `as` aliasing) — conflict resolution per PLAN §6 | — | ❌ |
| 28 | `CALLS` from `FuncCall` | already: `Visitor.php:122` | ✅ |
| 29 | `CALLS` from `MethodCall`, tier `HEURISTIC` | already: `Visitor.php:112` | ✅ |
| 30 | `CALLS` from **`NullsafeMethodCall`** (`$o?->m()`) — S2 | distinct class; no code path | ❌ |
| 31 | `CALLS` from `StaticCall` | already: `Visitor.php:116` | ✅ |
| 32 | **First-class callable** `f(...)` (`CallLike::isFirstClassCallable()`) distinguished from a call | currently emits a plain `CALLS` | ❌ |
| 33 | `NEW` with a static `Name` | already: `Visitor.php:110` | ✅ |
| 34 | `NEW` with an anonymous class, and `new $var` → `DYNAMIC` (R5.2) | guarded out at `Visitor.php:110` | ❌ |
| 35 | `IMPORTS` from plain `Use_` | already: `Visitor.php:106` | ✅ |
| 36 | `IMPORTS` — **alias** captured (`UseItem::$alias`) | alias dropped | ❌ |
| 37 | `IMPORTS` — **function/const** import type (`Use_::TYPE_*`) distinguished | type dropped | ❌ |
| 38 | `IMPORTS` from **`GroupUse`** (incl. mixed-type group use) | no code path | ❌ |
| 39 | `INCLUDES` literal path | already: `Visitor.php:162` | ✅ |
| 40 | `INCLUDES` variable path → `DYNAMIC` | already: `Visitor.php:170` | ✅ |
| 41 | **Attributes** captured raw on declarations (R3) | no code path | ❌ |
| 42 | `--server`: handshake + lock-step loop (R5) **and** `ErrorHandler\Collecting` keeping the stream alive on a bad file (R4), with `--file` preserved | `index.php:19` rejects anything but `--file`; 12 spike tests depend on `--file` | ❌ |

**Tally: 18 already satisfied by the 006 spike · 24 unbuilt** — of which **23 are task 025's**
(rows 1–41) and row 42 is superseded by P1–P18 above.

### Surface inventory

`SURFACES: n/a` — TRACK is backend (`.harness.json:19`) and the repo has no UI surface, so the
surface inventory, the M1–M10 rubric and `DESIGN.md` are inert for this ticket (S5).

## Clarifications

`CLARIFICATION: 9 raised | 6 self-resolved (cited) | 3 answered at Gate 0 | 0 outstanding`

**Self-resolved (cited):**

- **S1 — AC1's assertions ship in 007, not deferred to 012.** R6.1 (`ENGINEERING_RULES.md:82-85`)
  makes a fixture + conformance assertion the definition of done for *any* adapter change, and R6.2
  requires them spec-driven. Task 012 owns the cross-adapter conformance suite (R3.4,
  `ENGINEERING_RULES.md:57`), not this ticket's own correctness. Surfaced in the AC table, not
  silently corrected.
- **S2 — nullsafe method calls (`$o?->m()`) are in scope.** `Expr\NullsafeMethodCall` is a class
  distinct from `MethodCall` in the vendored parser, and R2.1 (`ENGINEERING_RULES.md:40`) + PLAN §6
  (`PLAN.md:184`) bind the adapter to the **full 8.5 grammar**, not to the ticket's example list.
- **S3 — property hooks (PHP 8.4, `Node\PropertyHook`) are in scope.** Same citation as S2; the
  class is present in the vendored parser and carries its own params.
- **S4 — global `const` declarations are in scope.** `contract.py:33` reserves a `Const` node kind
  that no adapter emits, and `NameResolver.php:119-122` assigns `namespacedName` to each
  `Node\Const_`, so it is emittable today. R2.1 full grammar.
- **S5 — no frontend gates.** `.harness.json:19` sets `track: "backend"`; the repo has no UI path,
  so `SURFACES`, the M1–M10 rubric and `DESIGN.md` are inert.
- **S6 — PHP diagnostics must be forced off stdout.** Verified on this host, not assumed: with
  `php -d display_errors=1`, a `Warning:` is written to **stdout**, landing between two protocol
  lines. `display_errors` is host/ini-configured (empty here, commonly `1` in dev and Docker
  images — which task 008 targets), so the same file would yield different results on two machines,
  which R4.2 forbids, and `SubprocessAdapter._read_line` (`code_atlas/adapter.py:221`) would hand
  the warning text to `json.loads` and soft-fail a file that parsed fine. PLAN §4.1 (`PLAN.md:92`)
  makes stdout protocol-only. → inventory row P7.

**Answered at Gate 0 (2026-07-31):**

- **H1 — anonymous-declaration qnames are line-anchored:** `\App\Models\User::save::{closure@42}`,
  `\App\Models::{class@17}`, `tests/x.php::{fn@8}`. Satisfies C4/R4.2 (the start line is a pure
  function of the file's own text) and, unlike an ordinal, an inserted closure does not rename every
  later one. Collision only if two anonymous declarations open on the same line — add `:col` if it
  ever bites. **Applies to task 025**, which owns rows 9/19/20.
- **H2 — protocol first, then coverage.** 007 is re-scoped to the streaming protocol
  (`--server` + `ErrorHandler\Collecting`); the 23 grammar constructs move to a new task **025**.
  Rationale: 007 as re-scoped unblocks 008 and 009 — the critical path to the M3 ship — while only
  012 waits on grammar coverage. This is R7.1 applied.
- **H3 — enum cases reuse the `ClassConst` node kind**, with enum-ness recorded in `extra`. No
  `CONTRACT_VERSION` bump, so PLAN §4.4's v2 stays reserved for task 019. Grounded in PHP's own
  reflection hierarchy (`ReflectionEnumUnitCase extends ReflectionClassConstant`). **Applies to
  task 025**, which owns row 17. C3 therefore drops to N/A for 007.

---

## Phase 1 — Analysis ✋ Gate 1

**Per-goal gap analysis (enhancement).**

| Goal | Current (`path:line`) | Target | Gap |
|------|------------------------|--------|-----|
| Language coverage (§6) | `Visitor.php` dispatches 4 class-like kinds, methods, properties, class consts, functions, and 6 edge families — 18/42 inventory items | full 8.5 grammar per R2.1 | **24 constructs**, concentrated in: anonymous/inline declarations (9, 19, 20, 34), trait semantics (26, 27), the `use` family (36, 37, 38), member detail (8, 12, 13, 14, 16, 17, 21), attributes (41) |
| Protocol (§7, §4.1) | `index.php:19` accepts `--file` only; failure handling is a `catch (Throwable)` at `index.php:44` | handshake + lock-step stdin loop + `ErrorHandler\Collecting` | the adapter has **never been driven by `SubprocessAdapter`** — this ticket is the first live integration of the two halves built in 005 and 006 |

**Handler / entry point + blast radius.**

- Entry points: `adapters/php/index.php` (argv dispatch), `adapters/php/src/Visitor.php` (traversal).
- Consumers of `--file` — **must keep working**: `tests/test_php_adapter_spike.py` (12 tests, 5 of
  which skip without PHP + `vendor/`), and `adapters/php/README.md:24` which documents it as the
  debugging mode. `--server` is *added*, never a replacement.
- Consumer of `--server`: `code_atlas/adapter.py:75` `SubprocessAdapter`. Its handshake check
  (`adapter.py:190-209`) is strict — a missing line, a bad shape, or `contract_version != 1` is a
  loud `AdapterError`. `tests/test_config.py:99-195` already assumes a launch argv ending `--server`.
- Contract surface: `code_atlas/contract.py` — touched **only** if H3 resolves toward a new node
  kind, which would force `CONTRACT_VERSION` + `tests/contract/` in the same change (R3.1, C3).
- Not touched: `store.py`, `resolver.py`, `indexer.py`, `tools/`. No DB schema change, no migration.
- No `db-map` exists under `docs/`, so no schema-dependent blast radius to widen into.

**RULE SECTIONS** — applicable sections derived from the change type (adapter parser change ·
subprocess protocol · possible contract-vocabulary change · new dependencies-free code · new tests):

`RULE SECTIONS: §1 ✅ · §2 ✅ · §3 ✅ · §4 ✅ · §5 ✅ · §6 ✅ · §7 ✅ · §8 ✅ — 8/8 checked, 0 unchecked`

- **§1 Architectural boundaries** ✅ — R1.1/R1.3/R1.4 → C1. All new code under `adapters/php/`; core
  gains no PHP branch; adapter imports nothing from `code_atlas/`. R1.2/R1.6 N/A-with-reason: no new
  abstraction and no capability flag is proposed (adapter #2 does not exist yet).
- **§2 Standard over sample** ✅ — R2.1 drives S2–S4 and the N=42 denominator; R2.2/R2.3 → C2/AC2.
- **§3 Contract frozen & versioned** ✅ — R3.3 → R6 (bare edges). R3.1/R3.2 → C3: **mandatory** here
  because H3 can change the vocabulary; if it does, the version bump and `tests/contract/` update
  ride this same change.
- **§4 Determinism** ✅ — R4.2 → C4, load-bearing for H1 (anonymous qnames must be a pure function of
  the file text). R4.1 N/A-with-reason: no LLM/network anywhere near an adapter. R4.3 N/A: no writer.
- **§5 Error handling** ✅ — R5.1 → R4 (`Collecting`); R5.2 → inventory rows 29, 32, 34, 40
  (`HEURISTIC`/`DYNAMIC` tiers); R5.3 → the handshake and argv failures must stay loud (`index.php:11`
  pattern preserved).
- **§6 Testing** ✅ — R6.1/R6.2 → S1 and AC1's pinned definition; R6.5 → any new sweep or gate over
  `adapters/` must keep excluding `vendor/` and stay non-empty-guarded.
- **§7 Change discipline** ✅ — R7.1 → **H2** (is one L-sized card the smallest useful thing?);
  R7.2 → BACKLOG + frontmatter sync at finalise; R7.3 → commit hygiene, CI-gated since task 024;
  R7.5 → C5.
- **§8 Dependencies** ✅ — R8.1/R8.3: no new Composer dependency is anticipated (`nikic/php-parser`
  already provides `ErrorHandler\Collecting`); if one is added, `composer.lock` ships with it.
- **DB-conventions section:** N/A — this rulebook has none, and the change contains no migration or
  schema edit. **Design-token / a11y section:** N/A — TRACK is backend, no UI surface (S5).

**Self-audit.**

- Every section decomposed: 4/4 ✅ · every acceptance value falsifiable or pinned ✅ (AC1's "correct"
  pinned to a measurable tuple-match; no AC carries a bare `✅`)
- `BASELINE` captured on the untouched checkout ✅ · **active inventory N=18** (P1–P18), one row per
  protocol guarantee ✅; the 42-construct inventory is recorded and carried to task 025, not dropped ✅
- Matrix `Status` filled on all 15 rows ✅ (`⚠ 025` on R1–R3 = deferred with an owner, not unmet)
- `RULE SECTIONS` 8/8 emitted ✅
- Multi-clause split: the R5/R6 bullet split into two rows ✅; R4+R5's protocol clauses expanded to
  18 individually falsifiable rows rather than one aggregate ✅
- `STRUCTURE: native` · `TRACK: backend` · `TIER: full` · `SCOPE: M` (re-declared from L) ✅
- **`j = 0` → Gate 0 cleared** (H1, H2, H3 answered 2026-07-31 and recorded above).
- **Gate 1 status:** waiting on user

---

## Phase 2 — Design ✋ Gate 2

**Approach.**

1. **Extract the parse into `adapters/php/src/Parser.php`** — a `final class Parser` that builds
   `ParserFactory` + parser **once** and exposes `parse(string $path): array` returning a contract
   result. Both modes call it, so `--file` and `--server` produce identical output *by construction*
   rather than by promise (P16), and server mode gets the "one process boot amortized across all
   files" property §4.1 promises. Two immediate call sites justify the class (R1.2/R7.4).
2. **`index.php` becomes argv dispatch only** — `--file <path>` | `--server` — and its **first**
   statement is `ini_set('display_errors', 'stderr')`, before any output (P7/S6). Missing `vendor/`
   and bad argv keep failing loud with exit 2 (P14/P15, R5.3).
3. **`--server`** writes the handshake line, then loops `while (($line = fgets(STDIN)) !== false)`
   in lock-step, with an **explicit `fflush(STDOUT)` after every reply**. `capabilities` is
   `new stdClass()`, never PHP's natural `[]`.
4. **`ErrorHandler\Collecting`** is shared by the parser and `NameResolver` (as PLAN §7 sketches).
   `hasErrors()` → `ok:false` carrying the first error message plus the error count; the process
   stays alive for the next request (R4/R5.1, P11/P13).
5. **`Parser` reads the file unsuppressed** (`file_get_contents`, dropping today's `@` at
   `index.php:25`). With the diagnostic destination now controlled, suppression only destroys
   information that belongs on stderr; the explicit `=== false` check keeps the soft-fail (R5.1).

**Rejected alternatives.**

- **Inline the loop in `index.php`, duplicating the parse per mode.** Rejected: two code paths can
  drift, which turns P16's regression guarantee from a structural fact into a promise.
- **Keep `ErrorHandler\Throwing` (today's `catch (Throwable)`).** Rejected: it surfaces only the
  first error and leaves `NameResolver`'s traversal-time errors outside the parse try-block shape.
  R4 names `Collecting` explicitly.
- **Reply to a malformed request line with a synthetic `path`.** Rejected: `adapter.py:239` raises
  on a path mismatch, so a fabricated reply converts a driver bug into a *misattributed* one. Skip +
  a stderr diagnostic keeps every well-formed later request in step.
- **Force `output_buffering` / `implicit_flush` via `ini_set`.** Rejected in favour of an
  unconditional `fflush(STDOUT)` — one line, and immune to any host ini rather than racing it.
- **Emit `capabilities` only when non-empty.** Rejected: an always-present key documents the
  handshake shape for adapter #2; `contract.validate_meta` accepts both, so this is a readability
  call, not a correctness one.

**Assumptions** — all four runtime/3p assumptions were **spiked** before this gate, using a
throwaway server prototype driven by the **real** `SubprocessAdapter` (scratchpad, not committed):

| Assumption | Tag | Spike result |
|------------|-----|--------------|
| Empty `capabilities` survives the handshake | **novel-untested → resolved** | **False as written.** `json_encode(['capabilities'=>[]])` yields `{"capabilities":[]}` — a JSON *array*. `contract.validate_meta` returns `meta.capabilities: list (expected an object of flag -> boolean)` → a loud `AdapterError` at startup. `new stdClass()` yields `{}` and validates. Design pinned to `stdClass`. |
| PHP CLI will not block a lock-step reader on an unflushed reply | **novel-untested → resolved** | **True, and the mechanism is documented, not luck:** CLI SAPI reports `output_buffering=0`, `implicit_flush=1`, and both hold when **stdout is a pipe**, not just a tty. The prototype completed a full handshake + 5 requests with no explicit flush. Belt-and-braces `fflush(STDOUT)` retained because both are ini-overridable. |
| `Collecting` yields `ok:false` and keeps the process alive | **novel-untested → resolved** | **True.** Prototype on a deliberately broken file: `ok=False error="Syntax error, unexpected '}', expecting T_VARIABLE on line 2 (1 error(s))"`, and the **next** request on the same process returned `ok=True nodes=6`. |
| A multi-megabyte reply survives one `\n`-framed line | **novel-untested → resolved** | **True.** A 4 000-class fixture produced 8 001 nodes in a **~2.1 MB single-line** reply, transported intact — PLAN §4.1's "a 2 MB result line is normal" literally exercised. |
| A host-set `display_errors` can corrupt stdout | **verified (analysis S6)** | Re-confirmed at design: `php -d display_errors=1` reading a **directory** prints `Notice: … Is a directory` **on stdout**, immediately above the JSON reply. With `ini_set('display_errors','stderr')` the Notice moves to stderr and stdout stays clean. This is the proving test's mechanism. |

No `novel-untested` assumption remains open.

**Smallest change-list** (every item traces to a matrix row):

| # | Change | File / area | Ph2 covered by | k/N |
|---|--------|-------------|----------------|-----|
| 1 | `final class Parser`: one parser boot, `parse(path): array`, `Collecting` shared with `NameResolver`, unsuppressed read | `adapters/php/src/Parser.php` (**new**) | R4, R6 | P10–P13, P17 → 5/18 |
| 2 | argv dispatch + `display_errors → stderr` as the first statement | `adapters/php/index.php` | R5, C4 | P7, P14–P16 → 4/18 |
| 3 | `--server`: handshake (`capabilities` = `stdClass`) + lock-step loop + `fflush(STDOUT)` | `adapters/php/index.php` | R5 | P1–P6, P8, P9 → 9/18 |
| 4 | Server-mode integration suite driven by the real `SubprocessAdapter` | `tests/test_php_adapter_server.py` (**new**) | AC1, R4, R5 | P1–P9, P11, P13, P18 → 13/18 |
| 5 | Fixture carrying a recoverable syntax error | `tests/fixtures/php/syntax_error.php` (**new**) | R4 | P11 → 1/18 |
| 6 | **Proof collateral** — README: `--server` is live; document the launch string and both host-ini hazards; drop the "arrives with task 007" note | `adapters/php/README.md:24,25,63` | R5 | — |
| 7 | **Proof collateral** — the grammar half needs a ticket **and** a BACKLOG row, or `test_backlog_bookkeeping.py` goes red | `docs/tasks/025_php-adapter-grammar.md` (**new**), `docs/BACKLOG.md` | G1, R1–R3 | — |
| 8 | **Proof collateral** — 007 status sync in frontmatter **and** the BACKLOG row | `docs/tasks/007_php-adapter-visitor.md`, `docs/BACKLOG.md` | R7.2 | — |

**Union of the k/N column = P1–P18 = 18/18.** No inventory row is left without a planned proof.

**Test blast-radius (mechanical trace, not a name grep).**

- **Consumers of `--file`** — `grep -rn '\-\-file' tests/ adapters/`: `tests/test_php_adapter_spike.py:37`
  and `:135` (12 tests, 5 skipping without PHP + `vendor/`), plus `adapters/php/README.md:29`. Moving
  the parse into `Parser` must leave `--file` byte-identical; `test_php_adapter_spike.py:45` asserts
  `stdout.count("\n") == 1`, so any stray output breaks it. → item 6 covers the doc, item 1 the code.
- **Consumers of `--server`** — `code_atlas/adapter.py:75` `SubprocessAdapter`; `tests/test_config.py:99–195`
  already assumes a launch argv ending `--server` (config-level only, no adapter contact). No edit needed.
- **Authored-source sweeps** — `tests/test_sql_confinement.py` and `ci.yml:72` `php -l` both walk
  `adapters/` excluding `vendor/`; the new `src/Parser.php` joins both automatically and keeps each
  non-empty (R6.5). No edit needed, but review re-confirms.
- **Bookkeeping** — `tests/test_backlog_bookkeeping.py:57` asserts `len(backlog_statuses()) == len(task_files())`,
  so creating task 025 **without** its BACKLOG row turns 49 tests red. → item 7. A `todo` task needs no
  Token-usage row (`:77` returns early unless `done`), so 025 adds none.
- **Not touched:** `code_atlas/**` (confirms C1 — no core change), `store.py`, `resolver.py`,
  `contract.py` (H3 removed the vocabulary pressure), `docs/PLAN.md` (§4.1 already states
  "stdout is protocol-only"; the ini hazards are implementation detail, and §7's sketch stays accurate).

**Rule compliance.**

- **R1.1/R1.3/R1.4 (C1)** — every change is under `adapters/php/` or `tests/`; the core gains no
  branch and the adapter imports nothing from `code_atlas/`. `Parser` parses; it never touches SQLite.
- **R1.2/R7.4** — `Parser` is not a speculative seam: it has two call sites the moment it lands.
- **R2.1/R2.2 (C2, AC2)** — no repo or framework name enters `Parser.php`, the fixture, or the tests;
  the syntax-error fixture uses neutral names.
- **R3.3 (R6, P17)** — `Parser` reuses `Visitor` unchanged, so edges stay bare. **R3.1/R3.2 (C3)** —
  no vocabulary change, `CONTRACT_VERSION` stays 1.
- **R4.2 (C4)** — the `display_errors` fix is precisely what makes the reply host-independent; the
  error message is the **first** collected error plus a count, which `Collecting` orders deterministically.
- **R5.1/R5.3** — soft: unreadable file, collected syntax error, unencodable result. Loud: missing
  `vendor/`, bad argv, and (driver-side) a bad handshake or desync.
- **R6.1/R6.2** — item 4 is the fixture-backed assertion set R6.1 demands; item 5 is spec-driven.
- **R6.5** — both sweeps stay non-empty and keep excluding `vendor/`.
- **R7.5 (C5)** — every new comment ≤ 3 lines. **R8.1/R8.3** — no new Composer dependency
  (`ErrorHandler\Collecting` ships with `nikic/php-parser`), so `composer.lock` is untouched.

**Verification plan** (one row per at-risk requirement; risk layer classified first):

| AC / req | risk layer | proof artifact | layer-match |
|----------|-----------|----------------|-------------|
| R5 · P1–P3 handshake shape + version | integration (the driver validates and fails loud) | integration — real `SubprocessAdapter.start()`, assert `name`/`extensions`/`capabilities` | ✅ |
| R5 · P4 lock-step correlation by `path` | integration | integration — N sequential `parse()` calls, each reply matched | ✅ |
| R5 · P5 clean EOF exit | runtime | integration — `stop()` completes at `wait()` with no terminate/kill | ✅ |
| R5 · P6 blank / malformed request | integration | integration — write raw lines to the child's stdin, assert no desync | ✅ |
| **P7 stdout protocol-only** | **runtime/3p (host ini)** | integration — launch under `-d display_errors=1`, request a **directory**, assert stdout is clean JSON **and** the Notice landed in the `stderr_path` file | ✅ |
| P8 stderr bounded / non-blocking | runtime | integration — `stderr_path` set, drive many requests, no deadlock | ✅ |
| P9 multi-MB single-line reply | integration | integration — generated large fixture, assert node count survives | ✅ |
| R4 · P11 recoverable error → `ok:false`, stream continues | integration/3p | integration — bad file **then** a good file on the **same** process | ✅ |
| P13 unrecoverable error → `ok:false`, process alive | integration/3p | integration — same shape, unrecoverable input | ✅ |
| P10/P12/P14/P15/P16 regressions | mixed runtime | the existing 12 `--file` spike tests, re-run unchanged | ✅ |
| P17 bare edges | logic | assertion over emitted edges: no `target_qname` key | ✅ |
| P18 core drives the real adapter | e2e | the integration suite itself is the e2e proof | ✅ |
| AC2 no repo/framework names | logic (greppable) | `ci.yml:112` grep-gate + `test_sql_confinement.py` sweep | ✅ |

**No layer-match `❌`.** Nothing is proven below its risk layer, so there are **no coverage-gap
exclusions** to record for this ticket.

**Coverage-gap exclusions:** none.

**Proving test.** Two named assertions, both at the integration/runtime layer, both failing
pre-change:

1. **Primary (R5, P18)** — `tests/test_php_adapter_server.py::test_the_core_drives_the_real_php_adapter_end_to_end`.
   Pre-change it fails at `start()`: `index.php` rejects `--server` with exit 2, so the driver raises
   `AdapterError("did not announce itself")`. Post-change it returns valid `ParseResult`s.
2. **Regression-class (P7)** — `tests/test_php_adapter_server.py::test_a_host_that_prints_warnings_cannot_corrupt_the_protocol`.
   Pre-change (no `ini_set`) the `Notice` lands on stdout and the driver soft-fails the file with
   "adapter emitted a line that is not JSON"; post-change the reply is a clean `ok:false` and the
   Notice is found in the stderr file.

Invocation: `.venv/bin/pytest tests/test_php_adapter_server.py -q` (whole suite: `.venv/bin/pytest -q`).
Both skip when PHP or `vendor/` is absent, so **`0 skipped` in CI remains the load-bearing evidence**
that the PHP path actually executed — the same bar task 006 set.

**Rollback + porting.** Branch `feat/007-php-server-mode`; revert by deleting the branch pre-merge,
or `git revert -m 1 <merge sha>` after. Every code change is additive (`--file` untouched, no core
change, no dependency, no DB or migration, no data written), so revert is complete and instant. The
only cross-file coupling is bookkeeping: reverting must also drop the 025 ticket **and** its BACKLOG
row together, or `test_backlog_bookkeeping.py` goes red. Porting: single repo (`app`), none.

**SCOPE confirmed: M** — unchanged from the Gate-0 re-declaration. 5 code/test items + 3
bookkeeping items, one new class, no new dependency, no core change. No tier crossing, no
*outgrew-its-ticket* nudge.

**Self-audit.** Every change-list item traces to a matrix row ✅ · `Ph2 covered by` filled, union
= 18/18 ✅ · all 5 assumptions tagged, all 4 `novel-untested` ones **resolved by recorded spike** ✅ ·
proving tests named and runnable ✅ · verification plan has **no ❌**, so no exclusions needed ✅ ·
rollback + porting recorded ✅ · frontend items inert (TRACK backend, S5) ✅.

- **Gate 2 status:** waiting on user

## Phase 3 — Execute

- **Branch:** `feat/007-php-server-mode` (from `main` @ `fc85dc6`)
- **Commits** (logical units, no AI-attribution trailer): see `git log main..HEAD`.
- **Proving tests added:** `tests/test_php_adapter_server.py` — 14 tests, 13 of which skip without
  PHP + `vendor/`. Confirmed **red before the change** (all 13 failed, the driver raising
  `AdapterError: adapter 'php' exited (code 2) with the stream open`), green after.
- **Result vs `BASELINE: green`:** `pytest` **316 passed** (300 baseline + 14 server + 2 new
  bookkeeping parametrisations for task 025), `ruff check .` clean, `mypy code_atlas` clean,
  `php -l` clean on all 3 authored adapter files, R2.2 grep-gate clean. No new failure.

**Negative controls** — a guard that cannot fail is not evidence (LESSONS 002). Each mutation was
applied to a `cp` copy and restored from it, never with `git checkout` (LESSONS 004); byte-identity
re-verified with `cmp` + `sha256sum` after every one.

| # | Mutation | Result |
|---|----------|--------|
| M1 | Delete `ini_set('display_errors', 'stderr')` | **1 failed, 12 passed** — exactly `test_a_host_that_prints_warnings_cannot_corrupt_the_protocol` |
| M2 | `capabilities` → PHP's natural `[]` | **11 failed, 2 passed** — every test that starts a server; the handshake is rejected at `start()` |
| M3 | Delete the flush after each reply | **13 passed** — the suite did *not* catch it; see deviation D1 |
| M4 | Revert `fwrite(STDOUT, …)` → `echo` + `fflush(STDOUT)` | **1 failed, 13 passed** — exactly the new buffering test, which now covers what M3 exposed |

**Verification sweep — Axis 1 (file set).**

- Zero stray references ✅ — the only `fflush(STDOUT)` occurrence left is inside the comment that
  explains why it is *not* used.
- Diff ⊆ approved change list ✅ — 8 files, each mapping to a Gate-2 item: `src/Parser.php` (1),
  `index.php` (2, 3), `tests/test_php_adapter_server.py` (4), `tests/fixtures/php/syntax_error.php`
  (5), `README.md` (6), `docs/tasks/025_*.md` + `docs/BACKLOG.md` (7), `docs/tasks/007_*.md` (8).
  **No file outside the list**; no untouched-line reformatting; no formatter run over a shared file.
- `code_atlas/` **untouched** ✅ (C1) · `CONTRACT_VERSION` still `1` ✅ (C3) · `composer.lock`
  untouched ✅ (R8.3 — `ErrorHandler\Collecting` ships with the pinned parser).

**Verification sweep — Axis 2 (design-conformance self-check).** Walking each Gate-2 Approach bullet:

| Gate-2 Approach bullet | Verdict |
|------------------------|---------|
| 1 — extract `Parser.php`, parser built once, both modes call it | implemented-as-approved |
| 2 — `index.php` argv dispatch, `display_errors → stderr` first | implemented-as-approved |
| 3 — handshake + lock-step loop + **explicit `fflush(STDOUT)`** | **deviated → D1** |
| 4 — `Collecting` shared with `NameResolver`, `hasErrors()` → `ok:false` + count | implemented-as-approved |
| 5 — unsuppressed file read | implemented-as-approved |

**Design-conformance deviations** (surfaced to review for adjudication):

| ID | Approved Gate-2 bullet | What was implemented instead | `path:line` |
|----|------------------------|------------------------------|-------------|
| D1 | "unconditional `fflush(STDOUT)` — immune to any host ini" | `fwrite(STDOUT, $line . "\n")`. The approved rationale was **false**: `echo` writes into PHP's *output buffer*, and under `-d output_buffering=8192 -d implicit_flush=0` **both** `fflush(STDOUT)` and `flush()` still deadlocked the reader (measured: blocked until timeout); only `fwrite` to the stream got through. Intent preserved and now actually achieved, plus proven — M3 showed the approved line was unproven, M4 shows the replacement is load-bearing. | `adapters/php/index.php:56` |
| D2 | inventory row **P13** — "an *unrecoverable* parse error → `ok:false`, process alive" | The premise is largely false: `ErrorHandler\Collecting` **recovered from every syntax error that could be constructed** (missing brace, stray token, unterminated string, unterminated comment) — none threw; `$ast` merely came back `NULL`. P13 is proven in its reachable form (a file the parser cannot build statements from returns `ok:false` and the process serves the next request), while the `catch (Throwable)` stays a **defensive backstop with no reachable source fixture**. Recorded as a coverage-gap exclusion rather than claimed proven. | `adapters/php/src/Parser.php:52` |

**Coverage-gap exclusion added at execute** (design recorded none; this one is requested of review):

| Item | Risk tier | Why deferred | Follow-up |
|------|-----------|--------------|-----------|
| P13's `catch (Throwable)` backstop in `Parser::parse` | low — defensive only | `Collecting` recovers from every constructible syntax error, so no source fixture reaches the catch; forcing one would mean faking a parser fault, which proves the fake, not the adapter | Revisit if task 015's 112k-file scale run trips it; a real hit arrives as a `parsed_ok=0` row carrying a non-syntax message |

**Inventory progress — 18/18 rows carry a proof.** P1–P4, P6, P9, P16, P17 by the new server tests;
P5 by `test_the_server_exits_cleanly_when_its_stdin_closes`; P7 by the `display_errors` test
(negative-controlled, M1); P8 by the `stderr_path` assertion in that same test; P10/P12/P14/P15 by
the 12 unchanged `--file` spike tests; P11 by `test_a_bad_file_fails_softly_and_the_next_file_still_parses`;
**P13 partially — see D2**; P18 by the suite as a whole. One guarantee was added beyond the 18: the
output-buffering defence, which the design had assumed rather than proven.

## Phase 4 — Review ✋ (stop only if not clean)

- reviewer verdict: **not dispatched** — skipped by user instruction ("chạy challenger là đủ").
- challenger (ticket-blind) result: _pending_
- Scope reconciliation: Axis 1 clean (see Phase 3); Axis 2 carries deviations **D1** and **D2** for
  adjudication.
- Proving test result vs `BASELINE: green`: 316 passed, 0 failed, 0 skipped locally.
- **Clean?** _pending challenger_
- **Reviewed at:** _pending_

## Phase 5 — Finalise ✋ final gate

- PR draft: `/tmp/pr-007.md`
- Planned outward actions (each needs separate approval): _pending_

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| 1 — analysis | none dispatched (`explore_fanout` available but the session forbids subagents unless requested) | — | 0 dispatch | rtk active; per-task saving not attributable (`rtk gain` is global all-time) |

## Decision log

| When | Decision | Why |
|------|----------|-----|
| Phase 1 | AC1's denominator is 42, not the ~21 the ticket enumerates | R2.1 binds the adapter to the full 8.5 grammar; the ticket's list is an example set, and counting only what it named is how a tail ships unproven |
| Phase 1 | AC1's assertions ship in 007 (S1) | R6.1 makes tests the definition of done for an adapter change; 012 owns the cross-adapter suite, not this ticket's own correctness |
| Phase 2 | Spiked all 4 novel-untested runtime assumptions against the **real** `SubprocessAdapter` before Gate 2 | Design step 3 forbids passing Gate 2 on an unresolved 3p/runtime assumption — and the spike caught the `capabilities: []` trap, which would have been a confusing loud startup failure at execute |
| Phase 2 | Extract `Parser.php` rather than branching inside `index.php` | Makes "`--file` and `--server` agree" a structural fact instead of a promise (P16), and gives server mode the one-boot amortization §4.1 promises. Two call sites, so not a speculative seam (R1.2/R7.4) |
| Phase 2 | Drop the `@` on the file read | The diagnostic destination is now controlled (P7), so suppression only destroys information belonging on stderr; the explicit `=== false` check keeps R5.1's soft-fail |
| Phase 2 | A malformed request line is skipped with a stderr note, never answered | `adapter.py:239` raises on a path mismatch, so a fabricated reply would turn a driver bug into a misattributed one |
| Phase 1 | `SCOPE: L` | 24 unbuilt constructs across two distinct concerns (grammar coverage, streaming protocol) — the basis for H2 |
| Gate 0 | **H2: 007 re-scoped L → M**; the 23 grammar constructs split out to a new task **025** | R7.1 — the protocol half is the smallest useful thing and it alone unblocks 008/009, the critical path to the M3 ship. 012 is the only consumer of grammar coverage |
| Gate 0 | **H1: anonymous qnames are line-anchored** (`…::{closure@42}`) | A pure function of the file's own text (C4/R4.2); unlike an ordinal, inserting a closure does not rename every later one. Applies to 025 |
| Gate 0 | **H3: enum cases reuse `ClassConst`**, enum-ness in `extra` | Avoids spending the `CONTRACT_VERSION` bump PLAN §4.4 reserves for task 019; matches PHP's own `ReflectionEnumUnitCase extends ReflectionClassConstant`. Applies to 025 |
| Phase 1 | **S6: `display_errors` must be forced to stderr** | Verified, not assumed: `php -d display_errors=1` writes `Warning:` to stdout between protocol lines, so the same file yields different results on two hosts (R4.2) and a clean parse soft-fails |

## Session status

- **Last updated:** Phase 3 complete, on branch `feat/007-php-server-mode`
- **Current phase:** Phase 3 — Execute, complete; flowing into Phase 4 (review)
- **Next action:** run the ticket-blind `challenger` on the raw ticket + the branch diff (the
  `mango:reviewer` dispatch is skipped by user instruction), adjudicate deviations D1 and D2, then
  finalise and open the PR.
- **Blocked on:** nothing
