# Design — what an answer discloses

> Part of code-atlas's **design record**. The [README](../../README.md) states what the product does and
> how to install it; this file carries *why an answer is shaped the way it is*, one section per
> field incident that changed it. It is **not** a rule book (→ [`ENGINEERING_RULES.md`](../ENGINEERING_RULES.md)), not
> task status (→ [`BACKLOG.md`](../BACKLOG.md)), and never the authority for a benchmark number
> (→ [`runbooks/`](../runbooks/)).

A silently partial answer is worse than no answer. Every section here is a field incident where a
payload told a caller something true and let them conclude something false — and what the payload
now says instead.

### Reading an answer — every payload says what it is not telling you

An answer that is silently partial is worse than no answer, so the payload carries its own limits.
The list-returning tools take **`limit` / `offset`** and page in a stable order, and every one of
them reports:

- **`total_count`** — the true size of the answer, never the length of the page you were handed.
- **`truncated`** — whether *this page* is the whole set. It describes the page alone, so a pager
  terminates; a walk that stopped on its own node budget says so separately in `walk_truncated`.
- **`limit_capped_to`** — present only when your `limit` exceeded the page cap (`CA_PAGE_LIMIT`). The server
  honoured fewer rows than you asked for, and says so rather than letting `truncated` imply it.
- **`reason`** — why an answer is empty. `no_such_symbol`, `name_not_qualified` (with
  `candidate_count`), `not_indexed` (the file is on disk but untracked), `relationship_not_modelled`,
  `capability_not_configured`. `find_callers` may instead answer an empty linked result with
  `proximity_candidates` rows, each naming its `candidate_of` (258). **An empty result is never an unexplained zero**, and where a better
  route exists the payload names a real, callable tool in `try_instead`.
- **`resolved_qname`** — when you typed `Foo\Bar` and the index stores `\Foo\Bar`, the tool answers
  about the stored name and tells you which one it used.

Two more fire when a page could mislead: a truncated `file_outline` adds **`result_kinds`** (every
kind in the file with its count, so a capped symbol map cannot read as complete), and a truncated
`find_callers` page spanning several top-level subtrees adds **`result_subtrees`**, because page 1 of
a store-ordered answer clusters into whichever subtree sorts first.

`read_symbol` has the same honesty for a different unit of size: a declaration above
`BODY_LINE_THRESHOLD` (600 — one site in `source_slice`) returns the signature with
`body_elided: true` and `line_count`, plus a route, instead of shipping tens of thousands of tokens
by default. `full_body=true` or a `line_start`/`line_end` range inside the symbol still reach the
bytes; under the threshold the payload stays byte-identical (288 / 061).

