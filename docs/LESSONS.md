# Lessons — code-atlas

## 068 — Synthetic anchors are edges, not source files

A rules bookmark that is a real `files` row with `parsed_ok=True` makes two honest counters disagree
by one. Keep the edge `file_path` for provenance; do not upsert a `files` row or File node. Purge
legacy bookmark rows on every apply so upgrades self-heal.

## 071 — Answers must name the tree they describe

`db_path` on status is a database location; agents need the **source root**. Emit `index_root` =
`config.root` on every answer (not status-only — agents skip status). Never guess the client's cwd.
Recommend `CA_DB_PATH` per worktree for isolation; the field only makes the un-isolated case legible.
Recalibrate the tokens-to-answer floor when every payload grows (`0.8 × observed`).

## 064 — Empty adapter map is misconfiguration, not an empty repo

`_announce` looping zero times looks like "nothing to do". Fail before meta when
`adapter_cmds` is empty. A successful build over zero matching files still stamps
non-empty `indexed_suffixes` so callers can tell the two apart. The empty-suffix-union
half needed no code: the handshake validator already rejects `extensions: []`. A guard
added for it was unreachable, and its test matched a regex the *handshake* error also
satisfied — a proving test must name the mechanism it proves, or it proves nothing.

## 063 follow-up — Cap the match set, not the CALLS table

`view_data` enrichment must look up CALLS by setter (`idx_edges_raw`), not scan a
`source_qname` prefix of *all* CALLS. A 10k cap on the whole table silently missed
~99% of anchor `setData` sites. Bound = O(matching sites); report truncation only if
a match-set cap returns.

## 063 — Count-first ACs need an Outcome above the mango separator

A “count before code” AC cannot be proven from a single squash commit. Put the table + kill/proceed
in the ticket **Outcome** (above the working-doc separator) and pin it with a small test that reads
that section — otherwise a ticket-blind challenger marks AC1 `can't tell` and Gate 4 fails.

## 062 — `key_arg` is an argument index, not a string-literal ordinal

`view_data` rules name which **argument** holds the key. Store `args` only record categories, so
enrichment must map `key_arg` through those categories to the Nth quoted literal on the call line
(e.g. `put($bag, 'extra', 1)` with `key_arg: 2`). Treating `key_arg` as a raw literal ordinal fails
as soon as a non-string arg precedes the key.

## 061 — Payload fields that earn nothing should leave nav/search

Keep `db_path` on `get_index_status` only. Make `next_tool_suggestions` state-reactive (empty when
current). Suppress redundant File∩Class search hits. Emit `subject_refreshed_only` only when the
subject was actually reparsed — a constant `true` is dead weight.

## 053 — Git refresh hooks must stay opt-in and out of band

When field evidence says an incremental can cost ~a minute, contrib git hooks must spawn
`code-atlas-refresh` in the background and always `exit 0`. Never auto-write `.git/hooks`.
Use a non-blocking lock beside the DB so overlapping hooks skip cleanly (R4.3) instead of
racing the MCP writer.

## 052 — Measure-only tickets still need an Outcome defect decision

When AC demands “is this a defect?” but the host has no repo-sized sample, record **suspected /
unconfirmed** with the field evidence and the profiler command — do not invent a phase split, and do
not close as honest price without one. Ship the profiler; leave 053 gated. Fixture-scale
confirm/refute + a stated pull_shaped wall still belong in Outcome even when the scale sample is unset.

A local-tier profiler that rebuilds `Config` from process env must **fail loud** when
`adapter_cmds` is empty — otherwise reconcile can wipe the index. After touch+restore scenarios,
re-run an untimed incremental so hashes match the restored tree.

## 060 — Record scale re-measures in ticket Outcome with a commit SHA

When an AC requires re-measuring full-build vs status on a clean server, land an `## Outcome`
section (with the tip SHA, and an honest “scale sample unset” if the anchor was not remounted) in
the same card as the code — reviewer and ticket-blind challenger both treat a missing Outcome as
not-met even when fixture tests already prove agreement.

## 058 — A status-only `detail_level` value must update CONVENTION §6

When one tool gains a third `detail_level` (here `verbose` on `get_index_status`), PLAN and the
MCP schema tests are not enough: CONVENTION §6 still said every tool is `{minimal, standard}` and
review correctly blocked on R7.2. Update CONVENTION in the same card as the Literal change.

## 057 — Scope "enumerate every result set" to store-ordered pages

When a ticket AC says every oversized answer must be fully enumerable, pin which
tools/depths use a total store ``ORDER BY … LIMIT/OFFSET`` versus a BFS with a
count floor. Otherwise review correctly rejects depth>1 callers as incomplete
against the letter of the AC. Record the scope in Outcome + PLAN in the same card.

