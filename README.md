# code-atlas

**An evidence layer for AI coding agents.** Local-first MCP server that indexes your codebase into a
symbol graph, then answers *resolved relationship* questions — who calls this, what implements that,
what breaks if I change this file — with every answer carrying its own confidence tier, its own
truncation, and its own reason for being empty.

The same graph also renders **what the code actually is** — layers, modules, hubs, entry points,
flow — as a committable map, so a human can see where an agent's work actually went and show the
state of the project to someone else. Two pillars, one graph, stated authoritatively in
[`docs/PLAN.md`](docs/PLAN.md) §1.

Language-agnostic core with per-language adapters. **PHP today**; TypeScript/JavaScript, Python and
C#/.NET are next.

> Status: **shipped and in daily use — 20 tools.** The PHP path is feature-complete: index → search /
> read / outline → callers / refs / impls → impact → incremental (`git diff`) → reachability /
> orphans → shortest path, plus read-through freshness reparse. The **onboarding layer has shipped
> too** (`architecture_overview`, `guided_tour`, `generate_onboarding`) and emits a committable
> system map. See [`docs/PLAN.md`](docs/PLAN.md) for design and milestones,
> [`docs/BACKLOG.md`](docs/BACKLOG.md) for what is open.

## The problem it solves

An agent asks *"who calls `save()`?"*. `grep` returns every line containing the string — across every
class that happens to declare one, with no way to tell a resolved call from a coincidence. The agent
reads them all to find out. **That reading is the cost**, and it is paid in context, not in seconds.

code-atlas parses each language with its **best** parser into a **SQLite symbol graph**, resolves
cross-file edges once at index time, and serves the answer as rows: callers, implementations, blast
radius, reachability, the path between two symbols.

## Measured, not asserted

Every number here is reproducible from a runbook in this repo.

| What | Result | Where |
|---|---|---|
| Tokens to reach a resolved answer, vs grep-and-read | **~69× cheaper** across the whole question set on pinned public PHP repos (laravel / symfony / brick); **95–114×** on the relation queries alone | [`tokens-to-answer.md`](docs/runbooks/tokens-to-answer.md) |
| The onboarding layer's own cost gate | **cheaper for lookups** (12/12 correct, recall 1.0) and **wrong for reading order** (1 of 5 on a canonical repo) | [`121_onboarding-question-class.md`](docs/benchmarks/121_onboarding-question-class.md) |
| Cost of the *n*-th parallel agent | **~70 MB PSS**; the 925 MB index costs **0 MB** (page-cached, never mmapped) | [`parallel-agents.md`](docs/runbooks/parallel-agents.md) |
| Five agents vs one | **4.3× throughput**, 1.3 % of RAM, zero `SQLITE_BUSY` reaching a caller | same |
| No-op rebuild after 080 | **56.1 s → 2.113 s (26×)**, two no-ops byte-identical | §19 |
| Answer correctness, blind field round 5 | **8 of 8 checked claims exact, zero false statements** | §19 |

The last row is the one the design optimises for. Every failure that round was *silence or ambiguity*
— never a wrong answer.

## Who this is for

- a large PHP codebase (>10k files) you did not write
- an AI agent doing the reading, not a human in an IDE
- you need the answer to be checkable, not plausible

A reader who fails all three should be able to leave in ten seconds. That is a feature: a wrong
install is a bad first impression you never get to correct.

## Answers that say what they are not telling you

A silently partial answer is worse than no answer, so the payload carries its own limits:
`total_count` (the true size, not the page), `truncated`, `limit_capped_to`, `reason` (`no_such_symbol`
· `name_not_qualified` · `not_indexed` · `relationship_not_modelled` · `capability_not_configured`),
`resolved_qname`, `index_root`, and `confidence_tier` on every edge — `RESOLVED`, `HEURISTIC` or
`DYNAMIC`, never a guess linked as a fact.

Pass `sign: true` and four tools add a one-line `claim` you can paste into a PR body — a claim a text
search cannot make, in a form a reviewer can re-run.

## What it is not

- **Not a faster `grep`.** Broad `grep` over a 19k-file tree runs in under nine seconds. If you want
  faster text search, you do not need this. See *Founding premise, refuted* below.
- **Not a language server.** code-atlas is the indexed search/impact layer; an LSP stays for precise
  nav and edit.
- **Not an editor.** It returns exact line ranges; it never mutates code.
- **Not multi-language yet.** Only the PHP adapter exists. A TypeScript, Python or C# project will
  not index today.

## Founding premise, refuted

This project began on the claim that native tools and `grep` are weak at name-resolved *search* on
large repos. On **2026-08-08** that was measured against a ~19k-file private monorepo and **it did not
hold** — native tools answered five real symptom-first questions correctly, and broad `grep` ran under
nine seconds at every scope.

The claim is kept in [`docs/PLAN.md`](docs/PLAN.md) §19 **struck, not deleted**, because every decision
in this repo was taken under it. What replaced it is narrower and is what the table above measures:
**the index sells resolved relationships and token cost, not search speed.**

