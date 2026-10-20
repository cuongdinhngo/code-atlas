# Lessons — code-atlas

The **claim corpus** the learning loop reads. One atomic claim per record
(`type` · `handle` · `status` · `seen` · `evidence` · `destination`); recall greps `handle:` and
**recurrence is the number of distinct ticket keys in `seen:`**, unioned across every claim sharing a
handle. Newest first.

**Reset for phase 2 (2026-09-27).** Phase 1's corpus — its live claims, its class index and its
retired index — was archived with phase 1's task files. The rules it produced stay binding in
[`ENGINEERING_RULES.md`](ENGINEERING_RULES.md) and [`AGENT_BRIEF.md`](AGENT_BRIEF.md); a claim id
they cite (`127-C1`, `PROM-C3`) names a phase-1 record and resolves in that archive, not here.
Recurrence restarts at zero: a new sighting of a class a rule already carries cites the rule, and
becomes a claim here only when it shows the rule's wording missed a case.

**No per-ticket narrative.** A record states the claim and its evidence; what the ticket did lives
in its task file and its [`TOKEN_LEDGER.md`](TOKEN_LEDGER.md) row. This is R7.6 applied to this file.

**One claim record per handle.** A second sighting of a handle bumps that record's `seen:`; it never
opens a sibling record, or a recurrence-2 class reads as two recurrence-1 notes.

**Retired claims are an index, not records.** A claim whose class a rule now carries moves to the
Retired table — id, handle, rule — so the rule book's citation still resolves. `RECALL:` skips it.

A record, for shape:

```
### NNN-C1 — the claim, stated as what is true

- type: 2 (code | process) · handle: `a-kebab-case-class-slug`
- status: proposed · seen: NNN
- evidence: what happened, where (path:line, commit, test), and why it generalises past this ticket.
- destination: where it goes on promotion (a rule, a brief entry) — or "first sighting".
```

## Class index — read this before proposing a new rule

Every type-2 handle at recurrence ≥ 2, and where it landed.

| handle | rec | tickets | where it landed |
|---|---|---|---|
| `formatter-rewrites-untouched-lines` | 10 | 343, 357, 359, 360, 361, 362, 363, 364, 365, 366 | ENGINEERING_RULES R7.7 |
| `child-build-inherits-adapter-env` | 2 | 356, 357 | ENGINEERING_RULES R6.10 |
| `widen-every-query-that-shares-the-page` | 11 | 362, 364, 367, 389, 396, 397, 398, 400, 402, 403, 404 | proposed for ENGINEERING_RULES by 389 — awaiting the maintainer's `/mango:promote` |
| `read-a-literal-by-its-structure-not-a-regex` | 2 | 361, 371 | not yet — awaiting the maintainer's `/mango:promote` |
| `a-route-list-must-come-from-the-tools-verdict` | 3 | 388, 396, 401 | not yet — awaiting the maintainer's `/mango:promote` |
| `a-shell-surface-needs-an-agent-channel` | 2 | 387, 401 | not yet — awaiting the maintainer's `/mango:promote` |

## Live claims

### 399-C1 — a row that came from another language's region inherits its file's language wherever `files.language` is joined

- type: 2 (code) · handle: `a-guest-row-needs-its-own-language`
- status: proposed · seen: 399
- evidence: a PHP view's `<script>` functions written under the view would read as PHP to the resolver's same-language
  bare-name gate (204), so a PHP call could link to a JS function and a unique PHP link go ambiguous. The exposure-checker
  then listed every other `files.language` reader (census, filters). The row carries its own `language` (schema 9).
- destination: first sighting.

### 400-C1 — one long writer transaction turns every reader-side write into a busy-timeout wait

- type: 2 (code) · handle: `a-long-writer-makes-reader-writes-wait`
- status: proposed · seen: 400
- evidence: WAL readers of an incremental's one transaction read in 0.001 s, but each fit bump waited the full 5 s busy
  timeout and dropped its count, two per served call. The poke repair and `reset_fit_counts` did the same, and the
  reviewer found the last. Before you lengthen a write transaction, list every writer that runs on a reader's path.