## 056 — Spell `NodeKind` as `Literal[…]` and derive `NODE_KINDS` with `get_args`

`Literal[*NODE_KINDS]` fails mypy (`valid-type`) even when the tuple looks like string literals.
Spelling the `Literal` out (`NodeKind = Literal["File", …]`) and setting
`NODE_KINDS = get_args(NodeKind)` keeps one vocabulary, types MCP `kind: NodeKind | None` cleanly,
and publishes `anyOf: [{enum…, type:string}, {type:null}]` — coherent with a null default.
Do **not** bolt `enum` on via `json_schema_extra` as a sibling of `anyOf`: sibling keywords are
ANDed, so `null` satisfies `anyOf` but fails `enum` and the schema rejects its own default.

## 043 — A per-file dedupe keys on the full UNIQUE key, and a core guard never names `sqlite3`
Two constraints surfaced while making a duplicate-declaration file soft-fail instead of aborting the
build:
- **Dedupe by `(qualified_name, file_path)`, not `qualified_name` alone.** `replace_file_rows` is
  legitimately called with same-qname nodes for **different** files in one call (multi-candidate
  resolver siblings — `tests/test_resolver.py`). A qname-only key silently collapsed them; the design's
  own C1 already said the key is the full UNIQUE key. Match the constraint you are de-duping against.
- **A writer guard must catch a store-owned type, never `sqlite3` directly.** Adding `except
  sqlite3.Error` to `indexer.py` tripped `test_sql_confinement.py` (R1.4/R4.3 — only `store.py` may
  reference SQLite). Export a `WRITE_ERRORS = (sqlite3.Error,)` tuple from the store and catch that, so
  SQLite stays confined. Generalises: when the core must react to a boundary module's failure, the
  boundary owns the exception vocabulary.
Both were caught only by the **existing** regression suite, not the new tests — the delta-green
baseline diff (byte-comparing failure sets) is what exposed them; a bare pass/fail count would not have.
- **Baseline-set diffing has a blind spot: a test that fails-at-launch locally hides a regression in
  the code it would run post-launch.** A widened `replace_file_rows` return (`None`→`int`) broke the
  `RecordingStore` test double (it dropped the `super()` return), but `test_every_write_...` fails on
  the Windows dev host at fake-adapter subprocess launch, so it sat in **both** baseline and after
  failure-sets → the name-diff scored it "not new." CI (Linux) launched the adapter and hit the real
  `TypeError`. **Fix:** when a change alters a signature/return that a subprocess-only test path
  consumes, exercise that consumer **without** the subprocess (drive the store subclass / `_write`
  directly) rather than trusting the failure-set diff. Also: a store subclass override must propagate
  the base return value, and `tests/` is not mypy-checked so an incompatible override annotation there
  won't be caught by the `type` job.

### 043-C1 — Full-UNIQUE-key dedupe + store-owned WRITE_ERRORS
- type: 5 project-ground-truth
- status: confirmed
- evidence: `test_resolver.py` multi-file siblings; `test_sql_confinement.py`; Gate-4 clean
- area: store / indexer / R1.4 / R5.1
- destination: stays in lessons_path

## 042 — A ticket's "References" can be stale; verify claimed wiring before scoping
Task 042's References said the `source: sample` path was "already wired via `cross_repo_validate`". It
was **not** — `tokens_to_answer.py` skipped every non-fixture row and only listed sample IDs as
skipped. Taking the claim at face value would have under-scoped the task to a JSON edit; it actually
needed a new clone→build→evaluate code path plus a scheduled workflow (SCOPE S→L at Gate 0). **Fix:**
at analysis, grep for the symbol/path a ticket claims exists and confirm it before sizing; a stale
"References" line is a requirement to rebuild, not a freebie. Generalises: treat a ticket's factual
claims about the current codebase as hypotheses to verify, not givens.

### 042 — Env prerequisites are satisfiable locally, don't defer on their absence
The sample tier needs PHP+clone, absent on the Windows dev box (`php: not found`, no
`adapters/php/vendor`). Rather than defer the value claim to an operator run, a **portable PHP 8.3.33 +
Composer** env was stood up in scratchpad and the adapter ran end to end (fixtures 10/10, then samples
5/5, ratio 98.2). **Fix:** when a task is gated on a missing runtime, try provisioning a throwaway one
before falling back to a deferral — the fuller deliverable often beats the split. The earlier
`WinError 2` in tests was the *fake* test adapter's subprocess quoting, not the real adapter.

