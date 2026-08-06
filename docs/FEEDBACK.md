# FEEDBACK.md — external review & assessments

A running log of external comments/feedback on code-atlas and the repo-verified assessment of
each. **Ordered latest-first.** This is a record, not a decision: any conclusion that changes the
product is ratified in [`PLAN.md`](PLAN.md) §19 and reflected in [`BACKLOG.md`](BACKLOG.md).

Each entry keeps three things separate: (a) the prompt/question that produced the feedback,
(b) the reviewer's points, (c) **Assessment** — what was verified against the repo, including
corrections where the feedback was stale or wrong (cited `file:line`).

---

## Round 4 — 2026-08-05 — Field report: Serena OOM under parallel agents (does code-atlas share the failure?)

**Source:** a real incident on **anchor-repo** (~55k-file PHP monorepo, the §19 anchor). Running
`/parallel-tasks` — one `claude --bg` agent per Jira ticket, each in its own git worktree — the
machine hit **out-of-memory** during the fan-out.

**The field report (verbatim mechanism):** `claude --bg` **inherits the launching session's MCP
config**, so every background agent starts **its own Serena**, and each Serena forks **its own
Intelephense** (Node PHP LSP) that indexes the whole tree into RAM. Cost ≈ **5.6 GB per agent**
(Serena Python 4.25 GB + Intelephense 1.4 GB), scaling **linearly** — a 5-agent batch ≈ 15–16 GB for
Serena alone, an OOM on a 16 GB box. Two aggravating facts: (i) every agent's Serena was launched
with `--project <mainrepo>` **hardcoded**, so a worktree agent querying symbols got **`main`'s
symbols, not its own edits** — wasteful *and wrong*; (ii) servers **lingered** after the run and
memory wasn't reclaimed. Fix: dispatch bg agents with an **empty MCP config file + `--strict-mcp-config`**
(zero MCP servers), keeping Serena only on the main interactive session.

**The question this raises for code-atlas:** it is the same consumer (an AI agent in a terminal, §19 /
round 3) on the same repo. **Does code-atlas cause the same OOM cascade under a parallel fan-out?**

**Assessment (repo-verified):** The catastrophic RAM cascade — **NO**. The wrong-tree correctness
bug — **NO, the opposite**. The MCP-config-inheritance behaviour — **YES, structurally identical but
benign**. There is one honest, non-fatal caveat (a transient build-time process burst). In detail:

- **No resident language server holding the index in RAM.** Serena's 5.6 GB was a *resident*
  Intelephense (whole 55k-file index expanded in memory) plus Serena's Python, alive for the whole
  session. code-atlas keeps **nothing** resident: every query tool opens the SQLite index, reads, and
  closes **per call** (`code_atlas/tools/find_callers.py:67` — `with GraphStore(config.db_path) as
  store:`); the graph is an **on-disk** file the OS pages in, never a whole-tree in-RAM structure. The
  MCP server process holds only config + FastMCP registrations (`code_atlas/main.py:51-82,104`), no
  graph. A query against an un-built repo returns a cheap empty result and spawns nothing
  (`find_callers.py:64`).
- **The parser is transient, per-build, and parses one file at a time.** The PHP adapter is started
  only for a build/reparse and `stop()`ped in a `finally` (`code_atlas/indexer.py:102-104,182-184,
  234-236`); it serves **one file per request** (`code_atlas/adapter.py:83-88`), so a worker holds one
  file's AST — tens of MB — not the whole tree. This is the exact inverse of Intelephense, whose cost
  *is* the whole-tree resident index.
