# Tools — the full surface

> The agent-facing surface of code-atlas: all 24 tools, what each returns, which take a list of
> subjects and which do not, the operator prompts, and the opt-in hooks. The
> [README](../README.md) names the handful you call first; this is the reference. It is **not**
> the payload contract (→ [`CONVENTION.md`](CONVENTION.md) §6) and not design reasoning
> (→ [`design/`](design/)).

## Tools

| Tool | Returns |
|---|---|
| `get_index_status` | index stats, last indexed commit, staleness, next-step suggestions (call first). **Leads with a one-line `summary`** at every level — staleness, counts, built-on ref and the edge-health verdict lifted into one sentence from the fields below, so a caller reads the headline without reparsing the payload (316). With `entry_points` / `stub_roots` unset it also nominates candidate globs with `files_matched` and applies none — `entry_point_candidates` / `stub_root_candidates`, on an unbuilt index at any level and otherwise at `standard`, never on the cheap `minimal` path (268). `standard` also names the running build — `server_version` and `server_build`, with `+dirty` when the checkout has uncommitted changes — so a report can say [which code and which config answered it](design/payload.md#which-code-answered-and-which-config-tasks-170-175) (125/170/175); on a multi-language index `standard` also carries `edge_health_by_language` as the per-language verdict (`unlinked` / `by_tier` only — 261) beside the bounded `cross_language` crossing census (`linked` / `unlinked` / `by_tier`, no `pairs` — 243) and `capabilities_by_language` (231/244), and `verbose` replaces it with the full census including `pairs` (183); `verbose` also carries `fit_counts` — local per-tool ask tallies (task 260; definition in [design/fit.md](design/fit.md) — read that before quoting a number); `reset_fit_counts=true` clears them. `parse_failures` (standard+) is adapter parse inability — a floor, not a fatal surface (`parse_failures_note`; 280). On a `behind` index it names the routes rather than one verdict — `behind_serves` / `behind_refuses`, the `serve_behind_opt_in` that flips them, the `changed_indexed_between` pair it drifted across and, at `standard`, `changed_indexed_files` (274); while a build holds the lock it names `build_progress_route`, the one live phase no MCP tool can read (177/203) |
| `build_or_update_index` | `wrote` counts + timing; `standard` also `graph` totals; `full=false` incremental when possible, else full. An index one **vocabulary era** behind cannot be extended incrementally (030 AC1), and rebuilding it can outlast the call: `full=false` answers `mode: refused` · `reason: contract_rebuild_required` with the `code-atlas-build --full` route instead of starting it, and `allow_full_rebuild=true` runs it in-band anyway — and the same refusal shape now answers an explicit `full=true` on an index that already exists, because MCP cannot outlive its client and a timed-out "failed" does not stop the server-side build (291). The escalation is reported as `contract_change`, disjoint from 172's `scope_change`, so a caller can tell which one it hit (201). A build killed mid-write leaves a graph no incremental can repair — `last_commit` still names HEAD — so `staleness` reads `incomplete`, the next build escalates and reports `incomplete_index`, and `repair_incomplete=false` refuses instead for a caller that must not start a long build of its own (202). A **fourth** escalation is about cost rather than correctness: past `CA_FULL_BUILD_CROSSOVER` files to parse, the delta would be the slower route, so the build escalates and reports `delta_too_large` with the parse count, the git-named count and the threshold beside each other. **It is off by default (`0`), because measuring this repo found no such crossover:** a delta costs ~60.8 s plus 0.135 s per parsed file up to 1,000 files, then the slope collapses to 0.0088 s/file as the resolve phase saturates — 213.6 s for 3,000 changed files against a measured 550 s full build. R2.3 forbids importing another project's constant, so the mechanism ships for a repo that measures its own. The three correctness routes outrank it, and a contract-era lag never reaches it at all (212) |
| `search_symbol` | ranked symbols (`qname`, kind, `file:line`) — exact and prefix matches band ahead of substring near-misses across the whole result set, not just the page ([180](design/indexing.md#exact-matches-band-ahead-of-near-misses-task-180)). Within a band, any hit CONTAINED by a direct-match parent ranks after the container's own definitions so members cannot truncate them off the page ([292, 297](design/indexing.md#a-container-outranks-its-contains-members-tasks-292-297)); paths outside a stamped mirror pair rank above copies, and a mirrored hit names `mirror_counterpart` only when that sibling is itself indexed — a diverged file gets no field rather than a path that does not exist (282); `search_order` states the rule when mirrors exist (277 / 115). **The stack-trace spelling is a first-class query:** `Class::method` — and the container spelling `Class.method` — bands as a *direct* match when it is a separator-boundary suffix of the qname, so you can paste what the stack trace, the code review or the ticket said without first splitting it (287/293). A miss sharing no substring with any symbol is routed through its own name tokens rather than answered as a flat zero — `reason: token_candidates` (253). A zero **at a coverage edge** — a `dynamic_sql` / unmodelled-resolution stamp, or a suffix outside what the index holds — carries a `try_instead_hint` naming the Grep fallback (no `try_instead`, since Grep is not a registered tool), so the dead end routes the reader on instead of dying silent (314) |
| `file_outline` | symbols + line ranges, no bodies |
| `read_symbol` | source of just one class/method + docblock; bodies above `BODY_LINE_THRESHOLD` (600) elide by default with `body_elided` + route (`full_body` / `line_start`–`line_end` keep the whole or a range — 288); at `standard` `stored_fields` lists the node and `extra` keys actually populated, so an absent field reads as absent rather than unasked (250); on a repo with stamped mirror pairs a hit names its twin — `mirror_counterpart`, or `mirror_no_counterpart: true` when the sibling is not indexed — so a perfect body for the port no request reaches cannot read as *the* code that runs (286) |
| `find_callers` / `find_references` / `find_implementations` | resolved relationships + confidence tier; `find_references` on a `Foo::class` mention is `DYNAMIC` and sets `authoritative: false` when every hit is (094); on a **Table** or **Column**, `find_references` returns linked `WRITES` only (tiers as stored) — a Table unions writers of the table and of its CONTAINS columns, a Column is the narrower set — with `unlinked_writes_count` when the graph still holds unlinked writers; multi-language indexes carry `writes_emitters_only` when a covered language emits no `WRITES` — host-language string writes stay out of scope (278/281); `find_callers` can also filter call sites by argument shape (`arg_position` + `arg_is`), and by tier: `confidence_tier` at depth 1 is a **store predicate**, not a post-page filter, so the one RESOLVED caller of a common name is reachable — and the default inbound page order is now tier-first (`RESOLVED` before `HEURISTIC` before `DYNAMIC`, then today's stable keys — 265), so page 1 is no longer an accident of spelling; `tier_filter` names an opt-in filter and an unfiltered mixed page carries `tier_census` (251). Three answers are deliberately **not** `ok`: a class-level `find_references` answered from its members' callers is `via_members` (252), an empty `find_callers` on a `Method` that expands to proximity-ranked unresolved same-named call sites is `proximity_candidates` with `candidate_of` on every row (258), and an empty `find_references` with unlinked inbound edges of **any** kind says so in `unlinked_edge_kinds` rather than a bare `no_matches` — the honesty predicate is no longer keyed to the two kinds a PHP class subject happens to have (255). Both `find_callers` and `find_references` take `serve_behind` (default off): on an index behind HEAD they answer and label it — unchanged subject as `index_behind` (257), unrepaired dirty subject as `index_behind_subject_changed` (267) — with the built revision, instead of declining at the moment a caller most wants them. Both inbound tools partition the answer by role: `production_count` + `test_count`, with `test_role_source` naming how the test rows were decided (`adapter` · `path_convention` · `mixed`) — *three callers* and *three callers, all in the unit test* are different answers (262). `exclude_tests=true` filters in SQL **before** paging, so page 1 is production callers, not the production callers that survived a page of tests; depth 1 only, and the census is omitted above it because a depth-1 partition cannot add up to a BFS total. A zero at a coverage edge here likewise carries the Grep-routing `try_instead_hint` rather than a silent `no_matches` (314) |
| `find_view_data` | view-scope keys a handler publishes (`PROVIDES_VIEW_DATA` — needs `CA_INDIRECTION_RULES` `view_data` setters) |
| `include_graph` | `include`/`require` neighbors (`imports` / `imported_by` / `both`); a file whose language carries the relation as `IMPORTS` instead gets `relation_unmodelled_for_language` and a route, never a confident zero (186/188) |
| `impact` | bounded blast radius of a change (paths/qnames), depth-limited with decay; each row names its test role and mirror twin, and `exclude_tests` filters inside the walk (313) |
| `impact_modules` | the same radius rolled up to the business modules it reaches — per-module symbol counts split by confidence tier, one exemplar `file:line` to read first, and an explicit `unassigned` bucket. `walk_truncated` marks a bounded walk, which makes every count an under-estimate (140) |
| `subtree_dependencies` | tree-to-tree crossing with duplicate-declaration attribution — attributable vs unattributable always paired; dynamic alias bridges surfaced |
| `reachable_from` | forward reachability from configured entry points. Default `detail_level` is **`minimal`** (268) — ask for `standard` when you want the full walk |
| `find_orphans` | unreachable / zero-inbound symbols (dead-code candidates). Default `detail_level` is **`minimal`** (268); pages with `limit`/`offset`, and its walk is bounded by its **own** `CA_ORPHANS_MAX_NODES` rather than the impact budget. Roots that match nothing, a walk that exhausts its budget (182), and an index stamped with `unmodelled_resolution_by_language` (279, and 294-296 for the other three adapters) [refuse instead of returning rows](design/indexing.md#find-orphans-refuses-rather-than-dumping-what-it-has-flagged-tasks-182-279) |
| `explain_path` | shortest control-flow path between two symbols |
| `architecture_overview` | this repo's layers, their degrees and the crossings between them — default `detail_level` is **`minimal`** (268) — plus the zero-inbound split, the capability table and the mirror panel ([detail](#architecture_overview--layers-crossings-and-the-populations-behind-a-zero)) (onboarding) |
| `guided_tour` | a dependency-ordered reading list of files, cycle-safe and budget-bounded ([detail](#guided_tour--a-reading-order-that-expands)) (onboarding) |
| `generate_onboarding` | writes the committable markdown and the self-contained `index.html` **system map** under `docs/onboarding/` — four or five files depending on `audience`, no per-module page tree ([detail](#generate_onboarding--the-committable-system-map)) (onboarding) |
| `check_architecture_rules` | confirmed vs candidate violations of declarative path-set dependency rules (`CA_ARCHITECTURE_RULES`) |
| `diff_architecture` | architectural drift between two onboarding dataset / manifest snapshots |
| `class_diagram` | mermaid class diagram for one type plus its ancestry, or every type in one file — inheritance from resolved edges; associations from declared types only |
| `check_column_defaults` | which writers of a table omit a column that declares a `DEFAULT`, against the total that write it — a writer naming no columns is *unmeasured*, never an omitter; a bare table name resolves to its one schema-qualified table or is refused with the candidates (SQL tier 2, 320) |
| `trace_capability` | the capability flows ONE subject takes part in — an entry symbol (`qname`), a file (`path`) or a business module (`module`); each result is a traced path with its hops (`qname` · `file` · `layer` · `kind` · `tier`), how it `ended` and its `sink`. Carries no layer table, matrix or hub list: for the whole picture call `architecture_overview`. A subject the index does not hold answers `no_such_symbol`; one that joins no flow answers `no_matches` (199) |

### `architecture_overview` — layers, crossings, and the populations behind a zero

- `summary.reachability` splits the zero-inbound modules into their real populations — web surface,
  vendored, tests, no-inbound-but-outbound (**not** dead code), no-edge-either-way (a list to check,
  not a conclusion) — with the raw total kept beside them.
- `summary.business_modules` is the capability table — which file to open for a named screen — with
  its own coverage beside it, the container level derived from the tree rather than named, and a
  role-organised container refused with its reason. It is **never empty**: it fills from three
  ordered sources — a human `docs/onboarding/capabilities.toml`, then entry rows from
  `CA_ENTRY_POINTS` / HTTP entries, then structural modules — and only a genuine miss falls through,
  naming its candidate globs and `files_matched` rather than an empty table (263).
- `summary.mirrors` names sibling subtrees that duplicate each other's paths — discovered, not
  configured — with a counterpart lookup whose negative answer marks divergence, and the standing
  caveat that it compares paths, not bytes.
- Each bucket also reports **which signal produced it** — `signals: {declared, vocabulary,
  structure}` — and every declared glob reports what it `files_matched` beside what it
  `zero_inbound_claimed`, so a stale declaration is legible instead of invisible (119).
- A bucket whose own declaration was never given **and** whose count is 0 says so where the count
  is, and names the setting that would populate it (`entry_points` / `stub_roots`, env
  `CA_ENTRY_POINTS` / `CA_STUB_ROOTS`) — that 0 answers a question nobody asked, and reading it as
  *"this repo vendors nothing"* is the misreading it now prevents (208). A declaration that matches
  no indexed file still reports so beside the count, so the two disclosures compose.
- Every list is capped at `CA_MAX_RESULTS`; `verbose` pages the per-module rows with `offset`.

### `guided_tour` — a reading order that expands

- Dependency-ordered list of files, cycle-safe via SCC condensation.
- Roots prefer files that lead somewhere, then reading-seed layer rank (HTTP before Config), and are
  capped at a quarter of the node budget, so the walk expands
  instead of spending the budget on isolated files.
- A component no entry point reaches is re-seeded, not dropped.
- The walk is bounded by `CA_IMPACT_MAX_NODES`; the page is capped at `CA_MAX_RESULTS` with `offset`.

### `generate_onboarding` — the committable system map

- Writes `overview.md` and `manifest.json` always, plus whatever the `audience` contract names —
  `tour.md`, `flows.md` and a self-contained `index.html`, so `full` and `newcomer` get **five files**
  and `maintainer` **four** (no tour). Offline, theme-aware, repo text escaped so a path cannot
  inject markup, with a `<noscript>` fallback. `overview.md` includes a mermaid layer flowchart
  (GitHub/VS Code render it; the HTML map stays fetch-free and does not bundle mermaid).
  Its body is organised under **question-shaped headings** — the seven a reader actually asks (what
  is this repo, where are the landmines, where to start reading, which file for a named change, the
  spine, what changed since the last generate, what not to trust) — with the graph-noun census
  sections demoted to an appendix (269).
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
- **There is no per-module page tree.** It emitted one page per node-budget slot — 500 on every
  repo, whatever its size — and the median page carried a path already in its own filename, a role,
  a layer and a truncated neighbour list; on a 24,535-file repo 412 of the 500 rendered a Summary
  line saying there was no summary (205). The facts those pages carried are in `tour.md`,
  `overview.md` and the map.
- It refuses a tree it did not write, and removes the module pages a **pre-205** manifest recorded —
  so the first regeneration after 205 cleans the old tree and leaves a hand-authored file alone.
- Regenerable, versioned `artifact.json` under `.code-atlas/onboarding/` (`ARTIFACT_VERSION`;
  gitignored). The tour walk is bounded by `CA_IMPACT_MAX_NODES`; nothing else borrows that budget.

## What it cannot answer — reach for `grep` instead

The verdict of the field retros ([protocol](runbooks/field-retro.md); the round corpus is kept
outside this repo, findings land in [PLAN §19](PLAN.md#19-project-context--decision-log)):
code-atlas is excellent at **who / what / where** over resolved symbols, and structurally
unable to answer **"is something missing here?"**. The
index holds what the adapters parsed. A question whose answer is an *absence* cannot be settled by a
store of presences, and asking anyway buys a confident wrong answer.

| Question shape | Why the index cannot settle it | Ask instead |
|---|---|---|
| "Is there any call site that forgets to check X?" | an omission leaves no node and no edge | `grep` the positive form, then subtract |
| "Does any file still use the old constant?" | string-only usage is not a resolved relation | `grep` — it is literal text |
| "Which of these have no test?" | an untested symbol has no *absence* row; only `find_callers` + `test_count` can bound it | `find_callers` per subject, then read the zeros as *candidates* |
| "Is this config key read anywhere?" | keys live in strings, not the symbol table | `grep`, then `find_references` on whatever resolves |

The positive twin of each of these **is** a graph question — *who calls this*, *what writes that
table*, *which modules does this change reach* — and that is where the ~69× token saving lives.

## Coverage honesty — before you read a zero as "it is not there"

Three fields say the index never looked, rather than looked and found nothing:
`unconfigured_adapters` (the adapter is not launchable), `unindexed_languages` (it runs, the graph
holds none of that language) and `unindexed_same_basename` (same-stem files whose suffix the index
does not hold, beside a **non-empty** page). Field rules are the contract's, in
[`CONVENTION.md` §6](CONVENTION.md#6-mcp-tool-conventions); what matters at call time is this:

- **They are omitted when empty**, so seeing one at all is the signal (061).
- **`detail_level: "minimal"` omits all three** (223) — and `reachable_from`, `find_orphans` and
  `architecture_overview` *default* to `minimal` (268). On those three, a default-level zero is not
  an audited zero: ask for `standard` before concluding absence.
- **A partial answer needs them as much as an empty one** (192). One hit with `reason: ok` for a
  symbol with hundreds of sites in a language the index does not hold is a false negative wearing a
  modelled zero's clothes — `reason` stays `ok`, the field beside it is the caveat (299).

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
answer says so rather than reporting a quieter `no_matches`. When a sweep mixes `ok` with
`index_stale`, the envelope names `index_stale_subjects`, `repair_budget_shared`, and
`repair_budget_order: "queries"` (275); a fully-`ok` sweep stays unchanged. Each stale entry carries
`retry_as: "query"` so the single-subject call can spend the whole budget. A `kind=` filter that
drops an exact-name hit of another kind answers `kind_excluded` (with those kinds), not absence.
A `path_prefix=` filter that drops an exact-name hit outside the subtree answers `path_excluded`
(with those file paths), not absence (315).

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
| `impact_modules` | the same subject as `impact`, and the same reason: one radius, rolled up once |
| `subtree_dependencies` | its subject is a directory prefix — the answer is a repo-wide report, not a per-name lookup |
| `reachable_from` | its subject is the configured entry-point set, not a caller-supplied name |
| `find_orphans` | the complement of the whole graph — there is no subject to list |
| `explain_path` | its subject is already a pair; a list of pairs is a query language, which 101 deliberately is not |
| `architecture_overview` | its subject is the whole index — there is one repo to lay out, and a list of subjects has no meaning for a repo-wide shape |
| `guided_tour` | its subject is the whole index — there is one reading order, and a list of subjects has no meaning for a repo-wide walk |
| `generate_onboarding` | a write is one artifact against one tree — R4.3's single writer, not a fan-out |
| `check_architecture_rules` | its subject is the configured rule set — a list of rule ids is filtering, not a batch of independent questions |
| `diff_architecture` | its subject is already a pair of snapshots — a list of pairs is a query language, which 101 deliberately is not |
| `class_diagram` | its subject is one type (plus ancestry) or one file — a list of subjects is N diagrams, and the honest form is N calls |
| `check_column_defaults` | its subject is one table, and the answer is already a scan of every defaulted column on it — a list of tables is N independent scans with no shared arithmetic |
| `trace_capability` | its subject IS the question — *what happens when a user does X* is asked of one entry, one file or one module. A list would return N unrelated traces and reintroduce exactly the over-answering 199 exists to remove (101) |

## Operator prompts (human-invoked — not part of the agent tool surface)

These MCP prompts are **operator recipes a human invokes**; an agent's client exposes only the tools
above to the model, so a model never sees a prompt (task 081). Agent routing lives in the tool
descriptions themselves (each names the question it answers — task 069), not here. `which_tool` is
the exception a model *can* read: task 200 generates its map into an Agent Skill at
[`contrib/skill/`](../contrib/skill/) — generated from the registered tools, never hand-edited, with
a drift guard.
The blind recognition probe that scores whether those descriptions route — and that separates
name-only answers from description-backed ones — is
[`docs/runbooks/tool-recognition-probe.md`](runbooks/tool-recognition-probe.md) (081, 097).

| Prompt | Recipe |
|---|---|
| `explore_area` | status → search/outline → read only what's needed |
| `find_usages` | status → find_references / find_callers / find_implementations → read to confirm |
| `impact_of_change` | status → impact on the changed paths/qnames → read only the blast-radius surface |
| `which_tool` | a recognition map: which tool answers a given question, across all 24 tools |

## Hooks (opt-in)

code-atlas answers when asked. Two hooks cover the moments an agent was never going to ask — an edit
that drifts the index, and a `Read` that could have carried one line of context. Both are opt-in, and
both are offered rather than installed.

### Keep the index fresh while Claude edits (opt-in)

Task 035 already reparses drifted files at query time. For eager updates after Claude Code
`Edit`/`Write` on a file **any** installed adapter owns — the matcher is generated from each
adapter's own declared suffixes, so the next adapter is covered the day it lands (200) — install the
PostToolUse hook under
[`contrib/claude-code/`](../contrib/claude-code/) (`code-atlas-poke` console script + `"async": true`);
opt-in git refresh after pull/checkout via [`contrib/git/`](../contrib/git/) (`code-atlas-refresh`,
background — never auto-installed into `.git/hooks`).
Safe no-op when `.code-atlas/graph.db` is missing; does not stall the tool round-trip.

### The read-time signal — a line that rides along with a file you are already opening (opt-in)

Field evidence (task [099](tasks/099_write-time-signal-seam.md)): the three most consequential
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

### The session-boundary state line — the index state, restated when the first copy decayed (opt-in)

MCP `instructions` deliver the index state once, on `initialize`; a long session outlives it and a
compaction drops it, so agents that started a multi-minute build filed its progress signal as missing
([322](tasks/322_the-state-line-is-delivered-once-and-never-again.md)). `code-atlas-state` restates
`get_index_status`'s own `summary` — lifted, never recomposed — at `SessionStart` (its `compact`
source is the post-compaction delivery) and `PreCompact`. While a build holds the lock it appends the
live phase and names `code-atlas-build --status`. **Silent** when there is no index, or when the index
is current and no build runs; ≤ 90 tokens; always exits 0; never builds, reparses or takes the build
lock. Wiring: the generated [`contrib/claude-code/settings.snippet.json`](../contrib/claude-code/).

## Configuration reference

Every knob resolves **environment → project file → default**. The project file is
`.code-atlas.toml` at the repo root (optional, meant to be committed); its keys are the environment
names lower-cased without the `CA_` prefix. A malformed value or an unknown key is a loud error, never
a silent fallback.

| Environment | `.code-atlas.toml` | Default | Meaning |
|---|---|---|---|
| `CA_DB_PATH` | `db_path` | `.code-atlas/graph.db` | index location (relative to the repo root) |
| `CA_WORKERS` | `workers` | `max(1, min(cpu-2, 8))` | adapter processes during a build |
| `CA_ADAPTER_TIMEOUT` | `adapter_timeout` | `30` | seconds an adapter may stay silent before a build kills it |
| `CA_PAGE_LIMIT` | `page_limit` | `50` | query-time row ceiling for search/nav; a request above the cap is honoured to the cap and says so in `limit_capped_to`. Changing it does **not** require a rebuild (259) |
| `CA_MAX_CANDIDATES` | `max_candidates` | `50` | build-time resolver fan-out; changing it **requires a rebuild**. `CA_MAX_RESULTS` / project-file `max_results` alias here only — they no longer set the page cap (259). Since 258 fan-out no longer multiplies unresolved bare-name `Method` calls into the graph |
| `CA_MAX_SUBJECTS` | `max_subjects` | `25` | subjects one `search_symbol` sweep may take; a refused subject is named in `subjects_dropped`, never dropped silently |
| `CA_IMPACT_DEPTH` | `impact_depth` | `2` | hops the impact engine traverses (with default decay/floor, depths above ~8 are a no-op) |
| `CA_IMPACT_MAX_NODES` | `impact_max_nodes` | `500` | node budget for one impact query (seeds kept preferentially when over budget) |
| `CA_ORPHANS_MAX_NODES` | `orphans_max_nodes` | `500` | node budget for the reachability walk inside `find_orphans` only — deliberately **not** the impact knob, so tuning one cannot change which orphans exist |
| `CA_FULL_BUILD_CROSSOVER` | `full_build_crossover` | `0` (disabled) | files-to-parse above which an incremental escalates to a full build **for cost**, reported as `delta_too_large`. Off by default because measuring the anchor found no crossover below its own size — a delta there is cheaper at every size, since the resolve phase saturates around 1,000 files (212). Set it only from your own measurement (R2.3) |
| `CA_PATH_INDEX_MAX` | `path_index_max` | `20000` | path cap for the onboarding dataset's front-coded path index; when it trims, the dataset carries both the total and the shown count |
| `CA_ENTRY_POINTS` | `entry_points` | unset | file globs that seed reachability. **`reachable_from` and `find_orphans` need this** — unset, they report *no roots configured* rather than guessing |
| `CA_STUB_ROOTS` | `stub_roots` | unset | dependency roots (e.g. `vendor`) to index declarations-only, so third-party signatures resolve; hits carry `stub: true`. Costs one extra pass |
| `CA_WORKING_ROOTS` | `working_roots` | unset | repo-relative directory prefixes the onboarding artifact treats as the reader's working tree. It narrows the onboarding tour, flow seeds and busiest-file pick; unset is the whole index |
| `CA_SOURCE_ROOTS` | `source_roots` | unset | extra repo-relative directories tried (in order) after the repo root and the importer's ancestors when resolving absolute imports. Needed for a `src/` layout or a mounted layer/package tree; unset keeps today's climb-only behaviour |
| `CA_PROJECT_FILES` | `project_files` | the ecosystem manifests, a root `README*` and an agent brief | repo-relative files the onboarding *Start here* section quotes and cites. Values are lifted from declared keys and reproduced verbatim, never summarised; a file that cannot be parsed becomes a stated gap and never fails the build |
| `CA_AUDIENCE` | `audience` | `full` | who the WRITTEN onboarding tree is for: `full` (every section), `newcomer` (orientation, a four-line summary, the layer vocabulary, the tour and the flows) or `maintainer` (every aggregate, no tour, no orientation). An unrecognised value falls back to `full` and the artifact states which audience it actually used |
| `CA_INDIRECTION_RULES` | `indirection_rules` | unset | JSON rule files mapping framework indirection to edges. **`find_view_data` needs this** — without `view_data` setters it answers `capability_not_configured`, not a zero |
| `CA_ARCHITECTURE_RULES` | `architecture_rules` | unset | JSON rule files of path-set dependency constraints. **`check_architecture_rules` needs this** — unset → `capability_not_configured` |
| `CA_TOOLS` | `tools` | all tools | comma-separated tool allow-list. Opt-in field-18 six-tool preset (268): `get_index_status,search_symbol,read_symbol,find_callers,find_references,impact` (`code_atlas.main.FIELD18_TOOLS`). Default surface stays 24. |
| `CA_HOST_ROOT` | `host_root` | unset | absolute-path rewrite only (pair with `CA_CONTAINER_ROOT`; unused by the relative-path build) |
| `CA_CONTAINER_ROOT` | `container_root` | unset | absolute-path rewrite only (pair with `CA_HOST_ROOT`) |
| `CA_<LANG>_CMD` | `[adapter_cmd].<lang>` | — | the **complete argv** that launches one adapter in server mode |

```toml
# .code-atlas.toml
workers = 4
page_limit = 50
max_candidates = 50
tools = ["get_index_status", "build_or_update_index"]   # only names the server serves; a typo is a loud error
# Optional: only needed if something passes absolute host paths to the adapter.
# host_root = "/home/you/project"
# container_root = "/app"

[adapter_cmd]
php = "docker compose exec -T php php /app/adapters/php/index.php --server"
typescript = "node /abs/path/to/code-atlas/adapters/typescript/index.js --server"
sql = "node /abs/path/to/code-atlas/adapters/sql/index.js --server"
python = "python /abs/path/to/code-atlas/adapters/python/index.py --server"
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
[`onboarding_llm/`](../onboarding_llm/README.md), plugs into three seams: it can replace the one-line
module summary (085), rename weak architectural layers — the generic `source`/`sink`/`mixed` bands
084 falls back to on flat namespaces (091) — and write the map's prose (117): each layer's
responsibility line, each tour step's narrative, and the wording of the headline facts.

**Structure is never the seam's to change.** Every count, ranking, grouping and the set of headline
facts is derived before a model is consulted, so enrichment rewords the map and nothing more; a
failure or a filler answer simply leaves the deterministic sentence in place.

**What each seam costs per build**, because the two are bounded differently and a single figure for
"enrichment" was wrong:

| seam | calls per build | bound by |
|---|---|---|
| prose (117) | at most **45** whatever the repo's size | a per-slot ceiling: 6 headline · 12 layer · 15 step · 12 module |
| layer names (091) | one, and only when the layer method is a weak fallback | the layer table, not the repo |
| module summaries (085) | **one call per tour module** — uncapped by the seam | `CA_IMPACT_MAX_NODES` (default 500), which sizes the tour |

So the summarizer is the expensive one: it scales with the tour budget while prose does not. Narrow
it with `CA_IMPACT_MAX_NODES` or `CA_WORKING_ROOTS` before turning it on over a large repo.

The **core never imports it**: you install the `llm` extra, set `CA_ONBOARDING_SUMMARIZER=llm`,
`CA_ONBOARDING_LAYER_REFINER=llm` and/or `CA_ONBOARDING_PROSE=llm`, and run `code-atlas-llm` instead
of `code-atlas`. All three are memoised in content-hash caches so runs replay and diffs stay stable.
These are `onboarding_llm` knobs, not core config — the full table is in that package's README.

**`audience` and `detail_level` are different knobs, and this is the decision (210).**
`detail_level` means the same thing on 24 tools — how much of the **response** to return — and the
response is read once and dropped. Growing it to reshape the committed tree would make files a repo
checks into git depend on a per-call argument, so it **stays a payload knob and is unchanged**.
`audience` is the artifact knob: it selects which sections `overview.md` holds and which documents
are written at all, and the tree states which audience produced it, in `overview.md`'s *Who this was
written for* section and in `manifest.json`. Each audience is a written content contract — the
sections it gets **and why that reader needs each one** — held in one place, `onboarding/audience.py`,
which the markdown, the dataset and the viewer all read rather than re-deriving.

**What a newcomer asks first** is answered above the aggregates, in `overview.md`'s *Start here*
section: what the repo says it is, how to run its tests, its declared commands, services, ports and
runtime — each one quoted from a declared project file and carrying the `path:line` it came from,
and each one the repo does **not** declare stated as an explicit gap rather than left silent. The
graph never sees these files; the section is I/O over the repo, not inference (207). The answers reach `dataset.json` under
`orientation`; the tool payload carries none of them — read the committed `overview.md` (207).

**Which one wrote the tree you are reading** is recorded in the artifact itself: `overview.md` ends
with a *How this was written* section and `manifest.json` carries the same three names under
`provenance`, so an empty summary is attributable to the run rather than read as a fact about the
repo (209).