## 041 — Prefer language-free ignore globs over splitting a guarded token
Builtin Blade exclusion is `*.blade.*` (compound template suffix, any trailing extension) — not a
concatenated `*.blade.php` that defeats the R1.1 language-name guard. File-level builtins also apply
inside `collect_stubs` so `CA_STUB_ROOTS=vendor` cannot re-route ignored templates.

### 041-C1 — R1.1-honest Blade ignore + stub-walk coverage
- type: 5 project-ground-truth
- status: confirmed
- evidence: PR #47 review — split-token dodge rejected; `*.blade.*` + `_STUB_FILE_IGNORE`
- area: ignore / indexer / R1.1
- sub-shape: normative
- destination: stays in lessons_path

## 040 — Shipping enrichment requires PLAN §1 / R1.4 honesty in the same card
When an “optional enrichment layer” moves from non-goal into `code_atlas/`, update PLAN §1,
CONVENTION layout, and R1.4’s SRP inventory in the same PR — otherwise review blocks on R7.2
even when the runtime is correct.

### 040-C1 — Doc inventory lags new core module
- type: 5 project-ground-truth
- status: confirmed
- evidence: reviewer findings 1–3 on `5926e2d`; fixed in `794b55d`
- area: docs / R7.2 / R1.4
- sub-shape: normative
- destination: stays in lessons_path

## 039 — Stub roots must bypass ignore *and* hash-gate on incremental
`vendor/` is a built-in directory exclusion, so `.codeatlasignore` negation cannot re-include it —
stub indexing needs a separate filesystem walk (`collect_stubs`). Those paths are also outside
`git ls-files`, so incremental must hash-gate the whole stub set (not only `changed ∩ stubs`), or
disk edits never refresh and enabling stubs mid-life never indexes new files (R4.2).

### 039-C1 — Incremental stub refresh is hash-gated, not git-named
- type: 5 project-ground-truth
- status: confirmed
- evidence: reviewer finding on `changed_set & stub_set`; fixed in `ddcfe77` + `test_incremental_hash_gates_stub_edits`
- area: indexer / R4.2
- sub-shape: normative
- destination: stays in lessons_path
- seen: 039

## 038 — Edge-shaped hop dicts trip R3.2 unless keys are assigned one-by-one
Building a hop `{source_qname, target_qname, kind, confidence_tier, line}` as one dict literal
fails `test_contract_sole_source` (≤1 EDGE_FIELDS string per collection). Assign each key in its
own statement (or concatenate single-field key tuples), matching the impact/reachability pattern.

### 038-C1 — Path hop shaping must not multi-key EDGE_FIELDS in one literal
- type: 5 project-ground-truth
- status: confirmed
- evidence: sole-source fail on store.py / explain_path.py; fixed via per-statement hop keys
- area: store / tools / R3.2
- sub-shape: normative
- destination: stays in lessons_path
- seen: 038

## 037 — A guard that checks a formula against itself cannot catch a unit error in its input
037's A/B summed `call_delta` over **4** measured questions, then `verdict()` multiplied that
aggregate by a call count — so the published break-even was in *4-call batches*, wrong by ~4× (8.9 vs
35.7). The existing guard test fed `verdict()` hand-picked deltas and asserted its algebra, which was
self-consistent and stayed green. **Normalize where the number is produced** (`measure()` publishes
`call_delta_per_call`), and write the guard against the **unit**, not the arithmetic.

The tell was in the prose, not the code: the same sentence read "~7 tokens per call" and "break-even
8.9", and 241/7 ≈ 34. When a derived figure and its own stated rate disagree, the figure is wrong —
divide it out by hand before publishing it.

### 037-C1 — Aggregate-vs-per-unit must be normalized at the producer, not the consumer
- type: 5 project-ground-truth
- status: confirmed
- evidence: reviewer round 1 finding 1; `call_delta 27` over 4 questions; corrected 8.9 → 35.7 calls;
  regression guard `test_break_even_is_in_calls_not_in_measured_batches` fails `10.0 vs 40.0` when the
  defect is reinstated (re-mutated by the round-2 reviewer)
- area: benchmark / tokens-to-answer / A-B measurement
- sub-shape: normative
- destination: stays in lessons_path
- seen: 037

### 037-C2 — A decision's argument must be withdrawn when its number moves, not re-fitted
- type: 5 project-ground-truth
- status: confirmed
- evidence: Decision §1 ("crossover ~9, an agent passes it inside one task") no longer held at ~36
  calls and was struck rather than re-argued; the verdict was re-grounded on "no net win at all"
  (−234…+434 tokens) plus C3 and R1.2, and the round-2 reviewer judged the result honest