- **The build itself is bounded-memory.** The result queue is explicitly bounded with back-pressure
  (`indexer.py:511`, comment: "a slow writer back-pressures the workers instead of buffering the whole
  graph"), and edge resolution streams in 1000-row batches to "avoid loading the whole table"
  (`code_atlas/resolver.py:11-12,29`). Even a 112k-file build never assembles a multi-GB in-RAM graph.
- **Worktree correctness — fixed, not inherited.** `db_path` resolves relative to `Path.cwd()`
  (`code_atlas/config.py:117` + `main.py:104`), so a worktree agent reads the `.code-atlas/graph.db`
  in **its own** worktree — its own edits — and read-through freshness reparses a drifted file inline
  before answering (`code_atlas/tools/freshness.py`, capped at **1** reparse/call, `READ_THROUGH_CAP`).
  Where Serena's hardcoded `--project <mainrepo>` made worktree agents both wasteful and *wrong*,
  code-atlas is cheap *and* correct there.
- **MCP-config inheritance — the same behaviour, a different order of magnitude.** `claude --bg`
  inherits the parent MCP config regardless of the server, so if code-atlas is a configured MCP
  server, each background agent **does** start its own code-atlas core — the same inheritance the field
  report describes. The difference is entirely per-instance cost: a code-atlas core is a lightweight
  Python process (~tens of MB, no LSP), so `N` agents cost `N × tens-of-MB`, not `N × 5.6 GB`. The
  report's hygiene (`--mcp-config <file> --strict-mcp-config`, minding the variadic-flag order) is
  still correct practice for fan-outs — it just prevents megabytes here, not an OOM.
- **The one honest caveat — a transient build-time burst, not a resident leak.** If `N` background
  agents each trigger `build_or_update_index` **concurrently**, each build fans out up to `workers`
  PHP processes (`config.py:176-178`, default `max(1, min(cpu-2, 8))`) → `N × workers` short-lived PHP
  processes and CPU oversubscription. This is real but bounded and transient: adapters are reaped when
  the build ends (`adapter.py:349-367` escalates wait→terminate→kill), `workers` is configurable down,
  and worktree agents each build their **own** DB so they don't contend on one writer. Agents sharing
  **one** DB path would serialise writes (WAL single-writer, `busy_timeout=5000`, `store.py:49`) — a
  5 s wait, not an OOM. Nothing lingers: there is no resident server to leak, and the poke hook
  (task 036) is a short-lived process that exits.

**Net:** code-atlas converts the field report's "`N` × multi-GB resident language servers" into
"`N` × lightweight query processes over a shared on-disk index," and *fixes* the worktree wrong-tree
bug instead of inheriting it — so the specific OOM cascade does not reproduce. This is a strong
real-world confirmation of the §19 SQLite-index thesis. **Cheap follow-up (worth a runbook line, not
an architecture change):** for a parallel fan-out, cap `CA_WORKERS` and prefer a per-worktree index
(or one pre-built shared index queried read-only) over many concurrent builds; and apply the same
`--strict-mcp-config` hygiene the report recommends, for tidiness rather than survival.

---

## Round 3 — 2026-08-04 — "The consumer is an AI agent in a terminal, not an IDE"

**Prompt:** "I build code-atlas because AI will use it in their work instead of manual scan or
native grep. I use Claude Code via terminal, not a PHP IDE. As the architect, what do you want to
improve?"

**Reviewer's thesis (supersedes rounds 1–2):** The right baseline is not PhpStorm — it's
`grep -r` + `Read` + a context window. Against that, code-atlas wins on the axis that costs money:
**tokens spent per correctly answered question.** This dissolves the framework objection from
round 2: a *calibrated* HEURISTIC candidate list beats grep's unranked matches, because the tier
tells the model how much to trust each row.

Key points:
- **Metric to build the project around:** tokens-to-correct-answer vs a grep+Read baseline —
  ~40 known-answer questions across the sample matrix; publish the ratio; gate regressions. This is
  the product thesis made falsifiable. (Round 1's precision/recall-vs-LSP was the wrong metric.)
- **Empty ≠ unknown.** An `[]` reads to a model as "nothing exists," so it will confidently report
  dead code. Every response needs a reason code: `no_such_symbol` / `not_indexed` / `index_stale`
  / `filtered_by_tier` / `truncated`. Generalize the `get_index_status.next_tool_suggestions`
  instinct to every tool.
- **Freshness must be enforced, not surfaced.** A human rebuilds a stale index; an agent won't. So
  read-through invalidation (reparse a file inline on hash drift before answering) becomes
  correctness. Ship a Claude Code `PostToolUse` hook on Edit/Write to poke the index — a
  distribution move worth more than several features.
- **Fewer, more compound tools.** Every tool costs schema tokens in every request. Consolidate
  `find_callers`/`find_references`/`find_implementations` → one `find_relations(qname, relation)`;
  make results answer completely (return the call-site line — the agent's next call is always
  "show me"). Round-trips are the real cost.
- **Tool descriptions are the product surface** — engineer them (incl. negative guidance) and eval
  them ("given N user questions, does the model pick the right tool?"). CONVENTION §6 already makes
  the docstring the description; the eval is missing.
- **Lean into task-level questions** ("what breaks if I change this," "where is auth handled") —
  why `impact` and 031 reachability matter more than parity features. Add `explain_path(from, to)`.
- **Drops in priority:** symbolic editing (cede to native `Edit` permanently, say so in §1),
  rename, type inference (below response-shape work now), TS/JS (finish the agent-PHP loop first).

**Reviewer's proposed order:** 1) reason codes + truncation honesty everywhere → 2) tokens-to-answer
benchmark → 3) read-through freshness + Claude Code hook → 4) finish 031 → 5) tool consolidation +
compound responses → 6) `explain_path` → 7) vendor stubs, then framework rules as data. Plus: fix
the license line.

