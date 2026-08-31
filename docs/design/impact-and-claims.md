# Design — blast radius, and signing an answer

> Part of code-atlas's **design record**. The [README](../../README.md) states what the product does and
> how to install it; this file carries *why an answer is shaped the way it is*, one section per
> field incident that changed it. It is **not** a rule book (→ [`ENGINEERING_RULES.md`](../ENGINEERING_RULES.md)), not
> task status (→ [`BACKLOG.md`](../BACKLOG.md)), and never the authority for a benchmark number
> (→ [`runbooks/`](../runbooks/)).

`impact` is the one tool whose answer is acted on destructively, so its seed handling is stated
here in full. `sign: true` is the opposite end of the same axis: turning an answer into a claim a
reviewer can re-run — and the list of answers deliberately left unsigned.

### An `impact` path seed says how far it expanded, and refuses a twinned one (task 169)

`impact(paths=[...])` used to append **every symbol in the file** as a seed, bypassing the
classification a `qnames=[...]` seed goes through. One file became N seeds silently, and the walk's
bare-name links then pulled in the twins' callers and callees — a **29× over-report** measured
against the same subject asked for by qname, on the one tool whose answer is acted on destructively.

Two things changed, both on the path seed only (the qname half was already fixed):

- **`seed_expansion: {"paths": 1, "seeds": 102}`** — how many seeds the request's paths produced, so
  a 6-node answer about one symbol is no longer indistinguishable from a 176-node answer about 102.
- **A path-derived seed whose trailing name is defined elsewhere is disclosed, not walked** — it
  comes back in `sibling_definitions` with `authoritative: false`, counted in `seeds_dropped`, and
  when nothing is left walkable the answer is `subject_ambiguous` with a route back
  (`try_instead: file_outline`, then re-run `impact` with `qnames=[...]`).

A path seed over a file with no same-named twins is unchanged.

### Signing a claim — `sign: true` (opt-in, off by default)

Five tools answer with an **attestation** rather than a list: a modelled zero, a counted set at a
named tier, the revision an answer describes. Those are claims a text search cannot make — and a
claim that never reaches the artifact where it is made has, in practice, not been produced.

Pass `sign: true` to `impact`, `impact_modules`, `find_callers`, `find_references` or
`get_index_status` and the
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
| `check_column_defaults` | the ratio it returns is only as complete as the writers the graph measured; a one-line claim would drop the `unmeasured` population, which is the whole point of the answer |
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
| `class_diagram` | a diagram is a shape; a count of types without the mermaid body is not checkable (144) |
| `trace_capability` | a traced path is only meaningful hop by hop: a one-line claim would assert *"this request touches N files"* while dropping the order, the layers and the tier of each hop — the parts that make it checkable at all (199) |