- area: mango / review / recorded decisions
- sub-shape: normative
- destination: stays in lessons_path
- seen: 037

## 033 — Split vocab-vs-emit when a later ticket owns emission
When Scope lists an enum member (e.g. `index_stale`) that a dependent ticket (035) will emit, refine
must record **W1 vocab present** and **W2 no emit-proof this card**. Otherwise a ticket-blind
challenger scores emission as **not met** against the raw ticket and looks like a Gate-4 miss.

### 033-C1 — Enum members deferred to a paired ticket need W1/W2 at refine
- type: 5 project-ground-truth
- status: confirmed
- evidence: challenger 7cf518c3 row 1b; ASSUMED Option 1; task 035 pairs with 033
- area: mango / refine / reason-codes
- sub-shape: normative
- destination: stays in lessons_path
- seen: 033

Durable lessons discovered while shipping tasks: constraints found, wrong assumptions, process gaps.
One entry per lesson; newest first.

## 030 — Alias remap must rewrite `Class::method`, not only class FQNs
`alias_targets` maps alias class → real class. CALLS/NEW often carry `\Alias::method`. Remapping
only exact class keys leaves method edges dangling; rewrite the class portion before `::` so
`find_callers`/`find_references` under Real see Alias users.

### 030-C1 — Alias remap rewrites the class portion of member qnames
- type: 5 project-ground-truth
- status: confirmed
- evidence: resolver `_lookup_raw` rpartition; proving test Aka::ping → Real::ping
- area: resolver / aliases
- sub-shape: normative
- destination: stays in lessons_path
- seen: 030

## 029 — Innermost class owns `parent::`, not an outer ancestor
`enclosingParentQname` must stop at the first `Class_` in the scope stack. Walking past a
null-`extends` class (e.g. anonymous nested inside `Outer extends Base`) falsely attributes
`Outer`'s parent to the inner class — a RESOLVED-eligible lie (R5.2). Return null when the
innermost class has no extends and leave `\parent::…` as today.

### 029-C1 — parent:: resolution must not walk past an innermost Class_ with null extends
- type: 5 project-ground-truth
- status: confirmed
- evidence: review finding on feat/029; NestedOuter fixture; Visitor.php enclosingParentQname
- area: php-adapter / receiver-resolution
- sub-shape: normative
- destination: stays in lessons_path
- seen: 029

## 028 — Prefer `parsed_ok` over a parallel meta parse-failure counter
When a ticket asks for `parse_failures` "if the build does not already persist this", check existing
aggregates first. `files.parsed_ok` already feeds `GraphStore.counts()["failed"]`; a second `meta`
counter can drift from the file rows (R4). Alias the status field (`parse_failures`) to that count
on `standard` and keep the existing `failed` key for minimal byte-identity.

### 028-C1 — Parse-failure status reads `files.parsed_ok` via `counts()["failed"]`, not a parallel meta counter
- type: 5 project-ground-truth
- status: confirmed
- evidence: ticket 028 R3 conditional; `code_atlas/store.py` counts(); indexer marks `parsed_ok=0`
- area: index-status / parse-health
- sub-shape: normative
- destination: stays in lessons_path
- seen: 028

## 016 — Dependents must be reparsed, not reconstructed
Hash-skipping dependents made `file_paths_targeting` dead work: a dependent is unchanged by
construction, so its hash always matches and it never reached the adapter. Reconstructing its edges
via `unlink_targets` (and collapsing HEURISTIC siblings) then lost adapter confidence tiers and
legitimately duplicated keys — diverging from a full rebuild (R4.2). **Always reparse dependents**;
hash-skip only unchanged *changed* paths. `replace_file_rows` restores adapter output verbatim.

Also: fold paths leaving `collect` (rename sources, newly ignored) into affected qnames *before*
reconcile — `git diff --name-only` names only the rename destination — and union the working tree
vs `HEAD` into the incremental path set so uncommitted edits are not a silent no-op.

## 014 — `code-atlas --help` is not an install smoke test
FastMCP's entry point always calls `.run()` (stdio). Passing `--help` still starts the MCP transport
and will hang CI waiting on stdin. Prove a non-editable install with `importlib.metadata` (version +
console_scripts entry) and an import of `TOOL_NAMES`, never by invoking the server binary.