**Assessment (repo-verified):**
- Reframe is correct and is the strongest of the three rounds; it is the authoritative framing.
- `next_tool_suggestions` precedent is real and already filtered to registered tools
  (`code_atlas/tools/get_index_status.py:59,81,114`) — "generalize this instinct" is well-founded.
- **Reason codes: PARTIAL, targeted.** `read_symbol` already distinguishes not-found vs stale
  (`read_symbol.py:38-61`); `reachable_from`/`find_orphans` carry a status enum (`reach_shared.py`).
  Missing specifically from the core `find_*`/`search` tools, which return a bare
  `{indexed, results: [], truncated}` for both "no callers" and "no such symbol" (`nav_result.py:60-79`).
- **Truncation is ALREADY honest** — a `truncated` bool is on every nav/search response
  (`find_callers.py:90`, `search_symbol.py:37`). The real gap is a `total_count`, not the flag.
- Three separate relation tools confirmed (`main.py:63-68`) → consolidation proposal is coherent.
- `explain_path` does not exist (confirmed).
- Architect's divergences: take the **compound-response** half (call-site line + reason codes are
  pure wins) but hold on **merging** the three tools — it muddies each description and collides with
  the one-module-per-tool convention (R1.2); A/B it *with the new benchmark*. Deferring TS/JS
  (019/020/021) indefinitely is the user's call, not the reviewer's — it trades the
  language-agnostic thesis and belongs in a written §19 decision.

---

## Round 2 — 2026-08-04 — "Would a PHP master use it? Is it useless on frameworks?"

**Prompt:** "As a PHP master, would you use code-atlas? … So it's good for plain PHP and useless
for Laravel/Symfony?"

Reviewer's points:
- **Use it on:** big legacy monoliths, and any project worked with an AI agent — both underserved.
  **Skip on:** a modern typed Laravel/Symfony app at PHPStan level max, where PhpStorm + Laravel
  Idea/Symfony plugins already cover it and `find_callers` would miss facade/container callers.
- **Most-valued property:** it writes a SQLite file you can query yourself (migration/teardown
  audits) — nothing else in the PHP ecosystem hands you the graph cheaply. `include_graph` on
  `require_once` code is the same story.
- **"Useless on frameworks" is too strong.** ~70% of the graph works on a framework app (declarations,
  extends/implements/use, `new X`, FQN static calls — all RESOLVED; namespaced+typed helps). What
  breaks is dispatch the framework moves out of static PHP: facades (`__callStatic`), container-by-
  string (`app('id')` → DYNAMIC), Eloquent magic, Symfony `services.yaml`/route wiring (not `.php`),
  `vendor/` base classes dangling, Blade files. **All degrade honestly** — HEURISTIC/DYNAMIC/absent,
  never confident-wrong.
- **"Good for plain PHP" is too kind too** — legacy has its own nightmare (variable includes,
  `call_user_func`, `$$var`, `global`). code-atlas wins there because the alternatives are worse.
- Adoption blockers: **License: TBD**; not on PyPI (git-clone workflow); needs Python+PHP+Composer;
  `vendor/` unindexed; index stale until rebuilt; **no accuracy benchmark**.
- What earns trust: the CLI-protocol details done right (stdout error leakage, `output_buffering` +
  `fwrite(STDOUT)`, `ErrorHandler\Collecting`, never promoting a unique name-match to RESOLVED).

**Assessment (repo-verified):**
- License TBD confirmed (`README.md:184`, no `LICENSE` file) — genuine hard stop for commercial use;
  cheapest fix; do first.
- `vendor/` ignored by default (`ignore.py:18`) → framework base classes dangle. Biggest single
  gap, closable with a declarations-only stub index.
- Blade routing confirmed: `foo.blade.php`.suffix == `.php`, matched and sent to the PHP adapter
  (`indexer.py:161`, last-segment match); no blade ignore rule. Wasted adapter calls returning
  symbol-less HTML — noise, not corruption; a one-line ignore fixes it.