- destination: first sighting.

### 400-C2 — a `with conn:` through a local alias commits a batch that a `with self._conn:` sweep missed

- type: 2 (code) · handle: `an-alias-hides-the-commit`
- status: proposed · seen: 400
- evidence: replacing the 12 `with self._conn:` sites left `_fill_delta_temps`' `conn = self._conn; with conn:`
  (`store.py:3104`), which committed the build mid-way. Only the in-batch `BatchLostError` guard caught it, at the
  resolve. Sweep for the object, not one spelling of it, and keep a guard that fails when one slips through.
- destination: first sighting.

### 398-C1 — a worktree run of the suite tests the main checkout's adapters and core

- type: 5 (environment) · area: `test harness / git worktrees` · verified-at: 2026-10-17, this host
- status: proposed · seen: 398
- evidence: in a `git worktree`, tests that spawn an adapter read the host's `CA_<LANG>_CMD` (pointing at the main
  checkout) and the fake adapter imports `code_atlas` from the venv's editable install, so a contract bump read
  "adapter speaks v15" ~400 times, and a symlinked `adapters/php/vendor` autoloaded the main checkout's `src/`. Run
  with `CA_*_CMD` unset and `PYTHONPATH=<worktree>`, copy `vendor/`, or run the gate in the main checkout.
- destination: stays in lessons_path (type 5, environment).

### 396-C1 — a payload that omits `reason` reads as `ok`, so a relabel keyed on `"ok"` skips it

- type: 2 (code) · handle: `an-absent-reason-is-ok`
- status: proposed · seen: 396
- evidence: `impact` builds its envelope with no `reason`, so `attach_rules_stale`'s `reason == "ok"` test never
  fired on `impact(routes=)` and a stale route answered unlabelled. The challenger asked for the untested surface;
  its test raised `KeyError: 'reason'`. The relabel now reads an absent reason as `ok`.
- destination: first sighting.

### 389-C1 — a shared store's read-through repair rewrites rows another checkout reads as built

- type: 5 (descriptive) · area: `freshness / shared index across checkouts`
- status: proposed · seen: 389
- evidence: the challenger's F5 — main's `find_callers` repaired its own dirty file into the one store while
  `last_commit` stayed at the build, so a worktree reading an unchanged file got main's spans. The overlay now
  compares the stored hash with the worktree's bytes per file (`Overlay.changes`); `test_challenger_main_…`.
- destination: stays in lessons_path (type 5, descriptive; no `design_doc_path` file exists yet).

### 388-C1 — a status that names what a tool refuses must ask the tool's own predicate

- type: 2 (code) · handle: `a-route-list-must-come-from-the-tools-verdict`
- status: proposed · seen: 388, 396, 401
- evidence: `get_index_status` put `find_callers` / `find_references` under `behind_refuses` from a constant list
  whenever the index was behind, yet both answered `ok` for every unchanged subject (reproduced on `main` daa6baa0);
  six anchor PRs fell back to Grep. R1.8 covers two sites branching on one verdict; this site never consulted the
  verdict at all. 365 had fixed the held case the same way, by calling the guard's predicate.
- destination: first sighting.

### 387-C1 — a surface reached only from a shell is invisible to an agent until its brief names it

- type: 2 (process) · handle: `a-shell-surface-needs-an-agent-channel`
- status: proposed · seen: 387, 401
- evidence: 382–384 shipped `code-atlas query` and its modes with README, design and CHANGELOG text, and 385
  `route=` with a waiver saying TOOLS.md teaches it; no surface an agent loads named any of them, so 387 was opened
  to add them. Tool params were gated (`test_agent_brief_usage_completeness`), CLI flags were not; 387's test now
  derives `query.py`'s flags. Any non-tool entry point (a CLI, a rule-file kind) has the same gap.
- destination: first sighting.

### 384-C1 — a store that de-dupes keep-first hides later declarations from a per-row fingerprint