## 014 — `LIKE ESCAPE '\\'` breaks PHP qnames
Namespace filters that use SQL `LIKE` with backslash as the escape character mis-parse every `\` in
a PHP FQN (`\App\Models\…`). Use a rare escape character that does not appear in qnames (e.g. `!`)
and escape only `!`, `%`, and `_`.

## 012 — Planted tmp_path negative controls must not use relative_to(ROOT)
AC2 plants live under pytest `tmp_path`, which is outside the repo. Calling
`path.relative_to(ROOT)` on those plants raises `ValueError` and breaks the proof that the
grep-gate fails on a planted hit. Assert on `Path` identity (or root the plant under the repo).

## 025 — NEW must peek anonymous qnames without registering them
`enterNew` and `enterAnonymousClass` both need the same H1 qname. If both call a registering
`anonymousQname()`, the Class_ node gets a spurious collision suffix even when it is the only
anonymous class on that line. Peek (`register: false`) on the NEW edge; register only when declaring
the Class_ node. Same-line *true* collisions append `:col` from `getStartFilePos()` (ticket C1) —
not an ordinal, which would rename later same-line declarations when one is inserted earlier.

## 008 — Proving-test names must not overclaim the path shape they assert
Review caught that `…_results_stay_repo_relative` asserted host-**absolute** `ParseResult.path` after
wire rebase (Approach §3 keeps the **caller** path). The relative half was the real repo-relative
proof; the name lied about the absolute half. Rename (or split asserts) so the test title matches
what each half actually checks — R6.1 proofs and CONVENTION “repo-relative” claims stay honest.

## 011 — Never promote HEURISTIC to RESOLVED just because a name is unique
PR review caught that `_resolve_symbol` set the tier from hit count alone. An adapter-emitted
`HEURISTIC` edge whose `target_raw` matched one qname became `RESOLVED`. A unique name does not make
a guess certain — M6 impact will trust these tiers. Fix: take the weaker of (incoming, computed).

**Also deferred to M4 (task 015):** per-edge SQLite commits + materializing all unresolved edges, and
top-N name-match fan-out on common method names (`get`/`save`) exploding edge counts.

## 011 — A clean `Reviewed at` does not survive tip commits landed after it
Task 011's review was clean at `cf445e4` (resolver change-list only). Teammate commits for
`AGENTS.md` / `.mailmap` then landed on the same branch. Finalise's stale-review guard correctly
refused: the marker is a **file-set** claim, not a "we reviewed this ticket once" claim. Keeping the
tip without a new `Reviewed at` covering HEAD is a **human override**, not a cleared gate.

**Fix:** either (a) re-review the full tip and rewrite the marker, or (b) land teammate docs/chore
work on a separate branch/PR so the feature marker stays valid.

## 010 — The same thread rule that enforced a design in 009 dictated the design in 010
Task 009 found that `sqlite3` binds a connection to its creating thread, and treated it as a free
guarantee: R4.3's single writer could not be broken by accident. Task 010 met the same fact from the
other side. FastMCP registers a synchronous tool with `run_in_thread=True` by default, so **every**
tool call runs on a worker thread — a `GraphStore` opened when the server was built raises
`ProgrammingError: SQLite objects created in a thread can only be used in that same thread` on its
first use, in every call, forever. The obvious shape (build the server, hold the store, serve) does
not work at all.

So each tool opens its own store inside the call, and `get_index_status` opens none when there is no
database file. The lesson is not "sqlite is thread-affine" — 009 already recorded that. It is that a
constraint discovered as a *guarantee* in one task can be the thing that *rules out* the natural
design in the next, and only a spike against the real library says which. This one was tagged
`novel-untested` at design and spiked before Gate 2; it came back **false**, and the ten-line spike
that killed it cost less than the rewrite would have.

**Fix:** when a task hands work to a third-party runtime, spike *where that runtime runs your code*
before designing what your code holds on to.

## 009 — The runtime may already enforce the rule you were about to prove by convention
R4.3's "single SQLite writer" read like a discipline the indexer had to keep. It is not: `sqlite3`
binds a connection to the thread that created it, so a worker thread that tried to write through the
build's store raises `ProgrammingError` — loudly, before a single row is touched. The design was
better for finding out: the fan-out needs no lock, no write queue, and no review vigilance, because
the failure mode it was guarding against cannot compile past the first call.

The general lesson is about **when** to check. This was a `novel-untested` assumption tagged at
design and spiked *before* Gate 2, not discovered at execute. Two of the five spikes changed the
design, and this one changed it by coming back **false** — which is the whole point of tagging an
assumption instead of asserting it.

## 009 — A negative control can indict the code instead of the test
Five mutation controls ran against `full_build`; two came back green, and they meant opposite things.
Deleting the `sorted()` from collection broke nothing because the fixture tree happened to be
discovered in order — a **test** too weak to see its own subject, fixed by shaping a tree the walk
provably reaches out of order. Deleting the per-build `rebuild_search_index()` also broke nothing,
but no test could ever have caught it: the schema's triggers already keep `nodes_fts` current, so the
call was a full re-index that changed nothing. That one indicted the **code**, and it was removed.

So a green negative control is a question, not a verdict: *can* a test see this, or is the line
unreachable by construction? The first answer costs a better fixture; the second costs a deletion —
and on a 112k-file repo, that particular deletion is a whole FTS rebuild per build.

## 007 — A stream protocol inherits the host's `php.ini`, so "it works here" proves nothing
Two ini settings silently corrupt a JSONL protocol, and neither shows up on a developer machine.
`display_errors` defaults to **stdout** on many builds, so a PHP notice lands *between two protocol
lines* and the driver reads it as a reply; `output_buffering` holds `echo` output until the process
exits, deadlocking a lock-step reader. Both are host state, so the same file yields different results
on two machines — exactly what R4.2 forbids. **Fix:** force `display_errors` to `stderr` before
anything is written, and write replies with `fwrite(STDOUT, …)`. Note the trap: the design approved
`fflush(STDOUT)` as "immune to any host ini" and that was **false** — `echo` has already entered PHP's
*output buffer*, which neither `fflush()` nor `flush()` releases. Only bypassing `echo` works. Prove a
buffering fix by reading **while the child still runs**; at exit every buffer flushes, so a
post-mortem read passes no matter what.

## 007 — A language's natural empty value may not be the contract's
`json_encode(['capabilities' => []])` yields `{"capabilities":[]}` — a JSON **array**. The contract
requires an object, so the core rejected the handshake with a loud startup error naming
`meta.capabilities`, pointing the reader at the core rather than at the one adapter line responsible.
PHP has one array type for both shapes; `new stdClass()` is needed to get `{}`. **Fix:** spike the
handshake against the real validator before writing the loop — the design phase caught this, and had
it slipped to execute it would have read as a driver bug. Generalises to every adapter: an empty map,
an empty list, and a null are three different wire values, and a language that conflates any two of
them will encode the wrong one by default.

## 024 — A rule enforced only by a lifecycle gate is unenforced for work that skips the lifecycle
`AGENTS.md` says no PR opens without the task's token spend recorded in **both** the working-doc cost
ledger and the BACKLOG table. Tasks 001–006 all complied — because mango's `finalise` phase has a
ledger-completeness gate that refuses to proceed without it. Task 024 was done directly, outside the
five-phase lifecycle, so nothing checked, and PR #14 opened with no token row and a status left at
`in-progress`. The rule was never *disagreed* with; it simply had no enforcement outside one tool's
happy path. **Fix:** `tests/test_backlog_bookkeeping.py` asserts both bookkeeping rules from the repo
itself — every task's status matches in the backlog table and its frontmatter, and every `done` task
carries a token row naming a measured spend and a PR link. Negative-controlled three ways: deleting the
row, desyncing a status, and writing a spend cell with no number each turn it red. Generalises: when a
process rule lives in a document and its only enforcement is a step inside one workflow, it is
**optional by construction** — the moment work arrives by another path, the rule is silently off. Put
the check where the artifact lives, not where the process happens to run.

## 006 — An `instanceof` narrow that falls through to null erases the difference between "absent" and "unhandled"
The PHP visitor read a parameter's type as `$param->type instanceof Node\Name ? fqn(...) : null`. That
looked right and passed both fixtures, because both typed parameters happened to use *class* types. But
`string`, `int`, `bool` and every other scalar hint arrive as `Node\Identifier`, so they fell through to
`null` — and in the emitted JSON, `"type": null` is exactly what an **untyped** parameter looks like. The
adapter was not deferring the case; it was reporting the wrong answer, and nothing could tell. A
ticket-blind challenger found it by writing its own probe file with a scalar hint. **Fix:** when mapping
a foreign AST or schema into your own vocabulary, an `instanceof` chain whose fallback is `null` needs
either exhaustive arms or a loud fallback — never a silent one that collides with a legitimate value.
Generalises: a partial mapping is only safe when "I did not handle this" is **distinguishable in the
output** from "this was not there". Ask of every `?:` default whether some real input already produces
that same value; if so, the branch cannot be audited from the data.

## 006 — The first vendored dependency turns a repo-wide grep-gate into a false positive
`ci.yml`'s R2.2 gate greps `adapters/` for framework names. It was green for five tasks because
`adapters/` was empty. The first `composer install` put 280 files there, and **Composer's own
`vendor/composer/ClassLoader.php` documents itself with a `Symfony\Component` example** — so a
guardrail about *our* source failed on a dependency nobody here wrote. The same run also had
`tests/test_sql_confinement.py` sweeping all 280 dependency files looking for the string `code_atlas`.
**Fix:** scope every guardrail grep to *authored* source (`--exclude-dir=vendor --exclude-dir=node_modules`)
and then guard the scoping — a filter that quietly swallows the authored files too restores exactly the
0/0 vacuity the guard existed to remove (LESSONS 002), so assert the sweep is non-empty. Do it in the
change that introduces the first dependency, since that is the change that creates the collision.
Generalises: a text-grep guardrail's blast radius is a **directory**, not a codebase, and directories
grow third-party content the moment a package manager runs.

## 005 — A subprocess seam fails by silence and by chatter, not by errors
Two failure modes of a long-lived adapter process are invisible in the happy path and neither raises.
**Chatter:** with `stderr=PIPE` left undrained, a child that writes more than a pipe buffer (~64 KB)
blocks writing while the driver blocks reading stdout — a spike reproduced it with 200 KB and got no
reply in 3 s. `stderr=STDOUT` is worse: it corrupts the protocol stream. Only `DEVNULL` or a real file
is safe, and a PHP adapter emitting warnings makes this the *normal* case, not an exotic one.
**Silence:** a child that stays alive and simply never answers hangs a blocking `readline()` forever —
and it does so at `start()` (waiting for the handshake), not only at `parse()`. The analysis had
recorded the hang as a `parse()`-only exclusion; execute found the wider truth when a fixture mode that
went mute wedged the whole suite. **Fix:** never leave a subprocess pipe undrained; treat *silence* as
a first-class failure mode with its own deadline, and when deferring it say which calls it can strike,
not just the obvious one. Generalises: for any IPC seam, enumerate what happens when the peer says
**too much** and when it says **nothing** — those are the two that hang rather than throw, and a test
suite that only feeds well-formed errors will never meet either.

## 005 — A ticket-blind agent can read the working doc without opening it
The challenger is kept honest by *withholding* the working doc: it is handed the raw ticket text plus
the diff and told not to read `docs/tasks/`. It obeyed — and still saw the design. A `git grep` for
`--server` across the repo returned matching lines *from* the working doc, including a "RATIFIED (Q2)"
rationale, so the author's reasoning landed in front of it before it had formed its own view on that
requirement. It disclosed this itself; six of its seven other verdicts were unaffected. **Fix:** the
blind-agent brief must exclude the tickets directory from **every search**, not just from direct reads
(`git grep ... -- ':!docs/tasks/'`, `grep --exclude-dir`), and the agent should be told to report a
leak rather than quietly continue. Generalises: an information barrier enforced as "don't open that
file" leaks through every tool that reads files *without opening* them — grep, search indexes, IDE
symbol lookup. Scope the barrier to the **content**, not to the act of opening; and since the guarantee
is procedural, report it as procedural rather than as proof.

## 004 — A schema object that exists is not a schema object that runs
`tests/test_store.py` asserted every DDL object was registered in `sqlite_master`, and that assertion was
read as if it also proved each object *works*. It does not. The ticket-blind challenger replaced the body
of the `nodes_au` FTS trigger with a reference to a nonexistent column and **the whole suite still passed**
— because `GraphStore.replace_file_rows` only ever DELETEs then INSERTs, so nothing in the codebase fires
an UPDATE on `nodes`. A broken trigger would have shipped green. **Fix:** for any schema object no code
path currently exercises (trigger, `DEFAULT`, `CHECK`, `ON DELETE`), write a test that *fires* it directly
in SQL, and keep the object rather than deleting it as dead code when it closes an invariant — a mirror
with a hole desyncs silently the first time a later task takes that path. Generalises: **existence tests
and behaviour tests are different tests**, and mutation is the cheap way to tell which one you actually
wrote — break the thing on a copy and see whether anything goes red. The same run also caught a related
self-report: the task's own matrix claimed `busy_timeout` was asserted when nothing asserted it.

## 036 — Distribution hooks that promise exit 0 must wrap config load too
A Claude Code PostToolUse script documented as "always exits 0" still raised when
`load_config` saw an unpaired `CA_HOST_ROOT`. Soft-fail only around `reparse_file` is not
enough — wrap imports + config + reparse. Relative path containment must `resolve()` under
the project root (``../`` escapes are not no-ops).

## 035 — Missing on-disk paths are stale; planted fixtures must write matching bytes
`FreshnessGuard.ensure` returns `"stale"` when `(root/path).is_file()` is false so production
never asserts `reason=ok` for a deleted indexed file. Planted-store nav tests therefore write real
bytes (and the matching content hash) in `seed_file(..., root=)` — a shared short-circuit that
trusted the index for missing paths caused the trust bug 033 closed. Adapter/DB failures during
`reparse_file` also degrade to `"stale"` instead of crashing the read tool.

## 073 — Zero-hit freshness cannot invent a subject path
Read-through (035) only repaired paths already on the answer. A brand-new symbol in a drifted file
matched nothing, so `ensure_qname` / `search_symbol` returned a confident empty without reparsing.
**Fix:** miss-repair spends `READ_THROUGH_CAP=1` on the sole dirty indexed tracked file; multiple dirty
files emit `index_stale` + `try_instead=file_outline` instead of guessing. Requires git
`dirty_paths`. Generalises: result-driven repair is incomplete without a documented miss path.

## 065 — Inbound includes cannot be counted by target_qname
`include_graph(direction="imported_by")` used to emit `unresolved_includes: 0` because the outbound
counter is skipped for that direction — a confident zero that is structurally always zero. Unlinked
inbound edges have empty `target_qname`, so they are invisible to `edges_by_target`. **Fix:** omit the
field for `imported_by`, and only claim `relationship_not_modelled` when a cheaper basename
`instr(target_raw, …)` proxy finds evidence. Generalises: a counter that is unanswerable in one
query direction must not print zero; absent beats a structural lie.

## 004 — `git checkout -- <file>` restores the committed state, so it deletes uncommitted work
While negative-controlling the R3.2 guard, a violating literal was appended to `code_atlas/store.py` and
then reverted with `git checkout -- code_atlas/store.py`. The implementation was **not yet committed**, so
the checkout restored the one-line stub from `main` and the whole module was gone; it had to be rewritten.
The first negative control had worked only because the file it mutated (`config.py`) was unmodified in the
working tree. **Fix:** commit the work **before** running any guard experiment that mutates tracked files,
and restore from a `cp` copy (verify with `sha256sum`) rather than from git. Generalises: `git checkout --`
is not an undo for *your* edit — it is a reset to the index/HEAD, and its blast radius is every uncommitted
change in that file.

## 003 — The R1.1 grep-gate fires on ordinary English, not just on code
The CI guardrail for "no language branches in the core" is
`grep -rEn 'if[^\n]*\blanguage\b[^\n]*==|match[^\n]*\blanguage\b' code_atlas/`
(`.github/workflows/ci.yml:49`). Its second alternative has **no code anchor**: any line under
`code_atlas/` where the token `match` appears *before* the word `language` fails the build — including
a plain comment or docstring like `# match the language name to its env var`. The reverse order
(`language … match`) is safe. **Fix:** when touching the core, phrase prose so `language` precedes
`match` (or avoid one word), and run the gate's exact regex locally before opening the PR — a green
`pytest`/`ruff`/`mypy` says nothing about it. Generalises: a guardrail expressed as a text grep over
source will also match the *prose* in that source, so treat comments and docstrings as inputs to
every grep-gate, not just the code.