- Self-query thesis holds: `edges.source_qname/target_qname`, `nodes.qualified_name/file_path` all
  exist (`store.py:56-66`). Worth promoting to a first-class, documented feature.
- Packaging: `pyproject.toml` exists but not published; install is git-clone + `scripts/setup.py`.
- **Correction:** "590 tests" is wrong — ~354 `def test_` functions. The point (tests prove intent,
  not accuracy) survives.

---

## Round 1 — 2026-08-04 — "As creator, what to improve to replace Serena for every PHP project?"

**Prompt:** "If you're the code-atlas creator, what to improve? Purpose: replace Serena, run on
every PHP project."

Reviewer's points:
- **Strategic call:** depth-in-PHP is the credible goal; "replace Serena for 67 languages" is not.
  Defer TS/JS (019) and 020/021; spend the budget on PHP. Own the pivot in §19 and rewrite the §1
  sentences ("complements Serena," "no type inference in the core") that were written for the old goal.
- **Two decisive changes:** (1) **read-through freshness** — on a tool touching file X, compare X's
  hash to `files.hash` and reparse just X inline before answering (one adapter call, no daemon, no
  determinism violation); (2) **local type inference in the PHP adapter** — recover most HEURISTIC
  from the spec alone (`new X`, typed properties, promoted params, hints, return types, `@var`),
  then wire PHPStan as opt-in `semantic_types`.
- **Priority stack:** freshness → type inference → finish 031 → vendor stub index → replace/insert
  editing wrappers (refuse rename until type inference lands) → framework indirection as data →
  configurable extensions + encoding hardening.
- **Measurement gap:** no precision/recall harness — build a hand-labelled ground-truth set and
  differential testing vs Serena/phpactor.
- **Sample matrix gap:** all modern namespaced PHP; add WordPress/Drupal/ZF1/CodeIgniter + a real
  windows-latest CI job.
- **Honest counterargument:** adding editing + type inference makes this a language server; a better
  PHP backend for Serena might get further. Answer it in §19, don't ignore it.

**Assessment (repo-verified):**
- Core thesis (freshness + type inference are the real gaps) is right. §1 wording confirmed as the
  blocker: "Complement Serena, not duplicate it" (`PLAN.md:27`), "No rename/refactor/edit"
  (`PLAN.md:31`), "No type inference in the core" (`PLAN.md:32`).
- `semantic_types` flag exists (`contract.py:119`), PHP adapter emits empty capabilities
  (`adapters/php/index.php:28`), PHPStan already a dev-dep (`adapters/php/composer.json:18`) — the
  "use the existing extension point" argument is valid.
- No precision/recall harness confirmed (`tests/test_cross_repo_validation.py` is smoke-only);
  sample matrix is laravel/symfony/brick-math, no public procedural/legacy.
- **Corrections:** (1) **031 is DONE** (`BACKLOG.md:37`), not in flight — it's a differentiator you
  already have; every round mis-states this. (2) **Freshness is PARTIAL, not absent** — `read_symbol`
  already hash-checks but returns `stale:true` and punts to rebuild instead of reparsing inline
  (`read_symbol.py:50-61`); other tools don't check at all. (3) **`.php` is NOT hardcoded** — core
  maps extensions from the adapter handshake (`indexer.py:247`); only encoding-hardening and
  announcing `.phtml/.module/.inc` remain.

---

## Convergence across all three rounds (for §19 / BACKLOG)

The same small set of work recurs, re-sequenced by round 3's agent-consumer framing:

1. **License line** — one file; unblocks all adoption. (R2)
2. **Reason codes + `total_count`** on `find_*`/`search` — empty ≠ unknown. (R3)
3. **Tokens-to-answer benchmark** vs grep+Read — the falsifiable thesis; do before proving any
   accuracy change. (R1 metric, corrected by R3)
4. **Read-through freshness + Claude Code Edit/Write hook.** (R1 + R3)
5. **031** — already done; next: **tool consolidation (hold) + compound responses (take).** (R3)
6. **`explain_path`.** (R3)
7. **Vendor stub index → framework indirection as data** (facade→concrete, string-callback→CALLS,
   container aliases), as a rules file outside `adapters/` to keep R2.2 clean. (R1 + R2)

Deferred/dropped: symbolic editing (cede to native `Edit`, amend §1); type inference (below
response-shape work now); TS/JS 019/020/021 (finish the agent-PHP loop first — a §19 decision, not a
silent drop).