- type: 2 (code) · handle: `keep-first-hides-the-later-declaration`
- status: proposed · seen: 384
- evidence: `UNIQUE(qualified_name, file_path)` keeps a TS overload's first signature, so a body hash over that
  row's lines never saw the implementation: an edit to it read `unchanged`. The challenger's twins finding led there;
  each adapter now hashes the union span of a qname's declarations. Any per-row derived value has the same gap.
- destination: first sighting.

### 381-C1 — SessionStart stdout reaches only the agent; `systemMessage` is what a person sees

- type: 5 (environment) · area: `claude-code hooks / output routing` · verified-at: 2026-10-10, Claude Code docs (`hooks.md`)
- status: proposed · seen: 381
- evidence: an anchor's skew line fired at session start and the developer never saw it. The docs:
  SessionStart plain stdout is added to Claude's context; `systemMessage` surfaces a message to the
  user; PreCompact discards `systemMessage` and adds no stdout to context. Seen on screen: not yet (E1).
- destination: first sighting.

### 381-C2 — uv pins a tool install only when the install names `@<ref>`

- type: 5 (environment) · area: `install / uv tool receipt` · verified-at: 2026-10-10, uv 0.11.28
- status: proposed · seen: 381
- evidence: a local git package installed as `git+file://…` wrote no `rev` to `uv-receipt.toml`;
  as `git+file://…@<sha>` it wrote `?rev=<sha>`, and `uv tool upgrade` then answered "Nothing to
  upgrade" after a new commit. This machine's own code-atlas receipt carries `?rev=864ae8a`.
- destination: first sighting.

### 386-C1 — a hook that compacts `git diff` output makes a saved patch unusable

- type: 1 (tool) · handle: `symbol:rtk git diff`
- status: proposed · seen: 386
- evidence: `git diff -- adapters > patch` ran through the RTK rewrite hook and wrote its compact
  summary, not a patch; the `git checkout -- adapters` after it discarded the ticket's edits, which were
  re-applied from the edit script. Save a patch with `rtk proxy git diff`, or set work aside in a WIP commit.
- destination: first sighting.

### 377-C1 — a subagent's hook payload carries its parent's `session_id`, plus `agent_id`

- type: 5 (environment) · area: `claude-code hooks / payload identity` · verified-at: 2026-10-09, Claude Code 2.1.295
- status: proposed · seen: 377
- evidence: `claude -p` with a hook dumping each Grep `PostToolUse` payload: the main thread's had
  `session_id` and no `agent_id`; the general-purpose subagent's had the same `session_id` plus
  `agent_id` and `agent_type`. Anything keyed on `session_id` alone treats a subagent as its parent.
- destination: first sighting.

### 374-C1 — a memo guarded by a change probe must seed the probe when it first computes

- type: 2 (code) · handle: `seed-the-change-probe-with-the-first-answer`
- status: proposed · seen: 374, 396
- evidence: `server_identity()` read `_identity is None or _loaded_modules_changed()`, so the first
  call never stamped the loaded modules; the second took the swapped files as its baseline, and a
  `uv tool upgrade` between them left `server_stale_process: false` for good — the anchor's report.
  Every test stubbed the probe, so none could see it; the new one writes a real loaded file
  (`test_server_identity_is_live.py`). Whether uv also restored 0.2.0 on Windows stays unverified.
- destination: first sighting.

### 369-C1 — a receiver read by its spelling needs the scope that could rebind it

- type: 2 (code) · handle: `a-name-receiver-needs-its-scope`
- status: proposed · seen: 369
- evidence: `Foo.count` and `self.count` were read as the class whenever the spelling matched, so a
  parameter named `Foo` or a rebound `self` gave a confident reference onto the wrong target. The
  challenger found it; both adapters now check the enclosing scopes' parameters and bindings.
- destination: first sighting.

### 365-C1 — asking SQLite "are you locked?" misses a writer between its transactions