## 002 — A guard written before its consumers exist must be negative-controlled
Task 002's AC2(b) ("no field lists duplicated in store/indexer") was **vacuously true**: all five
schema-consuming modules were one-line stubs, so any grep or guard passed while proving nothing about
the tasks that would actually write them. A guard that cannot fail is not evidence. **Fix:** inject a
real violation (`COLUMNS = ["kind", "name", …]` appended to `store.py`), confirm the guard fails, then
remove it and confirm the file is byte-identical again — and assert the guard's own inputs are non-empty
(`len(VOCABULARY) == 38`, `len(consumers()) >= 5`) so it can't silently degrade to a no-op later.
Generalises: when an acceptance criterion is satisfied only because the thing it constrains doesn't
exist yet, say so out loud and either negative-control the guard or record the vacuity.

## 001 — Fold a mid-task governance request into the ticket's scope, don't ride it on the branch
When a user asks for a repo-wide rule change mid-task (here: the "Token usage on PR" rule in
`AGENTS.md` + `docs/BACKLOG.md`), the ticket-blind challenger and the reviewer both read it as
untraceable scope creep — it maps to no ticket requirement. **Fix:** add it to the task's
Scope/Deliverables + a matrix row (task 001 → R6 + change-list item 8) with a one-line rationale, so
every hunk still traces to a requirement. Splitting it into its own docs ticket is the alternative;
either way, never let a change ride the branch untraceable to a row.