Every answer also carries **`index_root`** — the source tree it describes — so an agent in a worktree
can spot a server pointed at the main checkout. While a build holds the write lock it also carries
**`build_in_progress: true`** and **`build_phase`** — a full rebuild answers from the last good
index until it publishes ([356](indexing.md#a-full-rebuild-keeps-serving-the-last-good-index-task-356)). Full field reference:
[`docs/CONVENTION.md`](../CONVENTION.md) §6.

### When an answer is a partition, both nav tools say so (task 168)

A same-named definition under a *different* qname means a simple-name reference may bind there, so
an answer keyed on one qname is a **partition of the truth, not the whole of it**. `find_callers`
disclosed that; `find_references` did not — 16 hits at `reason: "ok"` against 19 real sites.

Both now carry the same three fields, and each is omitted when there is nothing to say (061):

| Field | Meaning |
|---|---|
| `sibling_definitions` | the same-named definitions under other qnames, as `{file, line, kind}` sites |
| `authoritative: false` | this count is a partition — widen before you act on it |
| `authoritative_caveats` | **why**, one name per reason and merged, never replaced: `sibling_definitions`, `all_hits_dynamic`, `args_not_captured_by_adapter` (231), `cross_language_relation_unmodelled` (221/238; hit-path only when the stamped census has edges — 276), `tier_partition` (265) |
| `sibling_definitions_ranked` | **whether** position means anything here — a boolean verdict, always present at ≥ 2 sites |
| `sibling_definitions_ranked_by` | **what** the order was decided by — rides only when there is a basis to name |

`authoritative: false` alone cannot tell an agent whether to widen the query or to distrust the
confidence tier — two different actions behind one boolean. The sibling query is keyed on the
**subject's own kind**, which is 054's rule (a bare Method name is not a Function qname) stated once
rather than as a per-tool constant.

**Two bases, because one field answers two questions** (171 → 181 → 189).
`shared_file_name_with_subject` puts the same-named files first: a regional twin is another
`ModelMember.php`, while same-name noise is `Unrelated0.php`. `shared_subtree_with_subject` falls
back to nearest-first, which is the right order for *"where might a simple name bind?"* — the
question 165's caveat was actually asking. Ranking on nearness alone put 40 same-region vendor rows
above the one wanted twin and ranked the answer **last**, so the fix was not a better ranking; it
was naming which predicate decided the order.

An order with no evidence behind it is no longer dressed as one. `ranked_by: "path"` was **retired
from the vocabulary, not annotated** — a value that reads as a basis while meaning *there was no
basis* is a caveat nobody can act on. An unranked list is capped at 10 with its total reported
(8,705 B → 1,054 B on the field case); a **ranked** list is never capped, because there the position
*is* the answer.

`ambiguous_definitions` stays separate: that is the *same* qname defined twice, which is a different
fact and can appear on the same payload.

### Coverage claims key on what the graph holds (task 173)

A zero answer names the index's language gaps so it cannot read as absence. Both halves of that gap
are reported, because flipping a switch is not the same as running a build:

| Field | When it appears | What is missing |
|---|---|---|
| `unconfigured_adapters` | an adapter ships in-repo with no launch command | the switch — set `CA_<LANG>_CMD` |
| `unindexed_languages` | the adapter is configured, the graph holds no files of it | the build — `build_or_update_index(full=true)` |
| `unindexed_same_basename` | a non-empty `search_symbol` page whose hits (or query) share a stem with a tree file whose suffix is outside 173's held set | that suffix was never a candidate — count + suffixes, never a guessed language (299) |

Before this, wiring an adapter emptied the note *and* moved `indexed_suffixes` onto the new
language — while the graph still held zero files of it. So `collection` now names both sides:
`indexed_suffixes` is what the graph **holds** files for, and `claimed_suffixes` appears beside it,
only when the two differ, for what the build was configured to index.

Task 299 shrinks 160's AC3 carve-out on hit lists: a confident non-empty page is byte-identical
only when no same-stem unindexed twin exists. ``reason`` stays the hit band; the field is the note.

A skipped total also says what it is *made of* — `skipped.suffix_top` ranks the suffixes behind it,
`skipped.suffix_kinds` is the denominator (174). *"An adapter exists"* is a fact about the product
and four consecutive field rounds disclosed it and reported zero; *"3,294 files in **this** repo are
invisible"* is a fact about the reader's own cost, and it is the one that gets acted on.

### A zero that names the language, not just the index (tasks 186, 188)

160's coverage note names every language the index does not cover — deliberately *excluding* the
subject's own. On one language that carve-out is free. On two it manufactures a confident false
negative: `include_graph(path="…/thing.ts", direction="imported_by")` answered `no_matches`, meaning
*nothing imports this file*, when the truth was *TypeScript does not use `include` — this relation
is `IMPORTS` here, and this tool does not read it*. The better the adapter, the more confident the
wrong zero.

An empty inbound answer on a file whose language emits no `INCLUDES` **at all** now returns
`reason: "relation_unmodelled_for_language"`. Where that language carries the relation under a kind
that is linked, the payload names a real route; where it carries it under nothing, it stays a hint
with **no** route, because a fabricated `try_instead` is worse than admitting there isn't one.

That route exists at all because of 188. The TS adapter resolved every `import` specifier to a real
repo path — `tsconfig` `baseUrl`/`paths` and `export *` included — and the core discarded the
answer, because nothing linked `IMPORTS`. Every one was unlinked, so no tool could walk a module
graph. They are linked now, and `find_references` on a module's `File` qname lists its importers.

### Which code answered, and which config (tasks 170, 175)

`server_build` names the commit the running process imported when the disk still matches; on a
stale process it is the loaded content hash and rides `server_build_kind: content_hash` so a reader
does not treat it as a git object (284). `server_stale_process` makes that verdict **live**: it
fires when a loaded module's own content has moved on, so a build swapped under a long-lived server
is reportable rather than invisible. When it fires it also names the action and the axis —
`server_stale_action: restart_mcp_server_process` and `server_stale_differs` — because a warning an
autonomous caller cannot act on is noise, and the interactive `/mcp` reconnect it used to imply is
not a step an agent can take (267). `server_stale_impact` then says whether the tool-contract
surface moved with the disk (`tool_contract_unchanged` / `tool_contract_changed`), and
`server_repo_head` is the checkout's HEAD — context for the worktree tip, never "which code
answered".

Config is stamped the same way, because config decides what the index even contains — the field
episode edited `.code-atlas.toml` to add an adapter, built, and got a cheerful `wrote.files: 0`
describing the old world. `config_build` names the config the process loaded, `index_config_build`
the one the index was built with, and `config_stale_process` is **stated either way, never
omitted**: an absent field cannot distinguish *no divergence* from *not checked*.

Both ride `get_index_status` and `build_or_update_index` only — the two places a divergence costs a
build. Nav payloads already pay for the code axis unconditionally, and symmetry alone is not a good
enough reason to tax them twice.