- type: 2 (code) · handle: `a-transaction-probe-misses-the-writer-between-transactions`
- status: proposed · seen: 365
- evidence: read-through repair probed the live DB with a zero-wait `BEGIN IMMEDIATE`. An in-place
  incremental holds `write.lock` for its whole run but its SQLite write lock only per transaction, so
  between two the probe read "free" and a repair could still wait 5 s behind the next one. The
  challenger found it; the guard now also counts `write.lock` held with no shadow file.
- destination: first sighting.

### 366-C1 — FastMCP middleware never sees a client's `roots/list_changed`

- type: 5 (environment) · area: `fastmcp / middleware notifications` · verified-at: 2026-10-07, FastMCP 3.4.5
- status: proposed · seen: 366
- evidence: a session-keyed roots cache cleared in `Middleware.on_notification` stayed stale after
  the client sent `roots/list_changed`; the challenger found it. Also, the in-process
  `Client.set_roots` leaves a live session's answer unchanged — a roots *handler* is what moves it.
- destination: first sighting.

### 363-C1 — a zero from a text search must count the rows the search cannot match

- type: 2 (code) · handle: `a-zero-must-count-what-the-search-cannot-see`
- status: proposed · seen: 363, 397
- evidence: `include_graph` attested an unused copy by searching unlinked include text for its
  basename; an interpolated include is stored as `(dynamic)` and names nothing, so it could be the
  includer yet never matches. The challenger found it; the zero now counts them and is not
  authoritative while any exist.
- destination: first sighting.

### 362-C1 — a widened target must widen every query behind the same answer

- type: 2 (code) · handle: `widen-every-query-that-shares-the-page`
- status: proposed · seen: 362, 364, 367, 389, 396, 397, 398, 400, 402, 403, 404, 407
- evidence: 362 — a constructor's answer widened its page, count and censuses but not its subtree
  spread; 364 — a new rule edge kind reached the edges but not the rule census, which read CALLS
  rows only. The challenger found both; enumerate every read the payload is built from. 407 — a
  record target widened to a file reached the stored records but not `impact`'s row-file carriers.
- destination: `cannot promote: unattended run` — `/mango:promote` is the maintainer's pass.

### 361-C1 — a regex over a literal's text reads nested and partial values as the literal's own

- type: 2 (code) · handle: `read-a-literal-by-its-structure-not-a-regex`
- status: proposed · seen: 361, 371, 398
- evidence: `{data: {action: 'inner'}}` gave `action='inner'`, `{action: 'a' + b}` gave `'a'`, and a
  ternary gave a bogus field — each a guessed rule link. The challenger found it; a depth-aware split
  at top-level commas, keeping only an entry that is exactly a name and one string, reads none of them.
- destination: first sighting.

### 357-C1 — a loop driven by "while the flag file exists" spins if the flag cannot be removed

- type: 2 (code) · handle: `a-flag-loop-needs-a-clearable-flag`
- status: proposed · seen: 357
- evidence: the lock holder re-ran while `write.pending` existed and cleared it on each pass; an
  unlink that failed with a non-`FileNotFoundError` `OSError` still counted as cleared, so a
  read-only marker re-ran builds forever. The challenger found it; `clear_pending` now reports
  whether the flag is gone, and the loop continues only when it is.
- destination: first sighting.

### 360-C1 — a ticket that names why a repair path fails assumes the path runs

- type: 2 (process) · handle: `confirm-the-blocked-path-runs`
- status: proposed · seen: 360, 365
- evidence: the ticket said read-through "cannot repair" a file added mid-build because its diff
  was empty, and the design fixed the diff. `file_outline` returned `found: false` for a path
  missing from `files` before read-through ran at all, so AC4 stayed red until it routed the
  miss through `ensure_miss`. Run the named path once before designing around its blocker.
- destination: first sighting.

### 348-C1 — an installed plugin moves only when its `version` does, and only on `claude plugin update`