That refutation is the reason for the payload discipline in the section above. §19 has the full
result, including what it got wrong.

## How it works

```
MCP client ──stdio──▶ core (Python / FastMCP) ──JSONL contract──▶ language adapter (e.g. PHP sidecar)
                          │
                          ▼
                   SQLite  .code-atlas/graph.db   (nodes · edges · files · fts5 · meta)
```

The core is language-agnostic — no per-language branches, CI-gated. Adapters parse files and emit a
common `{nodes, edges}` vocabulary; the core stores them, resolves cross-file edges, and exposes MCP
tools. Everything runs offline against local SQLite; incremental updates via `git diff`. Requires
**SQLite ≥ 3.25**.

On top of that graph sits the **onboarding layer**: deterministic enrichment feeding three tools and
one committable system map. The LLM is optional, writes prose only, lives outside the core in
`onboarding_llm/`, and with it switched off the map still renders complete.

## Install

You need **Python ≥ 3.12**, and — to index PHP (the only adapter so far) — a **PHP CLI ≥ 8.1** and
**[Composer](https://getcomposer.org/)** on your PATH.

One command sets everything up and writes a ready-to-use `.mcp.json` into your project:

```bash
git clone https://github.com/cuongdinhngo/code-atlas.git
cd code-atlas
python scripts/setup.py /abs/path/to/your-project
```

That installs the core, builds the PHP adapter, and writes `<your-project>/.mcp.json` with the correct
interpreter, adapter path, and working directory filled in — the three things that are easy to get
wrong by hand. Run it with no path to print the snippet instead of writing it, or `--no-adapter` to
skip PHP. If PHP or Composer is missing it tells you and continues; rerun once they're installed.

Then **reload your MCP client** (in Claude Code: restart, or re-approve the project's `.mcp.json`) and
the `code-atlas` tools appear.

Onboarding a **large legacy repo** — where the first build takes minutes, `.gitignore` negations can
smuggle vendored trees into the index, and one knob decides whether the database is 1 GB or 2 GB — is
covered step by step in [`docs/runbooks/onboarding-a-repo.md`](docs/runbooks/onboarding-a-repo.md).

<details>
<summary>Prefer to wire it up by hand?</summary>

`pip install -e .`, then `composer install --working-dir=adapters/php`, then point an `.mcp.json` at
your repo — `command` = `code-atlas` (or `python -m code_atlas.main`), `cwd` = the repo to index,
`env.CA_PHP_CMD` = `php /abs/path/to/code-atlas/adapters/php/index.php --server`. The adapter lives in
this checkout, so `CA_PHP_CMD` must be an **absolute** path. Docker instead of host PHP:
`docker compose exec -T php php /app/adapters/php/index.php --server`. Details in
[`adapters/php/README.md`](adapters/php/README.md).
</details>

### Ship the server in a container

To run the whole MCP server (core + PHP adapter) from a container instead of installing Python and PHP
on the host, build the runtime image and point your client at `docker run`:

```bash
docker build -f docker/Dockerfile.runtime -t code-atlas-server .
```

```jsonc
// .mcp.json — the server indexes the mounted repo and writes .code-atlas/graph.db into it
{
  "mcpServers": {
    "code-atlas": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
               "-v", "/abs/path/to/your-project:/workspace",
               "code-atlas-server"]
    }
  }
}
```

The server talks MCP over stdio, so `-i` (stdin attached) is required; it indexes `/workspace`, so mount
the repo there. Add `"--user", "1000:1000"` (your uid:gid) to the args to keep `.code-atlas/` writes
owned by you rather than root. The image bundles the pinned PHP adapter, so no host PHP/Composer is
needed. See [`docker/`](docker/).

## Usage

Drive everything through the MCP tools:

1. **`get_index_status`** — call first. The cheap (~100-token) entry point: is there an index, how
   stale is it, what to call next. A fresh project reports `indexed: false`.
2. **`build_or_update_index`** — builds the SQLite graph under `.code-atlas/graph.db`. Later,
   `full=false` does an incremental `git diff` update when it can, else a full rebuild.
   The index is a derived cache with no migration runner: after upgrading code-atlas across a
   `schema_version` change, an index **older** than the server is deleted and rebuilt in-band. An
   index **newer** than the server is refused untouched — that means the running server predates the
   upgrade, so restart the MCP client rather than rebuild (see `direction` in the payload).
3. **Query** — `search_symbol`, `file_outline`, `read_symbol`, `find_callers`, `find_references`,
   `find_implementations`, `find_view_data`, `include_graph`, `impact`, `subtree_dependencies`,
   `reachable_from`,
   `find_orphans`, `explain_path`.
4. **Understand a repo you did not write** — `architecture_overview` (layers and their crossings),
   `guided_tour` (a dependency-ordered reading list), `generate_onboarding` (write the committable
   system map). These answer a once-per-repo question, not a once-per-ticket one. See
   [Tools](#tools).

Every tool takes `detail_level` — `minimal` for the payload alone; `standard` (default) may add
provenance (`db_path` on `get_index_status` / build reports only after 061). Every answer also carries
`index_root` (the configured source tree — task 071) so a worktree agent can spot a mismatched server.

> **Language scope today:** only the **PHP** adapter exists. A TypeScript, Python, or C# project won't
> index yet — those are planned (see [Roadmap](#roadmap)).

## Tools

| Tool | Returns |
|---|---|
| `get_index_status` | index stats, last indexed commit, staleness, next-step suggestions (call first). `standard` also names the running build — `server_version` and `server_build`, with `+dirty` when the checkout has uncommitted changes — so a report can say which code answered it (125) |
| `build_or_update_index` | `wrote` counts + timing; `standard` also `graph` totals; `full=false` incremental when possible, else full |
| `search_symbol` | ranked symbols (`qname`, kind, `file:line`) |
| `file_outline` | symbols + line ranges, no bodies |
| `read_symbol` | source of just one class/method + docblock |
| `find_callers` / `find_references` / `find_implementations` | resolved relationships + confidence tier; `find_references` on a `Foo::class` mention is `DYNAMIC` and sets `authoritative: false` when every hit is (094); `find_callers` can also filter call sites by argument shape (`arg_position` + `arg_is`) |
| `find_view_data` | view-scope keys a handler publishes (`PROVIDES_VIEW_DATA` — needs `CA_INDIRECTION_RULES` `view_data` setters) |
| `include_graph` | `include`/`require` neighbors (`imports` / `imported_by` / `both`) |
| `impact` | bounded blast radius of a change (paths/qnames), depth-limited with decay |
| `subtree_dependencies` | tree-to-tree crossing with duplicate-declaration attribution — attributable vs unattributable always paired; dynamic alias bridges surfaced |
| `reachable_from` | forward reachability from configured entry points |
| `find_orphans` | unreachable / zero-inbound symbols (dead-code candidates); pages with `limit`/`offset`, and its walk is bounded by its **own** `CA_ORPHANS_MAX_NODES` rather than the impact budget. `walk_truncated` marks an answer where the walk stopped early, so the orphan count is an over-estimate (124) |
| `explain_path` | shortest control-flow path between two symbols |
| `architecture_overview` | this repo's layers, their degrees and the crossings between them — plus the zero-inbound split, the capability table and the mirror panel ([detail](#architecture_overview--layers-crossings-and-the-populations-behind-a-zero)) (onboarding) |
| `guided_tour` | a dependency-ordered reading list of files, cycle-safe and budget-bounded ([detail](#guided_tour--a-reading-order-that-expands)) (onboarding) |
| `generate_onboarding` | writes the committable markdown and the self-contained `index.html` **system map** under `docs/onboarding/` ([detail](#generate_onboarding--the-committable-system-map)) (onboarding) |
| `check_architecture_rules` | confirmed vs candidate violations of declarative path-set dependency rules (`CA_ARCHITECTURE_RULES`) |
| `diff_architecture` | architectural drift between two onboarding dataset / manifest snapshots |

### `architecture_overview` — layers, crossings, and the populations behind a zero

- `summary.reachability` splits the zero-inbound modules into their real populations — web surface,
  vendored, tests, no-inbound-but-outbound (**not** dead code), no-edge-either-way (a list to check,
  not a conclusion) — with the raw total kept beside them.
- `summary.business_modules` is the capability table — which file to open for a named screen — with
  its own coverage beside it, the container level derived from the tree rather than named, and a
  role-organised container refused with its reason.
- `summary.mirrors` names sibling subtrees that duplicate each other's paths — discovered, not
  configured — with a counterpart lookup whose negative answer marks divergence, and the standing
  caveat that it compares paths, not bytes.
- Each bucket also reports **which signal produced it** — `signals: {declared, vocabulary,
  structure}` — and every declared glob reports what it `files_matched` beside what it
  `zero_inbound_claimed`, so a stale declaration is legible instead of invisible (119).
- Every list is capped at `CA_MAX_RESULTS`; `verbose` pages the per-module rows with `offset`.

### `guided_tour` — a reading order that expands

- Dependency-ordered list of files, cycle-safe via SCC condensation.
- Roots prefer files that lead somewhere, then reading-seed layer rank (HTTP before Config), and are
  capped at a quarter of the node budget, so the walk expands
  instead of spending the budget on isolated files.
- A component no entry point reaches is re-seeded, not dropped.
- The walk is bounded by `CA_IMPACT_MAX_NODES`; the page is capped at `CA_MAX_RESULTS` with `offset`.

### `generate_onboarding` — the committable system map

- Writes markdown (overview · tour · per-module) plus `manifest.json` and a self-contained
  `index.html` under `docs/onboarding/` — offline, theme-aware, repo text escaped so a path cannot
  inject markup, with a `<noscript>` fallback. `overview.md` includes a mermaid layer flowchart
  (GitHub/VS Code render it; the HTML map stays fetch-free and does not bundle mermaid).
- The map renders the onboarding dataset **alone**: sitemap treemap with drill-down, layer table with
  its node-kind composition, the full layer×layer dependency matrix with nothing cut, hubs, the
  capability table, the zero-inbound split, the mirror panel, a search palette with counterpart
  lookup, and a provenance section naming which parts are derived.
- Every figure is interpolated, so the same dataset always renders identical bytes, and a section
  that is empty or capped says so instead of looking exhaustive.
- The search palette ranks before it truncates, keeps one row for every top-level subtree the full
  match set spans, and names those subtrees when the page is cut — the artifact-layer form of
  `result_subtrees`. Every caveat the dataset carries is asserted to be *rendered*, by a guard that
  derives the caveat set from the dataset rather than listing it.
- It removes only the pages its own last manifest recorded, and refuses a tree it did not write.
- A module with no edge either way and no summary gets **no page** (one would only repeat its path) —
  the overview counts them, the manifest names them with `page: null`, `standard` reports
  `isolated_modules`, and a page whose neighbours the budget cut is kept and says so.
- Regenerable cache under `.code-atlas/onboarding/`; tour and pages bounded by `CA_IMPACT_MAX_NODES`.

### Reading an answer — every payload says what it is not telling you

An answer that is silently partial is worse than no answer, so the payload carries its own limits.
Nine list-returning tools take **`limit` / `offset`** and page in a stable order, and every one of
them reports:

- **`total_count`** — the true size of the answer, never the length of the page you were handed.
- **`truncated`** — whether *this page* is the whole set. It describes the page alone, so a pager
  terminates; a walk that stopped on its own node budget says so separately in `walk_truncated`.
- **`limit_capped_to`** — present only when your `limit` exceeded `CA_MAX_RESULTS`. The server
  honoured fewer rows than you asked for, and says so rather than letting `truncated` imply it.
- **`reason`** — why an answer is empty. `no_such_symbol`, `name_not_qualified` (with
  `candidate_count`), `not_indexed` (the file is on disk but untracked), `relationship_not_modelled`,
  `capability_not_configured`. **An empty result is never an unexplained zero**, and where a better
  route exists the payload names a real, callable tool in `try_instead`.
- **`resolved_qname`** — when you typed `Foo\Bar` and the index stores `\Foo\Bar`, the tool answers
  about the stored name and tells you which one it used.

Two more fire when a page could mislead: a truncated `file_outline` adds **`result_kinds`** (every
kind in the file with its count, so a capped symbol map cannot read as complete), and a truncated
`find_callers` page spanning several top-level subtrees adds **`result_subtrees`**, because page 1 of
a store-ordered answer clusters into whichever subtree sorts first.

Every answer also carries **`index_root`** — the source tree it describes — so an agent in a worktree
can spot a server pointed at the main checkout. Full field reference:
[`docs/CONVENTION.md`](docs/CONVENTION.md) §6.

### Signing a claim — `sign: true` (opt-in, off by default)

Four tools answer with an **attestation** rather than a list: a modelled zero, a counted set at a
named tier, the revision an answer describes. Those are claims a text search cannot make — and a
claim that never reaches the artifact where it is made has, in practice, not been produced.

Pass `sign: true` to `impact`, `find_callers`, `find_references` or `get_index_status` and the
payload gains one extra key, `claim`: a single `key=value` line a human or an agent can paste
straight into a PR body, a review comment or a commit message.

A real example. This prose shipped in a PR:

> No product code, no `src/` consumer.

A reader cannot check it. The payload that could have signed it was already on screen:

```
code-atlas/1 tool=impact subject="app/Http/A.php,app/B.php,+2" question=blast-radius answer=25 tier=RESOLVED seeds=4 seeds_dropped=0 frontier_skipped_non_resolved=0 rev=a1b2c3d ref=main index=current
```

`answer=25 seeds=4` says twenty-one things depend on the four changed paths; `answer=4 seeds=4`
would be the **modelled zero** — the blast radius is the seeds themselves. `seeds_dropped=0` is what
separates that zero from a query that found nothing because it asked wrong: every subject you named
that produced no seed is counted there, so a non-zero value means the question, not the codebase,
came up empty. An `impact` answer that lost *every* subject also carries `reason` (and, where the
classifier has them, `candidate_count` / `try_instead`) rather than an unexplained empty result.

**The line degrades honestly.** Every caveat owns its own key, so a weakening answer cannot quietly
drop it: `tier=` always names the **weakest** tier present, `index=behind` (with `dirty_indexed=`)
says HEAD has moved past the tree the answer describes, `authoritative=false` marks an all-`DYNAMIC`
candidate list, `truncated=true` marks a page rather than a set, and `reason=` rides along whenever
the answer is not a plain `ok`.

**When no line is emitted.** An answer over an unbuilt index, and an `impact` answer where no seed
resolved, carry **no** `claim` — a question nothing answered would be signed `answer=0` for a subject
the index never held, and a claim that cannot be re-run is decoration. The payload still says so in
its own fields: `seeds_dropped` names the loss and `reason` names its kind.

**Cost.** Off by default and byte-identical to today when off. When on, the line costs one extra
git HEAD read and, measured on a one-symbol answer, **+51 tokens** on `impact` and **+46** on
`find_callers` (`code_atlas/tokens.py` proxy). The signed payload is pinned under a 60-token delta.

#### Answers deliberately left unsigned

A list of rows is not a claim. Signing one would produce a quotable artifact that asserts nothing —
worse than none. Each of these would have lost a caveat that no one-line form can carry:

| Tool | The caveat a one-line claim would have lost |
|---|---|
| `build_or_update_index` | it reports work done, not a state of the world — the counts describe a run, and a run is not a claim about the tree |
| `search_symbol` | ranking. A count of matches says nothing about whether the right one is on the page |
| `file_outline` | structure. "17 symbols" is not the claim a reader wants; the shape is |
| `read_symbol` | the body IS the answer — a line summarising source is a paraphrase of the thing itself |
| `find_implementations` | interface scope: a count is meaningless without which interface, and stubs vs real implementers differ |
| `find_view_data` | `capability_not_configured` — a zero here is usually an inert tool, not a modelled zero (069) |
| `include_graph` | direction. `imports` and `imported_by` are different claims and a single count conflates them |
| `subtree_dependencies` | attributable vs unattributable is a pair — a one-line blocker count is precisely the naive error this tool exists to prevent (120) |
| `reachable_from` | the entry-point set it was configured with — the claim is only as good as `CA_ENTRY_POINTS`, which the line cannot carry |
| `find_orphans` | "unreachable" is a candidate, not a verdict — dynamic dispatch and framework wiring are outside the graph |
| `explain_path` | a path is a sequence; its length without its hops is not checkable |
| `architecture_overview` | a layer split is a shape, and a count of layers asserts nothing a reader could check; the method that derived it is the caveat, and it already rides the payload |
| `guided_tour` | a reading order is a sequence; its length without the stops and their rationales is not checkable |
| `generate_onboarding` | it reports files written, not a state of the world — a count of pages is not the docs themselves |
| `check_architecture_rules` | confirmed vs candidate is a pair — a one-line violation count would erase the HEURISTIC tier partition (138) |
| `diff_architecture` | a drift report is a shape across sections — a one-line change count erases which revision and which field moved (139) |

## Sweeps — `search_symbol` takes a list of subjects (task 101)

*"Are any of these ten names already taken?"* is one question. Until 101 it was **ten calls**, so a
field session framed it as a sweep and reached for `grep -rn` instead — one call for all ten, over
two directories, where the index would have searched the whole tree. The tool was known and the cost
was not the problem: **ten calls is the wrong granularity for one question.**

```jsonc
search_symbol(queries: ["getState", "setState", "flushCache", …], kind: "Function")
→ { "indexed": true, "subject_count": 10, "index_root": "…",
    "subjects": [                                  // caller's order, never merged or deduped
      {"query": "getState",  "results": [{"qname": "\\Lib\\getState", …}], "reason": "ok",         "total_count": 1, "truncated": false},
      {"query": "setState",  "results": [],                                "reason": "no_matches", "total_count": 0, "truncated": false}
    ] }
```

Answer *i* answers subject *i*, so one miss never colours the other nine, and each entry carries its
own `reason` (and its own `try_instead`, when it has one). At most `CA_MAX_SUBJECTS` (default **25**)
subjects are accepted; the rest come back named in `subjects_dropped` beside `subjects_capped_to` —
a sweep exists to be complete, so a silent truncation is worse than ten honest calls (066). Passing
`query` and `queries` together raises. A `query=`-only call is byte-identical to before.

One caveat the shape imposes: a sweep shares **one** read-through repair budget across every subject,
because scaling it per subject is the unbounded fan-out the bound exists to prevent. A subject whose
file drifted may therefore answer `index_stale` where a single call would have repaired it — the
answer says so rather than reporting a quieter `no_matches`.

#### Tools that take one subject at a time

Batching is not free: it is only right where the question is genuinely list-shaped. One batched tool
first, proven in the field, before the pattern spreads (R1.2). Each of these keeps a single subject
for a reason:

| Tool | Why one subject |
|---|---|
| `get_index_status` | there is one index; a list of subjects has no meaning for a server-state answer |
| `build_or_update_index` | a build is one write against one tree — R4.3's single writer, not a fan-out |
| `file_outline` | already plural in its answer: one path returns every symbol in it |
| `read_symbol` | a batched body read is just a file read, and bodies are the one thing this server does not return in bulk |
| `find_callers` | the answer is a bounded traversal per subject; N subjects is N traversals, and the honest form of that is N calls the caller can page independently |
| `find_references` | same traversal cost as `find_callers`, plus `ambiguous_definitions` is a per-subject warning a merged page would bury (070) |
| `find_implementations` | subtypes of a list of interfaces is a different question — a union, which is exactly the merge 070 forbids |
| `find_view_data` | its zero is usually `capability_not_configured`, an inert-tool fact about the call, not about a subject (069) |
| `include_graph` | its subject is a path and its answer is already a graph; batching graphs means merging them |
| `impact` | it already takes `paths` and `qnames` — and merges them into one radius on purpose, because a blast radius is a union by definition (see ticket 102 for the cost of that merge) |
| `subtree_dependencies` | its subject is a directory prefix — the answer is a repo-wide report, not a per-name lookup |
| `reachable_from` | its subject is the configured entry-point set, not a caller-supplied name |
| `find_orphans` | the complement of the whole graph — there is no subject to list |
| `explain_path` | its subject is already a pair; a list of pairs is a query language, which 101 deliberately is not |
| `architecture_overview` | its subject is the whole index — there is one repo to lay out, and a list of subjects has no meaning for a repo-wide shape |
| `guided_tour` | its subject is the whole index — there is one reading order, and a list of subjects has no meaning for a repo-wide walk |
| `generate_onboarding` | a write is one artifact against one tree — R4.3's single writer, not a fan-out |
| `check_architecture_rules` | its subject is the configured rule set — a list of rule ids is filtering, not a batch of independent questions |
| `diff_architecture` | its subject is already a pair of snapshots — a list of pairs is a query language, which 101 deliberately is not |

## Operator prompts (human-invoked — not part of the agent tool surface)

These MCP prompts are **operator recipes a human invokes**; an agent's client exposes only the tools
above to the model, so a model never sees a prompt (task 081). Agent routing lives in the tool
descriptions themselves (each names the question it answers — task 069), not here.
The blind recognition probe that scores whether those descriptions route — and that separates
name-only answers from description-backed ones — is
[`docs/runbooks/tool-recognition-probe.md`](docs/runbooks/tool-recognition-probe.md) (081, 097).

| Prompt | Recipe |
|---|---|
| `explore_area` | status → search/outline → read only what's needed |
| `find_usages` | status → find_references / find_callers / find_implementations → read to confirm |
| `impact_of_change` | status → impact on the changed paths/qnames → read only the blast-radius surface |
| `which_tool` | a recognition map: which tool answers a given question, across all 20 tools |

## Hooks (opt-in)

code-atlas answers when asked. Two hooks cover the moments an agent was never going to ask — an edit
that drifts the index, and a `Read` that could have carried one line of context. Both are opt-in, and
both are offered rather than installed.

### Keep the index fresh while Claude edits (opt-in)

Task 035 already reparses drifted files at query time. For eager updates after Claude Code
`Edit`/`Write` on PHP files, install the PostToolUse hook under
[`contrib/claude-code/`](contrib/claude-code/) (`code-atlas-poke` console script + `"async": true`);
opt-in git refresh after pull/checkout via [`contrib/git/`](contrib/git/) (`code-atlas-refresh`,
background — never auto-installed into `.git/hooks`).
Safe no-op when `.code-atlas/graph.db` is missing; does not stall the tool round-trip.

### The read-time signal — a line that rides along with a file you are already opening (opt-in)

Field evidence (task [099](docs/tasks/099_write-time-signal-seam.md)): the three most consequential
decisions an agent made *without* calling code-atlas all wanted **one line at the moment of a `Read`
or a `Write`** — and none of them wanted a tool call. An MCP tool answers when asked; this fires
when the agent was never going to ask, so it is a **hook**, not a tool.

`code-atlas-signal` prints at most one line (~150 tokens, hard cap) and exits 0:

- **`Read`** an indexed file with ≥ 5 symbols → `code-atlas: <path> defines N symbols — name:line, …`
- **`Write`** creating a new path under the indexed tree → `code-atlas: <path> is untracked — symbol
  queries answer `not_indexed` until it is committed and reindexed`

It never builds, never reparses and never takes the write lock; a file that has drifted since the
last index still answers, with `(index may be behind)` appended.

**Wire `Read` at `PostToolUse` and `Write` at `PreToolUse`.** The create-vs-edit test is whether the
path exists yet, so a `PostToolUse` `Write` is silent by construction — correct for an edit, useless
for a create.

**It stays silent** on any other tool (so browser-probe output and CI shell results are untouched),
on writes to files that already exist, on files below the symbol floor, and when there is no index.
That silence rule is the design, not a default: a line that fires on every read is chrome within
three invocations.

**code-atlas does not wire itself into anyone's editor.** As with the poke and refresh hooks, the
command is offered and the host decides — there is no installer and nothing is written to your
settings.

## Configuration

Every knob resolves **environment → project file → default**. The project file is
`.code-atlas.toml` at the repo root (optional, meant to be committed); its keys are the environment
names lower-cased without the `CA_` prefix. A malformed value or an unknown key is a loud error, never
a silent fallback.

| Environment | `.code-atlas.toml` | Default | Meaning |
|---|---|---|---|
| `CA_DB_PATH` | `db_path` | `.code-atlas/graph.db` | index location (relative to the repo root) |
| `CA_WORKERS` | `workers` | `max(1, min(cpu-2, 8))` | adapter processes during a build |
| `CA_ADAPTER_TIMEOUT` | `adapter_timeout` | `30` | seconds an adapter may stay silent before a build kills it |
| `CA_MAX_RESULTS` | `max_results` | `50` | result cap for search/nav tools — **and** the resolver's per-call-site candidate fan-out, which sets index size; a request above the cap is honoured to the cap and says so in `limit_capped_to` |
| `CA_MAX_SUBJECTS` | `max_subjects` | `25` | subjects one `search_symbol` sweep may take; a refused subject is named in `subjects_dropped`, never dropped silently |
| `CA_IMPACT_DEPTH` | `impact_depth` | `2` | hops the impact engine traverses (with default decay/floor, depths above ~8 are a no-op) |
| `CA_IMPACT_MAX_NODES` | `impact_max_nodes` | `500` | node budget for one impact query (seeds kept preferentially when over budget) |
| `CA_ORPHANS_MAX_NODES` | `orphans_max_nodes` | `500` | node budget for the reachability walk inside `find_orphans` only — deliberately **not** the impact knob, so tuning one cannot change which orphans exist |
| `CA_PATH_INDEX_MAX` | `path_index_max` | `20000` | path cap for the onboarding dataset's front-coded path index; when it trims, the dataset carries both the total and the shown count |
| `CA_ENTRY_POINTS` | `entry_points` | unset | file globs that seed reachability. **`reachable_from` and `find_orphans` need this** — unset, they report *no roots configured* rather than guessing |
| `CA_STUB_ROOTS` | `stub_roots` | unset | dependency roots (e.g. `vendor`) to index declarations-only, so third-party signatures resolve; hits carry `stub: true`. Costs one extra pass |
| `CA_INDIRECTION_RULES` | `indirection_rules` | unset | JSON rule files mapping framework indirection to edges. **`find_view_data` needs this** — without `view_data` setters it answers `capability_not_configured`, not a zero |
| `CA_ARCHITECTURE_RULES` | `architecture_rules` | unset | JSON rule files of path-set dependency constraints. **`check_architecture_rules` needs this** — unset → `capability_not_configured` |
| `CA_TOOLS` | `tools` | all tools | comma-separated tool allow-list |
| `CA_HOST_ROOT` | `host_root` | unset | absolute-path rewrite only (pair with `CA_CONTAINER_ROOT`; unused by the relative-path build) |
| `CA_CONTAINER_ROOT` | `container_root` | unset | absolute-path rewrite only (pair with `CA_HOST_ROOT`) |
| `CA_<LANG>_CMD` | `[adapter_cmd].<lang>` | — | the **complete argv** that launches one adapter in server mode |

```toml
# .code-atlas.toml
workers = 4
max_results = 50
tools = ["get_index_status", "build_or_update_index"]   # only names the server serves; a typo is a loud error
# Optional: only needed if something passes absolute host paths to the adapter.
# host_root = "/home/you/project"
# container_root = "/app"

[adapter_cmd]
php = "docker compose exec -T php php /app/adapters/php/index.php --server"
# or, where quoting bites (Windows paths), one word per entry:
# php = ["C:\\php\\php.exe", "adapters/php/index.php", "--server"]
```

The adapter command is the **whole** command: the core appends nothing to it, not even `--server`, so
it never has to know where a language's adapter lives. An adapter announces its own name, the file
suffixes it owns, and its capabilities on the first line it writes — that handshake is what routes
files to it.

Files are skipped using built-in patterns (`vendor/ var/ uploads/ log/ node_modules/ .git/
*.blade.*`), then `.gitignore`, then an optional `.codeatlasignore` — later rules win, so
`.codeatlasignore` can re-include what an earlier source excluded. A path below an excluded
*directory* stays excluded, which is what lets the walk prune a subtree.

### Optional LLM enrichment (opt-in, off by default)

The onboarding tools are fully deterministic by default — no LLM, no network. An opt-in package,
[`onboarding_llm/`](onboarding_llm/README.md), plugs into three seams: it can replace the one-line
module summary (085), rename weak architectural layers — the generic `source`/`sink`/`mixed` bands
084 falls back to on flat namespaces (091) — and write the map's prose (117): each layer's
responsibility line, each tour step's narrative, and the wording of the headline facts.

**Structure is never the seam's to change.** Every count, ranking, grouping and the set of headline
facts is derived before a model is consulted, so enrichment rewords the map and nothing more; a
failure or a filler answer simply leaves the deterministic sentence in place, and spend is capped at
33 calls per build whatever the repo's size.

The **core never imports it**: you install the `llm` extra, set `CA_ONBOARDING_SUMMARIZER=llm`,
`CA_ONBOARDING_LAYER_REFINER=llm` and/or `CA_ONBOARDING_PROSE=llm`, and run `code-atlas-llm` instead
of `code-atlas`. All three are memoised in content-hash caches so runs replay and diffs stay stable.
These are `onboarding_llm` knobs, not core config — the full table is in that package's README.

## Testing

`scripts/gate.sh` runs the whole gate in one step — entry points, `ruff`, `mypy`, `pytest`, the
tokens-to-answer benchmark, `composer validate`, `php -l`, phpstan at level max, and the four
rulebook grep-gates — in the same order [`ci.yml`](.github/workflows/ci.yml) runs them. It exits
non-zero if a check **failed or was skipped**, because a gate that quietly shrinks to whatever the
host can run has not verified anything. Add `--fast` to skip the two slow checks.

The test command on its own is `pytest`. The full suite needs a POSIX host (the index lock uses `fcntl`) and the
PHP adapter (`php` on `PATH` + `composer install` in `adapters/php`); without those, tests that need
them **skip or fail to collect** — so a partial local run is not the whole suite.

To run **everything** off any host (Windows/macOS included), use the Linux test image — it mirrors
CI's `ruff · mypy · pytest` gate with the adapter's composer deps baked in:

```sh
scripts/docker-test.sh                       # ruff + mypy + pytest -q (the full suite)
scripts/docker-test.sh pytest -q -k php      # just the PHP-adapter integration tests
# or, via compose:
docker compose -f docker/compose.yaml run --rm --build test
```

The image (`docker/Dockerfile`) copies the source in at build time, so re-run after editing to test
the new code (Docker's layer cache keeps dependency installs warm). See [`docker/`](docker/).

## Language support

| Language | Parser | Status |
|---|---|---|
| PHP (8.5 grammar, 8.1+ runtime) | nikic/php-parser | Available (first) — see [`adapters/php/`](adapters/php/) |
| TypeScript / JavaScript | TypeScript Compiler API | Planned |
| Python | `ast` + jedi | Planned |
| C# / .NET | Roslyn | Planned |

## Roadmap

- **Phase 1 — Core + PHP:** full build → resolver → **search/read/outline (first daily release)** →
  scale → incremental → impact.
- **Phase 3 — Onboarding: shipped** (ahead of language breadth — depth before breadth). `architecture_overview`,
  `guided_tour` and `generate_onboarding` emit a committable **system map** under `docs/onboarding/`:
  responsibility layers, dependency matrix, hubs, a business-module table, mirror-subtree lookup, a
  bounded tour, and the zero-inbound population split. Deterministic by default; LLM prose is opt-in.
- **Phase 2 — More languages: deferred, not cancelled.** TS/JS (hardens the contract), then Python,
  then C#/.NET — order unchanged; it waits until the PHP agent-loop is complete.

## Design principles

SOLID **at the boundaries** (the axis of change is *languages*, expressed through one versioned
contract) + **YAGNI** (one seam only until a second adapter exists) + **standard over sample** (adapters
encode the language spec/standards, never a specific repo's conventions). Details in the
[build plan](docs/PLAN.md). Cross-repo validation (opt-in / scheduled, not per-PR) lives in
[`docs/runbooks/cross-repo-validation.md`](docs/runbooks/cross-repo-validation.md).

## Documentation

Seven docs answer most questions. What every standing document is **and is not** — the full role
table, boundaries included — is [`docs/CONVENTION.md`](docs/CONVENTION.md) §8.1.

| Doc | Answers |
|---|---|
| [`docs/PLAN.md`](docs/PLAN.md) | the authoritative design — the contract, the schema, the resolver, every tool, and **§19**, the decision log: what was measured, what was refuted, and why the project is shaped this way |
| [`docs/BACKLOG.md`](docs/BACKLOG.md) | what is open and what landed |
| [`docs/TOKEN_LEDGER.md`](docs/TOKEN_LEDGER.md) | what each task cost — one spend row per ticket |
| [`docs/CONVENTION.md`](docs/CONVENTION.md) | naming, repo layout, the fixed contract vocabulary, and **§6** — the payload contract every tool answer obeys |
| [`docs/ENGINEERING_RULES.md`](docs/ENGINEERING_RULES.md) | the binding *how we build* rules (R1.1 …), several of them CI-gated |
| [`docs/LESSONS.md`](docs/LESSONS.md) | what shipping this taught us, per task — the evidence the rules were promoted from |
| [`docs/FEEDBACK.md`](docs/FEEDBACK.md) | external review rounds 1–4 (2026-08-04/05) and what each claim checked out as — a closed record; the field retros that replaced it are in PLAN §19 and [`runbooks/field-retro.md`](docs/runbooks/field-retro.md) |

**Runbooks** — operator protocols, each reproducible:
[onboarding a large legacy repo](docs/runbooks/onboarding-a-repo.md) ·
[tokens-to-answer](docs/runbooks/tokens-to-answer.md) (the value claim and how it is gated) ·
[parallel agents](docs/runbooks/parallel-agents.md) (measured memory and write contention) ·
[cross-repo validation](docs/runbooks/cross-repo-validation.md) ·
[field retro](docs/runbooks/field-retro.md) ·
[tool-recognition probe](docs/runbooks/tool-recognition-probe.md).

Phase 3's own breakdown, and the reviewed mockup the system map was built from, are under
[`docs/phase3-onboarding/`](docs/phase3-onboarding/). Contributing agents should start at
[`AGENTS.md`](AGENTS.md).

## License

MIT — see [`LICENSE`](LICENSE). © 2026 Cuong Ngo.
