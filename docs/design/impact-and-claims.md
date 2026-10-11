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
code-atlas/2 tool=impact subject="app/Http/A.php,app/B.php,+2" question=blast-radius answer=25 tier=RESOLVED seeds=4 seeds_dropped=0 frontier_skipped_non_resolved=0 rev=a1b2c3d ref=main index=current server=0.2.0 build=<sha> call="{""paths"":[""app/Http/A.php"",""app/B.php"",""app/C.php"",""app/D.php""]}"
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

**Re-running a claim (383).** The line ends with `call=`: the tool's arguments as JSON, defaults
left out, so the `+2` in `subject` costs nothing. `code-atlas query --verify-claim '<line>'` asks
that call again at the current index and prints `status`: `holds`, `changed` with `changed` naming
each asserted key that moved (`answer`, `tier`, `reason`, …), or `unverifiable` with a `reason` —
another format version (`claim_format`, which a `code-atlas/1` line always gets), an unreadable or
rejected call, a tool not served, or a refusal. `then` / `now` hold the asserted keys; provenance
(`rev`, `index`, `server`, …) is not compared; `rev_then` / `rev_now` name both trees and
`index_now: behind` says the answering tree is older than HEAD. A lost subject signs nothing, so its
`now` is the tool's `reason`. `holds` is about the counts the line asserts, not the set behind them:
one caller swapped for another still holds. A line in any other format version — older or newer —
is never replayed, and a call carrying an argument a re-run never replays (`reset_fit_counts`) is
`call_rejected`. The index is the project's, found as `code-atlas query` finds it. `--verify-claims <file>` finds every line
in a text file, prose and Markdown around them skipped, and adds `source` (`file:line`). Exit `3`
when any claim did not hold, so a consuming repo's lint fails on it.

**Cost.** Off by default and byte-identical to today when off. When on, the line costs one extra
git HEAD read and, measured on a one-symbol answer, **+75 tokens** on `impact` and **+70** on
`find_callers` (`code_atlas/tokens.py` proxy; `call` is 16 of them). Pinned under an 80-token delta.

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

## Has this symbol changed since revision X (384)

A record anchored to a method — a test doc, a verified behaviour, a signed claim — goes stale
when the method changes, and a file diff flags every record in a long file. So each adapter stamps
every symbol with `extra.body_hash`: a digest of the tokens on its lines from the language's own
tokenizer, comments and layout dropped (a Python docstring and a decorator count; SQL hashes per
line). A symbol covers its lines, so a class's fingerprint moves with any member's; a qname declared
twice in a file (an overload) covers every declaration. The core never reads source for it, and an
unstamped symbol answers `unknown`.

`code-atlas query --snapshot-symbols <out>` writes every symbol's qname, file, kind, signature
(params, modifiers, declared type) and fingerprint at the index's revision; the consumer keeps the
file. `--changed-since <out>` with `--qname` / `--path` (repeatable) answers one line per symbol:

| status | when |
|---|---|
| `unchanged` | same file, signature and fingerprint |
| `signature_changed` | params, modifiers or declared type moved — checked before the body |
| `body_changed` | same signature, another fingerprint |
| `moved` | the same fingerprint in another file — the same qname, or the same name and kind (`qname_now`) |
| `removed` | none of the above |
| `unknown_at_base` | the snapshot never held it — never `unchanged` |
| `unknown` | no fingerprint (`no_body_hash`), its file changed since the build (`file_changed_since_index` — git decides, so outside a checkout nothing is), the snapshot's own index had drifted there (`snapshot_file_drifted`), or the body sits in two places (`ambiguous_move`) |

A `--path` names every symbol the snapshot held in that file, plus any it gained (`unknown_at_base`).
A rename changes the tokens, so it reads `removed`; a body changed while moving keeps its qname or
reads `removed`. Each line carries `rev_base` and `rev_now`. A fingerprint is 64 bits and its
algorithm is the adapter's: after an adapter changes how it tokenizes (CHANGELOG says so), take a
new snapshot, or every body reads `body_changed` — never the reverse. Exit `3` unless every line is
`unchanged`. A claim (383) can hold on its count while the body under
it changed; this is the question that catches that. Build cost: see task 384.