- type: 5 (environment) · area: `claude-code plugins / update` · verified-at: 2026-09-30, Claude Code 2.1.284
- status: proposed · seen: 348
- evidence: a directory marketplace. With the version unchanged, a content change answered
  `already at the latest version (0.1.0)`. After a bump to 0.2.0, `claude plugin marketplace update`
  left 0.1.0 installed, and `claude plugin update code-atlas@code-atlas` moved it to 0.2.0 (restart
  to apply). Whether a session start auto-updates a third-party marketplace is unmeasured.
- destination: first sighting.

### 345-C1 — a PostToolUse hook's plain stdout never reaches the model; `additionalContext` does

- type: 5 (environment) · area: `claude-code hooks / output channel` · verified-at: 2026-09-29, Claude Code 2.1.284
- status: proposed · seen: 345, 346
- evidence: a Read hook printing a marker as plain text — the model, asked to quote it, said `NONE`;
  the same marker as `hookSpecificOutput.additionalContext` JSON came back verbatim. `code-atlas-nudge`
  emits JSON and was quoted live; `code-atlas-signal` did the same once 346 moved it to JSON, on
  `PreToolUse` too.
- destination: first sighting.

### 344-C1 — Claude Code runs a hook's `if` only when it is ONE permission rule

- type: 5 (environment) · area: `claude-code hooks / if filter` · verified-at: 2026-09-29, Claude Code 2.1.284
- status: proposed · seen: 344
- evidence: `Read(*.py)` ran on `app.py` and skipped `notes.txt`; `Read(*.php)|Read(*.py)`,
  `Read(*.{php,py,ts})` and `Read(*.php) Read(*.py)` all logged `Skipping hook due to if condition`
  on `app.py`. The shipped snippet's `|`-joined filters had never fired; `gen_skill._per_suffix`
  now emits one entry per rule.
- destination: first sighting.

### 344-C2 — a plugin's `userConfig` reaches its MCP server, never its hooks

- type: 5 (environment) · area: `claude-code plugins / userConfig` · verified-at: 2026-09-29, Claude Code 2.1.284
- status: proposed · seen: 344
- evidence: `${user_config.python}` expanded in `mcpServers.env`; a hook saw no
  `CLAUDE_PLUGIN_OPTION_PYTHON`, and an exec-form hook with the option in `args` did not run. Both
  the server and the hooks get `CLAUDE_PROJECT_DIR` and run with the project as cwd — the docs
  research said the server runs from the plugin root.
- destination: first sighting.

### 344-C3 — a directory-marketplace install reads the working tree, so it hides an uncommitted file

- type: 2 (process) · handle: `verify-the-shipped-artifact-not-the-working-tree`
- status: proposed · seen: 344
- evidence: `.gitignore`'s `.mcp.json` dropped the plugin's server file; the live install from the
  checkout connected anyway. Only a clone of the branch shows what a user gets. The challenger found it
  independently. Guard: `tests/test_claude_code_plugin.py::test_every_generated_file_is_committable`.
- destination: first sighting.

*None yet.*

### 343-C1 — Claude Code keeps only a 2,048-character prefix of an MCP server's `instructions`

- type: 5 (environment) · area: `routing surface / server instructions` · verified-at: 2026-09-29, Claude Code 2.1.284
- status: proposed · seen: 343
- evidence: a padded probe server (`%08d|` cells) via `claude -p --strict-mcp-config` returned
  `…00002043|00002… [truncated]` — cell 2,043 plus 5 chars. The cut counts characters, not bytes.
  `instructions.CLIENT_CAP` carries the figure; re-measure on a new Claude Code major.
- destination: first sighting.

## Retired — the rule carries the class now

`RECALL:` skips these. The rule named is the one that cites the id.

| claim | handle | rule |
|---|---|---|
| 349-C1 | `ungated-floor-drifts-silently` | AGENT_BRIEF P8 |
| 343-C2 | `formatter-rewrites-untouched-lines` | ENGINEERING_RULES R7.7 |
| 356-C1 | `child-build-inherits-adapter-env` | ENGINEERING_RULES R6.10 |
